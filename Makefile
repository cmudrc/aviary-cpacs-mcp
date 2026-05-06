PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
PIP ?= $(PYTHON) -m pip
PYTEST ?= $(PYTHON) -m pytest
RUFF ?= $(PYTHON) -m ruff
MYPY ?= $(PYTHON) -m mypy
BUILD ?= $(PYTHON) -m build
TWINE ?= $(PYTHON) -m twine

.PHONY: help dev install-dev lint fmt fmt-check type test qa ci clean

help:
	@echo "Common targets:"
	@echo "  dev            Install project in editable mode with dev dependencies."
	@echo "  test           Run the default pytest suite."
	@echo "  qa             Run lint, formatting, typing, and tests."
	@echo "  ci             Full CI check (qa)."
	@echo "  clean          Remove generated artifacts."

dev:
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

install-dev: dev

lint:
	$(RUFF) check .

fmt:
	$(RUFF) format .

fmt-check:
	$(RUFF) format --check .

type:
	$(MYPY) src

test:
	PYTHONPATH=src $(PYTEST) -q

qa: lint fmt-check type test

ci: qa

clean:
	rm -rf .coverage .mypy_cache .pytest_cache .ruff_cache artifacts build dist src/*.egg-info src/aviary_cpacs_mcp.egg-info
	find . -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
	find . -type f \( -name "*.pyc" -o -name ".coverage.*" \) -exec rm -f {} + 2>/dev/null || true
