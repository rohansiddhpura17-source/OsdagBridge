#!/usr/bin/env python3
"""
Phase 16 BUG-14 & ADV-003 Live GUI Regression Script.
Runs identical real PySide6 GUI workflows against either:
  --target baseline  (/Volumes/OsdagBridgeEnv/OsdagBridge)
  --target candidate (/Volumes/OsdagBridgeEnv/worktrees/phase89-fixes)

Tests:
  1. BUG-14 (ADV-007): Optimized -> Custom -> Optimized mode switching:
     - Zero unintended unit conversion on crash_barrier.area (m^2 vs mm^2)
     - Zero silent mutation of unrelated user-edited parameters
       (deck_thickness, wearing_course.density, railing, gamma_m0, load_cycles)
     - Zero stale custom stiffener keys remaining after Custom -> Optimized return
  2. ADV-003 (BUG-09 / BUG-14): Cross-bracing count reduction 29 -> 3 + Save + full Design:
     - Zero stale B*M4..B*M29 keys in input_dict and output_dict
     - Output pair keys match configured count=3 (G1-G2, G2-G3, spacing=7.5, brace_type=X)
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import time
import traceback
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--target", choices=("baseline", "candidate"), required=True)
args = parser.parse_args()

SRC_ROOT = (
    "/Volumes/OsdagBridgeEnv/OsdagBridge/src"
    if args.target == "baseline"
    else "/Volumes/PortableSSD/OsdagBridge-screening-2026/phase20/candidate/src"
)
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)
os.environ["PYTHONPATH"] = SRC_ROOT

OUT_DIR = Path("/Volumes/PortableSSD/OsdagBridge-screening-2026/phase20/evidence/gui_bug14")
OUT_DIR.mkdir(parents=True, exist_ok=True)

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication, QComboBox, QDialog, QLabel, QLineEdit, QWidget

from osdagbridge.core.bridge_types.plate_girder.plategirderbridge import PlateGirderBridge
from osdagbridge.core.utils.common import (
    KEY_CARRIAGEWAY_WIDTH,
    KEY_CB_AREA,
    KEY_DESIGN_MODE,
    KEY_DO_GAMMA_M0,
    KEY_DO_LOAD_CYCLES,
    KEY_MP_CB_BRACING_CONNECTION,
    KEY_MP_CB_NO_OF_CROSS_BRACINGS,
    KEY_MP_CB_TYPE,
    KEY_MP_STIFFENER_INTERMEDIATE,
    KEY_MP_STIFFENER_INTERMEDIATE_SPACING,
    KEY_MP_STIFFENER_SPACING,
    KEY_PROJECT_LOCATION,
    KEY_RL_LOAD_VALUE,
    KEY_RL_WIDTH,
    KEY_SPAN,
    KEY_TS_DECK_THICKNESS,
    KEY_WC_DENSITY,
    KEY_WC_THICKNESS,
)
from osdagbridge.desktop.ui.dialogs import custom_messagebox
from osdagbridge.desktop.ui.template_page import CustomWindow

POPUP_LOG: list[dict] = []
DELHI_LOC = {
    "state": "Delhi",
    "district": "New Delhi",
    "weather_data": {"zone": "IV", "wind_speed": 47, "max_temp": 45.0, "min_temp": 4.0},
}


def pump(ms: int = 120):
    deadline = time.time() + ms / 1000.0
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.01)


def install_popup_recorder():
    def _recorded_exec(self):
        texts = [lbl.text().strip() for lbl in self.findChildren(QLabel) if lbl.text() and lbl.text().strip()]
        POPUP_LOG.append({"title": self.windowTitle(), "text": " | ".join(texts)})
        self.accept()
        btns = getattr(self, "buttons", None)
        if isinstance(btns, (list, tuple)) and btns:
            return btns[0]
        return "Continue"
    custom_messagebox.CustomMessageBox.exec = _recorded_exec


def set_le(w: QLineEdit, val: str):
    w.setFocus()
    w.clear()
    w.setText(str(val))
    w.editingFinished.emit()
    pump(80)


def set_cb(w: QComboBox, text: str) -> bool:
    idx = w.findText(text)
    if idx < 0:
        for i in range(w.count()):
            if w.itemText(i).strip().lower() == text.strip().lower():
                idx = i
                break
    if idx < 0:
        return False
    w.setCurrentIndex(idx)
    w.currentTextChanged.emit(w.itemText(idx))
    pump(120)
    return True


def wait_for_design(win: CustomWindow, timeout_s: float = 240.0) -> float:
    t0 = time.time()
    while getattr(win, "_design_running", False):
        QCoreApplication.processEvents()
        if time.time() - t0 > timeout_s:
            raise TimeoutError("Design timed out")
        time.sleep(0.05)
    pump(300)
    return round(time.time() - t0, 2)


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    install_popup_recorder()

    repo_file = str(Path(sys.modules[PlateGirderBridge.__module__].__file__).resolve())
    expected_substr = "/OsdagBridge/" if args.target == "baseline" else "/phase20/candidate/"
    assert expected_substr in repo_file, f"Wrong target imported: {repo_file}"

    report = {"target": args.target, "repo_file": repo_file, "assertions": {}, "details": {}}

    # =========================================================================
    # TEST 1: BUG-14 (ADV-007) — Optimized -> Custom -> Optimized Mode Switch
    # =========================================================================
    win = CustomWindow(title=f"BUG-14 {args.target}", backend=PlateGirderBridge)
    win.resize(1380, 860)
    win.show()
    pump(350)
    try:
        win.input_dock._update_input_dict(KEY_PROJECT_LOCATION, copy.deepcopy(DELHI_LOC))
        set_le(win.input_dock._w(KEY_SPAN), "30")
        set_le(win.input_dock._w(KEY_CARRIAGEWAY_WIDTH), "4.25")
        pump(150)

        # Open AdditionalInputs via real common_design_func so initial defaults + computes run
        win.common_design_func("Additional Inputs")
        pump(250)
        dlg = win._get_additional_inputs()

        # User edits enabled unrelated parameters in Optimized mode & clicks Save
        set_le(dlg.findChild(QWidget, KEY_TS_DECK_THICKNESS), "200")
        set_le(dlg.findChild(QWidget, KEY_WC_THICKNESS), "65")
        set_le(dlg.findChild(QWidget, KEY_DO_GAMMA_M0), "1.15")
        set_le(dlg.findChild(QWidget, KEY_DO_LOAD_CYCLES), "500000")
        dlg.save_button.click()
        pump(200)
        dlg.hide()
        pump(100)

        tracked_keys = [
            KEY_TS_DECK_THICKNESS,
            KEY_WC_THICKNESS,
            KEY_WC_DENSITY,
            KEY_CB_AREA,
            KEY_RL_WIDTH,
            KEY_RL_LOAD_VALUE,
            KEY_DO_GAMMA_M0,
            KEY_DO_LOAD_CYCLES,
        ]
        before_opt = {k: win.input_dict.get(k) for k in tracked_keys}
        opt_stiff_before = {
            KEY_MP_STIFFENER_SPACING: win.input_dict.get(KEY_MP_STIFFENER_SPACING),
            KEY_MP_STIFFENER_INTERMEDIATE: win.input_dict.get(KEY_MP_STIFFENER_INTERMEDIATE),
            KEY_MP_STIFFENER_INTERMEDIATE_SPACING: win.input_dict.get(KEY_MP_STIFFENER_INTERMEDIATE_SPACING),
            "G1M1_spacing": win.input_dict.get(f"{KEY_MP_STIFFENER_SPACING}.G1.M1"),
            "G1M1_int_spacing": win.input_dict.get(f"{KEY_MP_STIFFENER_INTERMEDIATE_SPACING}.G1.M1"),
        }

        # Switch Optimized -> Custom via real InputDock Design Mode combo
        dm_combo = win.input_dock._w(KEY_DESIGN_MODE)
        set_cb(dm_combo, "Custom")
        pump(300)
        after_custom = {k: win.input_dict.get(k) for k in tracked_keys}

        # Check numeric preservation of every tracked unrelated key (and crash_barrier.area < 5.0 m^2)
        mutations = {}
        for k in tracked_keys:
            b, a = before_opt.get(k), after_custom.get(k)
            try:
                same = abs(float(b) - float(a)) < 1e-4
            except (TypeError, ValueError):
                same = (b == a)
            if not same:
                mutations[k] = {"before": b, "after": a}

        cb_area_after = float(after_custom[KEY_CB_AREA]) if after_custom.get(KEY_CB_AREA) is not None else -1.0
        cb_area_unit_ok = 0.01 < cb_area_after < 5.0

        # Edit Custom stiffener overrides & click Save
        dlg = win._get_additional_inputs()
        set_cb(dlg.findChild(QWidget, KEY_MP_STIFFENER_INTERMEDIATE), "Yes")
        set_le(dlg.findChild(QWidget, KEY_MP_STIFFENER_INTERMEDIATE_SPACING), "3000")
        set_le(dlg.findChild(QWidget, KEY_MP_STIFFENER_SPACING), "150")
        dlg.save_button.click()
        pump(200)
        dlg.hide()
        pump(100)
        custom_stiff_saved = {
            KEY_MP_STIFFENER_SPACING: win.input_dict.get(KEY_MP_STIFFENER_SPACING),
            KEY_MP_STIFFENER_INTERMEDIATE: win.input_dict.get(KEY_MP_STIFFENER_INTERMEDIATE),
            KEY_MP_STIFFENER_INTERMEDIATE_SPACING: win.input_dict.get(KEY_MP_STIFFENER_INTERMEDIATE_SPACING),
            "G1M1_spacing": win.input_dict.get(f"{KEY_MP_STIFFENER_SPACING}.G1.M1"),
            "G1M1_int_spacing": win.input_dict.get(f"{KEY_MP_STIFFENER_INTERMEDIATE_SPACING}.G1.M1"),
        }

        # Switch Custom -> Optimized via real InputDock Design Mode combo
        set_cb(dm_combo, "Optimized")
        pump(300)
        after_return_opt = {k: win.input_dict.get(k) for k in tracked_keys}
        opt_stiff_after = {
            KEY_MP_STIFFENER_SPACING: win.input_dict.get(KEY_MP_STIFFENER_SPACING),
            KEY_MP_STIFFENER_INTERMEDIATE: win.input_dict.get(KEY_MP_STIFFENER_INTERMEDIATE),
            KEY_MP_STIFFENER_INTERMEDIATE_SPACING: win.input_dict.get(KEY_MP_STIFFENER_INTERMEDIATE_SPACING),
            "G1M1_spacing": win.input_dict.get(f"{KEY_MP_STIFFENER_SPACING}.G1.M1"),
            "G1M1_int_spacing": win.input_dict.get(f"{KEY_MP_STIFFENER_INTERMEDIATE_SPACING}.G1.M1"),
        }

        return_mutations = {}
        for k in tracked_keys:
            b, a = before_opt.get(k), after_return_opt.get(k)
            try:
                same = abs(float(b) - float(a)) < 1e-4
            except (TypeError, ValueError):
                same = (b == a)
            if not same:
                return_mutations[k] = {"before": b, "after": a}

        # Verify custom overrides (150, 3000) did NOT linger after returning to Optimized
        stale_stiffeners = {
            k: v for k, v in opt_stiff_after.items()
            if str(v) in ("150", "3000") and str(opt_stiff_before.get(k)) != str(v)
        }

        report["details"]["BUG14_ADV007"] = {
            "before_opt": before_opt,
            "after_custom": after_custom,
            "after_return_opt": after_return_opt,
            "mutations_opt_to_custom": mutations,
            "mutations_custom_to_opt": return_mutations,
            "cb_area_m2_after_custom": cb_area_after,
            "opt_stiff_before": opt_stiff_before,
            "custom_stiff_saved": custom_stiff_saved,
            "opt_stiff_after_return": opt_stiff_after,
            "stale_stiffeners_after_return": stale_stiffeners,
        }
        report["assertions"]["BUG14_no_unrelated_mutations_opt_to_custom"] = (len(mutations) == 0)
        report["assertions"]["BUG14_cb_area_unit_m2_preserved"] = cb_area_unit_ok
        report["assertions"]["BUG14_no_unrelated_mutations_custom_to_opt"] = (len(return_mutations) == 0)
        report["assertions"]["BUG14_no_stale_stiffeners_after_return"] = (len(stale_stiffeners) == 0)
    finally:
        win.close()
        pump(150)

    # =========================================================================
    # TEST 2: ADV-003 — Cross-Bracing Count Reduction 29 -> 3 + Save + Design
    # =========================================================================
    win = CustomWindow(title=f"ADV-003 {args.target}", backend=PlateGirderBridge)
    win.resize(1380, 860)
    win.show()
    pump(350)
    try:
        win.input_dock._update_input_dict(KEY_PROJECT_LOCATION, copy.deepcopy(DELHI_LOC))
        set_le(win.input_dock._w(KEY_SPAN), "30")
        set_le(win.input_dock._w(KEY_CARRIAGEWAY_WIDTH), "4.25")
        pump(150)

        win.common_design_func("Additional Inputs")
        pump(250)
        dlg = win._get_additional_inputs()
        set_cb(dlg.findChild(QWidget, KEY_MP_CB_TYPE), "X-Bracing")
        set_cb(dlg.findChild(QWidget, KEY_MP_CB_BRACING_CONNECTION), "Welded")
        cb_cnt_w = dlg.findChild(QWidget, KEY_MP_CB_NO_OF_CROSS_BRACINGS)
        set_le(cb_cnt_w, "30")  # clamps to 29, seeds B1M1..B1M29
        set_le(cb_cnt_w, "3")   # reduces 29 -> 3
        dlg.save_button.click()
        pump(200)
        dlg.hide()

        cb_re = re.compile(r"\.G\d+G\d+\.B\d+M(\d+)$")
        stale_in = [
            k for k in win.input_dict
            if k.startswith("member_properties.cross_bracing_details.")
            and cb_re.search(k)
            and int(cb_re.search(k).group(1)) > 3
        ]

        # Run full live GUI Design
        win.input_dock.design_btn.click()
        pump(150)
        t_des = wait_for_design(win)
        out_d = dict(win.backend.output_dict)
        stale_out = [
            k for k in out_d
            if k.startswith("member_properties.cross_bracing_details.")
            and cb_re.search(k)
            and int(cb_re.search(k).group(1)) > 3
        ]
        cb_res = out_d.get("crossbracing_design_results") or {}
        cb_forces = out_d.get("crossbracing_forces_dict") or {}

        report["details"]["ADV003_brace_29_to_3"] = {
            "elapsed_s": t_des,
            "stale_input_keys_count": len(stale_in),
            "stale_output_keys_count": len(stale_out),
            "stale_sample": stale_in[:6],
            "no_of_cross_bracings": out_d.get(KEY_MP_CB_NO_OF_CROSS_BRACINGS),
            "output_pairs": sorted(cb_res.keys()) if isinstance(cb_res, dict) else [],
            "brace_type": cb_forces.get("brace_type") if isinstance(cb_forces, dict) else None,
            "spacing": out_d.get("member_properties.cross_bracing_details.spacing"),
        }
        report["assertions"]["ADV003_zero_stale_input_keys_29_to_3"] = (len(stale_in) == 0)
        report["assertions"]["ADV003_zero_stale_output_keys_29_to_3"] = (len(stale_out) == 0)
        report["assertions"]["ADV003_design_pairs_and_type_ok"] = (
            sorted(cb_res.keys()) == ["G1-G2", "G2-G3"]
            and cb_forces.get("brace_type") == "X"
            and int(out_d.get(KEY_MP_CB_NO_OF_CROSS_BRACINGS) or 0) == 3
            and abs(float(out_d.get("member_properties.cross_bracing_details.spacing") or 0.0) - 7.5) < 0.01
        )
    finally:
        win.close()
        pump(150)

    passed = sum(1 for v in report["assertions"].values() if v)
    total = len(report["assertions"])
    report["summary"] = {"passed": passed, "total": total, "all_passed": passed == total}
    out_path = OUT_DIR / f"bug14_adv003_gui_{args.target}.json"
    out_path.write_text(json.dumps(report, indent=2, default=str))
    print(f"=== {args.target.upper()} SUMMARY ===")
    print(json.dumps(report["summary"], indent=2))
    print(json.dumps(report["assertions"], indent=2))
    sys.exit(0 if report["summary"]["all_passed"] else 1)


if __name__ == "__main__":
    main()
