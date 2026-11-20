"""Phase 20 End-to-End Live PySide6 GUI Issue #92 Thermal Workflow Verification.

Exercises the complete GUI pipeline against phase20/candidate/src:
  1. Launch CustomWindow -> configure 25 m / 7.5 m bridge with Delhi location (65 / -10 C).
  2. Open Additional Inputs -> Temperature Load tab -> set 20e-6 (steel) / 10e-6 (RCC),
     save dialog, capture screenshot.
  3. Execute full Design via GUI button -> wait for completion -> capture MainWindow
     and OCC 3D CAD viewport PNGs + DTO verification.
  4. Render matplotlib plots for 1.0 TL (BMD, Deflection) and Envelope ULS (BMD) -> PNGs.
  5. Save .osi, reload valid .osi, and verify legacy temperature_load_kN_m2 .osi rejection.
  6. Generate LaTeX (.tex) + compiled PDF via Tectonic pdflatex shim and verify thermal
     content in extracted text + Results/Excel builders.

Outputs stored strictly under phase20/evidence/gui_issue92/.
"""
from __future__ import annotations

import copy
import json
import os
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

TESTS_BIN = "/Volumes/PortableSSD/OsdagBridge-screening-2026/phase20/tests/bin"
os.environ["PATH"] = TESTS_BIN + ":" + os.environ.get("PATH", "")

OUT_DIR = Path("/Volumes/PortableSSD/OsdagBridge-screening-2026/phase20/evidence/gui_issue92")
OUT_DIR.mkdir(parents=True, exist_ok=True)
SHOT_DIR = OUT_DIR / "screenshots"
SHOT_DIR.mkdir(parents=True, exist_ok=True)

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication, QFileDialog, QLabel, QLineEdit, QTabWidget, QWidget

from osdagbridge.core.bridge_types.plate_girder import plot_generator
from osdagbridge.core.bridge_types.plate_girder.plategirderbridge import PlateGirderBridge
from osdagbridge.core.reports.report_generator import (
    ReportMetadata,
    ReportOptions,
    ReportRequest,
)
from osdagbridge.core.utils.common import (
    KEY_CARRIAGEWAY_WIDTH,
    KEY_PROJECT_LOCATION,
    KEY_SPAN,
    KEY_TL_BRIDGE_TEMP_MAX,
    KEY_TL_BRIDGE_TEMP_MIN,
    KEY_TL_HIGHEST_MAX_TEMP,
    KEY_TL_LOWEST_MIN_TEMP,
    KEY_TL_TEMP_FALL,
    KEY_TL_TEMP_RISE,
    KEY_TL_THERMAL_COEFF_RCC,
    KEY_TL_THERMAL_COEFF_STEEL,
)
from osdagbridge.desktop.ui.dialogs import custom_messagebox
from osdagbridge.desktop.ui.dialogs.generate_results_values_builder import (
    resolve_temperature_load_parameters,
    resolve_thermal_analysis_summary,
)
from osdagbridge.desktop.ui.template_page import CustomWindow

POPUP_LOG: list[dict] = []

DELHI_65_LOC = {
    "state": "Delhi",
    "district": "New Delhi",
    "weather_data": {
        "zone": "IV",
        "z_value": 0.24,
        "wind_speed": 47.0,
        "max_temp": 65.0,
        "min_temp": -10.0,
    },
}


def pump(ms: int = 150):
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

    orig_show_design_error = getattr(CustomWindow, "_show_design_error", None)
    if orig_show_design_error is not None:
        def _recorded_design_error(self, err_trace):
            print("DESIGN_ERROR_TRACE:\n" + str(err_trace), flush=True)
            POPUP_LOG.append({"title": "DesignError", "text": str(err_trace)})
            return orig_show_design_error(self, err_trace)

        CustomWindow._show_design_error = _recorded_design_error


def set_le(w: QLineEdit, val: str):
    w.setFocus()
    w.clear()
    w.setText(str(val))
    w.editingFinished.emit()
    pump(100)


def wait_for_design(win: CustomWindow, timeout_s: float = 240.0) -> float:
    t0 = time.time()
    while getattr(win, "_design_running", False):
        QCoreApplication.processEvents()
        if time.time() - t0 > timeout_s:
            raise TimeoutError("Design timed out")
        time.sleep(0.05)
    pump(400)
    return round(time.time() - t0, 2)


