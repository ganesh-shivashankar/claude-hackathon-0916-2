#!/usr/bin/env python3
"""End-to-end validation: test all tools against the 8 known failure events."""

import subprocess
import json
import sys

FAILURES = [
    {"event": "EVT-001", "pump": "P-01", "mode": "bearing_wear", "date": "2025-09-26", "start": "2025-09-25"},
    {"event": "EVT-002", "pump": "P-03", "mode": "cavitation", "date": "2025-10-19", "start": "2025-10-18"},
    {"event": "EVT-003", "pump": "P-07", "mode": "bearing_wear", "date": "2025-11-12", "start": "2025-11-11"},
    {"event": "EVT-004", "pump": "P-05", "mode": "seal_failure", "date": "2025-12-05", "start": "2025-12-04"},
    {"event": "EVT-005", "pump": "P-10", "mode": "misalignment", "date": "2025-12-28", "start": "2025-12-25"},
    {"event": "EVT-006", "pump": "P-02", "mode": "impeller_damage", "date": "2026-01-19", "start": "2026-01-17"},
    {"event": "EVT-007", "pump": "P-08", "mode": "bearing_wear", "date": "2026-02-10", "start": "2026-02-09"},
    {"event": "EVT-008", "pump": "P-11", "mode": "seal_failure", "date": "2026-02-23", "start": "2026-02-22"},
]

SIGNAL_MAP = {
    "bearing_wear": {"bearing_temp_rising": True, "vibration_elevated": True, "motor_current_rising": True},
    "seal_failure": {"seal_leak_detected": True, "suction_pressure_dropping": True, "flow_declining": True},
    "cavitation": {"suction_pressure_low": True, "vibration_axial_elevated": True, "flow_erratic": True},
    "impeller_damage": {"differential_pressure_declining": True, "flow_declining": True, "motor_current_dropping": True},
    "misalignment": {"vibration_axial_high": True, "bearing_temp_elevated": True, "motor_current_elevated": True},
}


def run_tool(script, params):
    try:
        result = subprocess.run(
            ["python3", f"tools/{script}", json.dumps(params)],
            capture_output=True, text=True, timeout=120
        )
        return json.loads(result.stdout)
    except Exception as e:
        return {"error": str(e)}


def test_failure(f):
    pump = f["pump"]
    mode = f["mode"]
    event = f["event"]
    print(f"\n{'='*60}")
    print(f"Testing {event}: {pump} - {mode} (failure: {f['date']})")
    print(f"{'='*60}")

    # 1. Query sensors in pre-failure window
    sensor_data = run_tool("query_sensors.py", {
        "pump_id": pump,
        "start": f["start"],
        "end": f["date"],
        "metrics": ["bearing_temp_c", "vibration_x_mms", "vibration_axial_mms", "suction_pressure_psi", "differential_pressure_psi", "flow_rate_m3hr"],
        "aggregation": "daily",
        "include_labels": True
    })
    labels = sensor_data.get("label_distribution", {})
    has_prefailure = labels.get("pre_failure", 0) > 0
    print(f"  [{'PASS' if has_prefailure else 'WARN'}] Sensor labels: {labels}")
    print(f"       Source: sensor_timeseries.csv rows {sensor_data.get('source', {}).get('row_range', '?')}")

    # 2. Classify failure mode
    signals = SIGNAL_MAP.get(mode, {})
    classification = run_tool("classify_failure_mode.py", {"pump_id": pump, "signals": signals})
    top = classification.get("top_diagnosis", "none")
    conf = classification.get("top_confidence", "none")
    correct = top == mode
    print(f"  [{'PASS' if correct else 'FAIL'}] Classification: {top} ({conf}) — expected {mode}")

    # 3. Get pump profile
    profile = run_tool("get_pump_profile.py", {"pump_id": pump})
    model = profile.get("model", "unknown")
    print(f"  [INFO] Pump model: {model}, Manual: {profile.get('oem_manual', '?')}")

    # 4. Check vibration zone
    vib = run_tool("check_vibration_zone.py", {"pump_id": pump, "timestamp": f"{f['start']}T12:00:00"})
    zone = vib.get("overall_zone", "?")
    print(f"  [INFO] Vibration zone at {f['start']}: {zone}")

    # 5. Search alarms
    alarms = run_tool("search_alarms.py", {
        "pump_id": pump,
        "start": f["start"],
        "end": f["date"]
    })
    alarm_count = alarms.get("total_count", 0)
    print(f"  [INFO] Alarms in window: {alarm_count}")

    return {"event": event, "pump": pump, "mode": mode, "classification_correct": correct,
            "has_prefailure_label": has_prefailure, "zone": zone, "alarms": alarm_count}


if __name__ == "__main__":
    results = []
    for f in FAILURES:
        r = test_failure(f)
        results.append(r)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    correct = sum(1 for r in results if r["classification_correct"])
    prefailure = sum(1 for r in results if r["has_prefailure_label"])
    print(f"Classification accuracy: {correct}/{len(results)}")
    print(f"Pre-failure labels found: {prefailure}/{len(results)}")
    for r in results:
        status = "PASS" if r["classification_correct"] else "FAIL"
        print(f"  [{status}] {r['event']} {r['pump']}: classified={r.get('mode','?')}, zone={r['zone']}, alarms={r['alarms']}")
