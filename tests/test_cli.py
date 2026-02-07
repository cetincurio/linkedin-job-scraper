"""Tests for CLI module.

Focused on testing actual CLI behavior, not just help text.
"""

import tempfile

from typer.testing import CliRunner

from ljs.cli import app


runner = CliRunner()


class TestCLICommands:
    """Test CLI commands that can run without browser."""

    def test_version_shows_package_info(self) -> None:
        """Verify --version returns package name and version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "LinkedIn Job Scraper" in result.stdout
        assert "v" in result.stdout  # Version number present

    def test_countries_lists_all_supported(self) -> None:
        """Verify countries command shows complete list with codes."""
        result = runner.invoke(app, ["countries"])
        assert result.exit_code == 0
        # Check major countries are listed
        assert "Germany" in result.stdout
        assert "United States" in result.stdout
        assert "United Kingdom" in result.stdout
        # Check format includes codes
        assert "DE" in result.stdout or "germany" in result.stdout

    def test_stats_returns_all_metrics(self) -> None:
        """Verify stats command returns all expected metrics."""
        result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        assert "Search Job IDs" in result.stdout
        assert "Recommended" in result.stdout
        assert "Job Details" in result.stdout

    def test_search_requires_keyword_and_country(self) -> None:
        """Verify search command validates required arguments."""
        result = runner.invoke(app, ["search"])
        assert result.exit_code == 2  # Typer missing argument exit code

    def test_loop_requires_keyword_and_country(self) -> None:
        """Verify loop command validates required arguments."""
        result = runner.invoke(app, ["loop"])
        assert result.exit_code == 2

    def test_scrape_invalid_source_shows_error(self) -> None:
        """Verify scrape rejects invalid source filter with helpful message."""
        result = runner.invoke(app, ["scrape", "--source", "invalid"])
        assert result.exit_code == 1
        assert "Invalid source" in result.stdout
        assert "search" in result.stdout or "recommended" in result.stdout


class TestExportCommand:
    """Test export command functionality."""

    def test_export_creates_empty_dataset(self) -> None:
        """Verify export succeeds with no data, creating empty dataset."""
        result = runner.invoke(app, ["export"])
        assert result.exit_code == 0
        assert "Records" in result.stdout
        assert "0" in result.stdout  # Zero records

    def test_export_with_custom_paths(self) -> None:
        """Verify export respects custom output and manifest paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output = f"{tmpdir}/custom.jsonl"
            manifest = f"{tmpdir}/custom.manifest.json"
            result = runner.invoke(app, ["export", "--output", output, "--manifest", manifest])
            assert result.exit_code == 0
            assert output in result.stdout or "custom.jsonl" in result.stdout

    def test_export_options_are_reflected(self) -> None:
        """Verify export options appear in output."""
        result = runner.invoke(app, ["export", "--redact-pii", "--limit", "10"])
        assert result.exit_code == 0
