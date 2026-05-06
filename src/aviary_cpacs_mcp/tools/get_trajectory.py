"""Extract Aviary trajectory timeseries from a completed run."""

from __future__ import annotations

from typing import Any

from ..session_manager import session_manager


def get_trajectory(payload: dict[str, Any]) -> dict[str, Any]:
    """Return per-phase trajectory timeseries from the last Aviary run.

    Aviary produces continuous timeseries per phase (climb, cruise, descent)
    with altitude, Mach, mass, throttle, drag, and distance.

    Parameters
    ----------
    payload : dict
        ``session_id`` -- session with completed run_mission.
        ``variables`` -- optional list of variable names to return. Available:
        ``time_s``, ``altitude_ft``, ``mach``, ``mass_kg``, ``throttle``,
        ``drag_N``, ``distance_nmi``.
    """
    session_id = payload.get("session_id")
    if not session_id:
        return {"error": {"type": "ValidationError", "message": "session_id is required"}}

    session = session_manager.get(str(session_id))

    if session.trajectory is None:
        return {"error": {"type": "RuntimeError", "message": "No trajectory data. Run run_mission first."}}

    trajectory = session.trajectory
    requested = payload.get("variables")
    all_vars = [
        "time_s",
        "altitude_ft",
        "mach",
        "mass_kg",
        "throttle",
        "drag_N",
        "distance_nmi",
    ]
    if requested:
        invalid = [v for v in requested if v not in all_vars]
        if invalid:
            return {
                "error": {
                    "type": "ValidationError",
                    "message": f"Unknown variable(s): {invalid}. Available: {all_vars}",
                }
            }
        data = {v: trajectory.get(v, []) for v in requested}
    else:
        data = {v: trajectory.get(v, []) for v in all_vars}

    data["phase_labels"] = trajectory.get("phase_labels", [])
    data["num_points"] = trajectory.get("num_points", 0)

    return {
        "success": True,
        "session_id": session_id,
        "backend": "aviary",
        "trajectory": data,
    }
