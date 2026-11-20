# Draft follow-up for existing issue #125 — no remote write

Environment: unmodified `dev` commit `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3`, macOS. All actions used the GUI and all snapshots came from the live process. Evidence manifest: `evidence/retry04/manifest.json`.

## Reproduction A: 30 → 32 → 30 m in three consecutive designs

RUN-04, RUN-05 and RUN-06 completed without a restart. RUN-05 submitted span 32 m. RUN-06 displayed and submitted 30 m, but 66 normalized input values still differed from RUN-04, including optimized girder dimensions and cross-bracing spacing. There were 128 differing top-level output values. Reloading the same baseline OSI and designing RUN-07 restored all 471 input values and baseline outputs except the generated report timestamp. This fails RUN-001 and extends the stale-state behavior reported in #125. Exact span-state source cause remains to be isolated.

## Reproduction B: three → four → three girders

RUN-07 (three girders) had 471 input keys and 835 output keys. RUN-11 (four girders) had 590 and 1080. After the GUI returned to three girders, RUN-12 still had 590 input keys and 954 output keys: 119 obsolete input keys and 42 G4-related output keys remained, including `member_properties.girder_details.member_id.G4.M1`. The 471 common input values and the 835 common output values matched RUN-07, apart from the report timestamp. Settled CAD returned to three girders. This fails DICT-005; the observed common calculation results returned to baseline.

A subsequent genuine **Save Input** action produced `evidence/retry04/RUN-12-three-return-stale.osi.osi` (the app appended `.osi` to the entered filename; SHA-256 `e16bc5cf3fce1def6dce2e0c846036bf92fffd262973390dde4e2a211ba5b9a6`). Its 474 keys include **no G4 key**. The live dictionary defect therefore did not carry into this particular saved OSI. Report/PDF impact has not been tested for RUN-12.

## Code-Level Fix & Verification
The working dictionary removes obsolete dynamic keys in `defaults.py:542-550,653-663,714-728,750-762`, but `additional_inputs.py:518` commits it with `self.default_input_dict.update(self.working_input_dict)`. `update()` does not remove keys deleted from the working copy. The shared dictionary originates from `template_page.py:478`. In the verified 17-fix candidate patch (`scripts/isolated-candidate-fixes-phase16.patch`), contents are replaced in place (`clear(); update(working)`) and stale dynamic keys are cleared on redesign (verified in `phase16/evidence/candidate_17fix/candidate_17fix_live_revalidation.json`: 0 stale keys on 30->32->30 m and 3->4->3 girder returns).

Regression: run 3→4→3 in one GUI process; assert the final shared raw and normalized inputs and Output Dictionary contain no G4/G3G4 entries, CAD shows three girders, and baseline calculation outputs match. Check saved OSI and report separately to define their actual exposure. Separately run 30→32→30 and assert full restored optimized section inputs, CAD, plots and outputs match the original baseline apart from generated timestamps.

Related existing issue: https://github.com/Nidhikhare12/OsdagBridge/issues/125. Keep this as a draft follow-up; do not publish without approval.
