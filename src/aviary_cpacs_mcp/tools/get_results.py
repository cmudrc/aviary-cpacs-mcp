"""Retrieve results from a completed mission analysis."""

from __future__ import annotations

from typing import Any

from ..session_manager import session_manager


def get_results(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the stored results of the last run_mission call.

    Parameters
    ----------
    payload : dict
        ``session_id`` – mission session.
    """
    session_id = payload.get("session_id")
    if not session_id:
        return {"error": {"type": "ValidationError", "message": "session_id is required"}}

    session = session_manager.get(str(session_id))
    if session.results is None:
        return {"error": {"type": "RuntimeError", "message": "No results yet. Call run_mission first."}}

    return session.results
