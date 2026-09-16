# KSB Etanorm 100-080 Centrifugal Pump
## Operation, Maintenance & Troubleshooting Manual
### Applicable Units: P-05, P-06, P-09, P-12 (Diesel / Fuel Oil Service)

---

## 1. Pump Specifications

| Parameter | Value |
|---|---|
| Model | Etanorm 100-080-200 |
| Type | Single-stage, end-suction, back pull-out |
| Service fluid | Diesel / fuel oil / light distillates |
| Design flow | 100 m³/hr |
| Design head | 70 m |
| Rated power | 30 kW |
| Rated speed | 2,950 RPM |
| Impeller diameter | 262 mm |
| Impeller type | Closed, 6-vane |
| Casing material | EN-GJL-250 cast iron (diesel service) |
| Impeller material | EN-GJS-400-15 ductile iron |
| Shaft material | 1.4021 martensitic stainless steel |
| Bearing type | NSK 6310 (drive end), NSK 6306 (non-drive end) |
| Seal type | Mechanical single seal, API Plan 11 |
| NPSH required | 3.0 m at design flow |
| Maximum allowable temperature | 140°C |
| Maximum allowable pressure | 12.5 bar |

---

## 2. Normal Operating Envelope

### 2.1 Flow & Head Envelope
- Minimum continuous flow: 40 m³/hr (40% of BEP)
- Best Efficiency Point (BEP): 100 m³/hr at 70 m head
- Maximum continuous flow: 115 m³/hr (115% of BEP)
- Pump efficiency at BEP: 78%

### 2.2 Bearing Temperature Limits

| Condition | Bearing Temp (°C) | Action |
|---|---|---|
| Normal operation | 45–65°C | No action required |
| Elevated — monitor | 65–78°C | Check lubrication; increase monitoring |
| Warning threshold | 78–85°C | Inspect within 4 hours |
| Alarm threshold | >85°C | Reduce load; inspect immediately |
| Failure threshold | >95°C | Immediate shutdown |

### 2.3 Vibration Limits (ISO 10816-3, Group 2)

| Zone | Vibration (mm/s RMS) | Condition | Action |
|---|---|---|---|
| A | 0 – 2.3 | New machine | Normal |
| B | 2.3 – 4.5 | Acceptable long-term | Monitor |
| C | 4.5 – 7.1 | Unsatisfactory | Plan maintenance within 2 weeks |
| D | > 7.1 | Dangerous | Shutdown immediately |

**Misalignment signature**: Elevated axial vibration (>2× radial) combined with 2× running speed frequency in spectrum — indicates angular misalignment. Realign within 48 hours.

### 2.4 Back Pull-Out Feature
The Etanorm 100-080 uses a back pull-out design — the rotating assembly (impeller, shaft, bearings, seal) can be removed without disturbing the pump casing or pipe connections. This reduces maintenance downtime significantly:
- Typical bearing/seal replacement time: 2–3 hours (vs. 6–8 hours for conventional design)
- Casing remains bolted to baseplate and piping during maintenance

---

## 3. Bearing Maintenance

### 3.1 Lubrication Specifications
- Lubricant: NSK Grease LG2 (NLGI Grade 2) or equivalent
- Alternative: Castrol Tribol 1100/220
- Relubrication interval: every 3,000 operating hours
- Grease quantity: drive end 18 g, non-drive end 10 g
- Grease nipple location: bearing housing top (both ends)

### 3.2 NSK 6310 Bearing Data
- Dynamic load rating (C): 61.8 kN
- Static load rating (C0): 38.0 kN
- Limiting speed (grease): 6,300 RPM
- L10 life at design conditions (P ≈ 6.0 kN, n = 2,950 RPM): ~44,000 hours

### 3.3 Bearing Replacement Procedure (Back Pull-Out)
1. Close suction and discharge isolation valves; drain pump casing
2. Disconnect coupling (do not disturb motor or piping)
3. Remove back pull-out unit: loosen 4 × M16 casing bolts; slide rotating assembly rearward
4. Place rotating assembly on maintenance bench
5. Remove bearing housing end covers (6 × M10 bolts, torque 25 N·m)
6. Extract bearings using hydraulic puller — support shaft to avoid bending
7. Clean shaft journals; inspect for wear (replace if diameter reduced >0.02 mm)
8. Heat new NSK 6310 to 80°C; press onto shaft
9. Repack: 18 g grease in drive end housing, 10 g in non-drive end
10. Reassemble back pull-out unit; slide into casing; torque casing bolts to 85 N·m
11. Align coupling: ≤ 0.05 mm parallel, ≤ 0.05 mm angular TIR
12. Run-in: 1 hour at 50% load; verify temperature and vibration

### 3.4 Misalignment — Common Root Cause for P-05, P-06, P-09, P-12
These units are mounted on a shared baseplate with the motor. Thermal growth of the motor during operation causes misalignment if cold alignment is not corrected for thermal offset:
- Cold alignment target: 0.10–0.15 mm low (pump shaft lower than motor shaft)
- This compensates for motor thermal growth at operating temperature
- Check alignment after first 100 hours of operation on new installations

---

## 4. Mechanical Seal Maintenance

### 4.1 Seal System — API Plan 11
- Flush from pump discharge via 3 mm orifice to seal chamber
- Seal face materials: Silicon carbide (rotating) vs. Carbon graphite (stationary)
- O-ring material: FKM (Viton) — compatible with diesel and fuel oil

