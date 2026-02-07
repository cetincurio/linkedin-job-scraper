"""Scraper modules for LinkedIn job data extraction."""

from ljs.scrapers.base import BaseScraper
from ljs.scrapers.detail import JobDetailScraper
from ljs.scrapers.recommended import RecommendedJobsScraper
from ljs.scrapers.search import JobSearchScraper


__all__ = [
    "BaseScraper",
    "JobDetailScraper",
    "JobSearchScraper",
    "RecommendedJobsScraper",
]
