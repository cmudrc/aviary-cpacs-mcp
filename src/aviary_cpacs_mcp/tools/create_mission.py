"""Create and close mission sessions."""

from __future__ import annotations

from typing import Any

from ..session_manager import session_manager


def create_mission(payload: dict[str, Any]) -> dict[str, Any]:
    """Create a new mission analysis session.

    Parameters
    ----------
    payload : dict
        ``name`` – human-readable mission name (optional).
    """
    name = payload.get("name", "unnamed_mission")
    session = session_manager.create(name=name)
    return {
        "session_id": session.session_id,
        "name": name,
        "message": "Mission session created. Set vehicle data and segments next.",
    }


def close_mission(payload: dict[str, Any]) -> dict[str, Any]:
    """Close a mission session and free resources."""
    session_id = payload.get("session_id")
    if not session_id:
        return {"error": {"type": "ValidationError", "message": "session_id is required"}}
    session_manager.close(str(session_id))
    return {"success": True}
