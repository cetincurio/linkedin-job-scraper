"""Tests for configuration module."""

from pathlib import Path

from linkedin_scraper.config import Settings, get_settings


class TestSettings:
    """Tests for Settings."""

    def test_default_settings(self) -> None:
        """Test default settings values."""
        # Avoid inheriting developer-local .env values when running tests.
        settings = Settings(_env_file=None)

        assert settings.headless is False
        assert settings.slow_mo == 50
        assert settings.browser_type == "chromium"
        assert settings.min_delay_ms == 800
        assert settings.max_delay_ms == 3000

    def test_settings_validation(self) -> None:
        """Test settings validation."""
        settings = Settings(min_delay_ms=100, max_delay_ms=500)

        assert settings.min_delay_ms == 100
        assert settings.max_delay_ms == 500

    def test_settings_paths(self, tmp_path: Path) -> None:
        """Test settings path properties."""
        settings = Settings(data_dir=tmp_path / "data")

        assert settings.job_ids_dir == tmp_path / "data" / "job_ids"
        assert settings.job_details_dir == tmp_path / "data" / "job_details"
        assert settings.screenshots_dir == tmp_path / "data" / "screenshots"

    def test_ensure_directories(self, tmp_path: Path) -> None:
        """Test directory creation."""
        settings = Settings(
            data_dir=tmp_path / "data",
            log_dir=tmp_path / "logs",
        )

        settings.ensure_directories()

        assert settings.job_ids_dir.exists()
        assert settings.job_details_dir.exists()
        assert settings.screenshots_dir.exists()
        assert settings.log_dir.exists()

    def test_get_settings_singleton(self) -> None:
        """Test that get_settings returns cached instance."""
        # Note: This test depends on module state, may need isolation
        settings1 = get_settings()
        settings2 = get_settings()

        # Should return same instance
        assert settings1 is settings2
