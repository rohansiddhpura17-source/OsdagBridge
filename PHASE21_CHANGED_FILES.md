# Phase 21 Changed Files

## Production code

- `src/osdagbridge/core/bridge_types/plate_girder/plategirderbridge.py` — explicit girder density input takes precedence for DB/custom grades, finite/range checks are applied, and the frozen `SteelProperties.rho` receives converted N/m³; removed the silent default-density `TypeError` fallback for self-weight generation.
- `src/osdagbridge/core/bridge_types/plate_girder/analysis_results.py` — replaces global-X endpoint pairing with connected longitudinal member paths, keeping EB1/EB2 separate from G1…Gn on skewed models.
- `src/osdagbridge/core/bridge_types/plate_girder/dto.py` — corrects the `SteelProperties.rho` unit documentation to N/m³.

## Tests and reproducibility

- `tests/unit/test_phase89_candidate_regressions.py` — adds density override/default/invalid-input checks, updates proportional self-weight expectation, and covers skewed longitudinal-line mapping.
- `tests/integration/run_phase21_engineering_matrix.py` — real solver matrix for 3G/4G, defaults/custom density, ±5° skew, overhang/zero overhang; records density, line loads, line mapping, report/cache key agreement, and warnings.
- `tests/integration/run_phase21_report.py` — generates a real backend report and compiles it with Tectonic for density/girder-label consistency checks.

## Evidence and deliverables

- `evidence/` — matrix JSON/log, Phase 20 comparison, full Phase 21 run, report-generation log, pre-fix skew mapping snapshot, generated diagnostic PDF/TeX/text, and rendered pages.
- `PHASE21_HOTFIX_REPORT.md` — implementation findings, baseline comparison, limits, and decision.
- `PHASE21_REGRESSION_RESULTS.md` — commands and exact test, solver, and PDF outcomes.
- `PHASE21_CHANGED_FILES.md` — this file.
- `PHASE21_SUBMISSION_READINESS.md` — release gate and exact local publication commands.
- `evidence/phase21-hotfix.patch` — reviewable code/test diff from the preserved Phase 20 baseline.

The edge-line section assignment was inspected and recorded but was not changed because an appropriate slab-strip section/stiffness model was not validated. No GitHub issues/comments were modified and no changes were pushed.
