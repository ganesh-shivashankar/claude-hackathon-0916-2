"""Get pump metadata, operating envelope, bearing temp limits, and OEM manual reference."""

import csv
from typing import Optional

from strands import tool

from config import (
    DATA_DIR, PUMP_METADATA, ALL_PUMP_IDS,
    pump_manual, pump_bearing_limits, MANUAL_MAP,
)

METADATA_FILE = DATA_DIR / "pump_metadata.csv"


@tool
def get_pump_profile(pump_id: str) -> dict:
    """Get pump metadata: model, manufacturer, operating envelope, bearing temp limits, OEM manual reference.

    Use pump_id='all' for fleet-wide overview of all 12 pumps.

    Parameters:
        pump_id: Pump ID (P-01 through P-12) or 'all' for entire fleet
    """
    if pump_id == "all":
        pumps = []
        for pid in ALL_PUMP_IDS:
            pumps.append(_build_profile(pid))
        row_nums = [p.pop("_source_row") for p in pumps]
        return {
            "status": "ok",
            "pumps": pumps,
            "source": {"file": "pump_metadata.csv", "row_range": [min(row_nums), max(row_nums)]},
        }

    if pump_id not in PUMP_METADATA:
        return {"status": "not_found", "pump_id": pump_id, "message": f"No metadata found for {pump_id}"}

    profile = _build_profile(pump_id)
    row = profile.pop("_source_row")
    return {**profile, "source": {"file": "pump_metadata.csv", "row": row}}


def _build_profile(pump_id: str) -> dict:
    meta = PUMP_METADATA[pump_id]
    design_flow = float(meta["design_flow_m3hr"])
    design_head = float(meta["design_head_m"])
    rated_power = float(meta["rated_power_kw"])

    return {
        "status": "ok",
        "pump_id": pump_id,
        "model": meta["model"],
        "manufacturer": meta["manufacturer"],
        "install_date": meta["install_date"],
        "service_fluid": meta["service_fluid"],
        "design_flow_m3hr": design_flow,
        "design_head_m": design_head,
        "rated_power_kw": rated_power,
        "criticality_rating": int(meta["criticality_rating"]),
        "bearing_type": meta["bearing_type"],
        "seal_type": meta["seal_type"],
        "last_maintenance_date": meta["last_maintenance_date"],
        "operating_envelope": {
            "min_flow_m3hr": design_flow * 0.6,
            "max_flow_m3hr": design_flow * 1.15,
            "min_head_m": design_head * 0.7,
            "max_head_m": design_head * 1.1,
            "max_bearing_temp_c": pump_bearing_limits(pump_id)["alarm_max"],
            "max_vibration_mms": 7.1,
        },
        "bearing_temp_limits": pump_bearing_limits(pump_id),
        "oem_manual": pump_manual(pump_id),
        "_source_row": meta["_row"],
    }
