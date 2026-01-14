# Installation

## Requirements

- Python 3.12 or higher
- A Chromium-based browser (installed automatically)

## Installation Methods

### Using uv (Recommended)

[uv](https://docs.astral.sh/uv/) is a fast Python package manager written in Rust.

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone https://github.com/yourusername/linkedin-job-scraper.git
cd linkedin-job-scraper

# Install dependencies (creates .venv automatically)
uv sync

# Install Playwright browsers
uv run playwright install chromium
```

### Using pip

```bash
# Clone repository
git clone https://github.com/yourusername/linkedin-job-scraper.git
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
uv sync --dev

# Install pre-commit hooks
uv run pre-commit install

# Run tests to verify
uv run pytest
```

## Troubleshooting

### Browser Installation Issues

If Playwright browser installation fails:

```bash
# Install with system dependencies
playwright install chromium --with-deps
```

### Permission Issues on Linux

```bash
# May need to run as user, not root
chmod +x ~/.local/bin/playwright
```
