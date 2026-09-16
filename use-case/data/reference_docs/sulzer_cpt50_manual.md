# Sulzer CPT-50 Centrifugal Pump
## Operation, Maintenance & Troubleshooting Manual
### Applicable Units: P-03, P-04, P-08, P-11 (Naphtha / Kerosene Service)

---

## 1. Pump Specifications

| Parameter | Value |
|---|---|
| Model | CPT-50 |
| Type | Single-stage, between-bearings, centrifugal |
| Service fluid | Naphtha / light hydrocarbons / kerosene |
| Design flow | 80 m³/hr |
| Design head | 60 m |
| Rated power | 22 kW |
| Rated speed | 2,950 RPM |
| Impeller diameter | 240 mm |
| Impeller type | Semi-open, 4-vane |
| Casing material | 316L stainless steel (naphtha service) |
| Impeller material | Duplex stainless steel 2205 |
| Shaft material | 316 stainless steel |
| Bearing type | FAG 6308 (both ends) |
| Seal type | Mechanical single seal, API Plan 11 |
| NPSH required | 2.8 m at design flow |
| Maximum allowable temperature | 120°C |
| Maximum allowable pressure | 10 bar |
| ATEX classification | II 2G Ex d IIB T3 (naphtha service) |

---

## 2. Normal Operating Envelope

### 2.1 Flow & Head Envelope
- Minimum continuous flow: 32 m³/hr (40% of BEP)
- Best Efficiency Point (BEP): 80 m³/hr at 60 m head
- Maximum continuous flow: 92 m³/hr (115% of BEP)

**CAUTION — Naphtha Service**: Operating below minimum flow causes rapid temperature rise in the pump casing. Naphtha flash point is 38°C — overheating creates fire and explosion risk. Always maintain minimum flow or open recirculation line.

### 2.2 Bearing Temperature Limits

| Condition | Bearing Temp (°C) | Action |
|---|---|---|
| Normal operation | 40–60°C | No action required |
| Elevated — monitor | 60–75°C | Check lubrication; increase monitoring |
| Warning threshold | 75–80°C | Inspect within 4 hours |
| Alarm threshold | >80°C | Reduce load; inspect immediately |
| Failure threshold | >90°C | Immediate shutdown |

**Note for naphtha service**: Lower alarm thresholds than crude service due to lower fluid flash point and lighter bearing loads.

### 2.3 Vibration Limits (ISO 10816-3, Group 2)

| Zone | Vibration (mm/s RMS) | Condition | Action |
|---|---|---|---|
| A | 0 – 2.3 | New or recently overhauled | Normal |
| B | 2.3 – 4.5 | Acceptable long-term | Monitor |
| C | 4.5 – 7.1 | Unsatisfactory | Plan maintenance |
| D | > 7.1 | Dangerous | Shutdown immediately |

**Axial vibration note**: CPT-50 semi-open impeller is sensitive to axial thrust. Axial vibration >3.5 mm/s RMS indicates impeller-to-casing clearance issue or misalignment — inspect within 48 hours.

### 2.4 Suction Pressure & Cavitation
- Minimum suction pressure: 1.5 bar absolute (to prevent cavitation)
- Cavitation indicators: crackling/popping noise, vibration increase, flow instability
- If suction pressure <1.2 bar: shutdown risk — check suction line for blockage or vapor lock

---

## 3. Bearing Maintenance

### 3.1 Lubrication Specifications
- Lubricant: FAG Arcanol LOAD150 grease (NLGI Grade 2)
- Alternative: Shell Gadus S2 V220
- Relubrication interval: every 2,500 operating hours
- Grease quantity: 12 g per bearing
- **Do not mix grease types** — incompatible thickeners cause bearing failure

### 3.2 Bearing Replacement Criteria
- Temperature consistently >75°C despite fresh lubrication
- Vibration Zone C or D
- Audible noise: grinding or irregular knocking
- After any temperature excursion >90°C
- Scheduled replacement: every 25,000 operating hours or 3 years

### 3.3 FAG 6308 Bearing Data
- Dynamic load rating (C): 41.0 kN
- Static load rating (C0): 24.0 kN
- Limiting speed (grease): 7,500 RPM
- L10 life at design conditions (P ≈ 4.2 kN, n = 2,950 RPM): ~38,000 hours

### 3.4 Bearing Replacement Procedure
1. Isolate pump; purge naphtha from casing (nitrogen purge — minimum 3 volumes)
2. Verify LEL <10% before opening any flanges (gas detector required)
3. Remove bearing housing end covers
4. Extract shaft; remove bearings using hydraulic puller
5. Clean shaft journal; inspect for scoring (replace shaft if scoring >0.05 mm deep)
6. Heat new FAG 6308 to 80°C using induction heater; press onto shaft
7. Allow to cool; verify zero axial play
8. Repack with 12 g Arcanol LOAD150
9. Reassemble; align to ≤ 0.05 mm TIR
10. Nitrogen purge casing before introducing naphtha

---

## 4. Mechanical Seal Maintenance

### 4.1 Seal System — API Plan 11 (Flush from Discharge)
- Flush flow: 2–4 L/min from pump discharge to seal chamber
- Flush line orifice: 3 mm (do not enlarge — controls flush rate)
- Seal chamber pressure: approximately 0.5 bar above suction pressure
- Seal face material: Silicon carbide vs. carbon graphite

