Draft separate issue — **not posted**

Title: [Bug] Concrete Results Table exports Ecm in GPa under MPa heading and inflates raw modular ratio 1000×

On baseline `dev` commit `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3`, export a Results Table containing Material Properties - Concrete for M40/E350A. In the exported workbook, Ecm is 33 under an MPa heading and the modular ratio is 6060.61; steel E is 200000 MPa. Expected: Ecm 33000 MPa and the table's raw `Es/Ecm` ratio 6.06. The IRC 22 short-term *design* ratio minimum of 7.5 is separate and should only appear if the field explicitly reports that code-adjusted ratio.

Root cause: `generate_results_values_builder.py:215` reads `ConcreteProperties.Ecm` in GPa, `:217-224` divides MPa steel E by that GPa value, and `:252` labels it MPa. `generate_results_dialog.py:1306-1384` exports these resolver values unchanged.

Fix: convert concrete Ecm to MPa before display and division; add a Results Table/Excel regression for M40 and a custom concrete value. Do not change the DTO's GPa contract.

Related: #148 covers the deck SLS calculation boundary but does not cover this independent table resolver/export boundary. #82 concerns steel Excel modulus labels. Upstream issue searches for “Material Properties - Concrete” and “modular ratio Excel” found no separate concrete export report as of 2026-11-18.

Evidence: the preserved BAS-001 exported workbook and source-level resolver reproduction in the local Phase 4 screening records. No issue has been published.
