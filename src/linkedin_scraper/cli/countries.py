"""CLI command: countries."""

from __future__ import annotations

from rich.table import Table

from linkedin_scraper.scrapers.search import COUNTRY_GEO_IDS

from .app import app
from .shared import console


@app.command()
def countries() -> None:
    """List supported country codes."""
    table = Table(title="Supported Countries", show_header=True, header_style="bold green")
    table.add_column("Country", style="cyan")
    table.add_column("Codes", style="white")

    country_codes: dict[str, list[str]] = {}
    for code, geo_id in COUNTRY_GEO_IDS.items():
        if len(code) > 2:
            country_codes.setdefault(code.title(), []).insert(0, code)
        else:
            for name, gid in COUNTRY_GEO_IDS.items():
                if gid == geo_id and len(name) > 2:
                    country_codes.setdefault(name.title(), []).append(code.upper())
                    break

    for country, codes in sorted(country_codes.items()):
        table.add_row(country, ", ".join(codes))

    console.print(table)
