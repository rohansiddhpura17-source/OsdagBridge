## Proposed resolution for #92 (local draft — not posted)

**Root cause.** `add_temperature_load()` only read the legacy key `temperature_load_kN_m2` and applied it as a vertical deck patch pressure. The canonical Temperature Load inputs (air temperatures, CTEs) never reached the analysis. On the untouched baseline, the #92 inputs (65/−10 °C, 20e−6/10e−6) and a different input set (45/5 °C, 11.7e−6) both give Envelope ULS Mz = 1633.8066 kNm. The legacy 2.5 kN/m² input produces a spurious vertical `1.0 TL` (Mz 277.2194 kNm).

**Fix.**
- Adds a new `thermal_analysis.py` implementing IRC:6-2017 Cl. 215: effective bridge temperatures, uniform rise/fall, and Cl. 215.4 composite heating/cooling gradients via layered section integration.
- Adds `ThermalElementLoad` equivalent element loads in ospgrillage, with explicit longitudinal bearing springs and reaction recovery.
- Uses transformed composite stiffness while keeping bare-steel self-weight.
- Creates five TL load cases, included in the ULS/SLS combinations, and updates report Ch. 3/4/8 and the results tables.
- Legacy pressure input and |skew| > 15° are rejected explicitly.

**Verification.**
- 15/15 OpenSeesPy analytical benchmarks pass.
- After the fix, #92 inputs give 3071.6366 kNm vs 2809.8823 kNm for the comparison set.
- Nonthermal runs are unchanged (0 TL cases).
- Live GUI workflow 7/7, with a 56-page compiled report.
- Existing regressions: 28 unit OK; GUI 7/7 + 15/15.

**Scope.** Single-span composite plate-girder bridges, |skew| ≤ 15°. Transverse slab expansion across Z-restrained bearings and continuous multi-span bridges are not covered.

Patch: `phase20_thermal_issue92_isolated.patch` (applies on top of the Phase 19 fixes).
