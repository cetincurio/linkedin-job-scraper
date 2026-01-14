"""Command-line interface for LinkedIn Job Scraper."""

import asyncio
import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from linkedin_scraper import __version__
from linkedin_scraper.config import Settings, get_settings
from linkedin_scraper.logging_config import setup_logging
from linkedin_scraper.models.job import JobIdSource
from linkedin_scraper.scrapers.detail import JobDetailScraper
from linkedin_scraper.scrapers.search import COUNTRY_GEO_IDS, JobSearchScraper
from linkedin_scraper.storage.jobs import JobStorage


__all__ = ["app"]

app = typer.Typer(
    name="linkedin-scraper",
    help="Educational LinkedIn public job ads scraper",
    add_completion=False,
    no_args_is_help=True,
)

console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"[bold blue]LinkedIn Job Scraper[/bold blue] v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    _version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-V", help="Enable verbose logging"),
    ] = False,
) -> None:
    """LinkedIn Job Scraper - Educational project for scraping public job ads."""
    settings = get_settings()
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging(level=level, log_dir=settings.log_dir)


@app.command()
def search(
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

    # Display results
    table = Table(title="Search Results", show_header=True, header_style="bold green")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Keyword", result.keyword)
    table.add_row("Country", result.country)
    table.add_row("Total Jobs Found", str(result.total_found))
    table.add_row("Pages Scraped", str(result.pages_scraped))

    console.print(table)
    console.print("\n[green]✓[/green] Job IDs saved to storage")


@app.command()
def scrape(
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
        linkedin-scraper scrape --limit 10
        linkedin-scraper scrape --job-id 1234567890
    """
    settings = get_settings()
    settings.headless = headless

    # Parse source filter
    source_filter = None
    if source:
        try:
            source_filter = JobIdSource(source.lower())
        except ValueError as err:
            console.print(f"[red]Invalid source: {source}. Use 'search' or 'recommended'[/red]")
            raise typer.Exit(1) from err

    # Handle single job ID
    job_ids = [job_id] if job_id else None

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

    # Display results
    console.print(f"\n[green]✓[/green] Scraped {len(results)} job details")

    if results:
        table = Table(title="Scraped Jobs", show_header=True, header_style="bold green")
        table.add_column("Job ID", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Company", style="white")
        table.add_column("Location", style="dim")

        for job in results[:10]:  # Show first 10
            table.add_row(
                job.job_id,
                (job.title or "N/A")[:40],
                (job.company_name or "N/A")[:25],
                (job.location or "N/A")[:20],
            )

        if len(results) > 10:
            table.add_row("...", f"({len(results) - 10} more)", "", "")

        console.print(table)


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


@app.command()
def countries() -> None:
    """List supported country codes."""
    table = Table(title="Supported Countries", show_header=True, header_style="bold green")
    table.add_column("Country", style="cyan")
    table.add_column("Codes", style="white")

    # Group by country
    country_codes: dict[str, list[str]] = {}
    for code, geo_id in COUNTRY_GEO_IDS.items():
        # Find full country name
        if len(code) > 2:
            country_codes.setdefault(code.title(), []).insert(0, code)
        else:
            # Find the full name for this geo_id
            for name, gid in COUNTRY_GEO_IDS.items():
                if gid == geo_id and len(name) > 2:
                    country_codes.setdefault(name.title(), []).append(code.upper())
                    break

    for country, codes in sorted(country_codes.items()):
        table.add_row(country, ", ".join(codes))

    console.print(table)


@app.command()
def export(
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output JSONL file path"),
    ] = None,
    manifest: Annotated[
        Path | None,
        typer.Option("--manifest", help="Optional manifest JSON path"),
    ] = None,
    redact_pii: Annotated[
        bool,
        typer.Option("--redact-pii", help="Redact email/phone-like PII from text fields"),
    ] = False,
    include_raw_sections: Annotated[
        bool,
        typer.Option("--include-raw-sections", help="Include raw_sections field in export"),
    ] = False,
    limit: Annotated[
        int | None,
        typer.Option("--limit", "-l", help="Limit number of job details to export"),
    ] = None,
) -> None:
    """Export stored job details as an ML-ready JSONL dataset with a manifest."""
    settings = get_settings()
    storage = JobStorage(settings)

    output_path = output or (settings.data_dir / "datasets" / "job_details.jsonl")

    console.print(
        Panel(
            f"[bold]Dataset:[/bold] {output_path}\n"
            f"[bold]Manifest:[/bold] {manifest or output_path.with_suffix('.manifest.json')}\n"
            f"[bold]Redact PII:[/bold] {redact_pii}\n"
            f"[bold]Include raw_sections:[/bold] {include_raw_sections}\n"
            f"[bold]Limit:[/bold] {limit or 'All'}",
            title="Export Dataset",
            border_style="blue",
        )
    )

    try:
        result = asyncio.run(
            storage.export_job_details_jsonl(
                output_path=output_path,
                manifest_path=manifest,
                redact_pii=redact_pii,
                include_raw_sections=include_raw_sections,
                limit=limit,
            )
        )
    except Exception as err:
        console.print(f"[red]Export failed:[/red] {err}")
        raise typer.Exit(1) from err

    table = Table(title="Export Result", show_header=True, header_style="bold green")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Records", str(result.get("record_count", 0)))
    table.add_row("Dataset", str(result.get("dataset_file", output_path)))
    table.add_row("Manifest", str(result.get("manifest_file", "")))
    table.add_row("SHA256", str(result.get("sha256", "")))
    console.print(table)


@app.command()
def loop(
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
        linkedin-scraper loop "data engineer" netherlands --cycles 5
    """
    settings = get_settings()
    settings.headless = headless

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
        console.print(f"\n[bold blue]═══ Cycle {cycle}/{cycles} ═══[/bold blue]")

        # Feature 1: Search
        console.print("\n[yellow]▶ Feature 1: Searching for jobs...[/yellow]")
        search_result = await search_scraper.run(
            keyword=keyword,
            country=country,
            max_pages=search_pages,
        )
        console.print(f"  Found {search_result.total_found} job IDs")

        # Feature 2 & 3: Scrape details + recommendations
        console.print("\n[yellow]▶ Feature 2 & 3: Scraping details + recommendations...[/yellow]")
        details = await detail_scraper.run(
            limit=scrape_limit,
            extract_recommended=True,
        )
        console.print(f"  Scraped {len(details)} job details")

        # Show stats
        stats_data = await storage.get_stats()
        console.print(
            f"\n[dim]Stats: {stats_data['search_job_ids']} search IDs, "
            f"{stats_data['recommended_job_ids']} recommended IDs, "
            f"{stats_data['job_details']} details[/dim]"
        )

        if cycle < cycles:
            console.print("\n[dim]Waiting before next cycle...[/dim]")
            await asyncio.sleep(5)

    console.print("\n[bold green]✓ Loop completed![/bold green]")
    final_stats = await storage.get_stats()

    table = Table(title="Final Statistics", show_header=True, header_style="bold green")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="white", justify="right")
    table.add_row("Total Search Job IDs", str(final_stats["search_job_ids"]))
    table.add_row("Total Recommended Job IDs", str(final_stats["recommended_job_ids"]))
    table.add_row("Total Job Details", str(final_stats["job_details"]))
    console.print(table)


@app.command()
def tui() -> None:
    """Launch the interactive TUI (Terminal User Interface)."""
    from linkedin_scraper.tui import LinkedInScraperApp  # noqa: PLC0415

    app_instance = LinkedInScraperApp()
    app_instance.run()


# =============================================================================
# ML Subcommands
# =============================================================================
ml_app = typer.Typer(
    name="ml",
    help="ML and analytics commands for job data",
    no_args_is_help=True,
)
app.add_typer(ml_app)


@ml_app.command("export")
def ml_export(
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Export format: parquet or jsonl"),
    ] = "parquet",
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file path"),
    ] = None,
) -> None:
    """Export job data to ML-ready formats."""
    from linkedin_scraper.ml.export import JobDataExporter  # noqa: PLC0415

    settings = get_settings()
    exporter = JobDataExporter(settings)

    try:
        if format == "parquet":
            path = exporter.export_parquet(output)
        elif format == "jsonl":
            path = exporter.export_jsonl(output)
        else:
            console.print(f"[red]Unknown format: {format}[/red]")
            raise typer.Exit(1)

        console.print(f"[green]✓ Exported to:[/green] {path}")

        stats = exporter.get_stats()
        console.print(f"  Jobs: {stats['total_jobs']}")
        console.print(f"  Companies: {stats['unique_companies']}")

    except Exception as e:
        console.print(f"[red]Export error: {e}[/red]")
        raise typer.Exit(1) from e


