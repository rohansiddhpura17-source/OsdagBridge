# Local Draft Follow-up for Issue #43 (Cross Bracing) — NOT POSTED

**Status:** LOCAL DRAFT (DO NOT PUBLISH WITHOUT EXPLICIT APPROVAL)  
**Defect ID:** BUG-06a / P11-001 (`MAT-S-004`)  
**Related Existing Issue:** https://github.com/Nidhikhare12/OsdagBridge/issues/43

## Reproduction & Evidence
In live GUI test `evidence/phase11-components-20261119` (baseline commit `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3`, PID 27137), entering custom cross-bracing steel `custom_steel_355_500` (`Fy = 355 MPa`, `Fu = 500 MPa`, `E = 199.9 GPa`, `density = 77.0 kN/m³`) stores all `material.cross_bracing.*` keys in `input_dict`, yet `RUN-01` (standard E 350A) and `RUN-02` (custom) produce identical cross-bracing member capacities (`Member.tension_yielding = 107.73 kN`, corresponding to hardcoded `E 250A`).

## Root Cause
1. `src/osdagbridge/core/bridge_types/plate_girder/crossbracingforces.py` (`run_member_designs`) and `plategirderbridge.py:2343` copy `design_dict_tension_bolted` / `design_dict_struts_bolted` from `src/osdagbridge/core/utils/connect.py`, which hardcodes `"Material": "E 250 (Fe 410 W)A"`, without reading `material.cross_bracing*`.
2. `src/osdagbridge/desktop/ui/dialogs/generate_results_values_builder.py:175-190` (`resolve_material_properties_steel`) clones girder steel properties onto the Cross Bracing row.

## Candidate Fix & Verification
- `connect.py`: added `resolve_component_steel_material()`, `apply_material_to_design_dict()`, and `_patched_osdag_core_material()` context manager inside `run_calculation()` so both mapped standard grades and custom steel overrides (`fy`, `fu`, `E_mpa`, `unit_mass`) execute inside `osdag_core`.
- `plategirderbridge.py` & `crossbracingforces.py`: resolve `cb_mat_spec`, record `output_dict["material.cross_bracing.effective"]`, and apply `cb_mat_spec` to every tension/compression job.
- `generate_results_values_builder.py`: resolve each steel row independently by component key/prefix.
- **Verification:** `test_cross_bracing_and_end_diaphragm_material_mapping_and_capacity` PASS; Live GUI integration (`phase12-candidate-integration`) shows cross-bracing `40 x 40 x 3` `Member.tension_yielding` scaling `107.73 kN` (baseline hardcoded E 250A) → `150.82 kN` (candidate E 350A, exact `1.400x`) → `198.22 kN` (candidate `custom_steel_460_600`, exact `1.840x`), and Excel Steel Results Table reports `460 / 600 / 210000 MPa` for Cross Bracing.
