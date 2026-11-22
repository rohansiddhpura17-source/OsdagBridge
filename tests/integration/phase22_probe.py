"""Run one fresh Phase 21 fixture and record inverse-map and SW diagnostics."""
import json
import sys
import warnings
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import numpy as np
from ospgrillage.osp_grillage import OspGrillage
from scipy.optimize import _minpack_py
from run_phase21_engineering_matrix import CASES, PlateGirderBridge, build_inputs


def probe(index):
    case = CASES[index]
    bridge = PlateGirderBridge()
    bridge.set_input(build_inputs(case))
    calls = []
    original = _minpack_py._root_hybr

    def trace(*args, **kw):
        result = original(*args, **kw)
        calls.append((int(result.status), int(result.nfev),
                      float(np.linalg.norm(result.fun, ord=np.inf)) / 4))
        return result

    sw_commands = []
    original_add = OspGrillage.add_load_case

    def record_load(model, load_case, *args, **kwargs):
        result = original_add(model, load_case, *args, **kwargs)
        if getattr(load_case, "name", None) == "SW":
            sw_commands.extend(model.load_case_list[-1]["load_command"])
        return result

    with warnings.catch_warnings(record=True) as caught, patch.object(_minpack_py, "_root_hybr", trace), patch.object(OspGrillage, "add_load_case", record_load):
        warnings.simplefilter("always")
        bridge.design()
    handler = bridge.get_result_handler()
    lines, _ = handler.build_girders(False)
    ds = handler.ds.sel(Loadcase="SW")
    forces = ds.forces.sel(Component=["Mz_i", "Mz_j"])
    moments = {k: float(abs(forces.sel(Element=v["elements"])).max()) / 1000 for k,v in lines.items()}
    rx = ds.reactions.sel(ReactionComponent="Fy") / 1000
    ends = {k: [float(rx.sel(Node=v[end])) for end in ("start","end")] for k,v in lines.items()}
    density = float(bridge.material_props.steel_prop.rho)
    weights = [p.A * density / 1000 for p in bridge.grillage_model.steel_girder_props]
    length = bridge.grillage_geometry.L
    expected = sum(weights) * length
    result = dict(case=case, rho=density, physical=list(bridge.design_results["per_girder"]),
                  sw_line_kN_m=weights, expected_sw_kN=expected, sw_reactions_kN=ends,
                  sum_Fy_kN=float(rx.sum()), residual_kN=abs(float(rx.sum()))-expected,
                  report_sw_reactions=bridge._reaction_summary.get("SW"),
                  sw_peak_kNm=moments, simple_span_kNm=[w*length**2/8 for w in weights],
                  envelope=bridge._lc_summary.get("Envelope ULS"),
                  warnings=dict(Counter(f"{w.category.__name__}: {w.message}" for w in caught)),
                  hybr={})
    if not sw_commands or any(name != "load" for name, _, _ in sw_commands):
        raise AssertionError("Expected SW nodal load commands")
    applied = sum(args[2] for _, args, _ in sw_commands) / 1000
    result["applied_Fy_kN"] = applied
    result["force_balance_kN"] = applied + float(rx.sum())
    coords, _, _ = handler.build_grillage_connectivity()
    applied_mz = sum(coords[a[0]][0]*a[2] + a[6] for _,a,_ in sw_commands) / 1000
    support_mz = sum(coords[int(n)][0]*float(rx.sel(Node=n)) for n in rx.Node.values)
    support_mz += float(ds.reactions.sel(ReactionComponent="Mz").sum()) / 1000
    result["moment_balance_about_z_kNm"] = applied_mz + support_mz
    for status in sorted(set(t[0] for t in calls)):
        subset=[r for r in calls if r[0]==status]
        result["hybr"][status]=dict(count=len(subset),nfev_range=[min(r[1] for r in subset),max(r[1] for r in subset)], max_residual_m=max(r[2] for r in subset))
    bridge.memory.release()
    return result


if __name__ == "__main__":
    Path(sys.argv[2]).write_text(json.dumps(probe(int(sys.argv[1])),indent=2,allow_nan=False))
