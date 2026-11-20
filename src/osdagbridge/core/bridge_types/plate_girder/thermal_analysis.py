"""First-class OpenSeesPy thermal mechanics & IRC:6-2017 Clause 215 integration.

Implements physically consistent thermal loading for single-span composite
plate-girder bridges using:
  1. Equivalent nodal fixed-end thermal actions assembled from each OpenSeesPy
     beam element's exact local 12-DOF Euler-Bernoulli stiffness matrix and
     ``geomTransf`` orientation axes.
  2. True composite steel-concrete section transformation and vertical layer
     integration for both uniform temperature (including distinct steel vs RCC
     thermal expansion coefficients) and IRC:6-2017 Cl. 215.4 gradients.
  3. Explicit support boundary mapping and optional finite longitudinal bearing
     spring restraints (``zeroLength`` + ``equalDOF``).
  4. Exact element-local internal-force recovery ``K_local q_local - f_th,local``
     via ``ThermalElementLoad`` inside ``ospgrillage``.

Standards basis:
  - IRC:6-2017 Clause 215 (incorporating Amendment No. 6, May 2021):
    uniform effective bridge temperature bounds (Cl. 215.2 / Table 15),
    non-linear heating/cooling temperature gradients (Cl. 215.4), and
    thermal expansion coefficient ``12.0e-6 /degC`` default when omitted.
  - IRC:6-2017 Amendment No. 8 (Annex B, Tables B.2 & B.3): ULS and SLS
    partial safety / combination factors for thermal load ``TL``.
  - IRC:6-2017 Amendment No. 10 (Notification No. 83): distinction between
    rigid structural restraint and bearing stiffness/frictional restraint.
  - IRC:24-2010 Cl. 504.8: grillage skew limit ``|skew| <= 15 deg``.
"""
from __future__ import annotations

import ast
import math
import re
from typing import Callable

import numpy as np
import openseespy.opensees as ops

from ospgrillage.load import ThermalElementLoad
from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
from osdagbridge.core.utils.common import (
    KEY_SC_LEFT_SUPPORT,
    KEY_SC_RIGHT_SUPPORT,
    KEY_SKEW_ANGLE,
    KEY_TL_BRIDGE_TEMP_MAX,
    KEY_TL_BRIDGE_TEMP_MIN,
    KEY_TL_HIGHEST_MAX_TEMP,
    KEY_TL_LOWEST_MIN_TEMP,
    KEY_TL_TEMP_FALL,
    KEY_TL_TEMP_RISE,
    KEY_TL_THERMAL_COEFF_RCC,
    KEY_TL_THERMAL_COEFF_STEEL,
)

# Default coefficient of thermal expansion per IRC:6-2017 Amendment No. 6 Cl. 215.4
DEFAULT_ALPHA_IRC6_AM6_PER_C = 12.0e-6

# Supported bridge support designations (mapped to ospgrillage edge boundary conditions)
SUPPORTED_SUPPORT_TYPES = {"Pinned", "Roller", "Fixed"}

# Canonical thermal action input keys (distinct from default CTE metadata keys)
CANONICAL_THERMAL_ACTION_KEYS = (
    KEY_TL_HIGHEST_MAX_TEMP,
    KEY_TL_LOWEST_MIN_TEMP,
    KEY_TL_BRIDGE_TEMP_MIN,
    KEY_TL_BRIDGE_TEMP_MAX,
    KEY_TL_TEMP_RISE,
    KEY_TL_TEMP_FALL,
)

KEY_TL_INITIAL_REF_TEMP = "loading.temperature_load.initial_ref_temp"
KEY_TL_INCLUDE_GRADIENT = "loading.temperature_load.include_gradient"
KEY_SC_LEFT_STIFFNESS_KN_M = "support_conditions.left_bearing_stiffness_kN_m"
KEY_SC_RIGHT_STIFFNESS_KN_M = "support_conditions.right_bearing_stiffness_kN_m"

_BEAM_ELE_RE = re.compile(
    r'ops\.element\(\s*"elasticBeamColumn"\s*,\s*(\d+)\s*,\s*\*\[([^\]]+)\]\s*,\s*\*\[([^\]]+)\]\s*,\s*(\d+)'
)


def _is_populated(val) -> bool:
    if val is None or isinstance(val, bool):
        return False
    if isinstance(val, str):
        s = val.strip()
        return s != "" and s not in ("—", "-")
    return True


