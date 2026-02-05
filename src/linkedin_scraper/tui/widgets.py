"""Reusable TUI widgets."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Button, Input, Label, ProgressBar, Select, Static

from linkedin_scraper.storage.jobs import JobStorage

from .constants import COUNTRIES


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
