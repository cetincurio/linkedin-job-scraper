<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
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
  - [Development](#development)
    - [Make Commands](#make-commands)
    - [Documentation](#documentation)
  - [Contributing](#contributing)
  - [License](#license)
  - [Disclaimer](#disclaimer)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# LinkedIn Job Scraper

[![CI](https://github.com/yourusername/linkedin-job-scraper/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/linkedin-job-scraper/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
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

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Quick Start with uv (Recommended)

```bash
# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/yourusername/linkedin-job-scraper.git
cd linkedin-job-scraper

# Install dependencies (creates .venv automatically)
uv sync

# Install Playwright browsers
uv run playwright install chromium

# Run the CLI
uv run linkedin-scraper --help
```

### Alternative: pip

```bash
git clone https://github.com/yourusername/linkedin-job-scraper.git
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
linkedin-scraper --help

# Feature 1: Search for jobs
linkedin-scraper search "python developer" germany --max-pages 10

# Feature 2 & 3: Scrape job details (with recommendations)
linkedin-scraper scrape --limit 10
linkedin-scraper scrape --job-id 1234567890

# Run all features in a loop
linkedin-scraper loop "data engineer" netherlands --cycles 5

# Show statistics
linkedin-scraper stats

# List supported countries
linkedin-scraper countries
```

### TUI (Terminal User Interface)

```bash
# Launch interactive TUI
linkedin-scraper tui
```

The TUI provides:

- Visual panels for all three features
- Real-time log output
- Results table
- Statistics display
- Keyboard shortcuts (q=quit, r=refresh, c=clear log)

### Running as Module

```bash
python -m linkedin_scraper search "software engineer" "united states"
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
LINKEDIN_SCRAPER_HEADLESS=false
LINKEDIN_SCRAPER_SLOW_MO=50
LINKEDIN_SCRAPER_MIN_DELAY_MS=800
LINKEDIN_SCRAPER_MAX_DELAY_MS=3000
LINKEDIN_SCRAPER_MAX_PAGES_PER_SESSION=10
LINKEDIN_SCRAPER_MAX_REQUESTS_PER_HOUR=100
```

### Settings Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `headless` | `false` | Run browser without GUI |
| `slow_mo` | `50` | Slowdown between operations (ms) |
| `min_delay_ms` | `800` | Minimum delay between actions |
| `max_delay_ms` | `3000` | Maximum delay between actions |
| `typing_delay_ms` | `80` | Delay between keystrokes |
| `max_pages_per_session` | `10` | Max pages to scrape per run |
| `max_requests_per_hour` | `100` | Rate limit per hour |

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
└── src/linkedin_scraper/
    ├── __init__.py
    ├── __main__.py         # Module entry point
    ├── cli.py              # CLI interface (Typer)
    ├── tui.py              # TUI interface (Textual)
    ├── config.py           # Settings management
    ├── logging_config.py   # Logging setup
    ├── browser/
    │   ├── stealth.py      # Anti-detection techniques
    │   ├── human.py        # Human behavior simulation
    │   └── context.py      # Browser lifecycle management
    ├── scrapers/
    │   ├── base.py         # Base scraper class
    │   ├── search.py       # Feature 1: Job search
    │   ├── detail.py       # Feature 2: Job details
    │   └── recommended.py  # Feature 3: Recommendations
    ├── storage/
    │   └── jobs.py         # Data persistence
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

## Development

```bash
# Install dev dependencies
uv sync --dev

# Install pre-commit hooks
uv run pre-commit install

# Run all checks
make check

# Or individually:
uv run ruff check src/ tests/    # Lint
uv run ruff format src/ tests/   # Format
uv run pyright src/              # Type check
uv run pytest                    # Test
uv run pytest --cov              # Test with coverage
```

### Make Commands

```bash
make help        # Show all commands
make dev         # Setup dev environment
make test        # Run tests
make lint        # Run linter
make format      # Format code
make type-check  # Run pyright
make docs        # Build documentation
make build       # Build package
```

### Documentation

```bash
# Build docs
uv sync --group docs
uv run mkdocs build

# Serve locally
uv run mkdocs serve
```

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - See [LICENSE](LICENSE) for details.

## Disclaimer

This tool is provided for educational purposes only. The authors are not responsible for any misuse. Always comply with LinkedIn's Terms of Service and applicable laws in your jurisdiction.
