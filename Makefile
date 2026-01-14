# Makefile for linkedin-job-scraper
# Simple commands for common development tasks

.PHONY: help install dev test lint format type-check docs clean build

# Default target
help:
	@echo "LinkedIn Job Scraper - Development Commands"
	@echo ""
	@echo "  make install     Install dependencies"
	@echo "  make dev         Install with dev dependencies"
	@echo "  make test        Run tests"
	@echo "  make lint        Run linter"
	@echo "  make format      Format code"
	@echo "  make type-check  Run type checker"
	@echo "  make docs        Build documentation"
	@echo "  make clean       Clean build artifacts"
	@echo "  make build       Build package"
	@echo ""

# Install production dependencies
install:
	uv sync

# Install with dev dependencies
dev:
	uv sync --dev
	uv run pre-commit install
	uv run playwright install chromium

# Run tests
test:
	uv run pytest tests/ -v

# Run tests with coverage
test-cov:
	uv run pytest tests/ --cov=src/linkedin_scraper --cov-report=html --cov-report=term

# Run linter
lint:
	uv run ruff check src/ tests/

# Format code
format:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

# Run type checker
type-check:
	uv run mypy src/

# Run all checks (lint + type-check + test)
check: lint type-check test

# Build documentation
docs:
	uv run mkdocs build

# Serve documentation locally
docs-serve:
	uv run mkdocs serve

# Clean build artifacts
clean:
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf site/
	find . -type d -name "__pycache__" -exec rm -rf {} +

# Build package
build: clean
	uv build

# Publish to PyPI (use with caution)
publish: build
	uv publish
