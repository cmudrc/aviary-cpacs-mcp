"""Execute Aviary trajectory-coupled mission optimization."""

from __future__ import annotations

import logging
from typing import Any

from ..session_manager import session_manager

logger = logging.getLogger(__name__)


def _run_aviary(session: Any, timeout_seconds: int = 300) -> dict[str, Any]:
    """Run the mission using NASA Aviary trajectory optimisation."""
    from ..aviary.runner import (
        create_aviary_problem,
        extract_results,
        extract_trajectory,
        run_aviary,
    )

    mc = dict(session.mission_config)
    ap = dict(session.aircraft_params)

    logger.info("Creating Aviary problem...")
    try:
        prob = create_aviary_problem(aircraft_params=ap, mission_config=mc)
    except Exception as exc:
        logger.exception("Aviary setup failed")
        return {"error": {"type": "AviarySetupError", "message": str(exc)}}

    session.aviary_prob = prob

    logger.info("Running Aviary optimisation...")
    try:
        run_result = run_aviary(prob, timeout_seconds=timeout_seconds)
    except Exception as exc:
        logger.exception("Aviary simulation failed")
        return {"error": {"type": "AviaryRunError", "message": str(exc)}}

    converged = run_result["converged"]
    session.aviary_converged = converged

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
        trajectory = extract_trajectory(prob)
        session.trajectory = trajectory
    except Exception as exc:
        logger.warning("Trajectory extraction failed: %s", exc)

    return dict(results)


def run_mission(payload: dict[str, Any]) -> dict[str, Any]:
    """Run Aviary mission analysis with the configured aircraft and mission_config.

    Parameters
    ----------
    payload : dict
        ``session_id`` -- session with set_aircraft + configure_mission completed.
        ``timeout_seconds`` -- wall-clock timeout (default 300).
    """
    session_id = payload.get("session_id")
    if not session_id:
        return {"error": {"type": "ValidationError", "message": "session_id is required"}}

    session = session_manager.get(str(session_id))
    timeout = int(payload.get("timeout_seconds", 300))
    summary = _run_aviary(session, timeout_seconds=timeout)
    session.results = summary
    return summary
