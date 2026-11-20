#!/usr/bin/env python3
"""
Phase 16: Combined End-to-End Live GUI Integration Revalidation of fixes BUG-01..BUG-13
(BUG-01 through BUG-13) on the candidate worktree (/Volumes/OsdagBridgeEnv/worktrees/phase89-fixes).

Preserves the corrected crack-width failure (wk_bot ~ 0.3524 mm > 0.30 mm on M40 baseline)
as engineering evidence — never suppressed.
"""
from __future__ import annotations

import copy
import json
import os
import pickle
import re
import subprocess
import sys
import time
import traceback
from pathlib import Path

CANDIDATE_SRC = "/Volumes/PortableSSD/OsdagBridge-screening-2026/phase20/candidate/src"
if CANDIDATE_SRC not in sys.path:
    sys.path.insert(0, CANDIDATE_SRC)
os.environ["PYTHONPATH"] = CANDIDATE_SRC
os.environ["PATH"] = "/Volumes/PortableSSD/OsdagBridge-screening-2026/phase20/tests/bin:" + os.environ.get("PATH", "")

OUT_DIR = Path("/Volumes/PortableSSD/OsdagBridge-screening-2026/phase20/evidence/gui_17fix")
OUT_DIR.mkdir(parents=True, exist_ok=True)
SHOT_DIR = OUT_DIR / "screenshots"
SHOT_DIR.mkdir(parents=True, exist_ok=True)

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication, QComboBox, QDialog, QFileDialog, QLabel, QLineEdit, QWidget

from osdagbridge.core.bridge_types.plate_girder import plot_generator
from osdagbridge.core.bridge_types.plate_girder.plategirderbridge import PlateGirderBridge
from osdagbridge.core.utils.common import (
    KEY_CARRIAGEWAY_WIDTH,
    KEY_CROSS_BRACING,
    KEY_DECK_CONCRETE_GRADE_BASIC,
    KEY_END_DIAPHRAGM,
    KEY_GIRDER,
    KEY_MATERIAL_CROSS_BRACING_FU,
    KEY_MATERIAL_CROSS_BRACING_FY,
    KEY_MATERIAL_DECK_DENSITY,
    KEY_MATERIAL_DECK_ECM,
    KEY_MATERIAL_DECK_FCK,
    KEY_MATERIAL_DECK_FCTM,
    KEY_MATERIAL_DECK_THERMAL,
    KEY_MATERIAL_END_DIAPHRAGM_FU,
    KEY_MATERIAL_END_DIAPHRAGM_FY,
    KEY_MATERIAL_GIRDER_DENSITY,
    KEY_MATERIAL_GIRDER_E,
    KEY_MATERIAL_GIRDER_FU,
    KEY_MATERIAL_GIRDER_FY,
    KEY_MATERIAL_GIRDER_G,
    KEY_MATERIAL_GIRDER_POISSON,
    KEY_MATERIAL_GIRDER_THERMAL,
    KEY_OUTPUT_DOCK_MEMBER_ID,
    KEY_PROJECT_LOCATION,
    KEY_SPAN,
    KEY_TS_NO_OF_GIRDERS,
)
from osdagbridge.desktop.ui.dialogs import custom_messagebox
from osdagbridge.desktop.ui.dialogs.generate_results_values_builder import (
    resolve_material_properties_concrete,
    resolve_material_properties_steel,
)
from osdagbridge.desktop.ui.dialogs.steel_design import SteelDesign
from osdagbridge.desktop.ui.template_page import CustomWindow

POPUP_LOG: list[dict] = []


def pump(ms: int = 120):
    deadline = time.time() + ms / 1000.0
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.01)


def install_popup_recorder():
    def _recorded_exec(self):
        texts = [
            lbl.text().strip()
            for lbl in self.findChildren(QLabel)
            if lbl.text() and lbl.text().strip()
        ]
        POPUP_LOG.append({"title": self.windowTitle(), "text": " | ".join(texts)})
        self.accept()
        btns = getattr(self, "buttons", None)
        if isinstance(btns, (list, tuple)) and btns:
            return btns[0]
        return "Continue"
    custom_messagebox.CustomMessageBox.exec = _recorded_exec


def unlock_if_locked(win: CustomWindow):
    if getattr(win.input_dock, "is_locked", False):
        win.input_dock.lock_btn.click()
        pump(200)
        assert not win.input_dock.is_locked, "InputDock remained locked after clicking lock_btn"


def wait_for_design(win: CustomWindow, timeout_s: float = 240.0) -> float:
    t0 = time.time()
    while getattr(win, "_design_running", False):
        QCoreApplication.processEvents()
        if time.time() - t0 > timeout_s:
            raise TimeoutError("Design timed out")
        time.sleep(0.05)
    pump(400)
    return round(time.time() - t0, 2)