def _parse_finite_float(val, label: str) -> float:
    if isinstance(val, bool):
        raise ValueError(f"{label} must be a finite numeric value, got bool {val!r}.")
    try:
        num = float(val)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric, got {val!r}.") from exc
    if not math.isfinite(num):
        raise ValueError(f"{label} must be finite, got {val!r}.")
    return num


def _parse_alpha(val, label: str, default_val: float = DEFAULT_ALPHA_IRC6_AM6_PER_C) -> float:
    if not _is_populated(val):
        return default_val
    num = _parse_finite_float(val, label)
    if num <= 0.0 or num > 1.0e-2:
        raise ValueError(
            f"{label} must be in (0, 1e-2] /degC (SI strain per degC, e.g. 12e-6), got {val!r}."
        )
    return num


def _parse_optional_stiffness(input_dict: dict, key: str, label: str) -> float | None:
    raw = input_dict.get(key)
    if not _is_populated(raw):
        return None
    val = _parse_finite_float(raw, label)
    if val <= 0.0:
        raise ValueError(f"{label} must be strictly positive (kN/m), got {val}.")
    return val


def parse_support_conditions(input_dict: dict) -> dict:
    """Validate and normalize support types and optional explicit bearing stiffness."""
    left_raw = input_dict.get(KEY_SC_LEFT_SUPPORT, "Pinned")
    right_raw = input_dict.get(KEY_SC_RIGHT_SUPPORT, "Roller")
    left = str(left_raw if _is_populated(left_raw) else "Pinned").strip()
    right = str(right_raw if _is_populated(right_raw) else "Roller").strip()
    if left not in SUPPORTED_SUPPORT_TYPES:
        raise ValueError(
            f"Unsupported left support '{left}'; expected one of {sorted(SUPPORTED_SUPPORT_TYPES)}."
        )
    if right not in SUPPORTED_SUPPORT_TYPES:
        raise ValueError(
            f"Unsupported right support '{right}'; expected one of {sorted(SUPPORTED_SUPPORT_TYPES)}."
        )
    return {
        "left_support": left,
        "right_support": right,
        "k_left_kN_m": _parse_optional_stiffness(
            input_dict, KEY_SC_LEFT_STIFFNESS_KN_M, "Left bearing stiffness"
        ),
        "k_right_kN_m": _parse_optional_stiffness(
            input_dict, KEY_SC_RIGHT_STIFFNESS_KN_M, "Right bearing stiffness"
        ),
    }


