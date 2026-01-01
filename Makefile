.PHONY: help build-rust test test-rust test-rust-unit test-rust-integration test-fast coverage coverage-python clean lint format install

help:
	@echo "Photidy Development Commands"
	@echo "============================"
	@echo ""
	@echo "Setup:"
	@echo "  make install              Install Python dependencies"
	@echo "  make install-dev          Install development dependencies"
	@echo "  make build-rust           Build and install Rust module"
	@echo ""
	@echo "Testing:"
	@echo "  make test                 Run all tests (Rust + Python)"
	@echo "  make test-rust            Run all Rust unit tests"
	@echo "  make test-fast            Run Python tests only (without Rust)"
	@echo "  make coverage-python      Run Python tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint                 Run linting and formatting checks (ruff)"
	@echo "  make format               Format code with ruff"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean                Remove build artifacts and cache"
	@echo ""
	@echo "Packaging:"
	@echo "  make bundle               Bundle application with PyInstaller"
	@echo ""
	@echo "Running:"
	@echo "  make run                  Run the application"
	@echo ""
	@echo "Use 'make <command>' to execute a specific command."
	@echo ""

install:
	uv sync

install-dev:
	uv sync --all-extras

build-rust:
	uv run python scripts/build_rust.py
	@echo "✓ Rust module built and installed successfully"

test-rust:
	@echo "Running all Rust unit tests..."
	uv run python scripts/test_rust.py
	@echo ""

test: build-rust test-rust
	@echo "Running Python tests..."
	uv run pytest -v
	@echo ""
	@echo "✓ All tests completed successfully"

test-fast:
	uv run pytest -v --no-cov || uv run pytest -v

coverage-python: build-rust
	uv run pytest --cov=src --cov-report=html --cov-report=term

lint:
	uv run ruff check src tests

format:
	uv run ruff format src tests
	uv run ruff check --fix src tests

clean:
	uv run python scripts/clean.py

bundle:
	pyinstaller pyinstaller/photidy.spec
	@echo "✓ Application bundled successfully"

run:
	uv run python -m src.ui.main

run-cli:
	uv run python -m src.cli.cli