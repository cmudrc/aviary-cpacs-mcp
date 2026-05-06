"""In-memory session store for Aviary mission profiles."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AviarySession:
    """Holds the state of a single Aviary mission analysis session."""

    session_id: str
    aircraft_params: dict[str, Any] = field(default_factory=dict)
    mission_config: dict[str, Any] = field(default_factory=dict)
    aviary_prob: Any = None
    aviary_converged: bool = False
    trajectory: dict[str, Any] | None = None
    results: dict[str, Any] | None = None
    meta: dict[str, Any] = field(default_factory=dict)


class SessionManager:
    """Thread-safe (GIL-sufficient) Aviary session store."""

    def __init__(self) -> None:
        self._sessions: dict[str, AviarySession] = {}

    def create(self, **meta: Any) -> AviarySession:
        sid = str(uuid.uuid4())
        session = AviarySession(session_id=sid, meta=meta)
        self._sessions[sid] = session
        return session

    def get(self, session_id: str) -> AviarySession:
        try:
            return self._sessions[session_id]
        except KeyError:
            raise KeyError(f"No Aviary session with id '{session_id}'") from None

    def close(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def list_ids(self) -> list[str]:
        return list(self._sessions.keys())


session_manager = SessionManager()
