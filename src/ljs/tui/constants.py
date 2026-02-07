"""TUI constants and shared data."""

from __future__ import annotations

from ljs.consent import ACK_ENV, ACK_MESSAGE
from ljs.scrapers.search import COUNTRY_GEO_IDS


_CANONICAL_COUNTRIES = sorted(
    name
    for name in COUNTRY_GEO_IDS
    # Include only readable country names, not short codes / aliases.
    if len(name) > 2 and name != "usa"
)

# Textual Select expects (label, value). We pass the *country key* (not geoId) as the value,
# because the scraper resolves it via COUNTRY_GEO_IDS.
COUNTRIES = [(name.title(), name) for name in _CANONICAL_COUNTRIES]

__all__ = ["ACK_ENV", "ACK_MESSAGE", "COUNTRIES"]
