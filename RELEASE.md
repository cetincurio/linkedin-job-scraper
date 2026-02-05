<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Release Checklist](#release-checklist)
  - [Notes](#notes)
  - [Release Notes Template](#release-notes-template)
    - [Highlights](#highlights)
    - [Added](#added)
    - [Changed](#changed)
    - [Fixed](#fixed)
    - [Deprecated](#deprecated)
    - [Security](#security)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Release Checklist

1. Choose the next version using PEP 440 (SemVer-style `X.Y.Z` that is PEP 440 valid).
2. Update `pyproject.toml` version and `CHANGELOG.md`.
3. Tag the release: `git tag vX.Y.Z` and push the tag.
4. Confirm the `Release` workflow builds artifacts.
5. Optional: Uncomment PyPI/TestPyPI publish jobs in `.github/workflows/release.yml`.

## Notes

- Versioning: follow PEP 440 for Python packaging compatibility.
- Build system: use the PEP 517 backend declared in `pyproject.toml`.

## Release Notes Template

### Highlights

-

### Added

-

### Changed

-

### Fixed

-

### Deprecated

-

### Security

-
