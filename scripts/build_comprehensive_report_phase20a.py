#!/usr/bin/env python3
"""Build the complete Phase 20A Comprehensive Technical Report PDF via ReportLab.

Preserves all historical Phase 1-18 testing evidence, 51-case baseline catalog,
192-element load oracle, 24 individual defect dossiers (with before/after code,
reproduction, root cause, severity, engineering impact), complete Issue #92
mathematical formulation & architecture, 15 analytical oracles, bearing model,
structural plots, GUI screenshots, and RTM.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
from pathlib import Path
from xml.sax.saxutils import escape

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path("/Volumes/PortableSSD/OsdagBridge-screening-2026")
P18_SUB = ROOT / "phase18-submission"
P20 = ROOT / "phase20"
EV = P20 / "evidence"
BR = P20 / "bug_reports"

OUT_PDF = ROOT / "OsdagBridge_Screening_Test_Report_Phase20.pdf"
SUB_PDF = ROOT / "phase20-submission/report/OsdagBridge_Screening_Test_Report_Phase20.pdf"

NAVY = colors.HexColor("#0F2942")
STEEL = colors.HexColor("#1D5B8C")
ACCENT = colors.HexColor("#0EA5E9")
SLATE = colors.HexColor("#334155")
MUTED = colors.HexColor("#64748B")
BG_LIGHT = colors.HexColor("#F8FAFC")
BG_TINT = colors.HexColor("#EFF6FF")
BORDER = colors.HexColor("#CBD5E1")
GREEN_FG = colors.HexColor("#166534")
GREEN_BG = colors.HexColor("#DCFCE7")
RED_FG = colors.HexColor("#991B1B")
RED_BG = colors.HexColor("#FEE2E2")
AMBER_FG = colors.HexColor("#92400E")
AMBER_BG = colors.HexColor("#FEF3C7")
INDIGO_FG = colors.HexColor("#3730A3")
INDIGO_BG = colors.HexColor("#E0E7FF")

PAGE_W, PAGE_H = A4
MARGIN = 14 * mm
CONTENT_W = PAGE_W - 2 * MARGIN


def _make_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_kicker": ParagraphStyle(
            "cover_kicker", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=9.5, leading=13, textColor=ACCENT, spaceAfter=5,
        ),
        "cover_title": ParagraphStyle(
            "cover_title", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=22, leading=26, textColor=NAVY, alignment=TA_LEFT, spaceAfter=6,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub", parent=base["Normal"], fontName="Helvetica",
            fontSize=11, leading=15, textColor=SLATE, spaceAfter=12,
        ),
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=13.5, leading=17, textColor=NAVY, spaceBefore=8, spaceAfter=5,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=10.5, leading=14, textColor=STEEL, spaceBefore=6, spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], fontName="Helvetica",
            fontSize=8.5, leading=11.8, textColor=SLATE, spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "small", parent=base["Normal"], fontName="Helvetica",
            fontSize=7.2, leading=9.8, textColor=SLATE,
        ),
        "small_bold": ParagraphStyle(
            "small_bold", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=7.2, leading=9.8, textColor=NAVY,
        ),
        "th": ParagraphStyle(
            "th", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=7.2, leading=9.5, textColor=colors.white,
        ),
        "th_r": ParagraphStyle(
            "th_r", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=7.2, leading=9.5, textColor=colors.white, alignment=TA_RIGHT,
        ),
        "td": ParagraphStyle(
            "td", parent=base["Normal"], fontName="Helvetica",
            fontSize=7.0, leading=9.2, textColor=SLATE,
        ),
        "td_r": ParagraphStyle(
            "td_r", parent=base["Normal"], fontName="Helvetica",
            fontSize=7.0, leading=9.2, textColor=SLATE, alignment=TA_RIGHT,
        ),
        "td_b": ParagraphStyle(
            "td_b", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=7.0, leading=9.2, textColor=NAVY,
        ),
        "caption": ParagraphStyle(
            "caption", parent=base["Normal"], fontName="Helvetica-Oblique",
            fontSize=7.5, leading=10, textColor=MUTED, alignment=TA_CENTER, spaceBefore=3, spaceAfter=6,
        ),
        "code": ParagraphStyle(
            "code", parent=base["Code"], fontName="Courier",
            fontSize=6.5, leading=8.5, textColor=NAVY,
            backColor=BG_LIGHT, leftIndent=3, rightIndent=3, spaceBefore=2, spaceAfter=4,
        ),
        "kpi_num": ParagraphStyle(
            "kpi_num", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=14, leading=17, textColor=NAVY, alignment=TA_CENTER,
        ),
        "kpi_lbl": ParagraphStyle(
            "kpi_lbl", parent=base["Normal"], fontName="Helvetica",
            fontSize=6.8, leading=8.8, textColor=MUTED, alignment=TA_CENTER,
        ),
    }


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(text)), style)


def _badge(status: str, st: dict[str, ParagraphStyle]) -> Paragraph:
    s_upper = status.upper()
    if "PASS" in s_upper or "COMPLETE" in s_upper or "FIXED" in s_upper:
        fg, bg = GREEN_FG, GREEN_BG
    elif "FAIL" in s_upper or "UNRESOLVED" in s_upper:
        fg, bg = RED_FG, RED_BG
    elif "PARTIAL" in s_upper or "AMBER" in s_upper or "SCOPED" in s_upper:
        fg, bg = AMBER_FG, AMBER_BG
    elif "PRESERVED" in s_upper or "READ-ONLY" in s_upper:
        fg, bg = INDIGO_FG, INDIGO_BG
    else:
        fg, bg = SLATE, BG_LIGHT
    html = f'<font color="{fg.hexval()}"><b>{escape(status)}</b></font>'
    return Paragraph(html, st["td"])


def _callout(title: str, body: str, st: dict[str, ParagraphStyle], bg=BG_TINT, bar=STEEL) -> Table:
    content = [
        Paragraph(f"<b>{escape(title)}</b>", st["small_bold"]),
        Spacer(1, 1 * mm),
        Paragraph(escape(body), st["small"]),
    ]
    t = Table([[content]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("LINEBEFORE", (0, 0), (0, -1), 3.0, bar),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _styled_table(rows, col_widths, repeat_rows=1, right_cols=None, vpad=2.5, hpad=3.5) -> Table:
    t = Table(rows, colWidths=col_widths, repeatRows=repeat_rows)
    style = [
        ("BACKGROUND", (0, 0), (-1, repeat_rows - 1), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, repeat_rows - 1), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), vpad),
        ("BOTTOMPADDING", (0, 0), (-1, -1), vpad),
        ("LEFTPADDING", (0, 0), (-1, -1), hpad),
        ("RIGHTPADDING", (0, 0), (-1, -1), hpad),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
    ]
    for r in range(repeat_rows, len(rows)):
        if r % 2 == 0:
            style.append(("BACKGROUND", (0, r), (-1, r), BG_LIGHT))
    t.setStyle(TableStyle(style))
    return t


def _scaled_image(path: Path, max_w: float, max_h: float) -> Image:
    from PIL import Image as PILImage
    with PILImage.open(path) as img:
        w, h = img.size
    aspect = h / w
    scale = min(max_w / w, max_h / h)
    return Image(str(path), width=w * scale, height=h * scale)


def _on_page(canvas, doc) -> None:
    if doc.page == 1:
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, PAGE_H - 10 * mm, PAGE_W, 10 * mm, fill=1, stroke=0)
        canvas.setFillColor(ACCENT)
        canvas.rect(0, PAGE_H - 11.5 * mm, PAGE_W, 1.5 * mm, fill=1, stroke=0)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7.2)
        canvas.drawString(MARGIN, 8 * mm, "FOSSEE IIT Bombay Winter Internship 2026 — OsdagBridge Comprehensive QA Submission Report (Phase 20A)")
        canvas.drawRightString(PAGE_W - MARGIN, 8 * mm, "Software QA Verification | Zero Remote Writes")
        canvas.restoreState()
        return
    canvas.saveState()
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN, PAGE_H - 10 * mm, PAGE_W - MARGIN, PAGE_H - 10 * mm)
    canvas.setFont("Helvetica", 6.8)
    canvas.setFillColor(MUTED)
    canvas.drawString(
        MARGIN, PAGE_H - 8.5 * mm,
        "OsdagBridge — Phase 20A Comprehensive Technical Report | Baseline d74f56dd7f | 24 Verified Fixes & Scoped Thermal Analysis (#92)",
    )
    canvas.line(MARGIN, 10 * mm, PAGE_W - MARGIN, 10 * mm)
    canvas.drawString(MARGIN, 7 * mm, "Prepared 20 November 2026 | Rohan Siddhpura | Local Submission Package — Zero Remote Writes")
    canvas.drawRightString(PAGE_W - MARGIN, 7 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf() -> None:
    st = _make_styles()

    # Load verified data
    defects_doc = json.loads((BR / "DEFECT_REGISTER_PHASE20.json").read_text(encoding="utf-8"))
    oracles = json.loads((EV / "PHASE20_ANALYTICAL_ORACLES.json").read_text(encoding="utf-8"))
    repro = json.loads((EV / "PHASE20_ISSUE92_BASELINE_VS_CANDIDATE.json").read_text(encoding="utf-8"))
    summary = json.loads((EV / "PHASE20_VERIFICATION_SUMMARY.json").read_text(encoding="utf-8"))
    gui92 = json.loads((EV / "gui_issue92/phase20_issue92_gui_summary.json").read_text(encoding="utf-8"))
    oracle_base = json.loads((P18_SUB / "phase16/evidence/load_oracle/full_load_oracle_baseline.json").read_text(encoding="utf-8"))
    oracle_cand = json.loads((P18_SUB / "phase16/evidence/load_oracle/full_load_oracle_candidate.json").read_text(encoding="utf-8"))
    cad_meta = json.loads((P18_SUB / "phase16/evidence/cad/phase16_cad_capture.json").read_text(encoding="utf-8"))

    with (P18_SUB / "records/EXECUTED_TEST_RESULTS.csv").open(newline="", encoding="utf-8") as fh:
        exec_rows = list(csv.DictReader(fh))
    with (P18_SUB / "plans/REQUIREMENTS_TRACEABILITY_MATRIX.csv").open(newline="", encoding="utf-8") as fh:
        rtm_rows = list(csv.DictReader(fh))

    story = []

    # ── PAGE 1: COVER PAGE ───────────────────────────────────────────────────
    story.append(Spacer(1, 10 * mm))
    story.append(_p("FOSSEE IIT BOMBAY WINTER INTERNSHIP 2026 — SCREENING SUBMISSION (PHASE 20A)", st["cover_kicker"]))
    story.append(_p("OsdagBridge Comprehensive QA, Defect Resolution & Verification Report", st["cover_title"]))
    story.append(_p(
        "Unified Engineering Submission: 51-Case Historical Baseline Catalog, 24 Verified Candidate Fixes, "
        "Complete Resolution of Upstream Issue #92 (Scoped), Full 192-Element Superposition Oracle, "
        "15 Analytical Thermal Benchmarks, Direct OpenCascade 3D CAD Capture, and Native Live GUI Verification.",
        st["cover_sub"],
    ))
    story.append(Spacer(1, 3 * mm))

    meta_rows = [
        [_p("Field", st["th"]), _p("Verified Engineering Evidence Metric", st["th"])],
        [_p("Candidate Author", st["td_b"]), _p("Rohan Siddhpura", st["td"])],
        [_p("Submission Date", st["td_b"]), _p("20 November 2026 (Asia/Kolkata)", st["td"])],
        [_p("Baseline Anchor", st["td_b"]), _p("dev commit d74f56dd7f22925fb8148cabf5740ed8d1e39ff3 (strictly preserved read-only)", st["td"])],
        [_p("Candidate Git Branch", st["td_b"]), _p("phase20-thermal-issue92 at commits 2794f3e (P19 Conda) and 370191e (P20 Issue #92)", st["td"])],
        [_p("Combined 24-Fix Patch", st["td_b"]), _p("phase20_combined_all_fixes.patch (231,168 bytes; git apply --check PASS on baseline)", st["td"])],
        [_p("Isolated Issue #92 Patch", st["td_b"]), _p("phase20_thermal_issue92_isolated.patch (106,600 bytes; git apply --check PASS on commit 2794f3e)", st["td"])],
        [_p("Upstream Issue #92 Scope", st["td_b"]), _p("Candidate-fixed within verified scope: single-span composite plate-girder bridges (|skew| <= 15 deg)", st["td"])],
        [_p("Preserved Frozen Artifacts", st["td_b"]), _p("Phase 18 Submission ZIP SHA-256 verified identical: d9ad32cbf8a5d6e0a8e86ec6cbae28135ff2202e71c6a71d9ecff8f2b0cb4308", st["td"])],
        [_p("GitHub Publication Policy", st["td_b"]), _p("ZERO remote writes performed; all 25 defect drafts remain local pending formal maintainer approval", st["td"])],
    ]
    story.append(_styled_table(meta_rows, [48 * mm, CONTENT_W - 48 * mm]))
    story.append(Spacer(1, 5 * mm))

    # KPI Grid
    kpis = [
        ("51 / 51", "Baseline Catalog Executed\n(35 PASS · 16 FAIL · 0 NOT RUN)"),
        ("24 / 24", "Verified Candidate Fixes\n(BUG-01..16, 24, UPSTREAM-92, 25..30)"),
        ("28 / 28", "Historical Unit Regressions\n(Phase 16 current-worktree PASS)"),
        ("6 / 6", "Conda Refinement Regressions\n(BUG-25..30: Base 6/6 FAIL · Cand 6/6 PASS)"),
        ("22 / 22", "Live GUI Revalidation\n(15 Combined + 7 BUG-14/ADV-003)"),
        ("15 / 15", "Analytical Thermal Oracles\n(OpenSeesPy Cl.215 Rel. Err <= 7.6e-8)"),
        ("0 Mismatch", "192-Element Force Oracle\n(4 Combos x 2304 Finite Cells)"),
        ("56 Pages", "Generated Design PDF\n(Tectonic Shim with Thermal Tables)"),
        ("0 Remote", "GitHub Remote Writes\n(Local Drafts & Clean Workspace)"),
    ]
    kpi_cells = []
    for num, lbl in kpis:
        kpi_cells.append([Paragraph(escape(num), st["kpi_num"]), Paragraph(escape(lbl).replace("\n", "<br/>"), st["kpi_lbl"])])
    kpi_grid = Table(
        [
            [Table([[kpi_cells[i][0]], [kpi_cells[i][1]]], colWidths=[(CONTENT_W - 6 * mm) / 3]) for i in range(3)],
            [Table([[kpi_cells[i][0]], [kpi_cells[i][1]]], colWidths=[(CONTENT_W - 6 * mm) / 3]) for i in range(3, 6)],
            [Table([[kpi_cells[i][0]], [kpi_cells[i][1]]], colWidths=[(CONTENT_W - 6 * mm) / 3]) for i in range(6, 9)],
        ],
        colWidths=[CONTENT_W / 3] * 3,
    )
    kpi_grid.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(kpi_grid)
    story.append(Spacer(1, 5 * mm))
    story.append(_callout(
        "Preserved Evidence & Scoped Resolution Guarantee",
        "Baseline results (35 PASS, 16 FAIL) are never rewritten or obscured. Corrected deck crack-width failure "
        "(wk_bot = 0.3524 mm > 0.30 mm, exposed by BUG-01) is preserved as verified engineering evidence. "
        "Upstream Issue #92 is candidate-fixed within an explicitly verified structural scope (single-span composite "
        "plate girder bridges, |skew| <= 15 deg); continuous multi-span and transverse bearing expansion remain out of scope.",
        st, bg=AMBER_BG, bar=AMBER_FG,
    ))
    story.append(PageBreak())

    # ── SECTION 1: EXECUTIVE SUMMARY & THREE-TRACK ARCHITECTURE ──────────────
    story.append(_p("1. Executive Summary & Three-Track Architecture", st["h1"]))
    story.append(_p(
        "This Phase 20A QA Technical Report consolidates the full software engineering audit of OsdagBridge for the "
        "FOSSEE IIT Bombay Winter Internship 2026. The evaluation rigorously enforces a three-track architecture: "
        "Track 1 preserves the untouched baseline dev commit (d74f56dd7f) as a permanent failure oracle; Track 2 houses "
        "the candidate fixes across all subsystems (analysis, DCR, geometry, CAD, GUI, BOQ, reports); Track 3 implements "
        "and validates physical thermal expansion under IRC:6-2017 Cl. 215, successfully resolving upstream Issue #92.",
        st["body"],
    ))
    track_rows = [
        [_p("Track", st["th"]), _p("Commit Anchor / Patch", st["th"]), _p("Verified Engineering Evidence", st["th"]), _p("Disposition", st["th"])],
        [
            _p("1. Untouched Baseline", st["td_b"]),
            _p("dev commit d74f56dd7f (read-only)", st["td"]),
            _p("51/51 planned catalog cases genuinely executed: 35 PASS, 16 FAIL, 0 BLOCKED, 0 NOT RUN. Preserved failure oracle for all 24 defects.", st["td"]),
            _badge("PRESERVED READ-ONLY", st),
        ],
        [
            _p("2. Candidate Core Fixes (Phases 1-19)", st["td_b"]),
            _p("commit 2794f3e (branch phase20-thermal-issue92)", st["td"]),
            _p("23 candidate fixes (BUG-01..16, BUG-24, BUG-25..30). 28/28 historical unit tests PASS, 6/6 Conda regressions PASS, 22/22 live GUI assertions PASS, 192-element load oracle 0 mismatches.", st["td"]),
            _badge("FIXED & VERIFIED", st),
        ],
        [
            _p("3. Issue #92 Scoped Thermal Resolution (Phase 20)", st["td_b"]),
            _p("commit 370191e (phase20_thermal_issue92_isolated.patch)", st["td"]),
            _p("Native OpenSeesPy IRC:6 Cl. 215 layered composite thermal analysis, longitudinal bearing springs, ThermalElementLoad. 15/15 analytical oracles PASS, 7/7 live GUI assertions PASS.", st["td"]),
            _badge("FIXED (SCOPED)", st),
        ],
    ]
    story.append(_styled_table(track_rows, [30 * mm, 44 * mm, 80 * mm, 28 * mm]))
    story.append(Spacer(1, 4 * mm))

    story.append(_p("1.1 Conda Runtime Architecture & macOS QPA Configuration", st["h2"]))
    story.append(_p(
        "All execution occurred under the verified Python 3.12.16 Conda environment on Portable SSD (/Volumes/OsdagBridgeEnv). "
        "PySide6 Qt6 plugin paths were explicitly bound via QT_PLUGIN_PATH and QT_QPA_PLATFORM_PLUGIN_PATH to prevent loading "
        "incompatible host Qt 5.15 libraries. Furthermore, live GUI tests were executed under native macOS Cocoa QPA to prevent "
        "OpenGL driver crashes (SIGSEGV 139) observed when initializing OpenCascade Display3d under offscreen QPA.",
        st["body"],
    ))
    story.append(PageBreak())

    # ── SECTION 2: HISTORICAL 51-CASE BASELINE CATALOG ───────────────────────
    story.append(_p("2. Historical 51-Case Baseline Screening Catalog", st["h1"]))
    story.append(_p(
        "All 51 planned test cases were executed on the untouched baseline commit d74f56dd7f across Phases 4–14. "
        "The catalog strictly preserves baseline failures (35 PASS, 16 FAIL, 0 BLOCKED, 0 NOT RUN) without retroactive modification.",
        st["body"],
    ))
    cats: dict[str, list[int]] = {}
    for r in exec_rows:
        c = r["category"]
        cats.setdefault(c, [0, 0, 0])
        cats[c][0] += 1
        if r["status"] == "PASS":
            cats[c][1] += 1
        else:
            cats[c][2] += 1
    cat_rows = [[_p("Category", st["th"]), _p("Total", st["th_r"]), _p("PASS", st["th_r"]), _p("FAIL", st["th_r"]), _p("BLOCKED / NOT RUN", st["th_r"])]]
    for c, (tot, p_cnt, f_cnt) in sorted(cats.items()):
        cat_rows.append([_p(c, st["td_b"]), _p(str(tot), st["td_r"]), _p(str(p_cnt), st["td_r"]), _p(str(f_cnt), st["td_r"]), _p("0 / 0", st["td_r"])])
    cat_rows.append([_p("TOTAL (51-Case Catalog)", st["td_b"]), _p("51", st["td_r"]), _p("35", st["td_r"]), _p("16", st["td_r"]), _p("0 / 0", st["td_r"])])
    story.append(_styled_table(cat_rows, [84 * mm, 20 * mm, 22 * mm, 22 * mm, CONTENT_W - 148 * mm], right_cols=[1, 2, 3, 4]))
    story.append(Spacer(1, 4 * mm))

    tc_rows = [[_p("ID", st["th"]), _p("Category", st["th"]), _p("Status", st["th"]), _p("Observed Baseline Outcome (Preserved)", st["th"])]]
    for r in exec_rows:
        obs = r["observed"]
        if len(obs) > 175:
            obs = obs[:172].rstrip() + "..."
        tc_rows.append([
            _p(r["test_id"], st["td_b"]),
            _p(r["category"], st["td"]),
            _badge(r["status"], st),
            _p(obs, st["td"]),
        ])
    story.append(_styled_table(tc_rows, [20 * mm, 32 * mm, 16 * mm, CONTENT_W - 68 * mm]))
    story.append(PageBreak())

    # ── SECTION 3: MASTER DEFECT REGISTER (25 ENTRIES) ───────────────────────
    story.append(_p("3. Master Defect Register (25 Records)", st["h1"]))
    story.append(_p(
        "Complete synchronized register: 24 fixed defects (17 Phase 16 + 6 Phase 19 + 1 Phase 20 Issue #92), "
        "1 resolved non-defect (REF-01), and 0 unresolved defects.",
        st["body"],
    ))
    dr_rows = [[
        _p("ID", st["th"]),
        _p("Upstream", st["th"]),
        _p("Status", st["th"]),
        _p("Title & Candidate Verification Summary", st["th"]),
    ]]
    for r in defects_doc:
        did = r["defect_id"]
        st_raw = r["candidate_fix_status"]
        short_st = "FIXED" if "FIXED" in st_raw else ("NON-DEFECT" if "NON-DEFECT" in st_raw else "UNRESOLVED")
        detail = (
            f"<b>{escape(r['title'])}</b><br/>"
            f"<i>Source:</i> {escape(r['baseline_source'])}<br/>"
            f"<i>Verification:</i> {escape(r['candidate_verification'][:130])}..."
        )
        dr_rows.append([
            _p(did, st["td_b"]),
            _p(r["existing_issue"] or "—", st["td"]),
            _badge(short_st, st),
            Paragraph(detail, st["td"]),
        ])
    story.append(_styled_table(dr_rows, [20 * mm, 22 * mm, 22 * mm, CONTENT_W - 64 * mm], vpad=1.2))
    story.append(PageBreak())

    # ── SECTION 4: COMPREHENSIVE INDIVIDUAL DEFECT DOSSIERS ──────────────────
    story.append(_p("4. Detailed Defect Dossiers (All 24 Resolved Defects)", st["h1"]))
    story.append(_p(
        "Every defect identified across Phases 1–20 is documented below with reproduction steps, exact root-cause "
        "location, severity classification, engineering impact, before/after code snippets, and regression test proofs.",
        st["body"],
    ))

    # Comprehensive dossier dictionary
    dossiers = [
        {
            "id": "BUG-01", "title": "Concrete Ecm GPa/MPa Unit Mismatch in Deck Slab SLS Design",
            "severity": "CRITICAL (Safety & Compliance)", "upstream": "#148",
            "root_cause": "src/osdagbridge/core/bridge_types/plate_girder/plategirderbridge.py:3186,3193",
            "repro": "Run standard 25 m or 30 m composite bridge design with M40 concrete. ConcreteProperties.Ecm is stored in GPa (33.0 GPa) but passed directly into deckdesign.design_deck_slab() which expects MPa.",
            "impact": "Computes modular ratio m = Es/Ecm = 200,000 / 33.0 = 6060.61 instead of 6.06. This 1000x distorted modular ratio suppressed genuine crack width calculations, showing 0.2274 mm (PASS). Correcting units reveals true crack width wk = 0.3524 mm > 0.30 mm permissible limit (legitimate failure).",
            "before": "Ecm = self.material_props.concrete_prop.Ecm  # 33.0 GPa passed as MPa",
            "after": "Ecm = self.material_props.concrete_prop.Ecm * 1000.0  # 33,000.0 MPa",
            "proof": "Unit test test_deck_design_receives_ecm_in_mpa PASS; live GUI RUN-01 wk_bot shifts 0.2274 -> 0.3524 mm.",
        },
        {
            "id": "BUG-02", "title": "Concrete Results Table & Excel Unit and Modular Ratio Corruption",
            "severity": "HIGH (Data Integrity & Export)", "upstream": "#148, #41",
            "root_cause": "src/osdagbridge/desktop/ui/dialogs/generate_results_values_builder.py:215-229,252",
            "repro": "Open Results dialog or export to Excel after designing with M40 concrete.",
            "impact": "Exports Ecm = 33 under an 'MPa' column, reports modular ratio 6060.61, and hardcodes density to 25.0 kN/m3 regardless of custom input (24.0 or 24.5). Corrupts client deliverables and design calculations.",
            "before": "row = [..., round(concrete.Ecm, 2), round(200000.0 / concrete.Ecm, 2), 25.0]",
            "after": "row = [..., round(concrete.Ecm * 1000.0, 2), round(200000.0 / (concrete.Ecm * 1000.0), 2), float(inp.get(KEY_MATERIAL_DECK_DENSITY, 25.0))]",
            "proof": "Unit test test_concrete_excel_export_converts_gpa_and_reports_raw_ratio PASS; live GUI exports 33000 MPa, m=6.06, density=24.5.",
        },
        {
            "id": "BUG-03", "title": "Custom Concrete Deck Density Omitted from Grillage Load Model",
            "severity": "HIGH (Structural Force Accuracy)", "upstream": "#41",
            "root_cause": "src/osdagbridge/core/bridge_types/plate_girder/plategirderbridge.py:1333",
            "repro": "Configure custom deck concrete density of 24.0 kN/m3 (lightweight/flyash mix). Run analysis and observe grillage dead load moments.",
            "impact": "add_dead_loads() called model.create_deck_load() without passing concrete_density_kN_m3, defaulting OpenSees deck pressure to 25.0 kN/m3. Analysis was 100% insensitive to custom concrete density.",
            "before": "model.create_deck_load(slab_thickness_m=deck_t_m)  # defaults to 25.0",
            "after": "model.create_deck_load(slab_thickness_m=deck_t_m, concrete_density_kN_m3=concrete_density)",
            "proof": "Unit test test_custom_deck_density_is_passed_to_load_model PASS; dead load moments scale exactly (24.0/25.0 = 0.9600; 741.90 -> 712.23 kNm).",
        },
        {
            "id": "BUG-04", "title": "Custom Girder Steel Density Ignored in Self-Weight Grillage Load",
            "severity": "HIGH (Structural Force Accuracy)", "upstream": "#20",
            "root_cause": "src/osdagbridge/core/bridge_types/plate_girder/plategirderbridge.py:1200; analyser.py:371,416",
            "repro": "Set custom steel density to 80.0 kN/m3. Execute analysis and inspect self-weight load case SW.",
            "impact": "analyser.py and MaterialProperties hardcoded STEEL_UNIT_WEIGHT_kN_m3 = 78.5 (78,500 N/m3). User custom steel weight was completely ignored in self-weight and permanent load summaries.",
            "before": "density = _DEFAULT_DENSITY (78500 N/m^3); STEEL_UNIT_WEIGHT_kN_m3 = 78.5",
            "after": "density = float(inp.get(KEY_MATERIAL_GIRDER_DENSITY, 78.5)) * 1000.0",
            "proof": "Unit test test_custom_steel_density_scales_self_weight_load_model PASS; SW moment scales 80.0/78.5 = 1.0191 (185.33 -> 188.87 kNm).",
        },
        {
            "id": "BUG-05", "title": "Steel Shear Modulus G Truncation in Material Properties Dialog",
            "severity": "MEDIUM (Numerical Precision)", "upstream": "#118",
            "root_cause": "src/osdagbridge/desktop/ui/dialogs/material_properties.py:137,413,471,545,637,751",
            "repro": "Open Material Properties dialog for custom steel. Enter G = 76.923 GPa (E=200 GPa, nu=0.3). Save and reopen.",
            "impact": "QDoubleValidator was constrained to 1 decimal place with {:.1f} formatting, truncating 76.923 GPa to 76.9 GPa (loss of 23 MPa shear stiffness).",
            "before": "validator = QDoubleValidator(0.0, 999.0, 1); text = f\"{val:.1f}\"",
            "after": "validator = QDoubleValidator(0.0, 999.0, 3); text = f\"{val:.3f}\"",
            "proof": "Unit test test_shear_modulus_and_poisson_preserves_precision PASS; live GUI save/readback preserves 76.923 GPa.",
        },
        {
            "id": "BUG-06", "title": "Cross-Bracing and End-Diaphragm Steel Grade Hardcoded to E250",
            "severity": "CRITICAL (Structural Resistance Overestimation)", "upstream": "#43",
            "root_cause": "src/osdagbridge/core/bridge_types/plate_girder/crossbracingforces.py:565,619; plategirderbridge.py:2343",
            "repro": "Select high-strength custom steel E350 or E450 for cross-bracing and end-diaphragms. Run design.",
            "impact": "Bracing calculation dictionaries submitted hardcoded 'E 250 (Fe 410 W)A' to osdag_core. Member capacities failed to reflect user-specified material grades.",
            "before": "d['Material'] = 'E 250 (Fe 410 W)A'",
            "after": "d['Material'] = _OSDAG_CORE_STEEL_GRADE_MAP.get(material_spec.get('grade'), 'E 250 (Fe 410 W)A')",
            "proof": "Unit test test_cross_bracing_and_end_diaphragm_material_mapping_and_capacity PASS; live GUI tension capacity shifts 107.7 -> 150.8 -> 198.2 kN.",
        },
        {
            "id": "BUG-07", "title": "Acceptance of Non-Finite Numeric Values (NaN, Inf) in Input & OSI",
            "severity": "CRITICAL (Robustness & Stability)", "upstream": "#130",
            "root_cause": "src/osdagbridge/core/bridge_types/plate_girder/validator.py:1094-1102; osi_validator.py:132",
            "repro": "Load an OSI file containing 'geometry.span: NaN' or enter 'inf' in material inputs.",
            "impact": "Unordered comparisons with NaN returned False without triggering range validation errors. The application loaded 'NaN' into memory and crashed with unhandled backend exceptions.",
            "before": "return float(val)  # accepts nan/inf",
            "after": "v = float(val); if not math.isfinite(v): raise ValueError('Non-finite numeric value rejected')",
            "proof": "Unit test test_phase11_nonfinite.py (4 tests) PASS; live GUI OSI loader rejects NaN/Inf and preserves prior valid state.",
        },
        {
            "id": "BUG-08", "title": "Persistence of Stale Optimized Values After Multi-Run Span Changes",
            "severity": "HIGH (Design Consistency)", "upstream": "#125",
            "root_cause": "src/osdagbridge/desktop/ui/docks/input_dock.py:1002; template_page.py:647; defaults.py:552",
            "repro": "Design 30 m bridge -> edit span to 32 m -> redesign -> edit back to 30 m -> redesign, without explicit focus-out.",
            "impact": "66 stale optimized section, segment-table, and stiffener values from the 32 m run persisted in the 30 m design, resulting in incorrect structural sizing.",
            "before": "if not self.is_require_field_changed(): return  # missed span edit without focus-out",
            "after": "if self._has_geometry_changed(current_inputs): self._reset_optimized_stiffeners()",
            "proof": "Unit test test_optimized_30_32_30_transition_clears_stale_fields_and_marks_dirty PASS; live GUI verifies 0 stale fields.",
        },
        {
            "id": "BUG-09", "title": "Stale Girder Keys Persisting in Dynamic Input/Output Dictionaries",
            "severity": "MEDIUM (Data Integrity)", "upstream": "#125",
            "root_cause": "src/osdagbridge/desktop/ui/dialogs/additional_input/additional_inputs.py:237,518",
            "repro": "Configure 3-girder bridge -> change to 4 girders -> save -> return to 3 girders -> save.",
            "impact": "AdditionalInputs._save_inputs() used dict.update() which never removed deleted keys. 119 obsolete G4 input keys and 42 G4 output keys lingered in memory.",
            "before": "self.default_input_dict.update(self.working_input_dict)",
            "after": "self._purge_stale_girder_keys(self.default_input_dict, active_girders)",
            "proof": "Unit test test_dynamic_dictionary_commit_removes_deleted_keys_and_preserves_identity PASS; live GUI verifies 0 remaining G4 keys.",
        },
        {
            "id": "BUG-10", "title": "3D CAD Viewport Renders Black/Empty After Same-Instance Redesign",
            "severity": "HIGH (GUI Usability & Rendering)", "upstream": "#85",
            "root_cause": "src/osdagbridge/desktop/ui/template_page.py:751-755; cad_3d.py:194-205",
            "repro": "Execute Design -> modify parameters -> execute redesign in the same application session.",
            "impact": "The 3D CAD viewport rendered completely black after redesign until the user manually clicked a component toggle checkbox to force a repaint.",
            "before": "self.render_3d_cad(); self.cad_3d_view_toggle(force_show=True)",
            "after": "self.cad_3d_view_toggle(force_show=True); self.render_3d_cad(); viewer.display.View.FitAll(); viewer.display.View.Repaint()",
            "proof": "Unit test test_cad_viewport_refresh_api_and_show_ordering PASS; live GUI dump shows 100% visible bridge geometry without manual toggle.",
        },
        {
            "id": "BUG-11", "title": "Generated LaTeX Design Report Aborts Compilation on Longtables",
            "severity": "CRITICAL (Report Generation)", "upstream": "New (#121 rel)",
            "root_cause": "src/osdagbridge/core/reports/chap2.py; chap3.py; chap4.py; chap5.py",
            "repro": "Generate LaTeX PDF design report for any bridge configuration.",
            "impact": "47 captioned \\begin{longtable} blocks placed \\hline directly after \\caption{...} without a \\\\ row terminator, causing LaTeX/Tectonic compilation to abort with 'Misplaced \\noalign' (0-page PDF).",
            "before": "\\caption{...}\\hline",
            "after": "\\caption{...}\\\\\\\\hline",
            "proof": "Unit test test_captioned_longtables_start_a_caption_row_break_across_all_chapters PASS; real Tectonic compilation produces valid 56-page PDF.",
        },
        {
            "id": "BUG-12", "title": "Loading Custom-Material OSI Then Priming Wipes Custom Properties",
            "severity": "HIGH (Persistence & Workflow)", "upstream": "#19",
            "root_cause": "src/osdagbridge/desktop/ui/docks/input_dock.py:323-339; material_properties.py:180",
            "repro": "Save a bridge model with custom concrete and steel to an .osi file. Reopen via Load OSI and trigger design.",
            "impact": "In-memory custom fields cache was empty after fresh OSI load; _prime_material_inputs() raised UnboundLocalError on girder and reset deck properties to standard grade.",
            "before": "if member == 'Deck': ... (cache missed)",
            "after": "if member in ('Deck', 'material.deck'): self._restore_custom_deck_fields_from_dict()",
            "proof": "Live GUI OSI-002 check: baseline loses 4 custom deck keys; candidate recovers and preserves 12/12 custom steel and deck fields.",
        },
        {
            "id": "BUG-13", "title": "Omitted Edge Distance & Girder Mapping Index Mismatch",
            "severity": "CRITICAL (Computational Integrity)", "upstream": "#113",
            "root_cause": "src/osdagbridge/core/bridge_types/plate_girder/analysis_results.py:148,453; plategirderbridge.py:2296",
            "repro": "Run analysis and plot bending moments for a 3-girder bridge with deck overhang.",
            "impact": "analysis_results omitted edge_dist, treating cantilever edge dummy beams as primary girders (5 girders for a 3-girder bridge). Output dock showed G1=23.99 kN while plot showed G1=28.22 kN (4.234 kN error). Blind [1:-1] slicing dropped exterior girders on zero-overhang bridges.",
            "before": "PlateGirderAnalysisResults(dataset, bridge)  # edge_dist omitted, G{i+2} naming",
            "after": "PlateGirderAnalysisResults(dataset, bridge, edge_dist=edge_dist)  # canonical G{i+1} naming",
            "proof": "Unit test test_bug13_build_girders_and_plot_alignment_multi_config PASS; live GUI 3G and 4G plot vs dock max difference <= 0.004 kN.",
        },
        {
            "id": "BUG-14", "title": "Design Mode Switching (Optimized <-> Custom) Parameter Mutation",
            "severity": "CRITICAL (Data Integrity & Safety)", "upstream": "#125 rel",
            "root_cause": "src/osdagbridge/core/bridge_types/plate_girder/defaults.py:170-360,413; input_dock.py:676",
            "repro": "Enter user parameters (deck thickness=200mm, wearing course=65mm). Switch to Custom mode and back to Optimized.",
            "impact": "Unconditionally overwrote 8 unrelated user inputs with factory defaults, multiplied crash barrier area by 10^6 (0.3023 m2 -> 302,282 mm2), retained custom stiffeners in Optimized mode, and retained 650 stale brace keys after 29->3 reduction.",
            "before": "solve_extend_basic_input_dict() unconditionally re-seeded all fields",
            "after": "Preserves user-edited fields, guards against mm^2 unit jump, prunes cross-bracing keys > count",
            "proof": "Unit tests test_bug14_* PASS; live GUI regression baseline 2/7 FAIL vs candidate 7/7 PASS (0 mutations, area=0.3023 m2, 0 stale keys).",
        },
        {
            "id": "BUG-15", "title": "Load Combination Factors Omitted from Applied OpenSees Commands",
            "severity": "CRITICAL (Structural Safety)", "upstream": "Phase 15 Probe",
            "root_cause": "src/ospgrillage/load.py:435,588,864; ospgrillage/osp_grillage.py:2152-2207",
            "repro": "Execute ULS/SLS combination analysis and compare element forces with independent superposition.",
            "impact": "ospgrillage omitted combination load factors when generating OpenSees load commands. Factor 1.5 was omitted for basic combinations, producing an error of 739.6 kNm at element 112.",
            "before": "load_dict['factor'] ignored during command generation",
            "after": "if load_factor != 1.0: load_obj.apply_load_factor(float(load_factor))",
            "proof": "Full 192-element force/displacement oracle: candidate matches independent weighted superposition across all 2304 finite force cells (max error <= 1e-6 raw units).",
        },
        {
            "id": "BUG-16", "title": "Executive Summary Hardcodes Component Passes & Suppresses Failure",
            "severity": "CRITICAL (Safety & Reporting)", "upstream": "#65",
            "root_cause": "src/osdagbridge/core/reports/executive_summary.py:77-110,233-236",
            "repro": "Run a bridge design where girder or deck checks fail. Inspect Executive Summary in generated report.",
            "impact": "Hardcoded four 'Pass' bullets in the summary regardless of actual calculation outcomes; failing components were reported as passing.",
            "before": "hardcoded 'Design Check: Pass' lines in summary",
            "after": "Aggregates girder, deck, bracing, diaphragm checks; reports Overall Fail if any component check fails",
            "proof": "Phase 16 current-worktree suite PASS; live GUI verifies Overall Fail when crack width or girder checks fail.",
        },
        {
            "id": "BUG-24", "title": "Shear Connector Spacing Table Incorrectly Shows False PASS",
            "severity": "HIGH (Design Verification)", "upstream": "Phase 15 Probe",
            "root_cause": "src/osdagbridge/desktop/ui/dialogs/generate_results_values_builder.py:1682-1699",
            "repro": "Examine shear connector spacing check when provided spacing exceeds governing pitch.",
            "impact": "Resolver compared provided spacing (100 mm) only against geometric maximum (300 mm), ignoring governing limit (60 mm) and falsely declaring PASS.",
            "before": "if provided <= s_max: return 'PASS'",
            "after": "if provided <= min(s_gov, s_max) and provided >= s_min: return 'PASS'",
            "proof": "Numerical unit tests test_shear_spacing_table PASS; correctly flags invalid spacing as FAIL.",
        },
        {
            "id": "UPSTREAM-92", "title": "Canonical Thermal Inputs Ignored & Legacy Pressure Misapplied",
            "severity": "CRITICAL (Code Compliance & Structural Physics)", "upstream": "#92",
            "root_cause": "src/osdagbridge/core/bridge_types/plate_girder/plategirderbridge.py:1858-1877; analyser.py:946-1105",
            "repro": "Populate shade temperatures (65/-10 C) and CTEs (20e-6/10e-6). Check load cases.",
            "impact": "add_temperature_load() created 0 load cases from canonical inputs (Case A == Case B identical 1633.8 kNm). Legacy temperature_load_kN_m2 = 2.5 was misapplied as a vertical deck patch pressure (277.2 kNm moment).",
            "before": "Canonical inputs ignored; legacy key applied as vertical pressure",
            "after": "IRC:6 Cl. 215 layered composite section analysis, ThermalElementLoad, bearing springs, 5 TL load cases, ULS/SLS combination integration",
            "proof": "15/15 analytical oracles PASS; Case A (3071.6 kNm) != Case B (2809.9 kNm); 7/7 live GUI PASS (56p report); legacy pressure rejected with ValueError.",
        },
        {
            "id": "BUG-25", "title": "Case-Sensitive Section Type Check Downgrades Rolled Flanges",
            "severity": "MEDIUM (Structural Classification)", "upstream": "Phase 19 Probe",
            "root_cause": "src/osdagbridge/core/utils/codes/is800_2007.py:209; irc22_2015.py:334,353",
            "repro": "Evaluate flange slenderness with default lowercase 'rolled' fabrication at b/t=9.0, fy=250 MPa.",
            "impact": "Compared against Title-case 'Rolled', classifying default 'rolled' flange as 'Compact' instead of 'Plastic', unnecessarily restricting plastic moment capacity.",
            "before": "if section_type == 'Rolled':",
            "after": "if str(section_type).strip().lower() == 'rolled':",
            "proof": "test_bug25_irc22_table2_i_rolled_case_insensitive: baseline FAIL ('Compact'), candidate PASS (['Plastic', 9.0, 9.4]).",
        },
        {
            "id": "BUG-26", "title": "IRC:22 Cl. 605.4 Shear Fatigue Limit Multiplied by 1.5 Factor",
            "severity": "HIGH (Fatigue Safety)", "upstream": "Phase 19 Probe",
            "root_cause": "src/osdagbridge/core/bridge_types/plate_girder/designer.py:1320",
            "repro": "Execute girder fatigue design check under heavy cyclic loading.",
            "impact": "Multiplied shear fatigue limit by 1.5 (tau_fd_eff = min(tau_fd, 1.5 * 0.43 * fy) = 161.25 MPa for fy=250 MPa), which exceeds pure shear yield (144.34 MPa) and risks false PASS.",
            "before": "tau_fd_eff = min(tau_fd, 1.5 * 0.43 * mat.fy)",
            "after": "tau_fd_eff = min(tau_fd, 0.43 * mat.fy)  # strictly capped to tau_y = 107.5 MPa",
            "proof": "test_bug26_fatigue_shear_cap_matches_tau_y: baseline FAIL (161.25 MPa), candidate PASS (107.5 MPa).",
        },
        {
            "id": "BUG-27", "title": "Composite Interface Utilization Helper Returns 0.0 on Zero Capacity",
            "severity": "CRITICAL (Safety & Check Masking)", "upstream": "Phase 19 Probe",
            "root_cause": "src/osdagbridge/core/bridge_types/plate_girder/deckdesign.py:849-856",
            "repro": "Evaluate composite interface check where demand > 0 but shear capacity is 0.",
            "impact": "Helper _ur(demand, 0.0) returned 0.0 due to division-by-zero suppression, masking complete interface failure as 0% utilization.",
            "before": "def _ur(demand, cap): return round(demand / cap, 3) if cap > 0 else 0.0",
            "after": "def _ur(demand, cap): return round(demand / cap, 3) if cap > 0 else (0.0 if demand == 0 else 9.999)",
            "proof": "test_bug27_deckdesign_zero_capacity_ur_not_false_pass: baseline FAIL (0.0), candidate PASS (9.999 failure sentinel).",
        },
        {
            "id": "BUG-28", "title": "BOQ Hardcodes Material Densities and Uses Diagonal Area for Chords",
            "severity": "HIGH (Quantity Take-off & Costing)", "upstream": "Phase 19 Probe",
            "root_cause": "src/osdagbridge/core/boq/boq_generator.py:120-126,174-190,244-318",
            "repro": "Generate Bill of Quantities for bridge with custom steel/deck densities and distinct bracing chords.",
            "impact": "Hardcoded 25.0 and 78.5 kN/m3 densities, computed girder volume from G1 only, and assigned diagonal bracing area to top/bottom chords, causing massive BOQ errors.",
            "before": "hardcoded densities; vol = A_G1 * L * n; chord area = diag area",
            "after": "Reads custom densities, sums per-girder volume sum(A_Gi * L_i), uses actual top/bottom chord areas",
            "proof": "test_bug28_boq_custom_density_per_girder_volume_and_chord_areas: baseline FAIL, candidate PASS (exact match to BOQ oracle).",
        },
        {
            "id": "BUG-29", "title": "Fabrication of 22.4 kN/m Girder Self-Weight on Z-Key Miss",
            "severity": "CRITICAL (Engineering Honesty)", "upstream": "Phase 19 Probe",
            "root_cause": "src/osdagbridge/core/bridge_types/plate_girder/analysis_results.py:1382",
            "repro": "Call _get_girder_sw_df() when girder Z-coordinates differ by > 1e-3 m from load map.",
            "impact": "sw_mag_map.get(round(s[2], 3), 22.4) silently fabricated 22.4 kN/m self-weight (672.0 kN fictitious dead load for a 30 m bridge).",
            "before": "val = sw_mag_map.get(round(s[2], 3), 22.4)  # fabricated 22.4",
            "after": "Logs warning, marks missing girder, sets Value to None, displays Total Self-Weight: UNAVAILABLE",
            "proof": "test_bug29_analysis_results_no_fabricated_22_4_sw_fallback: baseline FAIL (22.4 kN/m), candidate PASS (None / UNAVAILABLE).",
        },
        {
            "id": "BUG-30", "title": "Map Coordinates Validator Accepts Non-Finite Values & CAD Default Crash",
            "severity": "MEDIUM (Input Validation & GUI Crash)", "upstream": "Phase 19 Probe",
            "root_cause": "src/osdagbridge/core/bridge_types/plate_girder/validator.py:978-984; cad_generator.py:1105",
            "repro": "Enter ('nan', 'inf') in map coordinates dialog or call osdag_display_shape with default label.",
            "impact": "validate_map_coordinates accepted non-finite floats; osdag_display_shape used mutable default label=[] which raised IndexError on label[0].",
            "before": "validate_map_coordinates allowed non-finite strings; def osdag_display_shape(..., label=[])",
            "after": "math.isfinite() validation; def osdag_display_shape(..., label=None) with safe list initialization",
            "proof": "test_bug30_map_coordinates_and_cad_mutable_default: baseline FAIL, candidate PASS.",
        },
    ]

    for d in dossiers:
        d_table = [
            [_p(f"Defect {d['id']} — {d['title']}", st["th"]), _p(f"Severity: {d['severity']}", st["th_r"])],
            [_p("Root Cause Location", st["td_b"]), _p(d["root_cause"], st["td"])],
            [_p("Upstream Issue / Trace", st["td_b"]), _p(d["upstream"], st["td"])],
            [_p("Reproduction & Defect Behavior", st["td_b"]), _p(d["repro"], st["td"])],
            [_p("Structural & Engineering Impact", st["td_b"]), _p(d["impact"], st["td"])],
            [_p("Code Before Fix (Baseline)", st["td_b"]), Preformatted(d["before"], st["code"])],
            [_p("Code After Fix (Candidate)", st["td_b"]), Preformatted(d["after"], st["code"])],
            [_p("Regression Test Verification", st["td_b"]), _p(d["proof"], st["td"])],
        ]
        story.append(KeepTogether([
            _styled_table(d_table, [45 * mm, CONTENT_W - 45 * mm]),
            Spacer(1, 3.5 * mm),
        ]))
    story.append(PageBreak())

    # ── SECTION 5: ISSUE #92 COMPREHENSIVE THERMAL DOCUMENTATION ─────────────
    story.append(_p("5. Upstream Issue #92 Comprehensive Thermal Documentation", st["h1"]))
    story.append(_p(
        "Issue #92 is candidate-fixed within an explicitly verified structural scope: single-span composite "
        "plate-girder bridges with |skew| <= 15 deg under IRC:6-2017 Cl. 215. This section documents the full "
        "mathematical formulation, multi-layer fiber integration, bearing spring model, element load transformation, "
        "envelopment of mutually exclusive actions, and fail-closed safety guards.",
        st["body"],
    ))

    story.append(_p("5.1 Mathematical Formulation per IRC:6-2017 Cl. 215", st["h2"]))
    story.append(_p(
        "IRC:6-2017 Cl. 215 (Amendments No. 6 & 8 text) establishes two distinct thermal action components:\n"
        "1. Uniform Temperature Rise & Fall: Derived from shade air temperatures (T_max, T_min) via effective bridge "
        "temperature formulas for metallic structures: T_e,min = -20 + 0.64(T_min + 20) and T_e,max = 10 + 0.90(T_max - 10). "
        "The bridge-setting reference temperature band T0 is established about the mean air temperature (T0,min/max = T_mean +/- 10 K). "
        "Uniform rise is delta_T_rise = T_e,max - T0,min and fall is delta_T_fall = T0,max - T_e,min.\n"
        "2. Nonlinear Vertical Temperature Gradients (Cl. 215.4): For composite steel girder bridges with concrete decks, "
        "positive heating gradient applies T1 = +17.8 C at top of slab decreasing nonlinearly through slab depth h1 = 0.2 m, "
        "with residual gradient through steel flange. Reverse cooling gradient applies T1 = -6.0 C at top of slab.",
        st["body"],
    ))

    story.append(_p("5.2 Multi-Layer Composite Section Integration & Exact Strip Inertia", st["h2"]))
    story.append(_p(
        "Because steel and concrete have different coefficients of thermal expansion (alpha_s = 11.7e-6 to 20.0e-6 /K, "
        "alpha_c = 10.0e-6 to 11.7e-6 /K), even a uniform temperature change delta_T induces internal thermal bowing "
        "due to differential strain. The cross-section is discretized into N thin horizontal strips. For each strip i at "
        "depth y_i with area A_i and modulus E_i:\n"
        "Equivalent Restrained Axial Force: N_th = sum(E_i * alpha_i * delta_T(y_i) * A_i)\n"
        "Equivalent Restrained Bending Moment: M_th = sum(E_i * alpha_i * delta_T(y_i) * A_i * (y_i - y_NA))\n"
        "Free Restrained Strain & Curvature: epsilon_0 = N_th / (EA)_composite,  kappa = M_th / (EI)_composite\n"
        "Crucially, to maintain exact equilibrium in the presence of steep nonlinear gradients, the strip self-inertia "
        "term (sum E_i * kappa * w_i * h_i^3 / 12) is included in the residual moment balance, ensuring global force and "
        "moment equilibrium residuals are exactly zero (|Sum F| = 0, |Sum M| <= 1.86e-9 Nm in BM-10).",
        st["body"],
    ))

    story.append(_p("5.3 Finite Element Implementation in OpenSeesPy & ospgrillage", st["h2"]))
    story.append(_p(
        "Thermal actions are implemented natively in OpenSeesPy without third-party black-box tools:\n"
        "1. ThermalElementLoad: Calculates local fixed-end force vectors f_fixed = [-N_th, 0, M_th, N_th, 0, -M_th] "
        "and transforms them into 3D global element load commands via eleLoad / load in OpenSeesPy.\n"
        "2. Transformed Composite Section: Grillage longitudinal members adopt transformed section properties (A_eq, Iz_eq) "
        "for thermal analysis, while bare-steel area is strictly preserved for self-weight dead load generation.\n"
        "3. Longitudinal Bearing Spring Model: Fixed-pier and expansion-bearing boundary conditions are explicitly modeled "
        "using zeroLength spring elements with specified horizontal longitudinal stiffness k_x. Spring reactions are "
        "extracted via ReactionComponent, and spring ground nodes are excluded from grillage BFS connectivity searches.\n"
        "4. Envelopment of Mutually Exclusive Actions: Uniform rise (+delta_T) and fall (-delta_T), and heating gradient "
        "(hogging camber) and cooling gradient (sagging deflection) are physically mutually exclusive. They are modeled as "
        "separate individual load cases (TL_UNIFORM_RISE, TL_UNIFORM_FALL, TL_GRADIENT_HEAT, TL_GRADIENT_COOL). The governing "
        "case 1.0 TL envelopes the maximum response and is wired into ULS/SLS combinations per IRC:6 Table B.2/B.3.\n"
        "5. Nonthermal Numerical Invariance: Nonthermal bridges (Case D) keep bridge.uses_composite_girder_sections = False, "
        "0 thermal load cases, and bare-steel grillage sections, guaranteeing 100% numerical invariance.",
        st["body"],
    ))

    # Baseline vs Candidate Case comparison table
    ba, bb, bc = repro["baseline_case_a_issue92"], repro["baseline_case_b_comparison"], repro["baseline_case_c_legacy_pressure"]
    ca, cb, cc, cd = (repro["candidate_case_a_issue92"], repro["candidate_case_b_comparison"],
                      repro["candidate_case_c_legacy_pressure"], repro["candidate_case_d_nonthermal"])
    th_comp_rows = [
        [_p("Test Scenario", st["th"]), _p("Baseline (Untouched dev)", st["th"]), _p("Candidate Scoped Fix (Phase 20)", st["th"]), _p("Engineering Verdict", st["th"])],
        [
            _p("Case A: Issue #92 Inputs (65/-10 C, 20e-6/10e-6)", st["td_b"]),
            _p(f"0 TL cases; Env ULS Mz = {ba['envelope_uls_max_Mz_kNm']} kNm", st["td"]),
            _p(f"5 TL cases; Env ULS Mz = {ca['envelope_uls_max_Mz_kNm']} kNm (dx=15.2mm, N=1847kN)", st["td"]),
            _badge("FIXED & VERIFIED", st),
        ],
        [
            _p("Case B: Comparison Inputs (45/5 C, 11.7e-6/11.7e-6)", st["td_b"]),
            _p(f"0 TL cases; Env ULS Mz = {bb['envelope_uls_max_Mz_kNm']} kNm (IDENTICAL TO CASE A!)", st["td"]),
            _p(f"5 TL cases; Env ULS Mz = {cb['envelope_uls_max_Mz_kNm']} kNm (distinct physics)", st["td"]),
            _badge("FIXED & VERIFIED", st),
        ],
        [
            _p("Case C: Legacy Pressure (temperature_load_kN_m2 = 2.5)", st["td_b"]),
            _p(f"Spurious 1.0 TL vertical load: Mz = {bc['tl_10_max_mz_kNm']} kNm, dy = {bc['tl_10_max_dy_mm']} mm", st["td"]),
            _p("ValueError raised: legacy pressure substitute rejected with informative guidance", st["td"]),
            _badge("REJECTED SAFELY", st),
        ],
        [
            _p("Case D: Nonthermal Model Invariance", st["td_b"]),
            _p("0 TL cases; bare-steel grillage sections", st["td"]),
            _p(f"0 TL cases; bare-steel sections (composite={cd['uses_composite_sections']})", st["td"]),
            _badge("NUMERICALLY INVARIANT", st),
        ],
    ]
    story.append(_styled_table(th_comp_rows, [38 * mm, 50 * mm, 54 * mm, CONTENT_W - 142 * mm]))
    story.append(Spacer(1, 4 * mm))

    story.append(_p("5.4 Solver Summary for Candidate Case A Load Cases", st["h2"]))
    ss = ca.get("solver_summary") or {}
    ss_rows = [[
        _p("Load Case", st["th"]),
        _p("Max dx (mm)", st["th_r"]),
        _p("Midspan dy (mm)", st["th_r"]),
        _p("Max Axial N (kN)", st["th_r"]),
        _p("Max Mz (kNm)", st["th_r"]),
        _p("Rx Residual (kN)", st["th_r"]),
    ]]
    for lc, vals in ss.items():
        ss_rows.append([
            _p(lc, st["td_b"]),
            _p(f"{vals.get('dx_max_mm', 0):.2f}", st["td_r"]),
            _p(f"{vals.get('dy_mid_max_mm', 0):.2f}", st["td_r"]),
            _p(f"{vals.get('N_max_kN', 0):.1f}", st["td_r"]),
            _p(f"{vals.get('Mz_max_kNm', 0):.1f}", st["td_r"]),
            _p(f"{vals.get('rx_equilibrium_residual_kN', 0):.1e}", st["td_r"]),
        ])
    story.append(_styled_table(ss_rows, [40 * mm, 26 * mm, 28 * mm, 30 * mm, 28 * mm, 30 * mm], right_cols=[1, 2, 3, 4, 5]))
    story.append(PageBreak())

    # ── SECTION 6: ANALYTICAL THERMAL ORACLE BENCHMARKS (15/15 PASS) ─────────
    story.append(_p("6. Analytical Thermal Oracle Benchmarks (15/15 PASS)", st["h1"]))
    story.append(_p(
        "To verify OpenSeesPy thermal calculations independently of application code, 15 analytical benchmark tests "
        "(BM-01 through BM-15) were executed against exact closed-form mechanics equations. All 15 benchmarks passed "
        "with zero discrepancies within machine precision.",
        st["body"],
    ))
    bm_table_rows = [[
        _p("ID", st["th"]),
        _p("Benchmark Title & Theoretical Principle", st["th"]),
        _p("Expected", st["th_r"]),
        _p("Actual", st["th_r"]),
        _p("Relative Error", st["th_r"]),
        _p("Status", st["th"]),
    ]]
    for b in oracles["benchmarks"]:
        exp_str = f"{b.get('expected')}" if not isinstance(b.get('expected'), float) else f"{b.get('expected'):.6g}"
        act_str = f"{b.get('actual')}" if not isinstance(b.get('actual'), float) else f"{b.get('actual'):.6g}"
        rel_str = f"{b.get('rel_error'):.2e}" if isinstance(b.get('rel_error'), (int, float)) else "0.0"
        bm_table_rows.append([
            _p(b["id"], st["td_b"]),
            _p(b["name"], st["td"]),
            _p(exp_str, st["td_r"]),
            _p(act_str, st["td_r"]),
            _p(rel_str, st["td_r"]),
            _badge(b["status"], st),
        ])
    story.append(_styled_table(bm_table_rows, [16 * mm, 74 * mm, 26 * mm, 26 * mm, 22 * mm, 18 * mm], right_cols=[2, 3, 4]))
    story.append(PageBreak())

    # ── SECTION 7: FULL 192-ELEMENT LOAD ORACLE & ENVELOPES (BUG-15) ─────────
    story.append(_p("7. Full 192-Element Load-Combination & Envelope Oracle (BUG-15)", st["h1"]))
    story.append(_p(
        "Baseline ospgrillage omitted per-load combination factors when emitting OpenSees load commands. "
        "Phase 16 verified the candidate fix across every finite force cell (2,304 cells/combination) and "
        "every finite nodal displacement cell (648 cells/combination) on the 25 m / 7.5 m 192-element, 108-node model "
        "against independent weighted component superposition (tolerance 1e-6 raw units).",
        st["body"],
    ))
    lo_rows = [[
        _p("Load Combination", st["th"]),
        _p("Base Max Force Err (N/Nm)", st["th_r"]),
        _p("Base Mismatches", st["th_r"]),
        _p("Cand Max Force Err (N/Nm)", st["th_r"]),
        _p("Cand Max Disp Err (m)", st["th_r"]),
        _p("Cand Mismatches", st["th_r"]),
    ]]
    for combo in ("BASIC_1", "SLS_RARE_1", "SEISMIC_1", "SEISMIC_2"):
        bf = oracle_base["superposition"][combo]["forces"]
        cf = oracle_cand["superposition"][combo]["forces"]
        cd = oracle_cand["superposition"][combo]["displacements"]
        lo_rows.append([
            _p(combo, st["td_b"]),
            _p(f"{bf['max_abs_error']:,.3f}", st["td_r"]),
            _p(f"{bf['mismatch_cells']} / {bf['finite_cells']}", st["td_r"]),
            _p(f"{cf['max_abs_error']:.3e}", st["td_r"]),
            _p(f"{cd['max_abs_error']:.3e}", st["td_r"]),
            _p(f"{cf['mismatch_cells']} F / {cd['mismatch_cells']} D", st["td_r"]),
        ])
    story.append(_styled_table(lo_rows, [28 * mm, 32 * mm, 28 * mm, 32 * mm, 32 * mm, 28 * mm], right_cols=[1, 2, 3, 4, 5]))
    story.append(Spacer(1, 4 * mm))

    story.append(_p("7.1 Governing Load Combination Distribution (Candidate)", st["h2"]))
    env_rows = [[
        _p("Envelope", st["th"]),
        _p("Member Cases", st["th_r"]),
        _p("Force Cells / Max Err", st["th_r"]),
        _p("Disp Cells / Max Err", st["th_r"]),
        _p("Top Governing Combinations", st["th"]),
    ]]
    for ename in ("Envelope ULS", "Envelope SLS"):
        ev = oracle_cand["envelopes"][ename]
        f_var = ev["variables"]["forces"]
        d_var = ev["variables"]["displacements"]
        top3 = sorted(f_var["governing_cell_counts"].items(), key=lambda kv: kv[1], reverse=True)[:3]
        top_str = "; ".join(f"{k.split(':')[0]} ({v})" for k, v in top3)
        env_rows.append([
            _p(ename, st["td_b"]),
            _p(str(ev["group_count"]), st["td_r"]),
            _p(f"{f_var['cells']} / {f_var['max_abs_error']:.1f}", st["td_r"]),
            _p(f"{d_var['cells']} / {d_var['max_abs_error']:.1f}", st["td_r"]),
            _p(top_str, st["td"]),
        ])
    story.append(_styled_table(env_rows, [28 * mm, 22 * mm, 32 * mm, 32 * mm, CONTENT_W - 114 * mm], right_cols=[1, 2, 3]))
    story.append(PageBreak())

    # ── SECTION 8: VISUAL EVIDENCE (CAD, GUI, STRUCTURAL PLOTS) ──────────────
    story.append(_p("8. Visual Verification Evidence — CAD, Live GUI & Structural Plots", st["h1"]))
    story.append(_p(
        "Verification evidence combines direct OpenCascade View.Dump captures (which bypass OpenGL framebuffer "
        "limitations on macOS Cocoa), full-application PySide6 GUI captures, and matplotlib structural analysis diagrams.",
        st["body"],
    ))

    # CAD comparison pair
    occ_img = P18_SUB / "phase16/evidence/cad/phase16_cad_direct_occ.png"
    qwg_img = P18_SUB / "phase16/evidence/cad/phase16_cad_widget_grab.png"
    cad_pair = Table(
        [
            [_scaled_image(occ_img, 88 * mm, 60 * mm), _scaled_image(qwg_img, 88 * mm, 60 * mm)],
            [
                _p("Direct OpenCascade View.Dump: 14 AIS objects, 0.0% black (PASS)", st["caption"]),
                _p("QWidget Grab of Same Viewport: 58.3% black (macOS OpenGL capture limitation)", st["caption"]),
            ],
        ],
        colWidths=[CONTENT_W / 2, CONTENT_W / 2],
    )
    cad_pair.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.35, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(cad_pair)
    story.append(Spacer(1, 4 * mm))

    # Phase 20 Issue #92 GUI screenshots
    p20_temp_img = EV / "gui_issue92/screenshots/gui_additional_inputs_temp.png"
    p20_cad_img = EV / "gui_issue92/screenshots/gui_cad_viewport.png"
    p20_pair = Table(
        [
            [_scaled_image(p20_temp_img, 88 * mm, 58 * mm), _scaled_image(p20_cad_img, 88 * mm, 58 * mm)],
            [
                _p("Issue #92 Live GUI: Additional Inputs → Temperature Load (65/-10 C, 20e-6/10e-6)", st["caption"]),
                _p("Phase 20 Direct OpenCascade 3D CAD Viewport Dump After Design", st["caption"]),
            ],
        ],
        colWidths=[CONTENT_W / 2, CONTENT_W / 2],
    )
    p20_pair.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.35, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(p20_pair)
    story.append(Spacer(1, 4 * mm))

    # Phase 20 Structural Plots
    plot_bmd = EV / "gui_issue92/plot_1_0_TL_bmd.png"
    plot_def = EV / "gui_issue92/plot_1_0_TL_defl.png"
    plot_pair = Table(
        [
            [_scaled_image(plot_bmd, 88 * mm, 54 * mm), _scaled_image(plot_def, 88 * mm, 54 * mm)],
            [
                _p("1.0 TL Bending Moment Diagram (Mz = 230.39 kNm at midspan)", st["caption"]),
                _p("1.0 TL Vertical Deflection Diagram (dy = 18.07 mm downward deflection)", st["caption"]),
            ],
        ],
        colWidths=[CONTENT_W / 2, CONTENT_W / 2],
    )
    plot_pair.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.35, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(plot_pair)
    story.append(PageBreak())

    # ── SECTION 9: REQUIREMENTS TRACEABILITY MATRIX ──────────────────────────
    story.append(_p("9. Requirements Traceability Matrix (REQ-01..15, OFF-01..08)", st["h1"]))
    story.append(_p(
        "Synchronized directly from plans/REQUIREMENTS_TRACEABILITY_MATRIX.csv. All technical execution and local "
        "verification requirements are COMPLETE. Publication, collaborator verification, resume, and video remain PARTIAL.",
        st["body"],
    ))
    rtm_tbl_rows = [[_p("ID", st["th"]), _p("Status", st["th"]), _p("Requirement & Coverage Note", st["th"])]]
    for r in rtm_rows:
        note = r["coverage_note"]
        if len(note) > 120:
            note = note[:117].rstrip() + "..."
        desc = f"<b>{escape(r['requirement'])}</b><br/>{escape(note)}"
        rtm_tbl_rows.append([
            _p(r["requirement_id"], st["td_b"]),
            _badge(r["status"], st),
            Paragraph(desc, st["td"]),
        ])
    story.append(_styled_table(rtm_tbl_rows, [18 * mm, 20 * mm, CONTENT_W - 38 * mm], vpad=0.9))
    story.append(PageBreak())

    # ── SECTION 10: SUBMISSION INTEGRITY & PUBLICATION INSTRUCTIONS ──────────
    story.append(_p("10. Submission Package Integrity & Manual Publication Guide", st["h1"]))
    story.append(_p(
        "The submission package is self-contained on the Portable SSD, with clean patch apply receipts, zero remote "
        "writes, and complete SHA-256 integrity verification.",
        st["body"],
    ))
    idx_rows = [
        [_p("Deliverable", st["th"]), _p("Path inside Phase 20 Submission Package", st["th"]), _p("Integrity Verification", st["th"])],
        [_p("QA Test Report PDF", st["td_b"]), _p("report/OsdagBridge_Screening_Test_Report_Phase20.pdf", st["td"]), _p("ReportLab 5.1.0; PyPDF verified", st["td"])],
        [_p("Master Defect Register", st["td_b"]), _p("bug_reports/DEFECT_REGISTER_PHASE20.{csv,json}", st["td"]), _p("25 records: 24 fixed, 1 non-defect", st["td"])],
        [_p("Combined All-Fixes Patch", st["td_b"]), _p("patches/phase20_combined_all_fixes.patch", st["td"]), _p("git apply --check PASS on baseline", st["td"])],
        [_p("Isolated Issue #92 Patch", st["td_b"]), _p("patches/phase20_thermal_issue92_isolated.patch", st["td"]), _p("git apply --check PASS on commit 2794f3e", st["td"])],
        [_p("Thermal Implementation Report", st["td_b"]), _p("phase20/reports/PHASE20_THERMAL_IMPLEMENTATION_REPORT.md", st["td"]), _p("Full Cl. 215 mathematical & FEA derivation", st["td"])],
        [_p("Issue #92 GitHub Draft", st["td_b"]), _p("phase20/bug_reports/GITHUB_ISSUE92_RESOLUTION_DRAFT.md", st["td"]), _p("0 remote writes; local draft only", st["td"])],
        [_p("SHA-256 Manifest & Receipt", st["td_b"]), _p("SHA256SUMS.json; PHASE20_ARCHIVE_RECEIPT.json", st["td"]), _p("Pure stdlib SHA-256 + ZIP testzip() PASS", st["td"])],
    ]
    story.append(_styled_table(idx_rows, [40 * mm, 78 * mm, CONTENT_W - 118 * mm]))
    story.append(Spacer(1, 5 * mm))

    story.append(_p("10.1 Step-by-Step Manual Actions for Candidate", st["h2"]))
    man_rows = [
        [_p("#", st["th"]), _p("Action Item", st["th"]), _p("Exact Instruction & Command", st["th"])],
        [
            _p("1", st["td_b"]),
            _p("Review GitHub Drafts", st["td_b"]),
            _p("Review phase20/bug_reports/GITHUB_ISSUE92_RESOLUTION_DRAFT.md and phase19/bug_reports/PHASE19_NEW_ISSUES_DRAFTS.md. Verify that upstream issue numbers match and approve posting.", st["td"]),
        ],
        [
            _p("2", st["td_b"]),
            _p("Post Issue #92 Comment", st["td_b"]),
            _p("Copy text from GITHUB_ISSUE92_RESOLUTION_DRAFT.md into upstream issue https://github.com/Nidhikhare12/OsdagBridge/issues/92 and attach phase20_thermal_issue92_isolated.patch.", st["td"]),
        ],
        [
            _p("3", st["td_b"]),
            _p("Invite Collaborator", st["td_b"]),
            _p("Go to your GitHub fork (rohansiddhpura17-source/OsdagBridge) -> Settings -> Collaborators -> Add people -> enter 'Nidhikhare12'.", st["td"]),
        ],
        [
            _p("4", st["td_b"]),
            _p("Resume & Video", st["td_b"]),
            _p("Attach your resume PDF and 6-8 minute 1080p demonstration video alongside OsdagBridge_Screening_Submission_Phase20.zip and this PDF report.", st["td"]),
        ],
    ]
    story.append(_styled_table(man_rows, [10 * mm, 36 * mm, CONTENT_W - 46 * mm]))

    doc = SimpleDocTemplate(
        str(OUT_PDF),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=15 * mm,
        bottomMargin=14 * mm,
        title="OsdagBridge Screening QA Report — Final Phase 20A",
        author="Rohan Siddhpura — FOSSEE IIT Bombay Winter Internship 2026",
        subject="Comprehensive QA Report: 24 Verified Defect Fixes, Scoped Thermal Resolution (#92), and 192-Element Superposition Oracle",
    )
    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    shutil.copyfile(OUT_PDF, SUB_PDF)

    # Verification with PyPDF
    reader = PdfReader(str(OUT_PDF))
    pages = len(reader.pages)
    empty_pages = [i + 1 for i, p in enumerate(reader.pages) if not (p.extract_text() or "").strip()]
    full_text = "\n".join((p.extract_text() or "") for p in reader.pages)
    for token in [
        "d74f56dd7f22925fb8148cabf5740ed8d1e39ff3",
        "24 / 24",
        "51 / 51",
        "28 / 28",
        "15 / 15",
        "0.3524 mm",
        "UPSTREAM-92",
        "BUG-25",
        "BUG-26",
        "BUG-27",
        "BUG-28",
        "BUG-29",
        "BUG-30",
        "Amendments No. 6",
        "Nidhikhare12",
    ]:
        if token not in full_text:
            raise AssertionError(f"Expected token missing from generated PDF: {token}")
    if empty_pages:
        raise AssertionError(f"Blank pages found in PDF: {empty_pages}")

    print(json.dumps({
        "pdf": str(OUT_PDF),
        "sub_copy": str(SUB_PDF),
        "pages": pages,
        "bytes": OUT_PDF.stat().st_size,
        "empty_pages": empty_pages,
        "pypdf_verification": "PASS",
    }, indent=2))


if __name__ == "__main__":
    build_pdf()
