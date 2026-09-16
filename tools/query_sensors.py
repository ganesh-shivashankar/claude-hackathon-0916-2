#!/usr/bin/env python3
"""Query sensor_timeseries.csv with filtering, aggregation, and citation metadata.

Usage:
    python tools/query_sensors.py '{"pump_id":"P-07","start":"2025-11-10","end":"2025-11-12","metrics":["bearing_temp_c","vibration_x_mms"],"aggregation":"hourly"}'

Never loads the full 60MB file — reads in chunks and filters on the fly.
"""

import csv
import json
import sys
import os
from datetime import datetime, timedelta
from collections import defaultdict

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "use-case", "data"))
SENSOR_FILE = os.path.join(DATA_DIR, "sensor_timeseries.csv")

ALL_METRICS = [
    "bearing_temp_c", "vibration_x_mms", "vibration_y_mms", "vibration_axial_mms",
    "suction_pressure_psi", "discharge_pressure_psi", "differential_pressure_psi",
    "flow_rate_m3hr", "motor_current_amps", "motor_speed_rpm"
]
BOOL_COLS = ["seal_leak_detected"]
LABEL_COL = "label"


def parse_ts(s):
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def bucket_key(ts, aggregation):
    if aggregation == "raw":
        return ts.isoformat()
    elif aggregation == "hourly":
        return ts.replace(minute=0, second=0).isoformat()
    elif aggregation == "daily":
        return ts.strftime("%Y-%m-%d")
    return ts.isoformat()


def query(pump_id, start=None, end=None, metrics=None, aggregation="raw", last_n_hours=None, include_labels=False):
    if metrics is None:
        metrics = ALL_METRICS
    metrics = [m for m in metrics if m in ALL_METRICS]
    if not metrics:
        metrics = ALL_METRICS

    now_str = "2026-02-28T23:55:00"
    now = parse_ts(now_str)

    if last_n_hours and not start:
        end_dt = now
        start_dt = now - timedelta(hours=last_n_hours)
    else:
        start_dt = parse_ts(start) if start else None
        end_dt = parse_ts(end) if end else None

    buckets = defaultdict(lambda: {m: [] for m in metrics})
    label_counts = defaultdict(int)
    row_start = None
    row_end = None
    total_rows = 0
    seal_leak_count = 0

    with open(SENSOR_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):  # row 2 = first data row (1-indexed, header is row 1)
            if row["pump_id"] != pump_id:
                continue
            ts = parse_ts(row["timestamp"])
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

            bk = bucket_key(ts, aggregation)
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
        return json.dumps({
            "status": "no_data",
            "pump_id": pump_id,
            "message": f"No sensor data found for {pump_id} in the specified range",
            "source": {"file": "sensor_timeseries.csv"}
        }, indent=2)

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
                "count": len(vals)
            }
            if len(vals) >= 2:
                first_quarter = vals[:len(vals)//4] if len(vals) >= 4 else [vals[0]]
                last_quarter = vals[-(len(vals)//4):] if len(vals) >= 4 else [vals[-1]]
                first_avg = sum(first_quarter) / len(first_quarter)
                last_avg = sum(last_quarter) / len(last_quarter)
                summary[m]["trend"] = "rising" if last_avg > first_avg + 0.5 else ("falling" if last_avg < first_avg - 0.5 else "stable")
                if len(vals) >= 12:
                    hourly_rate = (last_avg - first_avg) / (len(vals) * 5 / 60)
                    summary[m]["rate_per_hour"] = round(hourly_rate, 3)

    output = {
        "status": "ok",
        "pump_id": pump_id,
        "aggregation": aggregation,
        "time_range": {"start": sorted(buckets.keys())[0], "end": sorted(buckets.keys())[-1]},
        "total_readings": total_rows,
        "seal_leak_detected_count": seal_leak_count,
        "summary": summary,
        "data": results if len(results) <= 200 else results[:50] + [{"...": f"({len(results) - 100} rows omitted)"}] + results[-50:],
        "source": {
            "file": "sensor_timeseries.csv",
            "row_range": [row_start, row_end],
            "total_rows_matched": total_rows,
            "columns": metrics
        }
    }
    if include_labels:
        output["label_distribution"] = dict(label_counts)

    return json.dumps(output, indent=2)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: query_sensors.py '{\"pump_id\":\"P-07\",...}'"}))
        sys.exit(1)
    params = json.loads(sys.argv[1])
    print(query(**params))