def parse_and_validate_thermal_inputs(input_dict: dict) -> dict | None:
    """Parse canonical thermal inputs, reject invalid/legacy configurations, or return None.

    Returns ``None`` cleanly when no canonical thermal action keys are populated
    and ``temperature_load_kN_m2`` is absent/zero, preserving valid nonthermal runs.
    """
    tl_legacy = input_dict.get("temperature_load_kN_m2")
    if _is_populated(tl_legacy):
        legacy_val = _parse_finite_float(tl_legacy, "temperature_load_kN_m2")
        if legacy_val != 0.0:
            raise ValueError(
                "Legacy 'temperature_load_kN_m2' represents vertical deck patch pressure, "
                "not physical thermal eigenstrain. Remove 'temperature_load_kN_m2' and supply "
                "canonical Temperature Load keys (KEY_TL_*) instead."
            )

    configured = [k for k in CANONICAL_THERMAL_ACTION_KEYS if _is_populated(input_dict.get(k))]
    if not configured:
        return None

    # Enforce IRC:24 Cl. 504.8 skew limit for grillage thermal analysis
    skew_raw = input_dict.get(KEY_SKEW_ANGLE)
    skew_deg = 0.0
    if _is_populated(skew_raw) and str(skew_raw).strip().lower() != "none":
        skew_deg = _parse_finite_float(skew_raw, "Skew angle")
        if abs(skew_deg) > 15.0:
            raise ValueError(
                f"Thermal grillage analysis is unsupported for |skew| > 15 deg per IRC:24 Cl. 504.8 (got {skew_deg} deg)."
            )

    supports = parse_support_conditions(input_dict)

    has_max_air = _is_populated(input_dict.get(KEY_TL_HIGHEST_MAX_TEMP))
    has_min_air = _is_populated(input_dict.get(KEY_TL_LOWEST_MIN_TEMP))
    t_max_air = _parse_finite_float(input_dict[KEY_TL_HIGHEST_MAX_TEMP], "Highest maximum air temp") if has_max_air else None
    t_min_air = _parse_finite_float(input_dict[KEY_TL_LOWEST_MIN_TEMP], "Lowest minimum air temp") if has_min_air else None

    if (t_max_air is not None) ^ (t_min_air is not None):
        raise ValueError("Both highest_max_temp and lowest_min_temp must be supplied together.")
    if t_max_air is not None and t_min_air is not None and t_max_air < t_min_air:
        raise ValueError(
            f"Invalid air temperature range: highest_max_temp ({t_max_air} C) < lowest_min_temp ({t_min_air} C)."
        )

    alpha_steel = _parse_alpha(
        input_dict.get(KEY_TL_THERMAL_COEFF_STEEL), "Coefficient of thermal expansion (steel)"
    )
    alpha_rcc = _parse_alpha(
        input_dict.get(KEY_TL_THERMAL_COEFF_RCC), "Coefficient of thermal expansion (RCC)"
    )

    has_ebt_min = _is_populated(input_dict.get(KEY_TL_BRIDGE_TEMP_MIN))
    has_ebt_max = _is_populated(input_dict.get(KEY_TL_BRIDGE_TEMP_MAX))
    if t_max_air is not None and t_min_air is not None:
        ebt = IRC6_2017.cl_215_2_effective_bridge_temperature(
            max_temp=t_max_air,
            min_temp=t_min_air,
            structural_type="metallic",
            snowbound=False,
        )
        t_e_min = float(input_dict[KEY_TL_BRIDGE_TEMP_MIN]) if has_ebt_min else float(ebt["T_min"])
        t_e_max = float(input_dict[KEY_TL_BRIDGE_TEMP_MAX]) if has_ebt_max else float(ebt["T_max"])
        t_mean_air = 0.5 * (t_max_air + t_min_air)
        half_band = 10.0 if (t_max_air - t_min_air) > 20.0 else 5.0
        t0_min = t_mean_air - half_band
        t0_max = t_mean_air + half_band
    elif has_ebt_min and has_ebt_max:
        t_e_min = _parse_finite_float(input_dict[KEY_TL_BRIDGE_TEMP_MIN], "Effective bridge temp min")
        t_e_max = _parse_finite_float(input_dict[KEY_TL_BRIDGE_TEMP_MAX], "Effective bridge temp max")
        t0_min = 0.5 * (t_e_min + t_e_max)
        t0_max = t0_min
    else:
        # Rise/fall provided directly without shade temperatures
        has_r = _is_populated(input_dict.get(KEY_TL_TEMP_RISE))
        has_f = _is_populated(input_dict.get(KEY_TL_TEMP_FALL))
        if not (has_r or has_f):
            raise ValueError("Incomplete thermal inputs: provide shade temperatures or explicit rise/fall.")
        r_val = _parse_finite_float(input_dict.get(KEY_TL_TEMP_RISE, 0.0), "Temperature rise") if has_r else 0.0
        f_val = _parse_finite_float(input_dict.get(KEY_TL_TEMP_FALL, 0.0), "Temperature fall") if has_f else 0.0
        t_e_min, t_e_max = -f_val, r_val
        t0_min, t0_max = 0.0, 0.0

    if not (math.isfinite(t_e_min) and math.isfinite(t_e_max)) or t_e_max < t_e_min:
        raise ValueError(f"Invalid effective bridge temperature range [{t_e_min}, {t_e_max}] C.")

    t_mean = 0.5 * (t_e_min + t_e_max)
    raw_ref = input_dict.get(KEY_TL_INITIAL_REF_TEMP)
    if _is_populated(raw_ref):
        t0_used = _parse_finite_float(raw_ref, "Initial reference temperature")
        ref_source = "user_explicit"
    else:
        t0_used = t_mean
        ref_source = "effective_mean"

    # Compute rise/fall relative to reference temperature unless user supplied both rise/fall directly
    if _is_populated(input_dict.get(KEY_TL_TEMP_RISE)) and _is_populated(input_dict.get(KEY_TL_TEMP_FALL)) and not _is_populated(raw_ref):
        delta_t_rise = _parse_finite_float(input_dict[KEY_TL_TEMP_RISE], "Temperature rise")
        delta_t_fall = _parse_finite_float(input_dict[KEY_TL_TEMP_FALL], "Temperature fall")
    else:
        delta_t_rise = max(0.0, t_e_max - t0_used)
        delta_t_fall = max(0.0, t0_used - t_e_min)

    if delta_t_rise < 0.0 or delta_t_fall < 0.0:
        raise ValueError(f"Temperature rise ({delta_t_rise}) and fall ({delta_t_fall}) must be >= 0.")

    include_grad_raw = input_dict.get(KEY_TL_INCLUDE_GRADIENT)
    include_gradient = True if include_grad_raw is None else bool(include_grad_raw)

    return {
        "configured_keys": configured,
        "skew_deg": skew_deg,
        "T_max_air_C": t_max_air,
        "T_min_air_C": t_min_air,
        "T_e_min_C": t_e_min,
        "T_e_max_C": t_e_max,
        "T_mean_C": t_mean,
        "T0_min_C": t0_min,
        "T0_max_C": t0_max,
        "T0_used_C": t0_used,
        "ref_source": ref_source,
        "delta_T_rise_C": delta_t_rise,
        "delta_T_fall_C": delta_t_fall,
        "alpha_steel_per_C": alpha_steel,
        "alpha_rcc_per_C": alpha_rcc,
        "include_gradient": include_gradient,
        **supports,
        "standards_basis": (
            "IRC:6-2017 Cl. 215 (Am. No. 6 Cl. 215.2/215.4, Table 15; "
            "Am. No. 8 Table B.2/B.3 factors; Am. No. 10 restraint terminology); "
            "IRC:24-2010 Cl. 504.8 skew <= 15 deg"
        ),
    }


