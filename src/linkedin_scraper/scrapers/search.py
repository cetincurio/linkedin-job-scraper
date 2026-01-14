"""Feature 1: Job search scraper with pagination and job ID extraction."""

import urllib.parse
from typing import Any

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

from linkedin_scraper.browser.human import HumanBehavior
from linkedin_scraper.logging_config import get_logger
from linkedin_scraper.models.job import JobId, JobIdSource, JobSearchResult
from linkedin_scraper.scrapers.base import BaseScraper


__all__ = ["JobSearchScraper"]

logger = get_logger(__name__)

# LinkedIn GeoIDs for countries (partial list)
COUNTRY_GEO_IDS: dict[str, str] = {
    "united states": "103644278",
    "usa": "103644278",
    "us": "103644278",
    "united kingdom": "101165590",
    "uk": "101165590",
    "germany": "101282230",
    "de": "101282230",
    "france": "105015875",
    "fr": "105015875",
    "netherlands": "102890719",
    "nl": "102890719",
    "canada": "101174742",
    "ca": "101174742",
    "australia": "101452733",
    "au": "101452733",
    "india": "102713980",
    "in": "102713980",
    "spain": "105646813",
    "es": "105646813",
    "italy": "103350119",
    "it": "103350119",
    "turkey": "102105699",
    "tr": "102105699",
    "poland": "105072130",
    "pl": "105072130",
    "sweden": "105117694",
    "se": "105117694",
    "switzerland": "106693272",
    "ch": "106693272",
    "belgium": "100565514",
    "be": "100565514",
    "austria": "103883259",
    "at": "103883259",
    "ireland": "104738515",
    "ie": "104738515",
    "portugal": "100364837",
    "pt": "100364837",
    "denmark": "104514075",
    "dk": "104514075",
    "norway": "103819153",
    "no": "103819153",
    "finland": "100456013",
    "fi": "100456013",
}


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
            logger.warning(f"Unknown country '{country}', searching without geo filter")

        return self.SEARCH_URL_TEMPLATE.format(
            keywords=urllib.parse.quote(keyword),
            location=urllib.parse.quote(country),
            geo_id=geo_id,
        )

    async def run(  # type: ignore[override]
        self,
        keyword: str,
        country: str,
        max_pages: int | None = None,
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
        max_pages = max_pages or self._settings.max_pages_per_session

        self._current_result = JobSearchResult(
            keyword=keyword,
            country=country,
        )

        logger.info(f"Starting job search: '{keyword}' in {country}")

        async with self._browser_manager.new_page() as (page, human):
            url = self._build_search_url(keyword, country)

            if not await self._safe_goto(page, url, human):
                logger.error("Failed to load search page")
                return self._current_result

            # Wait for job listings to load
            await self._wait_for_job_listings(page, human)

            # Extract initial job IDs
            await self._extract_job_ids_from_page(page, keyword, country)

            # Click "Show more" to load additional results
            pages_loaded = await self._load_all_results(page, human, max_pages)
            self._current_result.pages_scraped = pages_loaded

            # Final extraction
            await self._extract_job_ids_from_page(page, keyword, country)

            # Save job IDs to storage
            jobs = [
                JobId(
                    job_id=jid,
                    source=JobIdSource.SEARCH,
                    search_keyword=keyword,
                    search_country=country,
                )
                for jid in self._current_result.job_ids
            ]
            saved = await self._storage.save_job_ids(jobs)

            logger.info(
                f"Search complete: found {self._current_result.total_found} jobs, "
                f"saved {saved} new IDs"
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
                logger.debug(f"Job listings found with selector: {selector}")
                await human.simulate_reading(1, 2)
                return True

        logger.warning("Could not find job listings on page")
        await self._take_debug_screenshot(page, "no_job_listings")
        return False

    async def _extract_job_ids_from_page(
        self,
        page: Page,
        _keyword: str,
        _country: str,
    ) -> None:
        """Extract job IDs from the current page content."""
        html = await page.content()
        job_ids = self.extract_job_ids_from_html(html)

        # Also try extracting from job card links
        try:
            links = await page.locator('a[href*="/jobs/view/"]').all()
            for link in links:
                href = await link.get_attribute("href")
                if href:
                    job_id = self.extract_job_id_from_url(href)
                    if job_id:
                        job_ids.append(job_id)
        except Exception as e:
            logger.debug(f"Error extracting job IDs from links: {e}")

        # Deduplicate and update result
        unique_ids = list(set(job_ids))
        assert self._current_result is not None, "No current result initialized"
        new_ids = [jid for jid in unique_ids if jid not in self._current_result.job_ids]

        if new_ids:
            self._current_result.job_ids.extend(new_ids)
            self._current_result.total_found = len(self._current_result.job_ids)
            logger.info(
                f"Found {len(new_ids)} new job IDs (total: {self._current_result.total_found})"
            )

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
            # Scroll down first to trigger lazy loading
            await human.human_scroll("down", 400)
            await human.random_delay(800, 1500)

            # Try to find and click "Show more" button
            clicked = False
            for selector in show_more_selectors:
                try:
                    button = page.locator(selector).first
                    if await button.count() > 0 and await button.is_visible():
                        logger.debug(f"Found 'Show more' button: {selector}")

                        # Scroll button into view
                        await button.scroll_into_view_if_needed()
                        await human.random_delay(300, 600)

                        # Human-like click
                        await human.human_click(button)
                        await human.random_delay(1500, 3000)

                        # Extract new job IDs
                        assert self._current_result is not None
                        await self._extract_job_ids_from_page(
                            page,
                            self._current_result.keyword,
                            self._current_result.country,
                        )

                        pages_loaded += 1
                        consecutive_failures = 0
                        clicked = True
                        logger.info(f"Loaded page {pages_loaded}")
                        break
                except PlaywrightTimeout:
                    continue
                except Exception as e:
                    logger.debug(f"Error clicking button {selector}: {e}")
                    continue

            if not clicked:
                # Try scrolling to bottom to trigger infinite scroll
                await human.scroll_to_bottom(max_scrolls=3)
                await human.random_delay(1000, 2000)

                # Check if new content loaded
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
                else:
                    consecutive_failures += 1
                    logger.debug(
                        f"No new content loaded (failure {consecutive_failures}/{max_failures})"
                    )

        if consecutive_failures >= max_failures:
            logger.info("Reached end of search results")

        return pages_loaded
