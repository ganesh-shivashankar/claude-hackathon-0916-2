#!/usr/bin/env python3
"""Classify current vibration readings into ISO 10816 zones per axis.

Compares sensor readings against per-pump per-axis baselines from vibration_baselines.csv.
Also reads recent sensor data to get current vibration values.

Usage:
    python tools/check_vibration_zone.py '{"pump_id":"P-07"}'
    python tools/check_vibration_zone.py '{"pump_id":"P-07","timestamp":"2025-11-11T12:00:00"}'
"""

import csv
import json
import sys
import os
from datetime import datetime, timedelta

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "use-case", "data"))
BASELINES_FILE = os.path.join(DATA_DIR, "vibration_baselines.csv")
SENSOR_FILE = os.path.join(DATA_DIR, "sensor_timeseries.csv")

ISO_ZONES = {
    "A": {"label": "Good — new/overhauled condition", "action": "Normal operation"},
    "B": {"label": "Acceptable for long-term operation", "action": "Monitor"},
    "C": {"label": "Unsatisfactory — investigate", "action": "Plan maintenance within 2 weeks"},
    "D": {"label": "Dangerous — damage likely", "action": "Shut down immediately"},
}

AXIS_MAP = {
    "Drive End Horizontal": "vibration_x_mms",
    "Drive End Vertical": "vibration_y_mms",
    "Drive End Axial": "vibration_axial_mms",
    "Non-Drive End Horizontal": "vibration_x_mms",
    "Non-Drive End Vertical": "vibration_y_mms",
    "Non-Drive End Axial": "vibration_axial_mms",
}


def parse_ts(s):
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def classify_zone(value, baseline, alert, alarm, trip):
    if value <= alert:
        return "A" if value <= baseline * 1.2 else "B"
    elif value <= alarm:
        return "C"
    else:
        return "D"


def get_recent_vibration(pump_id, target_ts=None):
    if target_ts:
        target = parse_ts(target_ts)
        window_start = target - timedelta(hours=1)
        window_end = target + timedelta(hours=1)
    else:
        target = parse_ts("2026-02-28T23:55:00")
        window_start = target - timedelta(hours=4)
        window_end = target

    readings = []
    row_start = None
    row_end = None

    with open(SENSOR_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            if row["pump_id"] != pump_id:
                continue
            ts = parse_ts(row["timestamp"])
            if ts is None or ts < window_start or ts > window_end:
                continue
            if row_start is None:
                row_start = row_num
            row_end = row_num
            readings.append({
                "timestamp": row["timestamp"],
                "vibration_x_mms": float(row["vibration_x_mms"]),
                "vibration_y_mms": float(row["vibration_y_mms"]),
                "vibration_axial_mms": float(row["vibration_axial_mms"]),
                "bearing_temp_c": float(row["bearing_temp_c"]),
            })

    if not readings:
        return None, None, None

    latest = readings[-1]
    avg = {
        "vibration_x_mms": round(sum(r["vibration_x_mms"] for r in readings) / len(readings), 3),
        "vibration_y_mms": round(sum(r["vibration_y_mms"] for r in readings) / len(readings), 3),
        "vibration_axial_mms": round(sum(r["vibration_axial_mms"] for r in readings) / len(readings), 3),
        "bearing_temp_c": round(sum(r["bearing_temp_c"] for r in readings) / len(readings), 3),
    }
    return latest, avg, {"row_range": [row_start, row_end], "count": len(readings)}


def check_zones(pump_id, timestamp=None):
    baselines = []
    baseline_rows = []
    with open(BASELINES_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            if row["pump_id"] != pump_id:
                continue
            baselines.append({
                "measurement_point": row["measurement_point"],
                "baseline_mms": float(row["baseline_mms"]),
                "alert_threshold_mms": float(row["alert_threshold_mms"]),
                "alarm_threshold_mms": float(row["alarm_threshold_mms"]),
                "trip_threshold_mms": float(row["trip_threshold_mms"]),
                "sensor_column": AXIS_MAP.get(row["measurement_point"], "unknown"),
                "row": row_num,
            })
            baseline_rows.append(row_num)

    if not baselines:
        return json.dumps({
            "status": "no_baselines",
            "pump_id": pump_id,
            "message": f"No vibration baselines found for {pump_id}",
            "source": {"file": "vibration_baselines.csv"}
        }, indent=2)

    latest, avg, sensor_source = get_recent_vibration(pump_id, timestamp)
    if latest is None:
        return json.dumps({
            "status": "no_sensor_data",
            "pump_id": pump_id,
            "baselines": baselines,
            "message": f"No recent sensor data found for {pump_id}",
            "source": {"file": "vibration_baselines.csv", "rows": baseline_rows}
        }, indent=2)

    assessments = []
    worst_zone = "A"
    for bl in baselines:
        sensor_col = bl["sensor_column"]
        current_val = latest.get(sensor_col, 0)
        avg_val = avg.get(sensor_col, 0)
        zone = classify_zone(avg_val, bl["baseline_mms"], bl["alert_threshold_mms"],
                             bl["alarm_threshold_mms"], bl["trip_threshold_mms"])
        if zone > worst_zone:
            worst_zone = zone

        assessments.append({
            "measurement_point": bl["measurement_point"],
            "sensor_column": sensor_col,
            "current_value_mms": round(current_val, 3),
            "avg_value_mms": round(avg_val, 3),
            "baseline_mms": bl["baseline_mms"],
            "alert_threshold_mms": bl["alert_threshold_mms"],
            "alarm_threshold_mms": bl["alarm_threshold_mms"],
            "trip_threshold_mms": bl["trip_threshold_mms"],
            "iso_10816_zone": zone,
            "zone_description": ISO_ZONES[zone]["label"],
            "recommended_action": ISO_ZONES[zone]["action"],
            "baseline_row": bl["row"],
        })

    return json.dumps({
        "status": "ok",
        "pump_id": pump_id,
        "overall_zone": worst_zone,
        "overall_status": ISO_ZONES[worst_zone]["label"],
        "overall_action": ISO_ZONES[worst_zone]["action"],
        "bearing_temp_c": latest.get("bearing_temp_c"),
        "assessments": assessments,
        "source": {
            "baselines_file": "vibration_baselines.csv",
            "baselines_rows": baseline_rows,
            "sensor_file": "sensor_timeseries.csv",
            "sensor_rows": sensor_source["row_range"] if sensor_source else None,
            "sensor_readings_used": sensor_source["count"] if sensor_source else 0,
        }
    }, indent=2)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: check_vibration_zone.py '{\"pump_id\":\"P-07\"}'"}))
        sys.exit(1)
    params = json.loads(sys.argv[1])
    print(check_zones(**params))
