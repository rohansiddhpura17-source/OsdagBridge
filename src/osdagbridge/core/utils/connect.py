import os

# Force UTF-8 encoding in all subprocesses
os.environ["PYTHONIOENCODING"] = "utf-8"

import builtins
import contextlib
import functools
import logging
import re
import sqlite3
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Dict, List


# Safe print wrapper to avoid Unicode crashes
_original_print = print

def safe_print(*args, **kwargs):
    try:
        _original_print(*args, **kwargs)
    except UnicodeEncodeError:
        pass

builtins.print = safe_print

# Reconfigure Windows terminal encoding
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    sys.stderr.reconfigure(encoding="utf-8", errors="ignore")

from osdag_core.cli import _get_output_dictionary

from osdag_core.design_type.compression_member.compression_bolted import Compression_bolted
from osdag_core.design_type.compression_member.compression_welded import Compression_welded
from osdag_core.design_type.tension_member.tension_bolted import Tension_bolted
from osdag_core.design_type.tension_member.tension_welded import Tension_welded

MODULE_CLASS_MAP = {
    "Tension Member Design - Bolted to End Gusset": Tension_bolted,
    "Tension Member Design - Welded to End Gusset": Tension_welded,
    "Struts Bolted to End Gusset": Compression_bolted,
    "Struts Welded to End Gusset": Compression_welded,
}

CUSTOM_MATERIAL_OVERRIDE_KEY = "_osdagbridge_custom_material"

_OSDAG_CORE_STEEL_GRADE_MAP = {
    "E165": "E 165 (Fe 290)",
    "E165(FE290)": "E 165 (Fe 290)",
    "E250A": "E 250 (Fe 410 W)A",
    "E250(FE410W)A": "E 250 (Fe 410 W)A",
    "E250BR": "E 250 (Fe 410 W)B",
    "E250B0": "E 250 (Fe 410 W)B",
    "E250(FE410W)B": "E 250 (Fe 410 W)B",
    "E250C": "E 250 (Fe 410 W)C",
    "E250(FE410W)C": "E 250 (Fe 410 W)C",
    "E300A": "E 300 (Fe 440)",
    "E300BR": "E 300 (Fe 440)",
    "E300B0": "E 300 (Fe 440)",
    "E300C": "E 300 (Fe 440)",
    "E300(FE440)": "E 300 (Fe 440)",
    "E350A": "E 350 (Fe 490)",
    "E350BR": "E 350 (Fe 490)",
    "E350B0": "E 350 (Fe 490)",
    "E350C": "E 350 (Fe 490)",
    "E350(FE490)": "E 350 (Fe 490)",
    "E410A": "E 410 (Fe 540)",
    "E410BR": "E 410 (Fe 540)",
    "E410B0": "E 410 (Fe 540)",
    "E410C": "E 410 (Fe 540)",
    "E410(FE540)": "E 410 (Fe 540)",
    "E450A": "E 450 (Fe 570)D",
    "E450(FE570)D": "E 450 (Fe 570)D",
    "E450BR": "E 450 (Fe 590) E",
    "E450(FE590)E": "E 450 (Fe 590) E",
}


def _norm_grade(name: Any) -> str:
    return "".join(str(name or "").upper().split())


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _lookup_osdagbridge_steel_db(grade: str) -> dict[str, float] | None:
    db_path = Path(__file__).resolve().parents[1] / "data" / "ResourceFiles" / "Intg_osdag.sqlite"
    if not db_path.exists() or not grade:
        return None
    try:
        with sqlite3.connect(str(db_path)) as conn:
            row = conn.execute(
                'SELECT "Yield Strength", "Ultimate Tensile Strength", "Modulus of Elasticity", "Poisson\'s Ratio", "Density" '
                'FROM Steel_Grade_Properties WHERE "Grade" = ?',
                (grade,),
            ).fetchone()
        if not row:
            return None
        return {
            "fy": float(row[0]),
            "fu": float(row[1]),
            "E_gpa": float(row[2]),
            "poisson": float(row[3]),
            "density_kn_m3": float(row[4]) / 1000.0 if float(row[4]) > 1000 else float(row[4]),
        }
    except Exception:
        return None


