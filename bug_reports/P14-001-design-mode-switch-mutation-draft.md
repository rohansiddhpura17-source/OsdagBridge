# Local Draft Issue — NOT POSTED

## Title
[Bug] Switching Design Mode (`Optimized` ↔ `Custom`) overwrites unrelated user inputs, injects mm² into m² area fields, retains stale custom stiffeners, and leaks pruned cross-bracing dynamic keys

**Status:** LOCAL DRAFT (DO NOT PUBLISH WITHOUT EXPLICIT APPROVAL) — FIXED & VERIFIED IN CANDIDATE WORKTREE  
**Defect ID:** BUG-14 / P14-001 (formerly `OBS-14`; `ADV-007`, `ADV-003`)  
**Related Existing Issue:** Related to `#125` (UI input dictionary synchronization)

## Reproduction & Untouched Baseline Evidence
Executed live on untouched baseline commit `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3` (`evidence/phase14-final-closure/baseline_gui_batch_a.json` & `bug14_gui_regression/bug14_adv003_gui_baseline.json`, screenshot `ADV-007_custom_mode.png`):
1. Open OsdagBridge with `span = 30 m`, `carriageway_width = 4.25 m`, `geometry.design_mode = "Optimized"`.
2. Edit unrelated enabled fields in `Additional Inputs` (`deck_thickness = 200`, `wearing_course.thickness = 65`, `gamma_m0 = 1.15`, `load_cycles = 500000`) and Save.
3. Switch **Design Mode** in `InputDock` (`Optimized -> Custom -> Optimized`):
   - **8 unrelated keys silently overwritten:** `typical_section.deck_thickness` (`200 -> 250.0`), `wearing_course.thickness` (`65 -> 50.0`), `wearing_course.density` (`25.0 -> 24.0`), `crash_barrier.area` (`0.3023 m² -> 302282.768 mm²`, 1,000,000× unit jump), `railing.width` (`0.275 -> 0.0`), `railing.load_value` (`6.806 -> 1.4715`), `gamma_m0` (`1.15 -> 1.10`), `load_cycles` (`500000 -> 2000000`).
   - **Stale custom stiffener overrides:** Editing `bearing_stiffener_spacing = 150` and `intermediate_stiffener_spacing = 3000` in `Custom` mode, saving, and returning to `Optimized` disables stiffener widgets while leaving `150` and `3000` active in `window.input_dict` (both base keys and `.G1.M1` keys).
4. In `ADV-003`, probing cross-bracing count `30 -> 29` then reducing to `3` leaves **650 stale dynamic keys** (`B1M4..B1M29`, `B2M4..B2M29`) in both `input_dict` and `output_dict`.

## Root Causes
1. `src/osdagbridge/core/bridge_types/plate_girder/defaults.py`:
   - `_update_typical_section_defaults()`, `_update_loading_tab_defaults()`, `_update_support_conditions_defaults()`, `_update_design_options_defaults()`, and `_update_design_options_cont_defaults()` used unconditional `input_dict.update({key: value})` instead of only filling `None`/missing keys as documented.
   - `KEY_CB_AREA` and `KEY_MD_AREA` were seeded in **mm²** (`302282.768`), contradicting the Additional Inputs UI unit **m²** (`0.3023`).
   - `solve_extend_basic_input_dict()` unconditionally overwrote `KEY_RL_WIDTH` and `KEY_TS_FOOTPATH_WIDTH` to `0.0` when `footpath == 'None'`.
   - `_on_no_of_girders_changed()` only recomputed stiffener keys when missing/blank, never resetting Custom-mode stiffener overrides on return to `Optimized`.
   - `extend_cb_dynamic_keys()` only added `M1..Mk` keys and never pruned `M(k+1)..Mn` keys when `no_of_bracings` decreased, nor updated base `KEY_MP_CB_SPACING`.
2. `src/osdagbridge/desktop/ui/docks/input_dock.py`:
   - `_on_design_mode_changed()` did not write `KEY_DESIGN_MODE` immediately or re-seed Optimized stiffener keys and sync the cached `AdditionalInputs` dialog when switching `Custom -> Optimized`.
3. `src/osdagbridge/core/boq/boq_generator.py` & `plategirderbridge.py`:
   - `boq_generator.py` assumed `KEY_CB_AREA` was always in mm²; updated to handle `m²` cleanly while staying backward-compatible with legacy `mm²` OSI values (`> 100.0`).
   - `plategirderbridge.py` passes `0.0` for `footpath_width`/`railing_width` in `DeckLayoutProperties` when `n_footpaths == 0` so preserving `KEY_RL_WIDTH` in `input_dict` never alters deck layout geometry.

## Candidate Fix & Verification
- **Unit regressions (`test_phase89_candidate_regressions.py`):** `test_bug14_seeders_preserve_user_values_and_store_area_in_m2` and `test_bug14_cross_bracing_count_reduction_prunes_stale_member_keys` — **FAIL on baseline (`36 failures, 2 errors`), PASS on candidate (`21 / 21 OK`)**.
- **Live GUI Regression (`evidence/phase14-final-closure/bug14_gui_regression/`):**
  - Baseline (`bug14_adv003_gui_baseline.json`): **FAIL (`2 / 7`)** — 8 unrelated mutations, `302282.768 mm²`, stale stiffeners `150`/`3000`, and `650` stale CB input/output keys.
  - Candidate (`bug14_adv003_gui_candidate.json`): **PASS (`7 / 7`)** — `0` unrelated mutations across `Optimized -> Custom -> Optimized`, `crash_barrier.area = 0.3023 m²`, `0` stale stiffeners after return (`"100"` / `"2440"` restored), and `ADV-003` `29 -> 3` produces `0` stale input keys, `0` stale output keys, `no_of_cross_bracings = 3`, `spacing = 7.5 m`, `pairs = ["G1-G2", "G2-G3"]`, `brace_type = "X"`.
- **Combined 14-Fix Integration (`candidate_13fix_revalidation.json`):** **`15 / 15` assertions PASS** with all `BUG-01`..`BUG-14` active together.