def build_composite_section_layers(
    steel_dims: dict,
    b_eff_m: float,
    t_slab_m: float,
    E_s_Pa: float,
    E_c_Pa: float,
    alpha_steel: float,
    alpha_rcc: float,
    h_haunch_m: float = 0.0,
) -> list[dict]:
    """Build bottom-to-top rectangular layers ``(y_bot, y_top, width, E_Pa, alpha)``.

    ``y`` is measured upward from the soffit of the bottom steel flange (m).
    """
    t_fb = float(steel_dims["tf_bot_m"])
    b_fb = float(steel_dims["bf_bot_m"])
    d_w = float(steel_dims["dw_m"])
    t_w = float(steel_dims["tw_m"])
    t_ft = float(steel_dims["tf_top_m"])
    b_ft = float(steel_dims["bf_top_m"])
    D_steel = t_fb + d_w + t_ft

    layers = [
        {"name": "steel_bot_flange", "y_bot_m": 0.0, "y_top_m": t_fb, "width_m": b_fb, "E_Pa": E_s_Pa, "alpha_per_C": alpha_steel},
        {"name": "steel_web",        "y_bot_m": t_fb, "y_top_m": t_fb + d_w, "width_m": t_w, "E_Pa": E_s_Pa, "alpha_per_C": alpha_steel},
        {"name": "steel_top_flange", "y_bot_m": t_fb + d_w, "y_top_m": D_steel, "width_m": b_ft, "E_Pa": E_s_Pa, "alpha_per_C": alpha_steel},
    ]
    y_cur = D_steel
    if h_haunch_m > 0.0:
        layers.append({
            "name": "concrete_haunch",
            "y_bot_m": y_cur,
            "y_top_m": y_cur + h_haunch_m,
            "width_m": b_ft,
            "E_Pa": E_c_Pa,
            "alpha_per_C": alpha_rcc,
        })
        y_cur += h_haunch_m
    if t_slab_m > 0.0 and b_eff_m > 0.0:
        layers.append({
            "name": "concrete_slab",
            "y_bot_m": y_cur,
            "y_top_m": y_cur + t_slab_m,
            "width_m": float(b_eff_m),
            "E_Pa": E_c_Pa,
            "alpha_per_C": alpha_rcc,
        })
    return layers


