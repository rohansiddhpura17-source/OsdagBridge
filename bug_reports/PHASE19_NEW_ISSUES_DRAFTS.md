# Phase 19 Local GitHub Issue Drafts (BUG-25 .. BUG-30)

**Status:** LOCAL DRAFTS ONLY — ZERO REMOTE GITHUB WRITES PERFORMED. Recheck upstream `Nidhikhare12/OsdagBridge` issues before any user-approved publication.

## BUG-25: Case-sensitive section_type=='Rolled' check downgrades default 'rolled' compression flanges to Welded limits
- **Root Cause (`file:line`):** `src/osdagbridge/core/utils/codes/is800_2007.py:209; src/osdagbridge/core/utils/codes/irc22_2015.py:334,353`
- **Baseline Reproduction:** KEY_SECTION_FABRICATION[0] is lowercase 'rolled', but Table2_i and cl_602_table2_i compare against Title-case 'Rolled'; calling with default 'rolled' at b/t=9.0, fy=250 MPa returns ['Compact', 9.0, 9.4] instead of ['Plastic', 9.0, 9.4].
- **Minimal Fix (`phase19/evidence/phase19-incremental-6fixes.patch`):** `src/osdagbridge/core/utils/codes/is800_2007.py; src/osdagbridge/core/utils/codes/irc22_2015.py`
- **Verification:** test_bug25_irc22_table2_i_rolled_case_insensitive: FAIL on baseline ('Compact'), PASS on Phase 19 candidate (['Plastic', 9.0, 9.4], matching 'Rolled').
- **Duplicate Check:** None found by targeted search (recheck live upstream before posting)

## BUG-26: compute_fatigue() multiplies IRC:22 Cl. 605.4 shear fatigue limit tau_y (0.43*fy) by 1.5
- **Root Cause (`file:line`):** `src/osdagbridge/core/bridge_types/plate_girder/designer.py:1320`
- **Baseline Reproduction:** Computes tau_fd_eff_MPa = min(tau_fd, 1.5 * 0.43 * mat.fy) = 161.25 MPa for fy=250 MPa (50% above IRC:22 Cl. 605.4 tau_y = 107.5 MPa and above pure shear yield fy/sqrt(3) = 144.34 MPa), risking false PASS.
- **Minimal Fix (`phase19/evidence/phase19-incremental-6fixes.patch`):** `src/osdagbridge/core/bridge_types/plate_girder/designer.py`
- **Verification:** test_bug26_fatigue_shear_cap_matches_tau_y: FAIL on baseline (161.25 MPa), PASS on Phase 19 candidate (107.5 MPa == assessment['tau_y_limit_MPa']).
- **Duplicate Check:** None found by targeted search (recheck live upstream before posting)

## BUG-27: Composite interface utilization helper _ur(demand, 0) returns 0.0 (false PASS) on zero capacity
- **Root Cause (`file:line`):** `src/osdagbridge/core/bridge_types/plate_girder/deckdesign.py:849-856`
- **Baseline Reproduction:** _ur(120.0, 0.0) returns 0.0 instead of >1.0 failure sentinel (9.999), masking zero composite transverse shear/crack/stress capacity as 0% utilization.
- **Minimal Fix (`phase19/evidence/phase19-incremental-6fixes.patch`):** `src/osdagbridge/core/bridge_types/plate_girder/deckdesign.py`
- **Verification:** test_bug27_deckdesign_zero_capacity_ur_not_false_pass: FAIL on baseline (0.0), PASS on Phase 19 candidate (9.999 for demand>0, 0.0 for demand==0).
- **Duplicate Check:** None found by targeted search (recheck live upstream before posting)

## BUG-28: BOQ hardcodes concrete/steel densities, computes girder volume from G1 only, and uses diagonal area for bracing chords
- **Root Cause (`file:line`):** `src/osdagbridge/core/boq/boq_generator.py:120-126,174-190,228-229,244-318,353-354`
- **Baseline Reproduction:** With deck density 24.0 kN/m3, steel 80.0 kN/m3, girders [0.04, 0.06, 0.04] m2, and distinct chord areas [20, 25] cm2, baseline outputs deck 187.50 MT (exp 180.00), CB 45.00 MT (exp 43.20), girder vol 3.60 m3 (exp 4.20), girder wt 28.26 MT (exp 33.60), and top/bot chord area 0.00100 m2 (exp 0.00200/0.00250).
- **Minimal Fix (`phase19/evidence/phase19-incremental-6fixes.patch`):** `src/osdagbridge/core/boq/boq_generator.py`
- **Verification:** test_bug28_boq_custom_density_per_girder_volume_and_chord_areas: FAIL on baseline, PASS on Phase 19 candidate (exact match to analytical BOQ oracle).
- **Duplicate Check:** None found by targeted search (recheck live upstream before posting)

## BUG-29: _get_girder_sw_df() silently fabricates 22.4 kN/m girder self-weight on Z-key miss
- **Root Cause (`file:line`):** `src/osdagbridge/core/bridge_types/plate_girder/analysis_results.py:1382`
- **Baseline Reproduction:** sw_mag_map.get(round(s[2], 3), 22.4) silently invents 22.4 kN/m (672.0 kN total_v_audit over 30 m) when self_weight_load_case is absent or Z-coordinate differs beyond 1e-3 rounding.
- **Minimal Fix (`phase19/evidence/phase19-incremental-6fixes.patch`):** `src/osdagbridge/core/bridge_types/plate_girder/analysis_results.py`
- **Verification:** test_bug29_analysis_results_no_fabricated_22_4_sw_fallback: FAIL on baseline (22.4 kN/m, 672.0 kN), PASS on Phase 19 candidate (0.0 kN/m, 0.0 kN).
- **Duplicate Check:** None found by targeted search (recheck live upstream before posting)

## BUG-30: validate_map_coordinates accepts NaN/Inf/out-of-range coordinates; osdag_display_shape mutable default label=[] crashes
- **Root Cause (`file:line`):** `src/osdagbridge/core/bridge_types/plate_girder/validator.py:978-984; src/osdagbridge/core/bridge_types/plate_girder/cad_generator.py:1105,1118`
- **Baseline Reproduction:** validate_map_coordinates('nan', 'inf') and ('999', '-999') return (True, ''); osdag_display_shape(..., label=[]) uses mutable default and raises IndexError on label[0] when omitted.
- **Minimal Fix (`phase19/evidence/phase19-incremental-6fixes.patch`):** `src/osdagbridge/core/bridge_types/plate_girder/validator.py; src/osdagbridge/core/bridge_types/plate_girder/cad_generator.py`
- **Verification:** test_bug30_map_coordinates_and_cad_mutable_default: FAIL on baseline, PASS on Phase 19 candidate.
- **Duplicate Check:** None found by targeted search (recheck live upstream before posting)
