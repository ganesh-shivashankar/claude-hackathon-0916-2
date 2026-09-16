"""Search alarm history for a given pump, with optional time range and alarm type filters."""

import csv
from typing import Optional

from strands import tool

from config import DATA_DIR

ALARM_FILE = DATA_DIR / "alarm_history.csv"


@tool
def search_alarms(
    pump_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    alarm_type: Optional[str] = None,
) -> dict:
    """Search alarm_history.csv for alarms on a specific pump with optional date and type filters.

    Parameters:
        pump_id: Pump ID to search alarms for (e.g. P-01 through P-12)
        start: Start date filter in YYYY-MM-DD format (inclusive)
        end: End date filter in YYYY-MM-DD format (inclusive)
        alarm_type: Filter by alarm type (e.g. high_vibration, high_bearing_temp)
    """
    if not ALARM_FILE.is_file():
        return {"error": f"Data file not found: {ALARM_FILE}"}

    matches = []
    row_indices = []  # 1-based row numbers (header = row 1)

    with open(ALARM_FILE, newline="", encoding="utf-8") as fh:
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

    return {
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
            "columns": [
                "alarm_id", "pump_id", "timestamp", "alarm_type", "severity",
                "trigger_value", "duration_minutes", "acknowledged",
            ],
        },
    }
