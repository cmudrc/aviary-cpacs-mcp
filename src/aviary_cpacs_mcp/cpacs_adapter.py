"""Shared-CPACS adapter for the Aviary CPACS MCP.

Reads aircraft geometry + flight conditions from CPACS, runs Aviary
trajectory-coupled mission optimization, and writes mission results
back into ``//vehicles/aircraft/model/analysisResults/mission``.
"""

from __future__ import annotations

import importlib.metadata
import logging
from datetime import UTC, datetime
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

    # No default. 122.4 m2 is the D150's wing area; defaulting to it meant any
    # file without a reference area was flown as if it were a D150.
    ref_area_el = root.find(".//vehicles/aircraft/model/reference/area")
    ref_area = float(ref_area_el.text) if ref_area_el is not None and ref_area_el.text else None

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
        # Payload. Not defaulted -- 162 passengers is roughly nine tonnes of
        # people and bags, which is not a detail to assume on the caller's
        # behalf and then report as a mission result.
        "num_passengers": mp.get("num_passengers"),
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

    _append_header_update(
        root,
        "aviary-cpacs-mcp wrote analysisResults/mission (Aviary mission fuel burn and masses)",
        _creator_label(),
    )

    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def _creator_label() -> str:
    """Return ``"aviary-cpacs-mcp <version>"`` for the header provenance entry.

    The version is read from the installed distribution metadata. When the
    package is not installed as a distribution it is reported as ``unknown``
    rather than guessed.
    """
    try:
        version = importlib.metadata.version("aviary-cpacs-mcp")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    return f"aviary-cpacs-mcp {version}"


def _append_header_update(root: ET.Element, modification: str, creator: str) -> ET.Element:
    """Record one write in the CPACS ``header/updates`` provenance list.

    CPACS keeps a running log of changes to a document in ``header/updates``.
    Appending an entry for every write lets a reader of the shared file see
    which tool wrote which section and when, without opening the run logs.

    ``header`` is created as the first child of ``cpacs`` when it is missing.
    ``updates`` is created when it is missing and placed directly after
    ``cpacsVersion``, else directly after ``version``, else at the end of the
    header, so the CPACS 3.x element order stays valid. Existing header
    children are never removed or reordered.

    The new ``update`` carries, in schema order: ``modification`` (one
    sentence saying what was written), ``creator`` (package name and
    version), ``timestamp`` (UTC, ISO 8601, seconds precision), ``version``
    (a running count, 1 + the number of existing entries) and
    ``cpacsVersion`` (copied from ``header/cpacsVersion``, else from
    ``header/version``, else left empty).
    """
    header = root.find("header")
    if header is None:
        header = ET.Element("header")
        root.insert(0, header)

    updates = header.find("updates")
    if updates is None:
        updates = ET.Element("updates")
        anchor = header.find("cpacsVersion")
        if anchor is None:
            anchor = header.find("version")
        if anchor is None:
            header.append(updates)
        else:
            header.insert(list(header).index(anchor) + 1, updates)

    running_version = len(updates.findall("update")) + 1
    cpacs_version = (header.findtext("cpacsVersion") or header.findtext("version") or "").strip()

    update = ET.SubElement(updates, "update")
    ET.SubElement(update, "modification").text = modification
    ET.SubElement(update, "creator").text = creator
    ET.SubElement(update, "timestamp").text = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    ET.SubElement(update, "version").text = str(running_version)
    ET.SubElement(update, "cpacsVersion").text = cpacs_version
    return update


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

    missing = [
        name
        for name, key in (
            ("reference area (//vehicles/aircraft/model/reference/area)", "wing_area_m2"),
            ("payload (num_passengers in the mission profile)", "num_passengers"),
        )
        if inputs.get(key) is None
    ]
    if missing:
        return {
            "success": False,
            "solver": "aviary",
            "error": {
                "type": "missing_input",
                "message": ("Cannot fly a mission: " + ", ".join(missing) + " not available."),
                "details": (
                    "These describe the aircraft and its payload. They are not "
                    "defaulted, because a substituted value is written into "
                    "the shared CPACS and read downstream as a real result."
                ),
            },
        }

    aircraft_params = _build_aviary_params(inputs)
    mission_config = {
        "range_nmi": inputs["range_nmi"],
        "num_passengers": inputs["num_passengers"],
        "cruise_mach": inputs["cruise_mach"],
        "cruise_altitude_ft": inputs["cruise_altitude_ft"],
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
