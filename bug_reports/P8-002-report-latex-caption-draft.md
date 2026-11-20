# Local Draft Issue — NOT POSTED

## Title
[Bug] Generated LaTeX design report fails compilation (`Misplaced \noalign`) at 47 captioned `longtable`s

**Status:** LOCAL DRAFT (DO NOT PUBLISH WITHOUT EXPLICIT APPROVAL)  
**Defect ID:** BUG-11 / P8-002 (`DICT-004`)  
**Related Existing Issues:** Distinct from `#121` (which concerns repeated multipage headers, not caption syntax compilation failure)

## Reproduction
1. Run a baseline design at commit `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3` (`dev` branch).
2. Generate the design report `.tex` and compile using Tectonic / `pdflatex`.
3. Compilation aborts with `Misplaced \noalign` at the first captioned `longtable` (`chap2.py:170-173`); no PDF is produced.

## Root Cause
Forty-seven captioned `\begin{longtable}` blocks across four report modules omit the mandatory `\\` row break between `\caption{...}` and `\hline`:
- `src/osdagbridge/core/reports/chap2.py` (8 tables)
- `src/osdagbridge/core/reports/chap3.py` (7 tables)
- `src/osdagbridge/core/reports/chap4.py` (2 tables)
- `src/osdagbridge/core/reports/chap5.py` (30 tables)

## Candidate Fix & Verification
Added `\\` immediately after `\caption{...}` on all 47 captioned `longtable` blocks across `chap2.py`, `chap3.py`, `chap4.py`, and `chap5.py`.
- **Unit regression:** `test_captioned_longtables_start_a_caption_row_break_across_all_chapters` — FAIL on baseline, PASS on candidate (`>= 40` tables verified).
- **Full Tectonic LaTeX PDF compilations on candidate (0 compiler errors):**
  - `evidence/phase11-report-fix/candidate-pass2/full-report.pdf` (43 pages, 234,555 bytes, 45,535 extracted chars)
  - `evidence/phase12-report-check/run11-custom4g/report-4g.pdf` (47 pages, 244,837 bytes, 49,472 extracted chars)
  - `evidence/phase12-candidate-integration/report-4g/cand-4g-report.pdf` (47 pages, 244,139 bytes, 48,778 extracted chars)
