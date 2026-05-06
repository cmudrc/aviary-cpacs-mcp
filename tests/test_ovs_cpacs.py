"""OVS - Output Verification System checks for Aviary CPACS MCP output.

Validates that the Aviary adapter writes expected XPaths with plausible values.
Self-contained: no cross-repo dependencies.
"""

from xml.etree import ElementTree as ET

SAMPLE_AVIARY_OUTPUT = """\
<?xml version="1.0"?>
<cpacs>
  <vehicles>
    <aircraft>
      <model uID="test">
        <name>OVS Test Aircraft</name>
        <analysisResults>
          <mission>
            <backend>aviary</backend>
            <success>true</success>
            <converged>true</converged>
            <totalFuelBurnedKg>5812.3</totalFuelBurnedKg>
            <fuelBurnedKg>5812.3</fuelBurnedKg>
            <gtowKg>62732.4</gtowKg>
            <wingMassKg>6421.2</wingMassKg>
            <reserveFuelKg>581.2</reserveFuelKg>
            <zeroFuelWeightKg>56338.9</zeroFuelWeightKg>
            <runtimeSeconds>42.7</runtimeSeconds>
            <iterations>27</iterations>
          </mission>
        </analysisResults>
      </model>
    </aircraft>
  </vehicles>
</cpacs>
"""


def test_aviary_output_structure():
    root = ET.fromstring(SAMPLE_AVIARY_OUTPUT)
    assert root.tag == "cpacs"
    assert root.find(".//vehicles/aircraft") is not None


def test_aviary_results_present():
    root = ET.fromstring(SAMPLE_AVIARY_OUTPUT)
    mission = root.find(".//analysisResults/mission")
    assert mission is not None


def test_aviary_backend():
    root = ET.fromstring(SAMPLE_AVIARY_OUTPUT)
    be = root.find(".//analysisResults/mission/backend")
    assert be is not None and be.text == "aviary"


def test_aviary_converged():
    root = ET.fromstring(SAMPLE_AVIARY_OUTPUT)
    conv = root.find(".//analysisResults/mission/converged")
    assert conv is not None and conv.text in ("true", "false", "True", "False")


def test_aviary_fuel_burned_range():
    root = ET.fromstring(SAMPLE_AVIARY_OUTPUT)
    el = root.find(".//analysisResults/mission/fuelBurnedKg")
    assert el is not None and el.text is not None
    val = float(el.text)
    assert 0.0 <= val <= 500000.0


def test_aviary_gtow_range():
    root = ET.fromstring(SAMPLE_AVIARY_OUTPUT)
    el = root.find(".//analysisResults/mission/gtowKg")
    assert el is not None and el.text is not None
    val = float(el.text)
    assert 0.0 <= val <= 1e7


def test_aviary_wing_mass_range():
    root = ET.fromstring(SAMPLE_AVIARY_OUTPUT)
    el = root.find(".//analysisResults/mission/wingMassKg")
    assert el is not None and el.text is not None
    val = float(el.text)
    assert 0.0 < val <= 1e6


def test_aviary_reserve_fuel_below_total():
    root = ET.fromstring(SAMPLE_AVIARY_OUTPUT)
    res = root.find(".//analysisResults/mission/reserveFuelKg")
    fb = root.find(".//analysisResults/mission/fuelBurnedKg")
    assert res is not None and res.text is not None
    assert fb is not None and fb.text is not None
    assert float(res.text) <= float(fb.text)