def resolve_component_steel_material(
    input_dict: Dict[str, Any] | None,
    component_key: str,
    custom_prefix: str,
    lookup_fn: Any = None,
) -> Dict[str, Any]:
    """Resolve component steel grade & mechanical properties for osdag_core members."""
    data = input_dict or {}
    raw_grade = str(data.get(component_key) or "").strip()
    active_prefix = custom_prefix
    if not raw_grade:
        raw_grade = str(data.get("material.girder") or "").strip()
        active_prefix = "material.girder"
    if not raw_grade:
        return {
            "grade": "E 250 (Fe 410 W)A",
            "source_grade": "E 250A",
            "fy_mpa": 250.0,
            "fu_mpa": 410.0,
            "e_gpa": 200.0,
            "poisson": 0.3,
            "density_kn_m3": 78.5,
            "override": None,
        }

    fy = _safe_float(data.get(f"{active_prefix}.fy"))
    fu = _safe_float(data.get(f"{active_prefix}.fu"))
    e_gpa = _safe_float(data.get(f"{active_prefix}.e"))
    poisson = _safe_float(data.get(f"{active_prefix}.poisson"))
    density = _safe_float(data.get(f"{active_prefix}.density"))

    # Fall back to custom_steel_<fy>_<fu> naming token when fields weren't materialized.
    m = re.match(r"^(?:Cus_|custom_steel_)([0-9]+(?:\.[0-9]+)?)_([0-9]+(?:\.[0-9]+)?)$", raw_grade, re.IGNORECASE)
    if m:
        if fy is None:
            fy = float(m.group(1))
        if fu is None:
            fu = float(m.group(2))

    # Optional DB lookup for standard grades (either via callback or OsdagBridge SQLite DB).
    db_vals = _lookup_osdagbridge_steel_db(raw_grade)
    if db_vals is None and callable(lookup_fn):
        try:
            db_fy = lookup_fn(raw_grade, "Yield Strength")
            db_fu = lookup_fn(raw_grade, "Ultimate Tensile Strength")
            db_e = lookup_fn(raw_grade, "Modulus of Elasticity")
            db_v = lookup_fn(raw_grade, "Poisson's Ratio")
            db_rho = lookup_fn(raw_grade, "Density")
            if db_fy is not None and db_fu is not None:
                db_vals = {
                    "fy": float(db_fy) / 1e6,
                    "fu": float(db_fu) / 1e6,
                    "E_gpa": float(db_e) / 1e9 if db_e is not None else 200.0,
                    "poisson": float(db_v) if db_v is not None else 0.3,
                    "density_kn_m3": float(db_rho) / 1000.0 if db_rho is not None else 78.5,
                }
        except Exception:
            db_vals = None

    if db_vals:
        fy = db_vals["fy"] if fy is None else fy
        fu = db_vals["fu"] if fu is None else fu
        e_gpa = db_vals["E_gpa"] if e_gpa is None else e_gpa
        poisson = db_vals["poisson"] if poisson is None else poisson
        density = db_vals["density_kn_m3"] if density is None else density

    fy = 250.0 if fy is None else float(fy)
    fu = max(fy * 1.25, 410.0) if fu is None else float(fu)
    e_gpa = 200.0 if e_gpa is None else float(e_gpa)
    poisson = 0.3 if poisson is None else float(poisson)
    density = 78.5 if density is None else float(density)

    mapped_core = _OSDAG_CORE_STEEL_GRADE_MAP.get(_norm_grade(raw_grade))
    is_custom_name = raw_grade.lower().startswith(("custom_steel_", "cus_"))
    has_non_db_override = False
    if db_vals is not None:
        has_non_db_override = (
            abs(fy - db_vals["fy"]) > 1e-6
            or abs(fu - db_vals["fu"]) > 1e-6
            or abs(e_gpa - db_vals["E_gpa"]) > 1e-6
        )

    if mapped_core and not is_custom_name and not has_non_db_override:
        return {
            "grade": mapped_core,
            "source_grade": raw_grade,
            "fy_mpa": fy,
            "fu_mpa": fu,
            "e_gpa": e_gpa,
            "poisson": poisson,
            "density_kn_m3": density,
            "override": None,
        }

    # Unmapped OsdagBridge standard grades (e.g. E 275A, E 550A) or custom grades
    # use runtime Material override inside osdag_core worker calls.
    return {
        "grade": raw_grade,
        "source_grade": raw_grade,
        "fy_mpa": fy,
        "fu_mpa": fu,
        "e_gpa": e_gpa,
        "poisson": poisson,
        "density_kn_m3": density,
        "override": {
            "grade": raw_grade,
            "fy": fy,
            "fu": fu,
            "E_mpa": e_gpa * 1000.0,
            "unit_mass": density * 100.0,
        },
    }


