"""Focused checks for Phase 15 candidate changes."""

import copy
import unittest
from collections import namedtuple
from types import SimpleNamespace

from osdagbridge.core.bridge_types.plate_girder.defaults import (
    BASIC_INPUT_DICT,
    solve_extend_basic_input_dict,
)
from osdagbridge.core.reports.executive_summary import executive_summary
from osdagbridge.core.utils.common import (
    KEY_CARRIAGEWAY_WIDTH,
    KEY_FOOTPATH,
    KEY_RL_WIDTH,
    KEY_SPAN,
    KEY_TS_FOOTPATH_WIDTH,
    KEY_TS_NO_OF_GIRDERS,
)
from osdagbridge.desktop.ui.dialogs.generate_results_values_builder import (
    resolve_permanent_load_summary,
    resolve_governing_shear_connector_spacing,
    resolve_shear_connector_capacity,
)
from ospgrillage.load import (
    CompoundLoad,
    LineLoading,
    LoadCase,
    LoadVertex,
    NodalLoad,
    PatchLoading,
    PointLoad,
)
from ospgrillage.osp_grillage import OspGrillage


class Phase15RegressionTests(unittest.TestCase):
    def test_no_footpath_has_zero_effective_width_and_baseline_load(self):
        inputs = copy.deepcopy(BASIC_INPUT_DICT)
        inputs.update({KEY_SPAN: 30.0, KEY_CARRIAGEWAY_WIDTH: 7.5, KEY_FOOTPATH: "None"})

        solve_extend_basic_input_dict(inputs)

        self.assertEqual(inputs[KEY_TS_FOOTPATH_WIDTH], 0.0)
        self.assertEqual(inputs[KEY_RL_WIDTH], 0.0)
        self.assertEqual(resolve_permanent_load_summary(inputs)["rows"], [[22.9]])

        custom = copy.deepcopy(BASIC_INPUT_DICT)
        custom.update({KEY_SPAN: 30.0, KEY_CARRIAGEWAY_WIDTH: 7.5,
                       KEY_FOOTPATH: "None", KEY_RL_WIDTH: 0.275})
        solve_extend_basic_input_dict(custom)
        self.assertEqual(custom[KEY_RL_WIDTH], 0.275)
        self.assertEqual(custom[KEY_TS_FOOTPATH_WIDTH], 0.0)
        self.assertEqual(resolve_permanent_load_summary(custom)["rows"], [[22.9]])

    def test_nodal_combination_factor_changes_command_only(self):
        forces = namedtuple("Forces", "Fx Fy Fz Mx My Mz")
        source = NodalLoad(7, forces(1.0, 2.0, 3.0, 4.0, 5.0, 6.0))
        case = LoadCase("factored")
        case.add_load(source, load_factor=1.5)

        model = object.__new__(OspGrillage)
        commands = model._distribute_load_types_to_model(case)

        self.assertEqual(commands, [("load", (7, 1.5, 3.0, 4.5, 6.0, 7.5, 9.0), {})])
        self.assertEqual(case.load_groups[0]["load"].Fz, 3.0)
        self.assertEqual(source.Fz, 3.0)

    def test_shear_connector_table_converts_concrete_gpa_to_mpa(self):
        material = SimpleNamespace(concrete_prop=SimpleNamespace(fck=40.0, Ecm=33.0))
        bridge = SimpleNamespace(output_dict={}, _build_material_props=lambda: material)

        table = resolve_shear_connector_capacity({KEY_TS_NO_OF_GIRDERS: 1}, bridge)

        self.assertEqual(table["rows"][0][5], 33000.0)
        self.assertIn("(MPa)", table["columns"][5])

    def test_compound_factor_scales_point_line_and_patch_magnitudes(self):
        v = LoadVertex
        point = PointLoad(point1=v(0.0, 0.0, 0.0, 10.0))
        line = LineLoading(point1=v(0.0, 0.0, 0.0, 3.0), point2=v(2.0, 0.0, 0.0, 3.0))
        patch = PatchLoading(
            point1=v(0.0, 0.0, 0.0, 2.0),
            point2=v(2.0, 0.0, 0.0, 2.0),
            point3=v(2.0, 0.0, 1.0, 2.0),
            point4=v(0.0, 0.0, 1.0, 2.0),
        )
        group = CompoundLoad("loads")
        group.compound_load_obj_list = [point, line, patch]

        group.apply_load_factor(1.75)

        self.assertEqual(point.load_point_1.p, 17.5)
        self.assertEqual([line.load_point_1.p, line.load_point_2.p], [5.25, 5.25])
        self.assertEqual(line.line_end_point.p, 5.25)
        self.assertEqual([p.p for p in patch.point_list[:4]], [3.5] * 4)

    def test_executive_summary_reports_failed_deck_and_unassessed_members(self):
        output = {
            "design_results": {
                "overall_status": "PASS",
                "per_girder": {"G1": {"checks": [
                    {"name": "ULS Flexure", "status": "PASS", "dcr": 0.5},
                ]}},
            },
            "deck_design_results": {"ur_bot_crack": 1.17},
        }

        report = executive_summary({}, output, {})

        self.assertIn("Overall Design Status} & Fail (Deck slab)", report)
        self.assertIn("Girder design PASS", report)
        self.assertIn("Deck design FAIL", report)
        self.assertIn("Cross bracing design Not assessed", report)
        self.assertIn("End Diaphragm design Not assessed", report)

    def test_executive_summary_does_not_hide_backend_failure(self):
        output = {"design_results": {"overall_status": "FAIL", "per_girder": {}}}

        report = executive_summary({}, output, {})

        self.assertIn("Overall Design Status} & Fail (Backend design status)", report)
        self.assertIn("Girder design Not assessed", report)

    def test_shear_connector_spacing_table_checks_governing_and_minimum(self):
        design = {
            "stud_spacing_provided_mm": 100.0,
            "stud_spacing_governing_mm": 60.0,
            "stud_spacing_max_mm": 300.0,
            "stud_spacing_min_mm": 75.0,
        }
        bridge = SimpleNamespace(output_dict={"design_results": design})
        inputs = {KEY_TS_NO_OF_GIRDERS: 1}

        table = resolve_governing_shear_connector_spacing(inputs, bridge)
        self.assertEqual(table["rows"][0][-1], "FAIL")
        self.assertEqual(table["columns"][-2], "Provided Spacing (mm)")
        self.assertEqual(table["rows"][0][-2], 100.0)
        design["stud_spacing_governing_mm"] = 120.0
        self.assertEqual(resolve_governing_shear_connector_spacing(inputs, bridge)["rows"][0][-1], "PASS")
        design["stud_spacing_provided_mm"] = 50.0
        self.assertEqual(resolve_governing_shear_connector_spacing(inputs, bridge)["rows"][0][-1], "FAIL")


if __name__ == "__main__":
    unittest.main()
