<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [LinkedIn Job Scraper](#linkedin-job-scraper)
  - [Features](#features)
  - [Quick Start](#quick-start)
  - [Documentation](#documentation)
  - [Disclaimer](#disclaimer)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# LinkedIn Job Scraper

> **Educational project for learning web scraping with Playwright**

A Python-based LinkedIn public job ads scraper with stealth capabilities,
featuring both CLI and TUI interfaces.

## Features

- 🔍 **Job Search** - Search by keyword and country with pagination
- 📄 **Detail Extraction** - Comprehensive job information scraping
- 🔗 **Recommendations** - Discover related jobs automatically
- 🛡️ **Stealth Mode** - Anti-detection techniques built-in
- 💻 **CLI & TUI** - Beautiful interfaces for all workflows

## Quick Start

```bash
# Install with uv (recommended)
uv sync
uv run playwright install chromium

# Search for jobs
linkedin-scraper search "python developer" germany

# Scrape job details
linkedin-scraper scrape --limit 10

# Launch interactive TUI
linkedin-scraper tui
```

## Documentation

- [Installation](installation.md) - Setup instructions
- [Usage Guide](usage.md) - How to use the scraper
- [Configuration](configuration.md) - Settings and options
- [API Reference](api/index.md) - Module documentation
- [Contributing](contributing.md) - How to contribute

## Disclaimer

This project is for **educational purposes only**. Always respect LinkedIn's
Terms of Service and applicable laws in your jurisdiction.
