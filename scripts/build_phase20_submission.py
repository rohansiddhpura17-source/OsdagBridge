#!/usr/bin/env python3
"""Stage phase20-submission/, build ReportLab PDF, SHA256 manifest, ZIP and receipt. Phase 18 left untouched."""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

ROOT = Path("/Volumes/PortableSSD/OsdagBridge-screening-2026")
P18SUB = ROOT / "phase18-submission"
P19 = ROOT / "phase19"
P20 = ROOT / "phase20"
DST = ROOT / "phase20-submission"
PDF_OUT = ROOT / "OsdagBridge_Screening_Test_Report_Phase20.pdf"
ZIP_OUT = ROOT / "OsdagBridge_Screening_Submission_Phase20.zip"
RECEIPT = ROOT / "PHASE20_ARCHIVE_RECEIPT.json"
P18_ZIP = ROOT / "OsdagBridge_Screening_Submission_Phase18.zip"
P18_SHA = "d9ad32cbf8a5d6e0a8e86ec6cbae28135ff2202e71c6a71d9ecff8f2b0cb4308"
JUNK_DIRS = {"__pycache__", ".pytest_cache"}


def junk(name: str) -> bool:
    return name.startswith("._") or name == ".DS_Store" or name in JUNK_DIRS


def ign(_d, names):
    return {n for n in names if junk(n) or n.endswith(".pkl")}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while c := f.read(1 << 20):
            h.update(c)
    return h.hexdigest()


def copytree(src: Path, dst: Path):
    shutil.copytree(src, dst, ignore=ign, copy_function=shutil.copyfile, dirs_exist_ok=True)


