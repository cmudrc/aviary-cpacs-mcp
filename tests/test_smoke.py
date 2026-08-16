"""Import and surface smoke tests for the Aviary CPACS MCP.

These replace a previous file that defined a CPACS XML string as a constant and
then asserted facts about that same constant, so it exercised none of this
package and could not fail. The checks here import the real modules and assert
on the real tool surface, so they break if the package breaks.

They deliberately do not run Aviary. A trajectory solve needs the full
OpenMDAO/Dymos stack and is covered by the solver-integration job, which is
gated to Linux.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

#: Every tool module the server is expected to expose.
EXPECTED_TOOL_MODULES = [
    "check_constraints",
    "configure_mission",
    "create_mission",
    "get_results",
    "get_trajectory",
    "run_mission",
    "set_aircraft",
]


def test_package_imports() -> None:
    """The top-level package imports without side effects."""
    import aviary_cpacs_mcp

    assert aviary_cpacs_mcp.__name__ == "aviary_cpacs_mcp"


def test_cpacs_adapter_exposes_the_read_write_cycle() -> None:
    """The adapter keeps the read/write contract the orchestrator relies on."""
    from aviary_cpacs_mcp import cpacs_adapter

    for name in ("read_from_cpacs", "write_to_cpacs", "run_adapter"):
        assert callable(getattr(cpacs_adapter, name)), name


def test_aviary_availability_is_reported_not_assumed() -> None:
    """Aviary's presence is a flag, so a missing solver fails loudly, not silently."""
    from aviary_cpacs_mcp import cpacs_adapter

    assert isinstance(cpacs_adapter.AVIARY_AVAILABLE, bool)


@pytest.mark.parametrize("module_name", EXPECTED_TOOL_MODULES)
def test_tool_module_imports(module_name: str) -> None:
    """Each tool module imports, so a broken tool surfaces here rather than at runtime."""
    module = __import__(f"aviary_cpacs_mcp.tools.{module_name}", fromlist=[module_name])
    assert module is not None


def test_read_from_cpacs_parses_a_minimal_document() -> None:
    """The adapter reads a well-formed CPACS document without needing Aviary."""
    from aviary_cpacs_mcp import cpacs_adapter

    cpacs = """<?xml version="1.0"?>
<cpacs>
  <vehicles>
    <aircraft>
      <model uID="smoke">
        <reference><area>122.4</area><length>4.2</length></reference>
      </model>
    </aircraft>
  </vehicles>
</cpacs>"""
    # Guard the fixture itself, so a malformed literal fails here and not inside
    # the adapter, where the cause would be harder to read.
    assert ET.fromstring(cpacs).tag == "cpacs"

    result = cpacs_adapter.read_from_cpacs(cpacs)
    assert isinstance(result, dict)
