"""Get operating status and summary statistics for a pump over a date range."""

import csv
from typing import Optional

from strands import tool

from config import DATA_DIR

SCHEDULE_FILE = DATA_DIR / "operating_schedule.csv"


@tool
def get_operating_status(
    pump_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> dict:
    """Query operating_schedule.csv for a pump's operational status over a date range.

    Returns daily status entries plus summary statistics including days running,
    standby, maintenance, average load percentage, and cumulative run hours.

    Parameters:
        pump_id: Pump ID to query (e.g. P-01 through P-12)
        start: Start date filter in YYYY-MM-DD format (inclusive)
        end: End date filter in YYYY-MM-DD format (inclusive)
    """
    if not SCHEDULE_FILE.is_file():
        return {"error": f"Data file not found: {SCHEDULE_FILE}"}

    matches = []
    row_indices = []

    with open(SCHEDULE_FILE, newline="", encoding="utf-8") as fh:
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

    return {
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
            "columns": [
                "pump_id", "date", "status", "load_pct",
                "assigned_process", "run_hours_cumulative",
            ],
        },
    }
