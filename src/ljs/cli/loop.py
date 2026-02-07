"""CLI command: loop."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer
from rich.panel import Panel
from rich.table import Table

from ljs.config import Settings, get_settings
from ljs.log import bind_log_context, log_debug, log_info
from ljs.logging_config import get_logger
from ljs.scrapers.detail import JobDetailScraper
from ljs.scrapers.search import JobSearchScraper
from ljs.storage.jobs import JobStorage

from .app import app
from .shared import console, require_acknowledgement


logger = get_logger(__name__)


@app.command()
def loop(
    ctx: typer.Context,
    keyword: Annotated[str, typer.Argument(help="Job search keyword")],
    country: Annotated[str, typer.Argument(help="Country name or code")],
    cycles: Annotated[
        int,
        typer.Option("--cycles", "-c", help="Number of search->scrape cycles"),
    ] = 3,
    search_pages: Annotated[
        int,
        typer.Option("--search-pages", "-s", help="Pages per search"),
    ] = 5,
    scrape_limit: Annotated[
        int,
        typer.Option("--scrape-limit", "-l", help="Jobs to scrape per cycle"),
    ] = 10,
    headless: Annotated[
        bool,
        typer.Option("--headless", "-H", help="Run browser in headless mode"),
    ] = False,
) -> None:
    """
    Run all three features in a loop.

    Cycle: Search -> Scrape Details (with recommendations) -> Repeat

    Example:
        ljs loop "data engineer" netherlands --cycles 5
    """
    if cycles < 1:
        console.print("[red]--cycles must be >= 1[/red]")
        raise typer.Exit(1)
    if search_pages < 1:
        console.print("[red]--search-pages must be >= 1[/red]")
        raise typer.Exit(1)
    if scrape_limit < 1:
        console.print("[red]--scrape-limit must be >= 1[/red]")
        raise typer.Exit(1)

    require_acknowledgement(ctx)
    settings = get_settings()
    settings.headless = headless
    with bind_log_context(op="cli.loop"):
        log_info(
            logger,
            "cli.loop.start",
            keyword=keyword,
            country=country,
            cycles=cycles,
            search_pages=search_pages,
            scrape_limit=scrape_limit,
            headless=headless,
        )

    console.print(
        Panel(
            f"[bold]Keyword:[/bold] {keyword}\n"
            f"[bold]Country:[/bold] {country}\n"
            f"[bold]Cycles:[/bold] {cycles}\n"
            f"[bold]Search pages per cycle:[/bold] {search_pages}\n"
            f"[bold]Scrape limit per cycle:[/bold] {scrape_limit}",
            title="Loop Mode",
            border_style="blue",
        )
    )

    asyncio.run(
        _run_loop(
            keyword=keyword,
            country=country,
            cycles=cycles,
            search_pages=search_pages,
            scrape_limit=scrape_limit,
            settings=settings,
        )
    )


async def _run_loop(
    keyword: str,
    country: str,
    cycles: int,
    search_pages: int,
    scrape_limit: int,
    settings: Settings,
) -> None:
    """Run the search->scrape loop."""
    search_scraper = JobSearchScraper(settings)
    detail_scraper = JobDetailScraper(settings)
    storage = JobStorage(settings)

    for cycle in range(1, cycles + 1):
        with bind_log_context(op="loop.cycle", cycle=cycle, cycles=cycles):
            log_info(logger, "loop.cycle.start")
        console.print(f"\n[bold blue]═══ Cycle {cycle}/{cycles} ═══[/bold blue]")

        console.print("\n[yellow]▶ Feature 1: Searching for jobs...[/yellow]")
        search_result = await search_scraper.run(
            keyword=keyword,
            country=country,
            max_pages=search_pages,
        )
        with bind_log_context(op="loop.cycle", cycle=cycle, cycles=cycles):
            log_info(logger, "loop.search.complete", total_found=search_result.total_found)
        console.print(f"  Found {search_result.total_found} job IDs")

        console.print("\n[yellow]▶ Feature 2 & 3: Scraping details + recommendations...[/yellow]")
        details = await detail_scraper.run(
            limit=scrape_limit,
            extract_recommended=True,
        )
        with bind_log_context(op="loop.cycle", cycle=cycle, cycles=cycles):
            log_info(logger, "loop.scrape.complete", scraped=len(details))
        console.print(f"  Scraped {len(details)} job details")

        stats_data = await storage.get_stats()
        with bind_log_context(op="loop.cycle", cycle=cycle, cycles=cycles):
            log_debug(logger, "loop.stats", stats=stats_data)
        console.print(
            f"\n[dim]Stats: {stats_data['search_job_ids']} search IDs, "
            f"{stats_data['recommended_job_ids']} recommended IDs, "
            f"{stats_data['job_details']} details[/dim]"
        )

        if cycle < cycles:
            console.print("\n[dim]Waiting before next cycle...[/dim]")
            with bind_log_context(op="loop.wait", cycle=cycle):
                log_info(logger, "loop.wait.before_next_cycle", sleep_s=5)
            await asyncio.sleep(5)

    console.print("\n[bold green]✓ Loop completed![/bold green]")
    final_stats = await storage.get_stats()
    with bind_log_context(op="cli.loop"):
        log_info(logger, "cli.loop.complete", stats=final_stats)

    table = Table(title="Final Statistics", show_header=True, header_style="bold green")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="white", justify="right")
    table.add_row("Total Search Job IDs", str(final_stats["search_job_ids"]))
    table.add_row("Total Recommended Job IDs", str(final_stats["recommended_job_ids"]))
    table.add_row("Total Job Details", str(final_stats["job_details"]))
    console.print(table)
