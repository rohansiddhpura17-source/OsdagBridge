# Follow-up evidence for existing issue #92 — temperature-load adapter

No new issue is proposed. This is a local draft follow-up for upstream issue #92 only.

## Reproduction

- Baseline: `dev` commit `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3`.
- Candidate: isolated 17-fix worktree.
- Full probe: 25 m span, 7.5 m carriageway, 192 elements, 108 nodes.
- Canonical temperature fields were populated, but neither target contained a thermal load case among 48 load cases.
- Direct adapter instrumentation recorded zero calls from canonical fields on both targets.
- Legacy `temperature_load_kN_m2 = 2.5` produced one call and is only a positive control, not a proposed physical substitute.

## Independent arithmetic oracle

For the bounded mechanics probe (`Tmax=65 C`, `Tmin=-10 C`, metallic deck, 30 m, `E=200000 MPa`, `A=0.04 m2`, `alpha=11.7e-6/C`), `analyse_uniform_temperature()` matched the independent calculation exactly: `DeltaT=50 C`, free movement `17.55 mm`, effective axial action `1.754 kN`, and maximum absolute arithmetic error `0.0`.

This verifies the standalone helper's documented arithmetic. It does not verify production integration or code compliance. The production adapter at `plategirderbridge.py:1858-1877` still reads only `temperature_load_kN_m2`, while canonical keys are defined at `common.py:819-826`.

## Status

Reproduced on baseline and candidate. Unresolved. No candidate fix is supplied because converting a temperature delta into vertical pressure would be physically unsafe without an agreed bearing/restraint model and intended load representation.
