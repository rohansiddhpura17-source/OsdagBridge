# Source Code Audit

## Scope and result

Inspected the Phase 22.1 commit diff, all final tracked Python source and test files, the application README/license, report-generation changes, and related package artifacts. The final commit changes 17 paths: two added technical/reproduction documents, eight evidence/generated report artifact paths, seven report or verification source/test files. No structural solver, analysis, load, stiffness, or design-check implementation file is changed from Phase 22.

All **229** Python files in the final source/test tree pass Python AST parsing. A bulk `compileall` attempt also encountered filesystem-generated AppleDouble `._*.py` metadata sidecars containing null bytes; AST parsing was then run only on actual `.py` payloads and reported no syntax errors. The isolated unit and legacy regression suites pass. The source patch applies in check mode to the Phase 22 source archive; Git reports executable-mode warnings for seven paths while returning success. The audit did not install dependencies or edit source.

## Reviewed changes

- `src/osdagbridge/core/reports/chap1.py`: report chapter text, image presentation and limitations disclosure.
- `src/osdagbridge/core/reports/chap2.py:240`: `section_mm()` multiplies stored metre dimensions by 1,000 for display; missing values remain blank. The six displayed dimensions match the backend millimetre fields in all three rows.
- `src/osdagbridge/core/reports/executive_summary.py`: result summary continues to show the backend failure and 2.16 utilization.
- `tests/integration/phase22_cad.py`, `phase22_pdf.py`, `check_phase22_evidence.py`, and `run_phase21_report.py`: report capture/regeneration and evidence checks. These do not alter engineering calculations.

## Findings

### P2 — Unconditional debug output in model/report path

**File:** `/Volumes/PortableSSD/OsdagBridge-screening-2026/phase22.1-submission-polish/src/osdagbridge/core/bridge_types/plate_girder/plategirderbridge.py:3735` and `:3843` (printed input interpretation and stiffener values). The fresh solver/report run emitted these diagnostics. Other unguarded report-worker diagnostics remain in `src/osdagbridge/desktop/ui/template_page.py:1379` and nearby lines.

**Impact:** noisy console output and possible exposure of user-supplied design values in logs. No numerical effect was identified in the tested runs.

**Recommendation:** use module logging at an appropriate level or guard diagnostics behind an explicit environment flag.

### P2 — Full pytest suite not independently runnable

The installed Python environment lacks `pytest`; `python -m pytest -q` stops immediately with `No module named pytest`. The requested unittest/regression suites and solver evidence checks did run. Do not treat this as a source defect or claim a full pytest run.

### Review limits

AST parsing checks syntax, not every dynamic import or GUI state. The final branch tests cover listed fixtures only. Positive-overhang EB1/EB2 properties and skew load application are not certified by this source audit. No engineering calculation was changed.