def compute_composite_thermal_section(
    layers: list[dict],
    E_ref_Pa: float,
    dT_fn: Callable[[float, float], float],
    dy_m: float = 0.001,
) -> dict:
    """Integrate E-weighted composite stiffness, thermal resultants, and eigenstresses.

    Parameters
    ----------
    layers : list of dict
        Each dict specifies ``name``, ``y_bot_m``, ``y_top_m``, ``width_m``,
        ``E_Pa``, and ``alpha_per_C`` (coordinate ``y`` upward from steel soffit).
    E_ref_Pa : float
        Reference steel Young's modulus (Pa) used by OpenSees beam elements.
    dT_fn : callable
        ``dT_fn(y_from_bot_m, D_total_m) -> delta_T_C``.
    dy_m : float
        Vertical integration strip step (m).
    """
    if not layers:
        raise ValueError("At least one layer is required for composite thermal integration.")
    D_total = max(float(layer["y_top_m"]) for layer in layers)

    ea_total = 0.0
    ea_y_sum = 0.0
    n_th = 0.0
    m_y_sum = 0.0

    # First pass: EA_comp, neutral axis y_NA_from_bot, N_th
    strips = []
    for layer in layers:
        y0 = float(layer["y_bot_m"])
        y1 = float(layer["y_top_m"])
        h = y1 - y0
        if h <= 0.0:
            continue
        w = float(layer["width_m"])
        E_i = float(layer["E_Pa"])
        alpha_i = float(layer["alpha_per_C"])
        n_strips = max(1, int(math.ceil(h / dy_m)))
        step = h / n_strips
        for k in range(n_strips):
            ym = y0 + (k + 0.5) * step
            dA = w * step
            ea_i = E_i * dA
            ea_total += ea_i
            ea_y_sum += ea_i * ym
            dT = float(dT_fn(ym, D_total))
            dF_th = ea_i * alpha_i * dT
            n_th += dF_th
            m_y_sum += dF_th * ym
            strips.append((ym, w, step, dA, E_i, alpha_i, dT))

    if ea_total <= 0.0:
        raise ValueError("Composite section axial stiffness EA must be positive.")

    y_na = ea_y_sum / ea_total
    ei_total = 0.0
    for ym, w, step, dA, E_i, _, _ in strips:
        ei_total += E_i * (w * step**3 / 12.0 + dA * (ym - y_na) ** 2)

    m_th = m_y_sum - y_na * n_th
    eps0 = n_th / ea_total
    # Standard upward y: positive M_th means top expands more -> hogging (+kappa_local for vecxz=(0,0,-1))
    kappa_up = m_th / ei_total

    # Verify self-equilibrating eigenstress resultant check under free expansion/bowing
    residual_N = 0.0
    residual_M = 0.0
    max_eigen_MPa = 0.0
    min_eigen_MPa = 0.0
    layer_extreme_stresses_MPa = {}
    for layer in layers:
        y0 = float(layer["y_bot_m"])
        y1 = float(layer["y_top_m"])
        if y1 <= y0:
            continue
        E_i = float(layer["E_Pa"])
        alpha_i = float(layer["alpha_per_C"])
        for tag, yy in (("bot", y0), ("top", y1)):
            sig = E_i * (eps0 + kappa_up * (yy - y_na) - alpha_i * float(dT_fn(yy, D_total))) / 1.0e6
            layer_extreme_stresses_MPa[f"{layer['name']}_{tag}"] = round(sig, 4)

    for ym, _, step, dA, E_i, alpha_i, dT in strips:
        sig_pa = E_i * (eps0 + kappa_up * (ym - y_na) - alpha_i * dT)
        sig_mpa = sig_pa / 1.0e6
        if sig_mpa > max_eigen_MPa:
            max_eigen_MPa = sig_mpa
        if sig_mpa < min_eigen_MPa:
            min_eigen_MPa = sig_mpa
        residual_N += sig_pa * dA
        # Exact linear stress variation across strip thickness adds E * kappa * I_strip
        w_strip = dA / step if step > 0.0 else 0.0
        residual_M += sig_pa * (ym - y_na) * dA + E_i * kappa_up * w_strip * (step**3) / 12.0

    return {
        "D_total_m": D_total,
        "y_NA_from_bot_m": y_na,
        "EA_comp_N": ea_total,
        "EI_z_comp_Nm2": ei_total,
        "A_eq_steel_m2": ea_total / E_ref_Pa,
        "Iz_eq_steel_m4": ei_total / E_ref_Pa,
        "N_thermal_N": n_th,
        "M_z_thermal_Nm": m_th,
        "free_axial_strain": eps0,
        "free_curvature_per_m": kappa_up,
        "eigenstress_residual_N": residual_N,
        "eigenstress_residual_Nm": residual_M,
        "max_eigenstress_MPa": max_eigen_MPa,
        "min_eigenstress_MPa": min_eigen_MPa,
        "layer_extreme_stresses_MPa": layer_extreme_stresses_MPa,
    }