@ml_app.command("index")
def ml_index() -> None:
    """Index job data into vector store for semantic search."""
    from linkedin_scraper.ml.vectorstore import JobVectorStore  # noqa: PLC0415

    settings = get_settings()
    vectorstore = JobVectorStore(settings)

    with console.status("[bold green]Indexing jobs..."):
        count = vectorstore.index_jobs()

    console.print(f"[green]✓ Indexed {count} new jobs[/green]")

    stats = vectorstore.get_stats()
    console.print(f"  Total indexed: {stats['total_documents']}")


@ml_app.command("search")
def ml_search(
    query: Annotated[str, typer.Argument(help="Search query")],
    n_results: Annotated[
        int,
        typer.Option("--limit", "-n", help="Number of results"),
    ] = 10,
) -> None:
    """Search for similar jobs using semantic similarity."""
    from linkedin_scraper.ml.vectorstore import JobVectorStore  # noqa: PLC0415

    settings = get_settings()
    vectorstore = JobVectorStore(settings)

    results = vectorstore.search(query, n_results=n_results)

    if not results:
        console.print("[yellow]No results found. Try indexing jobs first.[/yellow]")
        return

    table = Table(title=f"Search: '{query}'", show_header=True)
    table.add_column("Score", style="cyan", justify="right")
    table.add_column("Title", style="white")
    table.add_column("Company", style="green")
    table.add_column("Location", style="blue")

    for r in results:
        table.add_row(
            f"{r['score']:.2f}",
            r["metadata"].get("title", "N/A")[:40],
            r["metadata"].get("company_name", "N/A")[:25],
            r["metadata"].get("location", "N/A")[:20],
        )

    console.print(table)


