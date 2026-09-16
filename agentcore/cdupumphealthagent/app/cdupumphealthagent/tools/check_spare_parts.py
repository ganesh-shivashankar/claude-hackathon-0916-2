"""Check spare parts inventory, filtering by pump_id, category, or part_number."""

import csv
from typing import Optional

from strands import tool

from config import DATA_DIR

SPARE_PARTS_FILE = DATA_DIR / "spare_parts_inventory.csv"


def _stock_status(qty_on_hand: str, reorder_point: str) -> str:
    """Determine stock status from quantity and reorder point."""
    qty = int(float(qty_on_hand))
    reorder = int(float(reorder_point))
    if qty <= 0:
        return "out_of_stock"
    elif qty <= reorder:
        return "low_stock"
    else:
        return "in_stock"


@tool
def check_spare_parts(
    pump_id: Optional[str] = None,
    category: Optional[str] = None,
    part_number: Optional[str] = None,
) -> dict:
    """Check spare_parts_inventory.csv for available parts. At least one filter must be provided.

    Filters are combined with AND logic: all supplied filters must match.
    Each returned part includes a computed stock_status (in_stock, low_stock, or out_of_stock).

    Parameters:
        pump_id: Filter by compatible pump ID (e.g. P-01 through P-12)
        category: Filter by part category (e.g. bearing, seal, impeller)
        part_number: Filter by specific part number
    """
    if not pump_id and not category and not part_number:
        return {"error": "At least one filter is required: pump_id, category, or part_number"}

    if not SPARE_PARTS_FILE.is_file():
        return {"error": f"Data file not found: {SPARE_PARTS_FILE}"}

    matches = []
    row_indices = []

    with open(SPARE_PARTS_FILE, newline="", encoding="utf-8") as fh:
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
            entry["stock_status"] = _stock_status(row["qty_on_hand"], row["reorder_point"])
            matches.append(entry)
            row_indices.append(i)

    if row_indices:
        row_range = f"{min(row_indices)}-{max(row_indices)}"
    else:
        row_range = "none"

    return {
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
            "columns": [
                "part_number", "description", "category", "unit_cost_usd",
                "qty_on_hand", "reorder_point", "lead_time_days", "compatible_pumps",
            ],
        },
    }