def measure_plot_sw_vy(backend: PlateGirderBridge) -> dict[str, float]:
    """Compute exact 3D plot SFD SW peak |Vy| per girder using plot_generator's exact logic."""
    ds_all = backend.get_results_dataset()
    nodes, members = backend.get_nodes_members()
    edge_dist = backend.get_edge_dist()
    # Find SW loadcase name
    all_lcs = [str(lc) for lc in ds_all.coords["Loadcase"].values]
    sw_lc = next((lc for lc in all_lcs if lc.strip().lower() in ("sw", "girder self weight", "self weight")), None)
    if sw_lc is None:
        sw_lc = next((lc for lc in all_lcs if "self weight" in lc.lower() or lc.strip() == "SW"), all_lcs[0])
    ds_sw = ds_all.sel(Loadcase=sw_lc)
    girders = list(plot_generator._find_girders(nodes, members).items())
    n_g = len(girders)
    peaks = {}
    for i, (_z, elems) in enumerate(girders):
        is_eb = edge_dist > 0 and (i == 0 or i == n_g - 1)
        if is_eb:
            continue
        g_name = f"G{i}" if edge_dist > 0 else f"G{i + 1}"
        _xs, _ys, _zs, vals, _nids = plot_generator._build_polyline(
            elems, members, nodes, "Vy_i", "Vy_j", ds_sw
        )
        peaks[g_name] = round(float(max(abs(float(v)) for v in vals)), 3)
    return {"sw_loadcase": sw_lc, "plot_sw_vy_peaks_kN": peaks}


def dump_cad_nonblank(win: CustomWindow, path: Path) -> dict:
    """Dump OCC 3D viewport directly without any view toggle (verifies BUG-10)."""
    from PIL import Image
    import numpy as np

    win.cad_3d_widget.viewer.display.View.Dump(str(path))
    img = Image.open(path).convert("RGB")
    arr = np.asarray(img)
    w, h = img.size
    # Non-white pixel fraction
    non_white = float(np.mean(np.any(arr < 245, axis=-1)))
    return {
        "path": str(path),
        "width": w,
        "height": h,
        "non_white_fraction": round(non_white, 4),
        "non_blank_full_size": (w >= 400 and h >= 250 and non_white > 0.01),
    }


