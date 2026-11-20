# Local Draft Follow-up for Issue #130 (Backend & OSI Non-Finite Rejection) — NOT POSTED

**Status:** LOCAL DRAFT (DO NOT PUBLISH WITHOUT EXPLICIT APPROVAL)  
**Defect ID:** BUG-07 / P4-003 / P11-003 (`INV-007`, `OSI-003`)  
**Related Existing Issue:** https://github.com/Nidhikhare12/OsdagBridge/issues/130

## Reproduction & Evidence
On baseline commit `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3`:
1. **Backend validator (`P4-003`):** `BridgeInputValidator.validate_basic_inputs("geometry.span", {"geometry.span": "NaN"})` returns `None` (valid) because `float("NaN")` succeeds and unordered `<` / `>` comparisons evaluate `False`.
2. **Backend normalization (`phase11-nonfinite`):** `PlateGirderBridge.set_input({"geometry.span": "nan"})` and `inf`/`-inf`/`1e999` succeed without raising, replacing `self.input_dict` with non-finite floats.
3. **OSI loader & Live GUI (`phase13-integrity-verification/baseline_integrity_check.json`):** Loading an OSI file containing `geometry.span: NaN` via `CustomWindow.loadOSI_inputs()` passes `validate_osi_inputs()`, displays `"Loaded OSI Successfully!"`, and commits `"NaN"` into live `window.input_dict`.

## Root Cause
- `src/osdagbridge/core/bridge_types/plate_girder/validator.py:1094-1102`: `_to_float()` lacked `math.isfinite()` and `OverflowError` handling; `_to_int()` lacked `OverflowError`.
- `src/osdagbridge/core/bridge_types/plate_girder/plategirderbridge.py:444`: `_normalize_input_dict()` coerced non-finite values without checking `isfinite()`.
- `src/osdagbridge/core/utils/osi_validator.py:132`: `OsiInputValidator.validate()` had no recursive finite check.

## Candidate Fix & Verification
- `validator.py`: `_to_float()` returns `parsed if isfinite(parsed) else None` and catches `OverflowError`; `_to_int()` catches `OverflowError`.
- `plategirderbridge.py`: `_normalize_input_dict()` recursively validates `isfinite()` over all scalars, dicts, and lists before mutating `self.input_dict`.
- `osi_validator.py`: added `_is_nonfinite_scalar()` and `_validate_all_finite()` in `OsiInputValidator.validate()`.
- **Verification:**
  - `test_phase11_nonfinite.py` (4 tests, 16+ subtests covering basic/material/additional validators, `set_input` state preservation, and nested lists) — baseline FAILS, candidate PASS.
  - `test_osi_validator_rejects_nonfinite_material_and_geometry_values` — baseline FAILS, candidate PASS.
  - Live GUI `loadOSI_inputs()` on candidate (`phase13-integrity-verification/candidate_integrity_check.json`) rejects `geometry.span: [`, `geometry.span: NaN`, and `material.girder.e: inf` with `"Invalid OSI File: numeric input must be finite."` and preserves 100% of prior `window.input_dict`.
