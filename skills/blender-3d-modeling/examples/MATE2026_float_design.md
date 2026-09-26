# MATE ROV 2026 — Vertical Profiling Float Design

**Concept: "Argus-P" — a compact Argo-style autonomous vertical profiler**

## Competition constraints driving the design (2026 MATE ROV specs)

| Requirement | Limit | Design response |
|---|---|---|
| Overall height | < 1.0 m incl. antenna | Total height **0.86 m** |
| Diameter | < 18 cm | Hull Ø **0.17 m** |
| Tether | No airline/rope to surface or bottom | Fully autonomous, onboard battery |
| Power | Onboard battery ≤ 12 VDC, ≤ 5 A, single fuse | 3S 18650 Li-ion pack (11.1 V), one inline fuse holder |
| Scoring | Buoyancy engine earns 10 pts vs 5 pts | Mid-waist external oil bladder + internal pump |
| Depth holds | Bottom of float at 2.5 m ± 33 cm for 30 s; top of float at 40 cm ± 33 cm for 30 s | Bottom-mounted pressure sensor (offset declared to judge), bottom-heavy ballast for stable vertical attitude |
| Penalty | −5 pts if surface breaks or ice contacts | Ascent limited to 40 cm top depth; low-profile antenna |
| Recovery | ROV recovers float to poolside; U-bolt required (per 2026 update) | Steel U-bolt handle on upper dome |
| Cameras | Not allowed on the float | Sensor-based only: pressure + temperature + conductivity |
| Comms | Transmit ≥ 20 data packets after recovery | LoRa whip antenna + shore receiver |

## Exterior configuration (bottom → top)

1. **BP_Keel_Weight** — Ø 0.10 m × 0.06 m lead-shot ballast keel (black). Bottom-heavy mass keeps the float vertical in water, which the depth-hold task rewards.
2. **BP_Sensor_Pod** — Ø 0.05 m pressure/CTD pod protruding 0.04 m below the keel; pressure sensor sits at the **very bottom face** so measured depth = depth of bottom of float (2.5 m hold spec), no offset math for the judge.
3. **BP_Dome_Bottom** — hemispherical lower dome (safety yellow).
4. **BP_Hull_Cylinder** — Ø 0.17 m × 0.46 m white pressure tube (PVC/acrylic), the visual spine of the float.
5. **BP_Bladder** — amber translucent toroidal external bladder around the hull waist (z ≈ 0.33 m) — the visible "buoyancy engine" of every real Argo float; inflates → ascends, deflates → descends.
6. **BP_Clamp_Rings** × 3 — stainless fairing/clamp bands on the hull.
7. **BP_Fuse_Pod** — small sealed pod on upper hull holding the single required fuse + power switch (accessible, visible to inspectors).
8. **BP_Dome_Top** — hemispherical upper dome (safety yellow).
9. **BP_Ubolt_Handle** — stainless U-bolt recovery handle (2026 requirement) on the upper dome for the ROV manipulator.
10. **BP_Mast** + **BP_Antenna** — yellow mast (Ø 0.02 m) to 0.78 m, black LoRa whip to **0.86 m total** (< 1 m rule, with 14 cm margin).
11. **BP_Strobe** — recovery strobe + status LED at mast base.

## Why this wins the task

- **Two scoring mechanisms in one device**: bladder buoyancy engine (10 pts/profile) plus passive trim stability from the keel (cheap depth holds).
- **Depth-hold strategy**: pressure sensor on the bottom face → 2.5 m hold is measured exactly as the rule defines it; bladder volume control gives slow, precise, thruster-free vertical speed for the 40 cm hold where thrusters would overshoot.
- **Compactness**: 0.17 m Ø leaves 10 mm margin in a busy pool; 0.86 m height keeps the antenna well under the 1 m cap even with assembly tolerances.
- **Realism**: visually modeled on SOCCOM/Argo floats — white hull, safety-yellow domes, waist bladder, whip antenna — so judges immediately read it as a serious oceanographic instrument.

## Blender scene

`mate_float_build.py` builds the full float (BP_ prefix), studio lighting, camera, and renders `mate_float_preview.png`. Run inside Blender 5.1+ (Text Editor → Run Script, or via the Kimi Blender plugin once connected).
