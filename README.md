# Aviary CPACS MCP

An MCP server for **CPACS-integrated NASA Aviary trajectory-coupled mission optimization**.

Part of the shared-CPACS aircraft analysis pipeline at the [Design Research Collective](https://github.com/cmudrc):

- [`tigl-mcp`](https://github.com/cmudrc/tigl-mcp) — geometry / STEP CAD export
- [`su2-mcp`](https://github.com/cmudrc/su2-mcp) — Euler / RANS aerodynamics
- [`pycycle-mcp`](https://github.com/cmudrc/pycycle-mcp) — turbofan engine cycle analysis
- **`aviary-cpacs-mcp` (this repo)** — NASA Aviary trajectory-coupled mission optimization
- [`nseg-mcp`](https://github.com/cmudrc/nseg-mcp) — fast segment-based mission analysis (sibling)
- [`aircraft-analysis`](https://github.com/cmudrc/aircraft-analysis) — pipeline orchestrator + documentation

## What this MCP does

Wraps NASA Aviary (with Dymos / OpenMDAO under the hood) so an AI agent or orchestration script can drive a trajectory-coupled mission optimization through MCP tool calls. It is the higher-fidelity sibling to `nseg-mcp` — slower, but produces a fully optimized fuel/mass profile across the mission.

Per Boeing's "one tool per MCP" guidance, NSEG and Aviary are deliberately split into separate MCP servers. The agent picks one per run based on the design question:

- Use **`aviary-cpacs-mcp`** when the question requires trajectory-coupled sizing or a full optimized mass + fuel profile.
- Use **`nseg-mcp`** when the question is point-performance trade studies or a fast Breguet-style sweep.

## Relation to `cmudrc/aviary-mcp`

The lab also maintains [`cmudrc/aviary-mcp`](https://github.com/cmudrc/aviary-mcp) (Jessica Ezemba) which exposes Aviary tooling more directly. **This repo (`aviary-cpacs-mcp`)** is the CPACS-integrated production version: it speaks the shared-CPACS schema, ships a CPACS adapter, and is wired into the `aircraft-analysis` orchestrator.

## Tools exposed

| Tool | Description |
|------|-------------|
| `create_mission` | Open a new analysis session |
| `close_mission` | Free session resources |
| `set_aircraft` | Set Aviary `Aircraft.*` design params (wing area, AR, sweep, taper, fuselage length, etc.) |
| `configure_mission` | `range_nmi`, `num_passengers`, `cruise_mach`, `cruise_altitude_ft`, `optimizer_max_iter` |
| `run_mission` | Execute Aviary + Dymos trajectory optimization |
| `get_results` | GTOW, fuel burn, wing mass, reserve fuel, zero-fuel weight, runtime, iterations |
| `get_trajectory` | Per-phase timeseries: time, altitude, Mach, mass, throttle, drag, distance |
| `check_constraints` | Pass/fail evaluation of `<=`, `>=`, `==` constraints on results |

## Quick start

```bash
pip install -e .

aviary-cpacs-mcp --transport stdio
# or
aviary-cpacs-mcp --transport http --host 0.0.0.0 --port 8004
```

## Shared-CPACS integration

The CPACS adapter (`src/aviary_cpacs_mcp/cpacs_adapter.py`) reads geometry from:

- `//vehicles/aircraft/model/reference/area`
- `//vehicles/aircraft/model/wings/wing/{aspectRatio,sweep/angle,taperRatio}`
- `//vehicles/aircraft/model/fuselages/fuselage/length`

and writes results to `//vehicles/aircraft/model/analysisResults/mission` with `<backend>aviary</backend>`.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT — see [LICENSE](LICENSE).
