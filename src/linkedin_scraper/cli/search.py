"""CLI command: search."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer
from rich.panel import Panel
from rich.table import Table

from linkedin_scraper.config import get_settings
from linkedin_scraper.scrapers.search import JobSearchScraper

from .app import app
from .shared import console, require_acknowledgement


@app.command()
def search(
    ctx: typer.Context,
    keyword: Annotated[str, typer.Argument(help="Job search keyword")],
    country: Annotated[str, typer.Argument(help="Country name or code (e.g., 'Germany', 'DE')")],
    max_pages: Annotated[
        int,
        typer.Option("--max-pages", "-m", help="Maximum pages to load"),
    ] = 10,
    headless: Annotated[
        bool,
        typer.Option("--headless", "-H", help="Run browser in headless mode"),
    ] = False,
) -> None:
    """
    Feature 1: Search for jobs and extract job IDs.

    Searches LinkedIn for jobs matching the keyword in the specified country,
    clicks 'Show more' to load results, and saves job IDs.

    Example:
        linkedin-scraper search "python developer" germany --max-pages 20
    """
    require_acknowledgement(ctx)
    settings = get_settings()
    settings.headless = headless

    console.print(
        Panel(
            f"[bold]Searching for:[/bold] {keyword}\n"
            f"[bold]Country:[/bold] {country}\n"
            f"[bold]Max pages:[/bold] {max_pages}",
            title="Job Search",
            border_style="blue",
        )
    )

    scraper = JobSearchScraper(settings)
    result = asyncio.run(scraper.run(keyword=keyword, country=country, max_pages=max_pages))

    table = Table(title="Search Results", show_header=True, header_style="bold green")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Keyword", result.keyword)
    table.add_row("Country", result.country)
    table.add_row("Total Jobs Found", str(result.total_found))
    table.add_row("Pages Scraped", str(result.pages_scraped))

    console.print(table)
    console.print("\n[green]✓[/green] Job IDs saved to storage")
