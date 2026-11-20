# Local Draft Follow-up for Issue #20 — NOT POSTED

**Status:** LOCAL DRAFT (DO NOT PUBLISH WITHOUT EXPLICIT APPROVAL)  
**Defect ID:** BUG-04 / P8-005 (`MAT-S-001`, `MAT-C-004`)  
**Related Existing Issue:** https://github.com/Nidhikhare12/OsdagBridge/issues/20

## Summary
On baseline commit `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3`, custom girder steel weight density (`material.girder.density`) is ignored in three backend/export locations:
1. `src/osdagbridge/core/bridge_types/plate_girder/plategirderbridge.py:1200`: `_build_material_props()` falls back to `_DEFAULT_DENSITY` (`78500 N/m³`) when `_lookup_material(steel_grade, "Density")` returns `None` for custom grades.
2. `src/osdagbridge/core/bridge_types/plate_girder/analyser.py:371,416` & `plategirderbridge.py:1332`: `create_self_weight_load()` hardcodes `STEEL_UNIT_WEIGHT_kN_m3` (`78.5 kN/m³`).
3. `src/osdagbridge/desktop/ui/dialogs/generate_results_values_builder.py:663`: `resolve_permanent_load_summary()` hardcodes `STEEL_UNIT_WEIGHT_kN_m3`.

## Candidate Fix & Verification
- `_build_material_props()` reads `KEY_MATERIAL_GIRDER_DENSITY` (`* 1000.0` N/m³) when custom steel is selected.
- `add_dead_loads()` forwards `steel_density_kN_m3` to `create_self_weight_load()`, which scales `girder_self_weight_kN_m(A_girder_m2, rho_s)`.
- `resolve_permanent_load_summary()` reads `KEY_MATERIAL_GIRDER_DENSITY` / `steel_prop.rho`.
- **Unit regressions:** `test_custom_steel_density_reaches_steel_properties`, `test_custom_steel_density_scales_self_weight_load_model`, and `test_permanent_load_summary_uses_custom_steel_and_deck_densities` — FAIL on baseline, PASS on candidate.
- **Live GUI integration:** Comparing Candidate `RUN-01` (`78.5 kN/m³`) vs `RUN-06` (`80.0 kN/m³`), `SW` `G1 Mu` scales from `185.33` to `188.87 kNm` (ratio `1.019101` vs exact `80.0/78.5 = 1.019108`, `0.0007%` diff).
