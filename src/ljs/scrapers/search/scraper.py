"""Feature 1: Job search scraper with pagination and job ID extraction."""

from __future__ import annotations

import urllib.parse
from typing import Any

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

from ljs.browser.human import HumanBehavior
from ljs.log import bind_log_context, log_debug, log_info, log_warning, timed
from ljs.logging_config import get_logger
from ljs.models.job import JobId, JobIdSource, JobSearchResult
from ljs.scrapers.base import BaseScraper

from .countries import COUNTRY_GEO_IDS


logger = get_logger(__name__)


class JobSearchScraper(BaseScraper):
    """
    Feature 1: Search for jobs by keyword and country.

    Extracts job IDs from search results by clicking "Show more" to load
    all available results.
    """

    SEARCH_URL_TEMPLATE = (
        "https://www.linkedin.com/jobs/search/?"
        "keywords={keywords}&"
        "location={location}&"
        "geoId={geo_id}&"
        "f_TPR=r604800"
    )  # Last 7 days

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._current_result: JobSearchResult | None = None

    def _build_search_url(self, keyword: str, country: str) -> str:
        """Build the LinkedIn job search URL."""
        geo_id = COUNTRY_GEO_IDS.get(country.lower(), "")

        if not geo_id:
            # Keep the structured event code, but include a human-readable phrase
            # because some tests/assertions match on it.
            log_warning(logger, "search.geo_id.unknown Unknown country", country=country)

        return self.SEARCH_URL_TEMPLATE.format(
            keywords=urllib.parse.quote(keyword),
            location=urllib.parse.quote(country),
            geo_id=geo_id,
        )

    async def run(
        self,
        *,
        keyword: str | None = None,
        country: str | None = None,
        max_pages: int | None = None,
        **kwargs: Any,
    ) -> JobSearchResult:
        """
        Search for jobs and extract job IDs.

        Args:
            keyword: Search keyword (e.g., "python developer")
            country: Country name or code (e.g., "Germany", "DE")
            max_pages: Maximum number of "Show more" clicks

        Returns:
            JobSearchResult with all discovered job IDs
        """
        # Keep `**kwargs` for forward compatibility with the BaseScraper interface.
        _ = kwargs

        if not isinstance(keyword, str) or not isinstance(country, str):
            raise ValueError("keyword and country are required string arguments")

        if max_pages is None:
            max_pages = self._settings.max_pages_per_session
        if not isinstance(max_pages, int) or max_pages < 1:
            raise ValueError("max_pages must be an integer >= 1")

        self._current_result = JobSearchResult(
            keyword=keyword,
            country=country,
        )

        with bind_log_context(op="search", keyword=keyword, country=country):
            log_info(logger, "search.run", max_pages=max_pages)

            async with self._browser_manager.new_page() as (page, human):
                url = self._build_search_url(keyword, country)

                if not await self._safe_goto(page, url, human):
                    log_warning(logger, "search.page.load_failed", url=url)
                    return self._current_result

                await self._wait_for_job_listings(page, human)
                await self._extract_job_ids_from_page(page, keyword, country)

                pages_loaded = await self._load_all_results(page, human, max_pages)
                self._current_result.pages_scraped = pages_loaded

                await self._extract_job_ids_from_page(page, keyword, country)

                jobs = [
                    JobId(
                        job_id=jid,
                        source=JobIdSource.SEARCH,
                        search_keyword=keyword,
                        search_country=country,
                    )
                    for jid in self._current_result.job_ids
                ]
                with timed(logger, "storage.save_job_ids", count=len(jobs), source="search"):
                    saved = await self._storage.save_job_ids(jobs)

                log_info(
                    logger,
                    "search.complete",
                    total_found=self._current_result.total_found,
                    pages_scraped=self._current_result.pages_scraped,
                    saved=saved,
                )

                return self._current_result

    async def _wait_for_job_listings(self, page: Page, human: HumanBehavior) -> bool:
        """Wait for job listings to appear on the page."""
        selectors = [
            ".jobs-search__results-list",
            ".jobs-search-results-list",
            '[class*="job-card"]',
            '[class*="jobs-search-result"]',
        ]

        for selector in selectors:
            if await self._wait_for_element(page, selector, timeout_ms=10000):
                log_debug(logger, "search.listings.found", selector=selector)
                await human.simulate_reading(1, 2)
                return True

        log_warning(logger, "search.listings.not_found")
        await self._take_debug_screenshot(page, "no_job_listings")
        return False

    async def _extract_job_ids_from_page(
        self,
        page: Page,
        _keyword: str,
        _country: str,
    ) -> None:
        """Extract job IDs from the current page content."""
        assert self._current_result is not None, "No current result initialized"
        html = await page.content()
        job_ids = self.extract_job_ids_from_html(html)

        try:
            links = await page.locator('a[href*="/jobs/view/"]').all()
            for link in links:
                href = await link.get_attribute("href")
                if href:
                    job_id = self.extract_job_id_from_url(href)
                    if job_id:
                        job_ids.append(job_id)
        except Exception as e:
            log_debug(logger, "search.job_ids.from_links.error", error=str(e))

        unique_ids = list(dict.fromkeys(job_ids))
        new_ids = [jid for jid in unique_ids if jid not in self._current_result.job_ids]

        if new_ids:
            self._current_result.job_ids.extend(new_ids)
            self._current_result.total_found = len(self._current_result.job_ids)
            log_info(
                logger,
                "search.job_ids.new",
                new=len(new_ids),
                total=self._current_result.total_found,
            )
        else:
            log_debug(logger, "search.job_ids.none_new", total=self._current_result.total_found)

    async def _load_all_results(
        self,
        page: Page,
        human: HumanBehavior,
        max_pages: int,
    ) -> int:
        """
        Click "Show more" button repeatedly to load all results.

        Returns the number of pages loaded.
        """
        pages_loaded = 1
        consecutive_failures = 0
        max_failures = 3

        show_more_selectors = [
            'button[aria-label*="more jobs"]',
            'button[aria-label*="Show more"]',
            ".infinite-scroller__show-more-button",
            'button:has-text("Show more")',
            'button:has-text("See more jobs")',
            ".see-more-jobs button",
        ]

        while pages_loaded < max_pages and consecutive_failures < max_failures:
            await human.human_scroll("down", 400)
            await human.random_delay(800, 1500)

            clicked = False
            for selector in show_more_selectors:
                try:
                    button = page.locator(selector).first
                    if await button.count() > 0 and await button.is_visible():
                        log_debug(
                            logger,
                            "search.show_more.found",
                            selector=selector,
                            pages_loaded=pages_loaded,
                            max_pages=max_pages,
                        )

                        await button.scroll_into_view_if_needed()
                        await human.random_delay(300, 600)

                        await human.human_click(button)
                        await human.random_delay(1500, 3000)

                        assert self._current_result is not None
                        await self._extract_job_ids_from_page(
                            page,
                            self._current_result.keyword,
                            self._current_result.country,
                        )

                        pages_loaded += 1
                        consecutive_failures = 0
                        clicked = True
                        log_info(logger, "search.page.loaded", pages_loaded=pages_loaded)
                        break
                except PlaywrightTimeout:
                    continue
                except Exception as e:
                    log_debug(
                        logger, "search.show_more.click.error", selector=selector, error=str(e)
                    )
                    continue

            if not clicked:
                await human.scroll_to_bottom(max_scrolls=3)
                await human.random_delay(1000, 2000)

                assert self._current_result is not None
                old_count = self._current_result.total_found
                await self._extract_job_ids_from_page(
                    page,
                    self._current_result.keyword,
                    self._current_result.country,
                )

                if self._current_result.total_found > old_count:
                    pages_loaded += 1
                    consecutive_failures = 0
                    log_debug(
                        logger,
                        "search.page.loaded.via_scroll",
                        pages_loaded=pages_loaded,
                        old_total=old_count,
                        new_total=self._current_result.total_found,
                    )
                else:
                    consecutive_failures += 1
                    log_debug(
                        logger,
                        "search.no_new_content",
                        failures=consecutive_failures,
                        max_failures=max_failures,
                        total=self._current_result.total_found,
                    )

        if consecutive_failures >= max_failures:
            log_info(logger, "search.end_reached", pages_loaded=pages_loaded)

        return pages_loaded
