# ZIP and Checksum Audit

## Published package

Path: `/Volumes/PortableSSD/OsdagBridge-screening-2026/FOSSEE-OsdagBridge-Phase22.1.zip`  
Expected and actual SHA-256: `bf5b58e38492700193e5a975f2fc8e2a9e1dd4cf56068c36a48491e953eb5e7e` — **MATCH**.

`unzip -t` reports no errors. The ZIP has 34 entries, no duplicate names, no AppleDouble entries, and no member over 25 MB. All **33** entries in the package `SHA256SUMS` manifest verify. The manifest intentionally does not hash itself. The package includes final report, diagnostic, Phase 21/22 summaries, numerical and test evidence, reproduction guide, Git references, patch, source archive and manifest. No obvious credentials, private-key files or environment secret files were found in the package path/member list.

## Nested source archive and patch

`source.zip` has 325 file members. It contains all tracked `src/` and `tests/` files from commit `cffc9ef9ec3e9d33814258cadbba81c1e890e881`, and each corresponding file hash matches the Git blob. It omits 132 non-source/non-test tracked paths, mainly docs, examples and supporting project records; see `DOCUMENTATION_REVIEW.md`. This is a scoped source-and-test archive, not a complete copy of all 457 tracked files.

`phase22.1-source.patch` passes `git apply --check` against the Phase 22 source archive with exit code 0. Git emits executable-mode warnings for seven changed files. A normal Git checkout should be used to verify executable-bit handling before applying the patch in a downstream workflow.

## Conclusion

The already-published ZIP is internally intact and byte-for-byte matches the expected hash. Do not rebuild or replace it without a separately approved release. Its hash proves artifact identity, not engineering correctness.
