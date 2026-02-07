"""UI event handlers split by feature."""

from __future__ import annotations

import asyncio
from typing import Any

from textual import on, work
from textual.widgets import Button, DataTable, Input, ProgressBar, Select, TabbedContent
from textual.worker import Worker

from ljs.logging_config import get_logger
from ljs.models.job import JobIdSource
from ljs.scrapers.detail import JobDetailScraper
from ljs.scrapers.search import JobSearchScraper


logger = get_logger(__name__)


def _parse_int(
    value: str,
    *,
    default: int | None = None,
    min_value: int | None = None,
) -> int:
    """Parse an int from user input, with optional default and minimum."""
    text = value.strip()
    if not text:
        if default is None:
            raise ValueError("Value is required")
        return default

    number = int(text)
    if min_value is not None and number < min_value:
        raise ValueError(f"Value must be >= {min_value}")
    return number


class SearchHandlers:
    """Handlers for the search panel."""

    @on(Button.Pressed, "#btn-search")
    def on_search_pressed(self: Any) -> None:
        """Handle search button press."""
        keyword_input = self.query_one("#search-keyword", Input)
        country_select = self.query_one("#search-country", Select)
        max_pages_input = self.query_one("#search-max-pages", Input)

        keyword = keyword_input.value.strip()
        country = country_select.value
        try:
            max_pages = _parse_int(max_pages_input.value, default=10, min_value=1)
        except ValueError as err:
            self.log_message(f"[red]Error: Invalid max pages ({err})[/red]")
            return

        if not keyword:
            self.log_message("[red]Error: Please enter a search keyword[/red]")
            return

        if not country or country == Select.BLANK:
            self.log_message("[red]Error: Please select a country[/red]")
            return

        self.log_message(f"[yellow]Starting search: '{keyword}' in {country}...[/yellow]")
        self._search_worker = self._run_search(keyword, str(country), max_pages)

    @on(Button.Pressed, "#btn-stop-search")
    def on_stop_search_pressed(self: Any) -> None:
        """Cancel the running search worker, if any."""
        worker: Worker[Any] | None = getattr(self, "_search_worker", None)
        if worker and not worker.is_finished:
            worker.cancel()
            self.log_message("[dim]Search cancelled[/dim]")

    @work(exclusive=True)
    async def _run_search(
        self: Any,
        keyword: str,
        country: str,
        max_pages: int,
    ) -> None:
        """Run the job search in background."""
        btn_search = self.query_one("#btn-search", Button)
        btn_stop = self.query_one("#btn-stop-search", Button)
        progress = self.query_one("#search-progress", ProgressBar)

        btn_search.disabled = True
        btn_stop.disabled = False
        progress.update(progress=0)

        try:
            scraper = JobSearchScraper(self._settings)
            result = await scraper.run(keyword=keyword, country=country, max_pages=max_pages)

            self.log_message(f"[green]Search complete: {result.total_found} jobs found[/green]")
            progress.update(progress=100)

            await self._refresh_stats()

        except asyncio.CancelledError:
            self.log_message("[dim]Search cancelled[/dim]")
            raise
        except Exception as e:
            self.log_message(f"[red]Search error: {e}[/red]")
            logger.exception("Search error")

        finally:
            btn_search.disabled = False
            btn_stop.disabled = True
            self._search_worker = None


