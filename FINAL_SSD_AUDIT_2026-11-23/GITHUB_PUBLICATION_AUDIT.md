# GitHub Publication Audit

## Verified remotely (read-only)

Repository: [rohansiddhpura17-source/OsdagBridge](https://github.com/rohansiddhpura17-source/OsdagBridge) — public fork of Nidhikhare12/OsdagBridge. GitHub API reports GPL-3.0. The default branch is `dev`.

Published branch `phase22.1-submission-polish` points to `cffc9ef9ec3e9d33814258cadbba81c1e890e881`. Published tag `screening-phase22.1` points to the same commit. Release [screening-phase22.1](https://github.com/rohansiddhpura17-source/OsdagBridge/releases/tag/screening-phase22.1) exists and contains one asset, `FOSSEE-OsdagBridge-Phase22.1.zip`, size 5,351,464 bytes, with GitHub-reported digest `sha256:bf5b58e38492700193e5a975f2fc8e2a9e1dd4cf56068c36a48491e953eb5e7e`, matching the local ZIP and expected hash.

The release notes preserve FAIL and 2.16 utilization, disclose positive-overhang and skew limitations, describe the offline CAD rendering, and state engineering acceptance remains on hold. No push, issue, pull request, tag, release or other GitHub modification was made during this audit.

## Findings

- **P1:** public README says MIT while the repository LICENSE/API report GPL-3.0; see `README_REVIEW.md`.
- **P2:** final branch is not the default branch, so the landing page shows `dev` content rather than Phase 22.1 submission instructions. Release notes are the correct screening artifact description.
- Public HTML README rendering was reachable. GitHub's dynamic release page exposed the release body and asset in API; UI page included a transient loading error for asset widgets, so asset verification relies on the successful read-only API response and checksum.

**Publication status:** release and branch are present and internally consistent. Repository landing-page/license presentation needs correction; branch/release presence is not upstream review or engineering acceptance.
