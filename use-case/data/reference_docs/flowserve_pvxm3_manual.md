# Flowserve PVXM-3 Centrifugal Pump
## Operation, Maintenance & Troubleshooting Manual
### Applicable Units: P-01, P-02, P-07, P-10 (CDU Service)

---

## 1. Pump Specifications

| Parameter | Value |
|---|---|
| Model | PVXM-3 |
| Type | Single-stage, end-suction, centrifugal |
| Service fluid | Crude oil / heavy hydrocarbons |
| Design flow | 120 m³/hr |
| Design head | 85 m |
| Rated power | 37 kW |
| Rated speed | 2,950 RPM |
| Specific speed (Ns) | 1,850 (metric) |
| Impeller diameter | 285 mm |
| Impeller type | Closed, 5-vane |
| Casing material | Carbon steel ASTM A216 WCB |
| Impeller material | 316 stainless steel |
| Shaft material | 17-4 PH stainless steel |
| Bearing type | SKF 6312 (drive end), SKF 6308 (non-drive end) |
| Seal type | Mechanical double seal, API Plan 53B |
| Seal flush fluid | Barrier fluid (glycol/water 50:50) |
| NPSH required | 3.2 m at design flow |
| Maximum allowable temperature | 180°C |
| Maximum allowable pressure | 16 bar |

---

## 2. Normal Operating Envelope

### 2.1 Flow & Head Envelope
- Minimum continuous flow: 48 m³/hr (40% of BEP)
- Best Efficiency Point (BEP): 120 m³/hr at 85 m head
- Maximum continuous flow: 138 m³/hr (115% of BEP)
- Operating outside this range causes increased vibration, bearing loads, and seal wear

### 2.2 Bearing Temperature Limits

| Condition | Bearing Temp (°C) | Action |
|---|---|---|
| Normal operation | 45–65°C | No action required |
| Elevated — monitor | 65–80°C | Increase monitoring frequency; check lubrication |
| Warning threshold | 80–85°C | Inspect bearing and lubrication within 4 hours |
| Alarm threshold | >85°C | Reduce load or shut down; inspect immediately |
| Failure threshold | >95°C | Immediate shutdown — bearing failure imminent |

**Rate-of-rise alert**: If bearing temperature rises >2°C/hr sustained over 4 hours, treat as warning regardless of absolute temperature.

### 2.3 Vibration Limits (ISO 10816-3, Group 2, >15 kW)

| Zone | Vibration (mm/s RMS) | Condition | Action |
|---|---|---|---|
| A | 0 – 2.3 | New or recently overhauled | Normal |
| B | 2.3 – 4.5 | Acceptable for long-term operation | Monitor |
| C | 4.5 – 7.1 | Unsatisfactory — investigate | Plan maintenance within 2 weeks |
| D | > 7.1 | Dangerous — damage likely | Shut down immediately |

Measurement points:
- Bearing housing, radial direction (X and Y axes)
- Bearing housing, axial direction
- Measure at BEP flow conditions for baseline

### 2.4 Motor Current Limits
- Normal operating current: 58–65 A (at rated conditions)
- Overload warning: >72 A sustained >5 minutes
- Overload trip: >80 A (motor protection relay setting)

---

## 3. Bearing Maintenance

### 3.1 Lubrication Specifications
- Lubricant type: Mobil SHC 526 (synthetic, ISO VG 100)
- Grease alternative: Shell Gadus S2 V220 (NLGI Grade 2)
- Relubrication interval: every 2,000 operating hours
- Grease quantity per bearing: 15–20 g (do not over-grease — causes overheating)
- Operating temperature range for lubricant: –30°C to +130°C

### 3.2 Bearing Replacement Criteria
Replace bearings when any of the following occur:
- Bearing temperature consistently >80°C despite fresh lubrication
- Vibration in Zone C or D
- Audible noise: grinding, squealing, or irregular knocking
- Visible pitting, spalling, or discoloration on races or rolling elements
- Radial clearance exceeds 0.08 mm (measured with feeler gauge)
- After any bearing temperature excursion >95°C

### 3.3 Bearing Replacement Procedure
1. Isolate pump from process (close suction and discharge valves)
2. Drain seal barrier fluid; depressurize seal system
3. Remove coupling guard and disconnect coupling
4. Remove bearing housing cover bolts (torque: 45 N·m)
5. Extract shaft assembly using bearing puller — do NOT use heat on SKF 6312
6. Press new bearing onto shaft using bearing heater (max 110°C) or press
7. Verify bearing seating: zero axial play, smooth rotation by hand
8. Repack with fresh grease (15 g per bearing)
9. Reassemble; align coupling to ≤ 0.05 mm TIR
10. Run-in: operate at 50% load for 2 hours; check temperature and vibration

### 3.4 Bearing Life Estimation (L10 Life)
Using SKF bearing life formula:
```
L10 (hours) = (C/P)^3 × (10^6 / (60 × n))
```
Where:
- C = dynamic load rating (SKF 6312: 81.9 kN)
- P = equivalent dynamic bearing load (kN)
- n = shaft speed (RPM)

At design conditions (P ≈ 8.5 kN, n = 2,950 RPM):
- L10 ≈ 42,000 hours (~5 years continuous operation)
- Actual service life reduced by: misalignment, contamination, overtemperature

---

## 4. Mechanical Seal Maintenance

