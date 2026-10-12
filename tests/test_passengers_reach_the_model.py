"""The passenger count the adapter requires must change the answer (2026-10-12).

Found in a Kiro study dry run: 150, 162 and 250 passengers returned the same
take-off mass, because the count never reached the Aviary model.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from aviary_cpacs_mcp import cpacs_adapter as a
from aviary_cpacs_mcp.aviary import AVIARY_AVAILABLE

D150 = Path(__file__).resolve().parents[2] / "aircraft-analysis" / "examples" / "D150_v30.xml"

pytestmark = pytest.mark.skipif(not AVIARY_AVAILABLE or not D150.is_file(), reason="needs Aviary and the public D150")


def _fly(pax: int) -> dict:
    os.environ.setdefault("OPENMDAO_REPORTS", "0")
    _, r = a.run_adapter(
        D150.read_text(),
        mission_profile={
            "range_nmi": 1500.0,
            "num_passengers": pax,
            "cruise_mach": 0.78,
            "cruise_altitude_ft": 35000.0,
        },
    )
    assert r.get("success"), r.get("error")
    return r


def test_more_passengers_means_a_heavier_aircraft() -> None:
    r150, r250 = _fly(150), _fly(250)
    assert r150["num_passengers"] == 150 and r250["num_passengers"] == 250
    assert r250["gtow_kg"] > r150["gtow_kg"] + 1000  # 100 people and bags, at least a tonne
    assert r250["zero_fuel_weight_kg"] > r150["zero_fuel_weight_kg"]
    assert r250["fuel_burned_kg"] > r150["fuel_burned_kg"]


def test_result_says_what_was_flown() -> None:
    r = _fly(150)
    assert "aircraft_for_bench_FwFm" in r["base_model"]
    assert "Aircraft.Wing.AREA" in r["from_cpacs"]
    assert "num_passengers=150" in r["from_caller"]
