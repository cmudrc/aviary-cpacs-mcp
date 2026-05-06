"""Configure Aviary mission profile parameters."""

from __future__ import annotations

from typing import Any

from ..session_manager import session_manager


def configure_mission(payload: dict[str, Any]) -> dict[str, Any]:
    """Set mission-level parameters for an Aviary run.

    Parameters
    ----------
    payload : dict
        ``session_id`` -- mission session to update.
        ``range_nmi`` -- mission range in nautical miles (default 1500).
        ``num_passengers`` -- number of passengers (default 162).
        ``cruise_mach`` -- cruise Mach number (default 0.785).
        ``cruise_altitude_ft`` -- cruise altitude in feet (default 35000).
        ``optimizer_max_iter`` -- SLSQP iterations (default 200).
    """
    session_id = payload.get("session_id")
    if not session_id:
        return {"error": {"type": "ValidationError", "message": "session_id is required"}}

    session = session_manager.get(str(session_id))
    mc = session.mission_config

    if "range_nmi" in payload:
        mc["range_nmi"] = float(payload["range_nmi"])
    if "num_passengers" in payload:
        num_p = int(payload["num_passengers"])
        if num_p < 0 or num_p > 200:
            return {"error": {"type": "ValidationError", "message": "num_passengers must be 0-200"}}
        mc["num_passengers"] = num_p
    if "cruise_mach" in payload:
        mc["cruise_mach"] = float(payload["cruise_mach"])
    if "cruise_altitude_ft" in payload:
        mc["cruise_altitude_ft"] = float(payload["cruise_altitude_ft"])
    if "optimizer_max_iter" in payload:
        mc["optimizer_max_iter"] = int(payload["optimizer_max_iter"])

    session.mission_config = mc

    passenger_mass_kg = 90.7
    payload_kg = round(mc.get("num_passengers", 162) * passenger_mass_kg, 1)

    return {
        "success": True,
        "session_id": session_id,
        "mission_config": mc,
        "payload_kg": payload_kg,
    }