DELHI_LOC = {
    "state": "Delhi",
    "district": "New Delhi",
    "weather_data": {"zone": "IV", "wind_speed": 47, "max_temp": 45.0, "min_temp": 4.0},
}


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    install_popup_recorder()

    repo_file = str(Path(sys.modules[PlateGirderBridge.__module__].__file__).resolve())
    assert "/phase20/candidate/" in repo_file, (
        f"Must run against candidate worktree! Got {repo_file}"
    )

    report = {
        "repo_file": repo_file,
        "assertions": {},
        "runs": {},
    }

    win = CustomWindow(title="Phase14 Candidate 13-Fix Verification", backend=PlateGirderBridge)
    win.resize(1380, 860)
    win.show()
    pump(400)

    try:
        # =====================================================================
        # RUN 1: 3-Girder Baseline (30 m) — BUG-01, BUG-02, BUG-10, BUG-13
        # =====================================================================
        print("\n=== RUN 1: 3-Girder Baseline (30 m) ===")
        win.input_dock._update_input_dict(KEY_PROJECT_LOCATION, copy.deepcopy(DELHI_LOC))
        span_w = win.input_dock._w(KEY_SPAN)
        cw_w = win.input_dock._w(KEY_CARRIAGEWAY_WIDTH)
        span_w.setText("30"); span_w.editingFinished.emit()
        cw_w.setText("4.25"); cw_w.editingFinished.emit()
        pump(150)

        POPUP_LOG.clear()
        win.input_dock.design_btn.click()
        pump(150)
        t1 = wait_for_design(win)

        out1 = dict(win.backend.output_dict)
        mp1 = win.backend._build_material_props()
        run1_steel_rho_knm3 = float(mp1.steel_prop.rho) / 1000.0 if float(mp1.steel_prop.rho) > 500.0 else float(mp1.steel_prop.rho)
        dr1 = out1.get("design_results", {}) or {}
        pg1 = dr1.get("per_girder", {}) or {}
        dd1 = out1.get("deck_design_results", {}) or {}
        drv1 = out1.get("deck_report_values", {}) or {}
        rh1 = win.backend.get_result_handler()
        gmap1, _ = rh1.build_girders(verbose=False)
        plot1 = measure_plot_sw_vy(win.backend)
        sw_lc1 = plot1["sw_loadcase"]

        # Compare Plot vs per_girder["per_lc"][sw_lc]["Vu_kN"] vs _load_effects_cache
        cache1 = getattr(win.backend, "_load_effects_cache", {}) or {}
        comp1 = {}
        max_diff_3g = 0.0
        for g in ("G1", "G2", "G3"):
            p_vy = plot1["plot_sw_vy_peaks_kN"].get(g)
            # per_lc SW key might be "SW" or sw_lc1
            per_lc_g = (pg1.get(g) or {}).get("per_lc") or {}
            pg_lc_key = sw_lc1 if sw_lc1 in per_lc_g else next((k for k in per_lc_g if "sw" in k.lower() or "self weight" in k.lower()), None)
            pg_vu = (per_lc_g.get(pg_lc_key) or {}).get("Vu_kN") if pg_lc_key else None
            c_vy = (cache1.get(g) or {}).get(sw_lc1, {}).get("Vy_max")
            diff_pg = abs(float(p_vy) - float(pg_vu)) if (p_vy is not None and pg_vu is not None) else 999.0
            diff_c = abs(float(p_vy) - float(c_vy)) if (p_vy is not None and c_vy is not None) else 999.0
            max_diff_3g = max(max_diff_3g, diff_pg, diff_c)
            comp1[g] = {
                "plot_Vy_kN": p_vy,
                "per_girder_Vu_kN": pg_vu,
                "cache_Vy_max_kN": c_vy,
                "diff_plot_vs_per_girder": round(diff_pg, 4),
                "diff_plot_vs_cache": round(diff_c, 4),
            }

        # Check Output Dock member combo + DCR selection for G1..G3 + SteelDesign member combo
        mem_combo = win.output_dock._w(KEY_OUTPUT_DOCK_MEMBER_ID)
        dock_members_3g = [mem_combo.itemText(i) for i in range(mem_combo.count())] if mem_combo else []
        dcr_g1_eng = win.backend.get_dcr_engine_for_selection("G1", sw_lc1)
        dcr_g1_vu = round(float(dcr_g1_eng.demand.Vu_kN), 3) if dcr_g1_eng else None

        # Instantiate SteelDesign dialog to verify its member_combo populates G1..G3 cleanly
        sd_dlg = SteelDesign(parent=win)
        pump(150)
        sd_items_3g = [
            {"text": sd_dlg.member_combo.itemText(i), "data": sd_dlg.member_combo.itemData(i)}
            for i in range(sd_dlg.member_combo.count())
        ]
        sd_dlg.close()

        # Check Excel Concrete row (BUG-02)
        conc_tbl1 = resolve_material_properties_concrete(dict(win.input_dict), bridge=win.backend)
        cad1 = dump_cad_nonblank(win, SHOT_DIR / "cand_run1_3g_cad.png")
        win.grab().save(str(SHOT_DIR / "cand_run1_3g_window.png"))

        # Save pickle of RUN-01 candidate output for independent numerical verification!
        run1_snap = {
            "n_girders": dr1.get("n_girders"),
            "per_girder_keys": list(pg1.keys()),
            "build_girders_keys": list(gmap1.keys()),
            "edge_dist": win.backend.get_edge_dist(),
            "plot_vs_per_girder_3g": comp1,
            "deck_design_results": dd1,
            "deck_report_values": drv1,
            "concrete_excel_table": conc_tbl1,
        }
        (OUT_DIR / "cand_run1_3g_snapshot.pkl").write_bytes(pickle.dumps(run1_snap))

        # Preserve corrected crack-width failure as engineering evidence!
        wk_bot_val = dd1.get("wk_bot") if dd1.get("wk_bot") is not None else drv1.get("deck.report.wk_bot")
        report["runs"]["RUN1_3G"] = {
            "elapsed_s": t1,
            "edge_dist": win.backend.get_edge_dist(),
            "rh_edge_dist": rh1.edge_dist,
            "build_girders_keys": list(gmap1.keys()),
            "design_results_n_girders": dr1.get("n_girders"),
            "per_girder_keys": list(pg1.keys()),
            "output_dock_members": dock_members_3g,
            "steel_design_dialog_members": sd_items_3g,
            "dcr_selection_G1_SW_Vu_kN": dcr_g1_vu,
            "plot_vs_dict_comparison": comp1,
            "max_diff_kN": round(max_diff_3g, 4),
            "deck_Ecm_MPa": dr1.get("Ecm_MPa"),
            "deck_wk_bot_mm_preserved": wk_bot_val,
            "deck_overall_status": dd1.get("overall_status"),
            "concrete_excel_rows": conc_tbl1.get("rows") if conc_tbl1 else None,
            "cad_dump": cad1,
        }
        report["assertions"]["BUG13_3G_mapping_and_alignment"] = (
            list(gmap1.keys()) == ["EB1", "G1", "G2", "G3", "EB2"]
            and list(pg1.keys()) == ["G1", "G2", "G3"]
            and dr1.get("n_girders") == 3
            and dock_members_3g == ["G1", "G2", "G3"]
            and [x["data"] for x in sd_items_3g] == ["G1", "G2", "G3"]
            and max_diff_3g < 0.01
            and dcr_g1_vu is not None and abs(dcr_g1_vu - comp1["G1"]["plot_Vy_kN"]) < 0.02
        )
        report["assertions"]["BUG01_Ecm_MPa_and_preserved_wk_failure"] = (
            float(dr1.get("Ecm_MPa") or 0) > 30000.0
            and wk_bot_val is not None and float(wk_bot_val) > 0.30
        )
        report["assertions"]["BUG02_concrete_excel_units"] = (
            conc_tbl1 is not None and any("33000" in str(r) or "33,000" in str(r) for r in (conc_tbl1.get("rows") or []))
        )
        report["assertions"]["BUG10_CAD_nonblank_run1"] = bool(cad1["non_blank_full_size"])

        # =====================================================================
        # RUN 2 & 3: Optimized 30 -> 32 -> 30 m (BUG-08 + BUG-10)
        # =====================================================================
        print("\n=== RUN 2 & 3: Optimized 30 -> 32 -> 30 m ===")
        unlock_if_locked(win)
        span_w.setText("32"); span_w.editingFinished.emit(); pump(150)
        win.input_dock.design_btn.click(); pump(150)
        t2 = wait_for_design(win)
        out2 = dict(win.backend.output_dict)
        cad2 = dump_cad_nonblank(win, SHOT_DIR / "cand_run2_32m_cad.png")

        unlock_if_locked(win)
        span_w.setText("30"); span_w.editingFinished.emit(); pump(150)
        win.input_dock.design_btn.click(); pump(150)
        t3 = wait_for_design(win)
        out3 = dict(win.backend.output_dict)
        cad3 = dump_cad_nonblank(win, SHOT_DIR / "cand_run3_30m_return_cad.png")

        # Compare key structural outputs of Run 3 vs Run 1 (must match cleanly — zero stale 32 m state)
        dr3 = out3.get("design_results", {}) or {}
        mu1 = float(dr1.get("Mu_kNm") or 0)
        mu2 = float((out2.get("design_results") or {}).get("Mu_kNm") or 0)
        mu3 = float(dr3.get("Mu_kNm") or 0)
        report["runs"]["RUN2_3_30_32_30"] = {
            "t_32m_s": t2, "t_30m_return_s": t3,
            "Mu_30m_1": mu1, "Mu_32m": mu2, "Mu_30m_return": mu3,
            "span_32m": (out2.get("design_results") or {}).get("span_m"),
            "span_30m_return": dr3.get("span_m"),
            "cad2": cad2, "cad3": cad3,
        }
        report["assertions"]["BUG08_30_32_30_zero_stale"] = (
            mu2 > mu1 and abs(mu3 - mu1) < 1e-3 and float(dr3.get("span_m") or 0) == 30.0
        )
        report["assertions"]["BUG10_CAD_nonblank_32_30"] = bool(cad2["non_blank_full_size"] and cad3["non_blank_full_size"])

        # =====================================================================
        # RUN 4 & 5: 3 -> 4 -> 3 Girders + Tectonic LaTeX PDF (BUG-09, BUG-11, BUG-13)
        # =====================================================================
        print("\n=== RUN 4 & 5: 3 -> 4 -> 3 Girders + 4G Tectonic PDF ===")
        unlock_if_locked(win)
        win._show_additional_inputs(); pump(200)
        dlg = win._get_additional_inputs()
        ng_w = dlg.findChild(QWidget, KEY_TS_NO_OF_GIRDERS)
        ng_w.setText("4"); ng_w.editingFinished.emit(); pump(150)
        dlg.save_button.click(); pump(200)

        win.input_dock.design_btn.click(); pump(150)
        t4 = wait_for_design(win)
        out4 = dict(win.backend.output_dict)
        dr4 = out4.get("design_results", {}) or {}
        pg4 = dr4.get("per_girder", {}) or {}
        rh4 = win.backend.get_result_handler()
        gmap4, _ = rh4.build_girders(verbose=False)
        plot4 = measure_plot_sw_vy(win.backend)
        sw_lc4 = plot4["sw_loadcase"]
        cache4 = getattr(win.backend, "_load_effects_cache", {}) or {}

        comp4 = {}
        max_diff_4g = 0.0
        for g in ("G1", "G2", "G3", "G4"):
            p_vy = plot4["plot_sw_vy_peaks_kN"].get(g)
            per_lc_g = (pg4.get(g) or {}).get("per_lc") or {}
            pg_lc_key = sw_lc4 if sw_lc4 in per_lc_g else next((k for k in per_lc_g if "sw" in k.lower() or "self weight" in k.lower()), None)
            pg_vu = (per_lc_g.get(pg_lc_key) or {}).get("Vu_kN") if pg_lc_key else None
            c_vy = (cache4.get(g) or {}).get(sw_lc4, {}).get("Vy_max")
            diff_pg = abs(float(p_vy) - float(pg_vu)) if (p_vy is not None and pg_vu is not None) else 999.0
            diff_c = abs(float(p_vy) - float(c_vy)) if (p_vy is not None and c_vy is not None) else 999.0
            max_diff_4g = max(max_diff_4g, diff_pg, diff_c)
            comp4[g] = {
                "plot_Vy_kN": p_vy,
                "per_girder_Vu_kN": pg_vu,
                "cache_Vy_max_kN": c_vy,
                "diff_plot_vs_per_girder": round(diff_pg, 4),
                "diff_plot_vs_cache": round(diff_c, 4),
            }

        dock_members_4g = [mem_combo.itemText(i) for i in range(mem_combo.count())] if mem_combo else []
        sd_dlg4 = SteelDesign(parent=win)
        pump(150)
        sd_items_4g = [
            {"text": sd_dlg4.member_combo.itemText(i), "data": sd_dlg4.member_combo.itemData(i)}
            for i in range(sd_dlg4.member_combo.count())
        ]
        sd_dlg4.close()

        # Generate full 4-girder LaTeX report & compile with Tectonic wrapper!
        rep_dir = OUT_DIR / "report_4g_phase14"
        rep_dir.mkdir(parents=True, exist_ok=True)
        pdf_out_path = rep_dir / "cand_phase14_4g_report.pdf"
        os.environ["PATH"] = "/Volumes/PortableSSD/OsdagBridge-screening-2026/phase20/tests/bin:" + os.environ.get("PATH", "")
        os.environ["REPORT_EVIDENCE"] = str(rep_dir)

        from osdagbridge.core.reports.report_generator import (
            ReportMetadata,
            ReportOptions,
            ReportRequest,
        )
        req = ReportRequest(
            metadata=ReportMetadata(
                project_name="Phase 14 Candidate 4-Girder Report Verification",
                project_location="New Delhi",
                designer="Screening QA Verification",
                client="FOSSEE IIT Bombay",
                company="OsdagBridge Screening",
            ),
            options=ReportOptions(
                sections=["loads", "analysis", "design_checks", "drawings"],
                include_figures=True,
                include_toc=True,
                include_pdf=True,
            ),
            output_dir=str(rep_dir),
            file_stem="cand_phase14_4g_report",
        )
        rep_result = win.backend.generate_design_report(req, cad_generator=None)
        pdf_exists = pdf_out_path.exists() and pdf_out_path.stat().st_size > 10000
        pdf_pages = 0
        has_g1_g4 = False
        has_spurious_g5_g6 = False
        if pdf_exists:
            pinfo = subprocess.check_output(["/opt/homebrew/bin/pdfinfo", str(pdf_out_path)], text=True)
            m_pg = re.search(r"Pages:\s+(\d+)", pinfo)
            pdf_pages = int(m_pg.group(1)) if m_pg else 0
            ptxt = subprocess.check_output(["/opt/homebrew/bin/pdftotext", str(pdf_out_path), "-"], text=True)
            has_g1_g4 = all(tok in ptxt for tok in ("G1", "G2", "G3", "G4"))
            # Check Table 5.13 / girder rows for any spurious G5/G6
            has_spurious_g5_g6 = bool(re.search(r"\bG[56]\b", ptxt))

        # Save 4G snapshot pickle for independent numerical verification
        (OUT_DIR / "cand_run4_4g_snapshot.pkl").write_bytes(pickle.dumps({
            "n_girders": dr4.get("n_girders"),
            "per_girder_keys": list(pg4.keys()),
            "build_girders_keys": list(gmap4.keys()),
            "edge_dist": win.backend.get_edge_dist(),
            "plot_vs_per_girder_4g": comp4,
        }))

        # Return 4 -> 3 girders (verify BUG-09 stale G4 cleanup + BUG-13 return to G1..G3)
        unlock_if_locked(win)
        win._show_additional_inputs(); pump(200)
        dlg = win._get_additional_inputs()
        ng_w = dlg.findChild(QWidget, KEY_TS_NO_OF_GIRDERS)
        ng_w.setText("3"); ng_w.editingFinished.emit(); pump(150)
        dlg.save_button.click(); pump(200)

        stale_g4_in_input = [k for k in win.input_dict if ".G4" in k or "G3G4" in k]
        win.input_dock.design_btn.click(); pump(150)
        t5 = wait_for_design(win)
        out5 = dict(win.backend.output_dict)
        dr5 = out5.get("design_results", {}) or {}
        pg5 = dr5.get("per_girder", {}) or {}
        stale_g4_in_output = [k for k in out5 if ".G4" in k or "G3G4" in k]

        report["runs"]["RUN4_5_4G_AND_RETURN"] = {
            "t_4g_s": t4, "t_3g_return_s": t5,
            "build_girders_4g": list(gmap4.keys()),
            "design_results_n_girders_4g": dr4.get("n_girders"),
            "per_girder_keys_4g": list(pg4.keys()),
            "output_dock_members_4g": dock_members_4g,
            "steel_design_dialog_members_4g": sd_items_4g,
            "plot_vs_dict_4g": comp4,
            "max_diff_4g_kN": round(max_diff_4g, 4),
            "report_4g": {
                "result": str(rep_result),
                "pdf_path": str(pdf_out_path),
                "pdf_exists": pdf_exists,
                "pdf_size_bytes": pdf_out_path.stat().st_size if pdf_exists else 0,
                "pdf_pages": pdf_pages,
                "text_has_G1_to_G4": has_g1_g4,
                "text_has_spurious_G5_or_G6": has_spurious_g5_g6,
            },
            "return_3g": {
                "stale_G4_in_input_dict": stale_g4_in_input,
                "stale_G4_in_output_dict": stale_g4_in_output,
                "design_results_n_girders": dr5.get("n_girders"),
                "per_girder_keys": list(pg5.keys()),
            },
        }
        report["assertions"]["BUG13_4G_mapping_and_alignment"] = (
            list(gmap4.keys()) == ["EB1", "G1", "G2", "G3", "G4", "EB2"]
            and list(pg4.keys()) == ["G1", "G2", "G3", "G4"]
            and dr4.get("n_girders") == 4
            and dock_members_4g == ["G1", "G2", "G3", "G4"]
            and [x["data"] for x in sd_items_4g] == ["G1", "G2", "G3", "G4"]
            and max_diff_4g < 0.01
        )
        report["assertions"]["BUG11_tectonic_4g_pdf_clean"] = (
            pdf_exists and pdf_pages >= 40 and has_g1_g4 and not has_spurious_g5_g6
        )
        report["assertions"]["BUG09_4G_to_3G_zero_stale_keys"] = (
            len(stale_g4_in_input) == 0
            and len(stale_g4_in_output) == 0
            and dr5.get("n_girders") == 3
            and list(pg5.keys()) == ["G1", "G2", "G3"]
        )

        # =====================================================================
        # RUN 6: Custom Materials (BUG-03, BUG-04, BUG-05, BUG-06, BUG-02)
        # =====================================================================
        print("\n=== RUN 6: Custom Steel, Deck, CB, ED Materials ===")
        unlock_if_locked(win)
        # Baseline SW & DD reference from Run 1
        sw1_g1 = comp1["G1"]["plot_Vy_kN"]
        dd_lc1 = next((k for k in (cache1.get("G1") or {}) if "deck" in k.lower() or k.strip() == "DD"), None)
        dd1_g1 = (cache1.get("G1") or {}).get(dd_lc1, {}).get("Vy_max") if dd_lc1 else None

        # Inject custom materials via InputDock dict update + material combos (matching OSI load)
        custom_osi = OUT_DIR / "custom_all_materials.osi"
        import yaml
        osi_payload = copy.deepcopy(dict(win.input_dict))
        osi_payload[KEY_GIRDER] = "custom_steel_355_495"
        osi_payload[KEY_MATERIAL_GIRDER_DENSITY] = "80.0"
        osi_payload[KEY_MATERIAL_GIRDER_FY] = "355.0"
        osi_payload[KEY_MATERIAL_GIRDER_FU] = "495.0"
        osi_payload[KEY_MATERIAL_GIRDER_E] = "200.0"
        osi_payload[KEY_MATERIAL_GIRDER_G] = "76.923"
        osi_payload[KEY_MATERIAL_GIRDER_POISSON] = "0.30"
        osi_payload[KEY_MATERIAL_GIRDER_THERMAL] = "11.7"
        osi_payload[KEY_DECK_CONCRETE_GRADE_BASIC] = "custom_concrete_40"
        osi_payload[KEY_MATERIAL_DECK_DENSITY] = "24.0"
        osi_payload[KEY_MATERIAL_DECK_FCK] = "40.0"
        osi_payload[KEY_MATERIAL_DECK_FCTM] = "3.5"
        osi_payload[KEY_MATERIAL_DECK_ECM] = "34.0"
        osi_payload[KEY_MATERIAL_DECK_THERMAL] = "10.0"
        osi_payload[KEY_CROSS_BRACING] = "custom_steel_460_600"
        osi_payload[KEY_MATERIAL_CROSS_BRACING_FY] = "460.0"
        osi_payload[KEY_MATERIAL_CROSS_BRACING_FU] = "600.0"
        osi_payload[KEY_END_DIAPHRAGM] = "custom_steel_410_540"
        osi_payload[KEY_MATERIAL_END_DIAPHRAGM_FY] = "410.0"
        osi_payload[KEY_MATERIAL_END_DIAPHRAGM_FU] = "540.0"
        custom_osi.write_text(yaml.safe_dump(osi_payload, sort_keys=False))

        # Load via REAL GUI loadOSI_inputs() (also tests BUG-12 custom OSI priming!)
        orig_get_open = QFileDialog.getOpenFileName
        QFileDialog.getOpenFileName = lambda *a, **kw: (str(custom_osi), "OSI Files (*.osi)")
        POPUP_LOG.clear()
        win.loadOSI_inputs()
        pump(200)
        # Explicitly trigger priming (called at start of design) and verify 12/12 custom keys preserved
        win.input_dock._prime_material_inputs()
        pump(150)

        primed_check = {
            KEY_MATERIAL_GIRDER_DENSITY: str(win.input_dict.get(KEY_MATERIAL_GIRDER_DENSITY)),
            KEY_MATERIAL_GIRDER_FY: str(win.input_dict.get(KEY_MATERIAL_GIRDER_FY)),
            KEY_MATERIAL_GIRDER_FU: str(win.input_dict.get(KEY_MATERIAL_GIRDER_FU)),
            KEY_MATERIAL_GIRDER_E: str(win.input_dict.get(KEY_MATERIAL_GIRDER_E)),
            KEY_MATERIAL_GIRDER_G: str(win.input_dict.get(KEY_MATERIAL_GIRDER_G)),
            KEY_MATERIAL_GIRDER_POISSON: str(win.input_dict.get(KEY_MATERIAL_GIRDER_POISSON)),
            KEY_MATERIAL_GIRDER_THERMAL: str(win.input_dict.get(KEY_MATERIAL_GIRDER_THERMAL)),
            KEY_MATERIAL_DECK_DENSITY: str(win.input_dict.get(KEY_MATERIAL_DECK_DENSITY)),
            KEY_MATERIAL_DECK_FCK: str(win.input_dict.get(KEY_MATERIAL_DECK_FCK)),
            KEY_MATERIAL_DECK_FCTM: str(win.input_dict.get(KEY_MATERIAL_DECK_FCTM)),
            KEY_MATERIAL_DECK_ECM: str(win.input_dict.get(KEY_MATERIAL_DECK_ECM)),
            KEY_MATERIAL_DECK_THERMAL: str(win.input_dict.get(KEY_MATERIAL_DECK_THERMAL)),
        }
        expected_primed = {
            KEY_MATERIAL_GIRDER_DENSITY: "80.0",
            KEY_MATERIAL_GIRDER_FY: "355.0",
            KEY_MATERIAL_GIRDER_FU: "495.0",
            KEY_MATERIAL_GIRDER_E: "200.0",
            KEY_MATERIAL_GIRDER_G: "76.923",
            KEY_MATERIAL_GIRDER_POISSON: "0.30",
            KEY_MATERIAL_GIRDER_THERMAL: "11.7",
            KEY_MATERIAL_DECK_DENSITY: "24.0",
            KEY_MATERIAL_DECK_FCK: "40.0",
            KEY_MATERIAL_DECK_FCTM: "3.5",
            KEY_MATERIAL_DECK_ECM: "34.0",
            KEY_MATERIAL_DECK_THERMAL: "10.0",
        }
        preserved_count = sum(1 for k, v in expected_primed.items() if primed_check.get(k) == v)

        # Run full design with custom materials
        win.input_dock.design_btn.click(); pump(150)
        t6 = wait_for_design(win)
        out6 = dict(win.backend.output_dict)
        plot6 = measure_plot_sw_vy(win.backend)
        cache6 = getattr(win.backend, "_load_effects_cache", {}) or {}
        sw6_g1 = plot6["plot_sw_vy_peaks_kN"].get("G1")
        dd6_g1 = (cache6.get("G1") or {}).get(dd_lc1, {}).get("Vy_max") if dd_lc1 else None

        sw_ratio = round(sw6_g1 / sw1_g1, 5) if (sw1_g1 and sw6_g1) else None
        sw_expected = round(80.0 / run1_steel_rho_knm3, 5)
        dd_ratio = round(dd6_g1 / dd1_g1, 5) if (dd1_g1 and dd6_g1) else None
        rho_deck_base = float(out1.get(KEY_MATERIAL_DECK_DENSITY) or 24.5)
        dd_expected = round(24.0 / rho_deck_base, 5)

        conc_tbl6 = resolve_material_properties_concrete(dict(win.input_dict), bridge=win.backend)
        steel_tbl6 = resolve_material_properties_steel(dict(win.input_dict), bridge=win.backend)
        cb_eff = out6.get("material.cross_bracing.effective")
        ed_eff = out6.get("material.end_diaphragm.effective")

        report["runs"]["RUN6_CUSTOM_MATERIALS"] = {
            "elapsed_s": t6,
            "primed_keys_preserved": f"{preserved_count}/12",
            "primed_values": primed_check,
            "sw_G1_baseline_kN": sw1_g1, "sw_G1_custom_kN": sw6_g1,
            "sw_ratio": sw_ratio, "sw_expected_80_76.4": sw_expected,
            "dd_lc": dd_lc1, "dd_G1_baseline_kN": dd1_g1, "dd_G1_custom_kN": dd6_g1,
            "dd_ratio": dd_ratio, "dd_expected_24_24.5": dd_expected,
            "cb_effective": cb_eff,
            "ed_effective": ed_eff,
            "concrete_excel_rows": conc_tbl6.get("rows") if conc_tbl6 else None,
            "steel_excel_rows": steel_tbl6.get("rows") if steel_tbl6 else None,
        }
        report["assertions"]["BUG12_custom_osi_priming_12_of_12"] = (preserved_count == 12)
        report["assertions"]["BUG03_G_precision_76.923"] = (
            primed_check.get(KEY_MATERIAL_GIRDER_G) == "76.923"
        )
        report["assertions"]["BUG04_custom_steel_density_SW_scaling"] = (
            sw_ratio is not None and abs(sw_ratio - sw_expected) < 0.005
        )
        report["assertions"]["BUG05_custom_deck_density_DD_scaling"] = (
            dd_ratio is not None and abs(dd_ratio - dd_expected) < 0.005
        )
        report["assertions"]["BUG06_CB_ED_custom_effective"] = (
            isinstance(cb_eff, dict) and float(cb_eff.get("fy_mpa", 0)) == 460.0
            and isinstance(ed_eff, dict) and float(ed_eff.get("fy_mpa", 0)) == 410.0
        )

        # =====================================================================
        # RUN 7: Live GUI OSI Non-Finite / Malformed Rejection (BUG-07)
        # =====================================================================
        print("\n=== RUN 7: Live GUI OSI Non-Finite & Malformed Rejection ===")
        unlock_if_locked(win)
        nan_osi = OUT_DIR / "invalid_nan.osi"
        nan_osi.write_text("geometry.span: NaN\nmaterial.girder.e: Infinity\n")
        bad_osi = OUT_DIR / "invalid_syntax.osi"
        bad_osi.write_text("geometry.span: [\n")

        span_before_inv = win.input_dict.get(KEY_SPAN)
        inv_results = {}
        for label, fpath in (("nan_inf", nan_osi), ("malformed_yaml", bad_osi)):
            POPUP_LOG.clear()
            QFileDialog.getOpenFileName = lambda *a, _p=str(fpath), **kw: (_p, "OSI Files (*.osi)")
            win.loadOSI_inputs()
            pump(150)
            inv_results[label] = {
                "span_unchanged": win.input_dict.get(KEY_SPAN) == span_before_inv,
                "popups": copy.deepcopy(POPUP_LOG),
                "rejected": not any("successfully" in p["text"].lower() for p in POPUP_LOG),
            }
        QFileDialog.getOpenFileName = orig_get_open

        report["runs"]["RUN7_GUI_NONFINITE_OSI"] = inv_results
        report["assertions"]["BUG07_GUI_OSI_nonfinite_rejected"] = all(
            v["span_unchanged"] and v["rejected"] for v in inv_results.values()
        )

    except Exception as exc:
        report["fatal_error"] = {"error": str(exc), "traceback": traceback.format_exc()}
        print("FATAL:", traceback.format_exc())
    finally:
        win.close()
        pump(150)

    passed = sum(1 for v in report["assertions"].values() if v)
    total = len(report["assertions"])
    report["summary"] = {
        "assertions_passed": passed,
        "assertions_total": total,
        "all_passed": (passed == total and total > 0 and "fatal_error" not in report),
    }

    out_json = OUT_DIR / "candidate_17fix_live_revalidation.json"
    out_json.write_text(json.dumps(report, indent=2, default=str))
    print("\n=== CANDIDATE 13-FIX REVALIDATION SUMMARY ===")
    print(json.dumps(report["summary"], indent=2))
    print(json.dumps(report["assertions"], indent=2))
    sys.exit(0 if report["summary"]["all_passed"] else 1)


if __name__ == "__main__":
    main()
