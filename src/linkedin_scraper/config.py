"""Configuration management using Pydantic settings."""

import functools
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


__all__ = ["Settings", "get_settings"]


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    if TYPE_CHECKING:
        # Pydantic dynamically generates a rich `__init__` for settings models.
        # Some type checkers miss those parameters; declare the ones we rely on in tests.
        def __init__(self, *, _env_file: Any | None = None, **values: Any) -> None: ...

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="LINKEDIN_SCRAPER_",
        extra="ignore",
    )

    # Browser settings
    headless: bool = Field(default=False, description="Run browser in headless mode")
    slow_mo: int = Field(default=50, ge=0, le=500, description="Slow down operations by ms")
    browser_type: Literal["chromium", "firefox", "webkit"] = Field(
        default="chromium", description="Browser engine to use"
    )
    disable_browser_sandbox: bool = Field(
        default=False,
        description=(
            "Disable the Chromium sandbox (unsafe). "
            "Only enable this in hardened containers where the sandbox is unavailable."
        ),
    )

    # Anti-detection settings
    min_delay_ms: int = Field(default=800, ge=100, description="Minimum delay between actions")
    max_delay_ms: int = Field(default=3000, ge=500, description="Maximum delay between actions")
    typing_delay_ms: int = Field(default=80, ge=20, le=300, description="Delay between keystrokes")
    mouse_movement_steps: int = Field(default=25, ge=5, le=100, description="Mouse movement steps")

    # Scraping settings
    max_pages_per_session: int = Field(default=10, ge=1, description="Max pages to scrape per run")
    page_load_timeout_ms: int = Field(default=30000, description="Page load timeout")
    request_timeout_ms: int = Field(default=15000, description="Request timeout")

    # Storage paths
    data_dir: Path = Field(default=Path("data"), description="Data storage directory")
    log_dir: Path = Field(default=Path("logs"), description="Log directory")

    # Rate limiting
    min_request_interval_sec: float = Field(
        default=2.0,
        ge=0.0,
        description="Minimum seconds between requests (0 disables the minimum-gap limiter)",
    )
    max_requests_per_hour: int = Field(
        default=100,
        ge=0,
        description="Maximum requests per hour (0 disables the hourly limiter)",
    )

    @property
    def job_ids_dir(self) -> Path:
        """Directory for storing job IDs."""
        return self.data_dir / "job_ids"

    @property
    def job_details_dir(self) -> Path:
        """Directory for storing job details."""
        return self.data_dir / "job_details"

    @property
    def screenshots_dir(self) -> Path:
        """Directory for storing screenshots (debugging)."""
        return self.data_dir / "screenshots"

    def ensure_directories(self) -> None:
        """Create all required directories."""
        for directory in [
            self.data_dir,
            self.job_ids_dir,
            self.job_details_dir,
            self.screenshots_dir,
            self.log_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.ensure_directories()
    return settings
