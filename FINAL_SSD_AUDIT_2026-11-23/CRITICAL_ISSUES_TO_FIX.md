# Critical Issues to Fix

No P0 finding was identified. Four P1 items should be resolved before treating this as a clean final package.

## P1 — Summary says end diaphragm not assessed while detail table passes it

**Location:** `FOSSEE-OsdagBridge-Phase22.1/diagnostic.pdf`, physical page 5; Tables 5.26–5.28 on physical pages 41–42.  
**Evidence:** executive summary states `End Diaphragm design Not assessed`; Table 5.28 gives the same sections, demands, capacities and PASS statuses as cross-bracing Table 5.25, and says the cross-bracing module was used.  
**Impact:** report implies checks were assessed when summary says they were not; the duplicated values do not establish end-diaphragm design.  
**Correction:** inspect end-diaphragm result mapping and either generate its genuine results or remove/mark the detailed checks as not assessed. Do not copy cross-bracing results.

## P1 — Compression brace utilization ratios do not match listed demand/capacity

**Location:** diagnostic PDF physical page 40 (Table 5.25; repeated end-diaphragm copy on physical page 42).  
**Evidence:** 6.490/13.170 = 0.493 but UR shown as 0.600; 5.980/15.180 = 0.394 but UR shown as 0.550. Tension rows agree to rounding.  
**Impact:** design-check ratios and statuses cannot be reconciled from the displayed values.  
**Correction:** check source demand, governing combination, section resistance and formatting; disclose formulas/values that govern and regenerate from actual solver/design outputs.

## P1 — README license conflicts with LICENSE

**Location:** `phase22.1-submission-polish/README.md:8`, `:280`, `:304`; `phase22.1-submission-polish/LICENSE:1`.  
**Evidence:** README says MIT; LICENSE is GNU GPL-3.0; GitHub API says GPL-3.0.  
**Impact:** users and reviewers receive contradictory licensing information.  
**Correction:** align badge and prose with the verified applicable license and contribution rights.

## P1 — Code edition references conflict

**Location:** diagnostic PDF physical pages 24, 35 and 47.  
**Evidence:** design check general text cites IRC 22:2014, deck discussion cites IRC 112:2011, while other criteria cite IRC 22:2015 and IRC 112:2020.  
**Impact:** applicable requirements for a structural check are ambiguous.  
**Correction:** confirm editions actually implemented for each check and harmonize applicable-code list, report text, equations and references.

## P2 — README cites absent CI workflow

**Location:** `phase22.1-submission-polish/README.md:319`; final tree `.github/workflows/`.  
**Evidence:** `ci.yml` is absent; tracked workflow is `conda-publish.yml`.  
**Impact:** inaccurate repository instructions.  
**Correction:** update the claim after checking current CI configuration.

## P2 — Unconditional diagnostic prints

**Location:** `src/osdagbridge/core/bridge_types/plate_girder/plategirderbridge.py:3735–3738, 3843–3844`; report worker debug prints in `src/osdagbridge/desktop/ui/template_page.py:1379–1442`.  
**Evidence:** fresh runs print raw/resolved inputs and internal values to stdout.  
**Impact:** noisy logs and potential disclosure of user inputs in logs.  
**Correction:** remove or guard behind a debug setting / logger.

## P2 — Source archive excludes non-code tracked files

**Location:** ZIP member `FOSSEE-OsdagBridge-Phase22.1/source.zip`.  
**Evidence:** all `src/` and `tests/` paths match commit blobs, but 132 other tracked paths (including docs and examples) are omitted.  
**Impact:** archive is not a full repository snapshot.  
**Correction:** label it as source-and-test subset or include the remaining required reference docs/fixtures.

## P2 — Site-dependent inputs remain unavailable

**Location:** diagnostic PDF physical pages 12 and 14.  
**Evidence:** braking/wind/temperature values include N/A or blank fields.  
**Impact:** not a complete site-specific calculation.  
**Correction:** obtain verified project inputs before engineering use; preserve N/A until then.

## P2 — Small isometric labels

**Location:** diagnostic PDF physical page 4.  
**Evidence:** geometry labels are small at full-page scale; numeric tables remain readable.  
**Correction:** increase label size or simplify view if the figure is expected to be read without zoom.
