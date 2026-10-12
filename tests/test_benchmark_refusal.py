"""Refuse by default when a run would be Aviary's benchmark aircraft (2026-10-12).

For the public D150 the adapter reads only the reference area, which this
Aviary configuration does not use, so a "D150 mission" would be the benchmark
aircraft at the requested range, passengers and cruise point. Mayank's
decision: refuse unless the caller says allow_benchmark_aircraft.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from aviary_cpacs_mcp import cpacs_adapter as a
from aviary_cpacs_mcp.aviary import AVIARY_AVAILABLE
from aviary_cpacs_mcp.tools import configure_mission, create_mission, run_mission, set_aircraft

D150 = Path(__file__).resolve().parents[2] / "aircraft-analysis" / "examples" / "D150_v30.xml"
MP = {"range_nmi": 1500.0, "num_passengers": 150, "cruise_mach": 0.78, "cruise_altitude_ft": 35000.0}


def test_refusal_helper_logic() -> None:
    assert a.benchmark_refusal({}) is not None
    assert a.benchmark_refusal({"Aircraft.Wing.AREA": 122.4})["error"]["type"] == "benchmark_aircraft_only"
    assert (
        "Aircraft.Wing.AREA set but without effect"
        in a.benchmark_refusal({"Aircraft.Wing.AREA": 122.4})["error"]["message"]
    )
    assert a.benchmark_refusal({"Aircraft.Wing.ASPECT_RATIO": 9.4}) is None
    assert a.benchmark_refusal({"Aircraft.Fuselage.LENGTH": 37.6, "Aircraft.Wing.AREA": 1.0}) is None


@pytest.mark.skipif(not AVIARY_AVAILABLE or not D150.is_file(), reason="needs Aviary and the public D150")
def test_d150_is_refused_by_default_and_runs_with_the_flag() -> None:
    os.environ.setdefault("OPENMDAO_REPORTS", "0")
    xml = D150.read_text()
    out_xml, r = a.run_adapter(xml, mission_profile=dict(MP))
    assert r["error"]["type"] == "benchmark_aircraft_only"
    assert out_xml == xml  # nothing written
    _, r2 = a.run_adapter(xml, mission_profile={**MP, "allow_benchmark_aircraft": True})
    assert r2["success"] and r2["from_cpacs"] == "nothing" and "benchmark" in r2["base_model"]


@pytest.mark.skipif(not AVIARY_AVAILABLE, reason="needs Aviary")
def test_session_route_refuses_without_an_effective_input() -> None:
    os.environ.setdefault("OPENMDAO_REPORTS", "0")
    sid = create_mission({"name": "refusal"})["session_id"]
    configure_mission({"session_id": sid, **MP})
    set_aircraft({"session_id": sid, "wing_area_m2": 115.0})
    r = run_mission({"session_id": sid})
    assert r["error"]["type"] == "benchmark_aircraft_only"
    set_aircraft({"session_id": sid, "aspect_ratio": 11.0})
    r2 = run_mission({"session_id": sid})
    assert r2.get("success"), r2.get("error")
