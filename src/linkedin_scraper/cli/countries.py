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

    # Build a stable mapping from geoId -> canonical country name + codes.
    # COUNTRY_GEO_IDS also contains aliases like "usa", which we intentionally omit from display.
    by_geo: dict[str, dict[str, list[str]]] = {}
    for key, geo_id in COUNTRY_GEO_IDS.items():
        entry = by_geo.setdefault(geo_id, {"names": [], "codes": []})
        if len(key) == 2:
            entry["codes"].append(key.upper())
        elif key != "usa":
            entry["names"].append(key)

    rows: list[tuple[str, list[str]]] = []
    for entry in by_geo.values():
        if not entry["names"]:
            continue
        # Prefer longer, more descriptive names (e.g. "united states" over "germany").
        canonical = sorted(entry["names"], key=lambda n: (n.count(" "), len(n)), reverse=True)[0]
        codes = sorted(set(entry["codes"]))
        rows.append((canonical.title(), codes))

    for country, codes in sorted(rows, key=lambda r: r[0]):
        table.add_row(country, ", ".join(codes) if codes else "-")

    console.print(table)
