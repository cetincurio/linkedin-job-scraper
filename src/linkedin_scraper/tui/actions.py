"""Shared actions for the TUI app."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

from textual.widgets import RichLog

from .widgets import StatsWidget


if TYPE_CHECKING:
    from .typing import TuiAppProtocol


class AppActions:
    """Common actions and helpers for the TUI app."""

    def log_message(self: TuiAppProtocol, message: str) -> None:
        """Add a message to the log panel."""
        log = self.query_one("#log-panel", RichLog)
        timestamp = datetime.now().strftime("%H:%M:%S")
        log.write(f"[dim]{timestamp}[/dim] {message}")

    async def _refresh_stats(self: TuiAppProtocol) -> None:
        """Refresh the stats widget."""
        stats_widget = self.query_one(StatsWidget)
        await stats_widget.refresh_stats()

    def action_refresh_stats(self: TuiAppProtocol) -> None:
        """Action to refresh statistics."""
        self._running_task = asyncio.create_task(self._refresh_stats())
        self.log_message("Stats refreshed")

    def action_clear_log(self: TuiAppProtocol) -> None:
        """Clear the log panel."""
        log = self.query_one("#log-panel", RichLog)
        log.clear()
        self.log_message("[dim]Log cleared[/dim]")

    def action_toggle_dark(self: TuiAppProtocol) -> None:
        """Toggle dark mode."""
        self.theme = "textual-dark" if self.theme == "textual-light" else "textual-light"
