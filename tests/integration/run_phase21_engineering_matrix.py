"""Run real OpenSees designs for the Phase 21 density/girder review.

Execute from the repository root with the Osdag Python 3.12 environment and
``PYTHONPATH=src``. The script uses the production bridge backend and solver;
it writes only into the supplied Phase 21 evidence directory.
"""
from __future__ import annotations

import json
import sys
import traceback
import warnings
from copy import deepcopy
from pathlib import Path

from osdagbridge.core.bridge_types.plate_girder.defaults import (
    BASIC_INPUT_DICT,
    solve_extend_basic_input_dict,
)
from osdagbridge.core.bridge_types.plate_girder.plategirderbridge import PlateGirderBridge
from osdagbridge.core.utils.common import (
    KEY_CARRIAGEWAY_WIDTH,
    KEY_GIRDER,
    KEY_MATERIAL_DECK_DENSITY,
    KEY_MATERIAL_DECK_ECM,
    KEY_MATERIAL_DECK_FCK,
    KEY_MATERIAL_DECK_FCTM,
    KEY_MATERIAL_GIRDER_DENSITY,
    KEY_MATERIAL_GIRDER_E,
    KEY_MATERIAL_GIRDER_FU,
    KEY_MATERIAL_GIRDER_FY,
    KEY_MATERIAL_GIRDER_G,
    KEY_MATERIAL_GIRDER_POISSON,
    KEY_PROJECT_LOCATION,
    KEY_SKEW_ANGLE,
    KEY_SPAN,
    KEY_TS_DECK_OVERHANG,
    KEY_TS_GIRDER_SPACING,
    KEY_TS_NO_OF_GIRDERS,
    KEY_TS_OVERALL_WIDTH,
)


