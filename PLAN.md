# Refinery Predictive Maintenance Agent — Architecture Plan

## The Problem

A crude distillation unit (CDU) runs 12 centrifugal pumps continuously, 24/7/365. Each pump has bearing temperature, vibration, pressure, flow, and motor sensors reporting every 5 minutes. When a pump fails unexpectedly, the downstream unit trips and the refinery loses $50K–$200K per hour of unplanned downtime.

The data exists. The sensors are there. But no one has time to watch 144 sensor streams simultaneously. Maintenance teams run on time-based schedules (replace every 12 months regardless of condition) or react after failure. Both approaches are wasteful and dangerous.

**This agent bridges the gap:** condition-based, AI-driven, evidence-grounded predictive maintenance.

---

## Who It Answers and What It Answers

**Primary user:** CDU shift engineer / maintenance planner

### Core Questions

| # | Question | Why It Matters |
|---|----------|---------------|
| 1 | "What's the health of pump P-07 right now?" | Real-time condition assessment with ISO 10816 zone classification |
| 2 | "Which pumps are at highest risk of failure?" | Prioritized risk ranking across the fleet — drives work order scheduling |
| 3 | "P-03 vibration is climbing — what's the diagnosis?" | Match sensor signature to failure mode, cite the OEM manual, recommend action |
| 4 | "Show me what happened before EVT-002 (P-03 cavitation)" | Retrospective root-cause analysis with sensor evidence trail |
| 5 | "Do we have parts to fix P-08's bearings? What's the cost?" | Spare parts check + repair-vs-failure cost comparison |
| 6 | "What maintenance should we plan this week?" | Proactive scheduling based on condition trends + lead times |
| 7 | "Compare P-01 and P-07 — same model, why different health?" | Fleet benchmarking across same-model pumps |

### Grounding Requirement

Every number and claim the application states must trace back to a specific file, row, or passage in the data. An answer that sounds expert but cites nothing is worth less than a narrower answer that shows its evidence. If the data doesn't support a conclusion, the right behavior is to say so, not to fill the gap.

---

## Data Inventory

### Sensor & Event Data

| File | Rows | Description | Key Columns |
|------|------|-------------|-------------|
| `sensor_timeseries.csv` | 625,536 | 5-min readings, 12 pumps, 6 months (2025-09-01 → 2026-02-28) | timestamp, pump_id, bearing_temp_c, vibration_{x,y,axial}_mms, suction/discharge/differential_pressure_psi, flow_rate_m3hr, motor_current_amps, motor_speed_rpm, seal_leak_detected, label |
| `failure_event_log.csv` | 8 | Labeled failures across 6 pumps | event_id, pump_id, failure_start_ts, failure_mode, failure_ts, downtime_hrs, repair_cost_usd |
| `failure_mode_reference.csv` | 5 | Sensor signature → failure mode lookup | failure_mode, primary_sensor_signature, secondary_indicators, typical_lead_time_hrs, recommended_action |
| `alarm_history.csv` | 200 | Historical alarms across 12 pumps | alarm_id, pump_id, timestamp, alarm_type, severity, trigger_value, duration_minutes, acknowledged |

### Maintenance Records

| File | Records | Description | Key Columns |
|------|---------|-------------|-------------|
| `pump_maintenance_history.json` | 59 | Completed service records (WO-00001 style IDs) | pump_id, work_order_id, date, work_type, technician_notes, parts_replaced, lubricant_type, hours_since_last_service |
| `maintenance_work_orders.csv` | 120 | CMMS work orders (WO-0001 style IDs) | work_order_id, pump_id, date, wo_type, status, description, cost_usd, labor_hours, shift |

> **WARNING:** These are two independent work-order logs, not the same list twice. The JSON uses `WO-00001`-style IDs; the CSV uses `WO-0001`-style IDs. There is zero overlap. Never join on `work_order_id`. Match on `pump_id` + nearby dates instead.

### Operating Context

| File | Rows | Description |
|------|------|-------------|
| `pump_metadata.csv` | 12 | Pump specs, model, manufacturer, criticality, operating envelope |
| `vibration_baselines.csv` | 72 | Per-pump per-axis baselines + alert/alarm/trip thresholds (ISO 10816-7) |
| `operating_schedule.csv` | 2,160 | Daily duty state (Running/Standby/Maintenance), load %, process assignment |
| `spare_parts_inventory.csv` | 12 | Stock levels, reorder points, lead times, compatible pumps |
| `cost_tracking.csv` | 288 | Monthly maintenance/energy/parts cost per pump |

