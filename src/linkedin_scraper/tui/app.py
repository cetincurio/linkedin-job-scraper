"""TUI application implementation."""

from __future__ import annotations

import asyncio
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, RichLog, TabbedContent, TabPane

from linkedin_scraper.config import get_settings
from linkedin_scraper.consent import is_acknowledged_env, set_acknowledged_env
from linkedin_scraper.logging_config import setup_logging

from .actions import AppActions
from .handlers import LoopHandlers, ScrapeHandlers, SearchHandlers
from .screens import ConsentScreen
from .styles import TUI_CSS
from .widgets import LoopPanel, ScrapePanel, SearchPanel, StatsWidget


class LinkedInScraperApp(AppActions, SearchHandlers, ScrapeHandlers, LoopHandlers, App[None]):
    """Main TUI application for LinkedIn Job Scraper."""

    CSS = TUI_CSS

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("r", "refresh_stats", "Refresh Stats"),
        Binding("c", "clear_log", "Clear Log"),
        Binding("d", "toggle_dark", "Toggle Dark Mode"),
    ]

    TITLE: str | None = "LinkedIn Job Scraper"
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
        if not is_acknowledged_env():
            self.push_screen(ConsentScreen(), self._on_consent)
            return

        await self._initialize_app()

    async def _initialize_app(self) -> None:
        """Finish initialization once consent is acknowledged."""
        await self._refresh_stats()

        table = self.query_one("#results-table", DataTable)
        table.add_columns("Job ID", "Title", "Company", "Location")

        self.log_message("[bold green]LinkedIn Job Scraper started[/bold green]")
        self.log_message("Use the panels on the left to search and scrape jobs.")

    def _on_consent(self, accepted: bool | None) -> None:
        """Handle consent dialog result."""
        if not accepted:
            self.exit()
            return

        set_acknowledged_env()
        self._running_task = asyncio.create_task(self._initialize_app())


def main() -> None:
    """Entry point for the TUI."""
    app = LinkedInScraperApp()
    app.run()