### 4.2 Seal Failure Indicators
- Visible fuel oil leakage at seal housing: shutdown required (fire hazard)
- Seal leak sensor activated: shutdown within 10 minutes
- Flush line temperature >100°C: check flush flow; inspect orifice for plugging
- Fuel oil in bearing housing: seal failure — immediate shutdown

### 4.3 Seal Replacement Procedure (Back Pull-Out)
1. Remove back pull-out unit (see Section 3.3, steps 1–3)
2. Remove gland plate (4 × M10 bolts)
3. Slide seal off shaft; inspect faces for scratches or chips
4. Clean shaft sleeve; inspect for wear (replace sleeve if worn >0.1 mm)
5. Install new seal cartridge; verify O-ring seating
6. Torque gland plate bolts evenly: 30 N·m
7. Reinstall back pull-out unit
8. Typical replacement time: 2–3 hours

### 4.4 Seal Life Expectancy
- Normal diesel service: 24–36 months
- Reduced life factors: particulate contamination, temperature >120°C, shaft runout >0.08 mm, dry running

---

## 5. Impeller & Wear Ring Maintenance

### 5.1 Wear Ring Clearance
- New clearance: 0.30–0.40 mm (radial, each side)
- Maximum allowable: 0.75 mm
- Measurement method: feeler gauge through inspection port or dial indicator on disassembled pump

### 5.2 Impeller Replacement Criteria
- Visible erosion on vane leading edges >3 mm deep
- Cavitation pitting covering >20% of suction vane surface
- Differential pressure decline >15% from baseline at same flow and speed
- Cracks or fractures (any size) — replace immediately

### 5.3 Impeller Removal
- Impeller nut: right-hand thread, M30 × 2.0
- Torque for installation: 120 N·m
- Use shaft-locking tool (KSB part 50.10) to prevent shaft rotation during removal

---

## 6. Troubleshooting Guide

| Symptom | Probable Cause | Corrective Action |
|---|---|---|
| Bearing temp >78°C | Insufficient lubrication | Re-grease per schedule |
| Bearing temp >78°C | Misalignment | Check cold alignment; correct thermal offset |
| Axial vibration 2× radial | Angular misalignment | Realign coupling |
| Vibration at 2× RPM frequency | Misalignment or impeller imbalance | Align; inspect impeller |
| Flow declining >10% | Wear ring clearance excessive | Measure clearance; replace rings |
| Seal leak | Seal face damage or dry run | Replace seal; check flush flow |
| Noise — cavitation | Low NPSH | Check suction line; reduce flow |
| Motor overcurrent | Impeller rubbing or fluid density change | Check clearance; verify fluid properties |
| Pump won't prime | Air in suction line | Vent suction; check foot valve |

---

## 7. Spare Parts Recommendation

### 7.1 Recommended On-Site Spares (per pump)
| Part | Quantity | Reason |
|---|---|---|
| Mechanical seal cartridge | 1 | High wear item |
| NSK 6310 bearing | 2 | Drive end — most loaded |
| NSK 6306 bearing | 1 | Non-drive end |
| Wear ring set (casing + impeller) | 1 | Erosion wear |
| Shaft sleeve | 1 | Seal area wear |
| O-ring set (full pump) | 2 | Routine replacement |
| Impeller | 1 | Cavitation damage risk |

### 7.2 Recommended Fleet Spares (for 4-pump fleet P-05/06/09/12)
- 1 complete back pull-out rotating assembly (ready to swap in <1 hour)
- 2 mechanical seal cartridges
- 4 bearing sets

## Vibration Analysis Guidelines

### ISO 10816-7 Zone Classification for Etanorm 100-080
| Zone | Velocity (mm/s RMS) | Condition | Action |
|------|--------------------|-----------| -------|
| A | 0 – 2.8 | Good | Normal operation |
| B | 2.8 – 7.1 | Acceptable | Monitor trend |
| C | 7.1 – 11.2 | Alert | Plan maintenance |
| D | > 11.2 | Danger | Immediate shutdown |

### Bearing Replacement Intervals
- Standard duty (< 4000 hrs/yr): Every 3 years or 12,000 hours
- Heavy duty (> 6000 hrs/yr): Every 2 years or 10,000 hours
- Continuous duty: Monitor vibration trend, replace at Zone C entry

### Seal Maintenance
- Mechanical seal inspection: Every 6 months or at any leak detection
- Seal flush system: Check flow rate monthly (min 2 L/min)
- Seal face materials: Carbon vs SiC — replace as matched set only
- Seal chamber pressure: Must exceed suction pressure by 1-2 bar

## Troubleshooting Decision Tree

### High Vibration (> 7.1 mm/s)
1. Check alignment (laser alignment within 0.05 mm)
2. Check coupling condition (replace elastomer if cracked)
3. Check bearing clearance (replace if > 0.15 mm)
4. Check impeller balance (residual imbalance < 6.3 g·mm/kg per ISO 1940 G6.3)
5. Check foundation bolts (torque to 120 N·m)

### High Bearing Temperature (> 80°C)
1. Check oil level (sight glass at center mark)
2. Check oil condition (replace if dark or contaminated)
3. Check cooling water flow (min 5 L/min)
4. Check bearing preload (axial play 0.05-0.10 mm)
5. Check alignment (misalignment causes thrust loading)