### OEM Manuals (`data/reference_docs/`)

| Manual | Applicable Pumps | Key Content |
|--------|-----------------|-------------|
| `flowserve_pvxm3_manual.md` | P-01, P-02, P-07, P-10 | Crude oil service, SKF 6312 bearings, double seal, §2.2 bearing temp limits, §2.3 vibration limits (ISO 10816-3), §7 FMEA table, §8 troubleshooting tree |
| `ksb_etanorm_manual.md` | P-05, P-06, P-09, P-12 | Diesel/fuel oil service, NSK 6310 bearings, back pull-out design, §3.4 misalignment root cause, §7 FMEA |
| `sulzer_cpt50_manual.md` | P-03, P-04, P-08, P-11 | Naphtha/kerosene service, FAG 6308 bearings, semi-open impeller, ATEX classified, lower temp thresholds, §2.4 cavitation sensitivity |

### Pump-to-Model Mapping

| Manufacturer | Model | Pumps | Service Fluid |
|-------------|-------|-------|---------------|
| Flowserve | PVXM-3 | P-01, P-02, P-07, P-10 | Crude oil |
| Sulzer | CPT-50 | P-03, P-04, P-08, P-11 | Naphtha / Kerosene |
| KSB | Etanorm 100-080 | P-05, P-06, P-09, P-12 | Diesel / Fuel oil |

### Known Failure Events (Ground Truth)

| Event | Pump | Mode | Failure Date | Downtime | Cost |
|-------|------|------|-------------|----------|------|
| EVT-001 | P-01 | bearing_wear | 2025-09-26 | 5.7 hrs | $39,849 |
| EVT-002 | P-03 | cavitation | 2025-10-19 | 20.3 hrs | $57,846 |
| EVT-003 | P-07 | bearing_wear | 2025-11-12 | 14.7 hrs | $16,241 |
| EVT-004 | P-05 | seal_failure | 2025-12-05 | 6.6 hrs | $39,148 |
| EVT-005 | P-10 | misalignment | 2025-12-28 | 22.9 hrs | $18,821 |
| EVT-006 | P-02 | impeller_damage | 2026-01-19 | 9.3 hrs | $47,753 |
| EVT-007 | P-08 | bearing_wear | 2026-02-10 | 12.5 hrs | $21,880 |
| EVT-008 | P-11 | seal_failure | 2026-02-23 | 22.6 hrs | $57,497 |

The `label` column in `sensor_timeseries.csv` marks `pre_failure` windows leading into each event — this is the ground truth for validating anomaly detection.

### Failure Mode Signatures

| Mode | Primary Signal | Secondary Indicators | Lead Time | ISO Zone |
|------|---------------|---------------------|-----------|----------|
| bearing_wear | bearing_temp_c rising >2°C/hr | vibration_x elevated, motor_current rising | 24 hrs | C |
| seal_failure | seal_leak_detected=True | suction_pressure dropping, flow declining | 8 hrs | B |
| cavitation | suction_pressure <15 psi | vibration_axial elevated, flow erratic | 4 hrs | C |
| impeller_damage | differential_pressure declining | flow declining, motor_current dropping | 48 hrs | B |
| misalignment | vibration_axial >3.5 mm/s | bearing_temp elevated, motor_current elevated | 72 hrs | C |

---

## Multi-Agent Architecture

### Pattern: Supervisor-Router with Specialist Agents

```
                    ┌─────────────────────┐
                    │   Orchestrator      │
                    │   (Router Agent)    │
                    └──────┬──────────────┘
                           │ routes by intent
          ┌────────────────┼────────────────┬──────────────────┐
          ▼                ▼                ▼                  ▼
  ┌───────────────┐ ┌──────────────┐ ┌──────────────┐ ┌───────────────┐
  │ Sensor        │ │ Diagnostician│ │ Maintenance  │ │ Fleet         │
  │ Analyst       │ │              │ │ Advisor      │ │ Overview      │
  └───────────────┘ └──────────────┘ └──────────────┘ └───────────────┘
        │                  │                │                  │
        ▼                  ▼                ▼                  ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │                     Tool Layer (Python scripts)                 │
  │  query_sensors │ check_baselines │ search_manuals │ check_parts │
  └─────────────────────────────────────────────────────────────────┘
        │
        ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │                     Data Layer (CSV / JSON / MD files)          │
  │  sensor_timeseries │ failure_event_log │ pump_metadata │ OEM   │
  └─────────────────────────────────────────────────────────────────┘
```

