"""TUI constants and shared data."""

from __future__ import annotations

from linkedin_scraper.consent import ACK_ENV, ACK_MESSAGE
from linkedin_scraper.scrapers.search import COUNTRY_GEO_IDS


COUNTRIES = [
    (name.title(), code)
    for name, code in sorted(
        {name: code for name, code in COUNTRY_GEO_IDS.items() if len(name) > 2}.items()
    )
]

__all__ = ["ACK_ENV", "ACK_MESSAGE", "COUNTRIES"]
