"""Terminal User Interface for LinkedIn Job Scraper using Textual."""

import asyncio
import os
from datetime import datetime
from typing import ClassVar

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar,
    RichLog,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

from linkedin_scraper.config import get_settings
from linkedin_scraper.logging_config import get_logger, setup_logging
from linkedin_scraper.models.job import JobIdSource
from linkedin_scraper.scrapers.detail import JobDetailScraper
from linkedin_scraper.scrapers.search import COUNTRY_GEO_IDS, JobSearchScraper
from linkedin_scraper.storage.jobs import JobStorage


__all__ = ["LinkedInScraperApp"]

logger = get_logger(__name__)

ACK_ENV = "LINKEDIN_SCRAPER_ACKNOWLEDGE"
ACK_MESSAGE = (
    "Educational use only. Only access content you are authorized to access "
    "and comply with all applicable terms, policies, and laws."
)

COUNTRIES = [
    (name.title(), code)
    for name, code in sorted(
        {name: code for name, code in COUNTRY_GEO_IDS.items() if len(name) > 2}.items()
    )
]


class StatsWidget(Static):
    """Widget to display storage statistics."""

    def compose(self) -> ComposeResult:
        yield Static("Loading stats...", id="stats-content")

    async def refresh_stats(self) -> None:
        """Refresh the statistics display."""
        storage = JobStorage()
        stats = await storage.get_stats()

        content = (
            f"[bold cyan]Search Job IDs:[/bold cyan] {stats['search_job_ids']} "
            f"([dim]{stats['unscraped_search']} unscraped[/dim])\n"
            f"[bold cyan]Recommended IDs:[/bold cyan] {stats['recommended_job_ids']} "
            f"([dim]{stats['unscraped_recommended']} unscraped[/dim])\n"
            f"[bold cyan]Job Details:[/bold cyan] {stats['job_details']}"
        )

        stats_content = self.query_one("#stats-content", Static)
        stats_content.update(content)


class SearchPanel(Container):
    """Panel for job search functionality."""

    def compose(self) -> ComposeResult:
        yield Label("Search for Jobs", classes="panel-title")

        with Horizontal(classes="form-row"):
            yield Label("Keyword:", classes="form-label")
            yield Input(placeholder="e.g., python developer", id="search-keyword")

        with Horizontal(classes="form-row"):
            yield Label("Country:", classes="form-label")
            yield Select(COUNTRIES, id="search-country", prompt="Select country")

        with Horizontal(classes="form-row"):
            yield Label("Max Pages:", classes="form-label")
            yield Input(value="10", id="search-max-pages")

        with Horizontal(classes="button-row"):
            yield Button("🔍 Search", id="btn-search", variant="primary")
            yield Button("⏹ Stop", id="btn-stop-search", variant="error", disabled=True)

        yield ProgressBar(id="search-progress", total=100, show_eta=False)


class ScrapePanel(Container):
    """Panel for job detail scraping functionality."""

    def compose(self) -> ComposeResult:
        yield Label("Scrape Job Details", classes="panel-title")

        with Horizontal(classes="form-row"):
            yield Label("Source:", classes="form-label")
            yield Select(
                [("All", "all"), ("Search", "search"), ("Recommended", "recommended")],
                id="scrape-source",
                value="all",
            )

        with Horizontal(classes="form-row"):
            yield Label("Limit:", classes="form-label")
            yield Input(value="10", id="scrape-limit")

        with Horizontal(classes="form-row"):
            yield Label("Job ID:", classes="form-label")
            yield Input(placeholder="Optional: specific job ID", id="scrape-job-id")

        with Horizontal(classes="button-row"):
            yield Button("📄 Scrape", id="btn-scrape", variant="primary")
            yield Button("⏹ Stop", id="btn-stop-scrape", variant="error", disabled=True)

        yield ProgressBar(id="scrape-progress", total=100, show_eta=False)


class LoopPanel(Container):
    """Panel for running the full loop."""

    def compose(self) -> ComposeResult:
        yield Label("Loop Mode", classes="panel-title")

        with Horizontal(classes="form-row"):
            yield Label("Keyword:", classes="form-label")
            yield Input(placeholder="e.g., data engineer", id="loop-keyword")

        with Horizontal(classes="form-row"):
            yield Label("Country:", classes="form-label")
            yield Select(COUNTRIES, id="loop-country", prompt="Select country")

        with Horizontal(classes="form-row"):
            yield Label("Cycles:", classes="form-label")
            yield Input(value="3", id="loop-cycles")

        with Horizontal(classes="button-row"):
            yield Button("🔄 Start Loop", id="btn-loop", variant="primary")
            yield Button("⏹ Stop", id="btn-stop-loop", variant="error", disabled=True)

        yield ProgressBar(id="loop-progress", total=100, show_eta=False)


