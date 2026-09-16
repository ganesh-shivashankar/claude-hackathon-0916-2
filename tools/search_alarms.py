#!/usr/bin/env python3
"""Search alarm history for a given pump, with optional time range and alarm type filters."""

import csv
import json
import os
import sys

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "use-case", "data"))


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing JSON argument. Usage: search_alarms.py '{\"pump_id\": \"P-03\"}'"}))
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

    start = params.get("start")  # e.g. "2025-10-01"
    end = params.get("end")      # e.g. "2025-10-20"
    alarm_type = params.get("alarm_type")

    csv_file = os.path.join(DATA_DIR, "alarm_history.csv")
    if not os.path.isfile(csv_file):
        print(json.dumps({"error": f"Data file not found: {csv_file}"}))
        sys.exit(1)

    matches = []
    row_indices = []  # 1-based row numbers (header = row 1)

    with open(csv_file, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader, start=2):  # data rows start at 2 (header is 1)
            if row["pump_id"] != pump_id:
                continue

            ts = row["timestamp"]
            date_part = ts[:10]  # "YYYY-MM-DD"

            if start and date_part < start:
                continue
            if end and date_part > end:
                continue
            if alarm_type and row["alarm_type"] != alarm_type:
                continue

            matches.append(row)
            row_indices.append(i)

    # Sort by timestamp ascending
    paired = list(zip(matches, row_indices))
    paired.sort(key=lambda x: x[0]["timestamp"])
    matches = [p[0] for p in paired]
    row_indices = [p[1] for p in paired]

    # Determine row range for citation
    if row_indices:
        min_row = min(row_indices)
        max_row = max(row_indices)
        row_range = f"{min_row}-{max_row}"
    else:
        row_range = "none"

    result = {
        "total_count": len(matches),
        "filters_applied": {
            "pump_id": pump_id,
            "start": start,
            "end": end,
            "alarm_type": alarm_type,
        },
        "alarms": matches,
        "source": {
            "file": "alarm_history.csv",
            "row_range": row_range,
            "columns": ["alarm_id", "pump_id", "timestamp", "alarm_type", "severity",
                         "trigger_value", "duration_minutes", "acknowledged"],
        },
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
