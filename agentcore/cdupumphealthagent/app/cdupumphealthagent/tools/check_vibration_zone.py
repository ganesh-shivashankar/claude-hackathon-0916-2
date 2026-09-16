"""Classify current vibration readings into ISO 10816 zones per axis."""

import csv
from datetime import datetime, timedelta
from typing import Optional

from strands import tool

from config import DATA_DIR, SIMULATED_NOW, ZONE_AB_MULTIPLIER, DEFAULT_LOOKBACK_HOURS, TIMESTAMP_WINDOW_HOURS

BASELINES_FILE = DATA_DIR / "vibration_baselines.csv"
SENSOR_FILE = DATA_DIR / "sensor_timeseries.csv"

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


def _parse_ts(s):
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _classify_zone(value, baseline, alert, alarm, trip):
    if value <= alert:
        return "A" if value <= baseline * ZONE_AB_MULTIPLIER else "B"
    elif value <= alarm:
        return "C"
    else:
        return "D"


def _get_recent_vibration(pump_id, target_ts=None):
    if target_ts:
        target = _parse_ts(target_ts)
        window_start = target - timedelta(hours=TIMESTAMP_WINDOW_HOURS)
        window_end = target + timedelta(hours=TIMESTAMP_WINDOW_HOURS)
    else:
        target = _parse_ts(SIMULATED_NOW)
        window_start = target - timedelta(hours=DEFAULT_LOOKBACK_HOURS)
        window_end = target

    readings = []
    row_start = row_end = None

    with open(SENSOR_FILE) as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            if row["pump_id"] != pump_id:
                continue
            ts = _parse_ts(row["timestamp"])
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
        k: round(sum(r[k] for r in readings) / len(readings), 3)
        for k in ["vibration_x_mms", "vibration_y_mms", "vibration_axial_mms", "bearing_temp_c"]
    }
    return latest, avg, {"row_range": [row_start, row_end], "count": len(readings)}


@tool
def check_vibration_zone(pump_id: str, timestamp: Optional[str] = None) -> dict:
    """Classify current vibration into ISO 10816 zones (A/B/C/D) per axis for a pump.

    Compares against per-pump baselines from vibration_baselines.csv.

    Parameters:
        pump_id: Pump ID (P-01 through P-12)
        timestamp: Optional — check at a specific time instead of latest
    """
    baselines = []
    baseline_rows = []
    with open(BASELINES_FILE) as f:
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
        return {
            "status": "no_baselines", "pump_id": pump_id,
            "message": f"No vibration baselines found for {pump_id}",
            "source": {"file": "vibration_baselines.csv"},
        }

    latest, avg, sensor_source = _get_recent_vibration(pump_id, timestamp)
    if latest is None:
        return {
            "status": "no_sensor_data", "pump_id": pump_id,
            "baselines": baselines,
            "message": f"No recent sensor data found for {pump_id}",
            "source": {"file": "vibration_baselines.csv", "rows": baseline_rows},
        }

    assessments = []
    worst_zone = "A"
    for bl in baselines:
        sensor_col = bl["sensor_column"]
        current_val = latest.get(sensor_col, 0)
        avg_val = avg.get(sensor_col, 0)
        zone = _classify_zone(avg_val, bl["baseline_mms"], bl["alert_threshold_mms"],
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

    return {
        "status": "ok", "pump_id": pump_id,
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
        },
    }
