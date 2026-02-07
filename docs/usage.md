<!-- START doctoc generated TOC please keep comment here to allow auto update -->

**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Usage Guide](#usage-guide)
  - [CLI Commands](#cli-commands)
    - [Search for Jobs (Feature 1)](#search-for-jobs-feature-1)
    - [Scrape Job Details (Feature 2 & 3)](#scrape-job-details-feature-2-3)
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
ljs search "python developer" germany --max-pages 10
```

Options:

- `--max-pages, -m`: Maximum pages to load (default: 10)
- `--headless, -H`: Run browser without GUI

### Scrape Job Details (Feature 2 & 3)

Scrape detailed information from job pages:

```bash
# Scrape first 10 unscraped jobs
ljs scrape --limit 10

# Scrape from search results only
ljs scrape --source search --limit 5

# Scrape a specific job
ljs scrape --job-id 1234567890

# Disable recommendation extraction
ljs scrape --limit 10 --no-recommended
```

### Loop Mode (All Features)

Run search and scrape in cycles:

```bash
ljs loop "data engineer" netherlands --cycles 5
```

### View Statistics

```bash
ljs stats
```

### List Supported Countries

```bash
ljs countries
```

## TUI (Terminal User Interface)

Launch the interactive interface:

```bash
ljs tui
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
from ljs.scrapers.search import JobSearchScraper
from ljs.scrapers.detail import JobDetailScraper
from ljs.config import get_settings

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

Data is stored as merge-friendly ledgers plus a local index:

```
data/
├── ledger/
│   ├── job_ids/
│   │   ├── <run_id>.jsonl             # Job ID discoveries (Feature 1 & 3)
│   └── job_scrapes/
│       └── <run_id>.jsonl             # Scrape completion events (Feature 2)
├── index/
│   └── job_index.sqlite3              # Local-only SQLite index (derived from ledgers)
└── job_details/
    ├── 1234567890.json          # Individual job details
    └── ...
```

Notes:

- The `data/ledger/` files are designed to be synced across machines (e.g., via Git).
- The `data/index/` database is derived and can be deleted/rebuilt at any time.