class ScrapeHandlers:
    """Handlers for the scrape panel."""

    @on(Button.Pressed, "#btn-scrape")
    def on_scrape_pressed(self: Any) -> None:
        """Handle scrape button press."""
        source_select = self.query_one("#scrape-source", Select)
        limit_input = self.query_one("#scrape-limit", Input)
        job_id_input = self.query_one("#scrape-job-id", Input)

        source = str(source_select.value) if source_select.value != "all" else None
        try:
            limit = _parse_int(limit_input.value, default=10, min_value=1)
        except ValueError as err:
            self.log_message(f"[red]Error: Invalid limit ({err})[/red]")
            return
        job_id = job_id_input.value.strip() or None

        self.log_message(
            f"[yellow]Starting scrape (limit={limit}, source={source or 'all'})...[/yellow]"
        )
        self._scrape_worker = self._run_scrape(source, limit, job_id)

    @on(Button.Pressed, "#btn-stop-scrape")
    def on_stop_scrape_pressed(self: Any) -> None:
        """Cancel the running scrape worker, if any."""
        worker: Worker[Any] | None = getattr(self, "_scrape_worker", None)
        if worker and not worker.is_finished:
            worker.cancel()
            self.log_message("[dim]Scrape cancelled[/dim]")

    @work(exclusive=True)
    async def _run_scrape(
        self: Any,
        source: str | None,
        limit: int,
        job_id: str | None,
    ) -> None:
        """Run job detail scraping in background."""
        btn_scrape = self.query_one("#btn-scrape", Button)
        btn_stop = self.query_one("#btn-stop-scrape", Button)
        progress = self.query_one("#scrape-progress", ProgressBar)
        table = self.query_one("#results-table", DataTable)

        btn_scrape.disabled = True
        btn_stop.disabled = False
        progress.update(progress=0)

        try:
            source_filter = JobIdSource(source) if source else None
            job_ids = [job_id] if job_id else None

            scraper = JobDetailScraper(self._settings)
            results = await scraper.run(
                job_ids=job_ids,
                source=source_filter,
                limit=limit,
                extract_recommended=True,
            )

            table.clear()
            for job in results:
                table.add_row(
                    job.job_id,
                    (job.title or "N/A")[:40],
                    (job.company_name or "N/A")[:25],
                    (job.location or "N/A")[:20],
                )

            self.log_message(f"[green]Scrape complete: {len(results)} jobs scraped[/green]")
            progress.update(progress=100)

            await self._refresh_stats()

            tabbed = self.query_one(TabbedContent)
            tabbed.active = "tab-results"

        except asyncio.CancelledError:
            self.log_message("[dim]Scrape cancelled[/dim]")
            raise
        except Exception as e:
            self.log_message(f"[red]Scrape error: {e}[/red]")
            logger.exception("Scrape error")

        finally:
            btn_scrape.disabled = False
            btn_stop.disabled = True
            self._scrape_worker = None


class LoopHandlers:
    """Handlers for the loop panel."""

    @on(Button.Pressed, "#btn-loop")
    def on_loop_pressed(self: Any) -> None:
        """Handle loop button press."""
        keyword_input = self.query_one("#loop-keyword", Input)
        country_select = self.query_one("#loop-country", Select)
        cycles_input = self.query_one("#loop-cycles", Input)

        keyword = keyword_input.value.strip()
        country = country_select.value
        try:
            cycles = _parse_int(cycles_input.value, default=3, min_value=1)
        except ValueError as err:
            self.log_message(f"[red]Error: Invalid cycles ({err})[/red]")
            return

        if not keyword:
            self.log_message("[red]Error: Please enter a search keyword[/red]")
            return

        if not country or country == Select.BLANK:
            self.log_message("[red]Error: Please select a country[/red]")
            return

        self.log_message(
            f"[yellow]Starting loop: '{keyword}' in {country}, {cycles} cycles...[/yellow]"
        )
        self._loop_worker = self._run_loop(keyword, str(country), cycles)

    @on(Button.Pressed, "#btn-stop-loop")
    def on_stop_loop_pressed(self: Any) -> None:
        """Cancel the running loop worker, if any."""
        worker: Worker[Any] | None = getattr(self, "_loop_worker", None)
        if worker and not worker.is_finished:
            worker.cancel()
            self.log_message("[dim]Loop cancelled[/dim]")

    @work(exclusive=True)
    async def _run_loop(
        self: Any,
        keyword: str,
        country: str,
        cycles: int,
    ) -> None:
        """Run the full scraping loop in background."""
        btn_loop = self.query_one("#btn-loop", Button)
        btn_stop = self.query_one("#btn-stop-loop", Button)
        progress = self.query_one("#loop-progress", ProgressBar)

        btn_loop.disabled = True
        btn_stop.disabled = False

        try:
            search_scraper = JobSearchScraper(self._settings)
            detail_scraper = JobDetailScraper(self._settings)

            for cycle in range(1, cycles + 1):
                progress.update(progress=(cycle - 1) * 100 // cycles)
                self.log_message(f"[blue]═══ Cycle {cycle}/{cycles} ═══[/blue]")

                self.log_message("[yellow]Searching...[/yellow]")
                result = await search_scraper.run(keyword=keyword, country=country, max_pages=5)
                self.log_message(f"Found {result.total_found} jobs")

                self.log_message("[yellow]Scraping details...[/yellow]")
                details = await detail_scraper.run(limit=10, extract_recommended=True)
                self.log_message(f"Scraped {len(details)} details")

                await self._refresh_stats()

                if cycle < cycles:
                    self.log_message("[dim]Waiting before next cycle...[/dim]")
                    await asyncio.sleep(3)

            self.log_message("[green]Loop completed![/green]")
            progress.update(progress=100)

        except asyncio.CancelledError:
            self.log_message("[dim]Loop cancelled[/dim]")
            raise
        except Exception as e:
            self.log_message(f"[red]Loop error: {e}[/red]")
            logger.exception("Loop error")

        finally:
            btn_loop.disabled = False
            btn_stop.disabled = True
            self._loop_worker = None
