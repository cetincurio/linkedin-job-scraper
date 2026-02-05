"""CLI command: stats."""

from __future__ import annotations

import asyncio

from rich.table import Table

from linkedin_scraper.storage.jobs import JobStorage

from .app import app
from .shared import console


@app.command()
def stats() -> None:
    """Show storage statistics."""
    storage = JobStorage()
    stats_data = asyncio.run(storage.get_stats())

    table = Table(title="Storage Statistics", show_header=True, header_style="bold green")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="white", justify="right")

    table.add_row("Search Job IDs", str(stats_data["search_job_ids"]))
    table.add_row("  └─ Unscraped", str(stats_data["unscraped_search"]))
    table.add_row("Recommended Job IDs", str(stats_data["recommended_job_ids"]))
    table.add_row("  └─ Unscraped", str(stats_data["unscraped_recommended"]))
    table.add_row("Job Details Saved", str(stats_data["job_details"]))

    console.print(table)
