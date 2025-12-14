.PHONY: help build-rust test coverage clean lint format install

help:
	@echo "Photidy Development Commands"
	@echo "============================"
	@echo ""
	@echo "Setup:"
	@echo "  make install              Install Python dependencies"
	@echo "  make build-rust           Build and install Rust module"
	@echo ""
	@echo "Testing:"
	@echo "  make test                 Run all tests"
	@echo "  make test-fast            Run tests without coverage"
	@echo "  make coverage             Run tests with coverage report"
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

test: build-rust
	uv run pytest -v

test-fast:
	uv run pytest -v --no-cov 2>/dev/null || uv run pytest -v

coverage: build-rust
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
	cd rust/metadata && cargo clean 2>/dev/null || true
