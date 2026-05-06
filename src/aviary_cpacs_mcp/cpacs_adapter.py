"""Shared-CPACS adapter for the Aviary CPACS MCP.

Reads aircraft geometry + flight conditions from CPACS, runs Aviary
trajectory-coupled mission optimization, and writes mission results
back into ``//vehicles/aircraft/model/analysisResults/mission``.
"""

from __future__ import annotations

import logging
from typing import Any
from xml.etree import ElementTree as ET

from aviary_cpacs_mcp.aviary import AVIARY_AVAILABLE

logger = logging.getLogger(__name__)


def read_from_cpacs(
    cpacs_xml: str,
    mission_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract aircraft geometry + flight conditions from CPACS for Aviary."""
    root = ET.fromstring(cpacs_xml)

    ref_area_el = root.find(".//vehicles/aircraft/model/reference/area")
    ref_area = float(ref_area_el.text) if ref_area_el is not None and ref_area_el.text else 122.4

    wing = root.find(".//vehicles/aircraft/model/wings/wing")
    wing_area = ref_area
    aspect_ratio = None
    sweep = None
    taper_ratio = None
    if wing is not None:
        ar_el = wing.find("aspectRatio")
        if ar_el is not None and ar_el.text:
            aspect_ratio = float(ar_el.text)
        sw_el = wing.find("sweep/angle")
        if sw_el is not None and sw_el.text:
            sweep = float(sw_el.text)
        tr_el = wing.find("taperRatio")
        if tr_el is not None and tr_el.text:
            taper_ratio = float(tr_el.text)

    fus = root.find(".//vehicles/aircraft/model/fuselages/fuselage")
    fus_length = None
    if fus is not None:
        fl_el = fus.find("length")
        if fl_el is not None and fl_el.text:
            fus_length = float(fl_el.text)

    mp = mission_profile or {}

    return {
        "wing_area_m2": wing_area,
        "aspect_ratio": aspect_ratio,
        "sweep_deg": sweep,
        "taper_ratio": taper_ratio,
        "fuselage_length_m": fus_length,
        "range_nmi": mp.get("range_nmi", mp.get("range_m", 3_000_000.0) / 1852.0),
        "num_passengers": mp.get("num_passengers", 162),
        "cruise_mach": mp.get("cruise_mach", 0.78),
        "cruise_altitude_ft": mp.get(
            "cruise_altitude_ft",
            mp.get("cruise_altitude_m", 10668.0) * 3.28084,
        ),
    }


def _build_aviary_params(inputs: dict[str, Any]) -> dict[str, Any]:
    """Map CPACS geometry to Aviary parameter names."""
    params: dict[str, Any] = {}
    if inputs.get("wing_area_m2"):
        params["Aircraft.Wing.AREA"] = inputs["wing_area_m2"]
    if inputs.get("aspect_ratio"):
        params["Aircraft.Wing.ASPECT_RATIO"] = inputs["aspect_ratio"]
    if inputs.get("sweep_deg"):
        params["Aircraft.Wing.SWEEP"] = inputs["sweep_deg"]
    if inputs.get("taper_ratio"):
        params["Aircraft.Wing.TAPER_RATIO"] = inputs["taper_ratio"]
    if inputs.get("fuselage_length_m"):
        params["Aircraft.Fuselage.LENGTH"] = inputs["fuselage_length_m"]
    return params


def write_to_cpacs(cpacs_xml: str, results: dict[str, Any]) -> str:
    """Write Aviary results into ``//vehicles/aircraft/model/analysisResults/mission``."""
    root = ET.fromstring(cpacs_xml)

    model = root.find(".//vehicles/aircraft/model")
    if model is None:
        model = _ensure_path(root, "vehicles/aircraft/model")

    ar = model.find("analysisResults")
    if ar is None:
        ar = ET.SubElement(model, "analysisResults")

    existing = ar.find("mission")
    if existing is not None:
        ar.remove(existing)

    m_el = ET.SubElement(ar, "mission")
    ET.SubElement(m_el, "backend").text = "aviary"
    ET.SubElement(m_el, "success").text = str(results.get("success", False)).lower()

    fuel = results.get("total_fuel_burned_kg") or results.get("fuel_burned_kg", 0.0)
    ET.SubElement(m_el, "totalFuelBurnedKg").text = str(fuel)

    for tag, key in [
        ("gtowKg", "gtow_kg"),
        ("wingMassKg", "wing_mass_kg"),
        ("reserveFuelKg", "reserve_fuel_kg"),
        ("zeroFuelWeightKg", "zero_fuel_weight_kg"),
        ("fuelBurnedKg", "fuel_burned_kg"),
        ("converged", "converged"),
        ("runtimeSeconds", "runtime_seconds"),
        ("iterations", "iterations"),
    ]:
        val = results.get(key)
        if val is not None:
            ET.SubElement(m_el, tag).text = str(val)

    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def run_adapter(
    cpacs_xml: str,
    mission_profile: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Full read -> Aviary run -> write cycle for the Mission domain.

    Returns (updated_cpacs_xml, summary_dict).
    """
    if not AVIARY_AVAILABLE:
        return cpacs_xml, {
            "error": {
                "type": "AviaryNotInstalled",
                "message": "Aviary is not installed. Run: pip install aviary==0.9.10 openmdao==3.36.0 dymos==1.13.1",
            }
        }

    inputs = read_from_cpacs(cpacs_xml, mission_profile)
    results = _run_with_aviary(inputs)

    if results.get("success"):
        updated_xml = write_to_cpacs(cpacs_xml, results)
    else:
        updated_xml = cpacs_xml

    return updated_xml, results


def _run_with_aviary(inputs: dict[str, Any]) -> dict[str, Any]:
    """Run mission using the Aviary trajectory optimizer."""
    from aviary_cpacs_mcp.aviary.runner import (
        create_aviary_problem,
        extract_results,
        extract_trajectory,
        run_aviary,
    )

    aircraft_params = _build_aviary_params(inputs)
    mission_config = {
        "range_nmi": inputs.get("range_nmi", 1500),
        "num_passengers": inputs.get("num_passengers", 162),
        "cruise_mach": inputs.get("cruise_mach", 0.785),
        "cruise_altitude_ft": inputs.get("cruise_altitude_ft", 35000),
        "optimizer_max_iter": 200,
    }

    logger.info(
        "Running Aviary mission: range=%d nmi, M=%.3f, alt=%d ft",
        mission_config["range_nmi"],
        mission_config["cruise_mach"],
        mission_config["cruise_altitude_ft"],
    )

    try:
        prob = create_aviary_problem(
            aircraft_params=aircraft_params,
            mission_config=mission_config,
        )
        run_result = run_aviary(prob, timeout_seconds=300)
    except Exception as exc:
        return {"error": {"type": "AviaryError", "message": str(exc)}, "success": False}

    converged = run_result["converged"]
    results = extract_results(prob, converged)
    results.update(
        {
            "success": True,
            "runtime_seconds": run_result["runtime_seconds"],
            "iterations": run_result["iterations"],
            "timed_out": run_result.get("timed_out", False),
        }
    )

    smry = run_result.get("summary", {})
    results["total_fuel_burned_kg"] = smry.get("fuel_burned_kg")
    results["fuel_burned_kg"] = smry.get("fuel_burned_kg")

    try:
        traj = extract_trajectory(prob)
        results["trajectory_points"] = traj.get("num_points", 0)
    except Exception:
        pass

    return results


def _ensure_path(root: ET.Element, path: str) -> ET.Element:
    current = root
    for part in path.split("/"):
        child = current.find(part)
        if child is None:
            child = ET.SubElement(current, part)
        current = child
    return current
