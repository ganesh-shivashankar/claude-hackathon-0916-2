#!/usr/bin/env python3
"""Classify the most likely failure mode based on sensor signals and reference data.

Reads failure_mode_reference.csv (5 rows) and failure_event_log.csv (8 rows).
Scores each failure mode against provided signals and returns a ranked list
with confidence levels, evidence, lead time, and recommended actions.

Usage:
    python tools/classify_failure_mode.py '{"pump_id":"P-07","signals":{"bearing_temp_c":"rising >2C/hr","vibration_x_mms":"elevated","motor_current_amps":"rising"}}'
    python tools/classify_failure_mode.py '{"pump_id":"P-07","signals":{"bearing_temp_rising":true,"vibration_elevated":true}}'
"""

import csv
import json
import os
import sys

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "use-case", "data"))
FAILURE_REF_FILE = os.path.join(DATA_DIR, "failure_mode_reference.csv")
FAILURE_LOG_FILE = os.path.join(DATA_DIR, "failure_event_log.csv")

# Signal keyword mapping for each failure mode.
# Maps user-friendly signal keys to the terms that appear in the reference CSV.
SIGNAL_KEYWORDS = {
    "bearing_wear": {
        "primary": [
            "bearing_temp", "temp_rising", "temperature_rising",
            "bearing_temp_rising", "bearing_temp_c",
        ],
        "secondary": [
            "vibration_elevated", "vibration_x", "vibration_high",
            "vibration_x_mms", "vibration_y_mms",
            "motor_current_rising", "motor_current_elevated",
            "current_rising", "motor_current_amps",
        ],
    },
    "seal_failure": {
        "primary": [
            "seal_leak", "seal_leak_detected", "leak_detected", "seal_failure",
        ],
        "secondary": [
            "suction_pressure_dropping", "suction_pressure_low",
            "suction_pressure_psi", "suction_pressure",
            "flow_declining", "flow_rate_declining", "flow_dropping",
            "flow_rate_m3hr", "flow_rate",
        ],
    },
    "cavitation": {
        "primary": [
            "suction_pressure_low", "suction_pressure_dropping",
            "low_suction", "cavitation",
            "suction_pressure_psi", "suction_pressure",
        ],
        "secondary": [
            "vibration_axial", "vibration_axial_elevated",
            "axial_vibration", "vibration_axial_mms",
            "flow_erratic", "flow_rate_erratic", "flow_unstable",
            "flow_rate_m3hr", "flow_rate",
        ],
    },
    "impeller_damage": {
        "primary": [
            "differential_pressure_declining", "differential_pressure_dropping",
            "dp_declining", "head_declining",
            "differential_pressure_psi", "differential_pressure",
        ],
        "secondary": [
            "flow_declining", "flow_rate_declining", "flow_dropping",
            "flow_rate_m3hr", "flow_rate",
            "motor_current_dropping", "motor_current_declining",
            "current_dropping", "motor_current_amps",
        ],
    },
    "misalignment": {
        "primary": [
            "vibration_axial_high", "vibration_axial_elevated",
            "axial_vibration_high", "vibration_axial",
            "vibration_axial_mms",
        ],
        "secondary": [
            "bearing_temp_elevated", "bearing_temp_high",
            "bearing_temp_c", "bearing_temp",
            "motor_current_elevated", "motor_current_high",
            "motor_current_rising", "motor_current_amps",
        ],
    },
}


def normalize_signal(key):
    """Normalize a signal key to a canonical lowercase underscore form."""
    return key.lower().strip().replace(" ", "_").replace("-", "_")