LOCATION = {
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

CASES = (
    {"name": "default_3g_0deg_overhang", "girders": 3, "skew": 0.0, "density": 78.5},
    {"name": "custom_3g_0deg_overhang_85", "girders": 3, "skew": 0.0, "density": 85.0, "custom": True},
    {"name": "default_4g_0deg_overhang", "girders": 4, "skew": 0.0, "density": 78.5},
    {"name": "default_3g_plus5deg_overhang", "girders": 3, "skew": 5.0, "density": 78.5},
    {"name": "default_4g_minus5deg_overhang", "girders": 4, "skew": -5.0, "density": 78.5},
    {"name": "default_3g_0deg_zero_overhang", "girders": 3, "skew": 0.0, "density": 78.5, "zero_overhang": True},
)


def build_inputs(case: dict) -> dict:
    data = deepcopy(BASIC_INPUT_DICT)
    data.update({
        KEY_SPAN: 25.0,
        KEY_CARRIAGEWAY_WIDTH: 7.5,
        KEY_PROJECT_LOCATION: deepcopy(LOCATION),
        KEY_SKEW_ANGLE: float(case["skew"]),
        KEY_TS_NO_OF_GIRDERS: int(case["girders"]),
        KEY_MATERIAL_GIRDER_DENSITY: float(case["density"]),
        KEY_MATERIAL_GIRDER_G: 76.923,
        KEY_MATERIAL_DECK_DENSITY: 25.0,
        KEY_MATERIAL_DECK_FCK: 40.0,
        KEY_MATERIAL_DECK_FCTM: 3.5,
        KEY_MATERIAL_DECK_ECM: 34.0,
    })
    if case.get("custom"):
        data.update({
            KEY_GIRDER: "custom_steel_355_500",
            KEY_MATERIAL_GIRDER_E: 210.0,
            KEY_MATERIAL_GIRDER_G: 80.769,
            KEY_MATERIAL_GIRDER_FY: 355.0,
            KEY_MATERIAL_GIRDER_FU: 500.0,
            KEY_MATERIAL_GIRDER_POISSON: 0.3,
        })
    solve_extend_basic_input_dict(data)
    if case.get("zero_overhang"):
        data[KEY_TS_DECK_OVERHANG] = 0.0
        data[KEY_TS_GIRDER_SPACING] = float(data[KEY_TS_OVERALL_WIDTH]) / (int(case["girders"]) - 1)
    return data


def run_case(case: dict) -> dict:
    bridge = PlateGirderBridge()
    inputs = build_inputs(case)
    bridge.set_input(inputs)
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        bridge.design()

    result_handler = bridge.get_result_handler()
    girder_map, _ = result_handler.build_girders(verbose=False)
    physical_names = [name for name in girder_map if name.startswith("G")]
    expected_physical = [f"G{i}" for i in range(1, int(case["girders"]) + 1)]
    expected_lines = (
        ["EB1", *expected_physical, "EB2"]
        if float(bridge.grillage_geometry.edge_dist) > 0.0
        else expected_physical
    )
    report_per_girder = list(bridge.design_results.get("per_girder", {}))
    cache_per_girder = list(getattr(bridge, "_load_effects_cache", {}))
    if (
        list(girder_map) != expected_lines
        or physical_names != expected_physical
        or int(bridge.design_results.get("n_girders", -1)) != int(case["girders"])
        or report_per_girder != expected_physical
        or cache_per_girder != expected_physical
    ):
        raise AssertionError({
            "expected_lines": expected_lines,
            "result_handler_lines": list(girder_map),
            "expected_physical": expected_physical,
            "report_per_girder": report_per_girder,
            "cache_per_girder": cache_per_girder,
            "reported_design_girders": bridge.design_results.get("n_girders"),
        })
    actual_rho = float(bridge.material_props.steel_prop.rho)
    density_kn_m3 = actual_rho / 1000.0
    main_sections = list(bridge.grillage_model.steel_girder_props)
    line_loads_n_m = [sec.A * density_kn_m3 * 1000.0 for sec in main_sections]
    expected_total_girder_weight_kN = sum(line_loads_n_m) * float(inputs[KEY_SPAN]) / 1000.0
    edge_props = bridge.grillage_model.edge_longitudinal_props
    representative = main_sections[0]
    edge_section_matches_full_girder = all(
        abs(float(getattr(edge_props, field)) - float(getattr(representative, field))) < 1e-12
        for field in ("A", "J", "Iz", "Iy", "Az", "Ay")
    )

    record = {
        "name": case["name"],
        "requested_physical_girders": int(case["girders"]),
        "reported_design_girders": int(bridge.design_results.get("n_girders", -1)),
        "result_handler_lines": list(girder_map),
        "physical_result_names": physical_names,
        "report_per_girder_names": report_per_girder,
        "load_effect_cache_girder_names": cache_per_girder,
        "model_longitudinal_lines": int(bridge.grillage_geometry.n_l),
        "edge_dist_m": float(bridge.grillage_geometry.edge_dist),
        "skew_deg": float(inputs[KEY_SKEW_ANGLE]),
        "steel_grade": str(inputs[KEY_GIRDER]),
        "steel_rho_N_m3": actual_rho,
        "steel_density_kN_m3": density_kn_m3,
        "girder_section_areas_m2": [float(sec.A) for sec in main_sections],
        "girder_self_weight_line_loads_N_m": line_loads_n_m,
        "total_applied_steel_girder_weight_kN": expected_total_girder_weight_kN,
        "edge_section_matches_full_girder": edge_section_matches_full_girder,
        "python_warnings": [str(item.message) for item in caught_warnings],
    }
    bridge.memory.release()
    return record


def main() -> int:
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("evidence/phase21_engineering_matrix.json")
    results = []
    for case in CASES:
        try:
            result = run_case(case)
            result["status"] = "completed"
            print("CASE_RESULT", json.dumps(result, sort_keys=True), flush=True)
            results.append(result)
        except Exception as exc:
            result = {"name": case["name"], "status": "failed", "error": str(exc), "traceback": traceback.format_exc()}
            print("CASE_FAILURE", json.dumps(result, sort_keys=True), flush=True)
            results.append(result)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    failures = [row for row in results if row["status"] != "completed"]
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
