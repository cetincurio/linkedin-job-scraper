"""Base scraper class with common functionality."""

import asyncio
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

from ljs.browser.context import BrowserManager
from ljs.browser.human import HumanBehavior
from ljs.config import Settings, get_settings
from ljs.log import log_debug, log_error, log_exception, log_info, log_warning, timed
from ljs.logging_config import get_logger
from ljs.storage.jobs import JobStorage


__all__ = ["BaseScraper"]

logger = get_logger(__name__)


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""

    LINKEDIN_BASE_URL = "https://www.linkedin.com"
    JOBS_BASE_URL = "https://www.linkedin.com/jobs"
    _RATE_LIMIT_MIN_WINDOW_S = 60.0

    def __init__(
        self,
        settings: Settings | None = None,
        storage: JobStorage | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._storage = storage or JobStorage(self._settings)
        self._browser_manager = BrowserManager(self._settings)
        self._request_count = 0
        self._session_start: datetime | None = None
        self._last_request_time_mono: float | None = None

    @abstractmethod
    async def run(self, **kwargs: Any) -> Any:
        """Execute the scraper's main functionality."""
        ...

    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting."""
        # Respect a minimum gap between requests, independent of hourly limits.
        min_interval = float(self._settings.min_request_interval_sec)
        if min_interval > 0 and self._last_request_time_mono is not None:
            elapsed = time.monotonic() - self._last_request_time_mono
            if elapsed < min_interval:
                log_debug(
                    logger,
                    "rate_limit.min_interval.sleep",
                    elapsed_s=round(elapsed, 3),
                    sleep_s=round(min_interval - elapsed, 3),
                    min_interval_s=min_interval,
                )
                await asyncio.sleep(min_interval - elapsed)

        max_per_hour = self._settings.max_requests_per_hour
        if max_per_hour <= 0:
            self._request_count += 1
            self._last_request_time_mono = time.monotonic()
            log_debug(
                logger,
                "rate_limit.disabled",
                max_per_hour=max_per_hour,
                request_count=self._request_count,
            )
            return

        if self._session_start is None:
            self._session_start = datetime.now()
            log_debug(logger, "rate_limit.session.start", session_start=str(self._session_start))

        elapsed_s = (datetime.now() - self._session_start).total_seconds()
        effective_elapsed_s = max(elapsed_s, self._RATE_LIMIT_MIN_WINDOW_S)
        elapsed_hours = effective_elapsed_s / 3600.0

        rate = (self._request_count / elapsed_hours) if self._request_count else 0.0
        if rate > max_per_hour:
            # Compute the minimum additional time needed to bring the average back under limit.
            required_elapsed_s = (self._request_count * 3600.0) / float(max_per_hour)
            wait_s = max(0.0, required_elapsed_s - elapsed_s)
            # `wait_s` should be positive when `rate > max_per_hour`,
            # but keep it safe and branch-free.
            log_warning(
                logger,
                "rate_limit.max_per_hour.sleep",
                max_per_hour=max_per_hour,
                request_count=self._request_count,
                elapsed_s=round(elapsed_s, 3),
                rate_per_hour=round(rate, 3),
                sleep_s=round(wait_s, 3),
            )
            await asyncio.sleep(wait_s)

        self._request_count += 1
        self._last_request_time_mono = time.monotonic()
        log_debug(
            logger,
            "rate_limit.tick",
            request_count=self._request_count,
            max_per_hour=max_per_hour,
        )

    async def _safe_goto(
        self,
        page: Page,
        url: str,
        human: HumanBehavior,
    ) -> bool:
        """
        Navigate to a URL with rate limiting and error handling.

        Returns True if navigation succeeded.
        """
        await self._check_rate_limit()

        try:
            log_info(logger, "nav.goto", url=url)
            await human.random_delay(500, 1500)

            with timed(logger, "nav.goto", url=url):
                response = await page.goto(url, wait_until="domcontentloaded")

            if response and response.status >= 400:
                log_error(logger, "nav.goto.http_error", url=url, http_status=response.status)
                return False

            # Wait for page to stabilize
            await human.random_delay(1000, 2000)
            log_debug(
                logger,
                "nav.goto.ok",
                url=url,
                http_status=(response.status if response else None),
            )
            return True

        except PlaywrightTimeout:
            log_error(logger, "nav.goto.timeout", url=url)
            return False
        except Exception:
            log_exception(logger, "nav.goto.error", url=url)
            return False

    async def _wait_for_element(
        self,
        page: Page,
        selector: str,
        timeout_ms: int | None = None,
    ) -> bool:
        """Wait for an element to appear on the page."""
        timeout = timeout_ms or self._settings.request_timeout_ms
        try:
            with timed(logger, "wait_for_selector", selector=selector, timeout_ms=timeout):
                await page.wait_for_selector(selector, timeout=timeout)
            log_debug(logger, "wait_for_selector.ok", selector=selector, timeout_ms=timeout)
            return True
        except PlaywrightTimeout:
            log_debug(logger, "wait_for_selector.timeout", selector=selector, timeout_ms=timeout)
            return False

    async def _extract_text(
        self,
        page: Page,
        selector: str,
        default: str = "",
    ) -> str:
        """Safely extract text from an element."""
        try:
            element = page.locator(selector).first
            if await element.count() > 0:
                text = await element.inner_text()
                return text.strip()
        except Exception as e:
            log_debug(logger, "extract_text.error", selector=selector, error=str(e))
        return default

    async def _extract_all_text(
        self,
        page: Page,
        selector: str,
    ) -> list[str]:
        """Extract text from all matching elements."""
        try:
            elements = page.locator(selector)
            count = await elements.count()
            texts = []
            for i in range(count):
                text = await elements.nth(i).inner_text()
                if text.strip():
                    texts.append(text.strip())
            return texts
        except Exception as e:
            log_debug(logger, "extract_all_text.error", selector=selector, error=str(e))
            return []

    @staticmethod
    def extract_job_id_from_url(url: str) -> str | None:
        """Extract job ID from a LinkedIn job URL."""
        # Pattern: /jobs/view/1234567890/ or /jobs/view/1234567890?...
        patterns = [
            r"/jobs/view/(\d+)",
            r"currentJobId=(\d+)",
            r"/jobs/(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    @staticmethod
    def _job_id_sort_key(s: str) -> int:
        """Sort key for job IDs.

        We intentionally keep the input type narrow (`str`) so type checkers don't
        widen the element type of the collection being sorted.
        """
        return int(s)

    @staticmethod
    def extract_job_ids_from_html(html: str) -> list[str]:
        """Extract job IDs from HTML content."""
        # Multiple patterns for different LinkedIn page formats
        patterns = [
            r'data-job-id="(\d+)"',
            r'data-entity-urn="urn:li:jobPosting:(\d+)"',
            r'href="/jobs/view/(\d+)',
            r"jobPosting:(\d+)",
        ]

        job_ids: set[str] = set()
        for pattern in patterns:
            matches = re.findall(pattern, html)
            job_ids.update(matches)

        # Stable output is important for reproducible runs and testability.
        # NOTE: `sorted(..., key=int)` causes type checkers to infer an overly-broad
        # element type because `int()` accepts many inputs; keep the element type `str`.
        return sorted(job_ids, key=BaseScraper._job_id_sort_key)

    async def _take_debug_screenshot(self, page: Page, name: str) -> None:
        """Take a screenshot for debugging purposes."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self._settings.screenshots_dir / f"{name}_{timestamp}.png"
        await page.screenshot(path=str(path))
        log_debug(logger, "screenshot.saved", path=path, name=name)
