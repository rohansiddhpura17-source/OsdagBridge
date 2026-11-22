# FOSSEE OsdagBridge Complete SSD Audit

**Audit date:** 23 November 2026  
**Mode:** Read-only audit; reports and isolated test/render work only in this directory.  
**Final source:** branch `phase22.1-submission-polish`, commit `cffc9ef9ec3e9d33814258cadbba81c1e890e881` (parent Phase 22 fallback `90f3fef48e7e9cfa5a615fbe0248b58aafc7f7ff`).

## Executive result

The local final branch and Phase 20, 21 and 22 worktrees are clean. The final branch is based directly on Phase 22.1 and its GitHub branch and release tag resolve to the expected commit. The published submission ZIP is intact and its SHA-256 matches the expected `bf5b58e38492700193e5a975f2fc8e2a9e1dd4cf56068c36a48491e953eb5e7e`.

The 49-page diagnostic regenerates in an isolated copy from the actual solver path. Its plan image is visible and matches the fixture geometry; Table 2.7 shows the expected millimetre dimensions; the check result remains **FAIL** with reported utilization **2.16** (backend **2.1576**). The numerical evidence checker passes, and 38 unit/regression tests pass. Six fresh solver cases and two fresh skew repeats also complete, with the recorded skew self-weight shortfall.

**The package is not ready to represent as an engineering-accepted design.** Positive-overhang EB1/EB2 stiffness remains unvalidated; skew self-weight remains 1.49% low; the diagnostic genuinely fails. The diagnostic also contains two unclosed design-check reporting inconsistencies, conflicting standards-year citations, and the README says MIT although the LICENSE is GPL-3.0. These findings require correction or explicit disclosure before calling the currently published package final.

## Inventory and worktree scope

The project tree contains **8,774 files** (about 880 MB) inventoried and SHA-256 hashed, excluding Git internals, the sparsebundle backing store, and this audit output. The inventory includes historical phases, submission artifacts, AppleDouble metadata, caches, and duplicate evidence; it is not a claim that every historical file received semantic review. All 229 Python files in the final tracked source/test tree parsed successfully with `ast.parse`.

The root had 70 `.pdf`-named paths: **53 valid PDF paths**, plus 17 AppleDouble sidecars. The valid PDFs comprise 19 unique byte streams and **1,955 pages** across all paths, including identical copies. All opened with Poppler, had metadata/text extracted, and were rendered page-by-page into contact sheets; no text-empty page was found. The diagnostic and final technical report were separately inspected at page scale. See `PDF_INVENTORY.csv` and `PDF_VISUAL_AUDIT.md`.

## Verification run

- 32 unit tests: PASS.
- 6 Phase 20 regression tests: PASS.
- **38 tests passed; 0 failed; 0 skipped** across these two suites.
- Six fresh solver cases and two repeated skew runs: PASS to completion; repeatability and numerical evidence checker passed.
- Fresh diagnostic report generation and evidence checker: PASS; 49 pages.
- ZIP internal test and all 33 SHA256SUMS entries: PASS.
- Source patch `git apply --check` against a Phase 22 archive: exit 0, with file-mode warnings on seven executable files.
- Full `pytest -q`: NOT RUN; the environment does not have `pytest` (`No module named pytest`). No dependencies were installed.

## Findings

| Severity | Count | Summary |
|---|---:|---|
| P0 — Submission-blocking | 0 | None found |
| P1 — Important | 4 | End-diaphragm PASS content conflicts with “Not assessed”; two brace ratios disagree with displayed demand/capacity; README license mismatch; standards editions conflict |
| P2 — Minor | 5 | Missing README CI workflow reference; debug output remains; source archive omits non-source tracked docs/fixtures; unspecified load inputs display N/A; some isometric labels are small |
| P3 — Cosmetic | 0 | None recorded |

Each issue and correction is described in `CRITICAL_ISSUES_TO_FIX.md` and the topic reports.

## Evidence-based ratings

| Category | Score | Evidence |
|---|---:|---|
| Source-code quality | 7/10 | 229 final-tree Python files AST-parse; changed Phase 22.1 files are report/presentation and verification code; six unguarded debug prints remain in the plate-girder generator. |
| Software functionality | 7/10 | 38 tests and eight fresh solver runs pass; tested scenarios do not validate the whole input space or structural model. |
| Regression testing | 8/10 | All requested unit and legacy regressions pass; the full pytest suite is unavailable in this environment. |
| Numerical verification | 6/10 | Density, zero-overhang control, equilibrium, and repeatable solver records verified; skew load deficit and overhang stiffness remain open. |
| Engineering acceptance readiness | 2/10 | The submitted diagnostic fails at 2.16; positive-overhang and skewed designs are explicitly unaccepted. |
| PDF formatting | 7/10 | Key plan and units are corrected and legible; summary/table inconsistency, brace ratios and standards citations remain. |
| Documentation quality | 7/10 | Phase reports disclose limitations and reproduction steps; standard editions and result-summary defects need reconciliation. |
| README professionalism | 4/10 | Screening contribution is identified, but the stated MIT license conflicts with GPL-3.0 and the referenced CI file is absent. |
| GitHub presentation | 7/10 | Public repository, branch, release and asset hash agree; the default branch remains `dev` and its README has the license conflict. |
| Submission completeness | 8/10 | ZIP, manifest, evidence, patch and reproduction guide are present; source archive omits some non-source tracked material. |

## Verdict

**NO-GO for calling the published package a clean final submission until the four P1 reporting/licensing findings are corrected or explicitly resolved.** The verified software changes and bounded screening evidence are suitable for FOSSEE software screening after that polish. **NO engineering acceptance** is supported: the diagnostic fails and the overhang/skew limitations remain unresolved. No source or publication changes were made during this audit.
