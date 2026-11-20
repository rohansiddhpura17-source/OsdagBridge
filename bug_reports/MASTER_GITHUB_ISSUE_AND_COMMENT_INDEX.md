# Master GitHub Issue & Comment Draft Index (Unified Phase 18 Submission)

**Baseline Commit:** `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3` (`dev` branch, read-only)  
**Verified Candidate Patch:** `scripts/isolated-candidate-fixes-phase16.patch` (17 fixed defects)  
**Separate Experimental Thermal Patch:** `phase17_experimental_thermal/patches/experimental-phase17-thermal-mitigation.patch` (fail-closed mitigation only; `#92` remains UNRESOLVED)  
**Publication Status:** **ALL DRAFTS ARE LOCAL ONLY. ZERO REMOTE GITHUB WRITES PERFORMED.**

Recheck live upstream issues immediately before any user-approved publication.

| ID | Status | Upstream Issue / Disposition | Action on Approval | Local Draft Path(s) |
|---|---|---|---|---|
| **BUG-01** | FIXED & VERIFIED (17-fix) | #148 | Comment on #148 | `bug_reports/P4-001-comment-for-issue-148.md` |
| **BUG-02** | FIXED & VERIFIED (17-fix) | Separate draft (rel. #148, #41) | New issue (reference #148, #41) | `bug_reports/P4-001-separate-excel-issue-draft.md` |
| **BUG-03** | FIXED & VERIFIED (17-fix) | #41 | Comment on #41 / #148 | `bug_reports/P4-001-comment-for-issue-148.md (related #41 tracked in register)` |
| **BUG-04** | FIXED & VERIFIED (17-fix) | #20 | Comment on #20 | `bug_reports/P8-005-custom-steel-density-followup-20.md` |
| **BUG-05** | FIXED & VERIFIED (17-fix) | #118 | Comment on #118 | `bug_reports/P8-001-modulus-input-precision-followup-118.md` |
| **BUG-06** | FIXED & VERIFIED (17-fix) | #43 | Comment on #43 | `bug_reports/P11-001-cross-bracing-material-mapping-draft.md`; `bug_reports/P11-002-end-diaphragm-material-mapping-draft.md` |
| **BUG-07** | FIXED & VERIFIED (17-fix) | #130 | Comment on #130 | `bug_reports/P11-003-nonfinite-input-validation-draft.md` |
| **BUG-08** | FIXED & VERIFIED (17-fix) | #125 | Comment on #125 | `bug_reports/P5-001-followup-for-issue-125-draft.md` |
| **BUG-09** | FIXED & VERIFIED (17-fix) | #125 | Comment on #125 | `bug_reports/P8-004-stale-dynamic-girder-keys-draft.md` |
| **BUG-10** | FIXED & VERIFIED (17-fix) | #85 | Comment on #85 | `bug_reports/P8-003-cad-redraw-draft.md` |
| **BUG-11** | FIXED & VERIFIED (17-fix) | New draft (distinct from #121) | New issue (distinct from #121) | `bug_reports/P8-002-report-latex-caption-draft.md` |
| **BUG-12** | FIXED & VERIFIED (17-fix) | #19 | Comment on #19 | `bug_reports/P13-001-custom-osi-priming-followup-19.md` |
| **BUG-13** | FIXED & VERIFIED (17-fix) | #113 | Comment on #113 | `bug_reports/P13-002-plot-output-girder-index-followup-113.md` |
| **BUG-14** | FIXED & VERIFIED (17-fix) | New draft (related #125) | New issue (reference #125) | `bug_reports/P14-001-design-mode-switch-mutation-draft.md` |
| **REF-01** | RESOLVED NON-DEFECT | None | No GitHub issue (resolved non-defect) | `bug_reports/BUG-002-osi-load-restoration-candidate.md` |
| **BUG-15** | FIXED & VERIFIED (17-fix) | None found by targeted search | New issue (recheck upstream first) | `phase16/bug_reports/BUG-15-load-combination-factors-draft.md` |
| **BUG-16** | FIXED & VERIFIED (17-fix) | #65 | Comment on #65 | `phase16/bug_reports/BUG-16-issue-65-followup.md` |
| **BUG-24** | FIXED & VERIFIED (17-fix) | None found by targeted search | New issue (recheck upstream first) | `phase16/bug_reports/BUG-24-shear-spacing-table-status-draft.md` |
| **UPSTREAM-92** | UNRESOLVED (exp. guard sep.) | #92 | Comment on #92 (UNRESOLVED — evidence + blockers) | `phase16/bug_reports/UPSTREAM-92-independent-oracle-followup.md`; `phase18/bug_reports/UPSTREAM-92-phase17-thermal-investigation-comment-draft.md` |

## Summary Counts
- **17** verified candidate-fixed defects (`BUG-01`..`BUG-16`, `BUG-24`) in `scripts/isolated-candidate-fixes-phase16.patch`
- **1** resolved non-defect historical record (`REF-01`)
- **1** unresolved reproduced upstream issue (`UPSTREAM-92`) with separate experimental Phase 17 thermal investigation & fail-closed mitigation artifacts
- **0** remote GitHub issues, comments, pushes, or pull requests created
