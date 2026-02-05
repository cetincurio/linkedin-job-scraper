






<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Changelog](#changelog)
  - [[Unreleased]](#unreleased)
    - [Added](#added)
    - [Security](#security)
  - [[0.1.0] - 2026-01-13](#010---2026-01-13)
    - [Added](#added-1)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial project structure
- Feature 1: Job search with pagination and job ID extraction
- Feature 2: Job detail scraper with comprehensive data extraction
- Feature 3: Recommended jobs ID extractor from job detail pages
- CLI interface with Typer
- TUI interface with Textual
- Modular package layout with focused submodules (CLI, TUI, scrapers, storage)
- Anti-detection techniques using playwright-stealth
- Human-like behavior simulation (mouse movements, typing delays)
- Pydantic models for type-safe data handling
- Async storage with JSON persistence
- Comprehensive logging with Rich
- Pre-commit hooks for code quality
- GitHub Actions CI/CD workflows
- Full test suite with pytest
- Switched build backend to `uv_build` with sdist source includes for tests and changelog

### Security

- No hardcoded credentials
- Rate limiting to respect server resources
- Educational use disclaimer

## [0.1.0] - 2026-01-13

### Added

- Initial release
- Core scraping functionality
- CLI and TUI interfaces
- Documentation

[Unreleased]: https://github.com/cetincurio/linkedin-job-scraper/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/cetincurio/linkedin-job-scraper/releases/tag/v0.1.0
