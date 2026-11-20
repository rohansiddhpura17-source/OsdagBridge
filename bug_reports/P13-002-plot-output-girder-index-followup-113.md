# Local Draft Follow-up for Issue #113 (Edge Distance & Girder Mapping Mismatch) — NOT POSTED

**Status:** LOCAL DRAFT (DO NOT PUBLISH WITHOUT EXPLICIT APPROVAL)  
**Defect ID:** BUG-13 / P13-002 (`CAD-004`)  
**Related Existing Issue:** https://github.com/Nidhikhare12/OsdagBridge/issues/113

## Reproduction & Baseline Evidence
Direct comparison of Phase 10 pass05 live Matplotlib Shear Force plot (`RUN-01-plot-numeric-samples.json`, load case `SW`, force `Fy`, member `All`) against the same run's Output Dictionary (`RUN-01-output-dict.json`, `design_results["per_girder"]`) on baseline commit `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3`:
- **Live Plot (`plot_generator.py` passes `edge_dist = 0.8583 > 0`, skipping edge beams):**
  `G1 = 28.224 kN`, `G2 = 23.996 kN`, `G3 = 28.224 kN` (3 structural girders).
- **Baseline Output Dictionary `per_girder`:**
  `G1 = 23.99 kN`, `G2 = 28.22 kN`, `G3 = 24.00 kN`, `G4 = 28.22 kN`, `G5 = 23.99 kN` (5 grillage lines, counting `EB1`/`EB2` edge beams as `G1` and `G5`, shifting main girders by +1 and causing a **4.234 kN** discrepancy on `G1` while leaving `G4` hidden from Output Dock `G1..G3` and Results Tables).

## Root Causes (Four Interlocking Defects)
1. `src/osdagbridge/core/bridge_types/plate_girder/analysis_results.py`:
   - `__init__(..., edge_dist=0)` defaulted `edge_dist` to `0` instead of inferring `bridge.edge_dist` when omitted.
   - `build_girders()` (lines 453–460) assigned `name = f"G{i}"` before overriding `i == 1 -> "EB1"` and `i == num_pairs -> "EB2"`, labeling main girders `G2..G(n+1)` instead of `G1..Gn` even when `edge_dist > 0` was passed.
2. `src/osdagbridge/core/bridge_types/plate_girder/plategirderbridge.py`:
   - `_run_dcr_checks()` (`:2296`), `get_result_handler()` (`:3325`), and `get_available_loadcases()` (`:3825`) omitted `edge_dist=self.get_edge_dist()`.
   - `get_edge_dist()` (`:3973`) only inspected `output_dict` instead of reading authoritative `grillage_model.edge_dist` while preserving explicit `0.0`.
3. `src/osdagbridge/core/bridge_types/plate_girder/designer.py`:
   - `BridgeConfig.from_plate_girder_bridge()` (`:401, 434`) set `GeometryConfig.n_girders = geom.n_l` (`5` for 3-girder, `6` for 4-girder) instead of `n_main_girders = bridge._girder_count()`.
4. `src/osdagbridge/desktop/ui/dialogs/steel_design.py`:
   - `_populate_member_combo()` (`:766`) used `keys[1:-1] if len(keys) > 2 else keys`, which drops outer main girders `G1` and `Gn` on zero-overhang (`edge_dist == 0`) bridges.

## Candidate Fix & Verification
Fixed all four modules in isolated candidate patch (`scripts/isolated-candidate-fixes-phase16.patch`):
- **Unit regressions (`test_phase89_candidate_regressions.py`):** `test_bug13_build_girders_and_plot_alignment_multi_config` (3-girder & 4-girder × `edge_dist=1.5` & `edge_dist=0.0`) and `test_bug13_edge_dist_dcr_config_and_steel_dialog_wiring` — **FAIL on baseline, PASS on candidate (19/19 OK)**.
- **Live GUI Integration (`evidence/phase14-final-closure/candidate_13fix/candidate_13fix_revalidation.json`):**
  - **3-Girder (`edge_dist = 0.8583 m`):** `build_girders = [EB1, G1, G2, G3, EB2]`, `n_girders = 3`, `per_girder = [G1, G2, G3]`, Output Dock & Steel Design combo `[G1, G2, G3]`, Plot vs `per_girder` `SW/Fy` = `[28.224 vs 28.22, 23.996 vs 24.00, 28.224 vs 28.22] kN` (`max_diff = 0.004 kN`, `0.000 kN` vs `_load_effects_cache`).
  - **4-Girder:** `build_girders = [EB1, G1, G2, G3, G4, EB2]`, `n_girders = 4`, `per_girder = [G1, G2, G3, G4]`, Output Dock & Steel Design combo `[G1, G2, G3, G4]`, Plot vs `per_girder` `SW/Fy` = `[29.252 vs 29.25, 26.352 vs 26.35, 26.352 vs 26.35, 29.252 vs 29.25] kN` (`max_diff = 0.002 kN`).
  - **Compiled 4-Girder Tectonic PDF (`cand_phase14_4g_report.pdf`):** 50 pages, 263,961 bytes, `0` compiler errors, verified `G1..G4` present with **zero** spurious `G5`/`G6` girder labels.
