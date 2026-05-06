"""Entry point for the Aviary CPACS MCP FastMCP server."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import Any, Literal, cast

from aviary_cpacs_mcp.server import build_server

TransportName = Literal["stdio", "http", "sse", "streamable-http"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aviary CPACS MCP server")
    parser.add_argument(
        "--transport",
        choices=("stdio", "http", "sse", "streamable-http"),
        default="stdio",
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8003)
    parser.add_argument("--path", help="Optional mount path for the HTTP endpoint.")
    parser.add_argument("--log-level", default="INFO")
    return parser


def _normalize_transport(transport: TransportName) -> TransportName:
    if transport == "http":
        return "streamable-http"
    return transport


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    app = build_server()
    transport = _normalize_transport(cast(TransportName, args.transport))

    transport_kwargs: dict[str, Any] = {
        "show_banner": False,
        "log_level": args.log_level,
    }
    if transport in {"sse", "streamable-http"}:
        transport_kwargs["host"] = args.host
        transport_kwargs["port"] = args.port
        if args.path is not None:
            transport_kwargs["path"] = args.path

    app.run(transport=transport, **transport_kwargs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
