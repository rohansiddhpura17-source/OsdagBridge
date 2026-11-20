# Bug #002 — OSI load-restoration observation

**Status: RESOLVED OBSERVATION — no defect reproduced; do not publish.**

## Reclassification

The user subsequently confirmed that loading `BAS-001-baseline.osi` restored the baseline inputs successfully. The earlier capture showed the success dialog and a clipped input pane, so it did not establish missing values. The current report records the earlier clipping as an observability issue, not a product defect.

The saved OSI contains 471 keys. The pre-save UI snapshot differs at 32 fields, but replaying the source save-time default expansion on a copy yields zero mismatches against the saved OSI. Those differences therefore do not establish failed serialization/restoration.

## Preserved evidence

- Load success dialog: `evidence/macos/osi-load-message-20261118.png` (SHA-256 `None`).
- Post-load window capture: `evidence/macos/osi-restored-window-20261118.png` (SHA-256 `None`); controls are clipped in this capture.
- OSI replay reconciliation: `execution/logs/BAS-001-osi-save-replay.json`; pre-save vs OSI mismatch count 32, source replay vs OSI mismatch count 0.
- User-confirmed successful restoration, recorded in this turn.

## Remaining scope

`OSI-001` remains `BLOCKED` because the exact post-load 471-key UI dictionary was not captured for a hash-to-hash equality comparison. This is a coverage gap, not evidence for the candidate defect. No issue was filed or modified.
