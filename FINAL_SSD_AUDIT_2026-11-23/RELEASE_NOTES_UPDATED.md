# OsdagBridge screening submission

**Phase 22.1 · 23 November 2026 · Decision: GO for software screening. Engineering acceptance remains on hold.**

The diagnostic is a 25 m straight bridge with three steel plate girders, positive deck overhang and a specified steel unit weight of 85 kN/m³. Its design **fails**. The governing reported girder utilization is **2.16** (backend 2.1576, fatigue normal stress). Review the enclosed diagnostic PDF for the individual checks.

## Report corrections and verification

Physical page 3 shows a plan of the actual case geometry. In the earlier report the deck surface obscured the framing in top view. The revised figure projects the generated solids into the longitudinal and transverse plane, displays the deck footprint beneath the framing, and identifies girder flanges, cross bracing and barriers. Axes are in metres. The cross-section caption now applies to the components present in the case.

Physical page 9 shows Table 2.7. The six member dimensions originate in metres and are converted once when the table is rendered. Each of G1, G2 and G3 has a depth of **1,390 mm**, an **8 mm** web, and **420 × 18 mm** top and bottom flanges. These values agree with the millimetre fields in the design output and the three girder design tables. The project overview now gives units for 2.8 m girder spacing and 250 mm deck thickness. The audit also checked 25 m span, 50 mm wearing course, 2,030 mm intermediate stiffener spacing, 20 mm stud diameter and 100 mm stud height. Their existing presentation units agree with this fixture.

A fresh production solver run supplied the report data. Tectonic compiled the diagnostic PDF. All 32 unit tests and six additional regression tests passed. The evidence check covered the six Phase 22 solver records, two stored skew repeats, and the fresh diagnostic. The 49-page PDF retains all six fixture figures. The reported steel self-weight reactions are −76.118 kN per end and the ULS moment is 2,727.621 kN·m. All numerical backend fields match Phase 22. The generated text includes a new run timestamp.

## Software evidence and engineering limits

- **Density and girder identity.** The 85 kN/m³ input yields 85,000 N/m³ and 2.029810 kN/m per girder on the analysis section. Physical results use G1–G3 for the diagnostic. Phase 22 also verified the zero-overhang self-weight correction against independent reaction and moment calculations.
- **Positive overhang.** EB1/EB2 retain full steel-girder stiffness. They attract bending without a corresponding physical girder in the input. Their effective stiffness and the resulting distribution of girder demands remain unvalidated.
- **Skew.** At +5° and −5°, the assembled steel self-weight was 1.49% below the expected value. Reactions balance the assembled loads. The shortfall concerns load placement and remains open.
- **Engineering acceptance.** Positive-overhang and skewed designs lack engineering acceptance. The diagnostic also uses a different section area for analysis self-weight and final optimized design. An independent reanalysis of the final section is outstanding.
- **CAD and plots.** Local native CAD screenshot capture failed in Phase 22. The geometry images use offline rendering of the generated solids. The bending, shear and deflection figures use the application’s analysis plotting functions. Their isometric labels are small at page scale; the corresponding tables give numerical values.

Phase 22.1 changes presentation and verification tooling. The Phase 22 structural analysis, loads, stiffness assignments, design checks and criteria are preserved. The original Phase 22 checkout remains the fallback.

## Independent SSD audit update — 23 November 2026

The published ZIP remains unchanged. A read-only audit is available on the [`phase22.1-audit-2026-11-23` branch](https://github.com/rohansiddhpura17-source/OsdagBridge/tree/phase22.1-audit-2026-11-23/FINAL_SSD_AUDIT_2026-11-23).

**Qualification:** the GO statement above applies to review of the verified software changes as a screening contribution. The full audit rates the current package **NO-GO as a clean final submission until four P1 findings are resolved**: contradictory end-diaphragm reporting, two compression-brace utilization ratios inconsistent with displayed demand/capacity, README MIT text conflicting with the GPL-3.0 license, and inconsistent standards-edition references.

The diagnostic still genuinely **FAILS** at utilization **2.16**. Engineering acceptance remains on hold. Positive-overhang EB1/EB2 stiffness is unvalidated, skewed self-weight is 1.49% below expected, and those designs are not engineering-accepted. Native CAD screenshot capture failed locally; offline rendering of generated solids was used.

The audit commit adds reports and inventory only. It does not change engineering calculations or replace the release ZIP.
