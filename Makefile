# Makefile for linkedin-job-scraper
# Simple commands for common development tasks

.PHONY: \
	help install dev \
	playwright-install playwright-install-deps \
	prek \
	test test-cov lint format type-check check \
	docs docs-serve docs-zensical docs-serve-zensical \
	clean build publish release

UV_RUN_ACTIVE := uv run
UV_SYNC_ACTIVE := uv sync
ifdef VIRTUAL_ENV
UV_RUN_ACTIVE := uv run --active
UV_SYNC_ACTIVE := uv sync --active
endif

# Default target
help:
	@echo "LinkedIn Job Scraper - Development Commands"
	@echo ""
	@echo "  make install     Install dependencies"
	@echo "  make dev         Install with dev dependencies"
	@echo "  make playwright-install       Install Playwright Chromium"
	@echo "  make playwright-install-deps  Install Chromium with system deps"
	@echo "  make prek        Run prek hooks on all files"
	@echo "  make test        Run tests"
	@echo "  make lint        Run linter"
	@echo "  make format      Format code"
	@echo "  make type-check  Run type checker"
	@echo "  make docs        Build documentation"
	@echo "  make docs-zensical  Build documentation with Zensical"
	@echo "  make clean       Clean build artifacts"
	@echo "  make build       Build package"
	@echo "  make release     Bump version + tag (VERSION=0.1.1)"
	@echo ""

# Install production dependencies
install:
	$(UV_SYNC_ACTIVE)

# Install with dev dependencies
dev:
	$(UV_SYNC_ACTIVE) --extra dev
	$(UV_RUN_ACTIVE) prek install
	$(UV_RUN_ACTIVE) playwright install chromium

# Install Playwright browser only
playwright-install:
	$(UV_RUN_ACTIVE) playwright install chromium

# Install Playwright browser with system deps (Linux CI or container)
playwright-install-deps:
	$(UV_RUN_ACTIVE) playwright install chromium --with-deps

# Run prek on all files
prek:
	$(UV_RUN_ACTIVE) prek run --all-files

# Run tests
test:
	$(UV_RUN_ACTIVE) pytest tests/ -v

# Run tests with coverage
test-cov:
	$(UV_RUN_ACTIVE) pytest tests/ --cov=src/ljs --cov-report=html --cov-report=term

# Run linter
lint:
	$(UV_RUN_ACTIVE) ruff check src/ tests/

# Format code
format:
	$(UV_RUN_ACTIVE) ruff format src/ tests/
	$(UV_RUN_ACTIVE) ruff check --fix src/ tests/

# Run type checker
type-check:
	$(UV_RUN_ACTIVE) ty check src/

# Run all checks (lint + type-check + test)
check: lint type-check test

# Build documentation
docs:
	$(UV_RUN_ACTIVE) mkdocs build

# Serve documentation locally
docs-serve:
	$(UV_RUN_ACTIVE) mkdocs serve

# Build documentation with Zensical
docs-zensical:
	$(UV_RUN_ACTIVE) zensical build

# Serve documentation with Zensical
docs-serve-zensical:
	$(UV_RUN_ACTIVE) zensical serve

# Clean build artifacts
clean:
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
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

# Bump version + create tag (does not push)
release:
	@if [ -z "$(VERSION)" ]; then echo "VERSION is required (e.g., make release VERSION=0.2.0)"; exit 1; fi
	@bad="$$(git status --porcelain | awk '{print $$2}' | grep -vE '^(pyproject\\.toml|CHANGELOG\\.md)$$' || true)"; \
	if [ -n "$$bad" ]; then \
		echo "Refusing to create a release with unrelated working tree changes:"; \
		echo "$$bad"; \
		exit 1; \
	fi
	@$(UV_RUN_ACTIVE) python - <<'PY'\nimport re\nfrom pathlib import Path\n\npath = Path(\"pyproject.toml\")\ntext = path.read_text(encoding=\"utf-8\")\nnew_version = \"$(VERSION)\"\npattern = r'^(version\\s*=\\s*\")([^\"]+)(\"\\s*)$'\nrepl = r\"\\\\1\" + new_version + r\"\\\\3\"\nnew_text, count = re.subn(pattern, repl, text, flags=re.MULTILINE)\nif count != 1:\n    raise SystemExit(\"Failed to update version in pyproject.toml\")\npath.write_text(new_text, encoding=\"utf-8\")\nprint(f\"Updated pyproject.toml version to {new_version}\")\nPY
	@git add pyproject.toml CHANGELOG.md
	@if git diff --cached --quiet; then echo "No changes to commit."; else git commit -m "chore(release): v$(VERSION)"; fi
	@git tag v$(VERSION)
	@echo "Created git tag v$(VERSION). Push with: git push --follow-tags"
