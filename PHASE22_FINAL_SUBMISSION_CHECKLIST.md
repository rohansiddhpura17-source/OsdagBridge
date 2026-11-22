# Final submission checklist • 23 November 2026

**Recommendation A for the screening project, with the engineering limitations below disclosed. No-go for presenting a verified passing bridge design.** Phase 22 preserves the Phase 21 density and girder identity corrections, fixes a measured zero-overhang loading defect, and replaces misleading reaction totals. Phase 21 remains available if the submission scope requires the previously frozen branch. The tests give no reason to prefer Phase 20, which predates the density override and skew mapping corrections.

| Feature | Classification | Acceptance evidence or remaining limitation |
|---|---|---|
| Phase 21 preservation | VERIFIED | Phase 22 branched from 05377d1589e8e34fbbd3b9cc37860f40ab38cea1, whose parent is de45927e53e5309f4c5ec43e2dc2579843f1b8ba. Phase 20 and Phase 21 have separate worktrees. |
| Girder density and identities | VERIFIED | Six fixtures retain requested density and G1…Gn, with EB1/EB2 separate at positive overhang. |
| Zero-overhang steel self-weight | VERIFIED | Three loaded lines, total force, per-bearing reaction and sampled moment agree with independent straight-span references. |
| Positive-overhang edge stiffness | UNRESOLVED | Unsupported deck-edge lines share substantial longitudinal moment. An independent physically specified reference section is missing. |
| Coordinate inversion at ±5° | VERIFIED | Repeated runs, forward-map tests and zero MINPACK warnings on the tested meshes. |
| Skewed self-weight distribution | UNRESOLVED | Assembled load falls short by 1.49%. The endpoint trial worsened the discrepancy and was excluded. |
| SW equilibrium and reaction reporting | VERIFIED | All six fixtures balance the assembled SW force and moment. Both report reaction columns match signed support reactions to 0.001 kN. |
| PDF diagnostic | VERIFIED | Six populated figures and checked backend values, genuine FAIL, 2.16 utilization. |
| Native CAD capture | UNRESOLVED | Local viewer attempts crashed. The diagnostic uses projected OCC geometry. |
| Final bridge design | PARTIALLY VERIFIED | The reported checks ran. Positive-overhang demands and agreement between the analysis section and final optimized section require independent verification. |
| Regression | No REGRESSION observed in the final test set | 38 automated tests passed. The rejected endpoint trial was a regression in an experiment. |

**Submission contents.** Include this checklist with PHASE22_ENGINEERING_VALIDATION.md, PHASE22_NUMERICAL_EVIDENCE.md and the diagnostic under evidence/phase22/pdf. The upstream reply file is a draft for the contributor's review. Publication and changes to the existing release remain subject to the owner's approval.
