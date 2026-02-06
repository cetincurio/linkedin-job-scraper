<!-- START doctoc generated TOC please keep comment here to allow auto update -->

**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Installation](#installation)
  - [Requirements](#requirements)
  - [Installation Methods](#installation-methods)
    - [Using uv (Recommended)](#using-uv-recommended)
    - [Using pip](#using-pip)
    - [From PyPI (when published)](#from-pypi-when-published)
  - [Verify Installation](#verify-installation)
  - [Development Installation](#development-installation)
  - [Troubleshooting](#troubleshooting)
    - [Browser Installation Issues](#browser-installation-issues)
    - [Permission Issues on Linux](#permission-issues-on-linux)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Installation

## Requirements

- Python 3.13 or higher
- A Chromium-based browser (installed automatically)

## Installation Methods

### Using uv (Recommended)

[uv](https://docs.astral.sh/uv/) is a fast Python package manager written in Rust.

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone https://github.com/cetincurio/linkedin-job-scraper.git
cd linkedin-job-scraper

# Install dependencies (creates .venv automatically)
uv sync

# Install Playwright browsers
uv run playwright install chromium

# If you activated a venv, prefer:
# uv sync --active
# uv run --active playwright install chromium
```

### Using pip

```bash
# Clone repository
git clone https://github.com/cetincurio/linkedin-job-scraper.git
cd linkedin-job-scraper

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows

# Install package
pip install -e .

# Install Playwright browsers
playwright install chromium
```

### From PyPI (when published)

```bash
pip install linkedin-job-scraper
playwright install chromium
```

## Verify Installation

```bash
# Check CLI is working
linkedin-scraper --version

# Show available commands
linkedin-scraper --help
```

## Development Installation

For contributors:

```bash
# Install with dev dependencies
uv sync --extra dev

# Install prek hooks
uv run prek install

# Run tests to verify
uv run pytest
```

## Troubleshooting

### Browser Installation Issues

If Playwright browser installation fails:

```bash
# Install with system dependencies
uv run playwright install chromium --with-deps
```

### Permission Issues on Linux

```bash
# May need to run as user, not root
chmod +x ~/.local/bin/playwright
```
