# Phase 21 Hotfix Report

Date: 2026-11-23  
Baseline: `de45927e53e5309f4c5ec43e2dc2579843f1b8ba` (`phase20-thermal-issue92`)  
Working branch: `phase21-submission-hotfix`

## Outcome

Phase 21 corrects explicit girder steel density propagation and fixes longitudinal result-line mapping for skewed bridges. A fresh 3-girder/4-girder solver matrix completed for 0°, +5°, and -5° skew. The Phase 20 checkout remains preserved in its own worktree and branch.

Issue #20 is fixed for the tested path. The real `KEY_MATERIAL_GIRDER_DENSITY` input is now an explicit override for database and custom grades, is validated as a finite 50–120 kN/m³ value, and is converted to N/m³ for `SteelProperties`. If absent, database density is retained; custom grades keep the historical 78,500 N/m³ default. The broad `TypeError` fallback that silently retried self-weight with a default density was removed.

Issue #113 is **partially fixed**. Result mapping, physical girder count, and per-girder output/report keys now exclude EB1/EB2 consistently, including under tested skew. However, edge longitudinal lines still use the full main girder section. The solver matrix confirms this (`edge_section_matches_full_girder: true`); consequently the physical load sharing and girder demand remain unresolved. No replacement slab-strip section was introduced without a validated model.

## Numerical comparison

For the same 25 m, 3-girder, 0° DB-grade E350A bridge case with explicit density input 85 kN/m³, Phase 20 ignored the override while Phase 21 applied it:

| Quantity | Phase 20 | Phase 21 |
|---|---:|---:|
| Effective steel density | 78.5 kN/m³ | 85.0 kN/m³ |
| Main-girder self-weight line load | 1,874.59 N/m | 2,029.81 N/m |
| Sum of 3 girder self-weight over 25 m | 140.594 kN | 152.236 kN |
| ULS envelope peak Mz | 2,717.88 kN·m | 2,727.62 kN·m |
| SLS envelope peak Mz | 1,908.63 kN·m | 1,915.85 kN·m |
| ULS envelope peak vertical displacement | 103.01 mm | 103.39 mm |
| Design girder count | 3 | 3 |

The applied line load changes by the expected density ratio (85 / 78.5) with section area held at 0.02388012 m². The comparison verifies propagation and solver response; it does not validate the unresolved edge-line stiffness model.

## Girder matrix

All six end-to-end solver cases completed: default 3-girder with overhang; custom 85 kN/m³ 3-girder with overhang; default 4-girder with overhang; 3-girder at +5°; 4-girder at -5°; and 3-girder with zero overhang. Result handler names, design counts, report per-girder keys, and load-effect cache keys agreed in each case. Positive-overhang maps were EB1, G1…Gn, EB2; zero-overhang maps were G1…Gn.

For the custom 85 kN/m³ case, the generated application report contains `Steel Self-Weight Applied 85.0 kN/m3` and G1, G2, G3 only. The diagnostic report itself is not a submission report: this fixture has overall design status Fail (maximum reported utilization 2.16) and the run excluded figure bytes, leaving report figure placeholders.

## Warnings and limits

- All solver runs without thermal inputs emit missing `thermal_load` warnings while forming combinations. The matrix cases also omit footpath, railing, and median components, which generate corresponding skip warnings.
- The ±5° solver runs completed but emitted hundreds of SciPy “iteration is not making good progress” warnings. Their results should be treated as provisional until investigated with convergence and equilibrium checks.
- The test matrix verifies girder self-weight line load and total applied weight from section area × density × length. It does not establish physical edge-strip stiffness or validate total transverse load distribution against a slab-strip model.
- The generated report was compiled by the real Tectonic engine through an adapter for the application's `pdflatex` invocation because the bundled `osdag_latex_env`/pdflatex executable was unavailable. The app report generator itself was used unchanged.
- The Phase 20 focused comparison is a fresh run from the preserved baseline commit; no Phase 20 source or evidence was replaced.

## Decision

Phase 21 is safer than Phase 20 for the two reported software defects: density now affects actual analysis loads, and tested skewed mappings no longer collapse the physical girders to G1. It is **not yet cleared as an engineering submission candidate** because positive-overhang edge members retain full main-girder stiffness, skew cases report convergence warnings, and the diagnostic report fixture fails design checks. Resolve and verify those items with an appropriate edge slab-strip model and independent load-equilibrium/simple-span checks before claiming engineering correctness.

See `PHASE21_REGRESSION_RESULTS.md`, `PHASE21_CHANGED_FILES.md`, and `PHASE21_SUBMISSION_READINESS.md` for test details and publication status.