def apply_material_to_design_dict(design_dict: Dict[str, Any], material_spec: Dict[str, Any] | None) -> Dict[str, Any]:
    """Apply resolved steel grade (and optional custom override) onto an osdag_core design dict."""
    if not material_spec:
        return design_dict
    grade = str(material_spec.get("grade") or "E 250 (Fe 410 W)A")
    design_dict["Material"] = grade
    design_dict["Member.Material"] = grade
    design_dict["Connector.Material"] = grade
    override = material_spec.get("override")
    if override:
        design_dict[CUSTOM_MATERIAL_OVERRIDE_KEY] = dict(override)
    else:
        design_dict.pop(CUSTOM_MATERIAL_OVERRIDE_KEY, None)
    return design_dict


@contextlib.contextmanager
def _patched_osdag_core_material(override: Dict[str, Any] | None):
    if not override:
        yield
        return

    from osdag_core.utils.common.material import Material

    original_init = Material.__init__
    target_grade = str(override.get("grade", ""))
    fy_val = float(override["fy"])
    fu_val = float(override["fu"])
    e_mpa = float(override.get("E_mpa", 200000.0))
    unit_mass = float(override.get("unit_mass", 7850.0))

    @functools.wraps(original_init)
    def _custom_material_init(self, material_grade="", thickness=41):
        if str(material_grade or "") == target_grade:
            self.fy_20 = fy_val
            self.fy_20_40 = fy_val
            self.fy_40 = fy_val
            self.fy = fy_val
            self.fu = fu_val
            self.material = target_grade
            self.modulus_of_elasticity = e_mpa
            self.unit_mass = unit_mass
            return
        original_init(self, material_grade=material_grade, thickness=thickness)

    Material.__init__ = _custom_material_init
    try:
        yield
    finally:
        Material.__init__ = original_init


# OUTPUT SUPPRESSION
@contextlib.contextmanager
def suppress_output(enabled: bool = True):
    if not enabled:
        yield
        return

    logging.disable(logging.CRITICAL)

    with open(os.devnull, "w", encoding="utf-8") as devnull:
        with contextlib.redirect_stdout(devnull):
            with contextlib.redirect_stderr(devnull):
                yield

    logging.disable(logging.NOTSET)

def run_calculation(design_dict: Dict[str, Any], quiet: bool = True) -> Dict[str, Any]:
    # Every subprocess needs UTF-8 again
    if sys.platform.startswith("win"):
        sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
        sys.stderr.reconfigure(encoding="utf-8", errors="ignore")

    clean_dict = dict(design_dict)
    override = clean_dict.pop(CUSTOM_MATERIAL_OVERRIDE_KEY, None)

    with suppress_output(quiet):
        module_name = clean_dict.get("Module")
        module_class = MODULE_CLASS_MAP.get(module_name)

        if not module_class:
            raise ValueError(f"Unsupported module type: {module_name}")

        with _patched_osdag_core_material(override):
            module_instance = module_class()
            module_instance.set_osdaglogger(None, None)

            validation_errors = module_instance.func_for_validation(clean_dict)

            if validation_errors:
                print(f"[Osdag] Validation errors: {validation_errors}")
                raise RuntimeError("Validation errors occurred during execution.")

            output_dict = _get_output_dictionary(module_instance)

        return output_dict

_forkserver_preloaded = False


