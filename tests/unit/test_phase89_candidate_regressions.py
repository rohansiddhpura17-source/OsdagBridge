import os
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from osdagbridge.core.bridge_types.plate_girder import analyser as analyser_module
from osdagbridge.core.bridge_types.plate_girder import defaults as defaults_module
from osdagbridge.core.bridge_types.plate_girder import plategirderbridge as bridge_module
from osdagbridge.core.bridge_types.plate_girder.crossbracingforces import CrossBracingForces
from osdagbridge.core.bridge_types.plate_girder.dto import ConcreteProperties
from osdagbridge.core.utils.common import (
    KEY_CARRIAGEWAY_WIDTH, KEY_CROSS_BRACING, KEY_DECK_CONCRETE_GRADE_BASIC,
    KEY_DESIGN_MODE, KEY_DS_REINF_MATERIAL, KEY_DS_STUD_HEIGHT,
    KEY_END_DIAPHRAGM, KEY_FOOTPATH, KEY_GIRDER, KEY_INCLUDE_MEDIAN,
    KEY_MATERIAL_CROSS_BRACING_DENSITY, KEY_MATERIAL_CROSS_BRACING_E,
    KEY_MATERIAL_CROSS_BRACING_FU, KEY_MATERIAL_CROSS_BRACING_FY,
    KEY_MATERIAL_DECK_DENSITY, KEY_MATERIAL_DECK_ECM,
    KEY_MATERIAL_DECK_FCK, KEY_MATERIAL_DECK_FCTM,
    KEY_MATERIAL_END_DIAPHRAGM_FU, KEY_MATERIAL_END_DIAPHRAGM_FY,
    KEY_MATERIAL_GIRDER_DENSITY, KEY_MATERIAL_GIRDER_E,
    KEY_MATERIAL_GIRDER_FU, KEY_MATERIAL_GIRDER_FY, KEY_MATERIAL_GIRDER_G,
    KEY_MATERIAL_GIRDER_POISSON, KEY_MP_CB_NO_OF_CROSS_BRACINGS,
    KEY_MP_CB_SPACING, KEY_MP_GD_SEGMENT_TABLE, KEY_MP_GD_TOTAL_SPAN,
    KEY_MP_GIRDER_DEPTH, KEY_MP_GIRDER_SECTIONAL_AREA,
    KEY_MP_GIRDER_TOP_FLANGE_WIDTH, KEY_MP_STIFFENER_BEARING_OUTSTAND,
    KEY_MP_STIFFENER_INTERMEDIATE_OUTSTAND, KEY_MP_STIFFENER_INTERMEDIATE_SPACING,
    KEY_PL_SELF_WEIGHT_FACTOR, KEY_SKEW_ANGLE, KEY_SPAN,
    KEY_TS_DECK_THICKNESS, KEY_TS_NO_OF_GIRDERS, KEY_TS_OVERALL_WIDTH,
    KEY_WC_DENSITY, KEY_WC_THICKNESS,
)
from osdagbridge.desktop.ui.dialogs.generate_results_values_builder import (
    resolve_material_properties_concrete,
    resolve_material_properties_steel,
    resolve_permanent_load_summary,
)
from osdagbridge.desktop.ui.dialogs.material_properties import MaterialPropertiesDialog


