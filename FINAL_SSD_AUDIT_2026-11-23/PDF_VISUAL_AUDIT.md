# PDF Visual Audit

## Corpus

The project contains 70 `.pdf`-named paths. Seventeen are 4 KB AppleDouble resource-fork sidecars rather than PDF documents. The remaining **53 valid PDF paths** opened with `pdfinfo` and `pdftotext`; they cover **1,955 pages**, including duplicate copies. SHA-256 grouping found 19 distinct PDF byte streams. Every page of every distinct stream was rasterized to a contact sheet; exact duplicate files inherit the same page render. No page had empty extracted text. Metadata, page count, dimensions, fonts and image lists were checked for the Phase 22.1 deliverables. `PDF_INVENTORY.csv` records per-path hashes, titles, page counts and status. Render artifacts are under `pdf_all_pages/` and `rendered/`.

## Final diagnostic PDF

File: `/Volumes/PortableSSD/OsdagBridge-screening-2026/FOSSEE-OsdagBridge-Phase22.1/diagnostic.pdf`  
49 physical A4 pages; unencrypted; embedded fonts; six case figures (plus cover logo). The file opens and all pages render. Figure 1 is a visible plan on **physical page 3**, based on the actual three-girder fixture; the deck outline, framing, cross-bracing and barriers are visible. Other figure pages show the fixture cross-section/isometric view and three analysis plots. The native CAD viewer capture failed locally, so the geometry views are offline projections of generated solids; the diagnostic documentation discloses this. Some isometric labels are small at full-page scale; report tables retain the numeric values.

**Physical page 9 / Table 2.7:** G1, G2, G3 each display D=1,390 mm; web=8 mm; top flange=420 × 18 mm; bottom flange=420 × 18 mm. All rows match backend millimetre fields in the evidence checker. Other checked dimensions (25 m span, 2.8 m spacing, 250 mm deck, 50 mm wearing course, 2,030 mm stiffener spacing, 20 mm stud diameter and 100 mm stud height) have suitable presentation units.

**Outcome preserved:** FAIL; backend governing utilization 2.1576, displayed 2.16. The self-weight reaction summary is −76.118 kN each end. The six figures and backend values came from the fixture; no substitute figure or passing result was used.

### Remaining report inconsistencies

- **P1, physical page 5:** executive summary says “End Diaphragm design Not assessed.” Detailed Tables 5.26–5.28 on physical pages 41–42 show PASS rows that duplicate the cross-bracing section, loads and capacities; Table 5.28 says the OsdagBridge cross-bracing module was used. This is internally contradictory and should not be presented as an assessed end-diaphragm design.
- **P1, physical pages 40 and 42:** Table 5.25 lists 6.490/13.170 with UR 0.600, and 5.980/15.180 with UR 0.550. Direct ratios are 0.493 and 0.394. The tension entries 6.923/58.180=0.119 and 6.378/58.180=0.110 do agree after rounding. Reconcile compression-row values/formulas before relying on those checks.
- **P2, physical pages 24, 35 and 47:** design discussion refers to IRC 22:2014, IRC 112:2011, and elsewhere IRC 22:2015 and IRC 112:2020. The exact edition governing each check needs confirmation and consistent citations.
- **P2, physical pages 12 and 14:** braking, wind and temperature fields include N/A or blank values. Treat as unavailable fixture inputs, not zero or verified loads; provide actual design inputs before use.

Historical PDFs include old phase content and placeholder figure frames; those are archived evidence, not the final diagnostic. Some historical files are byte-identical duplicates. Across the valid PDFs no blank-text page, unreadable/corrupt page, or gross clipping/overflow was observed in contact-sheet review. Text checks alone do not prove numerical engineering correctness.
