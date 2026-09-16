#!/usr/bin/env python3
"""Web server for demo UI. Wraps the Strands agent with REST endpoints and trace visualization.

This is the demo server — the production deployment uses AgentCore runtime (main.py).
Run: python web_server.py
"""

import json
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from strands import Agent

from config import SERVER_PORT, ALL_PUMP_IDS
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

SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.md").read_text()
STATIC_DIR = Path(__file__).parent / "static"

ALL_TOOLS = [
    query_sensors, get_pump_profile, check_vibration_zone,
    classify_failure_mode, search_alarms, get_maintenance_history,
    check_spare_parts, compute_cost, search_oem_manual, get_operating_status,
]

app = FastAPI(title="CDU Pump Predictive Maintenance Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

agent = Agent(
    model=load_model(),
    system_prompt=SYSTEM_PROMPT,
    tools=ALL_TOOLS,
    callback_handler=None,
)

trace_history: list[dict] = []


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    citations: list
    trace: dict
    tool_calls: int = 0


def _extract_citations_from_trace(trace: dict) -> list:
    citations = []
    for step in trace.get("steps", []):
        for evidence in step.get("evidence", []):
            citations.append(evidence)
    return citations


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    collector = TraceCollector()
    collector.start_invocation(req.message)

    start = time.time()
    try:
        result = agent(req.message)
        response_text = str(result)
    except Exception as e:
        response_text = f"Error: {e}"

    duration = (time.time() - start) * 1000

    for msg in agent.messages:
        if msg.get("role") == "assistant":
            for block in msg.get("content", []):
                if isinstance(block, dict) and "toolUse" in block:
                    tu = block["toolUse"]
                    tool_name = tu.get("name", "unknown")
                    tool_input = tu.get("input", {})
                    tool_id = tu.get("toolUseId", "")

                    tool_output = {}
                    for rmsg in agent.messages:
                        if rmsg.get("role") == "user":
                            for rblock in rmsg.get("content", []):
                                if isinstance(rblock, dict) and "toolResult" in rblock:
                                    tr = rblock["toolResult"]
                                    if tr.get("toolUseId") == tool_id:
                                        for c in tr.get("content", []):
                                            if isinstance(c, dict) and "text" in c:
                                                try:
                                                    tool_output = json.loads(c["text"])
                                                except (json.JSONDecodeError, TypeError):
                                                    tool_output = {"raw": c["text"][:500]}

                    collector.record_tool_call(tool_name, tool_input, tool_output, 0)

    collector.finish_invocation(response_text)
    trace = collector.get_trace() or {}
    trace["total_duration_ms"] = round(duration, 1)

    trace_history.append(trace)
    if len(trace_history) > 50:
        trace_history.pop(0)

    citations = _extract_citations_from_trace(trace)

    return ChatResponse(
        response=response_text,
        citations=citations,
        trace=trace,
        tool_calls=trace.get("total_tool_calls", 0),
    )


@app.post("/api/reset")
def reset_conversation():
    global agent
    agent = Agent(
        model=load_model(),
        system_prompt=SYSTEM_PROMPT,
        tools=ALL_TOOLS,
        callback_handler=None,
    )
    trace_history.clear()
    return {"status": "ok"}


@app.get("/api/fleet")
def fleet():
    results = []
    for pid in ALL_PUMP_IDS:
        profile = get_pump_profile(pump_id=pid)
        vib = check_vibration_zone(pump_id=pid)
        results.append({
            "pump_id": pid,
            "model": profile.get("model", "Unknown"),
            "manufacturer": profile.get("manufacturer", "Unknown"),
            "service_fluid": profile.get("service_fluid", "Unknown"),
            "criticality": profile.get("criticality_rating", 0),
            "vibration_zone": vib.get("overall_zone", "?"),
            "vibration_status": vib.get("overall_status", "Unknown"),
            "bearing_temp_c": vib.get("bearing_temp_c"),
        })
    return results


@app.get("/api/pump/{pump_id}")
def pump_detail(pump_id: str):
    profile = get_pump_profile(pump_id=pump_id)
    vib = check_vibration_zone(pump_id=pump_id)
    alarms = search_alarms(pump_id=pump_id)
    maintenance = get_maintenance_history(pump_id=pump_id)
    return {
        "profile": profile,
        "vibration": vib,
        "recent_alarms": alarms,
        "maintenance_history": maintenance,
    }


@app.get("/api/traces")
def get_traces():
    return {"traces": trace_history[-10:]}


@app.get("/api/traces/latest")
def get_latest_trace():
    if trace_history:
        return trace_history[-1]
    return {"steps": [], "citations": []}


@app.get("/")
def root():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text())
    return HTMLResponse("<h1>CDU Pump Health Monitor</h1><p>Frontend not built yet.</p>")


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn
    print(f"Starting CDU Pump Health Monitor on port {SERVER_PORT}...")
    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT)
