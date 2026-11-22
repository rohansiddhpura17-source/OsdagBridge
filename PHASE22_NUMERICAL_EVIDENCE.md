# Numerical evidence • 23 November 2026

All six cases used a 25 m span, the Phase 21 fixture builder and actual OpenSees results. Entries below report vertical force in kN and moment in kN·m. Applied Fy is the signed sum of the assembled SW load commands. Reactions are signed OpenSees nodal values. Expected weight is 25 × sum of bare-steel area × unit weight. Each area here is 0.02388012 m².

| Physical layout | Density kN/m³ | Expected SW | Applied SW | Left reaction | Right reaction | Phase 21 → 22 physical ULS peak magnitude |
|---|---:|---:|---:|---:|---:|---:|
| 3G straight, overhang | 78.5 | 140.594 | 140.594 | −70.297 | −70.297 | 2717.880 → 2717.880 |
| 3G straight, custom steel | 85 | 152.236 | 152.236 | −76.118 | −76.118 | 2727.621 → 2727.621 |
| 4G straight, overhang | 78.5 | 187.459 | 187.459 | −93.729 | −93.729 | 2296.862 → 2296.862 |
| 3G +5°, overhang | 78.5 | 140.594 | 138.503 | −68.226 | −70.277 | 2740.639 → 2740.639 |
| 4G −5°, overhang | 78.5 | 187.459 | 184.671 | −93.702 | −90.969 | 2269.656 → 2269.656 |
| 3G straight, zero overhang | 78.5 | 140.594 | 140.594 | −70.297 | −70.297 | 4392.637 → 4524.153 |

Across these SW cases, maximum absolute vertical force imbalance was below 5 × 10⁻¹³ kN and global moment imbalance about z below 2 × 10⁻¹² kN·m. The moment check sums xFy + Mz from applied commands and support responses about the same origin. Skew runs balanced their assembled loads but missed approximately 1.49% of prescribed self-weight. No claim of equilibrium for every load combination follows from this check. Detailed per-girder and edge moments, individual support reactions and ULS governing girders are in validation-0 through validation-5.json.

## Independent moment reference

For uniform loading on a simply supported isolated girder, w = 1.87458942 kN/m, wL/2 = 23.43237 kN and wL²/8 = 146.45230 kN·m. The zero-overhang model gives 23.43237 kN per end per girder and 145.94561 kN·m at the nearest sampled section. With identical uniform loads, straight geometry and three lines of equal stiffness, the control should be symmetric. Phase 21 instead applied one line of load and gave 46.86474 kN total vertical reaction magnitude. Its saved matrix field for total applied steel weight was calculated from nominal sections. Measuring reactions exposed the discrepancy.

## Coordinate solver

SciPy 1.18.1, MINPACK hybrd via scipy.optimize.fsolve, finite-difference Jacobian, xtol=1.49012e-8, initial point (−0.4444444444444, 0.99999999), factor=100. The installed no-Jacobian path sets maxfev to 200(N+1) = 600. The monitor recorded SciPy's nfev and termination status; MINPACK does not expose a separate iteration count here. Position residual is the infinity norm of the returned equation residual divided by four, in metres.

| Baseline case | Successful calls (status 1) | Stagnant calls (status 5) | nfev success / stagnant | Worst position residual on stagnant calls |
|---|---:|---:|---|---:|
| +5° | 6346 | 551 | 5–24 / 17–31 | 3.553 × 10⁻¹⁵ m |
| −5° | 7669 | 721 | 5–23 / 17–33 | 3.553 × 10⁻¹⁵ m |

The exact RuntimeWarning was “The iteration is not making good progress, as measured by the [newline] improvement from the last ten iterations.” The remaining 30 warnings per case concern omitted roadside components or unavailable thermal load cases. Phase 22 needed zero iterative calls for these mesh cells and emitted zero such RuntimeWarnings. Two fresh-process runs of each skew case produced identical recorded numerical and warning fields. The independent test forwards known natural coordinates through bilinear weights and compares the recovered coordinates. [SciPy fsolve documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.fsolve.html)

## PDF and test evidence

32 unit tests and six Phase 20 regression tests passed. Six fresh solver cases and both skew repeats completed. The numerical acceptance script checks identity, density, symmetry against the zero-overhang reference, force/moment equilibrium, signed reactions and PDF fields. The positive-overhang and skew demand limitations remain open. The native CAD run failed with signal 11 and the offline diagnostic succeeded. No independently validated all-checks-passing design was identified; the optional passing report was skipped.

The 49-page diagnostic PDF has six case figures on pages 3, 4, 22 and 23 plus the cover logo. No placeholder string was found in the extracted text. The custom case reports three physical girders, 85.0 kN/m³, SW maximum 94.751 kN·m, ULS maximum 2727.621 kN·m and a failing utilization of 2.16 (backend 2.1576). Three backend girder checks failed. The Chapter 4 SW reactions are −76.118 kN at both ends. The selected report chapters include loads, analysis and design checks. The headless images exercise this diagnostic; optional drawing chapters and native screenshot capture are outside its verified coverage. The printed girder design section has area 25,952 mm² while the grillage used 23,880.12 mm² for SW. This optimized design therefore cannot be assumed to verify a final as-designed section in a reanalysis.

## Reproduction

From the Phase 22 checkout on this machine, run the following in a shell. Baseline records use the same probe and fixtures with PYTHONPATH pointing to the preserved Phase 21 src directory. Record one fresh process per case. The JSON and test summaries in evidence/phase22 are the review records.

```sh
export PYTHONPATH=src QT_QPA_PLATFORM=cocoa MPLBACKEND=Agg
export QT_QPA_PLATFORM_PLUGIN_PATH=/Volumes/OsdagBridgeEnv/envs/osdagbridge-macos/lib/python3.12/site-packages/PySide6/Qt/plugins/platforms
py=/Volumes/OsdagBridgeEnv/envs/osdagbridge-macos/bin/python
rtk "$py" -m unittest discover -s tests/unit -p 'test*.py' -v
rtk "$py" tests/phase20/test_phase20_bug25_to_30_conda.py src
for i in 0 1 2 3 4 5; do
  rtk "$py" tests/integration/phase22_probe.py "$i" "evidence/phase22/validation-$i.json"
done
for i in 3 4; do
  rtk "$py" tests/integration/phase22_probe.py "$i" "evidence/phase22/validation-$i-repeat.json"
done
rtk "$py" tests/integration/phase22_pdf.py
rtk pdftotext -layout evidence/phase22/pdf/diagnostic.pdf evidence/phase22/pdf/diagnostic.txt
rtk "$py" tests/integration/check_phase22_evidence.py
```