def beam_stiffness_local_12dof(
    EA: float, GJ: float, EIy: float, EIz: float, length: float
) -> np.ndarray:
    """Exact 12x12 3D Euler-Bernoulli beam stiffness matrix in OpenSees local axes."""
    l = float(length)
    k = np.zeros((12, 12), dtype=float)

    def put(dofs: tuple[int, ...], block: np.ndarray) -> None:
        for r, di in enumerate(dofs):
            for c, dj in enumerate(dofs):
                k[di, dj] += block[r, c]

    put((0, 6), (EA / l) * np.array([[1.0, -1.0], [-1.0, 1.0]]))
    put((3, 9), (GJ / l) * np.array([[1.0, -1.0], [-1.0, 1.0]]))
    # Bending in local (x, y) plane -> local y translation & rotation about local z
    bz = EIz * np.array([
        [12.0 / l**3, 6.0 / l**2, -12.0 / l**3, 6.0 / l**2],
        [6.0 / l**2,  4.0 / l,    -6.0 / l**2,  2.0 / l],
        [-12.0 / l**3, -6.0 / l**2, 12.0 / l**3, -6.0 / l**2],
        [6.0 / l**2,  2.0 / l,    -6.0 / l**2,  4.0 / l],
    ])
    put((1, 5, 7, 11), bz)
    # Bending in local (x, z) plane -> local z translation & rotation about local y
    by = EIy * np.array([
        [12.0 / l**3, -6.0 / l**2, -12.0 / l**3, -6.0 / l**2],
        [-6.0 / l**2, 4.0 / l,     6.0 / l**2,   2.0 / l],
        [-12.0 / l**3, 6.0 / l**2, 12.0 / l**3,  6.0 / l**2],
        [-6.0 / l**2, 2.0 / l,     6.0 / l**2,   4.0 / l],
    ])
    put((2, 4, 8, 10), by)
    return k


def element_local_to_global_rotation(
    p_i: list[float], p_j: list[float], vecxz: list[float]
) -> np.ndarray:
    """Return 3x3 orthonormal rotation ``R`` where ``v_global = R @ v_local``.

    Follows OpenSeesPy ``geomTransf Linear`` right-handed local axes:
      e_x = (p_j - p_i) / ||p_j - p_i||
      e_y = (vecxz x e_x) / ||vecxz x e_x||
      e_z = e_x x e_y
    """
    dx = np.asarray(p_j, dtype=float) - np.asarray(p_i, dtype=float)
    length = float(np.linalg.norm(dx))
    if length <= 0.0:
        raise ValueError("Degenerate zero-length element encountered during thermal load assembly.")
    e_x = dx / length
    vxz = np.asarray(vecxz, dtype=float)
    e_y = np.cross(vxz, e_x)
    ey_norm = float(np.linalg.norm(e_y))
    if ey_norm <= 1e-12:
        raise ValueError(f"vecxz={vecxz} is parallel to element axis {e_x.tolist()}.")
    e_y = e_y / ey_norm
    e_z = np.cross(e_x, e_y)
    return np.column_stack([e_x, e_y, e_z])


def _extract_model_transform_map(model) -> dict[int, list[float]]:
    """Map integer geomTransf tag -> vecxz [x, y, z] from model.Mesh_obj.transform_dict."""
    ns = {"np": np}
    out: dict[int, list[float]] = {}
    for key_str, tag in getattr(model.Mesh_obj, "transform_dict", {}).items():
        vxz_str = key_str.split("|", 1)[0]
        vxz = [float(x) for x in eval(vxz_str, ns)]
        out[int(tag)] = vxz
    return out


