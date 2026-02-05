<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Contributing to LinkedIn Job Scraper](#contributing-to-linkedin-job-scraper)
  - [📋 Table of Contents](#-table-of-contents)
  - [Code of Conduct](#code-of-conduct)
  - [Getting Started](#getting-started)
  - [Development Setup](#development-setup)
    - [Prerequisites](#prerequisites)
    - [Setup with uv (Recommended)](#setup-with-uv-recommended)
    - [Setup with pip](#setup-with-pip)
  - [Making Changes](#making-changes)
    - [Branch Naming](#branch-naming)
    - [Commit Messages](#commit-messages)
  - [Code Style](#code-style)
    - [Formatting & Linting](#formatting--linting)
    - [Guidelines](#guidelines)
    - [Example](#example)
  - [Testing](#testing)
    - [Running Tests](#running-tests)
    - [Writing Tests](#writing-tests)
  - [Pull Request Process](#pull-request-process)
    - [PR Checklist](#pr-checklist)
  - [Questions?](#questions)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Contributing to LinkedIn Job Scraper

Thank you for your interest in contributing! This document provides guidelines
and instructions for contributing to this project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Code Style](#code-style)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

Be respectful, inclusive, and constructive. We're all here to learn and build.

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally
3. **Create a branch** for your changes

```bash
git clone https://github.com/yourusername/linkedin-job-scraper.git
cd linkedin-job-scraper
git checkout -b feature/your-feature-name
```

## Development Setup

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Setup with uv (Recommended)

```bash
# Install uv if you haven't
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync --dev

# Install Playwright browsers
uv run playwright install chromium

# Install pre-commit hooks
uv run pre-commit install
```

### Setup with pip

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
pip install -e ".[dev]"
playwright install chromium
pre-commit install
```

## Making Changes

### Branch Naming

Use descriptive branch names:

- `feature/add-proxy-support`
- `fix/job-id-extraction`
- `docs/update-readme`
- `refactor/storage-module`

### Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

[optional body]
```

Types:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:

```
feat(scraper): add support for salary extraction
fix(storage): handle duplicate job IDs correctly
docs(readme): add uv installation instructions
```

## Code Style

### Formatting & Linting

We use **Ruff** for both linting and formatting:

```bash
# Format code
uv run ruff format src/ tests/

# Lint code (auto-fix)
uv run ruff check --fix src/ tests/

# Type checking
uv run pyright src/
```

### Guidelines

1. **Type hints everywhere** - All functions must have type annotations
2. **Docstrings** - Public functions/classes need docstrings
3. **No print statements** - Use `logging` module instead
4. **Keep functions small** - Single responsibility principle
5. **Use pathlib** - Prefer `Path` over string paths

### Example

```python
from pathlib import Path
from linkedin_scraper.logging_config import get_logger

logger = get_logger(__name__)


def process_file(file_path: Path) -> dict[str, str]:
    """
    Process a file and extract data.

    Args:
        file_path: Path to the file to process.

    Returns:
        Dictionary with extracted data.

    Raises:
        FileNotFoundError: If file doesn't exist.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    logger.info(f"Processing file: {file_path}")
    # ... implementation
    return {}
```

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/linkedin_scraper --cov-report=html

# Run specific test file
uv run pytest tests/test_models.py

# Run tests in parallel
uv run pytest -n auto

# Skip integration tests (no browser needed)
uv run pytest -m "not integration"
```

### Writing Tests

1. Place tests in `tests/` directory
2. Name test files `test_*.py`
3. Use fixtures from `conftest.py`
4. Mark slow/integration tests appropriately

```python
import pytest

from linkedin_scraper.models.job import JobId, JobIdSource


class TestJobId:
    """Tests for JobId model."""

    def test_create_job_id(self) -> None:
        """Test creating a basic JobId."""
        job = JobId(job_id="123", source=JobIdSource.SEARCH)
        assert job.job_id == "123"

    @pytest.mark.slow
    def test_slow_operation(self) -> None:
        """Test that takes a while."""
        # ...

    @pytest.mark.integration
    async def test_browser_interaction(self) -> None:
        """Test requiring actual browser."""
        # ...
```

## Pull Request Process

1. **Update your branch** with the latest main:

   ```bash
   git fetch origin
   git rebase origin/main
   ```

2. **Run all checks locally**:

   ```bash
   uv run ruff format src/ tests/
   uv run ruff check src/ tests/
   uv run pyright src/
   uv run pytest
   ```

3. **Push and create PR**:

   ```bash
   git push origin feature/your-feature-name
   ```

4. **Fill out the PR template** with:
   - Description of changes
   - Related issues
   - Testing done
   - Screenshots (if UI changes)

5. **Address review feedback** promptly

### PR Checklist

- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] All checks passing
- [ ] Commit messages follow convention

## Questions?

Open an issue with the `question` label or start a discussion.

Thank you for contributing! 🎉