### 4.1 Seal System — API Plan 53B
- Barrier fluid: Glycol/water 50:50 (inhibited)
- Barrier fluid pressure: 2–3 bar above process pressure
- Barrier fluid temperature: maintain <60°C (cooling water required if >50°C ambient)
- Reservoir volume: 2.5 liters
- Refill interval: check monthly; refill if level drops >10%

### 4.2 Seal Failure Indicators
- Seal leak detected (proximity sensor): immediate action required
- Barrier fluid consumption >0.5 L/week: inspect seal faces
- Barrier fluid pressure drop >0.5 bar/day: seal face or O-ring failure
- Visible leakage at seal housing: shutdown required

### 4.3 Seal Replacement Procedure
1. Shut down pump; isolate from process
2. Depressurize and drain barrier fluid system
3. Remove coupling and bearing housing
4. Slide seal cartridge off shaft (cartridge design — no special tools required)
5. Inspect seal faces: replace if scratched, chipped, or worn >0.5 mm
6. Install new cartridge seal; verify O-ring seating
7. Refill barrier fluid; pressurize to 2 bar; check for leaks
8. Typical seal replacement time: 4–6 hours

### 4.4 Seal Life Expectancy
- Normal service: 18–24 months
- Reduced life factors: dry running (even momentary), process fluid contamination of barrier fluid, temperature >150°C, shaft misalignment >0.1 mm

---

## 5. Impeller Inspection & Replacement

### 5.1 Impeller Wear Indicators
- Differential pressure declining >10% from baseline at same flow: impeller wear
- Flow rate declining >15% at same speed and head: impeller damage
- Visible erosion on vane leading edges (inspect during overhaul)
- Cavitation damage: pitting on suction side of vanes

### 5.2 Wear Ring Clearance
- New clearance (impeller/casing wear ring): 0.35–0.45 mm
- Maximum allowable clearance: 0.80 mm
- If clearance >0.80 mm: replace wear rings (do not replace impeller unless damaged)

### 5.3 Impeller Replacement
1. Remove pump casing (8 × M20 bolts, torque 120 N·m)
2. Lock shaft; remove impeller nut (left-hand thread — turn clockwise to remove)
3. Pull impeller; inspect for erosion, cracks, or imbalance
4. Install new impeller; torque nut to 85 N·m
5. Check axial clearance between impeller and casing: 0.5–1.0 mm
6. Reassemble; perform vibration check at startup

---

## 6. Troubleshooting Guide

| Symptom | Probable Cause | Corrective Action |
|---|---|---|
| Bearing temp >80°C | Insufficient lubrication | Re-grease; check interval |
| Bearing temp >80°C | Misalignment | Check and correct coupling alignment |
| Bearing temp >80°C | Bearing failure | Replace bearing |
| Vibration Zone C/D | Impeller imbalance or damage | Inspect impeller; balance or replace |
| Vibration Zone C/D | Misalignment | Realign coupling |
| Vibration Zone C/D | Cavitation | Check NPSH; reduce flow or increase suction pressure |
| Vibration axial high | Misalignment (angular) | Check angular alignment |
| Flow rate declining | Impeller wear | Check wear ring clearance; replace if needed |
| Seal leak | Seal face damage | Replace mechanical seal |
| Motor overcurrent | Impeller rubbing casing | Check axial clearance |
| Noise — cavitation | NPSH insufficient | Increase suction pressure; reduce flow |
| Noise — bearing | Bearing failure | Replace bearing immediately |

## Vibration Analysis Guidelines

### ISO 10816-7 Zone Classification for PVXM-3
| Zone | Velocity (mm/s RMS) | Condition | Action |
|------|--------------------|-----------| -------|
| A | 0 – 2.8 | Good | Normal operation |
| B | 2.8 – 7.1 | Acceptable | Monitor trend |
| C | 7.1 – 11.2 | Alert | Plan maintenance |
| D | > 11.2 | Danger | Immediate shutdown |

### Common Vibration Signatures
- 1× RPM dominant: Imbalance — check impeller erosion, coupling alignment
- 2× RPM dominant: Misalignment — check coupling gap, soft foot
- Sub-synchronous (0.4-0.48×): Oil whirl in sleeve bearings
- Broadband elevation: Bearing defect — replace bearing set
- Blade pass frequency (vane × RPM): Recirculation or cavitation

### Bearing Temperature Limits
| Location | Normal | Alert | Alarm | Trip |
|----------|--------|-------|-------|------|
| Drive End | < 75°C | 75-85°C | 85-95°C | > 95°C |
| Non-Drive End | < 70°C | 70-80°C | 80-90°C | > 90°C |
| Thrust Bearing | < 80°C | 80-90°C | 90-100°C | > 100°C |

## Spare Parts Cross-Reference

| Part | Flowserve P/N | Generic Equivalent | Lead Time |
|------|--------------|-------------------|-----------|
| Impeller | PVXM3-IMP-316SS | N/A (proprietary) | 8-12 weeks |
| Mechanical Seal | PVXM3-SEAL-21 | John Crane Type 21 | 2-4 weeks |
| Bearing Set (DE) | PVXM3-BRG-DE | SKF 6305-2RS | 1-2 weeks |
| Bearing Set (NDE) | PVXM3-BRG-NDE | SKF 6205-2RS | 1-2 weeks |
| Coupling Element | PVXM3-COUP | Falk 1050T | 2-3 weeks |
| Wear Ring | PVXM3-WR-01 | N/A (proprietary) | 6-8 weeks |
