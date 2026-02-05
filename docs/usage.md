<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Usage Guide](#usage-guide)
  - [CLI Commands](#cli-commands)
    - [Search for Jobs (Feature 1)](#search-for-jobs-feature-1)
    - [Scrape Job Details (Feature 2 & 3)](#scrape-job-details-feature-2--3)
    - [Loop Mode (All Features)](#loop-mode-all-features)
    - [View Statistics](#view-statistics)
    - [List Supported Countries](#list-supported-countries)
  - [TUI (Terminal User Interface)](#tui-terminal-user-interface)
    - [Keyboard Shortcuts](#keyboard-shortcuts)
  - [Programmatic Usage](#programmatic-usage)
  - [Data Storage](#data-storage)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Usage Guide

## CLI Commands

### Search for Jobs (Feature 1)

Search LinkedIn for jobs by keyword and country:

```bash
linkedin-scraper search "python developer" germany --max-pages 10
```

Options:

- `--max-pages, -m`: Maximum pages to load (default: 10)
- `--headless, -H`: Run browser without GUI

### Scrape Job Details (Feature 2 & 3)

Scrape detailed information from job pages:

```bash
# Scrape first 10 unscraped jobs
linkedin-scraper scrape --limit 10

# Scrape from search results only
linkedin-scraper scrape --source search --limit 5

# Scrape a specific job
linkedin-scraper scrape --job-id 1234567890

# Disable recommendation extraction
linkedin-scraper scrape --limit 10 --no-recommended
```

### Loop Mode (All Features)

Run search and scrape in cycles:

```bash
linkedin-scraper loop "data engineer" netherlands --cycles 5
```

### View Statistics

```bash
linkedin-scraper stats
```

### List Supported Countries

```bash
linkedin-scraper countries
```

## TUI (Terminal User Interface)

Launch the interactive interface:

```bash
linkedin-scraper tui
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit |
| `r` | Refresh statistics |
| `c` | Clear log |
| `d` | Toggle dark mode |

## Programmatic Usage

```python
import asyncio
from linkedin_scraper.scrapers.search import JobSearchScraper
from linkedin_scraper.scrapers.detail import JobDetailScraper
from linkedin_scraper.config import get_settings

async def main():
    settings = get_settings()
    settings.headless = True

    # Search for jobs
    search = JobSearchScraper(settings)
    result = await search.run(
        keyword="python developer",
        country="germany",
        max_pages=5,
    )
    print(f"Found {result.total_found} jobs")

    # Scrape details
    detail = JobDetailScraper(settings)
    jobs = await detail.run(limit=5)
    for job in jobs:
        print(f"{job.title} at {job.company_name}")

asyncio.run(main())
```

## Data Storage

Data is stored in JSON format:

```
data/
├── job_ids/
│   ├── search_job_ids.json      # From Feature 1
│   └── recommended_job_ids.json # From Feature 3
└── job_details/
    ├── 1234567890.json          # Individual job details
    └── ...
```
