# Phase 20 — Thermal Load Implementation Report (Upstream Issue #92)

Candidate branch `phase20-thermal-issue92`; baseline `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3`; commits `2794f3e` (Phase 19 Conda refinements) and `370191e` (Issue #92).

## 1. Problem (reproduced on untouched baseline)
- Canonical Temperature Load inputs (air temperatures, steel/RCC CTE) are ignored: Issue #92 inputs (65/−10 °C, 20e−6/10e−6) and comparison inputs (45/5 °C, 11.7e−6) give identical Envelope ULS Mz = **1633.8066** vs **1633.8066 kNm**, with no thermal load cases.
- The legacy `temperature_load_kN_m2 = 2.5` is applied as a **vertical deck pressure**, producing a spurious `1.0 TL` Mz = 277.2194 kNm and dy = 10.8407 mm.

## 2. Engineering formulation
- IRC:6-2017 Cl. 215 (Amendment No. 6 / No. 8 text; Amendment No. 10 retitles the clause "Thermal Effects"; Amendment No. 9 concerns Cl. 203 and is not used): effective bridge temperature range from shade air temperatures, bridge-setting temperature band about the mean air temperature, uniform rise/fall, and Cl. 215.4 nonlinear heating/cooling gradients for composite decks.
- Composite section: layered strip integration over slab + steel with exact strip self-inertia term `E_i·κ·w·h³/12`; transformed `A_eq`, `Iz_eq` used for stiffness when thermal analysis is active, while girder self-weight still uses bare-steel area.
- `designer.py` uses stiffness ratio 1.0 when composite girder sections are already in the grillage (no double counting).
- `ThermalElementLoad` (ospgrillage) applies equivalent fixed-end axial force and moment per element in local axes, transformed to global; supports/bearings via explicit `zeroLength` longitudinal springs; reactions exposed via `ReactionComponent`; spring ground nodes excluded from connectivity BFS.
- Five load cases: `TL_UNIFORM_RISE`, `TL_UNIFORM_FALL`, `TL_GRADIENT_HEAT`, `TL_GRADIENT_COOL`, governing `1.0 TL`; wired into ULS/SLS combinations (e.g. `BASIC_3 … + 1.5TL`).
- Fail-closed guards: non-zero legacy `temperature_load_kN_m2` → `ValueError` (backend and OSI validator); |skew| > 15° → `ValueError`; inverted temperature ranges and non-finite values rejected.
- Reports: Ch. 3 Table 3.6 (CTE, effective temperatures), Ch. 4 reactions + Thermal Analysis Summary, Ch. 8 code basis and scope limits; Results/Excel builder thermal tables.

## 3. Scope and limitations
Resolved for **single-span composite plate-girder bridges with |skew| ≤ 15°** (longitudinal girder thermal action). **Out of scope:** transverse slab expansion across Z-restrained bearings, and continuous multi-span bridges. These limits are stated in Ch. 8 of the generated report.

## 4. Analytical oracle benchmarks (15/15 PASS)
| ID | Benchmark | Expected | Actual | Rel. error | Status |
|---|---|---|---|---|---|
| BM-01 | Zero Delta-T null state | 0.0 | 0.0 | 0.0 | PASS |
| BM-02 | Free uniform thermal expansion (Pinned-Roller) | 0.007200000000000001 | 0.007199999999999998 | 3.614007241618348e-16 | PASS |
| BM-03 | Fully restrained uniform thermal compression (Pinned-Pinned) | 3360000.0 | 3360000.0000000005 | 1.3858966884158905e-16 | PASS |
| BM-04 | Series stiffness with two zeroLength bearing springs | 86709.67741935485 | 86709.67741935479 | 5.801772339669455e-15 | PASS |
| BM-05 | Uniform heating vs cooling sign & linear proportionality | -0.6 | -0.5999999999999998 | 3.7007434154171886e-16 | PASS |
| BM-06 | IRC:6 Cl.215.4 heating gradient upward camber & zero secondary moment | 0.007561053653871764 | 0.007561053653871795 | 4.129718422457329e-15 | PASS |
| BM-07 | IRC:6 Cl.215.4 cooling gradient downward deflection | -0.0013114342572589364 | -0.0013114342572589427 | 4.7950345704400165e-15 | PASS |
| BM-08 | Composite differential CTE (20e-6 vs 10e-6) uniform-dT thermal bowing | -0.00024295181652022728 | -0.0002429518165202283 | 4.127925544716373e-15 | PASS |
| BM-09 | Fixed-Fixed restrained thermal curvature bending moment | 1000000.0 | 1000000.0 | 0.0 | PASS |
| BM-10 | 3D support reaction global force & moment equilibrium | 0.0 | 1.864137190988461e-09 | 1.864137190988461e-09 | PASS |
| BM-11 | Skew +-15 deg Oblique grillage free thermal expansion & R transform | 0.0072 | 0.0072 | 7.228014483236697e-16 | PASS |
| BM-12 | Mesh refinement independence (nt=5, 9, 17) | [218978.10218978103, 0.00864] | [218978.10218978036, 0.008639999999979402] | 2.3840401103875702e-12 | PASS |
| BM-13 | First-principles K*q - f_th local/global element recovery | 0.0 | 1.3969838619232178e-09 | 5.174014303419326e-16 | PASS |
| BM-14 | Full-bridge (192-element) ULS/SLS thermal superposition & bare-steel SW | 0.0 | 5.434267222881317e-07 | 7.617738623287046e-08 | PASS |
| BM-15 | Strict scope guards (legacy/skew>15/inverted) & nonthermal invariance | False | False | 0.0 | PASS |

## 5. Baseline vs candidate (Issue #92 inputs)
| Case | Baseline | Candidate |
|---|---|---|
| A: 65/−10 °C, 20e−6/10e−6 — Env. ULS Mz | 1633.8066 kNm, 0 TL cases | 3071.6366 kNm, 5 TL cases |
| B: 45/5 °C, 11.7e−6 — Env. ULS Mz | 1633.8066 kNm | 2809.8823 kNm |
| C: legacy 2.5 kN/m² | vertical pressure, Mz 277.2194 kNm | ValueError (rejected) |
| D: nonthermal | — | 0 TL cases, composite sections = False |

Candidate Case A solver summary:

| Load case | dx max (mm) | dy mid (mm) | N max (kN) | Mz max (kNm) | Rx residual (kN) |
|---|---|---|---|---|---|
| TL_UNIFORM_RISE | 15.217423 | -23.82887 | 1847.132512 | -303.803783 | 0.0 |
| TL_UNIFORM_FALL | -15.217423 | 23.82887 | -1847.132512 | 303.803783 | 0.0 |
| TL_GRADIENT_HEAT | 1.758523 | 5.761778 | 213.454304 | 73.459206 | 0.0 |
| TL_GRADIENT_COOL | -0.319693 | -1.118041 | -38.805182 | -14.254353 | 0.0 |
| 1.0 TL | 16.975945 | -18.067092 | 2060.586817 | -230.344576 | 0.0 |

## 6. Regression results
- Historical unit regressions: 28 ran, OK.
- BUG-25..30 Conda regressions: baseline FAILED (failures=6); candidate 6 ran, OK.
- Live PySide6 GUI — Issue #92 workflow (7/7):
- `gui_design_completed_with_thermal_cases`: PASS
- `gui_cad_3d_nonblank`: PASS
- `gui_plots_rendered_png`: PASS
- `gui_osi_save_and_reload_valid`: PASS
- `gui_osi_rejects_legacy_temperature_pressure`: PASS
- `gui_report_pdf_compiled_with_thermal_tables`: PASS
- `gui_results_builder_tables_populated`: PASS
- Live GUI — BUG-14/ADV-003: baseline 2/7 (defect reproduced), candidate 7/7.
- Live GUI — prior-fix revalidation: 15/15 (includes preserved corrected crack-width failure, BUG01 assertion).

## 7. Patches
- `phase20_thermal_issue92_isolated.patch` (106600 bytes): `git apply --check` PASS on commit `2794f3e`.
- `phase20_combined_all_fixes.patch` (231168 bytes, 34 source files, excludes tracked `._*` AppleDouble junk present in history): `git apply --check` on baseline `d74f56d` → PASS.
