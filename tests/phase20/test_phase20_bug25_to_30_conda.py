"""Phase 20 Conda-native (zero-stub) Baseline-FAIL / Candidate-PASS regression
suite for BUG-25..BUG-30 + Phase 20 refinements (inf UI bar safety, BOQ chord
toggles, missing-SW None/warning attrs, real osdag_core).

Usage (under Conda Qt6/OpenSeesPy environment):
  python test_phase20_bug25_to_30_conda.py /path/to/src
"""
from __future__ import annotations

import ast
import inspect
import logging
import math
import sys
import types
import unittest
from pathlib import Path

DEFAULT_CAND_SRC = Path(__file__).resolve().parents[1] / "candidate" / "src"
REPO_SRC = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else DEFAULT_CAND_SRC
if str(REPO_SRC) not in sys.path:
    sys.path.insert(0, str(REPO_SRC))


class TestPhase20Bug25To30Conda(unittest.TestCase):
    def test_bug25_irc22_table2_i_rolled_case_insensitive_real_osdag_core(self):
        from osdagbridge.core.utils.codes.irc22_2015 import IRC22_2014

        res_def = IRC22_2014.cl_602_table2_i_outstanding_compression_flange(90.0, 10.0, 250.0)
        res_roll = IRC22_2014.cl_602_table2_i_outstanding_compression_flange(90.0, 10.0, 250.0, section_type="rolled")
        res_title = IRC22_2014.cl_602_table2_i_outstanding_compression_flange(90.0, 10.0, 250.0, section_type="Rolled")
        self.assertEqual(res_def, ["Plastic", 9.0, 9.4])
        self.assertEqual(res_roll, ["Plastic", 9.0, 9.4])
        self.assertEqual(res_roll, res_title)

    def test_bug26_fatigue_shear_cap_matches_tau_y(self):
        from osdagbridge.core.bridge_types.plate_girder.designer import IRC22CapacityCalculator

        stub = types.SimpleNamespace(
            sec=types.SimpleNamespace(tf_top=20.0, tf_bot=20.0, fabrication="rolled"),
            mat=types.SimpleNamespace(fy=250.0, gamma_mft=1.35),
            fatigue=types.SimpleNamespace(Nsc=1000, ffn=None, tfn=None),
        )
        res = IRC22CapacityCalculator.compute_fatigue(stub, stress_range_MPa=50.0)
        self.assertAlmostEqual(res["tau_fd_eff_MPa"], 0.43 * 250.0, places=3)

    def test_bug27_deckdesign_zero_capacity_inf_and_qt_bar_safe(self):
        src = (REPO_SRC / "osdagbridge/core/bridge_types/plate_girder/deckdesign.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        ur_fn = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_ur":
                mod = ast.Module(body=[node], type_ignores=[])
                ns = {"invalid_capacity_checks": []}
                exec(compile(mod, "deckdesign.py", "exec"), ns)
                ur_fn = ns["_ur"]
                break
        self.assertIsNotNone(ur_fn)
        sig_ur = inspect.signature(ur_fn)
        if len(sig_ur.parameters) == 3:
            u_zero_cap = ur_fn("ur_composite_conc_stress", 120.0, 0.0)
            u_zero_zero = ur_fn("ur_composite_conc_stress", 0.0, 0.0)
            u_half = ur_fn("ur_composite_conc_stress", 50.0, 100.0)
            self.assertIn("ur_composite_conc_stress", ns["invalid_capacity_checks"])
        else:
            u_zero_cap = ur_fn(120.0, 0.0)
            u_zero_zero = ur_fn(0.0, 0.0)
            u_half = ur_fn(50.0, 100.0)
        self.assertTrue(u_zero_cap == float("inf") or u_zero_cap > 1.0)
        self.assertEqual(u_zero_zero, 0.0)
        self.assertAlmostEqual(u_half, 0.5)

        # Verify Qt PercentBarWidget formats/renders infinite UR safely without OverflowError
        from PySide6.QtWidgets import QApplication
        from osdagbridge.desktop.ui.utils.custom_widgets import PercentBarWidget

        app = QApplication.instance() or QApplication([])
        self.assertIsNotNone(app)
        w = PercentBarWidget()
        w.set_value(float("inf"))
        w.resize(120, 24)
        w.repaint()
        self.assertEqual(w._fmt(float("inf")), "INF")

    def test_bug28_boq_densities_girders_chords_and_disabled_toggles(self):
        from osdagbridge.core.utils.common import KEY_SPAN, KEY_TS_NO_OF_GIRDERS, KEY_TS_DECK_THICKNESS, KEY_TS_GIRDER_SPACING
        from osdagbridge.core.boq.boq_generator import calculate_material_quantities

        inp = {
            KEY_SPAN: 30.0,
            KEY_TS_NO_OF_GIRDERS: 3,
            "typical_section.overall_bridge_width": 10.0,
            KEY_TS_DECK_THICKNESS: 250.0,
            KEY_TS_GIRDER_SPACING: 3.0,
            "typical_section.crash_barrier.area": 0.30,
            "material.deck.density": 24.0,
            "material.steel.density": 80.0,
            "member_properties.girder_details.section_properties.area.G1.M1": 0.04,
            "member_properties.girder_details.section_properties.area.G2.M1": 0.06,
            "member_properties.girder_details.section_properties.area.G3.M1": 0.04,
        }
        out = {
            "transverse_member_design.cb.section_properties.bracing.G1G2.A": 10.0,
            "transverse_member_design.cb.section_properties.top_chord.G1G2.A": 20.0,
            "transverse_member_design.cb.section_properties.bottom_chord.G1G2.A": 25.0,
            "crossbracing_forces_dict": {"geometry": {"diagonal_length_m": 4.0, "cb_spacing_m": 5.0}},
        }
        q = calculate_material_quantities(inp, out)
        self.assertEqual(q["concrete_deck_wt_total"], "180.00")
        self.assertEqual(q["crash_barrier_wt_total"], "43.20")
        self.assertEqual(q["steel_girders_vol_total"], "4.20")
        self.assertEqual(q["steel_girders_wt_total"], "33.60")
        self.assertIn("0.00200", q["bracing_top_vol_formula"])
        self.assertIn("0.00250", q["bracing_bot_vol_formula"])

        out_off = dict(out)
        out_off["member_properties.cross_bracing_details.top_chord"] = False
        out_off["member_properties.cross_bracing_details.bottom_chord"] = False
        q_off = calculate_material_quantities(inp, out_off)
        self.assertEqual(q_off["bracing_top_qty"], "0")
        self.assertEqual(q_off["bracing_bot_qty"], "0")

    def test_bug29_analysis_results_no_fabricated_22_4_sw_fallback(self):
        from osdagbridge.core.bridge_types.plate_girder.analysis_results import PlateGirderAnalysisResults

        ar = PlateGirderAnalysisResults.__new__(PlateGirderAnalysisResults)
        ar.bridge = types.SimpleNamespace(self_weight_load_case=None)
        g_map = {"G1": {"start": 1, "end": 2}}
        nodes = {1: (0.0, 0.0, 1.5), 2: (30.0, 0.0, 1.5)}
        with self.assertLogs("osdagbridge.core.bridge_types.plate_girder.analysis_results", level=logging.WARNING):
            df = ar._get_girder_sw_df(g_map, nodes)
        val = df.iloc[0]["Value (kN/m)"]
        self.assertIsNone(val)
        self.assertIsNone(df.attrs.get("total_v"))
        self.assertIn("G1", df.attrs.get("missing_sw_girders", []))

    def test_bug30_map_coordinates_and_cad_mutable_default(self):
        from osdagbridge.core.bridge_types.plate_girder.validator import BridgeInputValidator
        from osdagbridge.core.bridge_types.plate_girder.cad_generator import osdag_display_shape

        v = BridgeInputValidator()
        self.assertFalse(v.validate_map_coordinates("nan", "inf")[0])
        self.assertFalse(v.validate_map_coordinates("999", "-999")[0])
        self.assertTrue(v.validate_map_coordinates("19.076", "72.877")[0])

        sig = inspect.signature(osdag_display_shape)
        self.assertIsNone(sig.parameters["label"].default)
        dummy_display = types.SimpleNamespace(
            DisplayShape=lambda *a, **kw: ["ais_1"],
            Context=types.SimpleNamespace(Activate=lambda a, m: None),
        )
        dummy_canvas = types.SimpleNamespace(model_ais_objects={})
        osdag_display_shape(dummy_display, object(), canvas=dummy_canvas)


if __name__ == "__main__":
    argv = [sys.argv[0]] + [a for a in sys.argv[1:] if a.startswith("-")]
    unittest.main(argv=argv, verbosity=2)
