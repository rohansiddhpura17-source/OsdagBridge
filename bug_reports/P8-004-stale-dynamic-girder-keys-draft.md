# Local Draft Issue / Follow-up — NOT POSTED

## Title
[Bug] Stale `G4`/`G3G4` dynamic dictionary keys persist in live dictionaries after reducing girder count (3 → 4 → 3)

**Status:** LOCAL DRAFT (DO NOT PUBLISH WITHOUT EXPLICIT APPROVAL)  
**Defect ID:** BUG-09 / P5-002 (`DICT-005`)  
**Related Existing Issue:** `#125`

## Reproduction
1. On baseline commit `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3`, run a 3-girder baseline design (`Retry04 RUN-07`).
2. Unlock, open **Additional Inputs**, change `typical_section.no_of_girders` to `4`, Save, and run **Design** (`RUN-11`, generating 116 `G4`/`G3G4` keys).
3. Unlock, open **Additional Inputs**, change `typical_section.no_of_girders` back to `3`, Save, and run **Design** (`RUN-12`).
4. Inspect live `window.input_dict` and `backend.output_dict`: **119 obsolete `G4`/`G3G4` input keys and 42 `G4`-related output keys remain** (note: the saved `.osi` file and rendered TeX do not contain `G4`, confirming the leak is in the shared live dictionary commit path).

## Root Cause
`src/osdagbridge/desktop/ui/dialogs/additional_input/additional_inputs.py` (`__init__` / `set_defaults` at line 237 and `_save_inputs()` at line 518) commits the validated working copy using `self.default_input_dict.update(self.working_input_dict)`. Because `dict.update()` never removes keys deleted from `working_input_dict`, obsolete `G4`/`G3G4` keys persist in the shared `input_dict`.

## Candidate Fix & Verification
Added `_replace_shared_input_values(shared, working)` in `additional_inputs.py`, performing `shared.clear(); shared.update(working)` to remove deleted keys while preserving the shared dictionary object identity.
- **Unit regression:** `test_dynamic_dictionary_commit_removes_deleted_keys_and_preserves_identity` — FAIL on baseline, PASS on candidate.
- **Live GUI integration (`phase12-candidate-integration`):** `RUN-04` (4 girders) has 116 `G4` keys; `RUN-05` (4→3 girders) has **0** `G4` keys immediately after `_save_inputs()` and after Design completion.