### 4.2 Seal Failure Indicators
- Visible naphtha leakage at seal housing: immediate shutdown (fire hazard)
- Seal leak proximity sensor activated: shutdown within 5 minutes
- Flush line flow loss: check orifice for plugging
- Seal face temperature >120°C: flush flow insufficient

### 4.3 Seal Replacement Procedure
**SAFETY**: Naphtha is highly flammable. Full PPE required. No ignition sources within 10 m.
1. Shutdown pump; close suction and discharge isolation valves
2. Depressurize casing; nitrogen purge (3 volumes minimum)
3. Verify LEL <10% with gas detector
4. Drain seal chamber via drain plug
5. Remove gland plate bolts (4 × M12, torque 35 N·m)
6. Slide seal off shaft; inspect faces and O-rings
7. Install new seal; verify face flatness (max 0.001 mm deviation)
8. Torque gland plate bolts evenly in cross pattern
9. Pressurize flush system; check for leaks before startup
10. Typical replacement time: 3–4 hours

### 4.4 Seal Life Expectancy
- Normal naphtha service: 12–18 months
- Reduced life factors: dry running, particulate contamination, temperature >100°C, shaft runout >0.05 mm

---

## 5. Semi-Open Impeller Clearance Setting

### 5.1 Importance of Impeller Clearance
The CPT-50 uses a semi-open impeller. The axial clearance between impeller vane tips and the casing wear plate directly affects efficiency and vibration:
- Too tight (<0.3 mm): impeller rubs casing — vibration, heat, damage
- Optimal (0.3–0.5 mm): best efficiency, lowest vibration
- Too loose (>0.8 mm): efficiency loss >8%, increased recirculation

### 5.2 Clearance Adjustment Procedure
1. Loosen bearing housing lock nuts
2. Advance shaft toward casing until impeller just contacts wear plate (zero clearance)
3. Back off shaft 0.4 mm using adjustment screws (1 turn = 0.5 mm on M10 thread)
4. Lock bearing housing; verify clearance with feeler gauge through inspection port
5. Rotate shaft by hand — must turn freely with no contact

### 5.3 Wear Plate Replacement
- Replace wear plate when: clearance cannot be reduced below 0.8 mm by adjustment
- Wear plate material: Duplex 2205 (same as impeller)
- Replacement interval: typically 3–5 years in naphtha service

---

## 6. Troubleshooting Guide

| Symptom | Probable Cause | Corrective Action |
|---|---|---|
| Bearing temp >75°C | Insufficient lubrication | Re-grease with Arcanol LOAD150 |
| Bearing temp >75°C | Misalignment | Check coupling alignment |
| Axial vibration >3.5 mm/s | Impeller clearance too tight | Adjust clearance to 0.4 mm |
| Axial vibration >3.5 mm/s | Angular misalignment | Realign coupling |
| Cavitation noise | Low suction pressure | Check suction line; increase NPSH |
| Flow declining | Impeller clearance too large | Adjust clearance; replace wear plate |
| Seal leak | Seal face damage | Replace seal immediately (fire hazard) |
| Motor overcurrent | Impeller rubbing | Check and adjust clearance |
| Pump overheating | Below minimum flow | Open recirculation line |

## Vibration Analysis Guidelines

### ISO 10816-7 Zone Classification for CPT-50
| Zone | Velocity (mm/s RMS) | Condition | Action |
|------|--------------------|-----------| -------|
| A | 0 – 2.8 | Good | Normal operation |
| B | 2.8 – 7.1 | Acceptable | Monitor trend |
| C | 7.1 – 11.2 | Alert | Plan maintenance |
| D | > 11.2 | Danger | Immediate shutdown |

### Cavitation Detection
- NPSH available must exceed NPSH required by minimum 0.5 m (safety margin)
- Cavitation signature: broadband noise at 2-10 kHz, random vibration spikes
- Suction pressure monitoring: alarm at NPSH margin < 1.0 m
- Flow recirculation onset: typically below 60% of BEP flow

### Performance Degradation Indicators
| Parameter | New | Acceptable | Degraded | Replace |
|-----------|-----|-----------|----------|---------|
| Head at BEP | 100% | > 95% | 90-95% | < 90% |
| Efficiency | 100% | > 93% | 85-93% | < 85% |
| Vibration | Zone A | Zone A-B | Zone B-C | Zone C-D |
| Bearing temp | < 65°C | < 75°C | 75-85°C | > 85°C |

## Condition-Based Maintenance Intervals

| Component | Monitoring Method | Replacement Trigger |
|-----------|------------------|-------------------|
| Bearings | Vibration trending + temperature | Zone C entry or temp > 85°C |
| Mechanical seal | Visual leak check + seal pressure | Any visible leak or pressure drop |
| Impeller | Performance test (head/flow) | Head drop > 5% at BEP |
| Coupling | Vibration 2× RPM component | 2× exceeds 50% of 1× amplitude |
| Wear rings | Internal clearance measurement | Clearance > 2× design value |
| Motor insulation | Megger test (quarterly) | Insulation resistance < 5 MΩ |

## Failure Mode and Effects Analysis (FMEA)

| Failure Mode | Detection Method | Severity | Occurrence | RPN |
|-------------|-----------------|----------|------------|-----|
| Bearing wear | Vibration + temperature | 7 | 4 | 196 |
| Seal failure | Leak detection + pressure | 8 | 3 | 168 |
| Cavitation | Vibration + NPSH monitoring | 6 | 5 | 210 |
| Impeller damage | Performance degradation | 8 | 2 | 112 |
| Misalignment | Vibration 2× component | 5 | 4 | 140 |
