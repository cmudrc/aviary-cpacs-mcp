# Contributing to `aviary-cpacs-mcp`

Thanks for improving the project.

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
make dev
```

The `dev` extra installs linting, formatting, typing, testing, and pre-commit tooling.

To enable NASA Aviary (trajectory optimization):

```bash
pip install -e ".[aviary]"
```

## Local Quality Checks

Run these before opening a pull request:

```bash
make fmt
make lint
make type
make test
```

Optional but recommended:

```bash
pre-commit install
pre-commit run --all-files
```

## Pull Request Guidelines

- Keep changes focused.
- Add or update tests for behavior changes.
- Update docs and examples when user-facing workflows change.
- Describe what changed and how you validated it.

## Code Style

- Python 3.12+ target.
- Ruff for formatting and linting.
- Mypy for static type checking.
- Pytest for tests.

## Backends

- **Aviary** (primary): NASA's trajectory optimizer. Requires `openmdao==3.36.0`,
  `dymos==1.13.1`, `aviary==0.9.10`.
- **NSEG** (fallback): Built-in segment physics. No extra dependencies.
