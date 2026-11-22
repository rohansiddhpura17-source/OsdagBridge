# Phase 21 Regression Results

Runtime: mounted macOS Python 3.12.16 environment, PySide6 6.9.3, OpenSeesPy 3.8.0. Unit tests were run with `QT_QPA_PLATFORM=cocoa` and the mounted Qt plugin path.

## Unit tests

Command:

```sh
rtk env PYTHONPATH=src QT_QPA_PLATFORM=cocoa QT_QPA_PLATFORM_PLUGIN_PATH=/Volumes/OsdagBridgeEnv/envs/osdagbridge-macos/lib/python3.12/site-packages/PySide6/Qt/plugins/platforms /Volumes/OsdagBridgeEnv/envs/osdagbridge-macos/bin/python -m unittest tests.unit.test_phase89_candidate_regressions tests.unit.test_phase15_regressions tests.unit.test_analyser tests.unit.test_designer tests.unit.test_io tests.unit.test_phase11_nonfinite -v
```

Result: **31 passed, 0 failed**.

Coverage includes explicit database-grade density override and kN/m³→N/m³ conversion; database/custom defaults; invalid/non-finite density rejection; proportional self-weight load scaling; and 3-/4-girder mappings with overhang, zero overhang, and signed skew fixtures.

## End-to-end solver matrix

Command:

```sh
rtk env PYTHONPATH=src QT_QPA_PLATFORM=cocoa QT_QPA_PLATFORM_PLUGIN_PATH=/Volumes/OsdagBridgeEnv/envs/osdagbridge-macos/lib/python3.12/site-packages/PySide6/Qt/plugins/platforms /Volumes/OsdagBridgeEnv/envs/osdagbridge-macos/bin/python tests/integration/run_phase21_engineering_matrix.py evidence/phase21_engineering_matrix.json
```

Result: **6 completed, 0 failed**. Cases cover default 3G/4G, custom-density 3G, +5°/−5° skew, positive overhang, and zero overhang. For each case, configured count, result handler, design result, report keys, and load-effect cache keys agree. No phantom G5/G6 design results appear in four-girder reports. Full case records, captured Python warnings, and stdout/stderr are in `evidence/phase21_engineering_matrix.json` and `.log`.

Numerical self-weight check for fixed section area 0.02388012 m²:

| Density | Per-girder line load | 3 girders × 25 m |
|---:|---:|---:|
| 78.5 kN/m³ | 1,874.589 N/m | 140.594 kN |
| 85.0 kN/m³ | 2,029.810 N/m | 152.236 kN |

The density ratio matches the line-load ratio. The model's edge-line sections match the full main girder section in all positive-overhang cases; therefore this is not a validation of physical load distribution.

## Baseline comparison

Same 25 m / 3G / 0° DB-grade E350A case, explicit input density 85 kN/m³, run from each checkout:

| Result | Phase 20 baseline | Phase 21 |
|---|---:|---:|
| Runtime density | 78,500 N/m³ | 85,000 N/m³ |
| Self-weight line load | 1,874.59 N/m | 2,029.81 N/m |
| ULS peak Mz | 2,717.88 kN·m | 2,727.62 kN·m |
| SLS peak Mz | 1,908.63 kN·m | 1,915.85 kN·m |
| ULS peak displacement | 103.01 mm | 103.39 mm |

See `evidence/phase20-density-85-comparison.log` and `evidence/density-design-85-complete.log`.

## PDF and backend consistency

`tests/integration/run_phase21_report.py` ran the app's real report generator from a fresh custom-density solver design and compiled the output using real Tectonic 0.17.0. The output is 46 A4 pages. `pdftotext` confirms `Steel Self-Weight Applied 85.0 kN/m3`, three physical girders G1–G3, and no G4/G5/G6. The first-page and design-summary render were visually inspected.

The report fixture's overall design status is Fail (overall girder utilization 2.16), and unavailable figure bytes render as placeholders. This test validates report-data propagation and PDF generation, not a passing bridge design. Output and render files are under `evidence/generated-phase21-report/`.

## Failed, skipped, and warning outcomes

- An earlier density direct-run attempt failed because its input omitted mandatory girder `G`; the corrected complete run passed. Both logs are retained.
- Before the skew mapping fix, the real +5°/−5° matrix reported only G1; the pre-fix evidence is retained as `evidence/phase21_engineering_matrix.pre-girder-fix.json`.
- The skew matrix runs completed with hundreds of SciPy “iteration is not making good progress” warnings: 581 captured on the 3G +5° case and 751 on the 4G −5° case. They are not counted as silent passes; convergence remains a review item.
- Cases without thermal input report missing thermal load cases during combination construction. These cases also intentionally omit footpath, railing, and median components, which are reported as skipped.
- `tests/integration/test_api_plate_girder.py` and `test_cli_plate_girder.py` contain pytest-style placeholder functions only. `unittest` discovered zero tests in them; no pytest executable was available in the mounted environment. They are not counted as passing tests.
- No independent slab-strip load-distribution or simply-supported self-weight moment check was completed. This is an open engineering verification item, not a passed test.