class ConsentScreen(ModalScreen[bool]):
    """Modal screen to confirm educational-only usage."""

    def compose(self) -> ComposeResult:
        yield Container(
            Static("[bold]Educational Use Only[/bold]\n\n" + ACK_MESSAGE),
            Horizontal(
                Button("I Understand", id="btn-ack", variant="primary"),
                Button("Exit", id="btn-exit", variant="error"),
                classes="consent-buttons",
            ),
            id="consent-dialog",
        )

    @on(Button.Pressed, "#btn-ack")
    def on_ack_pressed(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#btn-exit")
    def on_exit_pressed(self) -> None:
        self.dismiss(False)


class LinkedInScraperApp(App[None]):
    """Main TUI application for LinkedIn Job Scraper."""

    CSS = """
    Screen {
        background: $surface;
    }

    .panel-title {
        text-style: bold;
        color: $primary;
        padding: 1 0;
        text-align: center;
    }

    .form-row {
        height: 3;
        margin: 0 1;
        align: center middle;
    }

    .form-label {
        width: 12;
        text-align: right;
        padding-right: 1;
    }

    .button-row {
        height: 3;
        margin: 1;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }

    ProgressBar {
        margin: 1 2;
    }

    #stats-panel {
        height: 5;
        border: solid $primary;
        padding: 0 1;
        margin: 0 1;
    }

    #log-panel {
        height: 100%;
        border: solid $secondary;
        margin: 0 1;
    }

    #results-table {
        height: 100%;
        margin: 0 1;
    }

    SearchPanel, ScrapePanel, LoopPanel {
        border: solid $primary;
        margin: 1;
        padding: 1;
        height: auto;
    }

    TabbedContent {
        height: 1fr;
    }

    #main-container {
        height: 100%;
    }

    #left-panel {
        width: 45%;
    }

    #right-panel {
        width: 55%;
    }

    RichLog {
        height: 100%;
        scrollbar-gutter: stable;
    }

    DataTable {
        height: 100%;
    }

    #consent-dialog {
        width: 70%;
        max-width: 80;
        border: solid $warning;
        padding: 2 3;
        background: $surface;
        align: center middle;
    }

    .consent-buttons {
        height: 3;
        align: center middle;
        margin-top: 1;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("q", "quit", "Quit", priority=True),
        Binding("r", "refresh_stats", "Refresh Stats"),
        Binding("c", "clear_log", "Clear Log"),
        Binding("d", "toggle_dark", "Toggle Dark Mode"),
    ]

    TITLE: ClassVar[str] = "LinkedIn Job Scraper"  # type: ignore[misc]
    SUB_TITLE = "Educational Project"

    def __init__(self) -> None:
        super().__init__()
        self._settings = get_settings()
        self._running_task: asyncio.Task[None] | None = None
        setup_logging(log_dir=self._settings.log_dir)

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="main-container"):
            with Vertical(id="left-panel"):
                yield StatsWidget(id="stats-panel")
                yield SearchPanel()
                yield ScrapePanel()
                yield LoopPanel()

            with Vertical(id="right-panel"), TabbedContent():
                with TabPane("Log", id="tab-log"):
                    yield RichLog(id="log-panel", highlight=True, markup=True)
                with TabPane("Results", id="tab-results"):
                    yield DataTable(id="results-table")

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the app on mount."""
        if not self._is_acknowledged():
            self.push_screen(ConsentScreen(), self._on_consent)
            return

        await self._initialize_app()

    async def _initialize_app(self) -> None:
        """Finish initialization once consent is acknowledged."""
        await self._refresh_stats()

        # Setup results table
        table = self.query_one("#results-table", DataTable)
        table.add_columns("Job ID", "Title", "Company", "Location")

        self.log_message("[bold green]LinkedIn Job Scraper started[/bold green]")
        self.log_message("Use the panels on the left to search and scrape jobs.")

    def _on_consent(self, accepted: bool | None) -> None:
        """Handle consent dialog result."""
        if not accepted:
            self.exit()
            return

        os.environ[ACK_ENV] = "1"
        self._running_task = asyncio.create_task(self._initialize_app())

    @staticmethod
    def _is_acknowledged() -> bool:
        env_value = os.getenv(ACK_ENV, "").strip().lower()
        return env_value in {"1", "true", "yes", "y"}

    def log_message(self, message: str) -> None:
        """Add a message to the log panel."""
        log = self.query_one("#log-panel", RichLog)
        timestamp = datetime.now().strftime("%H:%M:%S")
        log.write(f"[dim]{timestamp}[/dim] {message}")

    async def _refresh_stats(self) -> None:
        """Refresh the stats widget."""
        stats_widget = self.query_one(StatsWidget)
        await stats_widget.refresh_stats()

    def action_refresh_stats(self) -> None:
        """Action to refresh statistics."""
        self._running_task = asyncio.create_task(self._refresh_stats())
        self.log_message("Stats refreshed")

    def action_clear_log(self) -> None:
        """Clear the log panel."""
        log = self.query_one("#log-panel", RichLog)
        log.clear()
        self.log_message("[dim]Log cleared[/dim]")

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.theme = "textual-dark" if self.theme == "textual-light" else "textual-light"

    @on(Button.Pressed, "#btn-search")
    def on_search_pressed(self) -> None:
        """Handle search button press."""
        keyword_input = self.query_one("#search-keyword", Input)
        country_select = self.query_one("#search-country", Select)
        max_pages_input = self.query_one("#search-max-pages", Input)

        keyword = keyword_input.value.strip()
        country = country_select.value
        max_pages = int(max_pages_input.value or "10")

        if not keyword:
            self.log_message("[red]Error: Please enter a search keyword[/red]")
            return

        if not country or country == Select.BLANK:
            self.log_message("[red]Error: Please select a country[/red]")
            return

        self.log_message(f"[yellow]Starting search: '{keyword}' in {country}...[/yellow]")
        self._run_search(keyword, str(country), max_pages)

    @work(exclusive=True)
    async def _run_search(self, keyword: str, country: str, max_pages: int) -> None:
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

        except Exception as e:
            self.log_message(f"[red]Search error: {e}[/red]")
            logger.exception("Search error")

        finally:
            btn_search.disabled = False
            btn_stop.disabled = True

    @on(Button.Pressed, "#btn-scrape")
    def on_scrape_pressed(self) -> None:
        """Handle scrape button press."""
        source_select = self.query_one("#scrape-source", Select)
        limit_input = self.query_one("#scrape-limit", Input)
        job_id_input = self.query_one("#scrape-job-id", Input)

        source = str(source_select.value) if source_select.value != "all" else None
        limit = int(limit_input.value or "10")
        job_id = job_id_input.value.strip() or None

        self.log_message(
            f"[yellow]Starting scrape (limit={limit}, source={source or 'all'})...[/yellow]"
        )
        self._run_scrape(source, limit, job_id)

    @work(exclusive=True)
    async def _run_scrape(
        self,
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

            # Update results table
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

            # Switch to results tab
            tabbed = self.query_one(TabbedContent)
            tabbed.active = "tab-results"

        except Exception as e:
            self.log_message(f"[red]Scrape error: {e}[/red]")
            logger.exception("Scrape error")

        finally:
            btn_scrape.disabled = False
            btn_stop.disabled = True

    @on(Button.Pressed, "#btn-loop")
    def on_loop_pressed(self) -> None:
        """Handle loop button press."""
        keyword_input = self.query_one("#loop-keyword", Input)
        country_select = self.query_one("#loop-country", Select)
        cycles_input = self.query_one("#loop-cycles", Input)

        keyword = keyword_input.value.strip()
        country = country_select.value
        cycles = int(cycles_input.value or "3")

        if not keyword:
            self.log_message("[red]Error: Please enter a search keyword[/red]")
            return

        if not country or country == Select.BLANK:
            self.log_message("[red]Error: Please select a country[/red]")
            return

        self.log_message(
            f"[yellow]Starting loop: '{keyword}' in {country}, {cycles} cycles...[/yellow]"
        )
        self._run_loop(keyword, str(country), cycles)

    @work(exclusive=True)
    async def _run_loop(self, keyword: str, country: str, cycles: int) -> None:
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

                # Search
                self.log_message("[yellow]Searching...[/yellow]")
                result = await search_scraper.run(keyword=keyword, country=country, max_pages=5)
                self.log_message(f"Found {result.total_found} jobs")

                # Scrape
                self.log_message("[yellow]Scraping details...[/yellow]")
                details = await detail_scraper.run(limit=10, extract_recommended=True)
                self.log_message(f"Scraped {len(details)} details")

                await self._refresh_stats()

                if cycle < cycles:
                    self.log_message("[dim]Waiting before next cycle...[/dim]")
                    await asyncio.sleep(3)

            self.log_message("[green]Loop completed![/green]")
            progress.update(progress=100)

        except Exception as e:
            self.log_message(f"[red]Loop error: {e}[/red]")
            logger.exception("Loop error")

        finally:
            btn_loop.disabled = False
            btn_stop.disabled = True


def main() -> None:
    """Entry point for the TUI."""
    app = LinkedInScraperApp()
    app.run()


if __name__ == "__main__":
    main()
