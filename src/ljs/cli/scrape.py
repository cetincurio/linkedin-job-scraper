"""CLI command: scrape."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer
from rich.panel import Panel
from rich.table import Table

from ljs.config import get_settings
from ljs.log import bind_log_context, log_info
from ljs.logging_config import get_logger
from ljs.models.job import JobIdSource
from ljs.scrapers.detail import JobDetailScraper

from .app import app
from .shared import console, require_acknowledgement


logger = get_logger(__name__)


@app.command()
def scrape(
    ctx: typer.Context,
    limit: Annotated[
        int | None,
        typer.Option("--limit", "-l", help="Maximum jobs to scrape"),
    ] = None,
    source: Annotated[
        str | None,
        typer.Option("--source", "-s", help="Source filter: 'search' or 'recommended'"),
    ] = None,
    job_id: Annotated[
        str | None,
        typer.Option("--job-id", "-j", help="Scrape a specific job ID"),
    ] = None,
    no_recommended: Annotated[
        bool,
        typer.Option("--no-recommended", help="Don't extract recommended job IDs"),
    ] = False,
    headless: Annotated[
        bool,
        typer.Option("--headless", "-H", help="Run browser in headless mode"),
    ] = False,
) -> None:
    """
    Feature 2 & 3: Scrape job details and extract recommended jobs.

    Visits job pages, extracts detailed information, and discovers
    new job IDs from recommendation sections.

    Example:
        ljs scrape --limit 10
        ljs scrape --job-id 1234567890
    """
    if limit is not None and limit < 1:
        console.print("[red]--limit must be >= 1[/red]")
        raise typer.Exit(1)

    source_filter = None
    if source:
        try:
            source_filter = JobIdSource(source.lower())
        except ValueError as err:
            console.print(f"[red]Invalid source: {source}. Use 'search' or 'recommended'[/red]")
            raise typer.Exit(1) from err

    require_acknowledgement(ctx)
    settings = get_settings()
    settings.headless = headless

    job_ids = [job_id] if job_id else None
    with bind_log_context(op="cli.scrape"):
        log_info(
            logger,
            "cli.scrape.start",
            limit=limit,
            source=(source_filter.value if source_filter else None),
            job_id=job_id,
            extract_recommended=(not no_recommended),
            headless=headless,
        )

    console.print(
        Panel(
            f"[bold]Limit:[/bold] {limit or 'All unscraped'}\n"
            f"[bold]Source:[/bold] {source or 'All'}\n"
            f"[bold]Extract recommended:[/bold] {not no_recommended}",
            title="Job Detail Scraper",
            border_style="blue",
        )
    )

    scraper = JobDetailScraper(settings)
    results = asyncio.run(
        scraper.run(
            job_ids=job_ids,
            source=source_filter,
            limit=limit,
            extract_recommended=not no_recommended,
        )
    )
    with bind_log_context(op="cli.scrape"):
        log_info(logger, "cli.scrape.complete", scraped=len(results))

    console.print(f"\n[green]✓[/green] Scraped {len(results)} job details")

    if results:
        table = Table(title="Scraped Jobs", show_header=True, header_style="bold green")
        table.add_column("Job ID", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Company", style="white")
        table.add_column("Location", style="dim")

        for job in results[:10]:
            table.add_row(
                job.job_id,
                (job.title or "N/A")[:40],
                (job.company_name or "N/A")[:25],
                (job.location or "N/A")[:20],
            )

        if len(results) > 10:
            table.add_row("...", f"({len(results) - 10} more)", "", "")

        console.print(table)
