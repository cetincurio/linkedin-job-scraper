"""Pytest configuration and shared fixtures."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from linkedin_scraper.config import Settings
from linkedin_scraper.storage.jobs import JobStorage


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop]:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_data_dir() -> Generator[Path]:
    """Create a temporary directory for test data."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_settings(temp_data_dir: Path) -> Settings:
    """Create test settings with temporary directories."""
    return Settings(
        data_dir=temp_data_dir / "data",
        log_dir=temp_data_dir / "logs",
        headless=True,
        min_delay_ms=100,
        max_delay_ms=500,
        typing_delay_ms=20,
    )


@pytest.fixture
async def storage(test_settings: Settings) -> AsyncGenerator[JobStorage]:
    """Create a JobStorage instance with test settings."""
    store = JobStorage(test_settings)
    yield store


@pytest.fixture
def sample_job_ids() -> list[str]:
    """Sample job IDs for testing."""
    return ["1234567890", "2345678901", "3456789012"]


@pytest.fixture
def sample_html_with_jobs() -> str:
    """Sample HTML containing job IDs."""
    return """
    <html>
    <body>
        <div data-job-id="1234567890">Job 1</div>
        <a href="/jobs/view/2345678901/">Job 2</a>
        <div data-entity-urn="urn:li:jobPosting:3456789012">Job 3</div>
    </body>
    </html>
    """