def dump_cad_nonblank(win: CustomWindow, path: Path) -> dict:
    from PIL import Image
    import numpy as np

    win.cad_3d_widget.viewer.display.View.Dump(str(path))
    img = Image.open(path).convert("RGB")
    arr = np.asarray(img)
    w, h = img.size
    non_white = float(np.mean(np.any(arr < 245, axis=-1)))
    return {
        "path": str(path),
        "width": w,
        "height": h,
        "non_white_fraction": round(non_white, 4),
        "non_blank_full_size": (w >= 400 and h >= 250 and non_white > 0.01),
    }


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    install_popup_recorder()

    repo_file = str(Path(sys.modules[PlateGirderBridge.__module__].__file__).resolve())
    assert "/phase20/candidate/" in repo_file, f"Wrong candidate imported: {repo_file}"

    report = {"repo_file": repo_file, "assertions": {}, "artifacts": {}, "details": {}}

    win = CustomWindow(title="Phase 20 Issue #92 GUI Verification", backend=PlateGirderBridge)
    win.resize(1380, 860)
    win.show()
    pump(400)

    try:
        # 1. Basic geometry & location (65 / -10 degC)
        win.input_dock._update_input_dict(KEY_PROJECT_LOCATION, copy.deepcopy(DELHI_65_LOC))
        set_le(win.input_dock._w(KEY_SPAN), "25")
        set_le(win.input_dock._w(KEY_CARRIAGEWAY_WIDTH), "7.5")
        pump(150)

        # 2. Additional Inputs -> Loading -> Temperature Load tab
        win.common_design_func("Additional Inputs", target_tab="Loading")
        pump(300)
        dlg = win._get_additional_inputs()
        if hasattr(dlg, "tabs"):
            for i in range(dlg.tabs.count()):
                if dlg.tabs.tabText(i).strip().lower() == "loading":
                    dlg.tabs.setCurrentIndex(i)
                    pump(200)
                    break

        for sub_tw in dlg.findChildren(QTabWidget):
            if sub_tw is getattr(dlg, "tabs", None):
                continue
            for idx in range(sub_tw.count()):
                if "temperature" in sub_tw.tabText(idx).strip().lower():
                    if sub_tw.currentIndex() != idx:
                        sub_tw.setCurrentIndex(idx)
                    elif hasattr(sub_tw, "refresh_active_tab"):
                        sub_tw.refresh_active_tab()
                    pump(250)
                    break

        le_steel = dlg.findChild(QWidget, KEY_TL_THERMAL_COEFF_STEEL)
        le_rcc = dlg.findChild(QWidget, KEY_TL_THERMAL_COEFF_RCC)
        if le_steel is not None:
            set_le(le_steel, "20e-6")
        if le_rcc is not None:
            set_le(le_rcc, "10e-6")
        pump(200)

        temp_shot = SHOT_DIR / "gui_additional_inputs_temp.png"
        dlg.grab().save(str(temp_shot))
        dlg.save_button.click()
        pump(250)
        dlg.hide()
        pump(150)

        assert win.input_dict.get(KEY_TL_HIGHEST_MAX_TEMP) is not None, (
            f"Expected {KEY_TL_HIGHEST_MAX_TEMP} to be populated after Temperature Load tab refresh+save; "
            f"got {win.input_dict.get(KEY_TL_HIGHEST_MAX_TEMP)!r}"
        )
        assert win.input_dict.get(KEY_TL_LOWEST_MIN_TEMP) is not None, (
            f"Expected {KEY_TL_LOWEST_MIN_TEMP} to be populated after Temperature Load tab refresh+save; "
            f"got {win.input_dict.get(KEY_TL_LOWEST_MIN_TEMP)!r}"
        )

        # 3. Full live GUI Design
        POPUP_LOG.clear()
        win.input_dock.design_btn.click()
        pump(150)
        elapsed_s = wait_for_design(win)

        main_shot = SHOT_DIR / "gui_mainwindow_thermal_design.png"
        win.grab().save(str(main_shot))
        cad_shot = SHOT_DIR / "gui_cad_viewport.png"
        cad_info = dump_cad_nonblank(win, cad_shot)
        cad_dto = win.backend.get_3d_cad_parameters()

        ds = win.backend.get_results_dataset()
        out_d = dict(win.backend.output_dict)
        lcs = [str(x) for x in ds.coords["Loadcase"].values]
        tinfo = out_d.get("thermal_analysis") or {}
        solver_summary = tinfo.get("solver_summary") or {}

        # 4. Matplotlib plots for 1.0 TL & Envelope ULS
        nodes, members = win.backend.get_nodes_members()
        edge_dist = win.backend.get_edge_dist()

        fig_bmd_tl, sum_bmd_tl = plot_generator.build_figure_bmd(
            ds.sel(Loadcase="1.0 TL"), "Mz", nodes, members, edge_dist=edge_dist
        )
        p_bmd_tl = OUT_DIR / "plot_1_0_TL_bmd.png"
        p_bmd_tl.write_bytes(plot_generator.figure_to_bytes(fig_bmd_tl))

        fig_def_tl, sum_def_tl = plot_generator.build_figure_deflection(
            ds.sel(Loadcase="1.0 TL"), "Dy", nodes, members, edge_dist=edge_dist
        )
        p_def_tl = OUT_DIR / "plot_1_0_TL_defl.png"
        p_def_tl.write_bytes(plot_generator.figure_to_bytes(fig_def_tl))

        fig_bmd_env, sum_bmd_env = plot_generator.build_figure_bmd(
            ds.sel(Loadcase="Envelope ULS"), "Mz", nodes, members, edge_dist=edge_dist
        )
        p_bmd_env = OUT_DIR / "plot_env_uls_bmd.png"
        p_bmd_env.write_bytes(plot_generator.figure_to_bytes(fig_bmd_env))

        # 5. Save OSI, reload OSI, and reject legacy temperature_load_kN_m2 OSI
        orig_save = QFileDialog.getSaveFileName
        orig_open = QFileDialog.getOpenFileName
        saved_osi = OUT_DIR / "issue92_thermal_saved.osi"
        legacy_osi = OUT_DIR / "invalid_legacy_temperature.osi"
        legacy_osi.write_text("geometry.span: 25.0\ntemperature_load_kN_m2: 2.5\n", encoding="utf-8")

        try:
            POPUP_LOG.clear()
            QFileDialog.getSaveFileName = lambda *a, **kw: (str(saved_osi), "Input Files(*.osi)")
            win.saveOSI_inputs()
            pump(150)

            POPUP_LOG.clear()
            QFileDialog.getOpenFileName = lambda *a, **kw: (str(saved_osi), "Input Files (*.osi)")
            win.loadOSI_inputs()
            pump(150)
            valid_reload_ok = (
                saved_osi.exists()
                and any("loaded osi successfully" in p["text"].lower() for p in POPUP_LOG)
                and abs(float(win.input_dict.get(KEY_TL_THERMAL_COEFF_STEEL) or 0.0) - 20.0e-6) < 1e-12
            )

            POPUP_LOG.clear()
            QFileDialog.getOpenFileName = lambda *a, **kw: (str(legacy_osi), "Input Files (*.osi)")
            win.loadOSI_inputs()
            pump(150)
            legacy_rejected = (
                not any("loaded osi successfully" in p["text"].lower() for p in POPUP_LOG)
                and any("temperature_load_kN_m2" in p["text"] for p in POPUP_LOG)
            )
        finally:
            QFileDialog.getSaveFileName = orig_save
            QFileDialog.getOpenFileName = orig_open

        # 6. LaTeX report + compiled PDF + Results/Excel tables
        rep_dir = OUT_DIR / "report_issue92"
        rep_dir.mkdir(parents=True, exist_ok=True)
        req = ReportRequest(
            metadata=ReportMetadata(
                project_name="Phase 20 Issue #92 Thermal GUI Verification",
                project_location="New Delhi",
                designer="Screening QA",
                client="FOSSEE IIT Bombay",
                company="OsdagBridge",
            ),
            options=ReportOptions(
                sections=["loads", "analysis", "design_checks", "drawings"],
                include_figures=True,
                include_toc=True,
                include_pdf=True,
            ),
            output_dir=str(rep_dir),
            file_stem="issue92_thermal_report",
        )
        rep_res = win.backend.generate_design_report(req, cad_generator=None)
        pdf_path = Path(rep_res.pdf_path) if rep_res.pdf_path else (rep_dir / "issue92_thermal_report.pdf")
        tex_path = Path(rep_res.tex_path) if rep_res.tex_path else (rep_dir / "issue92_thermal_report.tex")
        pdf_exists = pdf_path.exists() and pdf_path.stat().st_size > 10000
        pdf_pages = 0
        pdf_has_thermal = False
        if pdf_exists:
            pinfo = subprocess.check_output(["/opt/homebrew/bin/pdfinfo", str(pdf_path)], text=True)
            m_pg = re.search(r"Pages:\s+(\d+)", pinfo)
            pdf_pages = int(m_pg.group(1)) if m_pg else 0
            ptxt = subprocess.check_output(["/opt/homebrew/bin/pdftotext", str(pdf_path), "-"], text=True)
            has_s = any(tok in ptxt for tok in ("20e-6", "2e-05", "2.000e-05"))
            has_r = any(tok in ptxt for tok in ("10e-6", "1e-05", "1.000e-05"))
            pdf_has_thermal = ("Thermal Analysis Summary" in ptxt and "1.0 TL" in ptxt and has_s and has_r)

        tbl_tl = resolve_temperature_load_parameters(dict(win.input_dict), bridge=win.backend)
        tbl_sum = resolve_thermal_analysis_summary(dict(win.input_dict), bridge=win.backend)

        report["artifacts"] = {
            "screenshot_temp_tab": str(temp_shot),
            "screenshot_mainwindow": str(main_shot),
            "screenshot_cad_3d": str(cad_shot),
            "plot_1_0_TL_bmd": str(p_bmd_tl),
            "plot_1_0_TL_defl": str(p_def_tl),
            "plot_env_uls_bmd": str(p_bmd_env),
            "saved_osi": str(saved_osi),
            "report_tex": str(tex_path),
            "report_pdf": str(pdf_path),
        }
        report["details"] = {
            "design_elapsed_s": elapsed_s,
            "cad_info": cad_info,
            "cad_dto_span_mm": getattr(cad_dto.girder_segments[0], "length", None),
            "thermal_cases_in_ds": [c for c in lcs if c.startswith("TL_") or c == "1.0 TL"],
            "solver_summary": solver_summary,
            "bmd_1_0_tl_summary": sum_bmd_tl,
            "defl_1_0_tl_summary": sum_def_tl,
            "bmd_env_uls_summary": sum_bmd_env,
            "pdf_pages": pdf_pages,
            "tbl_tl_row": tbl_tl["rows"][0] if tbl_tl else None,
            "tbl_sum_rows": tbl_sum["rows"] if tbl_sum else None,
        }

        report["assertions"] = {
            "gui_design_completed_with_thermal_cases": (
                set(tinfo.get("load_cases", [])) == {"TL_UNIFORM_RISE", "TL_UNIFORM_FALL", "TL_GRADIENT_HEAT", "TL_GRADIENT_COOL", "1.0 TL"}
                and len(solver_summary) == 5
            ),
            "gui_cad_3d_nonblank": bool(cad_info["non_blank_full_size"]),
            "gui_plots_rendered_png": (
                p_bmd_tl.exists() and p_bmd_tl.stat().st_size > 10000
                and p_def_tl.exists() and p_def_tl.stat().st_size > 10000
                and p_bmd_env.exists() and p_bmd_env.stat().st_size > 10000
            ),
            "gui_osi_save_and_reload_valid": bool(valid_reload_ok),
            "gui_osi_rejects_legacy_temperature_pressure": bool(legacy_rejected),
            "gui_report_pdf_compiled_with_thermal_tables": bool(pdf_exists and pdf_pages >= 20 and pdf_has_thermal),
            "gui_results_builder_tables_populated": bool(
                tbl_tl
                and abs(float(tbl_tl["rows"][0][2]) - 20.0e-6) < 1e-12
                and abs(float(tbl_tl["rows"][0][3]) - 10.0e-6) < 1e-12
                and tbl_sum
                and len(tbl_sum["rows"]) == 5
            ),
        }

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
    out_json = OUT_DIR / "phase20_issue92_gui_summary.json"
    out_json.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print("\n=== PHASE 20 ISSUE #92 GUI WORKFLOW SUMMARY ===")
    print(json.dumps(report["summary"], indent=2))
    print(json.dumps(report["assertions"], indent=2))
    sys.exit(0 if report["summary"]["all_passed"] else 1)


if __name__ == "__main__":
    main()
