"""Query sensor_timeseries.csv with filtering, aggregation, and citation metadata."""

import csv
import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from strands import tool

from config import (
    DATA_DIR, SIMULATED_NOW, SENSOR_INTERVAL_MINUTES,
    TREND_THRESHOLD, MIN_READINGS_FOR_RATE,
    RAW_DATA_DISPLAY_LIMIT, RAW_DATA_HEAD, RAW_DATA_TAIL,
)

SENSOR_FILE = DATA_DIR / "sensor_timeseries.csv"

ALL_METRICS = [
    "bearing_temp_c", "vibration_x_mms", "vibration_y_mms", "vibration_axial_mms",
    "suction_pressure_psi", "discharge_pressure_psi", "differential_pressure_psi",
    "flow_rate_m3hr", "motor_current_amps", "motor_speed_rpm",
]
LABEL_COL = "label"


def _parse_ts(s):
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _bucket_key(ts, aggregation):
    if aggregation == "hourly":
        return ts.replace(minute=0, second=0).isoformat()
    elif aggregation == "daily":
        return ts.strftime("%Y-%m-%d")
    return ts.isoformat()


@tool
def query_sensors(
    pump_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    metrics: Optional[list[str]] = None,
    aggregation: str = "raw",
    last_n_hours: Optional[int] = None,
    include_labels: bool = False,
) -> dict:
    """Query sensor_timeseries.csv for a specific pump. Returns time series data with aggregation and trend analysis.

    ALWAYS specify pump_id and a time range (start/end or last_n_hours).
    Use aggregation='hourly' or 'daily' for ranges over 24 hours.

    Parameters:
        pump_id: Pump ID (P-01 through P-12)
        start: Start datetime (YYYY-MM-DD or ISO format)
        end: End datetime
        metrics: Sensor columns to include (bearing_temp_c, vibration_x_mms, etc.)
        aggregation: Aggregation level — raw, hourly, or daily
        last_n_hours: Alternative to start/end: query last N hours
        include_labels: Include label distribution (normal/pre_failure/failure)
    """
    if metrics is None:
        metrics = ALL_METRICS
    metrics = [m for m in metrics if m in ALL_METRICS] or ALL_METRICS

    now = _parse_ts(SIMULATED_NOW)

    if last_n_hours and not start:
        end_dt = now
        start_dt = now - timedelta(hours=last_n_hours)
    else:
        start_dt = _parse_ts(start) if start else None
        end_dt = _parse_ts(end) if end else None

    buckets = defaultdict(lambda: {m: [] for m in metrics})
    label_counts = defaultdict(int)
    row_start = row_end = None
    total_rows = 0
    seal_leak_count = 0

    with open(SENSOR_FILE) as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            if row["pump_id"] != pump_id:
                continue
            ts = _parse_ts(row["timestamp"])
            if ts is None:
                continue
            if start_dt and ts < start_dt:
                continue
            if end_dt and ts > end_dt:
                continue

            if row_start is None:
                row_start = row_num
            row_end = row_num
            total_rows += 1

            bk = _bucket_key(ts, aggregation)
            for m in metrics:
                try:
                    buckets[bk][m].append(float(row[m]))
                except (ValueError, KeyError):
                    pass

            if row.get("seal_leak_detected", "").strip().lower() == "true":
                seal_leak_count += 1

            if include_labels and LABEL_COL in row:
                label_counts[row[LABEL_COL]] += 1

    if not buckets:
        return {
            "status": "no_data", "pump_id": pump_id,
            "message": f"No sensor data found for {pump_id} in the specified range",
            "source": {"file": "sensor_timeseries.csv"},
        }

    results = []
    for bk in sorted(buckets.keys()):
        entry = {"timestamp": bk}
        for m in metrics:
            vals = buckets[bk][m]
            if not vals:
                continue
            if aggregation == "raw" and len(vals) == 1:
                entry[m] = round(vals[0], 3)
            else:
                entry[m + "_mean"] = round(sum(vals) / len(vals), 3)
                entry[m + "_min"] = round(min(vals), 3)
                entry[m + "_max"] = round(max(vals), 3)
        results.append(entry)

    summary = {}
    all_vals = defaultdict(list)
    for bk in buckets:
        for m in metrics:
            all_vals[m].extend(buckets[bk][m])
    for m in metrics:
        vals = all_vals[m]
        if vals:
            summary[m] = {
                "mean": round(sum(vals) / len(vals), 3),
                "min": round(min(vals), 3),
                "max": round(max(vals), 3),
                "latest": round(vals[-1], 3),
                "count": len(vals),
            }
            if len(vals) >= 2:
                q = max(len(vals) // 4, 1)
                first_avg = sum(vals[:q]) / q
                last_avg = sum(vals[-q:]) / q
                summary[m]["trend"] = (
                    "rising" if last_avg > first_avg + TREND_THRESHOLD
                    else ("falling" if last_avg < first_avg - TREND_THRESHOLD else "stable")
                )
                if len(vals) >= MIN_READINGS_FOR_RATE:
                    hourly_rate = (last_avg - first_avg) / (len(vals) * SENSOR_INTERVAL_MINUTES / 60)
                    summary[m]["rate_per_hour"] = round(hourly_rate, 3)

    display_data = (
        results if len(results) <= RAW_DATA_DISPLAY_LIMIT
        else results[:RAW_DATA_HEAD] + [{"...": f"({len(results) - RAW_DATA_HEAD - RAW_DATA_TAIL} rows omitted)"}] + results[-RAW_DATA_TAIL:]
    )

    output = {
        "status": "ok", "pump_id": pump_id, "aggregation": aggregation,
        "time_range": {"start": sorted(buckets.keys())[0], "end": sorted(buckets.keys())[-1]},
        "total_readings": total_rows,
        "seal_leak_detected_count": seal_leak_count,
        "summary": summary,
        "data": display_data,
        "source": {
            "file": "sensor_timeseries.csv",
            "row_range": [row_start, row_end],
            "total_rows_matched": total_rows,
            "columns": metrics,
        },
    }
    if include_labels:
        output["label_distribution"] = dict(label_counts)

    return output
