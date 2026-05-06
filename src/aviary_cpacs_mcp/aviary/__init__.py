"""Aviary integration layer for the Aviary CPACS MCP.

Wraps NASA's Aviary Level 2 API for trajectory optimization and fuel burn
analysis. Falls back gracefully when Aviary is not installed.
"""

try:
    import aviary  # noqa: F401

    AVIARY_AVAILABLE = True
except ImportError:
    AVIARY_AVAILABLE = False

__all__ = ["AVIARY_AVAILABLE"]