### Agent Responsibilities

#### 1. Orchestrator Agent (Router)

- Classifies user intent: health check, diagnosis, planning, retrospective, fleet comparison
- Routes to the right specialist(s) — may fan out to multiple agents in parallel
- Merges responses, ensures every claim has a citation
- Falls back to "data doesn't support this" when evidence is insufficient

#### 2. Sensor Analyst Agent

- Queries `sensor_timeseries.csv` via Python tool (chunked reads, never full-file load)
- Computes: current values, rolling averages (1hr/4hr/24hr), rate-of-change, trend direction
- Classifies vibration into ISO 10816 zones (A/B/C/D) using `vibration_baselines.csv` thresholds
- Classifies bearing temp against OEM thresholds (per pump model — Sulzer has lower limits)
- Detects anomalies: values crossing alert/alarm/trip thresholds
- **Cites:** timestamp ranges, specific sensor columns, baseline file rows

#### 3. Diagnostician Agent

- Takes anomaly signals from Sensor Analyst
- Matches sensor patterns against `failure_mode_reference.csv` (5 failure modes with primary + secondary signatures)
- Cross-references with OEM manual troubleshooting trees (Flowserve §7 FMEA, Sulzer §6, KSB §7)
- Checks `alarm_history.csv` for corroborating alarms near the anomaly window
- Outputs: diagnosed failure mode, confidence level, supporting evidence, estimated lead time to failure
- **Cites:** failure_mode_reference.csv row, OEM manual section + line, alarm IDs

#### 4. Maintenance Advisor Agent

- Queries `pump_maintenance_history.json` (59 records) for service history
- Queries `maintenance_work_orders.csv` (120 records) for pending/scheduled work
- Matches the two logs by `pump_id` + date proximity (never by work_order_id)
- Checks `spare_parts_inventory.csv` for part availability and lead times
- Computes cost impact: proactive repair cost vs. expected failure cost (using `cost_tracking.csv` + `failure_event_log.csv` known repair costs)
- Recommends: repair now / schedule within N days / monitor — with cost justification
- **Cites:** work order IDs, part numbers + stock levels, cost rows

#### 5. Fleet Overview Agent

- Aggregates health scores across all 12 pumps
- Groups by manufacturer (Flowserve / Sulzer / KSB)
- Ranks by risk using weighted scoring: vibration zone + temp trend + alarm frequency + time since maintenance
- Identifies pumps with same model but divergent health for benchmarking
- Checks `operating_schedule.csv` for duty state (Running/Standby/Maintenance) and load %
- **Cites:** pump_metadata.csv, operating_schedule.csv rows

---

## Tool Definitions

Each tool is a standalone Python script. The sensor tool uses chunked/filtered reads for the 60MB file.

| Tool | Input | Output | Data Source |
|------|-------|--------|-------------|
| `query_sensors` | pump_id, time_range, metrics, aggregation (raw/hourly/daily) | Time series values + summary stats | `sensor_timeseries.csv` |
| `get_pump_profile` | pump_id | Metadata, operating envelope, OEM model, criticality | `pump_metadata.csv` |
| `check_vibration_zone` | pump_id, timestamp or time_range | ISO 10816 zone per axis, current vs. baseline, trend | `vibration_baselines.csv` + sensor data |
| `classify_failure_mode` | pump_id, anomaly_signals dict | Matched failure mode + confidence + evidence chain | `failure_mode_reference.csv` |
| `search_alarms` | pump_id, time_range, alarm_type (optional) | Matching alarm events with severity | `alarm_history.csv` |
| `get_maintenance_history` | pump_id | Merged timeline from both logs, sorted by date | `pump_maintenance_history.json` + `maintenance_work_orders.csv` |
| `check_spare_parts` | part_category or pump_id | Stock level, lead time, compatible pumps, reorder status | `spare_parts_inventory.csv` |
| `compute_cost` | pump_id, scenario (repair/failure/comparison) | Cost breakdown, what-if analysis | `cost_tracking.csv` + `failure_event_log.csv` |
| `search_oem_manual` | pump_model, topic (bearing/seal/vibration/troubleshooting) | Relevant manual section text with line numbers | `reference_docs/*.md` |
| `get_operating_status` | pump_id, date_range | Duty state, load %, run hours, process assignment | `operating_schedule.csv` |

