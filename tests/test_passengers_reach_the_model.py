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
    # The D150 file carries none of the elements the adapter reads for aspect ratio,
    # sweep, taper or fuselage length, so nothing effective comes from it.
    assert r["from_cpacs"] == "nothing"
    assert "Aircraft.Wing.AREA" in r["set_but_without_effect"]
    assert "num_passengers=150" in r["from_caller"]


def test_which_cpacs_inputs_matter_is_pinned() -> None:
    """If a future Aviary setup starts reading the wing area, this fails and the
    EFFECTIVE/INERT lists in the adapter must be re-measured."""
    from aviary_cpacs_mcp.aviary import runner as rr

    base = {
        "Aircraft.Wing.AREA": 122.4,
        "Aircraft.Wing.ASPECT_RATIO": 9.4,
        "Aircraft.Wing.SWEEP": 25.0,
        "Aircraft.Wing.TAPER_RATIO": 0.25,
        "Aircraft.Fuselage.LENGTH": 37.6,
    }
    mc = {"range_nmi": 1500, "num_passengers": 150, "cruise_mach": 0.78, "cruise_altitude_ft": 35000}

    def gtow(params: dict) -> float:
        prob = rr.create_aviary_problem(aircraft_params=params, mission_config=mc)
        res = rr.run_aviary(prob, timeout_seconds=300)
        return rr.extract_results(prob, res["converged"])["gtow_kg"]

    g0 = gtow(base)
    for name in a.INERT_PARAMS:
        p = dict(base)
        p[name] = base[name] * 1.2
        assert abs(gtow(p) - g0) < 0.01, name  # identical to the gram; solver noise is micrograms
    for name in a.EFFECTIVE_PARAMS:
        p = dict(base)
        p[name] = base[name] * 1.2
        assert abs(gtow(p) - g0) > 10.0, name
