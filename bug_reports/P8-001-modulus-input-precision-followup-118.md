# Draft follow-up for existing issue #118 — not posted

## Summary
A custom girder shear modulus entered as **76.923 GPa** is normalized to **76.9 GPa** before design. The run uses **76,900 MPa**, so the precision loss affects calculations rather than only the displayed value.

## Reproduction and evidence
On baseline commit `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3`, enter custom steel `G=76.923 GPa` in the Girder material dialog and run the design. The Retry04 live readback and normalized backend input show `76.9`; effective properties use `G=76.9 GPa`. The isolated comparison in `evidence/phase56-live-20261119-retry04/manifest.json` records a changed representative `Mcr` when the value is retained as 76.923.

## Root cause
The material dialog's numeric validator and save/populate path use one decimal place for `E` and `G` (`material_properties.py` baseline near lines 413, 546, 754). The backend receives the rounded dialog value.

## Proposed correction and regression
Preserve the entered precision consistently through validation, save, OSI and pre-worker dictionaries. The isolated candidate uses three decimal places for `E/G`; its regression asserts a `76.923` readback/save/populate round trip. Baseline fails that regression and the candidate passes.

The repository does not document a formal modulus precision contract. Three decimal places in GPa (1 MPa increments) is the tested candidate, not an established product requirement; confirm/document the intended granularity before merging.

Evidence: `evidence/phase8-9-20261119/regression-manifest.json`, `candidate-regression.log`, and `baseline-regression.log`. Related existing report: [#118](https://github.com/Nidhikhare12/OsdagBridge/issues/118). No issue publication or baseline source change was made.