def cp(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


# ------------------------------------------------------------------ 1. stage
if DST.exists():
    shutil.rmtree(DST, ignore_errors=True)
DST.mkdir(parents=True, exist_ok=True)
copytree(P18SUB, DST)
(DST / "SHA256SUMS.json").unlink(missing_ok=True)
if (DST / "README.md").exists():
    shutil.move(DST / "README.md", DST / "README_PHASE18.md")
if (DST / "EVIDENCE_INDEX.md").exists():
    shutil.move(DST / "EVIDENCE_INDEX.md", DST / "EVIDENCE_INDEX_PHASE18.md")
old_pdf = DST / "report/OsdagBridge_Screening_Test_Report.pdf"
if old_pdf.exists():
    shutil.move(old_pdf, DST / "report/OsdagBridge_Phase18_Snapshot.pdf")

for sub in ("bug_reports", "evidence", "tests"):
    copytree(P19 / sub, DST / "phase19" / sub)
for sub in ("bug_reports", "evidence", "reports", "tests"):
    copytree(P20 / sub, DST / "phase20" / sub)
EV = P20 / "evidence"
cp(P20 / "bug_reports/DEFECT_REGISTER_PHASE20.csv", DST / "bug_reports/DEFECT_REGISTER_PHASE20.csv")
cp(P20 / "bug_reports/DEFECT_REGISTER_PHASE20.json", DST / "bug_reports/DEFECT_REGISTER_PHASE20.json")
cp(EV / "phase20_thermal_issue92_isolated.patch", DST / "patches/phase20_thermal_issue92_isolated.patch")
cp(EV / "phase20_combined_all_fixes.patch", DST / "patches/phase20_combined_all_fixes.patch")

S = json.loads((EV / "PHASE20_VERIFICATION_SUMMARY.json").read_text())
O = json.loads((EV / "PHASE20_ANALYTICAL_ORACLES.json").read_text())
R = json.loads((EV / "PHASE20_ISSUE92_BASELINE_VS_CANDIDATE.json").read_text())
G92 = json.loads((EV / "gui_issue92/phase20_issue92_gui_summary.json").read_text())
with (P20 / "bug_reports/DEFECT_REGISTER_PHASE20.csv").open(newline="", encoding="utf-8") as fh:
    DEF = list(csv.DictReader(fh))

readme = f"""# OsdagBridge Screening Submission — Phase 20

FOSSEE IIT Bombay Winter Internship 2026 screening task (OsdagBridge).

## Status
- 25 register entries: **24 fixed** (17 Phase 16, 6 Phase 19, Issue #92 resolved in Phase 20 within a defined scope), 1 resolved non-defect, 0 unresolved.
- Issue #92 scope: {S["issue92_scope"]}
- Baseline `{S["commits"]["baseline"]}`; candidate commits `{S["commits"]["commit_phase19_conda_refinements"]}` (Phase 19 Conda refinements) and `{S["commits"]["commit_issue92_thermal"]}` (Issue #92).

## Phase 20 verification (actual runs)
| Suite | Result |
|---|---|
| Analytical OpenSeesPy thermal benchmarks | {S["analytical_oracles"]} |
| Historical unit regressions | {S["unit_28_historical_candidate"]} |
| BUG-25..30 Conda regressions | baseline {S["unit_bug25_30_baseline"]}; candidate {S["unit_bug25_30_candidate"]} |
| Issue #92 baseline-vs-candidate | {S["issue92_baseline_vs_candidate_test"]} |
| Live GUI Issue #92 workflow | {S["gui_issue92_candidate"]} |
| Live GUI BUG-14/ADV-003 | baseline {S["gui_bug14_adv003_baseline"]}; candidate {S["gui_bug14_adv003_candidate"]} |
| Live GUI prior-fix revalidation | {S["gui_17fix_revalidation_candidate"]} |
| Combined patch `git apply --check` on baseline | {S["patches"]["combined_apply_check_on_baseline"]} |

## Layout
- `report/OsdagBridge_Screening_Test_Report_Phase20.pdf` — main report (previous: `OsdagBridge_Phase18_Snapshot.pdf`).
- `patches/` — `phase20_combined_all_fixes.patch` (all 24 fixes vs baseline), `phase20_thermal_issue92_isolated.patch`.
- `bug_reports/DEFECT_REGISTER_PHASE20.{{csv,json}}`; `phase20/bug_reports/GITHUB_ISSUE92_RESOLUTION_DRAFT.md`.
- `phase20/` evidence, tests, thermal implementation report; `phase19/`; Phase 1–18 history (`README_PHASE18.md`).

## Pending manual actions
GitHub issue/comment publication, collaborator invitation, resume and video submission. No remote writes were made.
"""
(DST / "README.md").write_text(readme, encoding="utf-8")

# ------------------------------------------------------------------ 2. PDF (Comprehensive 18-Page Phase 20A Technical Report)
import sys
sys.path.insert(0, str(P20 / "tests"))
from build_comprehensive_report_phase20a import build_pdf
build_pdf()

rd = PdfReader(str(PDF_OUT))
pages = len(rd.pages)
empty = [i + 1 for i, p in enumerate(rd.pages) if len((p.extract_text() or "").strip()) < 20]

idx = ["# Evidence Index — Phase 20", ""]
for p in sorted((DST / "phase20").rglob("*")):
    if p.is_file():
        idx.append(f"- `{p.relative_to(DST)}` ({p.stat().st_size} bytes)")
(DST / "EVIDENCE_INDEX.md").write_text("\n".join(idx) + "\n", encoding="utf-8")

# ------------------------------------------------------------------ 3. manifest + zip
for p in list(DST.rglob("*")):
    if junk(p.name):
        shutil.rmtree(p) if p.is_dir() else p.unlink()

substantive_files = sorted(p for p in DST.rglob("*") if p.is_file() and not junk(p.name) and p.name != "SHA256SUMS.json")
manifest = {str(p.relative_to(DST)): sha256(p) for p in substantive_files}
manifest_path = DST / "SHA256SUMS.json"
manifest_path.write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")

# Purge any AppleDouble sidecars created during file write
for p in list(DST.rglob("*")):
    if junk(p.name):
        p.unlink()

all_zip_files = substantive_files + [manifest_path]
ZIP_OUT.unlink(missing_ok=True)
with zipfile.ZipFile(ZIP_OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for p in all_zip_files:
        if not junk(p.name):
            z.write(p, f"phase20-submission/{p.relative_to(DST)}")

with zipfile.ZipFile(ZIP_OUT) as z:
    test = z.testzip()
    names = z.namelist()
    junk_members = [n for n in names if any(junk(part) for part in n.split("/"))]
    mism = [k for k, v in manifest.items()
            if hashlib.sha256(z.read(f"phase20-submission/{k}")).hexdigest() != v]

assert len(junk_members) == 0, f"Found junk members in zip: {junk_members}"
assert len(mism) == 0, f"Found manifest mismatches in zip: {mism}"
assert test is None, f"Corrupted zip detected: {test}"
p18_now = sha256(P18_ZIP)
receipt = {"submission_root": str(DST), "archive": str(ZIP_OUT), "archive_bytes": ZIP_OUT.stat().st_size,
           "archive_sha256": sha256(ZIP_OUT), "zip_members": len(names), "zip_test": "PASS" if test is None else test,
           "zip_junk_members": len(junk_members), "manifest_files": len(manifest), "manifest_mismatches": len(mism),
           "pdf_path": str(PDF_OUT), "pdf_pages": pages, "pdf_pages_without_text": empty,
           "pdf_sha256": sha256(PDF_OUT), "combined_patch_apply_check": S["patches"]["combined_apply_check_on_baseline"],
           "isolated_issue92_patch_apply_check": S["patches"]["isolated_apply_check_on_phase19_commit"],
           "defect_counts": S["defect_counts"], "phase18_zip_sha256": p18_now,
           "phase18_zip_unchanged": p18_now == P18_SHA, "remote_writes": 0}
RECEIPT.write_text(json.dumps(receipt, indent=2))
print(json.dumps(receipt, indent=2))
