"""Build the 85 kN/m³ diagnostic with the normal CAD and plot capture functions."""
import json
from pathlib import Path
from unittest.mock import patch
from phase22_cad import cad_views
from run_phase21_report import tectonic_compat, ReportRequest, ReportOptions, ReportMetadata
from run_phase21_engineering_matrix import PlateGirderBridge, build_inputs, CASES
from osdagbridge.core.bridge_types.plate_girder.plot_generator import capture_report_figures

def main():
    bridge = PlateGirderBridge()
    bridge.set_input(build_inputs(CASES[1]))
    bridge.design()
    out = Path("evidence/phase22/pdf")
    out.mkdir(parents=True, exist_ok=True)
    figures = cad_views(bridge.get_3d_cad_parameters())
    figures.update(capture_report_figures(bridge.get_result_handler().ds, *bridge.get_nodes_members(),
                                          edge_dist=bridge.get_edge_dist()))
    for key, data in figures.items():
        (out / (key + ".png")).write_bytes(data)
    meta = ReportMetadata("Phase 22 verification", "Delhi", "Screening project", "Diagnostic fixture", "Local validation",
                          report_date="2026-11-23", additional_comments=(
                              ""
                              "Positive-overhang EB1/EB2 stiffness remains unvalidated. The tested skewed cases "
                              "applied 1.49% less steel self-weight than expected. Positive-overhang and skewed "
                              "designs lack engineering acceptance. Native CAD screenshot capture failed locally. "
                              "The geometry figures use offline projections of the generated case solids."))
    request = ReportRequest(meta, ReportOptions(["loads", "analysis", "design_checks"], True, True, True),
                            str(out), "diagnostic")
    # Compile a fresh file in the report generator's own temporary directory.
    (out / "diagnostic.pdf").unlink(missing_ok=True)
    with patch("subprocess.run", tectonic_compat):
        result = bridge.generate_design_report(request, {"figure_data": figures})
    if not result.pdf_path:
        raise RuntimeError("PDF compilation failed")
    (out / "backend.json").write_text(json.dumps(dict(rho=bridge.material_props.steel_prop.rho,
        design=bridge.design_results, figures=list(figures), envelope=bridge._lc_summary["Envelope ULS"]),default=str,indent=2))



if __name__ == "__main__":
    main()
