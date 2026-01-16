# Install in editable mode
install:
	uv pip install -e .

# Install development dependencies
install-dev:
	uv sync --all-extras

# Build Rust extension
build-rust:
	uv run python scripts/build_rust.py

# Test Rust extension
test-rust: build-rust
	uv run python scripts/test_rust.py

# Run all tests
test: build-rust test-rust
	uv run pytest -v

# Test Python code
test-python:
	uv run pytest -v --no-cov

# Coverage report for Python code
cov-python: build-rust
	uv run pytest --cov=src --cov-report=html --cov-report=term

# Lint Python code
lint:
	uv run ruff check --fix src tests

# Format Python code
format:
	uv run ruff format src tests

# Type check Python code
type:
	uv run ty check src tests

# Run all checks
check: lint format type

# Run pre-commit hooks
pre:
	prek run --all-files

# Clean up temporary files
clean:
	uv run python scripts/clean.py

# Bundle application
bundle:
	pyinstaller pyinstaller/photidy.spec

# Run application
run:
	./.venv/bin/python -m src.ui.main
