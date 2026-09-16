#!/usr/bin/env python3
"""Groundedness evaluation for CDU Pump Health Agent.

Checks that agent responses:
1. Cite specific data files and row numbers
2. Don't fabricate numbers not present in tool outputs
3. Use correct pump IDs and failure modes
4. Follow the expected tool trajectory
"""

import json
import re
import sys
from pathlib import Path

CITATION_PATTERN = re.compile(r"\[([a-zA-Z_]+\.(?:csv|json|md)),\s*(.*?)\]")
ROW_PATTERN = re.compile(r"rows?\s*(\d+)[-–](\d+)")
FILE_PATTERN = re.compile(r"\b(sensor_timeseries|alarm_history|failure_event_log|failure_mode_reference|pump_metadata|vibration_baselines|cost_tracking|maintenance_work_orders|spare_parts_inventory|operating_schedule)\.csv\b")
MANUAL_PATTERN = re.compile(r"\b(flowserve_pvxm3|sulzer_cpt50|ksb_etanorm)_manual\.md\b")


def check_citations(response_text: str) -> dict:
    citations = CITATION_PATTERN.findall(response_text)
    file_refs = FILE_PATTERN.findall(response_text)
    manual_refs = MANUAL_PATTERN.findall(response_text)
    row_refs = ROW_PATTERN.findall(response_text)

    return {
        "has_citations": len(citations) > 0,
        "citation_count": len(citations),
        "files_referenced": list(set(file_refs)),
        "manuals_referenced": list(set(manual_refs)),
        "row_references": len(row_refs),
        "cited_files": [c[0] for c in citations],
    }


def check_trajectory(trace: dict, expected_tools: list[str]) -> dict:
    actual_tools = []
    for step in trace.get("steps", []):
        for t in step.get("tools", []):
            actual_tools.append(t["name"])

    expected_set = set(expected_tools)
    actual_set = set(actual_tools)
    missing = expected_set - actual_set
    extra = actual_set - expected_set

    return {
        "expected_tools": expected_tools,
        "actual_tools": actual_tools,
        "missing_tools": list(missing),
        "extra_tools": list(extra),
        "trajectory_match": len(missing) == 0,
        "tool_count": len(actual_tools),
    }


def check_groundedness(response_text: str, trace: dict) -> dict:
    """Check that claims in the response are grounded in tool outputs."""
    tool_outputs = []
    for step in trace.get("steps", []):
        for t in step.get("tools", []):
            tool_outputs.append(t.get("output_summary", ""))

    all_tool_text = " ".join(tool_outputs).lower()

    numbers_in_response = re.findall(r"\b(\d+\.?\d*)\b", response_text)
    grounded_numbers = 0
    ungrounded_numbers = []
    for num in numbers_in_response:
        if float(num) < 10:
            grounded_numbers += 1
            continue
        if num in all_tool_text:
            grounded_numbers += 1
        else:
            ungrounded_numbers.append(num)

    pump_ids_in_response = re.findall(r"P-\d{2}", response_text)
    valid_pump_ids = {f"P-{i:02d}" for i in range(1, 13)}
    invalid_pumps = [p for p in pump_ids_in_response if p not in valid_pump_ids]

    failure_modes = ["bearing_wear", "seal_failure", "cavitation", "impeller_damage", "misalignment"]
    mentioned_modes = [m for m in failure_modes if m in response_text.lower()]

    return {
        "total_numbers": len(numbers_in_response),
        "grounded_numbers": grounded_numbers,
        "ungrounded_numbers": ungrounded_numbers[:10],
        "groundedness_ratio": round(grounded_numbers / max(len(numbers_in_response), 1), 3),
        "invalid_pump_ids": invalid_pumps,
        "failure_modes_mentioned": mentioned_modes,
        "has_no_data_hedge": any(phrase in response_text.lower() for phrase in [
            "data does not contain", "no evidence", "insufficient data", "not enough data"
        ]),
    }


def evaluate_scenario(response_text: str, trace: dict, assertions: list[str], expected_trajectory: list[str]) -> dict:
    citation_check = check_citations(response_text)
    trajectory_check = check_trajectory(trace, expected_trajectory)
    groundedness_check = check_groundedness(response_text, trace)

    assertion_results = []
    for assertion in assertions:
        key_terms = assertion.lower().replace("must ", "").replace("mention ", "").replace("cite ", "").replace("include ", "").replace("show ", "")
        passed = any(term.strip() in response_text.lower() for term in key_terms.split(" ") if len(term.strip()) > 3)
        assertion_results.append({"assertion": assertion, "passed": passed})

    assertions_passed = sum(1 for a in assertion_results if a["passed"])
    total_assertions = len(assertion_results)

    score = 0.0
    score += 0.25 * (1.0 if citation_check["has_citations"] else 0.0)
    score += 0.25 * (1.0 if trajectory_check["trajectory_match"] else 0.5 if len(trajectory_check["missing_tools"]) <= 1 else 0.0)
    score += 0.25 * groundedness_check["groundedness_ratio"]
    score += 0.25 * (assertions_passed / max(total_assertions, 1))

    return {
        "score": round(score, 3),
        "pass": score >= 0.6,
        "citations": citation_check,
        "trajectory": trajectory_check,
        "groundedness": groundedness_check,
        "assertions": assertion_results,
        "assertions_passed": f"{assertions_passed}/{total_assertions}",
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: eval_groundedness.py <response_file.json>")
        print("  Input JSON: {response, trace, assertions, expected_trajectory}")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    result = evaluate_scenario(
        data["response"],
        data.get("trace", {}),
        data.get("assertions", []),
        data.get("expected_trajectory", []),
    )
    print(json.dumps(result, indent=2))
