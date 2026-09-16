#!/usr/bin/env python3
"""Web server for demo UI. Wraps the Strands agent with REST endpoints.

Run: python web_server.py
"""

import asyncio
import csv
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from strands import Agent

from config import SERVER_PORT, ALL_PUMP_IDS, PUMP_METADATA, DATA_DIR
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

executor = ThreadPoolExecutor(max_workers=4)
trace_history: list[dict] = []
conversation_messages: list[dict] = []
jobs: dict[str, dict] = {}


def _make_agent():
    return Agent(
        model=load_model(),
        system_prompt=SYSTEM_PROMPT,
        tools=ALL_TOOLS,
        callback_handler=None,
    )


class ChatRequest(BaseModel):
    message: str


def _extract_citations_from_trace(trace: dict) -> list:
    citations = []
    for step in trace.get("steps", []):
        for evidence in step.get("evidence", []):
            citations.append(evidence)
    return citations


def _run_agent_sync(message: str) -> dict:
    agent = _make_agent()
    agent.messages = list(conversation_messages)

    collector = TraceCollector()
    collector.start_invocation(message)

    start = time.time()
    try:
        result = agent(message)
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

    conversation_messages.clear()
    conversation_messages.extend(agent.messages)

    citations = _extract_citations_from_trace(trace)

    trace_history.append(trace)
    if len(trace_history) > 50:
        trace_history.pop(0)

    return {
        "response": response_text,
        "citations": citations,
        "trace": trace,
        "tool_calls": trace.get("total_tool_calls", 0),
    }


def _run_agent_for_job(job_id: str, message: str):
    result = _run_agent_sync(message)
    result["status"] = "done"
    jobs[job_id] = result


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Returns full response directly. Also supports polling via job_id if poll=true."""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, _run_agent_sync, req.message)
    return result


@app.post("/api/chat/async")
async def chat_async(req: ChatRequest):
    """Async version — returns job_id for polling."""
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "processing"}
    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, _run_agent_for_job, job_id, req.message)
    return {"job_id": job_id, "status": "processing"}


@app.get("/api/chat/status/{job_id}")
def chat_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return {"status": "not_found"}
    return job


@app.post("/api/reset")
def reset_conversation():
    conversation_messages.clear()
    trace_history.clear()
    jobs.clear()
    return {"status": "ok"}


def _load_fleet_fast():
    baselines = {}
    with open(DATA_DIR / "vibration_baselines.csv") as f:
        for row in csv.DictReader(f):
            pid = row["pump_id"]
            if pid not in baselines:
                baselines[pid] = []
            baselines[pid].append({
                "baseline": float(row["baseline_mms"]),
                "alert": float(row["alert_threshold_mms"]),
                "alarm": float(row["alarm_threshold_mms"]),
                "col": {"Drive End Horizontal": "vibration_x_mms",
                        "Drive End Vertical": "vibration_y_mms",
                        "Drive End Axial": "vibration_axial_mms",
                        "Non-Drive End Horizontal": "vibration_x_mms",
                        "Non-Drive End Vertical": "vibration_y_mms",
                        "Non-Drive End Axial": "vibration_axial_mms"}.get(row["measurement_point"], "vibration_x_mms"),
            })

    latest = {}
    with open(DATA_DIR / "sensor_timeseries.csv") as f:
        for row in csv.DictReader(f):
            latest[row["pump_id"]] = row

    results = []
    for pid in ALL_PUMP_IDS:
        meta = PUMP_METADATA.get(pid, {})
        row = latest.get(pid, {})
        zone = "A"
        if pid in baselines and row:
            for bl in baselines[pid]:
                val = float(row.get(bl["col"], 0))
                if val > bl["alarm"]:
                    z = "D"
                elif val > bl["alert"]:
                    z = "C"
                elif val > bl["baseline"] * 1.2:
                    z = "B"
                else:
                    z = "A"
                if z > zone:
                    zone = z

        zone_labels = {"A": "Good", "B": "Acceptable", "C": "Unsatisfactory", "D": "Dangerous"}
        results.append({
            "pump_id": pid,
            "model": meta.get("pump_model", "Unknown"),
            "manufacturer": meta.get("manufacturer", "Unknown"),
            "service_fluid": meta.get("service_fluid", "Unknown"),
            "criticality": int(meta.get("criticality_rating", 0)),
            "vibration_zone": zone,
            "vibration_status": zone_labels.get(zone, "Unknown"),
            "bearing_temp_c": float(row.get("bearing_temp_c", 0)) if row else None,
        })
    return results


@app.get("/api/fleet")
async def fleet():
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, _load_fleet_fast)


@app.get("/api/pump/{pump_id}")
async def pump_detail(pump_id: str):
    def _load():
        profile = get_pump_profile(pump_id=pump_id)
        vib = check_vibration_zone(pump_id=pump_id)
        alarms = search_alarms(pump_id=pump_id)
        maintenance = get_maintenance_history(pump_id=pump_id)
        return {"profile": profile, "vibration": vib, "recent_alarms": alarms, "maintenance_history": maintenance}
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, _load)


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
        return HTMLResponse(index.read_text(), headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        })
    return HTMLResponse("<h1>CDU Pump Health Monitor</h1>")


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn
    print(f"Starting CDU Pump Health Monitor on port {SERVER_PORT}...")
    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT, timeout_keep_alive=300)
