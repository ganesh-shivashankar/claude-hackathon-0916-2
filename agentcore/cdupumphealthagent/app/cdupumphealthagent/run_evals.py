#!/usr/bin/env python3
"""Run evaluation scenarios against the Strands agent and check groundedness.

Usage:
    cd /workshop/agentcore/cdupumphealthagent/app/cdupumphealthagent
    python run_evals.py
"""

import json
import time
import sys
from pathlib import Path

from strands import Agent
from model.load import load_model
from tracing import TraceCollector
from eval_groundedness import evaluate_scenario

from tools.query_sensors import query_sensors
from tools.get_pump_profile import get_pump_profile
from tools.check_vibration_zone import check_vibration_zone
from tools.classify_failure_mode import classify_failure_mode
from tools.search_alarms import search_alarms
from tools.get_maintenance_history import get_maintenance_history
from tools.check_spare_parts import check_spare_parts
from tools.compute_cost import compute_cost
from tools.search_oem_manual import search_oem_manual
from tools.get_operating_status import get_operating_status

SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.md").read_text()

ALL_TOOLS = [
    query_sensors, get_pump_profile, check_vibration_zone,
    classify_failure_mode, search_alarms, get_maintenance_history,
    check_spare_parts, compute_cost, search_oem_manual, get_operating_status,
]

SCENARIOS = json.loads(
    "[" + ",".join(
        line for line in
        (Path(__file__).parent.parent.parent / "agentcore" / "datasets" / "pump_health_eval.jsonl").read_text().strip().split("\n")
    ) + "]"
)


def run_scenario(scenario: dict, agent: Agent) -> dict:
    name = scenario.get("scenario_id", scenario.get("scenario_name", "unknown"))
    turns = scenario.get("turns", [])
    prompt = turns[0]["input"] if turns else scenario.get("prompt", "")
    assertions = scenario.get("assertions", [])
    expected_trajectory = scenario.get("expected_trajectory", [])

    print(f"\n{'='*60}")
    print(f"Scenario: {name}")
    print(f"Prompt: {prompt}")
    print(f"{'='*60}")

    collector = TraceCollector()
    collector.start_invocation(prompt)
    start = time.time()

    try:
        result = agent(prompt)
        response_text = str(result)
    except Exception as e:
        response_text = f"ERROR: {e}"

    duration = (time.time() - start) * 1000
    collector.finish_invocation(response_text)
    trace = collector.get_trace() or {"steps": [], "citations": []}
    trace["total_duration_ms"] = round(duration, 1)

    eval_result = evaluate_scenario(response_text, trace, assertions, expected_trajectory)

    print(f"  Score: {eval_result['score']}")
    print(f"  Pass: {eval_result['pass']}")
    print(f"  Citations: {eval_result['citations']['citation_count']}")
    print(f"  Trajectory match: {eval_result['trajectory']['trajectory_match']}")
    print(f"  Groundedness ratio: {eval_result['groundedness']['groundedness_ratio']}")
    print(f"  Assertions: {eval_result['assertions_passed']}")
    print(f"  Duration: {duration:.0f}ms")

    if eval_result["trajectory"]["missing_tools"]:
        print(f"  Missing tools: {eval_result['trajectory']['missing_tools']}")

    return {
        "scenario": name,
        "score": eval_result["score"],
        "pass": eval_result["pass"],
        "duration_ms": round(duration, 1),
        "details": eval_result,
    }


def main():
    print("CDU Pump Health Agent — Groundedness Evaluation")
    print("=" * 60)

    results = []
    for scenario in SCENARIOS:
        agent = Agent(
            model=load_model(),
            system_prompt=SYSTEM_PROMPT,
            tools=ALL_TOOLS,
            callback_handler=None,
        )
        r = run_scenario(scenario, agent)
        results.append(r)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    passed = sum(1 for r in results if r["pass"])
    total = len(results)
    avg_score = sum(r["score"] for r in results) / total if total else 0

    print(f"Passed: {passed}/{total}")
    print(f"Average score: {avg_score:.3f}")
    for r in results:
        status = "PASS" if r["pass"] else "FAIL"
        print(f"  [{status}] {r['scenario']}: score={r['score']}, duration={r['duration_ms']:.0f}ms")

    output_file = Path(__file__).parent / "eval_results.json"
    with open(output_file, "w") as f:
        json.dump({"passed": passed, "total": total, "avg_score": avg_score, "results": results}, f, indent=2)
    print(f"\nResults saved to {output_file}")


if __name__ == "__main__":
    main()