@ml_app.command("stats")
def ml_stats() -> None:
    """Show ML data statistics."""
    from linkedin_scraper.ml.export import JobDataExporter  # noqa: PLC0415
    from linkedin_scraper.ml.vectorstore import JobVectorStore  # noqa: PLC0415

    settings = get_settings()
    exporter = JobDataExporter(settings)
    vectorstore = JobVectorStore(settings)

    export_stats = exporter.get_stats()
    vs_stats = vectorstore.get_stats()

    table = Table(title="ML Data Statistics", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white", justify="right")

    table.add_row("Total Jobs", str(export_stats.get("total_jobs", 0)))
    table.add_row("Unique Companies", str(export_stats.get("unique_companies", 0)))
    table.add_row("Unique Locations", str(export_stats.get("unique_locations", 0)))
    table.add_row("Indexed in Vector Store", str(vs_stats.get("total_documents", 0)))
    table.add_row("Avg Description Length", str(export_stats.get("avg_description_length", 0)))

    console.print(table)

    # Top skills
    top_skills = export_stats.get("top_skills", [])
    if top_skills:
        console.print("\n[bold]Top Skills:[/bold]")
        for skill, count in top_skills[:10]:
            console.print(f"  {skill}: {count}")


@app.command()
def api(
    host: Annotated[str, typer.Option(help="Host to bind")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Port to bind")] = 8000,
) -> None:
    """Start the FastAPI server for job analytics."""
    try:
        import uvicorn  # noqa: PLC0415
    except ImportError as e:
        console.print("[red]uvicorn not installed. Run: uv sync --extra ml[/red]")
        raise typer.Exit(1) from e

    from linkedin_scraper.api.main import create_app  # noqa: PLC0415

    console.print(f"[bold green]Starting API server at http://{host}:{port}[/bold green]")
    console.print("  Docs: http://{host}:{port}/docs")

    app_instance = create_app()
    uvicorn.run(app_instance, host=host, port=port)


@app.command()
def dashboard() -> None:
    """Launch the Streamlit analytics dashboard."""
    import subprocess  # noqa: PLC0415
    import sys  # noqa: PLC0415

    dashboard_path = Path(__file__).parent / "dashboard.py"

    console.print("[bold green]Starting Streamlit dashboard...[/bold green]")
    subprocess.run(  # noqa: S603
        [sys.executable, "-m", "streamlit", "run", str(dashboard_path)],
        check=False,
    )


if __name__ == "__main__":
    app()
