#!/usr/bin/env python3
"""Check spare parts inventory, filtering by pump_id, category, or part_number."""

import csv
import json
import os
import sys

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "use-case", "data"))


def stock_status(qty_on_hand, reorder_point):
    """Determine stock status from quantity and reorder point."""
    qty = int(float(qty_on_hand))
    reorder = int(float(reorder_point))
    if qty <= 0:
        return "out_of_stock"
    elif qty <= reorder:
        return "low_stock"
    else:
        return "in_stock"


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing JSON argument. Usage: check_spare_parts.py '{\"pump_id\": \"P-07\"}'"}))
        sys.exit(1)

    try:
        params = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}))
        sys.exit(1)

    pump_id = params.get("pump_id")
    category = params.get("category")
    part_number = params.get("part_number")

    if not pump_id and not category and not part_number:
        print(json.dumps({"error": "At least one filter is required: pump_id, category, or part_number"}))
        sys.exit(1)

    csv_file = os.path.join(DATA_DIR, "spare_parts_inventory.csv")
    if not os.path.isfile(csv_file):
        print(json.dumps({"error": f"Data file not found: {csv_file}"}))
        sys.exit(1)

    matches = []
    row_indices = []

    with open(csv_file, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader, start=2):
            # Apply filters (all supplied filters must match)
            if pump_id:
                compatible = [p.strip() for p in row["compatible_pumps"].split(";")]
                if pump_id not in compatible:
                    continue

            if category and row["category"] != category:
                continue

            if part_number and row["part_number"] != part_number:
                continue

            entry = dict(row)
            entry["stock_status"] = stock_status(row["qty_on_hand"], row["reorder_point"])
            matches.append(entry)
            row_indices.append(i)

    if row_indices:
        row_range = f"{min(row_indices)}-{max(row_indices)}"
    else:
        row_range = "none"

    result = {
        "total_count": len(matches),
        "filters_applied": {
            "pump_id": pump_id,
            "category": category,
            "part_number": part_number,
        },
        "parts": matches,
        "source": {
            "file": "spare_parts_inventory.csv",
            "row_range": row_range,
            "columns": ["part_number", "description", "category", "unit_cost_usd",
                         "qty_on_hand", "reorder_point", "lead_time_days", "compatible_pumps"],
        },
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
