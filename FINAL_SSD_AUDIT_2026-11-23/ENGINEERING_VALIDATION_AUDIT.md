# Engineering Software Verification Audit

## Verified software behaviours

### Issue #20 — steel density

The custom density path accepts kN/m³ input and sends N/m³ to `SteelProperties`; the regression suite covers database defaults and explicit custom overrides. The Phase 22 evidence and fresh case 1 show 85 kN/m³ → 85,000 N/m³. Using the analysis area 0.02388012 m² gives 85,000 × 0.02388012 = **2,029.8102 N/m = 2.029810 kN/m**. Across three 25 m girders this is 152.236 kN; fresh reactions are −76.118 kN at each support. This verifies the recorded fixture path, not every steel-material input.

### Issue #113 — physical girder identity and self-weight

The diagnostic reports G1–G3 for three physical girders. Density, mapping and zero-overhang regression tests pass. The Phase 22 zero-overhang result has expected total steel weight 140.594 kN, equal applied weight, support reactions −70.297 kN each, and 145.946 kN·m maximum moment against a simply supported reference of 146.452 kN·m (0.35% difference). This validates the tested control fixture, not live-load distribution generally.

### Skew coordinate calculation and repeats

Fresh +5° and −5° probes completed; repeated probes reproduced the recorded numerical fields. The coordinate inversion path is exercised in `test_phase22_validation.py`. The evidence checker passed after both stored and freshly generated cases. Equilibrium of the assembled load set is within the recorded residual tolerance.

## Unresolved engineering limitations

- **P1 engineering limitation (open, no acceptance):** positive-overhang EB1/EB2 use full girder section stiffness despite there being no physical steel edge girders in the input. The record shows the model edges attract bending (about 87.844 kN·m in the three-girder straight case); effective stiffness and resulting demand distribution are not validated.
- **P1 engineering limitation (open, no acceptance):** fresh skew cases remain short of expected steel self-weight by 2.091 kN (+5°, 1.487%) and 2.788 kN (−5°, 1.487%). A trial correction over-applied load and was rejected. Do not treat equilibrium of the assembled load as proof that the applied weight is correct.
- **P1 engineering limitation:** the diagnostic itself genuinely **FAILS**. Governing girder utilization is 2.1576 backend, displayed 2.16. The final optimized girder section has a different area from the area used in analysis self-weight; independent reanalysis of the selected final section is outstanding.
- **P2 evidence limitation:** native CAD screenshot capture failed locally with signal 11. Offline projection of generated OCC solids was used for the geometry views; the plots use the application plotting functions.

## Decision

Software fixes for custom density, physical girder identity, tested zero-overhang self-weight, skew coordinate inversion, and report presentation are verified for the fixtures cited above. No bridge design is engineering-accepted on this evidence. The positive-overhang and skewed cases must remain excluded from engineering use pending model validation.
