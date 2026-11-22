"""Generate a real backend report through the app pipeline using Tectonic."""
from __future__ import annotations

import json
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

from osdagbridge.core.bridge_types.plate_girder.plategirderbridge import PlateGirderBridge
from osdagbridge.core.reports.report_generator import (
    ReportMetadata,
    ReportOptions,
    ReportRequest,
)


TECTONIC = os.environ.get("TECTONIC") or shutil.which("tectonic") or "tectonic"
ORIGINAL_RUN = subprocess.run
MATRIX_SPEC = importlib.util.spec_from_file_location(
    "phase21_engineering_matrix", Path(__file__).with_name("run_phase21_engineering_matrix.py")
)
MATRIX = importlib.util.module_from_spec(MATRIX_SPEC)
MATRIX_SPEC.loader.exec_module(MATRIX)


def tectonic_compat(command, **kwargs):
    """Translate the report generator's pdflatex invocation to real Tectonic."""
    if isinstance(command, (list, tuple)) and len(command) == 3 and command[1] == "-interaction=nonstopmode":
        tex_file = command[2]
        tectonic_command = [TECTONIC, "--color", "never", "-o", kwargs["cwd"], tex_file]
        return ORIGINAL_RUN(tectonic_command, **kwargs)
    return ORIGINAL_RUN(command, **kwargs)


def main() -> int:
    outdir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("evidence/generated-phase21-report")
    outdir.mkdir(parents=True, exist_ok=True)
    case = next(item for item in MATRIX.CASES if item["name"] == "custom_3g_0deg_overhang_85")
    bridge = PlateGirderBridge()
    bridge.set_input(MATRIX.build_inputs(case))
    bridge.design()

    request = ReportRequest(
        metadata=ReportMetadata(
            project_name="Phase 21 density regression",
            project_location="Local solver verification",
            designer="FOSSEE OsdagBridge QA",
            client="Regression fixture",
            company="FOSSEE IIT Bombay",
            report_date="2026-11-23",
        ),
        options=ReportOptions(
            sections=["loads", "analysis", "design_checks"],
            include_figures=False,
            include_toc=True,
            include_pdf=True,
        ),
        output_dir=str(outdir),
        file_stem="phase21-density-85",
    )
    subprocess.run = tectonic_compat
    try:
        report_result = bridge.generate_design_report(request, None)
    finally:
        subprocess.run = ORIGINAL_RUN

    result = {
        "pdf_path": report_result.pdf_path,
        "tex_path": report_result.tex_path,
        "pdf_exists": bool(report_result.pdf_path and Path(report_result.pdf_path).is_file()),
        "tex_exists": bool(report_result.tex_path and Path(report_result.tex_path).is_file()),
        "compiler": TECTONIC,
        "backend_density_N_m3": float(bridge.material_props.steel_prop.rho),
        "backend_design_girders": int(bridge.design_results.get("n_girders", -1)),
        "report_per_girder_keys": list(bridge.design_results.get("per_girder", {})),
        "status": "completed" if report_result.pdf_path and Path(report_result.pdf_path).is_file() else "failed",
    }
    Path(outdir, "phase21-report-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    bridge.memory.release()
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