class Phase89CandidateRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_concrete_excel_export_converts_gpa_and_reports_raw_ratio(self):
        bridge = SimpleNamespace(
            _build_material_props=lambda: SimpleNamespace(
                concrete_prop=SimpleNamespace(fck=40, fctm=3, Ecm=33),
                steel_prop=SimpleNamespace(E=200e9),
            )
        )
        block = resolve_material_properties_concrete(
            {KEY_DECK_CONCRETE_GRADE_BASIC: "M40", KEY_MATERIAL_DECK_DENSITY: 24.0},
            bridge,
        )
        row = block["rows"][0]
        self.assertEqual(row[4], 33000.0)
        self.assertEqual(row[5], 6.06)  # raw Es/Ecm; IRC minimum 7.5 is distinct
        self.assertEqual(row[6], 24.0)

    def test_permanent_load_summary_uses_custom_steel_and_deck_densities(self):
        base = {
            KEY_TS_NO_OF_GIRDERS: 3,
            KEY_PL_SELF_WEIGHT_FACTOR: 1.0,
            f"{KEY_MP_GIRDER_SECTIONAL_AREA}.G1.M1": 0.04,
            f"{KEY_MP_GIRDER_SECTIONAL_AREA}.G2.M1": 0.04,
            f"{KEY_MP_GIRDER_SECTIONAL_AREA}.G3.M1": 0.04,
            KEY_TS_OVERALL_WIDTH: 5.15,
            KEY_TS_DECK_THICKNESS: 250.0,
            KEY_WC_THICKNESS: 50.0,
            KEY_WC_DENSITY: 24.0,
        }
        std = resolve_permanent_load_summary(
            {**base, KEY_MATERIAL_GIRDER_DENSITY: 78.5, KEY_MATERIAL_DECK_DENSITY: 25.0}
        )["rows"][0][0]
        cust = resolve_permanent_load_summary(
            {**base, KEY_MATERIAL_GIRDER_DENSITY: 80.0, KEY_MATERIAL_DECK_DENSITY: 24.0}
        )["rows"][0][0]
        expected_delta = 0.04 * (80.0 - 78.5) + (0.25 * (24.0 - 25.0) * 5.15 / 3.0)
        self.assertAlmostEqual(cust - std, round(expected_delta, 3), delta=0.002)

    def test_deck_design_receives_ecm_in_mpa(self):
        captured = {}

        def fake_design(*args, **kwargs):
            captured.update(kwargs)
            return {"deck_design_check": "ok"}, {}

        bridge = object.__new__(bridge_module.PlateGirderBridge)
        bridge.input_dict = {KEY_DS_REINF_MATERIAL: "Fe 500", KEY_DS_STUD_HEIGHT: 100}
        bridge.material_props = SimpleNamespace(
            concrete_prop=ConcreteProperties("M40", 40, 3, 33)
        )
        bridge.design_results = {}
        bridge.output_dict = {}
        bridge._lookup_material = lambda *args: 500000 if args[-1] == "fy" else 200000
        with patch.object(bridge_module.deckdesign, "design_deck_slab", fake_design), patch.object(
            bridge_module, "resolve_girder_value", lambda *_: 0.5
        ):
            bridge.design_deck_slab()
        self.assertEqual(captured["Ecm"], 33000.0)

    def test_custom_steel_density_reaches_steel_properties(self):
        bridge = object.__new__(bridge_module.PlateGirderBridge)
        bridge.input_dict = {
            KEY_GIRDER: "custom_steel_case", KEY_CROSS_BRACING: "E 350A",
            KEY_END_DIAPHRAGM: "E 350A", KEY_DECK_CONCRETE_GRADE_BASIC: "M40",
            KEY_MATERIAL_GIRDER_E: 210, KEY_MATERIAL_GIRDER_G: 81,
            KEY_MATERIAL_GIRDER_POISSON: 0.3, KEY_MATERIAL_GIRDER_DENSITY: 80,
            KEY_MATERIAL_GIRDER_FY: 355, KEY_MATERIAL_GIRDER_FU: 505,
            KEY_MATERIAL_DECK_FCK: 40, KEY_MATERIAL_DECK_FCTM: 3,
            KEY_MATERIAL_DECK_ECM: 33,
        }
        bridge._lookup_material = lambda *_: None
        self.assertEqual(bridge._build_material_props().steel_prop.rho, 80000.0)

    def test_explicit_steel_density_overrides_database_grade_and_converts_units(self):
        bridge = object.__new__(bridge_module.PlateGirderBridge)
        bridge.input_dict = {
            KEY_GIRDER: "E 350A", KEY_CROSS_BRACING: "E 350A",
            KEY_END_DIAPHRAGM: "E 350A", KEY_DECK_CONCRETE_GRADE_BASIC: "M40",
            KEY_MATERIAL_GIRDER_DENSITY: 85.0,
            KEY_MATERIAL_GIRDER_E: 210, KEY_MATERIAL_GIRDER_G: 81,
            KEY_MATERIAL_GIRDER_POISSON: 0.3,
            KEY_MATERIAL_GIRDER_FY: 355, KEY_MATERIAL_GIRDER_FU: 505,
            KEY_MATERIAL_DECK_FCK: 40, KEY_MATERIAL_DECK_FCTM: 3,
            KEY_MATERIAL_DECK_ECM: 33,
        }
        bridge._lookup_material = lambda grade, prop: (
            78500.0 if prop == "Density" else
            210e9 if prop == "Modulus of Elasticity" else
            0.3 if prop == "Poisson's Ratio" else
            355e6 if prop == "Yield Strength" else
            505e6 if prop == "Ultimate Tensile Strength" else
            40 if prop == "fck" else
            3 if prop == "fctm" else
            33 if prop == "Ecm" else None
        )
        self.assertEqual(bridge._build_material_props().steel_prop.rho, 85000.0)

    def test_steel_density_defaults_to_database_or_legacy_custom_default(self):
        bridge = object.__new__(bridge_module.PlateGirderBridge)
        bridge.input_dict = {
            KEY_GIRDER: "E 350A", KEY_CROSS_BRACING: "E 350A",
            KEY_END_DIAPHRAGM: "E 350A", KEY_DECK_CONCRETE_GRADE_BASIC: "M40",
        }
        bridge._lookup_material = lambda _grade, prop: (
            78500.0 if prop == "Density" else
            210e9 if prop == "Modulus of Elasticity" else
            0.3 if prop == "Poisson's Ratio" else
            355e6 if prop == "Yield Strength" else
            505e6 if prop == "Ultimate Tensile Strength" else
            40 if prop == "fck" else
            3 if prop == "fctm" else
            33 if prop == "Ecm" else None
        )
        self.assertEqual(bridge._build_material_props().steel_prop.rho, 78500.0)

        bridge.input_dict[KEY_GIRDER] = "custom_steel_case"
        bridge._lookup_material = lambda *_: None
        self.assertEqual(bridge._build_material_props().steel_prop.rho, 78500.0)

    def test_invalid_explicit_steel_density_is_rejected(self):
        bridge = object.__new__(bridge_module.PlateGirderBridge)
        bridge.input_dict = {
            KEY_GIRDER: "custom_steel_case", KEY_CROSS_BRACING: "E 350A",
            KEY_END_DIAPHRAGM: "E 350A", KEY_DECK_CONCRETE_GRADE_BASIC: "M40",
            KEY_MATERIAL_GIRDER_E: 210, KEY_MATERIAL_GIRDER_G: 81,
            KEY_MATERIAL_GIRDER_POISSON: 0.3, KEY_MATERIAL_GIRDER_FY: 355,
            KEY_MATERIAL_GIRDER_FU: 505, KEY_MATERIAL_DECK_FCK: 40,
            KEY_MATERIAL_DECK_FCTM: 3, KEY_MATERIAL_DECK_ECM: 33,
        }
        bridge._lookup_material = lambda *_: None
        for bad_density in ("NaN", "Infinity", "not-a-number", 49.9, 120.1):
            with self.subTest(density=bad_density):
                bridge.input_dict[KEY_MATERIAL_GIRDER_DENSITY] = bad_density
                with self.assertRaisesRegex(ValueError, "density must be a finite value"):
                    bridge._build_material_props()

    def test_custom_steel_density_scales_self_weight_load_model(self):
        added = []
        gm = analyser_module.BridgeGrillageModel.__new__(analyser_module.BridgeGrillageModel)
        gm.edge_dist = 0.0
        gm.L = 30.0
        gm.girder_props = [SimpleNamespace(A=0.04)]
        fake_model = SimpleNamespace(
            Mesh_obj=SimpleNamespace(noz=[-1.5, 0.0, 1.5]),
            add_load_case=lambda lc: added.append(lc),
        )
        gm.model = fake_model
        gm.create_self_weight_load(steel_density_kN_m3=85.0)
        load_obj = added[0].load_command[0] if hasattr(added[0], "load_command") else added[0].loads_list[0] if hasattr(added[0], "loads_list") else None
        # Fallback inspection across ospgrillage LoadCase internals or create_load vertices
        with patch.object(analyser_module.og, "create_load_vertex", side_effect=lambda **kw: kw) as mock_vtx, patch.object(
            analyser_module.og, "create_load", return_value=object()
        ), patch.object(
            analyser_module.og, "create_load_case", return_value=SimpleNamespace(add_load=lambda *_: None)
        ):
            gm.create_self_weight_load(steel_density_kN_m3=85.0)
            p_custom = mock_vtx.call_args_list[0].kwargs["p"]
            mock_vtx.reset_mock()
            gm.create_self_weight_load(steel_density_kN_m3=78.5)
            p_std = mock_vtx.call_args_list[0].kwargs["p"]
        self.assertAlmostEqual(p_custom / p_std, 85.0 / 78.5, places=6)

    def test_custom_deck_density_is_passed_to_load_model(self):
        bridge = object.__new__(bridge_module.PlateGirderBridge)
        bridge.input_dict = {
            KEY_TS_DECK_THICKNESS: 250, KEY_WC_THICKNESS: 40,
            KEY_WC_DENSITY: 23.5, KEY_MATERIAL_DECK_DENSITY: 24.0,
        }
        bridge.grillage_model = SimpleNamespace(
            create_self_weight_load=lambda **kw: None,
            create_deck_load=lambda **kw: setattr(bridge, "captured_deck_load", kw),
            create_wearing_course_load=lambda **kw: None,
            create_footpath_load=lambda: None,
            create_crash_barrier_load=lambda **kw: None,
            create_railing_load=lambda **kw: None,
            create_median_load=lambda: None,
            create_dead_load_combination=lambda **kw: None,
        )
        with patch.object(bridge_module, "crash_barrier_load_from_inputs", lambda _: 0.0), patch.object(
            bridge_module, "railing_load_from_inputs", lambda _: 0.0
        ):
            bridge.add_dead_loads()
        self.assertEqual(bridge.captured_deck_load["concrete_density_kN_m3"], 24.0)

    def test_cross_bracing_and_end_diaphragm_material_mapping_and_capacity(self):
        from osdagbridge.core.utils import connect

        self.assertTrue(hasattr(connect, "resolve_component_steel_material"))
        inp = {
            KEY_GIRDER: "E 350A",
            KEY_CROSS_BRACING: "custom_steel_460_600",
            KEY_MATERIAL_CROSS_BRACING_FY: "460",
            KEY_MATERIAL_CROSS_BRACING_FU: "600",
            KEY_MATERIAL_CROSS_BRACING_E: "210",
            KEY_MATERIAL_CROSS_BRACING_DENSITY: "80.0",
            KEY_END_DIAPHRAGM: "E 410A",
            KEY_MATERIAL_END_DIAPHRAGM_FY: "410",
            KEY_MATERIAL_END_DIAPHRAGM_FU: "540",
        }
        cb_spec = connect.resolve_component_steel_material(inp, KEY_CROSS_BRACING, "material.cross_bracing")
        ed_spec = connect.resolve_component_steel_material(inp, KEY_END_DIAPHRAGM, "material.end_diaphragm")
        self.assertEqual(cb_spec["grade"], "custom_steel_460_600")
        self.assertEqual(cb_spec["fy_mpa"], 460.0)
        self.assertEqual(ed_spec["grade"], "E 410 (Fe 540)")

        captured_jobs = []

        class _FakeFuture:
            def result(self):
                return {}

        class _FakeExecutor:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def submit(self, fn, payload):
                captured_jobs.append(payload)
                return _FakeFuture()

        cb = object.__new__(CrossBracingForces)
        cb.bridge = SimpleNamespace(input_dict=inp, _lookup_material=None)
        forces = {
            "geometry": {"diagonal_length_m": 2.0, "horiz_proj_m": 1.7},
            "pairs": {"G1-G2": {"diag_tension_kN": 120.0, "diag_compression_kN": 90.0}},
        }
        with patch.object(connect, "design_pool", _FakeExecutor):
            cb.run_member_designs(forces)
        self.assertGreaterEqual(len(captured_jobs), 2)
        for job in captured_jobs:
            self.assertEqual(job["Material"], "custom_steel_460_600")
            self.assertEqual(job["Member.Material"], "custom_steel_460_600")

        # Verify actual osdag_core calculation changes yielding capacity with custom steel
        d250 = dict(connect.design_dict_tension_bolted)
        d250["Load.Axial"] = "180"
        d250["Member.Length"] = "1800"
        d460 = dict(d250)
        connect.apply_material_to_design_dict(
            d460, connect.resolve_component_steel_material(inp, KEY_CROSS_BRACING, "material.cross_bracing")
        )
        res250 = connect.run_calculation(d250)
        res460 = connect.run_calculation(d460)
        y250 = res250["Member.tension_yielding"]
        y460 = res460["Member.tension_yielding"]
        y250_val = float(y250["val"] if isinstance(y250, dict) else y250)
        y460_val = float(y460["val"] if isinstance(y460, dict) else y460)
        self.assertGreater(y460_val, y250_val)

        # Verify results table steel rows resolve per component instead of cloning girder
        steel_tbl = resolve_material_properties_steel(inp, bridge=None)
        cb_row = next(r for r in steel_tbl["rows"] if r[0] == "Cross Bracing")
        ed_row = next(r for r in steel_tbl["rows"] if r[0] == "End Diaphragm")
        self.assertEqual(cb_row[3], 460.0)
        self.assertEqual(ed_row[3], 410.0)

    def test_dynamic_dictionary_commit_removes_deleted_keys_and_preserves_identity(self):
        from osdagbridge.desktop.ui.dialogs.additional_input import additional_inputs

        shared = {"static": 1, "obsolete.G4": 4}
        identity = id(shared)
        commit = getattr(additional_inputs, "_replace_shared_input_values", None)
        self.assertIsNotNone(commit, "missing dynamic-key replacement behavior")
        commit(shared, {"static": 2})
        self.assertEqual(id(shared), identity)
        self.assertEqual(shared, {"static": 2})

        # Ensure _save_inputs itself replaces rather than `.update()`s default_input_dict
        fake_self = SimpleNamespace(
            default_input_dict={"static": 1, "member_properties.girder_details.depth.G4.M1": 1500},
            working_input_dict={"static": 1},
            findChild=lambda *args, **kwargs: None,
            update_template_page_2d_cad=SimpleNamespace(emit=lambda *_: None),
        )
        with patch.object(additional_inputs, "CustomMessageBox", return_value=SimpleNamespace(exec=lambda: None)):
            additional_inputs.AdditionalInputs._save_inputs(fake_self)
        self.assertNotIn("member_properties.girder_details.depth.G4.M1", fake_self.default_input_dict)

    def test_optimized_30_32_30_transition_clears_stale_fields_and_marks_dirty(self):
        from osdagbridge.desktop.ui.docks.input_dock import InputDock

        class _FakeDock:
            is_require_field_changed = False
            def _is_require_field(self, key):
                return key == KEY_SPAN
            class input_widget:
                @staticmethod
                def findChild(*args):
                    return None
            def _update_input_dict(self, key, val):
                self._d[key] = val
            validator = SimpleNamespace(validate_basic_inputs=lambda k, d: None)
            input_value_changed = SimpleNamespace(emit=lambda: None)

        fake_dock = _FakeDock()
        fake_dock._d = {KEY_SPAN: "30"}
        fake_dock.parent = SimpleNamespace(input_dict=fake_dock._d)
        InputDock._on_field_editing(fake_dock, "32", KEY_SPAN)
        self.assertTrue(fake_dock.is_require_field_changed)

        d = {
            KEY_SPAN: 30.0,
            KEY_CARRIAGEWAY_WIDTH: 4.25,
            KEY_INCLUDE_MEDIAN: "No",
            KEY_FOOTPATH: "None",
            KEY_SKEW_ANGLE: 0.0,
            KEY_DESIGN_MODE: "Optimized",
            KEY_GIRDER: "E 350A",
            KEY_CROSS_BRACING: "E 350A",
            KEY_END_DIAPHRAGM: "E 350A",
            KEY_DECK_CONCRETE_GRADE_BASIC: "M40",
        }
        defaults_module.solve_extend_basic_input_dict(d)
        snap_30_a = {
            "depth": d[f"{KEY_MP_GIRDER_DEPTH}.G1.M1"],
            "area": d[f"{KEY_MP_GIRDER_SECTIONAL_AREA}.G1.M1"],
            "seg_end": d[f"{KEY_MP_GD_SEGMENT_TABLE}.G1"][0]["end"],
            "total_span": d.get(KEY_MP_GD_TOTAL_SPAN),
            "stiff_sp": d[f"{KEY_MP_STIFFENER_INTERMEDIATE_SPACING}.G1.M1"],
            "stiff_bo": d[f"{KEY_MP_STIFFENER_BEARING_OUTSTAND}.G1.M1"],
            "cb_sp": d[f"{KEY_MP_CB_SPACING}.G1G2.B1M1"],
        }
        d[KEY_SPAN] = 32.0
        defaults_module.solve_extend_basic_input_dict(d)
        self.assertEqual(d[f"{KEY_MP_GD_SEGMENT_TABLE}.G1"][0]["end"], 32.0)
        self.assertEqual(d.get(KEY_MP_GD_TOTAL_SPAN), 32.0)
        self.assertNotEqual(d[f"{KEY_MP_GIRDER_DEPTH}.G1.M1"], snap_30_a["depth"])

        d[KEY_SPAN] = 30.0
        defaults_module.solve_extend_basic_input_dict(d)
        snap_30_b = {
            "depth": d[f"{KEY_MP_GIRDER_DEPTH}.G1.M1"],
            "area": d[f"{KEY_MP_GIRDER_SECTIONAL_AREA}.G1.M1"],
            "seg_end": d[f"{KEY_MP_GD_SEGMENT_TABLE}.G1"][0]["end"],
            "total_span": d.get(KEY_MP_GD_TOTAL_SPAN),
            "stiff_sp": d[f"{KEY_MP_STIFFENER_INTERMEDIATE_SPACING}.G1.M1"],
            "stiff_bo": d[f"{KEY_MP_STIFFENER_BEARING_OUTSTAND}.G1.M1"],
            "cb_sp": d[f"{KEY_MP_CB_SPACING}.G1G2.B1M1"],
        }
        self.assertEqual(snap_30_a, snap_30_b)

    def test_shear_modulus_and_poisson_preserves_precision(self):
        dialog = MaterialPropertiesDialog(read_only=False, member=KEY_GIRDER)
        widget = dialog.field_inputs[KEY_MATERIAL_GIRDER_G]
        nu_widget = dialog.field_inputs[KEY_MATERIAL_GIRDER_POISSON]
        self.assertEqual(widget.validator().decimals(), 3)
        self.assertGreaterEqual(nu_widget.validator().decimals(), 2)
        widget.setText("76.923")
        nu_widget.setText("0.28")
        dialog._save_form()
        self.assertEqual(dialog.form_data["fields"][KEY_MATERIAL_GIRDER_G], "76.923")
        dialog.form_data["fields"][KEY_MATERIAL_GIRDER_G] = "76.923"
        dialog.form_data["fields"][KEY_MATERIAL_GIRDER_POISSON] = "0.28"
        dialog._populate_fields()
        self.assertEqual(widget.text(), "76.923")
        self.assertEqual(nu_widget.text(), "0.28")
        dialog.close()

    def test_captioned_longtables_start_a_caption_row_break_across_all_chapters(self):
        repo = Path(os.environ.get("OSDAG_TEST_REPO", Path(__file__).parents[2]))
        checked = 0
        for p in sorted((repo / "src/osdagbridge/core/reports").glob("chap*.py")):
            text = p.read_text()
            for m in re.finditer(r"\\begin\{longtable\}.*?\\end\{longtable\}", text, re.S):
                blk = m.group(0)
                cap = re.search(r"\\caption\{([^\n]+)", blk)
                if not cap:
                    continue
                checked += 1
                after = blk[cap.end():cap.end() + 40]
                has_break = "\\\\" in cap.group(1) or after.lstrip().startswith("\\\\")
                self.assertTrue(has_break, f"{p.name}: missing \\\\ after caption {cap.group(1)!r}")
        self.assertGreaterEqual(checked, 40)

    def test_cad_viewport_refresh_api_and_show_ordering(self):
        from osdagbridge.desktop.ui.cad_3d import CAD3DWindow
        from osdagbridge.desktop.ui import template_page
        import inspect

        self.assertTrue(hasattr(CAD3DWindow, "refresh_viewport"))
        src = inspect.getsource(template_page.CustomWindow._on_design_done)
        self.assertLess(
            src.index("cad_3d_view_toggle(force_show=True)"),
            src.index("render_3d_cad("),
            "3D view must be shown/sized before render_3d_cad()",
        )

    def test_osi_validator_rejects_nonfinite_material_and_geometry_values(self):
        from osdagbridge.core.utils.osi_validator import validate_osi_inputs

        for val in (float("nan"), float("inf"), "NaN", "Infinity", "-inf", "1e999"):
            with self.subTest(val=val):
                res = validate_osi_inputs(
                    {KEY_SPAN: 30.0, KEY_MATERIAL_GIRDER_E: val}
                )
                self.assertFalse(res.is_valid)
                self.assertTrue(any("finite" in err.lower() for err in res.errors))

    def test_bug13_build_girders_and_plot_alignment_multi_config(self):
        """BUG-13: edge_dist inference, EB1/G1..Gn/EB2 naming, plot & cache 1-to-1 alignment."""
        import numpy as np
        import xarray as xr
        from types import SimpleNamespace
        from osdagbridge.core.bridge_types.plate_girder.analysis_results import (
            PlateGirderAnalysisResults,
        )
        from osdagbridge.core.bridge_types.plate_girder import plot_generator
        from osdagbridge.core.bridge_types.plate_girder.results_data import (
            build_load_effects_cache,
        )

        configs = [
            (3, 1.5, ["EB1", "G1", "G2", "G3", "EB2"], [11.0, 28.0, 24.0, 29.0, 12.0], 5.0),
            (4, 1.5, ["EB1", "G1", "G2", "G3", "G4", "EB2"], [10.0, 27.0, 22.0, 23.0, 31.0, 11.0], -5.0),
            (3, 0.0, ["G1", "G2", "G3"], [28.0, 24.0, 29.0], 5.0),
            (4, 0.0, ["G1", "G2", "G3", "G4"], [27.0, 22.0, 23.0, 31.0], -5.0),
        ]

        for n_main, edge_dist, expected_keys, line_shears_kn, skew_deg in configs:
            with self.subTest(n_main=n_main, edge_dist=edge_dist, skew_deg=skew_deg):
                n_lines = len(expected_keys)
                nodes = {}
                elements = {}
                adj = {}
                eid = 1
                nid = 1
                line_elems = []
                for li in range(n_lines):
                    z = float(li * 2.0)
                    x_shift = z * np.tan(np.deg2rad(skew_deg))
                    n_start, n_mid, n_end = nid, nid + 1, nid + 2
                    nid += 3
                    nodes[n_start] = (x_shift, 0.0, z)
                    nodes[n_mid] = (15.0 + x_shift, 0.0, z)
                    nodes[n_end] = (30.0 + x_shift, 0.0, z)
                    e1, e2 = eid, eid + 1
                    eid += 2
                    elements[e1] = (n_start, n_mid)
                    elements[e2] = (n_mid, n_end)
                    adj.setdefault(n_start, []).append(n_mid)
                    adj.setdefault(n_mid, []).extend([n_start, n_end])
                    adj.setdefault(n_end, []).append(n_mid)
                    line_elems.append([e1, e2])

                all_eids = [e for grp in line_elems for e in grp]
                comps = ["Vy_i", "Vy_j", "Mz_i", "Mz_j"]
                data = np.zeros((1, len(all_eids), len(comps)), dtype=float)
                for li, grp in enumerate(line_elems):
                    vy_n = line_shears_kn[li] * 1000.0
                    for e in grp:
                        idx = all_eids.index(e)
                        data[0, idx, 0] = vy_n
                        data[0, idx, 1] = -vy_n
                        data[0, idx, 2] = vy_n * 5.0
                        data[0, idx, 3] = vy_n * 5.0

                ds = xr.Dataset(
                    {"forces": (("Loadcase", "Element", "Component"), data)},
                    coords={"Loadcase": ["SW"], "Element": all_eids, "Component": comps},
                )
                fake_bridge = SimpleNamespace(edge_dist=edge_dist, model=None)
                rh = PlateGirderAnalysisResults(dataset=ds, bridge=fake_bridge)
                rh.build_grillage_connectivity = lambda: (nodes, elements, adj)
                rh.classify_loadcases = lambda: {
                    "all": ["SW"],
                    "dead": ["SW"],
                    "vehicle_static": [],
                    "vehicle_moving": [],
                }

                self.assertAlmostEqual(rh.edge_dist, edge_dist, places=6)
                g_map, _ = rh.build_girders(verbose=False)
                self.assertEqual(list(g_map.keys()), expected_keys)

                # Explicit edge_dist must produce identical EB1/G1..Gn/EB2 naming (no G2..G(n+1) shift)
                rh_exp = PlateGirderAnalysisResults(dataset=ds, bridge=fake_bridge, edge_dist=edge_dist)
                rh_exp.build_grillage_connectivity = lambda: (nodes, elements, adj)
                g_map_exp, _ = rh_exp.build_girders(verbose=False)
                self.assertEqual(list(g_map_exp.keys()), expected_keys)

                # Verify 1-to-1 element identity with plot_generator._find_girders
                plot_girders = list(plot_generator._find_girders(nodes, elements).items())
                n_plot = len(plot_girders)
                plot_main_elems = {}
                for i, (_z, elems) in enumerate(plot_girders):
                    is_eb = edge_dist > 0 and (i == 0 or i == n_plot - 1)
                    if is_eb:
                        continue
                    g_label = f"G{i}" if edge_dist > 0 else f"G{i + 1}"
                    plot_main_elems[g_label] = elems

                expected_main = [f"G{k}" for k in range(1, n_main + 1)]
                self.assertEqual(list(plot_main_elems.keys()), expected_main)
                for g_label in expected_main:
                    self.assertEqual(g_map[g_label]["elements"], plot_main_elems[g_label])

                # Verify load_effects_cache maps main girders G1..Gn to exact shears
                cache = build_load_effects_cache(rh)
                self.assertEqual(list(cache.keys()), expected_main)
                expected_main_shears = (
                    line_shears_kn[1:-1] if edge_dist > 0 else line_shears_kn
                )
                for g_label, exp_vy in zip(expected_main, expected_main_shears):
                    self.assertAlmostEqual(cache[g_label]["SW"]["Vy_max"], exp_vy, places=3)

    def test_bug13_edge_dist_dcr_config_and_steel_dialog_wiring(self):
        """BUG-13: PlateGirderBridge edge_dist propagation, BridgeConfig.n_girders, SteelDesign combo."""
        import inspect
        from types import SimpleNamespace
        from osdagbridge.core.bridge_types.plate_girder.plategirderbridge import (
            PlateGirderBridge,
        )
        from osdagbridge.core.bridge_types.plate_girder import designer
        from osdagbridge.core.bridge_types.plate_girder.dto import (
            GrillageGeometry,
            DeckLayoutProperties,
        )
        from osdagbridge.desktop.ui.dialogs import steel_design
        from osdagbridge.core.utils.common import (
            KEY_TS_DECK_OVERHANG,
            KEY_TS_NO_OF_GIRDERS,
            KEY_TS_DECK_THICKNESS,
            KEY_DS_BOTTOM_CLEAR_COVER,
            KEY_SC_LEFT_SUPPORT,
            KEY_SC_RIGHT_SUPPORT,
        )

        # 1) PlateGirderBridge.get_edge_dist() respects grillage_model.edge_dist including explicit 0.0
        b = PlateGirderBridge.__new__(PlateGirderBridge)
        b.grillage_model = SimpleNamespace(edge_dist=1.5)
        b.grillage_geometry = SimpleNamespace(edge_dist=1.5)
        b.output_dict = {}
        b.input_dict = {KEY_TS_DECK_OVERHANG: 0.0}
        self.assertAlmostEqual(b.get_edge_dist(), 1.5)

        b.grillage_model = SimpleNamespace(edge_dist=0.0)
        b.output_dict = {KEY_TS_DECK_OVERHANG: 1.5}
        self.assertAlmostEqual(b.get_edge_dist(), 0.0)

        # 2) get_result_handler() and _run_dcr_checks() propagate edge_dist
        b.grillage_model = SimpleNamespace(edge_dist=1.25, model=None)
        b.get_results_dataset = lambda: object()
        rh = b.get_result_handler()
        self.assertIsNotNone(rh)
        self.assertAlmostEqual(rh.edge_dist, 1.25)

        dcr_src = inspect.getsource(PlateGirderBridge._run_dcr_checks)
        self.assertIn("edge_dist=self.get_edge_dist()", dcr_src)

        # 3) BridgeConfig.from_plate_girder_bridge sets GeometryConfig.n_girders = n_main (not n_l)
        cfg_src = inspect.getsource(designer.BridgeConfig.from_plate_girder_bridge)
        self.assertNotIn("n_girders = geom.n_l", cfg_src)
        self.assertIn("n_girders = n_main_girders", cfg_src)

        # 4) SteelDesign._populate_member_combo filters EB* without slicing off G1/Gn when edge_dist==0
        combo_src = inspect.getsource(steel_design.SteelDesign._populate_member_combo)
        self.assertNotIn("keys[1:-1]", combo_src)
        self.assertIn('startswith("EB")', combo_src)

    def test_bug14_seeders_preserve_user_values_and_store_area_in_m2(self):
        """BUG-14: re-seeding on Design Mode change must not overwrite edited values or change units."""
        from osdagbridge.core.bridge_types.plate_girder import defaults as dflt
        from osdagbridge.core.utils.common import (
            KEY_TS_DECK_THICKNESS, KEY_WC_DENSITY, KEY_CB_AREA, KEY_MD_AREA,
            KEY_INCLUDE_MEDIAN, KEY_DO_LOAD_CYCLES, KEY_DO_GAMMA_M0, KEY_RL_WIDTH,
        )

        d = {
            KEY_TS_DECK_THICKNESS: 200, KEY_WC_DENSITY: 25.0, KEY_RL_WIDTH: 0.275,
            KEY_CB_AREA: 0.3023, KEY_DO_LOAD_CYCLES: 100000, KEY_DO_GAMMA_M0: 1.0,
            KEY_INCLUDE_MEDIAN: "Yes",
        }
        dflt._update_typical_section_defaults(d)
        dflt._update_design_options_cont_defaults(d)
        self.assertEqual(d[KEY_TS_DECK_THICKNESS], 200)
        self.assertEqual(d[KEY_WC_DENSITY], 25.0)
        self.assertEqual(d[KEY_RL_WIDTH], 0.275)
        self.assertEqual(d[KEY_CB_AREA], 0.3023)
        self.assertEqual(d[KEY_DO_LOAD_CYCLES], 100000)
        self.assertEqual(d[KEY_DO_GAMMA_M0], 1.0)

        fresh = {KEY_INCLUDE_MEDIAN: "Yes"}
        dflt._update_typical_section_defaults(fresh)
        self.assertEqual(fresh[KEY_TS_DECK_THICKNESS], 250.0)          # first seed unchanged
        self.assertLess(float(fresh[KEY_CB_AREA]), 5.0, "crash-barrier area must be stored in m^2")
        self.assertGreater(float(fresh[KEY_CB_AREA]), 0.01)
        self.assertLess(float(fresh[KEY_MD_AREA]), 5.0, "median area must be stored in m^2")

    def test_bug14_cross_bracing_count_reduction_prunes_stale_member_keys(self):
        """BUG-14 / ADV-003: reducing brace count 29 -> 3 must delete B*M4..M29 keys."""
        from osdagbridge.core.bridge_types.plate_girder.defaults import extend_cb_dynamic_keys
        from osdagbridge.core.utils.common import KEY_SPAN, KEY_MP_CB_TYPE
        import re

        sec_defaults = {
            "type": "X-Bracing",
            "bracing_section_type": "Double Angle (Long Leg)",
            "bracing_section_designation": "IS 100 x 100 x 10",
            "top_chord": "Yes",
            "top_chord_section_type": "Double Angle (Long Leg)",
            "top_chord_section_desig": "IS 100 x 100 x 10",
            "bottom_chord": "Yes",
            "bottom_chord_section_type": "Double Angle (Long Leg)",
            "bottom_chord_section_desig": "IS 100 x 100 x 10",
        }
        d = {KEY_SPAN: 30.0}
        extend_cb_dynamic_keys(d, 3, 29, section_defaults=sec_defaults)
        self.assertTrue(any(k.endswith(".B1M29") for k in d))
        extend_cb_dynamic_keys(d, 3, 3, section_defaults=sec_defaults)
        stale = [k for k in d if re.search(r"\.G\d+G\d+\.B\d+M(\d+)$", k) and int(re.search(r"M(\d+)$", k).group(1)) > 3]
        self.assertEqual(stale, [])
        self.assertIn(KEY_MP_CB_TYPE + ".G1G2.B1M3", d)


if __name__ == "__main__":
    unittest.main(verbosity=2)
