<!-- START doctoc generated TOC please keep comment here to allow auto update -->

**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [CI/CD (2026) Overview](#cicd-2026-overview)
  - [Pipeline At A Glance](#pipeline-at-a-glance)
  - [Release Pipeline (Build + Optional Publish)](#release-pipeline-build-optional-publish)
  - [Release Checklist (Small And Practical)](#release-checklist-small-and-practical)
  - [Triggers](#triggers)
  - [Workflows](#workflows)
    - [CI - Lint](#ci---lint)
    - [CI - Tests](#ci---tests)
    - [CI - Build](#ci---build)
    - [CI - Docs](#ci---docs)
    - [CI - Integration](#ci---integration)
  - [Status Checks](#status-checks)
  - [Caching Strategy](#caching-strategy)
  - [Performance & Minimalism Principles](#performance-minimalism-principles)
  - [Future Proofing](#future-proofing)
  - [Versioning System (2026 Best Practice)](#versioning-system-2026-best-practice)
  - [Build System In `pyproject.toml` (2026 Best Practice)](#build-system-in-pyprojecttoml-2026-best-practice)
  - [Enabling PyPI / TestPyPI Publishing](#enabling-pypi-testpypi-publishing)
  - [Files](#files)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# CI/CD (2026) Overview

This repo uses a modern, modular, and fast GitHub Actions pipeline designed for 2026 best practices:

- Fast feedback with cached `uv` dependencies and short job timeouts.
- Minimal surfaces: only the necessary jobs for lint, test, build, docs, and gated integration.
- Future-proofing: merge queue support, path filters, and explicit permissions.

## Pipeline At A Glance

```mermaid
flowchart LR
  A[push / PR / merge queue / manual] --> L[CI - Lint]
  A --> T[CI - Tests]
  A --> B[CI - Build]
  A --> D[CI - Docs]
  M[push to main] --> I[CI - Integration]
  D --> G{main push & ENABLE_PAGES?}
  G -- yes --> H[Deploy docs]
  G -- no --> S[Skip]
```

## Release Pipeline (Build + Optional Publish)

The release workflow builds sdist + wheel on tag pushes (`v*`) or manual runs.
Publishing to PyPI/TestPyPI is manual and controlled by workflow inputs.

```mermaid
flowchart LR
  R[tag push v* / manual] --> B[Build sdist + wheel]
  B --> A[Upload dist artifacts]
  A --> P{Manual publish}
  P --> P1[PyPI]
  P --> P2[TestPyPI]
```

## Release Checklist (Small And Practical)

1. Choose the next version using PEP 440 (see guidance below).
2. Update `pyproject.toml` version and `CHANGELOG.md`.
3. Tag the release: `git tag vX.Y.Z` and push the tag.
4. Confirm `Release` workflow builds artifacts.
5. (Optional) Run the Release workflow manually with `publish_target=testpypi`.
6. Validate the TestPyPI release.
7. Run the Release workflow manually with `publish_target=pypi`.

## Triggers

- `push` on `main` or `develop`, scoped to relevant paths.
- `pull_request` to `main`, scoped to relevant paths.
- `merge_group` for merge queue support.
- `workflow_dispatch` for manual runs.
- Docs deploy is gated by `ENABLE_PAGES=true` (repo variable).

## Workflows

### CI - Lint

- Installs `uv`, caches the global `uv` cache.
- Installs dev + types extras.
- Runs `ruff check`, `ruff format --check`, `ty`, and `prek`.

### CI - Tests

- Python `3.13` and `3.14`.
- Caches `uv` per Python version.
- Runs pytest with coverage and uploads to Codecov.

### CI - Build

- Builds artifacts using `uv build`.
- Uploads `dist/` artifacts for reuse.

Includes a wheel-install smoke test in the same workflow to validate packaging.

### CI - Docs

- Builds docs with MkDocs and deploys to GitHub Pages on `main`.

### CI - Integration

- Runs only on `push` to `main`.
- Installs Playwright Chromium and runs integration tests.

## Status Checks

Recommended required checks for branch protection:

- `CI - Lint`
- `CI - Tests`
- `CI - Build`
- `CI - Docs`
- (Optional) `CI - Integration`

## Caching Strategy

We use `setup-uv`'s built-in cache to avoid repeated downloads and accelerate cold starts.

```mermaid
flowchart LR
  A[setup-uv cache] --> B[Restore on next run]
```

## Performance & Minimalism Principles

- Use path filters to avoid running CI on non-code changes.
- Use `uv` for fast dependency resolution and installation.
- Use `uv sync --locked` and `uv run --no-sync` for reproducible, fast runs.
- Fail fast on lint/type issues.
- Use tight job timeouts to avoid wasted runner minutes.
- Pin `uv` via `UV_VERSION` for reproducibility.
- Optional cache trimming via `UV_CACHE_PRUNE=true` (repo variable).

## Future Proofing

- `merge_group` ensures compatibility with GitHub merge queue.
- Explicit `permissions` for least-privilege by default.
- Centralized Python version in workflow `env`.

## Versioning System (2026 Best Practice)

Use PEP 440 as the canonical versioning scheme for Python packages. PEP 440 is the
accepted standard in the Python ecosystem and is what packaging tools expect.
You can still follow a SemVer-like pattern (`X.Y.Z`) as long as it remains valid
PEP 440. Pre-releases and dev builds should use PEP 440 suffixes like `a`, `b`,
`rc`, and `.devN`.

## Build System In `pyproject.toml` (2026 Best Practice)

Best practice is to declare a PEP 517 build backend in `[build-system]` and use
standards-based metadata in `[project]` (PEP 621). This repo uses `uv_build`,
which is fast and aligned with uv-native workflows for pure-Python packages.

## Enabling PyPI / TestPyPI Publishing

Publishing is manual and controlled via `workflow_dispatch` inputs. Configure
PyPI Trusted Publishing for this GitHub repo and add environment protections in
GitHub for `pypi` and `testpypi`.

## Files

- Workflow (lint): `.github/workflows/ci-lint.yml`
- Workflow (tests): `.github/workflows/ci-test.yml`
- Workflow (build): `.github/workflows/ci-build.yml`
- Workflow (docs): `.github/workflows/ci-docs.yml`
- Workflow (integration): `.github/workflows/ci-integration.yml`
- Release workflow: `.github/workflows/ci-release.yml`
- This doc: `docs/dev/ci-cd.md`
