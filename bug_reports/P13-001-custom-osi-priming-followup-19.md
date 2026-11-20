# Local Draft Follow-up for Issue #19 (Custom Material OSI Priming Loss) — NOT POSTED

**Status:** LOCAL DRAFT (DO NOT PUBLISH WITHOUT EXPLICIT APPROVAL)  
**Defect ID:** BUG-12 / P13-001 (`OSI-002`)  
**Related Existing Issue:** https://github.com/Nidhikhare12/OsdagBridge/issues/19

## Reproduction & Evidence
On baseline commit `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3` (`phase13-integrity-verification/baseline_integrity_check.json`):
1. Save an `.osi` file containing custom girder steel (`custom_steel_360_510`, `density=80.0`, `fy=360.0`, `fu=510.0`, `e=200.0`, `g=76.9`) and custom concrete deck (`custom_concrete_40_3`, `density=24.0`, `fck=40.0`, `fctm=3.0`, `ecm=34.0`).
2. Load the `.osi` in a fresh `CustomWindow` via `loadOSI_inputs()` and trigger pre-design priming (`input_dock._prime_material_inputs()`).
3. **Observed baseline failure:**
   - `_prime_material_inputs()` logs `cannot access local variable 'defaults' where it is not associated with a value` for `material.girder`.
   - `material.deck.density` is overwritten from `"24.0"` to `"24.5"`, and `material.deck.fck`, `material.deck.fctm`, and `material.deck.ecm` are wiped to `None`.

## Root Cause
1. `src/osdagbridge/desktop/ui/docks/input_dock.py:323-339`: `_prime_material_inputs()` only looks up `self._material_custom_fields` (in-memory cache, empty after fresh OSI load) and does not reconstruct custom fields from `self.parent.input_dict`.
2. `src/osdagbridge/desktop/ui/dialogs/material_properties.py:180`: `is_deck_material` only checks `self.member == "Deck"`, not `KEY_DECK_CONCRETE_GRADE_BASIC` (`"material.deck"`).

## Candidate Fix & Verification
- `input_dock.py`: recover prefixed custom fields from `self.parent.input_dict` into `self._material_custom_fields` when absent for custom grade names.
- `material_properties.py`: recognize `KEY_DECK_CONCRETE_GRADE_BASIC` and `"material.deck"` in `is_deck_material`.
- **Live GUI verification (`phase13-integrity-verification/candidate_integrity_check.json`):** All 12 custom girder steel and concrete deck keys survive `loadOSI_inputs()` + `_prime_material_inputs()` intact on candidate (`all_survived_priming: true`).
