# Local Draft Follow-up for Issue #43 (End Diaphragm) — NOT POSTED

**Status:** LOCAL DRAFT (DO NOT PUBLISH WITHOUT EXPLICIT APPROVAL)  
**Defect ID:** BUG-06b / P11-002 (`MAT-S-005`)  
**Related Existing Issue:** https://github.com/Nidhikhare12/OsdagBridge/issues/43

## Reproduction & Evidence
In live GUI test `evidence/phase11-components-20261119` (baseline commit `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3`, PID 27137), entering custom end-diaphragm steel `custom_steel_360_510` (`Fy = 360 MPa`, `Fu = 510 MPa`) writes `material.end_diaphragm.*` keys to `input_dict`, but baseline end-diaphragm job construction and Excel export ignore those keys.

## Root Cause
1. `src/osdagbridge/core/bridge_types/plate_girder/plategirderbridge.py:2759-2785` submits `design_dict_tension_bolted` / `design_dict_struts_bolted` with hardcoded `E 250 (Fe 410 W)A` and never reads `material.end_diaphragm*`.
2. `src/osdagbridge/desktop/ui/dialogs/generate_results_values_builder.py:175-190` clones girder steel properties onto the End Diaphragm row.

## Candidate Fix & Verification
- `plategirderbridge.py` resolves `ed_mat_spec` via `connect.resolve_component_steel_material()`, stores `output_dict["material.end_diaphragm.effective"]`, and applies `apply_material_to_design_dict(d, ed_mat_spec)` to every end-diaphragm tension/compression job.
- `generate_results_values_builder.py` resolves End Diaphragm steel independently.
- **Verification:**
  - `test_cross_bracing_and_end_diaphragm_material_mapping_and_capacity` PASS.
  - Live GUI integration `RUN-06` confirms `material.end_diaphragm.effective` (`E 410 (Fe 540)`, `410/540 MPa`) and Excel Steel row `('End Diaphragm', 'E 410A', 540, 410, 200000, ...)`.
  - Targeted non-zero end-diaphragm member calculation (`phase13-integrity-verification/candidate_integrity_check.json`) confirms `osdag_core` `Member.tension_yielding` progresses `121.36 kN` (`E 250A`, `45x45x3`) → `176.67 kN` (`E 410A`, `40x40x3`) → `198.22 kN` (`custom_steel_460_600`, `40x40x3`).
