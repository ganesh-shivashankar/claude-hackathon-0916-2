"""CDU Pump Predictive Maintenance Agent — AgentCore Runtime Entry Point.

Uses Strands SDK with @tool-decorated functions, OpenTelemetry tracing,
and evidence-grounded reasoning.
"""

import json
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

from strands import Agent, tool
from strands.agent.conversation_manager.null_conversation_manager import NullConversationManager
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from model.load import load_model
from tracing import TraceCollector

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

app = BedrockAgentCoreApp()
log = app.logger

SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.md").read_text()

ALL_TOOLS = [
    query_sensors,
    get_pump_profile,
    check_vibration_zone,
    classify_failure_mode,
    search_alarms,
    get_maintenance_history,
    check_spare_parts,
    compute_cost,
    search_oem_manual,
    get_operating_status,
]

trace_store: dict[str, list[dict]] = {}


def _make_conversation_manager():
    return NullConversationManager()


def agent_factory():
    cache = OrderedDict()

    def get_or_create_agent(session_id):
        if session_id in cache:
            cache.move_to_end(session_id)
            return cache[session_id]
        if len(cache) >= 128:
            cache.popitem(last=False)
        cache[session_id] = Agent(
            model=load_model(),
            system_prompt=SYSTEM_PROMPT,
            tools=ALL_TOOLS,
            conversation_manager=_make_conversation_manager(),
        )
        return cache[session_id]

    return get_or_create_agent


get_or_create_agent = agent_factory()


def strip_trailing_tool_use(messages: Any) -> list[dict]:
    if not isinstance(messages, list):
        raise ValueError("messages must be a list")
    messages = list(messages)
    while messages:
        last = messages[-1]
        if not isinstance(last, dict):
            raise ValueError("each message must be an object")
        original_content = last.get("content", [])
        if not isinstance(original_content, list) or not all(isinstance(block, dict) for block in original_content):
            raise ValueError("each message content value must be a list of content blocks")
        content = [block for block in original_content if "toolUse" not in block]
        if len(content) == len(original_content):
            break
        if content:
            messages[-1] = {**last, "content": content}
            break
        messages.pop()
    return messages


def _extract_prompt(payload: dict):
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    if "messages" in payload:
        return strip_trailing_tool_use(payload["messages"])
    if "tool_results" in payload:
        tool_results = payload["tool_results"]
        if not isinstance(tool_results, list) or not all(
            isinstance(tr, dict) and isinstance(tr.get("toolUseId"), str) for tr in tool_results
        ):
            raise ValueError("tool_results must contain objects with a toolUseId string")
        return [{"role": "user", "content": [{"toolResult": {
            "toolUseId": tr["toolUseId"],
            "status": tr.get("status", "success"),
            "content": tr.get("content", []),
        }} for tr in tool_results]}]
    prompt = payload.get("prompt", "")
    if not isinstance(prompt, str):
        raise ValueError("prompt must be a string")
    return prompt


@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking CDU Pump Health Agent...")

    session_id = getattr(context, "session_id", "default-session")
    agent = get_or_create_agent(session_id)

    prompt = _extract_prompt(payload)

    collector = TraceCollector()
    query_text = prompt if isinstance(prompt, str) else json.dumps(prompt)[:200]
    collector.start_invocation(query_text)

    async for event in agent.stream_async(prompt):
        if not isinstance(event, dict) or "event" not in event:
            continue

        evt = event["event"]

        if "contentBlockStart" in evt:
            cbs = evt["contentBlockStart"]
            start = cbs.get("start", {})
            if isinstance(start, dict) and start.get("toolUse"):
                tool_name = start["toolUse"].get("name", "unknown")
                collector.advance_step(f"Calling {tool_name}")

        if not evt.get("contentBlockStart", {}).get("start"):
            pass

        yield event

    collector.finish_invocation()
    trace = collector.get_trace()
    if trace:
        if session_id not in trace_store:
            trace_store[session_id] = []
        trace_store[session_id].append(trace)

        yield {
            "event": {
                "metadata": {
                    "trace": trace,
                }
            }
        }


if __name__ == "__main__":
    app.run()
