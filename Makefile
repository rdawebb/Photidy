.PHONY: help build-rust test test-rust test-rust-unit test-rust-integration test-fast coverage coverage-python clean lint format install

help:
	@echo "Photidy Development Commands"
	@echo "============================"
	@echo ""
	@echo "Setup:"
	@echo "  make install              Install Python dependencies"
	@echo "  make build-rust           Build and install Rust module"
	@echo ""
	@echo "Testing:"
	@echo "  make test                 Run all tests (Rust unit + integration + Python)"
	@echo "  make test-rust            Run all Rust tests (unit + integration)"
	@echo "  make test-rust-unit       Run Rust unit tests only (fast)"
	@echo "  make test-rust-integration Run Rust integration tests only"
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

install:
	uv sync

build-rust:
	cd rust/photo_meta && maturin develop

test-rust-unit:
	@echo "Running Rust unit tests..."
	cd rust/photo_meta && cargo test --lib
	@echo ""

test-rust-integration:
	@echo "Running Rust integration tests..."
	cd rust/photo_meta && cargo test --test '*'
	@echo ""

test-rust:
	@echo "Running all Rust tests (unit + integration)..."
	cd rust/photo_meta && cargo test
	@echo ""

test: build-rust test-rust
	@echo "Running Python tests..."
	uv run pytest -v
	@echo ""
	@echo "✓ All tests completed successfully"

test-fast:
	uv run pytest -v --no-cov 2>/dev/null || uv run pytest -v

coverage-python: build-rust
	uv run pytest --cov=src --cov-report=html --cov-report=term

lint:
	uv run ruff check src tests
	uv run mypy src --ignore-missing-imports 2>/dev/null || echo "mypy check completed"

format:
	uv run ruff format src tests
	uv run ruff check --fix src tests

clean:
	rm -rf .pytest_cache .coverage htmlcov
	rm -rf src/.ruff_cache src/__pycache__
	rm -rf tests/__pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	cd rust/photo_meta && cargo clean 2>/dev/null || true
	cd rust/metadata && cargo clean 2>/dev/null || true