def design_pool(max_workers: int) -> ProcessPoolExecutor:
    """Executor for osdag_core design checks with a thread-safe start method.

    The default fork start method is unsafe here: the design pipeline runs on a
    QThread while the GUI thread spins the Qt event loop, and a fork taken at that
    moment inherits mutexes locked by other threads — the child deadlocks before it
    ever reaches run_calculation (observed hang in stage 7).

    forkserver avoids that (the server is launched via fork+exec, so workers fork
    from its clean single-threaded state) while staying fast: this module is
    preloaded into the server once, so every worker starts with osdag_core already
    imported and shares those pages copy-on-write. Windows has no forkserver and
    falls back to spawn — its default start method anyway.
    """
    import multiprocessing
    try:
        ctx = multiprocessing.get_context("forkserver")
        global _forkserver_preloaded
        if not _forkserver_preloaded:
            ctx.set_forkserver_preload(["osdagbridge.core.utils.connect"])
            _forkserver_preloaded = True
    except ValueError:
        ctx = multiprocessing.get_context("spawn")
    return ProcessPoolExecutor(max_workers=max_workers, mp_context=ctx)


def run_parallel_designs(design_dicts: List[Dict[str, Any]], quiet: bool = True) -> List[Dict[str, Any]]:
    cpu_count = os.cpu_count() or 4
    max_workers = min(cpu_count, len(design_dicts))

    with design_pool(max_workers) as executor:
        futures = [
            executor.submit(run_calculation, design_dict, quiet) 
            for design_dict in design_dicts
        ]
        results = [future.result() for future in futures]

    return results