def load_failure_reference():
    """Load failure_mode_reference.csv and return rows with row numbers."""
    modes = []
    with open(FAILURE_REF_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            modes.append({**row, "_row": row_num})
    return modes


def load_failure_history(pump_id):
    """Load failure events for a specific pump from failure_event_log.csv."""
    events = []
    with open(FAILURE_LOG_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            if row["pump_id"] == pump_id:
                events.append({
                    "event_id": row["event_id"],
                    "failure_mode": row["failure_mode"],
                    "failure_ts": row["failure_ts"],
                    "downtime_hrs": float(row["downtime_hrs"]),
                    "repair_cost_usd": float(row["repair_cost_usd"]),
                    "source_row": row_num,
                })
    return events


def load_all_failure_events():
    """Load all failure events to determine row range for citations."""
    rows = []
    with open(FAILURE_LOG_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            rows.append(row_num)
    return rows


def classify(pump_id, signals):
    """Classify failure mode from signals.

    1. Load all 5 failure modes and their signatures
    2. Score each mode against signals (primary=3pts, secondary=1pt)
    3. Return ranked list with confidence, evidence, lead time, recommended action
    4. Check failure_event_log.csv for past occurrences on this pump
    """
    ref_modes = load_failure_reference()
    history = load_failure_history(pump_id)

    # Normalize user signals into a set of searchable tokens
    user_signals = set()
    raw_signal_descriptions = {}
    for key, val in signals.items():
        norm = normalize_signal(key)
        val_str = str(val).lower().strip() if val is not None else ""

        if val is True or val_str in ("true", "yes", "1", "detected"):
            user_signals.add(norm)
            raw_signal_descriptions[norm] = f"{key}=true"
        elif isinstance(val, str) and val.strip():
            # Add the base signal key
            user_signals.add(norm)
            # Also add key+trend combinations
            for trend_word in ("rising", "elevated", "dropping", "declining",
                               "erratic", "high", "low", "detected"):
                if trend_word in val_str:
                    user_signals.add(f"{norm}_{trend_word}")
            raw_signal_descriptions[norm] = f"{key}={val}"
        elif isinstance(val, (int, float)):
            user_signals.add(norm)
            raw_signal_descriptions[norm] = f"{key}={val}"

        # Also generate sub-tokens so "bearing_temp_c" matches "bearing_temp"
        parts = norm.split("_")
        for i in range(1, len(parts)):
            user_signals.add("_".join(parts[:i]))

    # Score each failure mode
    results = []
    ref_row_start = None
    ref_row_end = None

    for ref in ref_modes:
        row_num = ref["_row"]
        if ref_row_start is None or row_num < ref_row_start:
            ref_row_start = row_num
        if ref_row_end is None or row_num > ref_row_end:
            ref_row_end = row_num

        mode = ref["failure_mode"]
        keywords = SIGNAL_KEYWORDS.get(mode, {"primary": [], "secondary": []})

        primary_matches = []
        secondary_matches = []

        for sig in user_signals:
            # Check primary keywords
            for pk in keywords["primary"]:
                if sig in pk or pk in sig:
                    primary_matches.append(sig)
                    break
            # Check secondary keywords
            for sk in keywords["secondary"]:
                if sig in sk or sk in sig:
                    secondary_matches.append(sig)
                    break

        primary_matches = list(set(primary_matches))
        secondary_matches = list(set(secondary_matches))
        total_matches = len(primary_matches) + len(secondary_matches)

        if total_matches == 0:
            continue

        # Determine confidence
        if primary_matches and secondary_matches:
            confidence = "HIGH"
        elif primary_matches:
            confidence = "MEDIUM"
        elif len(secondary_matches) >= 2:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        score = len(primary_matches) * 3 + len(secondary_matches)

        # Check past events for this pump + failure mode
        past_events = [e for e in history if e["failure_mode"] == mode]

        results.append({
            "failure_mode": mode,
            "confidence": confidence,
            "score": score,
            "primary_signal_matches": primary_matches,
            "secondary_signal_matches": secondary_matches,
            "primary_sensor_signature": ref["primary_sensor_signature"],
            "secondary_indicators": ref["secondary_indicators"],
            "typical_lead_time_hrs": ref["typical_lead_time_hrs"],
            "recommended_action": ref["recommended_action"],
            "iso_10816_zone_at_detection": ref["iso_10816_zone_at_detection"],
            "past_events_this_pump": past_events if past_events else None,
            "source": {
                "file": "failure_mode_reference.csv",
                "row": ref["_row"],
                "columns": [
                    "failure_mode", "primary_sensor_signature",
                    "secondary_indicators", "typical_lead_time_hrs",
                    "recommended_action", "iso_10816_zone_at_detection",
                ],
            },
        })

    results.sort(key=lambda x: x["score"], reverse=True)

    # Build event log source citation
    event_log_source = None
    pump_event_rows = [e["source_row"] for e in history]
    if pump_event_rows:
        event_log_source = {
            "file": "failure_event_log.csv",
            "row_range": [min(pump_event_rows), max(pump_event_rows)],
            "total_rows_matched": len(history),
            "columns": [
                "event_id", "pump_id", "failure_mode",
                "failure_ts", "downtime_hrs", "repair_cost_usd",
            ],
        }

    if not results:
        return json.dumps({
            "status": "no_match",
            "pump_id": pump_id,
            "signals_provided": dict(signals),
            "normalized_signals": sorted(user_signals),
            "message": (
                "No failure mode matched the provided signals. "
                "The signals may indicate a condition not in the reference database."
            ),
            "sources": [
                {
                    "file": "failure_mode_reference.csv",
                    "row_range": [ref_row_start, ref_row_end],
                    "total_rows_matched": len(ref_modes),
                    "columns": [
                        "failure_mode", "primary_sensor_signature",
                        "secondary_indicators",
                    ],
                }
            ],
        }, indent=2)

    output = {
        "status": "ok",
        "pump_id": pump_id,
        "signals_provided": dict(signals),
        "normalized_signals": sorted(user_signals),
        "top_diagnosis": results[0]["failure_mode"],
        "top_confidence": results[0]["confidence"],
        "top_recommended_action": results[0]["recommended_action"],
        "top_lead_time_hrs": results[0]["typical_lead_time_hrs"],
        "classifications": results,
        "historical_failures_this_pump": history if history else None,
        "sources": [
            {
                "file": "failure_mode_reference.csv",
                "row_range": [ref_row_start, ref_row_end],
                "total_rows_matched": len(ref_modes),
                "columns": [
                    "failure_mode", "primary_sensor_signature",
                    "secondary_indicators", "typical_lead_time_hrs",
                    "recommended_action", "iso_10816_zone_at_detection",
                ],
            },
        ],
    }
    if event_log_source:
        output["sources"].append(event_log_source)

    return json.dumps(output, indent=2)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": (
                "Usage: classify_failure_mode.py "
                "'{\"pump_id\":\"P-07\",\"signals\":{...}}'"
            ),
            "examples": [
                (
                    '{"pump_id":"P-07","signals":{'
                    '"bearing_temp_c":"rising >2C/hr",'
                    '"vibration_x_mms":"elevated",'
                    '"motor_current_amps":"rising"}}'
                ),
                (
                    '{"pump_id":"P-07","signals":{'
                    '"bearing_temp_rising":true,'
                    '"vibration_elevated":true}}'
                ),
            ],
        }))
        sys.exit(1)
    params = json.loads(sys.argv[1])
    print(classify(**params))
