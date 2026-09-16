#!/usr/bin/env python3
"""Retrieve merged maintenance history from two independent sources for a given pump."""

import csv
import json
import os
import sys

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "use-case", "data"))


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing JSON argument. Usage: get_maintenance_history.py '{\"pump_id\": \"P-07\"}'"}))
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

    # --- Source 1: pump_maintenance_history.json ---
    json_file = os.path.join(DATA_DIR, "pump_maintenance_history.json")
    json_records = []
    if os.path.isfile(json_file):
        with open(json_file, encoding="utf-8") as fh:
            all_json = json.load(fh)
        for idx, rec in enumerate(all_json):
            if rec.get("pump_id") == pump_id:
                entry = dict(rec)
                entry["source_file"] = "pump_maintenance_history.json"
                entry["source_index"] = idx  # 0-based index in the JSON array
                json_records.append(entry)

    # --- Source 2: maintenance_work_orders.csv ---
    csv_file = os.path.join(DATA_DIR, "maintenance_work_orders.csv")
    csv_records = []
    csv_row_indices = []
    if os.path.isfile(csv_file):
        with open(csv_file, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for i, row in enumerate(reader, start=2):
                if row["pump_id"] == pump_id:
                    entry = dict(row)
                    entry["source_file"] = "maintenance_work_orders.csv"
                    csv_records.append(entry)
                    csv_row_indices.append(i)

    # --- Merge and sort by date ---
    merged = json_records + csv_records
    merged.sort(key=lambda r: r.get("date", ""))

    # Build source citations
    sources = []

    if json_records:
        indices = [r.pop("source_index") for r in json_records]
        sources.append({
            "file": "pump_maintenance_history.json",
            "records_matched": len(json_records),
            "index_range": f"{min(indices)}-{max(indices)}",
            "columns": ["pump_id", "work_order_id", "date", "work_type",
                         "technician_notes", "parts_replaced", "lubricant_type",
                         "hours_since_last_service"],
        })

    if csv_records:
        sources.append({
            "file": "maintenance_work_orders.csv",
            "records_matched": len(csv_records),
            "row_range": f"{min(csv_row_indices)}-{max(csv_row_indices)}",
            "columns": ["work_order_id", "pump_id", "date", "wo_type", "status",
                         "description", "cost_usd", "labor_hours", "shift"],
        })

    result = {
        "pump_id": pump_id,
        "total_records": len(merged),
        "records": merged,
        "sources": sources,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