# TENSION BOLTED
design_dict_tension_bolted = {
    "Bolt.Bolt_Hole_Type": "Standard",
    "Bolt.Diameter": ["8", "10", "12", "16", "20", "24", "30", "36", "42", "48", "56", "64", "14", "18", "22", "27", "33", "39", "45", "52", "60"],
    "Bolt.Grade": ["3.6", "4.6", "4.8", "5.6", "5.8", "6.8", "8.8", "9.8", "10.9", "12.9"],
    "Bolt.Slip_Factor": "0.3",
    "Bolt.TensionType": "Pre-tensioned",
    "Bolt.Type": "Bearing Bolt",
    "Conn_Location": "Long Leg",
    "Connector.Material": "E 250 (Fe 410 W)A",
    "Connector.Plate.Thickness_List": ["8", "10", "12", "14", "16", "18", "20", "22", "25", "28", "32", "36", "40", "45", "50", "56", "63", "75", "80", "90", "100", "110", "120"],
    "Design.Design_Method": "Limit State Design",
    "Detailing.Corrosive_Influences": "No",
    "Detailing.Edge_type": "Sheared or hand flame cut",
    "Detailing.Gap": "10",
    "Load.Axial": "4",
    "Material": "E 250 (Fe 410 W)A",
    "Member.Designation": [
        "20 x 20 x 3",
        "20 x 20 x 4",
        "25 x 25 x 3",
        "25 x 25 x 4",
        "25 x 25 x 5",
        "30 x 30 x 3",  
        "30 x 30 x 4",
        "30 x 30 x 5",
        "35 x 35 x 3",
        "35 x 35 x 4",
        "35 x 35 x 5",
        "35 x 35 x 6",
        "40 x 40 x 3",
        "40 x 40 x 4",
        "40 x 40 x 5",
        "40 x 40 x 6",
        "45 x 45 x 3",
        "45 x 45 x 4",
        "45 x 45 x 5",
        "45 x 45 x 6",
        "50 x 50 x 3",
        "50 x 50 x 4",
        "50 x 50 x 5",
        "50 x 50 x 6",
        "55 x 55 x 4",
        "55 x 55 x 5",
        "55 x 55 x 6",
        "55 x 55 x 8",
        "60 x 60 x 4",
        "60 x 60 x 5",
        "60 x 60 x 6",
        "60 x 60 x 8",
        "65 x 65 x 4",
        "65 x 65 x 5",
        "65 x 65 x 6",
        "65 x 65 x 8",
        "70 x 70 x 5",
        "70 x 70 x 6",
        "70 x 70 x 8",
        "70 x 70 x 10",
        "75 x 75 x 5",
        "75 x 75 x 6",
        "75 x 75 x 8",
        "75 x 75 x 10",
        "80 x 80 x 6",
        "80 x 80 x 8",
        "80 x 80 x 10",
        "80 x 80 x 12",
        "90 x 90 x 6",
        "90 x 90 x 8",
        "90 x 90 x 10",
        "90 x 90 x 12",
        "100 x 100 x 6",
        "100 x 100 x 8",
        "100 x 100 x 10",
        "100 x 100 x 12",
        "110 x 110 x 8",
        "110 x 110 x 10",
        "110 x 110 x 12",
        "110 x 110 x 16",
        # "130 x 130 x 8",
        # "130 x 130 x 10",
        # "130 x 130 x 12",
        # "130 x 130 x 16",
        # "150 x 150 x 10",
        # "150 x 150 x 12",
        # "150 x 150 x 16",
        # "150 x 150 x 20",
        # "200 x 200 x 12",
        # "200 x 200 x 16",
        # "200 x 200 x 20",
        # "200 x 200 x 25",
        # "50 x 50 x 7",
        # "50 x 50 x 8",
        # "55 x 55 x 10",
        # "60 x 60 x 10",
        # "65 x 65 x 10",
        # "70 x 70 x 7",
        # "100 x 100 x 7",
        # "100 x 100 x 15",
        # "120 x 120 x 8",
        # "120 x 120 x 10",
        # "120 x 120 x 12",
        # "120 x 120 x 15",
        # "130 x 130 x 9",
        # "150 x 150 x 15",
        # "150 x 150 x 18",
        # "180 x 180 x 15",
        # "180 x 180 x 18",
        # "180 x 180 x 20",
        # "200 x 200 x 24",
        # "30 x 20 x 3",
        # "30 x 20 x 4",
        # "30 x 20 x 5",
        # "40 x 25 x 3",
        # "40 x 25 x 4",
        # "40 x 25 x 5",
        # "40 x 25 x 6",
        # "45 x 30 x 3",
        # "45 x 30 x 4",
        # "45 x 30 x 5",
        # "45 x 30 x 6",
        # "50 x 30 x 3",
        # "50 x 30 x 4",
        # "50 x 30 x 5",
        # "50 x 30 x 6",
        # "60 x 40 x 5",
        # "60 x 40 x 6",
        # "60 x 40 x 8",
        # "65 x 45 x 5",
        # "65 x 45 x 6",
        # "65 x 45 x 8",
        # "70 x 45 x 5",
        # "70 x 45 x 6",
        # "70 x 45 x 8",
        # "70 x 45 x 10",
        # "75 x 50 x 5",
        # "75 x 50 x 6",
        # "75 x 50 x 8",
        # "75 x 50 x 10",
        # "80 x 50 x 5",
        # "80 x 50 x 6",
        # "80 x 50 x 8",
        # "80 x 50 x 10",
        # "90 x 60 x 6",
        # "90 x 60 x 8",
        # "90 x 60 x 10",
        # "90 x 60 x 12",
        # "100 x 65 x 6",
        # "100 x 65 x 8",
        # "100 x 65 x 10",
        # "100 x 75 x 6",
        # "100 x 75 x 8",
        # "100 x 75 x 10",
        # "100 x 75 x 12",
        # "125 x 75 x 6",
        # "125 x 75 x 8",
        # "125 x 75 x 10",
        # "125 x 95 x 6",
        # "125 x 95 x 8",
        # "125 x 95 x 10",
        # "125 x 95 x 12",
        # "150 x 115 x 8",
        # "150 x 115 x 10",
        # "150 x 115 x 12",
        # "150 x 115 x 16",
        # "200 x 100 x 10",
        # "200 x 100 x 12",
        # "200 x 100 x 16",
        # "200 x 150 x 10",
        # "200 x 150 x 12",
        # "200 x 150 x 16",
        # "200 x 150 x 20",
        # "40 x 20 x 3",
        # "40 x 20 x 4",
        # "40 x 20 x 5",
        # "60 x 30 x 5",
        # "60 x 30 x 6",
        # "60 x 40 x 7",
        # "65 x 50 x 5",
        # "65 x 50 x 6",
        # "65 x 50 x 7",
        # "65 x 50 x 8",
        # "70 x 50 x 5",
        # "70 x 50 x 6",
        # "70 x 50 x 7",
        # "70 x 50 x 8",
        # "75 x 50 x 7",
        # "80 x 40 x 5",
        # "80 x 40 x 6",
        # "80 x 40 x 7",
        # "80 x 40 x 8",
        # "80 x 60 x 6",
        # "80 x 60 x 7",
        # "80 x 60 x 8",
        # "90 x 65 x 6",
        # "90 x 65 x 7",
        # "90 x 65 x 8",
        # "90 x 65 x 10",
        # "100 x 50 x 6",
        # "100 x 50 x 7",
        # "100 x 50 x 8",
        # "100 x 50 x 10",
        # "100 x 65 x 7",
        # "120 x 80 x 8",
        # "120 x 80 x 10",
        # "120 x 80 x 12",
        # "125 x 75 x 12",
        # "135 x 65 x 8",
        # "135 x 65 x 10",
        # "135 x 65 x 12",
        # "150 x 75 x 9",
        # "150 x 75 x 15",
        # "150 x 90 x 10",
        # "150 x 90 x 12",
        # "150 x 90 x 15",
        # "200 x 100 x 15",
        # "200 x 150 x 15",
        # "200 x 150 x 18",
    ],
    "Member.Length": "1500",
    "Member.Material": "E 250 (Fe 410 W)A",
    "Member.Profile": "Back to Back Angles",
    "Module": "Tension Member Design - Bolted to End Gusset",
    "out_titles_status": [1, 1, 1, 1, 1],
}

