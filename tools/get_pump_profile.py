#!/usr/bin/env python3
"""Look up pump metadata, operating envelope, and OEM manual reference.

Usage:
    python tools/get_pump_profile.py '{"pump_id":"P-07"}'
    python tools/get_pump_profile.py '{"pump_id":"all"}'
"""

import csv
import json
import sys
import os

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "use-case", "data"))
METADATA_FILE = os.path.join(DATA_DIR, "pump_metadata.csv")

PUMP_TO_MANUAL = {
    "P-01": "flowserve_pvxm3_manual.md",
    "P-02": "flowserve_pvxm3_manual.md",
    "P-07": "flowserve_pvxm3_manual.md",
    "P-10": "flowserve_pvxm3_manual.md",
    "P-03": "sulzer_cpt50_manual.md",
    "P-04": "sulzer_cpt50_manual.md",
    "P-08": "sulzer_cpt50_manual.md",
    "P-11": "sulzer_cpt50_manual.md",
    "P-05": "ksb_etanorm_manual.md",
    "P-06": "ksb_etanorm_manual.md",
    "P-09": "ksb_etanorm_manual.md",
    "P-12": "ksb_etanorm_manual.md",
}

BEARING_TEMP_LIMITS = {
    "Flowserve PVXM-3": {
        "normal_max": 65, "elevated_max": 80, "warning_max": 85,
        "alarm_max": 95, "rate_alert_c_per_hr": 2.0
    },
    "Sulzer CPT-50": {
        "normal_max": 60, "elevated_max": 75, "warning_max": 80,
        "alarm_max": 90, "rate_alert_c_per_hr": 2.0
    },
    "KSB Etanorm 100-080": {
        "normal_max": 65, "elevated_max": 78, "warning_max": 85,
        "alarm_max": 95, "rate_alert_c_per_hr": 2.0
    },
}


def get_profile(pump_id):
    results = []
    with open(METADATA_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            if pump_id != "all" and row["pump_id"] != pump_id:
                continue
            envelope = json.loads(row["operating_envelope_json"])
            model = row["model"]
            profile = {
                "pump_id": row["pump_id"],
                "model": model,
                "manufacturer": row["manufacturer"],
                "install_date": row["install_date"],
                "service_fluid": row["service_fluid"],
                "design_flow_m3hr": float(row["design_flow_m3hr"]),
                "design_head_m": float(row["design_head_m"]),
                "rated_power_kw": float(row["rated_power_kw"]),
                "criticality_rating": int(row["criticality_rating"]),
                "bearing_type": row["bearing_type"],
                "seal_type": row["seal_type"],
                "last_maintenance_date": row["last_maintenance_date"],
                "operating_envelope": envelope,
                "bearing_temp_limits": BEARING_TEMP_LIMITS.get(model, {}),
                "oem_manual": PUMP_TO_MANUAL.get(row["pump_id"], "unknown"),
                "source": {
                    "file": "pump_metadata.csv",
                    "row": row_num
                }
            }
            results.append(profile)

    if not results:
        return json.dumps({
            "status": "not_found",
            "pump_id": pump_id,
            "message": f"No metadata found for {pump_id}",
            "source": {"file": "pump_metadata.csv"}
        }, indent=2)

    if pump_id == "all":
        return json.dumps({
            "status": "ok",
            "count": len(results),
            "pumps": results,
            "source": {"file": "pump_metadata.csv", "row_range": [2, 13]}
        }, indent=2)

    return json.dumps({
        "status": "ok",
        **results[0]
    }, indent=2)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: get_pump_profile.py '{\"pump_id\":\"P-07\"}'"}))
        sys.exit(1)
    params = json.loads(sys.argv[1])
    print(get_profile(**params))