---

## UI Design

### Layout: Chat + Fleet Dashboard + Evidence Panel

```
┌─────────────────────────────────────────────────────────────────────┐
│  CDU Pump Health Monitor                              [Fleet View]  │
├───────────────────────────────┬─────────────────────────────────────┤
│                               │                                     │
│   FLEET HEALTH OVERVIEW       │   EVIDENCE PANEL                    │
│                               │                                     │
│   P-01 ●● Normal   [Zone B]  │   ┌─────────────────────────────┐   │
│   P-02 ●● Normal   [Zone B]  │   │ Sensor Trend: P-07          │   │
│   P-03 ●○ Watch    [Zone B]  │   │ bearing_temp_c              │   │
│   P-04 ●● Normal   [Zone A]  │   │ ╱──────╲                    │   │
│   P-05 ●● Normal   [Zone B]  │   │╱        ╲___/▔▔▔↗           │   │
│   P-06 ●● Normal   [Zone A]  │   │ Sep   Oct   Nov   Dec       │   │
│   P-07 ◉◉ WARNING  [Zone C]  │   │ Source: sensor_timeseries   │   │
│   P-08 ●○ Watch    [Zone B]  │   │ Rows: 360,289 - 361,152    │   │
│   P-09 ●● Normal   [Zone A]  │   └─────────────────────────────┘   │
│   P-10 ●● Normal   [Zone B]  │                                     │
│   P-11 ●○ Watch    [Zone B]  │   ┌─────────────────────────────┐   │
│   P-12 ●● Normal   [Zone A]  │   │ OEM Reference               │   │
│                               │   │ Flowserve PVXM-3 §2.2:     │   │
│   [3 Flowserve] [4 Sulzer]   │   │ "Warning threshold 80-85°C  │   │
│   [4 KSB]                    │   │  Inspect bearing within 4h"  │   │
│                               │   │ Source: flowserve_pvxm3.md  │   │
├───────────────────────────────┤   │ Line: 47-48                 │   │
│                               │   └─────────────────────────────┘   │
│   CHAT                        │                                     │
│                               │   ┌─────────────────────────────┐   │
│   You: What's wrong with P-07?│   │ Spare Parts                 │   │
│                               │   │ BRG-6305: 18 in stock ✓     │   │
│   Agent: P-07 shows bearing   │   │ Lead time: 33 days          │   │
│   wear signature. Bearing     │   │ Compatible: P-01,02,05,08.. │   │
│   temp rising at 2.3°C/hr     │   │ Source: spare_parts_inv.csv │   │
│   (exceeds 2°C/hr threshold   │   │ Row: 2                      │   │
│   per Flowserve §2.2).        │   └─────────────────────────────┘   │
│   Vibration now in Zone C     │                                     │
│   (5.2 mm/s vs 4.5 limit).   │                                     │
│                               │                                     │
│   Diagnosis: bearing_wear     │                                     │
│   Confidence: HIGH            │                                     │
│   Lead time: ~24 hrs          │                                     │
│   [See evidence panel →]      │                                     │
│                               │                                     │
│   > Ask a question...         │                                     │
└───────────────────────────────┴─────────────────────────────────────┘
```

### UI Components

| Component | Purpose |
|-----------|---------|
| **Fleet Health Panel** (top-left) | Color-coded health status for all 12 pumps. ISO 10816 zone badge. Click to drill into individual pump. Grouped by manufacturer. |
| **Chat Panel** (bottom-left) | Natural language Q&A. Supports all 7 core questions. Every response includes inline citations like `[sensor_timeseries.csv, rows 360289-361152]`. |
| **Evidence Panel** (right) | Auto-populates when agent responds. Shows: sensor trend charts, OEM manual excerpts (with section + line), alarm timeline, spare parts table, cost breakdown. Each card shows its source file and row/line numbers. |
| **Pump Detail View** | Expanded view for one pump: full sensor dashboard, maintenance timeline, alarm history, operating schedule. Accessed by clicking a pump in fleet view. |

### UI Principles

1. Every number on screen has a visible source citation
2. Charts show raw data points, not just summaries — the user can verify
3. OEM manual excerpts are shown verbatim with section numbers
4. When data is insufficient, the UI shows "Insufficient data" not a guess
5. Color coding follows ISO 10816: Green (A) → Blue (B) → Yellow (C) → Red (D)

