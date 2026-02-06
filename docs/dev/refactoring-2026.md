<!-- START doctoc generated TOC please keep comment here to allow auto update -->

**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Project Refactoring Guide (2026 Best Practices)](#project-refactoring-guide-2026-best-practices)
  - [Summary of Changes](#summary-of-changes)
  - [1. Type Checking with Ty](#1-type-checking-with-ty)
    - [Problem](#problem)
    - [Solution](#solution)
    - [Commands](#commands)
  - [2. Git Repository Setup](#2-git-repository-setup)
    - [Initialize](#initialize)
    - [Reorganized `.gitignore`](#reorganized-gitignore)
  - [3. Dependency Management](#3-dependency-management)
    - [Tool: `uv` (replaces pip, pip-tools, poetry)](#tool-uv-replaces-pip-pip-tools-poetry)
    - [Dependency Analysis with `deptry`](#dependency-analysis-with-deptry)
  - [4. pyproject.toml Reorganization](#4-pyprojecttoml-reorganization)
    - [Structure (2026 Best Practice)](#structure-2026-best-practice)
  - [5. Testing with pytest-asyncio](#5-testing-with-pytest-asyncio)
    - [Problem](#problem)
    - [Solution](#solution)
    - [Commands](#commands)
  - [6. Prek Simplification](#6-prek-simplification)
    - [Problem](#problem)
    - [Solution](#solution)
    - [Commands](#commands)
  - [7. Documentation with MkDocs](#7-documentation-with-mkdocs)
    - [Custom Fonts (mkdocs.yml)](#custom-fonts-mkdocsyml)
    - [Build with Strict Mode](#build-with-strict-mode)
    - [Serve Locally](#serve-locally)
  - [8. Multi-Account Git Setup](#8-multi-account-git-setup)
    - [Problem](#problem)
    - [Solution](#solution)
    - [Step 1: Generate SSH Key](#step-1-generate-ssh-key)
    - [Step 2: Configure SSH (`~/.ssh/config`)](#step-2-configure-ssh-sshconfig)
    - [Step 3: Add Key to GitHub](#step-3-add-key-to-github)
    - [Step 4: Set Local Git Config (per-repo)](#step-4-set-local-git-config-per-repo)
    - [Step 5: Add Remote with Alias](#step-5-add-remote-with-alias)
    - [Step 6: Verify & Push](#step-6-verify-push)
  - [Quick Reference Commands](#quick-reference-commands)
  - [Files Modified](#files-modified)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Project Refactoring Guide (2026 Best Practices)

This document captures the complete refactoring process applied to this project, following Python and tooling best practices as of January 2026.

---

## Summary of Changes

| Area | What Changed |
|------|-------------|
| Type Checking | Fixed all ty errors, enriched `tyconfig.json` |
| Git | Initialized repo, reorganized `.gitignore` |
| Dependencies | Updated to latest versions, verified compatibility |
| Build Config | Reorganized `pyproject.toml` with clear sections |
| Testing | Fixed `pytest-asyncio` config for v1.x |
| Prek | Simplified to use ruff as single tool |
| Docs | Custom fonts (Inter + JetBrains Mono), strict build |
| Multi-account Git | Per-repo SSH config for specific GitHub account |

---

## 1. Type Checking with Ty

### Problem

Ty was failing due to missing/invalid config.

### Solution

Created a proper `tyconfig.json` with comprehensive excludes:

```json
{
  "include": ["src"],
  "exclude": [
    "**/__pycache__",
    "**/node_modules",
    "**/.venv",
    "**/venv",
    "**/.git",
    "**/build",
    "**/dist",
    "**/*.egg-info",
    "**/site-packages",
    "**/.pytest_cache",
    "**/.ruff_cache",
    "**/htmlcov",
    "**/site",
    "**/docs"
  ],
  "venvPath": ".",
  "venv": ".venv"
}
```

### Commands

```bash
uv run ty check src/

# If you activated a venv:
# uv run --active ty check src/
```

---

## 2. Git Repository Setup

### Initialize

```bash
git init
```

### Reorganized `.gitignore`

Structured with clear sections:

- Python artifacts
- Virtual environments
- IDE/Editor files
- Testing & Coverage
- Build & Distribution
- Documentation
- Environment & Secrets
- Project Data
- Temporary & System Files

Key principle: **Group related patterns, add comments for clarity.**

---

## 3. Dependency Management

### Tool: `uv` (replaces pip, pip-tools, poetry)

```bash
# Sync all extras
uv sync --all-extras

# Lock dependencies
uv lock

# Check lock is up to date
uv lock --check
```

### Dependency Analysis with `deptry`

```bash
uv run --with deptry deptry src/
```

Added config to ignore false positives for CLI dev tools:

```toml
[tool.deptry]
extend_exclude = ["docs", "tests"]
ignore = ["DEP002"]
per_rule_ignores = { DEP002 = [
    "linkedin-job-scraper",  # Self-reference
    "coverage", "mkdocs", "pytest", "ruff",  # CLI tools
    # ... etc
] }
```

---

## 4. pyproject.toml Reorganization

### Structure (2026 Best Practice)

```toml
# =============================================================================
# PROJECT METADATA
# =============================================================================
[project]
name = "..."
version = "..."
# ...

[project.optional-dependencies]
dev = [...]
lint = [...]
test = [...]
types = [...]
docs = [...]

# =============================================================================
# BUILD SYSTEM
# =============================================================================
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

# =============================================================================
# TOOL CONFIGS (alphabetical, with doc links)
# =============================================================================
[tool.coverage.run]
# https://coverage.readthedocs.io/

[tool.pytest.ini_options]
# https://docs.pytest.org/

[tool.ruff]
# https://docs.astral.sh/ruff/
```

---

## 5. Testing with pytest-asyncio

### Problem

`pytest-asyncio` 1.x changed config options.

### Solution

Minimal config that works:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
asyncio_mode = "auto"
addopts = ["-ra", "-q", "--strict-markers", "--strict-config"]
```

**Note**: `asyncio_default_fixture_loop_scope` is NOT supported in pytest-asyncio 1.3.0.

### Commands

```bash
# Install dev/test dependencies first
uv sync --extra test

# Run tests
uv run pytest

# Optional: parallel run
uv run pytest -n auto --tb=short
```

---

## 6. Prek Simplification

### Problem

Multiple tools doing the same thing:

- `bandit` → duplicates ruff's `S` rules
- `reorder-python-imports` → duplicates ruff's `I` rules
- `pyupgrade` → duplicates ruff's `UP` rules

### Solution

Use **ruff as the single tool** for everything:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-json
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: check-case-conflict
      - id: detect-private-key
      - id: debug-statements

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.14.11
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/commitizen-tools/commitizen
    rev: v4.1.0
    hooks:
      - id: commitizen
        stages: [commit-msg]
```

### Commands

```bash
prek clean && prek install
prek run --all-files
```

---

## 7. Documentation with MkDocs

### Custom Fonts (mkdocs.yml)

```yaml
theme:
  name: material
  font:
    text: Inter              # Modern, readable sans-serif
    code: JetBrains Mono     # Designed for code, with ligatures
```

### Build with Strict Mode

```bash
uv run mkdocs build --strict
```

### Serve Locally

```bash
uv run python -m mkdocs serve --dev-addr 127.0.0.1:8000
```

---

## 8. Multi-Account Git Setup

### Problem

Multiple GitHub accounts on one machine.

### Solution

Per-repository config with SSH host aliases.

### Step 1: Generate SSH Key

```bash
ssh-keygen -t ed25519 -C "your-email@example.com" -f ~/.ssh/id_ed25519_github_account2
```

### Step 2: Configure SSH (`~/.ssh/config`)

```
Host github-account2
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_github_account2
    IdentitiesOnly yes
```

### Step 3: Add Key to GitHub

```bash
cat ~/.ssh/id_ed25519_github_account2.pub
# Copy → GitHub → Settings → SSH Keys → New
```

### Step 4: Set Local Git Config (per-repo)

```bash
git config user.name "cetincurio"
git config user.email "your-email@example.com"
```

### Step 5: Add Remote with Alias

```bash
git remote add origin git@github-account2:cetincurio/linkedin-job-scraper.git
```

### Step 6: Verify & Push

```bash
ssh -T git@github-account2  # Test connection
git push -u origin main
```

---

## Quick Reference Commands

```bash
# Full quality check
uv run ruff check src/ tests/
uv run ruff format src/ tests/
uv run ty check src/
uv run pytest

# Prek
uv run prek run --all-files

# Documentation
uv run mkdocs build --strict
uv run python -m mkdocs serve

# Dependency analysis
uv run --with deptry deptry src/
```

---

## Files Modified

| File | Changes |
|------|---------|
| `pyproject.toml` | Reorganized, updated deps, fixed pytest config |
| `tyconfig.json` | Created with proper excludes |
| `.gitignore` | Reorganized with clear sections |
| `.pre-commit-config.yaml` | Simplified to ruff-only |
| `mkdocs.yml` | Added custom fonts |
| `src/linkedin_scraper/cli/app.py` | CLI entry point, modularized commands |

---

*Document generated: January 2026*
