"""Shared configuration — single source of truth for all tools and the agent.

Loads pump metadata, thresholds, and mappings from CSV files at import time.
No hard-coded pump IDs, model names, or thresholds anywhere else in the codebase.
"""

import csv
import json
import os
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).parent / "data"))
MODEL_ID = os.environ.get("MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
SERVER_PORT = int(os.environ.get("PORT", "3000"))
MAX_TOOL_OUTPUT_CHARS = int(os.environ.get("MAX_TOOL_OUTPUT_CHARS", "50000"))
MAX_AGENT_TURNS = int(os.environ.get("MAX_AGENT_TURNS", "10"))
BEDROCK_MAX_TOKENS = int(os.environ.get("BEDROCK_MAX_TOKENS", "4096"))
BEDROCK_TEMPERATURE = float(os.environ.get("BEDROCK_TEMPERATURE", "0.1"))
SENSOR_INTERVAL_MINUTES = int(os.environ.get("SENSOR_INTERVAL_MINUTES", "5"))

# Scoring weights for failure classification
PRIMARY_SIGNAL_WEIGHT = 3
SECONDARY_SIGNAL_WEIGHT = 1

# Trend detection
TREND_THRESHOLD = 0.5
MIN_READINGS_FOR_RATE = 12

# Vibration zone A/B boundary multiplier
ZONE_AB_MULTIPLIER = 1.2

# Default lookback windows
DEFAULT_LOOKBACK_HOURS = 4
TIMESTAMP_WINDOW_HOURS = 1

# Data truncation
RAW_DATA_DISPLAY_LIMIT = 200
RAW_DATA_HEAD = 50
RAW_DATA_TAIL = 50

# OEM manual search
MANUAL_TOP_K = 5
MANUAL_MAX_SECTION_CHARS = 2000


def _get_now() -> str:
    """Return current timestamp, or end of dataset if DATA_DIR points to static data."""
    override = os.environ.get("SIMULATED_NOW")
    if override:
        return override
    latest_file = DATA_DIR / "sensor_timeseries.csv"
    if latest_file.exists():
        with open(latest_file) as f:
            for line in f:
                pass
            last_ts = line.split(",")[0]
            try:
                datetime.strptime(last_ts, "%Y-%m-%dT%H:%M:%S")
                return last_ts
            except ValueError:
                pass
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


SIMULATED_NOW = _get_now()


def _load_pump_metadata() -> dict:
    """Load pump_metadata.csv into a dict keyed by pump_id."""
    pumps = {}
    meta_file = DATA_DIR / "pump_metadata.csv"
    with open(meta_file) as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            pid = row["pump_id"]
            pumps[pid] = {**row, "_row": row_num}
    return pumps


PUMP_METADATA = _load_pump_metadata()
ALL_PUMP_IDS = sorted(PUMP_METADATA.keys())

MANUAL_MAP = {
    "Flowserve PVXM-3": "flowserve_pvxm3_manual.md",
    "Sulzer CPT-50": "sulzer_cpt50_manual.md",
    "KSB Etanorm 100-080": "ksb_etanorm_manual.md",
}

BEARING_TEMP_LIMITS = {
    "Flowserve PVXM-3": {
        "normal_max": 65, "elevated_max": 80,
        "warning_max": 85, "alarm_max": 95, "rate_alert_c_per_hr": 2.0,
    },
    "Sulzer CPT-50": {
        "normal_max": 60, "elevated_max": 75,
        "warning_max": 80, "alarm_max": 90, "rate_alert_c_per_hr": 2.0,
    },
    "KSB Etanorm 100-080": {
        "normal_max": 65, "elevated_max": 78,
        "warning_max": 85, "alarm_max": 95, "rate_alert_c_per_hr": 2.0,
    },
}


def pump_model(pump_id: str) -> str:
    return PUMP_METADATA.get(pump_id, {}).get("model", "Unknown")


def pump_manual(pump_id: str) -> str:
    model = pump_model(pump_id)
    return MANUAL_MAP.get(model, "unknown_manual.md")


def pump_bearing_limits(pump_id: str) -> dict:
    model = pump_model(pump_id)
    return BEARING_TEMP_LIMITS.get(model, BEARING_TEMP_LIMITS["Flowserve PVXM-3"])


PROACTIVE_COST_ESTIMATES = {
    "bearing_wear":     {"cost_usd": 3500, "downtime_hrs": 4},
    "seal_failure":     {"cost_usd": 5000, "downtime_hrs": 6},
    "cavitation":       {"cost_usd": 1500, "downtime_hrs": 2},
    "impeller_damage":  {"cost_usd": 8000, "downtime_hrs": 8},
    "misalignment":     {"cost_usd": 2000, "downtime_hrs": 3},
}
