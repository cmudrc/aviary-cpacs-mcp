"""Factory for the FastMCP server exposing Aviary trajectory-coupled mission tools."""

from __future__ import annotations

import logging
from typing import Any

from fastmcp.server import FastMCP

from . import tools
from .aviary import AVIARY_AVAILABLE

__all__ = ["build_server"]

LOGGER = logging.getLogger(__name__)


def _register_tools(server: FastMCP) -> None:
    """Attach Aviary tool implementations to a FastMCP instance."""

    @server.tool(
        name="create_mission",
        description="Create a new Aviary mission analysis session.",
        tags={"aviary", "mission", "session"},
    )
    def create_mission_tool(name: str = "unnamed_mission") -> dict[str, Any]:
        return tools.create_mission({"name": name})

    @server.tool(
        name="close_mission",
        description="Close an Aviary session and free resources.",
        tags={"aviary", "mission", "session"},
    )
    def close_mission_tool(session_id: str) -> dict[str, Any]:
        return tools.close_mission({"session_id": session_id})

    @server.tool(
        name="set_aircraft",
        description=(
            "Set Aviary `Aircraft.*` design parameters. Convenience aliases "
            "wing_area_m2, aspect_ratio, sweep_deg, taper_ratio, fuselage_length_m "
            "are also accepted."
        ),
        tags={"aviary", "aircraft"},
    )
    def set_aircraft_tool(
        session_id: str,
        wing_area_m2: float | None = None,
        aspect_ratio: float | None = None,
        sweep_deg: float | None = None,
        taper_ratio: float | None = None,
        fuselage_length_m: float | None = None,
        params: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        return tools.set_aircraft(
            {
                "session_id": session_id,
                "wing_area_m2": wing_area_m2,
                "aspect_ratio": aspect_ratio,
                "sweep_deg": sweep_deg,
                "taper_ratio": taper_ratio,
                "fuselage_length_m": fuselage_length_m,
                "params": params or {},
            }
        )

    @server.tool(
        name="configure_mission",
        description=(
            "Set Aviary mission profile: range_nmi, num_passengers, cruise_mach, "
            "cruise_altitude_ft, optimizer_max_iter."
        ),
        tags={"aviary", "configuration"},
    )
    def configure_mission_tool(
        session_id: str,
        range_nmi: float | None = None,
        num_passengers: int | None = None,
        cruise_mach: float | None = None,
        cruise_altitude_ft: float | None = None,
        optimizer_max_iter: int | None = None,
    ) -> dict[str, Any]:
        p: dict[str, Any] = {"session_id": session_id}
        if range_nmi is not None:
            p["range_nmi"] = range_nmi
        if num_passengers is not None:
            p["num_passengers"] = num_passengers
        if cruise_mach is not None:
            p["cruise_mach"] = cruise_mach
        if cruise_altitude_ft is not None:
            p["cruise_altitude_ft"] = cruise_altitude_ft
        if optimizer_max_iter is not None:
            p["optimizer_max_iter"] = optimizer_max_iter
        return tools.configure_mission(p)

    @server.tool(
        name="run_mission",
        description=(
            "Execute Aviary trajectory-coupled mission optimization. "
            "Requires Aviary, OpenMDAO, and Dymos to be installed."
        ),
        tags={"aviary", "execution"},
    )
    def run_mission_tool(
        session_id: str,
        timeout_seconds: int = 300,
    ) -> dict[str, Any]:
        return tools.run_mission({"session_id": session_id, "timeout_seconds": timeout_seconds})

    @server.tool(
        name="get_results",
        description="Retrieve summary results from the last Aviary run.",
        tags={"aviary", "results"},
    )
    def get_results_tool(session_id: str) -> dict[str, Any]:
        return tools.get_results({"session_id": session_id})

    @server.tool(
        name="get_trajectory",
        description=(
            "Return per-phase trajectory timeseries (time, altitude, Mach, mass, "
            "throttle, drag, distance) from the last Aviary run."
        ),
        tags={"aviary", "trajectory"},
    )
    def get_trajectory_tool(
        session_id: str,
        variables: list[str] | None = None,
    ) -> dict[str, Any]:
        p: dict[str, Any] = {"session_id": session_id}
        if variables:
            p["variables"] = variables
        return tools.get_trajectory(p)

    @server.tool(
        name="check_constraints",
        description=(
            "Evaluate pass/fail for user-defined constraints on Aviary mission results. "
            "Supports <=, >=, == operators on fuel_burned_kg, gtow_kg, "
            "wing_mass_kg, reserve_fuel_kg, etc."
        ),
        tags={"aviary", "constraints"},
    )
    def check_constraints_tool(
        session_id: str,
        constraints: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return tools.check_constraints(
            {
                "session_id": session_id,
                "constraints": constraints,
            }
        )


def build_server() -> FastMCP:
    """Construct a FastMCP server with all Aviary tools registered."""
    backend_note = "Aviary available" if AVIARY_AVAILABLE else "Aviary NOT installed -- run_mission will fail"
    server = FastMCP(
        name="aviary-cpacs-mcp",
        instructions=(
            "Aviary CPACS MCP -- aircraft mission analysis via NASA Aviary "
            "trajectory optimization (Dymos / OpenMDAO). "
            f"Status: {backend_note}. "
            "Workflow: create_mission, set_aircraft (Aviary Aircraft.* params), "
            "configure_mission (range_nmi, cruise_mach, cruise_altitude_ft, num_passengers), "
            "run_mission, then get_results / get_trajectory. "
            "Higher fidelity than the sibling nseg-mcp; use this when you need "
            "a fully optimized fuel/mass profile across the mission."
        ),
    )
    _register_tools(server)
    LOGGER.debug("FastMCP Aviary CPACS server configured (aviary=%s)", AVIARY_AVAILABLE)
    return server
