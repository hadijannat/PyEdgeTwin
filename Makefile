# PyEdgeTwin Makefile
# SoftwareX-compliant reproducibility infrastructure
#
# Quick reference:
#   make sandbox-up     - Start demo environment
#   make sandbox-down   - Stop and clean up
#   make reproduce      - Generate reproducible figures/data
#   make test           - Run all tests
#   make lint           - Check code quality

.PHONY: help install dev-install test lint typecheck sandbox-up sandbox-down reproduce clean

PYTHON := python3
EXAMPLE_DIR := examples/motor_filtering

help:
	@echo "PyEdgeTwin Development Commands"
	@echo "================================"
	@echo "  make install        Install package"
	@echo "  make dev-install    Install with dev dependencies"
	@echo "  make test           Run unit tests"
	@echo "  make lint           Run linter and formatter check"
	@echo "  make typecheck      Run type checker"
	@echo "  make sandbox-up     Start demo Docker environment"
	@echo "  make sandbox-down   Stop demo environment"
	@echo "  make reproduce      Generate reproducible data and figures"
	@echo "  make clean          Clean build artifacts"

# =============================================================================
# Installation
# =============================================================================

install:
	$(PYTHON) -m pip install -e .

dev-install:
	$(PYTHON) -m pip install -e ".[dev]"

# =============================================================================
# Quality Checks
# =============================================================================

test:
	pytest tests/unit -v --cov=pyedgetwin --cov-report=term

test-all:
	pytest tests/ -v --cov=pyedgetwin --cov-report=term

lint:
	ruff check src/
	ruff format --check src/

format:
	ruff format src/

typecheck:
	mypy src/pyedgetwin/ --ignore-missing-imports

check: lint typecheck test

# =============================================================================
# Docker Compose Demo
# =============================================================================

sandbox-up:
	@echo "Starting PyEdgeTwin demo environment..."
	cd $(EXAMPLE_DIR) && cp -n .env.example .env 2>/dev/null || true
	cd $(EXAMPLE_DIR) && docker compose up -d
	@echo ""
	@echo "Services starting. Wait ~30s for initialization."
	@echo "Dashboard: http://localhost:8501"
	@echo "InfluxDB:  http://localhost:8086"

sandbox-down:
	@echo "Stopping PyEdgeTwin demo environment..."
	cd $(EXAMPLE_DIR) && docker compose down -v

sandbox-logs:
	cd $(EXAMPLE_DIR) && docker compose logs -f

sandbox-status:
	cd $(EXAMPLE_DIR) && docker compose ps

# =============================================================================
# Reproducibility (SoftwareX requirement)
# =============================================================================

reproduce: sandbox-up
	@echo "Waiting for services to initialize (60s)..."
	sleep 60
	@echo "Generating reproducible data export and figure..."
	cd $(EXAMPLE_DIR) && $(PYTHON) scripts/reproduce_figure.py
	@echo ""
	@echo "Reproducible outputs generated in $(EXAMPLE_DIR)/output/"
	@echo "  - twin_data.csv       : Exported time-series data"
	@echo "  - figure_raw_vs_twin.png : Paper figure"

# =============================================================================
# Build & Distribution
# =============================================================================

build:
	$(PYTHON) -m build

clean:
	rm -rf build/ dist/ *.egg-info
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# =============================================================================
# Documentation
# =============================================================================

docs:
	cd docs && mkdocs serve

docs-build:
	cd docs && mkdocs build
