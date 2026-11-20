# Reconciled Master Defect Register & Local Issue Draft Index (Phase 14 Closure)

**Project:** FOSSEE IIT Bombay OsdagBridge Screening 2026  
**Baseline Commit:** `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3` (`dev` branch, strictly read-only)  
**Publication Policy:** ALL DRAFTS ARE LOCAL ONLY. ZERO ISSUES OR COMMENTS HAVE BEEN PUBLISHED TO GITHUB.

---

## Reconciled Defects (14 Fixed & Verified in Candidate + 0 Unresolved Observations + 1 Resolved Non-Defect)

| Master ID | Historical ID(s) | Test Case(s) | Existing Issue | Summary | Candidate Status | Local Draft |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **BUG-01** | `P4-001` | `BAS-001; MAT-C-001` | #148 | Concrete Ecm GPa/MPa unit mismatch in deck slab SLS design | FIXED & VERIFIED | `P4-001-comment-for-issue-148.md` |
| **BUG-02** | `P4-001-Excel; P4-002` | `BAS-001; MAT-C-001` | Separate draft (rel. #148, #41) | Concrete Results Table / Excel exports Ecm in GPa under MPa heading, inflates raw modular ratio 1000x, and hardcodes density 25.0 | FIXED & VERIFIED | `P4-001-separate-excel-issue-draft.md` |
| **BUG-03** | `P4-002; MAT-C-001` | `MAT-C-001; MAT-C-004` | #41 | Custom concrete deck density omitted from deck self-weight grillage load and permanent load summary | FIXED & VERIFIED | `P4-001-comment-for-issue-148.md (related #41 tracked in register)` |
| **BUG-04** | `P8-005 (Issue #20)` | `MAT-S-001; MAT-C-004` | #20 | Custom girder steel density ignored in MaterialProperties, grillage SW load, and permanent load summary | FIXED & VERIFIED | `P8-005-custom-steel-density-followup-20.md` |
| **BUG-05** | `P8-001` | `MAT-S-001` | #118 | Steel shear modulus G (and E) rounded to one decimal place (76.923 -> 76.9 GPa) in Material Properties dialog | FIXED & VERIFIED | `P8-001-modulus-input-precision-followup-118.md` |
| **BUG-06** | `P11-001; P11-002` | `MAT-S-004; MAT-S-005` | #43 | Cross-bracing and end-diaphragm designs ignore selected/custom steel materials and Steel Results Table clones girder properties | FIXED & VERIFIED | `P11-001-cross-bracing-material-mapping-draft.md; P11-002-end-diaphragm-material-mapping-draft.md` |
| **BUG-07** | `P4-003; P11-003` | `INV-007; OSI-003` | #130 | Backend validators, input normalization, and OSI loader accept non-finite numeric values (NaN, Inf, -Inf, 1e999) | FIXED & VERIFIED | `P11-003-nonfinite-input-validation-draft.md` |
| **BUG-08** | `P5-001` | `RUN-001` | #125 | 66 stale optimized girder section, segment-table, and stiffener values persist after 30->32->30 m same-instance designs | FIXED & VERIFIED | `P5-001-followup-for-issue-125-draft.md` |
| **BUG-09** | `P5-002; P8-004` | `DICT-005; ADV-003` | #125 | 119 stale G4/G3G4 dynamic input keys and 42 G4 output keys persist in live dicts after 3->4->3 girder change | FIXED & VERIFIED | `P8-004-stale-dynamic-girder-keys-draft.md` |
| **BUG-10** | `P8-003` | `CAD-003; CAD-005` | #85 | 3D CAD viewport renders black/empty after same-instance redesign until manual component toggle | FIXED & VERIFIED | `P8-003-cad-redraw-draft.md` |
| **BUG-11** | `P8-002` | `DICT-004` | New draft (distinct from #121) | Generated LaTeX design report fails compilation (Misplaced \noalign) across 47 captioned longtables | FIXED & VERIFIED | `P8-002-report-latex-caption-draft.md` |
| **BUG-12** | `P13-001 (Issue #19)` | `OSI-002` | #19 | Loading custom-material OSI then running _prime_material_inputs() errors on girder and wipes custom deck properties | FIXED & VERIFIED | `P13-001-custom-osi-priming-followup-19.md` |
| **BUG-13** | `OBS-13; P13-002 (Issue #113)` | `CAD-004` | #113 | Omitted edge_dist, shifted G2..G(n+1) naming, n_girders=n_l, and blind [1:-1] slicing scramble girder mapping across analysis, DCR, docks, dialogs, reports, and plots | FIXED & VERIFIED | `P13-002-plot-output-girder-index-followup-113.md` |
| **BUG-14** | `OBS-14; P14-001 (ADV-007 / ADV-003)` | `ADV-007; ADV-003` | New draft (related #125) | Design Mode switching (Optimized <-> Custom) unconditionally overwrites unrelated user inputs, injects mm^2 values into m^2 area fields, clobbers railing width, retains stale custom stiffeners, and fails to prune reduced cross-bracing dynamic keys | FIXED & VERIFIED | `P14-001-design-mode-switch-mutation-draft.md` |
| **REF-01** | `BUG-002` | `OSI-001` | None | Prior standard-OSI load restoration observation (resolved non-defect) | RESOLVED NON-DEFECT | `BUG-002-osi-load-restoration-candidate.md` |

### Phase 14b Final Closure Notes
- Resolved `OBS-13` as **`BUG-13`** across `analysis_results.py`, `plategirderbridge.py`, `designer.py`, and `steel_design.py`, verified by baseline-failing / candidate-passing unit tests and live GUI 3-girder & 4-girder alignment + 50-page Tectonic PDF compilation.
- Resolved `OBS-14` as **`BUG-14`** across `defaults.py`, `plategirderbridge.py`, `boq_generator.py`, and `input_dock.py`, verified by baseline-failing / candidate-passing unit tests (`21/21 OK` on candidate vs `36 failures, 2 errors` on baseline) and live GUI `run_bug14_and_adv003_gui_regression.py` (`7/7 PASS` on candidate vs `2/7 FAIL` on baseline — 0 unrelated mutations, `crash_barrier.area` in `m²`, 0 stale stiffeners, and `ADV-003` 29→3 with 0 stale input/output keys).
- Preserved the corrected baseline deck crack-width failure (`wk_bot = 0.3524 mm > 0.30 mm`, exposed by `BUG-01`) transparently as engineering evidence — never suppressed.
