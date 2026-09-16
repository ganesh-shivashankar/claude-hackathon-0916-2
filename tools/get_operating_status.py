#!/usr/bin/env python3
"""Get operating status and summary statistics for a pump over a date range."""

import csv
import json
import os
import sys

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "use-case", "data"))


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing JSON argument. Usage: get_operating_status.py '{\"pump_id\": \"P-07\", \"start\": \"2025-11-01\", \"end\": \"2025-11-15\"}'" }))
        sys.exit(1)

    try:
        params = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}))
        sys.exit(1)

    pump_id = params.get("pump_id")
    if not pump_id:
        print(json.dumps({"error": "pump_id is required"}))
        sys.exit(1)

    start = params.get("start")
    end = params.get("end")

    csv_file = os.path.join(DATA_DIR, "operating_schedule.csv")
    if not os.path.isfile(csv_file):
        print(json.dumps({"error": f"Data file not found: {csv_file}"}))
        sys.exit(1)

    matches = []
    row_indices = []

    with open(csv_file, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader, start=2):
            if row["pump_id"] != pump_id:
                continue

            date_val = row["date"]
            if start and date_val < start:
                continue
            if end and date_val > end:
                continue

            matches.append(row)
            row_indices.append(i)

    # Sort by date
    paired = list(zip(matches, row_indices))
    paired.sort(key=lambda x: x[0]["date"])
    matches = [p[0] for p in paired]
    row_indices = [p[1] for p in paired]

    # Compute summary statistics
    days_running = 0
    days_standby = 0
    days_maintenance = 0
    load_values = []

    for row in matches:
        status = row["status"]
        if status == "Running":
            days_running += 1
        elif status == "Standby":
            days_standby += 1
        elif status in ("Maintenance", "Under Maintenance"):
            days_maintenance += 1

        try:
            load = float(row["load_pct"])
            load_values.append(load)
        except (ValueError, TypeError):
            pass

    avg_load_pct = round(sum(load_values) / len(load_values), 1) if load_values else 0.0

    # Total run hours = sum of all run_hours_cumulative values in the period
    total_run_hours = 0.0
    for row in matches:
        try:
            total_run_hours += float(row["run_hours_cumulative"])
        except (ValueError, TypeError):
            pass
    total_run_hours = round(total_run_hours, 1)

    if row_indices:
        row_range = f"{min(row_indices)}-{max(row_indices)}"
    else:
        row_range = "none"

    result = {
        "pump_id": pump_id,
        "date_range": {"start": start, "end": end},
        "total_rows": len(matches),
        "summary": {
            "days_running": days_running,
            "days_standby": days_standby,
            "days_maintenance": days_maintenance,
            "avg_load_pct": avg_load_pct,
            "total_run_hours": total_run_hours,
        },
        "rows": matches,
        "source": {
            "file": "operating_schedule.csv",
            "row_range": row_range,
            "columns": ["pump_id", "date", "status", "load_pct",
                         "assigned_process", "run_hours_cumulative"],
        },
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
