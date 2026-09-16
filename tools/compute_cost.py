#!/usr/bin/env python3
"""Compute maintenance and failure cost summaries from cost_tracking.csv and failure_event_log.csv.

Usage:
    python tools/compute_cost.py '{"pump_id":"P-07"}'
    python tools/compute_cost.py '{"pump_id":"P-07","scenario":"comparison"}'
    python tools/compute_cost.py '{"scenario":"fleet_summary"}'
"""

import csv
import json
import os
import sys

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "use-case", "data"))
COST_FILE = os.path.join(DATA_DIR, "cost_tracking.csv")
FAILURE_FILE = os.path.join(DATA_DIR, "failure_event_log.csv")

# Pump-to-model mapping for proactive cost estimation
PUMP_MODEL_MAP = {
    "P-01": "Flowserve PVXM-3", "P-02": "Flowserve PVXM-3",
    "P-07": "Flowserve PVXM-3", "P-10": "Flowserve PVXM-3",
    "P-05": "KSB Etanorm 100-080", "P-06": "KSB Etanorm 100-080",
    "P-09": "KSB Etanorm 100-080", "P-12": "KSB Etanorm 100-080",
    "P-03": "Sulzer CPT-50", "P-04": "Sulzer CPT-50",
    "P-08": "Sulzer CPT-50", "P-11": "Sulzer CPT-50",
}

# Rough proactive maintenance cost estimates by failure mode (industry benchmarks)
PROACTIVE_COST_ESTIMATES = {
    "bearing_wear": {"proactive_cost_usd": 3500, "description": "Planned bearing replacement during scheduled shutdown", "typical_downtime_hrs": 4},
    "seal_failure": {"proactive_cost_usd": 5000, "description": "Planned seal replacement during scheduled shutdown", "typical_downtime_hrs": 6},
    "cavitation": {"proactive_cost_usd": 1500, "description": "NPSH correction and suction line inspection", "typical_downtime_hrs": 2},
    "impeller_damage": {"proactive_cost_usd": 8000, "description": "Planned impeller replacement during turnaround", "typical_downtime_hrs": 8},
    "misalignment": {"proactive_cost_usd": 2000, "description": "Laser alignment and coupling check", "typical_downtime_hrs": 3},
}


