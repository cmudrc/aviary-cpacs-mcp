"""Set Aviary aircraft parameters (Aircraft.* namespace) for a session."""

from __future__ import annotations

from typing import Any

from ..session_manager import session_manager

KNOWN_PARAMS = {
    "Aircraft.Wing.AREA",
    "Aircraft.Wing.ASPECT_RATIO",
    "Aircraft.Wing.SWEEP",
    "Aircraft.Wing.TAPER_RATIO",
    "Aircraft.Wing.THICKNESS_TO_CHORD",
    "Aircraft.Fuselage.LENGTH",
    "Aircraft.Fuselage.MAX_WIDTH",
    "Aircraft.Fuselage.MAX_HEIGHT",
    "Aircraft.HorizontalTail.AREA",
    "Aircraft.VerticalTail.AREA",
    "Aircraft.Engine.SCALE_FACTOR",
}


def set_aircraft(payload: dict[str, Any]) -> dict[str, Any]:
    """Set Aviary `Aircraft.*` design parameters for a session.

    Parameters
    ----------
    payload : dict
        ``session_id`` -- session to update.
        ``params`` -- dict mapping Aviary parameter name (e.g. ``Aircraft.Wing.AREA``)
        to numeric value. Unknown keys are ignored with a warning.

    Convenience aliases are also accepted at the top level: ``wing_area_m2``,
    ``aspect_ratio``, ``sweep_deg``, ``taper_ratio``, ``fuselage_length_m``.
    """
    session_id = payload.get("session_id")
    if not session_id:
        return {"error": {"type": "ValidationError", "message": "session_id is required"}}

    session = session_manager.get(str(session_id))

    aliases = {
        "wing_area_m2": "Aircraft.Wing.AREA",
        "aspect_ratio": "Aircraft.Wing.ASPECT_RATIO",
        "sweep_deg": "Aircraft.Wing.SWEEP",
        "taper_ratio": "Aircraft.Wing.TAPER_RATIO",
        "fuselage_length_m": "Aircraft.Fuselage.LENGTH",
    }

    params: dict[str, float] = dict(session.aircraft_params)

    for alias, canonical in aliases.items():
        if alias in payload and payload[alias] is not None:
            params[canonical] = float(payload[alias])

    explicit = payload.get("params") or {}
    unknown: list[str] = []
    for name, value in explicit.items():
        if name in KNOWN_PARAMS:
            params[name] = float(value)
        else:
            unknown.append(name)

    session.aircraft_params = params

    return {
        "success": True,
        "session_id": session_id,
        "aircraft_params": params,
        "ignored_unknown": unknown,
    }
