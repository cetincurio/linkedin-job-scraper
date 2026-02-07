<!-- START doctoc generated TOC please keep comment here to allow auto update -->

**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [LinkedIn Job Scraper](#linkedin-job-scraper)
  - [Features](#features)
    - [Three Core Features](#three-core-features)
    - [Anti-Detection Techniques](#anti-detection-techniques)
  - [Installation](#installation)
    - [Prerequisites](#prerequisites)
    - [Quick Start with uv (Recommended)](#quick-start-with-uv-recommended)
    - [Alternative: pip](#alternative-pip)
  - [Usage](#usage)
    - [CLI Commands](#cli-commands)
    - [TUI (Terminal User Interface)](#tui-terminal-user-interface)
    - [Running as Module](#running-as-module)
  - [Configuration](#configuration)
    - [Environment Variables](#environment-variables)
    - [Settings Reference](#settings-reference)
  - [Project Structure](#project-structure)
  - [Data Storage](#data-storage)
    - [Job IDs (`data/job_ids/`)](#job-ids-datajob_ids)
    - [Job Details (`data/job_details/`)](#job-details-datajob_details)
  - [Ethical Guidelines](#ethical-guidelines)
  - [Troubleshooting](#troubleshooting)
    - [Common Issues](#common-issues)
  - [CI/CD Summary](#cicd-summary)
  - [Release Checklist](#release-checklist)
  - [Development](#development)
    - [Build Backend](#build-backend)
    - [Make Commands (Optional)](#make-commands-optional)
    - [Documentation](#documentation)
  - [Contributing](#contributing)
  - [License](#license)
  - [Disclaimer](#disclaimer)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# LinkedIn Job Scraper

[![CI - Lint](https://github.com/cetincurio/linkedin-job-scraper/actions/workflows/ci-lint.yml/badge.svg)](https://github.com/cetincurio/linkedin-job-scraper/actions/workflows/ci-lint.yml)
[![CI - Tests](https://github.com/cetincurio/linkedin-job-scraper/actions/workflows/ci-test.yml/badge.svg)](https://github.com/cetincurio/linkedin-job-scraper/actions/workflows/ci-test.yml)
[![CI - Build](https://github.com/cetincurio/linkedin-job-scraper/actions/workflows/ci-build.yml/badge.svg)](https://github.com/cetincurio/linkedin-job-scraper/actions/workflows/ci-build.yml)
[![CI - Docs](https://github.com/cetincurio/linkedin-job-scraper/actions/workflows/ci-docs.yml/badge.svg)](https://github.com/cetincurio/linkedin-job-scraper/actions/workflows/ci-docs.yml)
[![Release](https://github.com/cetincurio/linkedin-job-scraper/actions/workflows/release.yml/badge.svg)](https://github.com/cetincurio/linkedin-job-scraper/actions/workflows/release.yml)
[![Docs](https://img.shields.io/website?url=https%3A%2F%2Fcetincurio.github.io%2Flinkedin-job-scraper%2F&label=docs)](https://cetincurio.github.io/linkedin-job-scraper/)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

> **⚠️ Educational Project Only**
> This project is for educational and learning purposes only. Always respect LinkedIn's Terms of Service and robots.txt. Only scrape publicly available job ads.

A Python-based LinkedIn public job ads scraper with stealth capabilities, featuring both CLI and TUI interfaces.

## Features

### Three Core Features

1. **Job Search (Feature 1)**
   - Search jobs by keyword and country
   - Pagination with "Show more" button handling
   - Extracts job IDs from search results

2. **Job Detail Scraper (Feature 2)**
   - Visits individual job pages
   - Extracts comprehensive job information
   - Saves structured data as JSON

3. **Recommended Jobs Extractor (Feature 3)**
   - Extracts job IDs from recommendation sections
   - Works alongside Feature 2
   - Discovers "Similar jobs", "People also viewed", etc.

### Anti-Detection Techniques

- **Playwright Stealth**: Integration with `playwright-stealth` library
- **Human-like Behavior**: Bezier curve mouse movements, variable typing speeds
- **Fingerprint Spoofing**: WebGL, plugins, languages, user-agent rotation
- **Rate Limiting**: Configurable delays and request limits
- **Browser Evasion**: Removes automation indicators

## Installation

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Quick Start with uv (Recommended)

```bash
# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/cetincurio/linkedin-job-scraper.git
cd linkedin-job-scraper

# Install dependencies (creates .venv automatically)
uv sync

# Install Playwright browsers
uv run playwright install chromium

# If you activated a venv, prefer:
# uv sync --active
# uv run --active playwright install chromium

# Run the CLI
uv run ljs --help
```

### Alternative: pip

```bash
git clone https://github.com/cetincurio/linkedin-job-scraper.git
cd linkedin-job-scraper

python -m venv .venv
source .venv/bin/activate  # Linux/macOS
pip install -e .
playwright install chromium
```

## Usage

### CLI Commands

```bash
# Show help
ljs --help

# Feature 1: Search for jobs
ljs search "python developer" germany --max-pages 10

# Feature 2 & 3: Scrape job details (with recommendations)
ljs scrape --limit 10
ljs scrape --job-id 1234567890

# Run all features in a loop
ljs loop "data engineer" netherlands --cycles 5

# Show statistics
ljs stats

# List supported countries
ljs countries
```

### TUI (Terminal User Interface)

```bash
# Launch interactive TUI
ljs tui
```

The TUI provides:

- Visual panels for all three features
- Real-time log output
- Results table
- Statistics display
- Keyboard shortcuts (q=quit, r=refresh, c=clear log)

### Running as Module

```bash
python -m ljs search "software engineer" "united states"
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
LINKEDIN_SCRAPER_HEADLESS=false
LINKEDIN_SCRAPER_SLOW_MO=50
LINKEDIN_SCRAPER_DISABLE_BROWSER_SANDBOX=false
LINKEDIN_SCRAPER_MIN_DELAY_MS=800
LINKEDIN_SCRAPER_MAX_DELAY_MS=3000
LINKEDIN_SCRAPER_MAX_PAGES_PER_SESSION=10
LINKEDIN_SCRAPER_MIN_REQUEST_INTERVAL_SEC=2.0
LINKEDIN_SCRAPER_MAX_REQUESTS_PER_HOUR=100
```

### Settings Reference

| Setting                 | Default | Description                      |
| ----------------------- | ------- | -------------------------------- |
| `headless`              | `false` | Run browser without GUI          |
| `slow_mo`               | `50`    | Slowdown between operations (ms) |
| `disable_browser_sandbox` | `false` | Disable Chromium sandbox (unsafe; containers only) |
| `min_delay_ms`          | `800`   | Minimum delay between actions    |
| `max_delay_ms`          | `3000`  | Maximum delay between actions    |
| `typing_delay_ms`       | `80`    | Delay between keystrokes         |
| `max_pages_per_session` | `10`    | Max pages to scrape per run      |
| `min_request_interval_sec` | `2.0` | Min seconds between requests (0 disables gap limiter) |
| `max_requests_per_hour` | `100`   | Rate limit per hour (0 disables hourly limiter) |

## Project Structure

```bash
linkedin-job-scraper/
├── pyproject.toml          # Dependencies and project config
├── README.md               # This file
├── .gitignore
├── .env                    # Environment variables (create this)
├── data/                   # Scraped data storage
│   ├── job_ids/            # Job ID JSON files
│   ├── job_details/        # Job detail JSON files
│   └── screenshots/        # Debug screenshots
├── logs/                   # Log files
└── src/ljs/
    ├── __init__.py
    ├── __main__.py         # Module entry point
    ├── consent.py          # Shared consent helpers
    ├── cli/                # CLI interface (Typer)
    │   ├── app.py
    │   ├── search.py
    │   ├── scrape.py
    │   ├── loop.py
    │   ├── export.py
    │   ├── stats.py
    │   ├── countries.py
    │   └── tui.py
    ├── tui/                # TUI interface (Textual)
    │   ├── app.py
    │   ├── actions.py
    │   ├── handlers.py
    │   ├── widgets.py
    │   ├── screens.py
    │   ├── styles.py
    │   └── constants.py
    ├── config.py           # Settings management
    ├── logging_config.py   # Logging setup
    ├── browser/
    │   ├── stealth.py      # Anti-detection techniques
    │   ├── human.py        # Human behavior simulation
    │   └── context.py      # Browser lifecycle management
    ├── scrapers/
    │   ├── base.py         # Base scraper class
    │   └── recommended.py  # Feature 3: Recommendations
    │   ├── search/
    │   │   ├── scraper.py  # Feature 1: Job search
    │   │   └── countries.py
    │   └── detail/
    │       ├── scraper.py  # Feature 2: Job details
    │       └── extractors.py
    ├── storage/
    │   └── jobs/           # Data persistence
    │       ├── storage.py
    │       ├── exporter.py
    │       └── text.py
    └── models/
        └── job.py          # Pydantic data models
```

## Data Storage

### Job IDs (`data/job_ids/`)

```json
[
  {
    "job_id": "1234567890",
    "source": "search",
    "discovered_at": "2025-01-13T23:30:00",
    "search_keyword": "python developer",
    "search_country": "germany",
    "scraped": false
  }
]
```

### Job Details (`data/job_details/`)

```json
{
  "job_id": "1234567890",
  "scraped_at": "2025-01-13T23:35:00",
  "title": "Senior Python Developer",
  "company_name": "Example Corp",
  "location": "Berlin, Germany",
  "workplace_type": "Hybrid",
  "employment_type": "Full-time",
  "seniority_level": "Mid-Senior level",
  "description": "...",
  "posted_date": "2 days ago",
  "skills": ["Python", "Django", "PostgreSQL"]
}
```

## Ethical Guidelines

1. **Respect robots.txt**: Always check LinkedIn's robots.txt
2. **Rate Limiting**: Use appropriate delays between requests
3. **Public Data Only**: Only scrape publicly accessible job ads
4. **No Personal Data**: Never scrape personal information
5. **Educational Use**: This tool is for learning purposes only

## Troubleshooting

### Common Issues

**Browser not launching:**

```bash
playwright install chromium
```

**Bot detection:**

- Run in non-headless mode: `--headless=false`
- Increase delays in configuration
- Use residential proxies (configure in settings)

**No jobs found:**

- Verify the country code is correct
- Check if LinkedIn's page structure changed
- Review debug screenshots in `data/screenshots/`

## CI/CD Summary

- CI is modular: lint, tests, build, docs, and integration are separate workflows for clarity and speed.
- Docs deploy automatically from `main` via GitHub Pages (opt-in via `ENABLE_PAGES=true`).
- Release workflow builds sdist + wheel on tag pushes (`v*`) or manual runs.
- TestPyPI/PyPI publishing is manual via workflow inputs.
- Full details and diagrams live in `docs/dev/ci-cd.md`.

## Release Checklist

1. Choose the next version using PEP 440 (see `docs/dev/ci-cd.md`).
2. Update `pyproject.toml` version and `CHANGELOG.md`.
3. Tag the release: `git tag vX.Y.Z` and push the tag.
4. Confirm the `Release` workflow builds artifacts.
5. If you want to publish, run the `Release` workflow manually with `publish_target=testpypi`.
6. Validate the TestPyPI release, then run again with `publish_target=pypi`.

## Development

### Build Backend

This project uses `uv_build` (the uv build backend) for fast, modern packaging. The
`pyproject.toml` config includes `source-include` entries to keep `tests/` and
`CHANGELOG.md` in the sdist.

```bash
# Install dev dependencies
uv sync --extra dev

# Install prek hooks
uv run prek install

# Or individually:
uv run ruff check src/ tests/    # Lint
uv run ruff format src/ tests/   # Format
uv run ty check src/             # Type check
uv run pytest                    # Test
uv run pytest --cov              # Test with coverage

# If you activated a venv, add --active:
# uv run --active ruff check src/ tests/
```

### Make Commands (Optional)

If you prefer Make, the repo includes shortcuts for the common uv commands.

### Documentation

```bash
# Build docs
uv sync --extra docs
uv run mkdocs build

# Serve locally
uv run mkdocs serve
```

Docs are deployed automatically to GitHub Pages from `main`.

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - See [LICENSE](LICENSE) for details.

## Disclaimer

This tool is provided for educational purposes only. The authors are not responsible for any misuse. Always comply with LinkedIn's Terms of Service and applicable laws in your jurisdiction.
