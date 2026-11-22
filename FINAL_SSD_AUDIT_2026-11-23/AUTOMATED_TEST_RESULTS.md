# Automated Test Results

## Environment

Tests ran from an isolated `git archive` of commit `cffc9ef9ec3e9d33814258cadbba81c1e890e881` under `/FINAL_SSD_AUDIT_2026-11-23/scratch`. Runtime: Python 3.12.16, PySide6/OpenSeesPy/SciPy/pythonocc-core from `/Volumes/OsdagBridgeEnv/envs/osdagbridge-macos`. `PYTHONPATH=src`, Qt Cocoa plugin path, and `MPLBACKEND=Agg` were set. No package installation was performed.

## Executed test suites

| Suite | Command | Result |
|---|---|---|
| Unit suite | `python -m unittest discover -s tests/unit -p 'test*.py' -v` | **32 passed**, 0 failed, 0 skipped |
| Phase 20 regressions | `python tests/phase20/test_phase20_bug25_to_30_conda.py src` | **6 passed**, 0 failed, 0 skipped |
| Phase 22 evidence check | `python tests/integration/check_phase22_evidence.py` | PASS on supplied records, then PASS after fresh solver/report regeneration; includes six records, two repeats, report FAIL/utilization and Table 2.7 backend dimensions |

Total tests actually passed in the two test suites: **38**. Warnings during fresh solver runs were for intentionally absent footpath/railing/median components, unavailable thermal cases, and optional LaTeX integration; no run failed because of them.

## Fresh numerical runs

`tests/integration/phase22_probe.py` was run independently for indices 0–5, then repeated for indices 3 and 4. All eight commands exited 0. The repeated fields agreed with the recorded cases. Reproduction showed 1.49% steel-weight shortfalls for both skew cases. This is evidence of software repeatability for the configured cases, not structural acceptance.

The diagnostic PDF generator `tests/integration/phase22_pdf.py` completed in scratch. The newly generated PDF is 49 pages; the evidence checker passed on its extracted text and stored backend records. Its scratch hash is `aa14bf131431720cf3a5ab01f560a48f52f3221dbfaaaff5c0f1a9b00ef2439d` (timestamps can vary; this is not the published PDF hash).

## Not run / not available

- Full `pytest -q`: **NOT RUN** because `pytest` is not installed (`No module named pytest`). No dependency was installed under the audit-only constraint.
- Other-platform GUI/native CAD execution: NOT VERIFIED.
- Independent engineering acceptance: NOT VERIFIED and explicitly outside these software tests.

An earlier attempt without the documented Qt plugin environment terminated before test completion; it is not counted. A bulk compileall attempt encountered AppleDouble metadata sidecars created by the SSD filesystem; syntax verification was completed instead by parsing all actual Python payloads (229 files, zero errors). The correctly configured reruns above produced the reported results.
