# README Review

## Local final branch

File: `/Volumes/PortableSSD/OsdagBridge-screening-2026/phase22.1-submission-polish/README.md` (305 lines). The README identifies Rohan Siddhpura as screening contributor, gives the fork URL, describes the screening scope, and acknowledges FOSSEE/IIT Bombay. Internal Markdown targets resolve. Headings and tables render as normal Markdown.

### P1 — Incorrect license statement

Lines 8, 280 and 304 label the project MIT. The adjacent `LICENSE` is GNU GPL version 3; GitHub API also reports `GPL-3.0`. This is a material licensing contradiction. Correct the badge, tree comment and License section to match the actual rights holder/source license, after confirming contribution licensing.

### P2 — Stale CI statement

Line 319 references `.github/workflows/ci.yml`; the final commit has only `.github/workflows/conda-publish.yml`. The README statement is unsupported by the tracked workflow. Correct the target or remove that claim.

The README's general install section is less complete than the Phase 22.1 reproduction guide (which correctly describes the machine-specific Osdag environment). The PDF/release also carry explicit engineering limits, which should remain prominent.

## Public GitHub default README

The repository default branch is `dev`. GitHub renders that branch's older project README, which also says MIT while the published LICENSE/API identify GPL-3.0. The Phase 22.1 branch is published, but it is not the default branch. Therefore the public landing page is not a reliable summary of this screening submission and repeats the license conflict.

**Status: not publication-ready** until the license and workflow references are resolved. Do not infer upstream acceptance or engineering approval from the README.
