"""LinkedIn Job Scraper - Educational project for scraping public job ads."""

from importlib.metadata import PackageNotFoundError, version


try:
    __version__ = version("linkedin-job-scraper")
except PackageNotFoundError:  # pragma: no cover
    # When running from a source checkout without an installed distribution.
    __version__ = "0.0.0"

__all__ = ["__version__"]
