#!/usr/bin/env python3
"""FastAPI server for the CDU Pump Predictive Maintenance Agent.

Wraps all 10 Python tools and uses Claude on Bedrock for reasoning.
Serves the static frontend and provides API endpoints.

Usage:
    cd /workshop && python agent/server.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import boto3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

TOOLS_DIR = Path(__file__).parent.parent / "tools"
DATA_DIR = Path(__file__).parent.parent / "use-case" / "data"
STATIC_DIR = Path(__file__).parent / "static"
SYSTEM_PROMPT_FILE = Path(__file__).parent / "system_prompt.md"

app = FastAPI(title="CDU Pump Predictive Maintenance Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

conversation_history = []


def load_system_prompt():
    return SYSTEM_PROMPT_FILE.read_text()


TOOL_DEFINITIONS = [
    {
        "name": "query_sensors",
        "description": "Query sensor_timeseries.csv for a specific pump. Returns time series data with aggregation and trend analysis. ALWAYS specify pump_id and a time range (start/end or last_n_hours). Use aggregation='hourly' or 'daily' for ranges over 24 hours.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pump_id": {"type": "string", "description": "Pump ID (P-01 through P-12)"},
                "start": {"type": "string", "description": "Start datetime (YYYY-MM-DD or ISO format)"},
                "end": {"type": "string", "description": "End datetime"},
                "last_n_hours": {"type": "integer", "description": "Alternative to start/end: query last N hours"},
                "metrics": {"type": "array", "items": {"type": "string"}, "description": "Sensor columns to include. Options: bearing_temp_c, vibration_x_mms, vibration_y_mms, vibration_axial_mms, suction_pressure_psi, discharge_pressure_psi, differential_pressure_psi, flow_rate_m3hr, motor_current_amps, motor_speed_rpm"},
                "aggregation": {"type": "string", "enum": ["raw", "hourly", "daily"], "description": "Aggregation level"},
                "include_labels": {"type": "boolean", "description": "Include label distribution (normal/pre_failure/failure)"}
            },
            "required": ["pump_id"]
        }
    },
    {
        "name": "get_pump_profile",
        "description": "Get pump metadata: model, manufacturer, operating envelope, bearing temp limits, OEM manual reference. Use pump_id='all' for all 12 pumps.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pump_id": {"type": "string", "description": "Pump ID or 'all'"}
            },
            "required": ["pump_id"]
        }
    },
    {
        "name": "check_vibration_zone",
        "description": "Classify current vibration into ISO 10816 zones (A/B/C/D) per axis for a pump. Compares against per-pump baselines from vibration_baselines.csv.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pump_id": {"type": "string", "description": "Pump ID"},
                "timestamp": {"type": "string", "description": "Optional: check at specific time instead of latest"}
            },
            "required": ["pump_id"]
        }
    },
    {
        "name": "classify_failure_mode",
        "description": "Match sensor anomaly signals against 5 known failure modes (bearing_wear, seal_failure, cavitation, impeller_damage, misalignment). Returns ranked diagnoses with confidence.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pump_id": {"type": "string", "description": "Pump ID"},
                "signals": {"type": "object", "description": "Dict of observed signals, e.g. {\"bearing_temp_rising\": true, \"vibration_elevated\": true}"}
            },
            "required": ["pump_id", "signals"]
        }
    },
    {
        "name": "search_alarms",
        "description": "Search alarm_history.csv for a pump. Returns alarm events filtered by time range and type.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pump_id": {"type": "string", "description": "Pump ID"},
                "start": {"type": "string", "description": "Start date"},
                "end": {"type": "string", "description": "End date"},
                "alarm_type": {"type": "string", "description": "Filter by alarm type"}
            },
            "required": ["pump_id"]
        }
    },
    {
        "name": "get_maintenance_history",
        "description": "Get merged maintenance history from both logs (pump_maintenance_history.json and maintenance_work_orders.csv). Returns unified timeline sorted by date.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pump_id": {"type": "string", "description": "Pump ID"}
            },
            "required": ["pump_id"]
        }
    },
    {
        "name": "check_spare_parts",
        "description": "Check spare parts inventory. Filter by pump compatibility, category (Bearing/Seal/Impeller/Coupling/Gasket/Lubricant), or part number.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pump_id": {"type": "string", "description": "Filter parts compatible with this pump"},
                "category": {"type": "string", "description": "Part category"},
                "part_number": {"type": "string", "description": "Specific part number"}
            }
        }
    },
    {
        "name": "compute_cost",
        "description": "Compute maintenance cost analysis. Modes: single pump history, repair-vs-failure comparison, or fleet summary.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pump_id": {"type": "string", "description": "Pump ID (omit for fleet summary)"},
                "scenario": {"type": "string", "enum": ["history", "comparison", "fleet_summary"], "description": "Analysis type"}
            }
        }
    },
    {
        "name": "search_oem_manual",
        "description": "Search OEM equipment manuals (Flowserve PVXM-3, Sulzer CPT-50, KSB Etanorm). Returns relevant sections with line numbers for citation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pump_id": {"type": "string", "description": "Pump ID (determines which manual)"},
                "pump_model": {"type": "string", "description": "Alternative: specify model directly"},
                "topic": {"type": "string", "description": "Topic: bearing, vibration, seal, troubleshooting, maintenance, cavitation"},
                "query": {"type": "string", "description": "Free-text search query"}
            }
        }
    },
    {
        "name": "get_operating_status",
        "description": "Get pump operating schedule: duty state (Running/Standby/Maintenance), load %, process assignment, run hours.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pump_id": {"type": "string", "description": "Pump ID"},
                "start": {"type": "string", "description": "Start date"},
                "end": {"type": "string", "description": "End date"}
            },
            "required": ["pump_id"]
        }
    },
]

TOOL_SCRIPT_MAP = {
    "query_sensors": "query_sensors.py",
    "get_pump_profile": "get_pump_profile.py",
    "check_vibration_zone": "check_vibration_zone.py",
    "classify_failure_mode": "classify_failure_mode.py",
    "search_alarms": "search_alarms.py",
    "get_maintenance_history": "get_maintenance_history.py",
    "check_spare_parts": "check_spare_parts.py",
    "compute_cost": "compute_cost.py",
    "search_oem_manual": "search_oem_manual.py",
    "get_operating_status": "get_operating_status.py",
}


def run_tool(tool_name: str, tool_input: dict) -> str:
    script = TOOL_SCRIPT_MAP.get(tool_name)
    if not script:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    script_path = TOOLS_DIR / script
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), json.dumps(tool_input)],
            capture_output=True, text=True, timeout=120,
            env={**os.environ, "DATA_DIR": str(DATA_DIR)}
        )
        if result.returncode != 0:
            return json.dumps({"error": f"Tool error: {result.stderr[:500]}"})
        return result.stdout[:50000]
    except subprocess.TimeoutExpired:
        return json.dumps({"error": f"Tool {tool_name} timed out after 120s"})
    except Exception as e:
        return json.dumps({"error": str(e)})


def call_bedrock(messages, system_prompt):
    bedrock_tools = [{"toolSpec": {"name": t["name"], "description": t["description"], "inputSchema": {"json": t["input_schema"]}}} for t in TOOL_DEFINITIONS]

    response = bedrock.converse(
        modelId=MODEL_ID,
        system=[{"text": system_prompt}],
        messages=messages,
        toolConfig={"tools": bedrock_tools},
        inferenceConfig={"maxTokens": 4096, "temperature": 0.1}
    )
    return response


def process_chat(user_message: str) -> dict:
    system_prompt = load_system_prompt()

    conversation_history.append({
        "role": "user",
        "content": [{"text": user_message}]
    })

    citations = []
    max_turns = 10
    turn = 0

    while turn < max_turns:
        turn += 1
        response = call_bedrock(conversation_history, system_prompt)
        output = response["output"]["message"]
        stop_reason = response["stopReason"]

        conversation_history.append(output)

        if stop_reason == "tool_use":
            tool_results = []
            for block in output["content"]:
                if "toolUse" in block:
                    tool_use = block["toolUse"]
                    tool_name = tool_use["name"]
                    tool_input = tool_use["input"]
                    tool_id = tool_use["toolUseId"]

                    result_str = run_tool(tool_name, tool_input)

                    try:
                        result_data = json.loads(result_str)
                        if "source" in result_data:
                            citations.append({
                                "tool": tool_name,
                                "input": tool_input,
                                "source": result_data["source"]
                            })
                        elif "sources" in result_data:
                            citations.append({
                                "tool": tool_name,
                                "input": tool_input,
                                "source": result_data["sources"]
                            })
                    except json.JSONDecodeError:
                        pass

                    tool_results.append({
                        "toolResult": {
                            "toolUseId": tool_id,
                            "content": [{"text": result_str}]
                        }
                    })

            conversation_history.append({
                "role": "user",
                "content": tool_results
            })
        else:
            text_parts = []
            for block in output["content"]:
                if "text" in block:
                    text_parts.append(block["text"])
            return {
                "response": "\n".join(text_parts),
                "citations": citations,
                "tool_calls": turn - 1
            }

    return {"response": "I reached the maximum number of tool calls. Please try a more specific question.", "citations": citations, "tool_calls": turn}


def get_fleet_health():
    profiles = json.loads(run_tool("get_pump_profile", {"pump_id": "all"}))
    fleet = []
    for pump in profiles.get("pumps", []):
        pid = pump["pump_id"]
        vib = json.loads(run_tool("check_vibration_zone", {"pump_id": pid}))
        fleet.append({
            "pump_id": pid,
            "model": pump["model"],
            "manufacturer": pump["manufacturer"],
            "service_fluid": pump["service_fluid"],
            "criticality": pump["criticality_rating"],
            "vibration_zone": vib.get("overall_zone", "?"),
            "vibration_status": vib.get("overall_status", "Unknown"),
            "bearing_temp_c": vib.get("bearing_temp_c"),
        })
    return fleet


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    citations: list
    tool_calls: int = 0


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        result = process_chat(req.message)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        conversation_history.clear()
        return ChatResponse(response=f"Error: {e}", citations=[], tool_calls=0)


@app.post("/api/reset")
def reset_conversation():
    conversation_history.clear()
    return {"status": "ok"}


@app.get("/api/fleet")
def fleet():
    return get_fleet_health()


@app.get("/api/pump/{pump_id}")
def pump_detail(pump_id: str):
    profile = json.loads(run_tool("get_pump_profile", {"pump_id": pump_id}))
    vib = json.loads(run_tool("check_vibration_zone", {"pump_id": pump_id}))
    alarms = json.loads(run_tool("search_alarms", {"pump_id": pump_id}))
    maintenance = json.loads(run_tool("get_maintenance_history", {"pump_id": pump_id}))
    return {
        "profile": profile,
        "vibration": vib,
        "recent_alarms": alarms,
        "maintenance_history": maintenance,
    }


@app.get("/")
def root():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text())
    return HTMLResponse("<h1>CDU Pump Health Monitor</h1><p>Frontend not found.</p>")


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn
    print("Starting CDU Pump Health Monitor on port 3000...")
    print("Open http://localhost:3000 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=3000)
