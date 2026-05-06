"""Aviary Level 2 API wrapper for the Aviary CPACS MCP.

Adapted from cmudrc/aviary-mcp (Jessica Ezemba). Encapsulates Aviary
problem setup, parameter override, simulation, and result/trajectory
extraction.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from copy import deepcopy
from typing import Any

logger = logging.getLogger(__name__)

try:
    import aviary.api as av

    try:
        from aviary.models.missions.height_energy_default import (
            phase_info as default_phase_info,
        )
    except ImportError:
        from aviary.interface.default_phase_info.height_energy import (
            phase_info as default_phase_info,
        )

    _AVIARY_OK = True
except ImportError:
    _AVIARY_OK = False
    av = None  # type: ignore[assignment]
    default_phase_info = None

AIRCRAFT_CSV = "models/test_aircraft/aircraft_for_bench_FwFm.csv"

CUSTOM_DESIGN_VARS = {
    "Aircraft.Engine.SCALE_FACTOR": {
        "lower": 0.8,
        "upper": 1.5,
        "units": None,
        "ref": 1.0,
    },
    "Aircraft.Wing.AREA": {
        "lower": 100.0,
        "upper": 160.0,
        "units": "m**2",
        "ref": 130.0,
    },
}


def _resolve_var(name: str):
    """Convert ``Aircraft.Wing.AREA`` to ``av.Aircraft.Wing.AREA``."""
    obj = av
    for part in name.split("."):
        obj = getattr(obj, part)
    return obj


def _build_phase_info(mission_config: dict[str, Any]) -> dict:
    pi = deepcopy(default_phase_info)
    range_nmi = mission_config.get("range_nmi", 1500)
    pi["post_mission"]["target_range"] = (float(range_nmi), "nmi")
    return pi


def create_aviary_problem(
    aircraft_params: dict[str, Any] | None = None,
    mission_config: dict[str, Any] | None = None,
):
    """Build a fully-configured ``AviaryProblem`` ready for optimization.

    Returns the problem instance so the caller can hold onto it for
    trajectory extraction after the run.
    """
    if not _AVIARY_OK:
        raise RuntimeError(
            "Aviary is not installed. Install with: pip install aviary==0.9.10 openmdao==3.36.0 dymos==1.13.1"
        )

    from .design_space import DEFAULT_MISSION_CONFIG

    mc = dict(DEFAULT_MISSION_CONFIG)
    if mission_config:
        mc.update(mission_config)
    if aircraft_params is None:
        aircraft_params = {}

    phase_info = _build_phase_info(mc)
    max_iter = mc.get("optimizer_max_iter", 200)

    prob = av.AviaryProblem(verbosity=0)
    prob.load_inputs(AIRCRAFT_CSV, phase_info)

    from .design_space import DESIGN_PARAMETERS

    _unit_map = {}
    for p in DESIGN_PARAMETERS:
        u = p.get("units", "unitless")
        if u and u != "unitless":
            _unit_map[p["name"]] = u.replace("^", "**")

    for pname, value in aircraft_params.items():
        try:
            kw: dict[str, Any] = {}
            if pname in _unit_map:
                kw["units"] = _unit_map[pname]
            prob.aviary_inputs.set_val(_resolve_var(pname), float(value), **kw)
        except Exception as exc:
            logger.warning("Could not set %s on aviary_inputs: %s", pname, exc)

    cruise_mach = mc.get("cruise_mach", 0.785)
    cruise_alt = mc.get("cruise_altitude_ft", 35000)
    range_nmi = mc.get("range_nmi", 1500)

    for var, val, kw in [
        (av.Mission.Design.CRUISE_ALTITUDE, cruise_alt, {"units": "ft"}),
        (av.Mission.Summary.CRUISE_MACH, cruise_mach, {}),
        (av.Mission.Design.RANGE, range_nmi, {"units": "nmi"}),
    ]:
        try:
            prob.aviary_inputs.set_val(var, val, **kw)
        except Exception as exc:
            logger.warning("Could not set mission param: %s", exc)

    prob.check_and_preprocess_inputs()
    prob.add_pre_mission_systems()
    prob.add_phases()
    prob.add_post_mission_systems()
    prob.link_phases()
    prob.add_driver("SLSQP", max_iter=max_iter)
    prob.add_design_variables()

    for pname, bounds in CUSTOM_DESIGN_VARS.items():
        kwargs: dict[str, Any] = {
            "lower": bounds["lower"],
            "upper": bounds["upper"],
            "ref": bounds["ref"],
        }
        if bounds["units"]:
            kwargs["units"] = bounds["units"]
        try:
            prob.model.add_design_var(_resolve_var(pname), **kwargs)
        except Exception as exc:
            logger.warning("Could not add design var %s: %s", pname, exc)

    prob.add_objective()
    prob.setup()
    prob.set_initial_guesses()

    for pname, value in aircraft_params.items():
        try:
            kw2: dict[str, Any] = {}
            if pname in _unit_map:
                kw2["units"] = _unit_map[pname]
            prob.set_val(_resolve_var(pname), float(value), **kw2)
        except Exception as exc:
            logger.warning("Could not set_val %s after setup: %s", pname, exc)

    return prob


def run_aviary(
    prob,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    """Run trajectory optimisation on a prepared ``AviaryProblem``.

    Returns a dict with convergence info and summary metrics.
    """
    start = time.time()
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(
        prob.run_aviary_problem,
        suppress_solver_print=True,
        run_driver=True,
        simulate=False,
        make_plots=False,
    )

    timed_out = False
    try:
        future.result(timeout=timeout_seconds)
    except FuturesTimeoutError:
        timed_out = True
        logger.warning("Aviary timed out after %ds", timeout_seconds)
    except Exception:
        logger.exception("Aviary run failed")
        raise
    finally:
        executor.shutdown(wait=False)

    elapsed = time.time() - start

    try:
        exit_code = 0 if not prob.driver.fail else 1
    except Exception:
        exit_code = -1

    converged = exit_code == 0 and not timed_out

    summary: dict[str, Any] = {}
    for label, var, units in [
        ("fuel_burned_kg", av.Mission.Summary.FUEL_BURNED, "kg"),
        ("gtow_kg", av.Mission.Summary.GROSS_MASS, "kg"),
        ("wing_mass_kg", av.Aircraft.Wing.MASS, "kg"),
    ]:
        try:
            summary[label] = float(prob.get_val(var, units=units)[0])
        except Exception:
            summary[label] = None

    try:
        reserve = float(prob.get_val(av.Mission.Design.RESERVE_FUEL, units="kg")[0])
        summary["reserve_fuel_kg"] = reserve
    except Exception:
        summary["reserve_fuel_kg"] = None

    if summary["gtow_kg"] is not None and summary["fuel_burned_kg"] is not None:
        reserve = summary.get("reserve_fuel_kg") or 0.0
        summary["zero_fuel_weight_kg"] = summary["gtow_kg"] - summary["fuel_burned_kg"] - reserve
    else:
        summary["zero_fuel_weight_kg"] = None

    try:
        iterations = prob.driver.iter_count
    except Exception:
        iterations = -1

    return {
        "converged": converged,
        "exit_code": exit_code,
        "runtime_seconds": round(elapsed, 2),
        "iterations": iterations,
        "timed_out": timed_out,
        "summary": summary,
    }


def extract_trajectory(prob) -> dict[str, Any]:
    """Extract timeseries data from all Aviary height-energy phases."""
    phases = ["climb", "cruise", "descent"]
    var_map = {
        "time_s": ("time", "s"),
        "altitude_ft": ("altitude", "ft"),
        "mach": ("mach", None),
        "mass_kg": ("mass", "kg"),
        "distance_nmi": ("distance", "nmi"),
        "throttle": ("throttle", None),
        "drag_N": ("drag", "N"),
    }

    trajectory: dict[str, list] = {key: [] for key in var_map}
    trajectory["phase_labels"] = []

    for phase in phases:
        try:
            time_vals = prob.get_val(f"traj.phases.{phase}.timeseries.time", units="s")
            n_points = len(time_vals)
        except Exception:
            logger.debug("No timeseries for phase '%s'", phase)
            continue

        trajectory["phase_labels"].extend([phase] * n_points)

        for key, (var_name, units) in var_map.items():
            try:
                kw = {"units": units} if units else {}
                vals = prob.get_val(f"traj.phases.{phase}.timeseries.{var_name}", **kw)
                trajectory[key].extend(float(v) for v in vals.flatten())
            except Exception:
                trajectory[key].extend([None] * n_points)

    trajectory["num_points"] = len(trajectory["phase_labels"])
    return trajectory


def extract_results(prob, converged: bool) -> dict[str, Any]:
    """Extract full result dict from a completed Aviary run."""
    results: dict[str, Any] = {"converged": converged, "backend": "aviary"}

    for label, var, units in [
        ("fuel_burned_kg", av.Mission.Summary.FUEL_BURNED, "kg"),
        ("gtow_kg", av.Mission.Summary.GROSS_MASS, "kg"),
        ("wing_mass_kg", av.Aircraft.Wing.MASS, "kg"),
        ("reserve_fuel_kg", av.Mission.Design.RESERVE_FUEL, "kg"),
    ]:
        try:
            results[label] = float(prob.get_val(var, units=units)[0])
        except Exception:
            results[label] = None

    if results["gtow_kg"] is not None and results["fuel_burned_kg"] is not None:
        reserve = results.get("reserve_fuel_kg") or 0.0
        results["zero_fuel_weight_kg"] = results["gtow_kg"] - results["fuel_burned_kg"] - reserve
    else:
        results["zero_fuel_weight_kg"] = None

    return results