# TENSION WELDED
design_dict_tension_welded = {
    "Conn_Location": "Long Leg",
    "Connector.Material": "E 165 (Fe 290)",
    "Connector.Plate.Thickness_List": ["8", "10", "12"],
    "Design.Design_Method": "Limit State Design",
    "Load.Axial": "5",
    "Material": "E 165 (Fe 290)",
    "Member.Designation": [
        "20 x 20 x 3",
        "25 x 25 x 3",
    ],
    "Member.Length": "500",
    "Member.Material": "E 165 (Fe 290)",
    "Member.Profile": "Angles",
    "Module": "Tension Member Design - Welded to End Gusset",
    "Weld.Fab": "Shop Weld",
    "Weld.Material_Grade_OverWrite": "290",
    "out_titles_status": [1, 1, 1, 1, 1],
}

# STRUTS BOLTED
design_dict_struts_bolted = {
    "Bolt.Bolt_Hole_Type": "Standard",
    "Bolt.Diameter": ["8", "10", "12", "16", "20", "24", "30", "36", "42", "48", "56", "64", "14", "18", "22", "27", "33", "39", "45", "52", "60"
],
    "Bolt.Grade": ["3.6", "4.6", "4.8", "5.6", "5.8", "6.8", "8.8", "9.8", "10.9", "12.9"],
    "Bolt.Slip_Factor": "0.3",
    "Bolt.TensionType": "Pre-tensioned",
    "Bolt.Type": "Bearing Bolt",
    "Conn_Location": "Long Leg",
    "Connector.Material": "E 250 (Fe 410 W)A",
    "Connector.Plate.Thickness_List": ["8", "10", "12", "16", "18", "20", "22", "25", "28", "32", "36", "40", "45", "50", "56", "63", "75", "80", "90", "100", "110", "120"],
    "Design.Design_Method": "Limit State Design",
    "Detailing.Corrosive_Influences": "No",
    "Detailing.Edge_type": "Sheared or hand flame cut",
    "Detailing.Gap": "10",
    "End_1": "Fixed",
    "End_2": "Fixed",
    "Load.Axial": "10",
    "Material": "E 250 (Fe 410 W)A",
    "Member.Designation": [
        "20 x 20 x 3",
        "20 x 20 x 4",
        "25 x 25 x 3",
        "25 x 25 x 4",
        "25 x 25 x 5",
        "30 x 30 x 3",
        "30 x 30 x 4",
        "30 x 30 x 5",
        "35 x 35 x 3",
        "35 x 35 x 4",
        "35 x 35 x 5",
        "35 x 35 x 6",
        "40 x 40 x 3",
        "40 x 40 x 4",
        "40 x 40 x 5",
        "40 x 40 x 6",
        "45 x 45 x 3",
        "45 x 45 x 4",
        "45 x 45 x 5",
        "45 x 45 x 6",
        "50 x 50 x 3",
        "50 x 50 x 4",
        "50 x 50 x 5",
        "50 x 50 x 6",
        "55 x 55 x 4",
        "55 x 55 x 5",
        "55 x 55 x 6",
        "55 x 55 x 8",
        "60 x 60 x 4",
        "60 x 60 x 5",
        "60 x 60 x 6",
        "60 x 60 x 8",
        "65 x 65 x 4",
        "65 x 65 x 5",
        "65 x 65 x 6",
        "65 x 65 x 8",
        "70 x 70 x 5",
        "70 x 70 x 6",
        "70 x 70 x 8",
        "70 x 70 x 10",
        "75 x 75 x 5",
        "75 x 75 x 6",
        "75 x 75 x 8",
        "75 x 75 x 10",
        "80 x 80 x 6",
        "80 x 80 x 8",
        "80 x 80 x 10",
        "80 x 80 x 12",
        "90 x 90 x 6",
        "90 x 90 x 8",
        "90 x 90 x 10",
        "90 x 90 x 12",
        "100 x 100 x 6",
        "100 x 100 x 8",
        "100 x 100 x 10",
        "100 x 100 x 12",
        "110 x 110 x 8",
        "110 x 110 x 10",
        "110 x 110 x 12",
        "110 x 110 x 16",
        # "130 x 130 x 8",
        # "130 x 130 x 10",
        # "130 x 130 x 12",
        # "130 x 130 x 16",
        # "150 x 150 x 10",
        # "150 x 150 x 12",
        # "150 x 150 x 16",
        # "150 x 150 x 20",
        # "200 x 200 x 12",
        # "200 x 200 x 16",
        # "200 x 200 x 20",
        # "200 x 200 x 25",
        # "50 x 50 x 7",
        # "50 x 50 x 8",
        # "55 x 55 x 10",
        # "60 x 60 x 10",
        # "65 x 65 x 10",
        # "70 x 70 x 7",
        # "100 x 100 x 7",
        # "100 x 100 x 15",
        # "120 x 120 x 8",
        # "120 x 120 x 10",
        # "120 x 120 x 12",
        # "120 x 120 x 15",
        # "130 x 130 x 9",
        # "150 x 150 x 15",
        # "150 x 150 x 18",
        # "180 x 180 x 15",
        # "180 x 180 x 18",
        # "180 x 180 x 20",
        # "200 x 200 x 24",
        # "30 x 20 x 3",
        # "30 x 20 x 4",
        # "30 x 20 x 5",
        # "40 x 25 x 3",
        # "40 x 25 x 4",
        # "40 x 25 x 5",
        # "40 x 25 x 6",
        # "45 x 30 x 3",
        # "45 x 30 x 4",
        # "45 x 30 x 5",
        # "45 x 30 x 6",
        # "50 x 30 x 3",
        # "50 x 30 x 4",
        # "50 x 30 x 5",
        # "50 x 30 x 6",
        # "60 x 40 x 5",
        # "60 x 40 x 6",
        # "60 x 40 x 8",
        # "65 x 45 x 5",
        # "65 x 45 x 6",
        # "65 x 45 x 8",
        # "70 x 45 x 5",
        # "70 x 45 x 6",
        # "70 x 45 x 8",
        # "70 x 45 x 10",
        # "75 x 50 x 5",
        # "75 x 50 x 6",
        # "75 x 50 x 8",
        # "75 x 50 x 10",
        # "80 x 50 x 5",
        # "80 x 50 x 6",
        # "80 x 50 x 8",
        # "80 x 50 x 10",
        # "90 x 60 x 6",
        # "90 x 60 x 8",
        # "90 x 60 x 10",
        # "90 x 60 x 12",
        # "100 x 65 x 6",
        # "100 x 65 x 8",
        # "100 x 65 x 10",
        # "100 x 75 x 6",
        # "100 x 75 x 8",
        # "100 x 75 x 10",
        # "100 x 75 x 12",
        # "125 x 75 x 6",
        # "125 x 75 x 8",
        # "125 x 75 x 10",
        # "125 x 95 x 6",
        # "125 x 95 x 8",
        # "125 x 95 x 10",
        # "125 x 95 x 12",
        # "150 x 115 x 8",
        # "150 x 115 x 10",
        # "150 x 115 x 12",
        # "150 x 115 x 16",
        # "200 x 100 x 10",
        # "200 x 100 x 12",
        # "200 x 100 x 16",
        # "200 x 150 x 10",
        # "200 x 150 x 12",
        # "200 x 150 x 16",
        # "200 x 150 x 20",
        # "40 x 20 x 3",
        # "40 x 20 x 4",
        # "40 x 20 x 5",
        # "60 x 30 x 5",
        # "60 x 30 x 6",
        # "60 x 40 x 7",
        # "65 x 50 x 5",
        # "65 x 50 x 6",
        # "65 x 50 x 7",
        # "65 x 50 x 8",
        # "70 x 50 x 5",
        # "70 x 50 x 6",
        # "70 x 50 x 7",
        # "70 x 50 x 8",
        # "75 x 50 x 7",
        # "80 x 40 x 5",
        # "80 x 40 x 6",
        # "80 x 40 x 7",
        # "80 x 40 x 8",
        # "80 x 60 x 6",
        # "80 x 60 x 7",
        # "80 x 60 x 8",
        # "90 x 65 x 6",
        # "90 x 65 x 7",
        # "90 x 65 x 8",
        # "90 x 65 x 10",
        # "100 x 50 x 6",
        # "100 x 50 x 7",
        # "100 x 50 x 8",
        # "100 x 50 x 10",
        # "100 x 65 x 7",
        # "120 x 80 x 8",
        # "120 x 80 x 10",
        # "120 x 80 x 12",
        # "125 x 75 x 12",
        # "135 x 65 x 8",
        # "135 x 65 x 10",
        # "135 x 65 x 12",
        # "150 x 75 x 9",
        # "150 x 75 x 15",
        # "150 x 90 x 10",
        # "150 x 90 x 12",
        # "150 x 90 x 15",
        # "200 x 100 x 15",
        # "200 x 150 x 15",
        # "200 x 150 x 18",
    ],
    "Member.Length": "1500",
    "Member.Material": "E 250 (Fe 410 W)A",
    "Member.Profile": "Back to Back Angles",
    "Module": "Struts Bolted to End Gusset",
    "is_leg_loaded": "Yes",
}

