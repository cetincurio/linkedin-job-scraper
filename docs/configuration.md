<!-- START doctoc generated TOC please keep comment here to allow auto update -->

**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [Settings Reference](#settings-reference)
  - [Programmatic Configuration](#programmatic-configuration)
  - [Anti-Detection Tips](#anti-detection-tips)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Configuration

## Environment Variables

Create a `.env` file in the project root:

```env
# Browser settings
LINKEDIN_SCRAPER_HEADLESS=false
LINKEDIN_SCRAPER_SLOW_MO=50
LINKEDIN_SCRAPER_BROWSER_TYPE=chromium
LINKEDIN_SCRAPER_DISABLE_BROWSER_SANDBOX=false

# Anti-detection delays (milliseconds)
LINKEDIN_SCRAPER_MIN_DELAY_MS=800
LINKEDIN_SCRAPER_MAX_DELAY_MS=3000
LINKEDIN_SCRAPER_TYPING_DELAY_MS=80

# Scraping limits
LINKEDIN_SCRAPER_MAX_PAGES_PER_SESSION=10
LINKEDIN_SCRAPER_PAGE_LOAD_TIMEOUT_MS=30000
LINKEDIN_SCRAPER_REQUEST_TIMEOUT_MS=15000

# Rate limiting
LINKEDIN_SCRAPER_MIN_REQUEST_INTERVAL_SEC=2.0
LINKEDIN_SCRAPER_MAX_REQUESTS_PER_HOUR=100

# Storage paths
LINKEDIN_SCRAPER_DATA_DIR=data
LINKEDIN_SCRAPER_LOG_DIR=logs
```

## Settings Reference

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `headless` | bool | `false` | Run browser without GUI |
| `slow_mo` | int | `50` | Slowdown between operations (ms) |
| `browser_type` | str | `chromium` | Browser engine |
| `disable_browser_sandbox` | bool | `false` | Disable Chromium sandbox (unsafe; containers only) |
| `min_delay_ms` | int | `800` | Minimum action delay |
| `max_delay_ms` | int | `3000` | Maximum action delay |
| `typing_delay_ms` | int | `80` | Delay between keystrokes |
| `mouse_movement_steps` | int | `25` | Mouse movement smoothness |
| `max_pages_per_session` | int | `10` | Max pages per run |
| `page_load_timeout_ms` | int | `30000` | Page load timeout |
| `min_request_interval_sec` | float | `2.0` | Min seconds between requests (0 disables gap limiter) |
| `max_requests_per_hour` | int | `100` | Rate limit per hour (0 disables hourly limiter) |

## Programmatic Configuration

```python
from ljs.config import Settings

settings = Settings(
    headless=True,
    min_delay_ms=500,
    max_delay_ms=2000,
    max_pages_per_session=20,
)
```

## Anti-Detection Tips

For best stealth:

1. **Use non-headless mode** during development
2. **Increase delays** if getting blocked
3. **Limit requests** per hour
4. **Vary your patterns** - don't scrape the same way every time
