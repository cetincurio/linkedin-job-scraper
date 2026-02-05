"""Tests for TUI components.

These tests verify the TUI structure and widget presence.
Interactive behavior tests require manual testing or playwright integration.
"""

import pytest
from textual.binding import Binding, BindingType
from textual.widgets import DataTable, Input, Select, Static

from linkedin_scraper.tui import LinkedInScraperApp


@pytest.fixture
def app() -> LinkedInScraperApp:
    """Create app instance for testing."""
    return LinkedInScraperApp()


class TestTUIStructure:
    """Verify TUI has all required components."""

    async def test_main_panels_exist(self, app: LinkedInScraperApp) -> None:
        """Verify all main UI panels are present."""
        async with app.run_test():
            # Stats panel shows storage metrics
            stats = app.query_one("#stats-panel", Static)
            assert stats is not None

            # Log panel for activity output
            assert app.query_one("#log-panel") is not None

            # Results table for job data
            table = app.query_one("#results-table", DataTable)
            assert table is not None

    async def test_search_panel_has_required_inputs(self, app: LinkedInScraperApp) -> None:
        """Verify search panel has keyword, country, max-pages inputs and button."""
        async with app.run_test():
            keyword = app.query_one("#search-keyword", Input)
            country = app.query_one("#search-country", Select)
            max_pages = app.query_one("#search-max-pages", Input)
            btn = app.query_one("#btn-search")

            assert keyword is not None
            assert country is not None
            assert max_pages is not None
            assert btn is not None

    async def test_scrape_panel_has_required_inputs(self, app: LinkedInScraperApp) -> None:
        """Verify scrape panel has limit input and button."""
        async with app.run_test():
            limit = app.query_one("#scrape-limit", Input)
            btn = app.query_one("#btn-scrape")

            assert limit is not None
            assert btn is not None

    async def test_loop_panel_has_required_inputs(self, app: LinkedInScraperApp) -> None:
        """Verify loop panel has cycles input and button."""
        async with app.run_test():
            cycles = app.query_one("#loop-cycles", Input)
            btn = app.query_one("#btn-loop")

            assert cycles is not None
            assert btn is not None


def _binding_key(binding: BindingType) -> str:
    if isinstance(binding, Binding):
        return binding.key
    return binding[0]


class TestKeyboardShortcuts:
    """Test keyboard bindings are registered and functional."""

    async def test_bindings_are_registered(self, app: LinkedInScraperApp) -> None:
        """Verify all expected keyboard bindings are registered."""
        async with app.run_test():
            # Check that bindings exist in the app
            binding_keys = {_binding_key(b) for b in app.BINDINGS}
            assert "q" in binding_keys  # Quit
            assert "r" in binding_keys  # Refresh
            assert "c" in binding_keys  # Clear
            assert "d" in binding_keys  # Dark mode

    async def test_refresh_shortcut_triggers_action(self, app: LinkedInScraperApp) -> None:
        """Verify 'r' shortcut executes without error."""
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.press("r")
            await pilot.pause()
            # Stats panel should still exist after refresh
            assert app.query_one("#stats-panel") is not None

    async def test_clear_shortcut_triggers_action(self, app: LinkedInScraperApp) -> None:
        """Verify 'c' shortcut executes without error."""
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.press("c")
            await pilot.pause()
            # Log panel should still exist after clear
            assert app.query_one("#log-panel") is not None

    async def test_theme_toggle_shortcut_triggers_action(self, app: LinkedInScraperApp) -> None:
        """Verify 'd' shortcut executes theme toggle action."""
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.press("d")
            await pilot.pause()
            # App should still be functional after toggle
            assert app.query_one("#stats-panel") is not None