---

## Tech Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Frontend | Next.js + React + Tailwind CSS | Fast to build, good charting libraries (Recharts), responsive |
| Agent framework | Claude Agent SDK (Strands) or direct Bedrock Converse API | Multi-agent orchestration with tool use |
| Tool scripts | Python 3 (csv module for chunked reads, no heavy deps) | Zero-dependency, reads the provided data files directly |
| Charts | Recharts or Chart.js | Time series visualization for sensor data |
| Deployment | Amazon Bedrock AgentCore | Required for Track 2 |
| Model | Claude Sonnet on Bedrock | Fast enough for interactive, strong reasoning for diagnosis |

### AgentCore Modules

| Module | Purpose |
|--------|---------|
| **Runtime** | Deploy the multi-agent system as a managed endpoint |
| **Memory** | Store conversation context and pump state across sessions |
| **Gateway** | API endpoint for the web frontend to call the agent |
| **Identity** | Auth for maintenance planner users |

---

## Implementation Phases

### Phase 1: Core Tools (2 hours) — Foundation

Build the Python tool scripts that all agents depend on.

- [ ] `tools/query_sensors.py` — Chunked CSV reader for sensor_timeseries.csv. Supports: filter by pump_id + time range, select specific metrics, aggregate (raw / hourly mean / daily mean), compute rate-of-change. Returns JSON with row ranges for citation.
- [ ] `tools/get_pump_profile.py` — Reads pump_metadata.csv, parses operating_envelope_json, returns full pump profile with OEM manual path.
- [ ] `tools/check_vibration_zone.py` — Reads vibration_baselines.csv, compares current sensor readings against per-pump per-axis thresholds, classifies into ISO 10816 zones A/B/C/D.
- [ ] `tools/classify_failure_mode.py` — Reads failure_mode_reference.csv, takes a dict of anomaly signals, matches against the 5 known failure mode signatures, returns ranked matches with confidence.
- [ ] `tools/search_alarms.py` — Filters alarm_history.csv by pump_id, time range, alarm type.
- [ ] `tools/get_maintenance_history.py` — Reads both maintenance logs (JSON + CSV), merges by pump_id + date, returns sorted timeline. Never joins on work_order_id.
- [ ] `tools/check_spare_parts.py` — Reads spare_parts_inventory.csv, filters by pump compatibility or part category.
- [ ] `tools/compute_cost.py` — Reads cost_tracking.csv + failure_event_log.csv, computes repair-vs-failure cost comparison.
- [ ] `tools/search_oem_manual.py` — Reads the markdown OEM manuals, searches by section/keyword, returns text with line numbers.
- [ ] `tools/get_operating_status.py` — Reads operating_schedule.csv, returns duty state and load for a pump.

### Phase 2: Single Agent MVP (1.5 hours) — First Demoable Version

- [ ] Build a single agent with all 10 tools, a system prompt that enforces citation requirements
- [ ] Test against all 7 core questions
- [ ] Validate: agent correctly identifies the 8 known failures when asked about them retrospectively
- [ ] Validate: agent cites specific files, rows, and manual sections in every answer

### Phase 3: Evidence Grounding (1 hour) — Scoring Differentiator

- [ ] Add structured citation format to every tool response: `{"source": "file.csv", "rows": [start, end], "columns": [...]}` 
- [ ] Agent system prompt enforces: no claim without citation, say "insufficient data" when appropriate
- [ ] Test edge cases: ask about a pump with no failures, ask for a prediction the data can't support
- [ ] Validate against all 8 failure events: can the agent reconstruct the pre_failure sensor trail?

### Phase 4: Web UI (2 hours) — Visual Impact

