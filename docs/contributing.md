<!-- START doctoc generated TOC please keep comment here to allow auto update -->

**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Contributing](#contributing)
  - [Quick Start for Contributors](#quick-start-for-contributors)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Contributing

Please see [CONTRIBUTING.md](https://github.com/cetincurio/linkedin-job-scraper/blob/main/CONTRIBUTING.md) in the repository root for detailed contribution guidelines.

## Quick Start for Contributors

```bash
# Clone and setup
git clone https://github.com/cetincurio/linkedin-job-scraper.git
cd linkedin-job-scraper

# Install with dev dependencies
uv sync --extra dev

# Install pre-commit hooks
uv run pre-commit install

# Run tests
uv run pytest

# Run linting
uv run ruff check src/ tests/
```