def parse_beam_elements_from_model(model) -> dict[int, dict]:
    """Extract live/registered elasticBeamColumn parameters per element tag."""
    transf_map = _extract_model_transform_map(model)
    specs: dict[int, dict] = {}
    for etag, cmd in getattr(model, "element_command_list", {}).items():
        m = _BEAM_ELE_RE.search(str(cmd))
        if not m:
            continue
        parsed_tag = int(m.group(1))
        nodes = [int(x.strip()) for x in m.group(2).split(",")]
        props = [float(ast.literal_eval(x.strip())) for x in m.group(3).split(",")]
        t_tag = int(m.group(4))
        if len(nodes) != 2 or len(props) != 6:
            continue
        A, E, G, J, Iy, Iz = props
        specs[parsed_tag] = {
            "ele_tag": parsed_tag,
            "nodes": nodes,
            "A": A,
            "E": E,
            "G": G,
            "J": J,
            "Iy": Iy,
            "Iz": Iz,
            "vecxz": transf_map.get(t_tag, [0.0, 0.0, -1.0]),
        }
    return specs


def build_thermal_element_load(
    model,
    name: str,
    per_element_strains: dict[int, tuple[float, float]],
    metadata: dict | None = None,
) -> ThermalElementLoad:
    """Assemble ``ThermalElementLoad`` from per-element ``(eps0, kappa_up)`` strains.

    Parameters
    ----------
    model : OspGrillage
        Instantiated ospgrillage model (``create_osp_model()`` already called).
    name : str
        Load identifier.
    per_element_strains : dict[int, tuple[float, float]]
        Maps OpenSees element tag -> ``(free_axial_strain, free_curvature_per_m)``
        where positive ``free_axial_strain`` elongates the beam and positive
        ``free_curvature_per_m`` denotes upward-convex bowing (top hotter than bottom).
    """
    beam_specs = parse_beam_elements_from_model(model)
    node_coords = {
        int(nid): [round(float(c), 4) for c in spec["coordinate"]]
        for nid, spec in model.Mesh_obj.node_spec.items()
    }

    element_fth_local: dict[int, list[float]] = {}
    element_fth_global: dict[int, list[float]] = {}
    nodal_loads_global: dict[int, np.ndarray] = {}

    up_y = np.array([0.0, 1.0, 0.0], dtype=float)

    for ele_tag, (eps0, kappa_up) in per_element_strains.items():
        spec = beam_specs.get(int(ele_tag))
        if spec is None:
            raise KeyError(f"Element tag {ele_tag} is not an elasticBeamColumn in ospgrillage model.")
        n_i, n_j = spec["nodes"]
        p_i = node_coords[n_i]
        p_j = node_coords[n_j]
        length = float(np.linalg.norm(np.asarray(p_j) - np.asarray(p_i)))

        R = element_local_to_global_rotation(p_i, p_j, spec["vecxz"])
        # Project local +y axis onto global +Y: if local +y = -global Y (standard vecxz),
        # sign is +1 so positive upward bowing kappa_up gives positive q0[7], q0[11].
        kappa_local = -float(np.dot(R[:, 1], up_y)) * float(kappa_up)

        EA = spec["E"] * spec["A"]
        GJ = spec["G"] * spec["J"]
        EIy = spec["E"] * spec["Iy"]
        EIz = spec["E"] * spec["Iz"]
        k_loc = beam_stiffness_local_12dof(EA, GJ, EIy, EIz, length)

        q0 = np.zeros(12, dtype=float)
        q0[6] = float(eps0) * length
        q0[7] = kappa_local * (length**2) / 2.0
        q0[11] = kappa_local * length

        fth_loc = k_loc @ q0
        T12 = np.zeros((12, 12), dtype=float)
        for blk in range(4):
            s = blk * 3
            T12[s:s + 3, s:s + 3] = R
        # Local-to-global nodal force transformation: f_global = T_12 @ f_local (since R columns are local axes)
        fth_glob = T12 @ fth_loc

        element_fth_local[int(ele_tag)] = fth_loc.tolist()
        element_fth_global[int(ele_tag)] = fth_glob.tolist()

        nodal_loads_global[n_i] = nodal_loads_global.get(n_i, np.zeros(6, dtype=float)) + fth_glob[:6]
        nodal_loads_global[n_j] = nodal_loads_global.get(n_j, np.zeros(6, dtype=float)) + fth_glob[6:12]

    nodal_out = {
        nid: vec.tolist()
        for nid, vec in nodal_loads_global.items()
    }
    return ThermalElementLoad(
        name=name,
        element_fth_local=element_fth_local,
        element_fth_global=element_fth_global,
        nodal_loads_global=nodal_out,
        metadata=metadata,
    )