def load_cost_data():
    """Load cost_tracking.csv and return rows plus row metadata."""
    rows = []
    with open(COST_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            row["_row_num"] = row_num
            for col in ("maintenance_cost_usd", "energy_cost_usd", "parts_cost_usd", "total_cost_usd"):
                try:
                    row[col] = float(row[col])
                except (ValueError, KeyError):
                    row[col] = 0.0
            rows.append(row)
    return rows


def load_failure_data():
    """Load failure_event_log.csv and return rows plus row metadata."""
    rows = []
    with open(FAILURE_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            row["_row_num"] = row_num
            try:
                row["repair_cost_usd"] = float(row["repair_cost_usd"])
            except (ValueError, KeyError):
                row["repair_cost_usd"] = 0.0
            try:
                row["downtime_hrs"] = float(row["downtime_hrs"])
            except (ValueError, KeyError):
                row["downtime_hrs"] = 0.0
            rows.append(row)
    return rows


def pump_cost_history(pump_id):
    """Return cost history and any failure costs for a single pump."""
    cost_rows = load_cost_data()
    failure_rows = load_failure_data()

    # Filter cost rows for this pump
    pump_costs = [r for r in cost_rows if r["pump_id"] == pump_id]
    if not pump_costs:
        return {
            "status": "no_data",
            "pump_id": pump_id,
            "message": f"No cost records found for {pump_id}",
            "source": {"file": "cost_tracking.csv"}
        }

    # Aggregate by month
    monthly = {}
    for r in pump_costs:
        m = r["month"]
        if m not in monthly:
            monthly[m] = {"month": m, "maintenance_cost_usd": 0, "energy_cost_usd": 0, "parts_cost_usd": 0, "total_cost_usd": 0, "entries": 0}
        monthly[m]["maintenance_cost_usd"] += r["maintenance_cost_usd"]
        monthly[m]["energy_cost_usd"] += r["energy_cost_usd"]
        monthly[m]["parts_cost_usd"] += r["parts_cost_usd"]
        monthly[m]["total_cost_usd"] += r["total_cost_usd"]
        monthly[m]["entries"] += 1

    monthly_list = []
    for m in sorted(monthly.keys()):
        entry = monthly[m]
        monthly_list.append({
            "month": entry["month"],
            "maintenance_cost_usd": round(entry["maintenance_cost_usd"], 2),
            "energy_cost_usd": round(entry["energy_cost_usd"], 2),
            "parts_cost_usd": round(entry["parts_cost_usd"], 2),
            "total_cost_usd": round(entry["total_cost_usd"], 2),
        })

    # Totals
    total_maintenance = round(sum(r["maintenance_cost_usd"] for r in pump_costs), 2)
    total_energy = round(sum(r["energy_cost_usd"] for r in pump_costs), 2)
    total_parts = round(sum(r["parts_cost_usd"] for r in pump_costs), 2)
    total_all = round(sum(r["total_cost_usd"] for r in pump_costs), 2)
    avg_monthly = round(total_all / len(monthly), 2) if monthly else 0

    # Failure events for this pump
    pump_failures = [r for r in failure_rows if r["pump_id"] == pump_id]
    failure_summary = []
    total_failure_cost = 0
    total_downtime = 0
    failure_row_start = None
    failure_row_end = None
    for f in pump_failures:
        if failure_row_start is None:
            failure_row_start = f["_row_num"]
        failure_row_end = f["_row_num"]
        total_failure_cost += f["repair_cost_usd"]
        total_downtime += f["downtime_hrs"]
        failure_summary.append({
            "event_id": f["event_id"],
            "failure_mode": f["failure_mode"],
            "failure_ts": f["failure_ts"],
            "downtime_hrs": f["downtime_hrs"],
            "repair_cost_usd": f["repair_cost_usd"],
        })

    cost_row_start = pump_costs[0]["_row_num"] if pump_costs else None
    cost_row_end = pump_costs[-1]["_row_num"] if pump_costs else None

    result = {
        "status": "ok",
        "pump_id": pump_id,
        "pump_model": PUMP_MODEL_MAP.get(pump_id, "unknown"),
        "cost_summary": {
            "total_maintenance_cost_usd": total_maintenance,
            "total_energy_cost_usd": total_energy,
            "total_parts_cost_usd": total_parts,
            "total_cost_usd": total_all,
            "months_tracked": len(monthly),
            "avg_monthly_cost_usd": avg_monthly,
        },
        "monthly_breakdown": monthly_list,
        "failure_events": failure_summary if failure_summary else "No failure events recorded",
        "failure_cost_summary": {
            "total_repair_cost_usd": round(total_failure_cost, 2),
            "total_downtime_hrs": round(total_downtime, 1),
            "event_count": len(failure_summary),
        } if failure_summary else None,
        "sources": [
            {
                "file": "cost_tracking.csv",
                "row_range": [cost_row_start, cost_row_end],
                "total_rows_matched": len(pump_costs),
                "columns": ["pump_id", "month", "maintenance_cost_usd", "energy_cost_usd", "parts_cost_usd", "total_cost_usd"],
            },
        ]
    }
    if failure_summary:
        result["sources"].append({
            "file": "failure_event_log.csv",
            "row_range": [failure_row_start, failure_row_end],
            "total_rows_matched": len(failure_summary),
            "columns": ["event_id", "pump_id", "failure_mode", "failure_ts", "downtime_hrs", "repair_cost_usd"],
        })

    return result


def comparison(pump_id):
    """Compare proactive maintenance cost vs reactive failure cost for a pump."""
    failure_rows = load_failure_data()
    pump_failures = [r for r in failure_rows if r["pump_id"] == pump_id]

    # Also get failures for same-model pumps to enrich the comparison
    model = PUMP_MODEL_MAP.get(pump_id, "unknown")
    same_model_pumps = [pid for pid, m in PUMP_MODEL_MAP.items() if m == model]
    model_failures = [r for r in failure_rows if r["pump_id"] in same_model_pumps]

    comparisons = []
    failure_row_start = None
    failure_row_end = None

    # Gather all failure modes seen across the model fleet
    failure_modes_seen = set()
    for f in model_failures:
        failure_modes_seen.add(f["failure_mode"])
        if failure_row_start is None or f["_row_num"] < failure_row_start:
            failure_row_start = f["_row_num"]
        if failure_row_end is None or f["_row_num"] > failure_row_end:
            failure_row_end = f["_row_num"]

    if not failure_modes_seen:
        failure_modes_seen = set(PROACTIVE_COST_ESTIMATES.keys())

    for mode in sorted(failure_modes_seen):
        proactive = PROACTIVE_COST_ESTIMATES.get(mode, {})
        # Find actual reactive costs for this pump and this failure mode
        reactive_events = [f for f in pump_failures if f["failure_mode"] == mode]
        # Also find model-wide reactive costs
        model_reactive = [f for f in model_failures if f["failure_mode"] == mode]

        reactive_cost_this_pump = sum(f["repair_cost_usd"] for f in reactive_events)
        reactive_downtime_this_pump = sum(f["downtime_hrs"] for f in reactive_events)

        avg_reactive_cost_model = round(sum(f["repair_cost_usd"] for f in model_reactive) / len(model_reactive), 2) if model_reactive else None
        avg_reactive_downtime_model = round(sum(f["downtime_hrs"] for f in model_reactive) / len(model_reactive), 1) if model_reactive else None

        proactive_cost = proactive.get("proactive_cost_usd", "N/A")
        proactive_downtime = proactive.get("typical_downtime_hrs", "N/A")

        entry = {
            "failure_mode": mode,
            "proactive_maintenance": {
                "estimated_cost_usd": proactive_cost,
                "estimated_downtime_hrs": proactive_downtime,
                "description": proactive.get("description", "N/A"),
            },
            "reactive_repair": {
                "this_pump_events": len(reactive_events),
                "this_pump_total_cost_usd": round(reactive_cost_this_pump, 2),
                "this_pump_total_downtime_hrs": round(reactive_downtime_this_pump, 1),
                "model_fleet_avg_cost_usd": avg_reactive_cost_model,
                "model_fleet_avg_downtime_hrs": avg_reactive_downtime_model,
                "model_fleet_events": len(model_reactive),
            },
        }

        if isinstance(proactive_cost, (int, float)) and avg_reactive_cost_model:
            savings = round(avg_reactive_cost_model - proactive_cost, 2)
            savings_pct = round((savings / avg_reactive_cost_model) * 100, 1) if avg_reactive_cost_model > 0 else 0
            entry["savings_estimate"] = {
                "cost_savings_vs_reactive_usd": savings,
                "savings_pct": savings_pct,
                "downtime_reduction_hrs": round(avg_reactive_downtime_model - proactive_downtime, 1) if avg_reactive_downtime_model else None,
            }

        comparisons.append(entry)

    result = {
        "status": "ok",
        "pump_id": pump_id,
        "pump_model": model,
        "scenario": "comparison",
        "same_model_pumps": same_model_pumps,
        "comparisons": comparisons,
        "sources": [
            {
                "file": "failure_event_log.csv",
                "row_range": [failure_row_start, failure_row_end] if failure_row_start else None,
                "total_rows_matched": len(model_failures),
                "columns": ["event_id", "pump_id", "failure_mode", "downtime_hrs", "repair_cost_usd"],
            },
            {
                "note": "Proactive cost estimates are industry benchmarks for planned maintenance vs unplanned repair",
            }
        ]
    }
    return result


def fleet_summary():
    """Return total cost summary across all pumps."""
    cost_rows = load_cost_data()
    failure_rows = load_failure_data()

    # Per-pump aggregation
    pump_totals = {}
    for r in cost_rows:
        pid = r["pump_id"]
        if pid not in pump_totals:
            pump_totals[pid] = {
                "pump_id": pid,
                "model": PUMP_MODEL_MAP.get(pid, "unknown"),
                "maintenance_cost_usd": 0,
                "energy_cost_usd": 0,
                "parts_cost_usd": 0,
                "total_cost_usd": 0,
                "row_count": 0,
            }
        pump_totals[pid]["maintenance_cost_usd"] += r["maintenance_cost_usd"]
        pump_totals[pid]["energy_cost_usd"] += r["energy_cost_usd"]
        pump_totals[pid]["parts_cost_usd"] += r["parts_cost_usd"]
        pump_totals[pid]["total_cost_usd"] += r["total_cost_usd"]
        pump_totals[pid]["row_count"] += 1

    # Round the totals
    for pid in pump_totals:
        for col in ("maintenance_cost_usd", "energy_cost_usd", "parts_cost_usd", "total_cost_usd"):
            pump_totals[pid][col] = round(pump_totals[pid][col], 2)

    # Sort by total cost descending
    sorted_pumps = sorted(pump_totals.values(), key=lambda x: x["total_cost_usd"], reverse=True)

    # Fleet totals
    fleet_maintenance = round(sum(p["maintenance_cost_usd"] for p in sorted_pumps), 2)
    fleet_energy = round(sum(p["energy_cost_usd"] for p in sorted_pumps), 2)
    fleet_parts = round(sum(p["parts_cost_usd"] for p in sorted_pumps), 2)
    fleet_total = round(sum(p["total_cost_usd"] for p in sorted_pumps), 2)

    # Failure totals
    total_failure_cost = round(sum(r["repair_cost_usd"] for r in failure_rows), 2)
    total_downtime = round(sum(r["downtime_hrs"] for r in failure_rows), 1)

    # Per-pump failure costs
    failure_by_pump = {}
    for f in failure_rows:
        pid = f["pump_id"]
        if pid not in failure_by_pump:
            failure_by_pump[pid] = {"repair_cost_usd": 0, "downtime_hrs": 0, "events": 0}
        failure_by_pump[pid]["repair_cost_usd"] += f["repair_cost_usd"]
        failure_by_pump[pid]["downtime_hrs"] += f["downtime_hrs"]
        failure_by_pump[pid]["events"] += 1

    for pid in failure_by_pump:
        failure_by_pump[pid]["repair_cost_usd"] = round(failure_by_pump[pid]["repair_cost_usd"], 2)
        failure_by_pump[pid]["downtime_hrs"] = round(failure_by_pump[pid]["downtime_hrs"], 1)

    cost_row_start = cost_rows[0]["_row_num"] if cost_rows else None
    cost_row_end = cost_rows[-1]["_row_num"] if cost_rows else None
    fail_row_start = failure_rows[0]["_row_num"] if failure_rows else None
    fail_row_end = failure_rows[-1]["_row_num"] if failure_rows else None

    result = {
        "status": "ok",
        "scenario": "fleet_summary",
        "fleet_cost_totals": {
            "total_maintenance_cost_usd": fleet_maintenance,
            "total_energy_cost_usd": fleet_energy,
            "total_parts_cost_usd": fleet_parts,
            "total_operating_cost_usd": fleet_total,
        },
        "fleet_failure_totals": {
            "total_repair_cost_usd": total_failure_cost,
            "total_downtime_hrs": total_downtime,
            "total_failure_events": len(failure_rows),
        },
        "per_pump_costs": sorted_pumps,
        "per_pump_failure_costs": failure_by_pump,
        "highest_cost_pump": sorted_pumps[0]["pump_id"] if sorted_pumps else None,
        "sources": [
            {
                "file": "cost_tracking.csv",
                "row_range": [cost_row_start, cost_row_end],
                "total_rows_matched": len(cost_rows),
                "columns": ["pump_id", "month", "maintenance_cost_usd", "energy_cost_usd", "parts_cost_usd", "total_cost_usd"],
            },
            {
                "file": "failure_event_log.csv",
                "row_range": [fail_row_start, fail_row_end],
                "total_rows_matched": len(failure_rows),
                "columns": ["event_id", "pump_id", "failure_mode", "downtime_hrs", "repair_cost_usd"],
            }
        ]
    }
    return result


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: compute_cost.py '{\"pump_id\":\"P-07\"}' or '{\"scenario\":\"fleet_summary\"}'"}))
        sys.exit(1)

    params = json.loads(sys.argv[1])
    pump_id = params.get("pump_id")
    scenario = params.get("scenario")

    if scenario == "fleet_summary":
        result = fleet_summary()
    elif scenario == "comparison" and pump_id:
        result = comparison(pump_id)
    elif pump_id:
        result = pump_cost_history(pump_id)
    else:
        result = {"error": "Provide pump_id, or scenario='fleet_summary'. For comparison, provide both pump_id and scenario='comparison'."}

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