- [ ] Fleet health dashboard with 12 pump cards (color-coded by risk)
- [ ] Chat interface with streaming responses
- [ ] Evidence panel that renders citations: sensor charts, OEM excerpts, data tables
- [ ] Pump detail view: sensor time series, alarm timeline, maintenance history
- [ ] Use port 3000 (NOT 8080 — that's the editor)

### Phase 5: Multi-Agent Split (1.5 hours) — Architectural Depth

- [ ] Split single agent into Orchestrator + 4 specialists
- [ ] Orchestrator routes by intent, fans out to specialists in parallel where possible
- [ ] Each specialist has only the tools it needs (least privilege)
- [ ] Orchestrator merges responses and ensures citation completeness

### Phase 6: AgentCore Deployment (1 hour) — Track 2

- [ ] Package agent as AgentCore-compatible runtime
- [ ] Deploy via `agentcore dev --port 3000` for local testing
- [ ] Deploy to Bedrock AgentCore Runtime for production endpoint
- [ ] Connect frontend to AgentCore Gateway

---

## Example Agent Reasoning Chains

### Q: "What's the health of P-07 right now?"

```
Orchestrator → Sensor Analyst + Fleet Overview (parallel)

Sensor Analyst:
  1. query_sensors(pump_id="P-07", time_range="last_24h", metrics="all")
  2. check_vibration_zone(pump_id="P-07")
  3. get_pump_profile(pump_id="P-07")  → Flowserve PVXM-3
  
  Findings:
  - bearing_temp_c: 78.3°C, rising 1.8°C/hr [sensor_timeseries.csv, rows 620100-620388]
  - vibration_x: 4.8 mm/s → Zone C [vibration_baselines.csv, row 37: P-07 DE Horiz baseline 2.02, alert 3.03, alarm 5.05]
  - Per Flowserve manual §2.2: 78°C is "Warning threshold — inspect within 4 hours" [flowserve_pvxm3_manual.md, line 47]

Fleet Overview:
  - P-07 last maintenance: 2025-06-18 [pump_metadata.csv, row 7]
  - Currently Running at 82% load [operating_schedule.csv, latest P-07 row]
  - 3 alarms in last 30 days [alarm_history.csv, ALM-00054, ALM-00081, ALM-00130]
```

### Q: "What happened before the P-03 cavitation failure?"

```
Orchestrator → Sensor Analyst + Diagnostician (sequential)

Sensor Analyst:
  1. query_sensors(pump_id="P-03", time_range="2025-10-15 to 2025-10-19", metrics="all", aggregation="hourly")
  2. Result: suction_pressure dropped from 42 psi to 12 psi over 72 hours
     [sensor_timeseries.csv, rows 115200-116352, label transitions: normal → pre_failure → failure]

Diagnostician:
  1. classify_failure_mode(pump_id="P-03", signals={suction_pressure: "declining <15psi", vibration_axial: "elevated", flow: "erratic"})
  2. Match: cavitation (confidence: HIGH) [failure_mode_reference.csv, row 3]
  3. search_oem_manual(model="Sulzer CPT-50", topic="cavitation")
     → §2.4: "Min suction pressure 1.5 bar absolute... cavitation indicators: crackling noise, vibration increase, flow instability" [sulzer_cpt50_manual.md, lines 64-67]
  4. search_alarms(pump_id="P-03", time_range="2025-10-15 to 2025-10-19")
     → ALM-00010: Cavitation Detected, Alarm severity, 2025-10-15 03:00 [alarm_history.csv, row 10]
  
  Conclusion: Cavitation caused by suction pressure drop below 15 psi. 
  Lead time was ~4 hours per failure_mode_reference.csv.
  The pre_failure label in sensor data began at 2025-10-18T20:00 (failure_start_ts in failure_event_log.csv, EVT-002).
```

---

## Critical Implementation Notes

1. **sensor_timeseries.csv is ~60MB** — Never load it all into memory or paste it into a prompt. Always query via Python script with filters. Use chunked reads (pandas `read_csv` with `chunksize` or Python `csv` module with row filtering).

2. **Two maintenance logs are independent** — `pump_maintenance_history.json` uses `WO-00001` IDs; `maintenance_work_orders.csv` uses `WO-0001` IDs. Zero overlap. Match on `pump_id` + date proximity only.

3. **The `label` column is ground truth** — Values are `normal`, `pre_failure`, `failure`. Use this to validate that anomaly detection catches the lead-up to all 8 known failures. The `failure_start_ts` in `failure_event_log.csv` marks when `pre_failure` begins.

4. **OEM temp thresholds vary by model** — Sulzer CPT-50 (naphtha service) has lower alarm thresholds (80°C) than Flowserve PVXM-3 (85°C) due to lower flash point. The agent must use model-specific limits, not a universal threshold.

5. **Port 8080 is the editor** — Use port 3000 for any local dev server or agent endpoint.

6. **Citation format** — Every tool response should include source metadata: `{source_file, row_range, columns_used}`. The agent's final response to the user should include human-readable citations like `[sensor_timeseries.csv, P-07, 2025-11-11 00:00–23:55, rows 360289–361152]`.
