"""Classify failure mode based on sensor signals against reference data."""

import csv
from typing import Optional

from strands import tool

from config import DATA_DIR, PRIMARY_SIGNAL_WEIGHT, SECONDARY_SIGNAL_WEIGHT

FAILURE_REF_FILE = DATA_DIR / "failure_mode_reference.csv"
FAILURE_LOG_FILE = DATA_DIR / "failure_event_log.csv"

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


def _normalize_signal(key):
    return key.lower().strip().replace(" ", "_").replace("-", "_")


@tool
def classify_failure_mode(pump_id: str, signals: dict) -> dict:
    """Match sensor anomaly signals against 5 known failure modes and return ranked diagnoses.

    Failure modes: bearing_wear, seal_failure, cavitation, impeller_damage, misalignment.

    Parameters:
        pump_id: Pump ID (P-01 through P-12)
        signals: Dict of observed signals, e.g. {"bearing_temp_rising": true, "vibration_elevated": true}
    """
    ref_modes = []
    with open(FAILURE_REF_FILE) as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            ref_modes.append({**row, "_row": row_num})

    history = []
    with open(FAILURE_LOG_FILE) as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            if row["pump_id"] == pump_id:
                history.append({
                    "event_id": row["event_id"],
                    "failure_mode": row["failure_mode"],
                    "failure_ts": row["failure_ts"],
                    "downtime_hrs": float(row["downtime_hrs"]),
                    "repair_cost_usd": float(row["repair_cost_usd"]),
                    "source_row": row_num,
                })

    user_signals = set()
    for key, val in signals.items():
        norm = _normalize_signal(key)
        val_str = str(val).lower().strip() if val is not None else ""

        if val is True or val_str in ("true", "yes", "1", "detected"):
            user_signals.add(norm)
        elif isinstance(val, str) and val.strip():
            user_signals.add(norm)
            for trend_word in ("rising", "elevated", "dropping", "declining", "erratic", "high", "low", "detected"):
                if trend_word in val_str:
                    user_signals.add(f"{norm}_{trend_word}")
        elif isinstance(val, (int, float)):
            user_signals.add(norm)

        parts = norm.split("_")
        for i in range(1, len(parts)):
            user_signals.add("_".join(parts[:i]))

    results = []
    ref_row_start = ref_row_end = None

    for ref in ref_modes:
        row_num = ref["_row"]
        if ref_row_start is None or row_num < ref_row_start:
            ref_row_start = row_num
        if ref_row_end is None or row_num > ref_row_end:
            ref_row_end = row_num

        mode = ref["failure_mode"]
        keywords = SIGNAL_KEYWORDS.get(mode, {"primary": [], "secondary": []})

        primary_matches = set()
        secondary_matches = set()

        for sig in user_signals:
            for pk in keywords["primary"]:
                if sig in pk or pk in sig:
                    primary_matches.add(sig)
                    break
            for sk in keywords["secondary"]:
                if sig in sk or sk in sig:
                    secondary_matches.add(sig)
                    break

        if not primary_matches and not secondary_matches:
            continue

        if primary_matches and secondary_matches:
            confidence = "HIGH"
        elif primary_matches:
            confidence = "MEDIUM"
        elif len(secondary_matches) >= 2:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        score = len(primary_matches) * PRIMARY_SIGNAL_WEIGHT + len(secondary_matches) * SECONDARY_SIGNAL_WEIGHT
        past_events = [e for e in history if e["failure_mode"] == mode]

        results.append({
            "failure_mode": mode,
            "confidence": confidence,
            "score": score,
            "primary_signal_matches": sorted(primary_matches),
            "secondary_signal_matches": sorted(secondary_matches),
            "primary_sensor_signature": ref["primary_sensor_signature"],
            "secondary_indicators": ref["secondary_indicators"],
            "typical_lead_time_hrs": ref["typical_lead_time_hrs"],
            "recommended_action": ref["recommended_action"],
            "iso_10816_zone_at_detection": ref["iso_10816_zone_at_detection"],
            "past_events_this_pump": past_events or None,
            "source": {"file": "failure_mode_reference.csv", "row": ref["_row"]},
        })

    results.sort(key=lambda x: x["score"], reverse=True)

    event_log_source = None
    pump_event_rows = [e["source_row"] for e in history]
    if pump_event_rows:
        event_log_source = {
            "file": "failure_event_log.csv",
            "row_range": [min(pump_event_rows), max(pump_event_rows)],
            "total_rows_matched": len(history),
        }

    if not results:
        return {
            "status": "no_match", "pump_id": pump_id,
            "signals_provided": dict(signals),
            "message": "No failure mode matched the provided signals.",
            "sources": [{"file": "failure_mode_reference.csv", "row_range": [ref_row_start, ref_row_end]}],
        }

    output = {
        "status": "ok", "pump_id": pump_id,
        "signals_provided": dict(signals),
        "top_diagnosis": results[0]["failure_mode"],
        "top_confidence": results[0]["confidence"],
        "top_recommended_action": results[0]["recommended_action"],
        "top_lead_time_hrs": results[0]["typical_lead_time_hrs"],
        "classifications": results,
        "historical_failures_this_pump": history or None,
        "sources": [{"file": "failure_mode_reference.csv", "row_range": [ref_row_start, ref_row_end]}],
    }
    if event_log_source:
        output["sources"].append(event_log_source)

    return output