# STRUTS WELDED
design_dict_struts_welded = {
    " In_Plane": "1.0",
    " Out_of_Plane": "1.0",
    "Bolt.Number": "1.0",
    "Conn_Location": "Long Leg",
    "Connector.Plate.Thickness_List": "8",
    "Design.Design_Method": "Limit State Design",
    "Effective.Area_Para": "1.0",
    "End_1": "Fixed",
    "End_2": "Fixed",
    "Load.Axial": "9",
    "Load.Type": "Concentric Load",
    "Material": "E 165 (Fe 290)",
    "Member.Designation": [
        "25 x 25 x 3",
        "40 x 40 x 3",
    ],
    "Member.Length": "900",
    "Member.Material": "E 165 (Fe 290)",
    "Member.Profile": "Angles",
    "Module": "Struts Welded to End Gusset",
    "Optimum.AllowUR": "1.0",
    "Weld.Fab": "Shop Weld",
    "Weld.Material_Grade_OverWrite": "290",
    "out_titles_status": [1, 1, 1, 1, 1],
}

# STANDALONE TESTING
if __name__ == "__main__":
    """
    Standalone testing:
    Runs 10 parallel Osdag designs
    using ProcessPoolExecutor
    """

    design_dicts = [
        design_dict_tension_bolted,
        design_dict_tension_welded,
        design_dict_struts_bolted,
        design_dict_struts_welded,
    ]

    start_time = time.perf_counter()
    results = run_parallel_designs(design_dicts, quiet=True)
    end_time = time.perf_counter()
    total_time = end_time - start_time

    print("\nParallel execution completed\n")
    print(f"Total designs : {len(results)}")
    print(f"Execution time: {total_time:.4f} seconds")
    print(f"Average/design: {total_time / len(results):.4f} seconds")
    print("\nSample outputs:\n")

    for index, result in enumerate(results):
        print(f"\nDesign {index + 1}:\n")
        print(result)