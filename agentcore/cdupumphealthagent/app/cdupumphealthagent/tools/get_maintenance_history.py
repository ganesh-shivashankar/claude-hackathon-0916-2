"""Retrieve merged maintenance history from two independent sources for a given pump."""

import csv
import json
from typing import Optional

from strands import tool

from config import DATA_DIR

JSON_FILE = DATA_DIR / "pump_maintenance_history.json"
CSV_FILE = DATA_DIR / "maintenance_work_orders.csv"


@tool
def get_maintenance_history(pump_id: str) -> dict:
    """Retrieve and merge maintenance records from pump_maintenance_history.json and maintenance_work_orders.csv for a specific pump.

    Records are merged from both sources and sorted chronologically by date.

    Parameters:
        pump_id: Pump ID to retrieve maintenance history for (e.g. P-01 through P-12)
    """
    # --- Source 1: pump_maintenance_history.json ---
    json_records = []
    if JSON_FILE.is_file():
        with open(JSON_FILE, encoding="utf-8") as fh:
            all_json = json.load(fh)
        for idx, rec in enumerate(all_json):
            if rec.get("pump_id") == pump_id:
                entry = dict(rec)
                entry["source_file"] = "pump_maintenance_history.json"
                entry["source_index"] = idx  # 0-based index in the JSON array
                json_records.append(entry)

    # --- Source 2: maintenance_work_orders.csv ---
    csv_records = []
    csv_row_indices = []
    if CSV_FILE.is_file():
        with open(CSV_FILE, newline="", encoding="utf-8") as fh:
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
            "columns": [
                "pump_id", "work_order_id", "date", "work_type",
                "technician_notes", "parts_replaced", "lubricant_type",
                "hours_since_last_service",
            ],
        })

    if csv_records:
        sources.append({
            "file": "maintenance_work_orders.csv",
            "records_matched": len(csv_records),
            "row_range": f"{min(csv_row_indices)}-{max(csv_row_indices)}",
            "columns": [
                "work_order_id", "pump_id", "date", "wo_type", "status",
                "description", "cost_usd", "labor_hours", "shift",
            ],
        })

    return {
        "pump_id": pump_id,
        "total_records": len(merged),
        "records": merged,
        "sources": sources,
    }
