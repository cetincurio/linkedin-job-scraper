"""Feature 3: Extract recommended/suggested job IDs from job detail pages."""

from typing import Any

from playwright.async_api import Page

from linkedin_scraper.browser.human import HumanBehavior
from linkedin_scraper.logging_config import get_logger
from linkedin_scraper.models.job import JobId, JobIdSource
from linkedin_scraper.scrapers.base import BaseScraper


__all__ = ["RecommendedJobsScraper"]

logger = get_logger(__name__)


class RecommendedJobsScraper(BaseScraper):
    """
    Feature 3: Extract job IDs from recommended/suggested sections.

    This scraper works in conjunction with the JobDetailScraper (Feature 2).
    When visiting a job detail page, it extracts job IDs from:
    - "People also viewed" section
    - "Similar jobs" section
    - "More jobs at [Company]" section
    - Any other recommendation sections
    """

    async def run(self, **kwargs: Any) -> list[str]:
        """
        Standalone run to extract recommended jobs from stored job IDs.

        Note: This is typically called internally by JobDetailScraper.
        For most use cases, use JobDetailScraper with extract_recommended=True.

        Args:
            parent_job_ids: Job IDs to visit and extract recommendations from
            limit: Maximum number of jobs to process

        Returns:
            List of newly discovered job IDs
        """
        parent_job_ids = kwargs.get("parent_job_ids")
        limit = kwargs.get("limit")

        if parent_job_ids is None:
            stored = await self._storage.get_job_ids(source=JobIdSource.SEARCH)
            parent_job_ids = [j.job_id for j in stored if j.scraped]

        if limit is not None:
            if not isinstance(limit, int) or limit < 1:
                raise ValueError("limit must be an integer >= 1")
            parent_job_ids = parent_job_ids[:limit]

        if not parent_job_ids:
            logger.info("No parent job IDs to process")
            return []

        all_recommended: list[str] = []

        async with self._browser_manager.new_page() as (page, human):
            for parent_id in parent_job_ids:
                url = f"https://www.linkedin.com/jobs/view/{parent_id}/"

                if await self._safe_goto(page, url, human):
                    recommended = await self.extract_from_page(page, human, parent_id)
                    all_recommended.extend(recommended)
                    await human.random_delay(2000, 4000)

        return list(dict.fromkeys(all_recommended))

    async def extract_from_page(
        self,
        page: Page,
        human: HumanBehavior,
        parent_job_id: str,
    ) -> list[str]:
        """
        Extract recommended job IDs from a job detail page.

        This method is called by JobDetailScraper after scraping job details.

        Args:
            page: Current page (already on job detail)
            human: Human behavior helper
            parent_job_id: The job ID of the current page

        Returns:
            List of extracted recommended job IDs
        """
        logger.debug(f"Extracting recommended jobs from {parent_job_id}")

        # Scroll down to load recommendation sections
        await human.human_scroll("down", 500)
        await human.random_delay(500, 1000)

        recommended_ids: set[str] = set()

        # Extract from various recommendation sections
        recommended_ids.update(await self._extract_similar_jobs(page))
        recommended_ids.update(await self._extract_people_also_viewed(page))
        recommended_ids.update(await self._extract_more_jobs_at_company(page))
        recommended_ids.update(await self._extract_from_sidebar(page))

        # Remove the parent job ID from results
        recommended_ids.discard(parent_job_id)

        if recommended_ids:
            # Save to storage
            jobs = [
                JobId(
                    job_id=jid,
                    source=JobIdSource.RECOMMENDED,
                    parent_job_id=parent_job_id,
                )
                for jid in sorted(recommended_ids, key=self._job_id_sort_key)
            ]
            saved = await self._storage.save_job_ids(jobs)
            logger.info(f"Saved {saved} new recommended job IDs from {parent_job_id}")

        # Keep the element type `str` for type checking (see note in BaseScraper).
        return sorted(recommended_ids, key=self._job_id_sort_key)

    async def _extract_similar_jobs(self, page: Page) -> set[str]:
        """Extract job IDs from 'Similar jobs' section."""
        job_ids: set[str] = set()

        selectors = [
            '.similar-jobs a[href*="/jobs/view/"]',
            'section[class*="similar"] a[href*="/jobs/view/"]',
            '[data-test="similar-jobs"] a[href*="/jobs/view/"]',
        ]

        for selector in selectors:
            ids = await self._extract_job_ids_from_selector(page, selector)
            job_ids.update(ids)

        if job_ids:
            logger.debug(f"Found {len(job_ids)} similar jobs")

        return job_ids

    async def _extract_people_also_viewed(self, page: Page) -> set[str]:
        """Extract job IDs from 'People also viewed' section."""
        job_ids: set[str] = set()

        selectors = [
            '.people-also-viewed a[href*="/jobs/view/"]',
            'section[class*="also-viewed"] a[href*="/jobs/view/"]',
            '[class*="also-viewed"] a[href*="/jobs/view/"]',
        ]

        for selector in selectors:
            ids = await self._extract_job_ids_from_selector(page, selector)
            job_ids.update(ids)

        if job_ids:
            logger.debug(f"Found {len(job_ids)} 'people also viewed' jobs")

        return job_ids

    async def _extract_more_jobs_at_company(self, page: Page) -> set[str]:
        """Extract job IDs from 'More jobs at [Company]' section."""
        job_ids: set[str] = set()

        selectors = [
            'section[class*="more-jobs"] a[href*="/jobs/view/"]',
            '[class*="company-jobs"] a[href*="/jobs/view/"]',
            '.jobs-company a[href*="/jobs/view/"]',
        ]

        for selector in selectors:
            ids = await self._extract_job_ids_from_selector(page, selector)
            job_ids.update(ids)

        if job_ids:
            logger.debug(f"Found {len(job_ids)} 'more jobs at company'")

        return job_ids

    async def _extract_from_sidebar(self, page: Page) -> set[str]:
        """Extract job IDs from sidebar recommendations."""
        job_ids: set[str] = set()

        selectors = [
            '.jobs-similar-jobs a[href*="/jobs/view/"]',
            'aside a[href*="/jobs/view/"]',
            '.scaffold-layout__aside a[href*="/jobs/view/"]',
        ]

        for selector in selectors:
            ids = await self._extract_job_ids_from_selector(page, selector)
            job_ids.update(ids)

        if job_ids:
            logger.debug(f"Found {len(job_ids)} sidebar jobs")

        return job_ids

    async def _extract_job_ids_from_selector(
        self,
        page: Page,
        selector: str,
    ) -> set[str]:
        """Extract job IDs from elements matching the selector."""
        job_ids: set[str] = set()

        try:
            elements = page.locator(selector)
            count = await elements.count()

            for i in range(count):
                href = await elements.nth(i).get_attribute("href")
                if href:
                    job_id = self.extract_job_id_from_url(href)
                    if job_id:
                        job_ids.add(job_id)
        except Exception as e:
            logger.debug(f"Error extracting from {selector}: {e}")

        return job_ids

    async def _extract_all_from_html(self, page: Page) -> set[str]:
        """Fallback: extract all job IDs from page HTML."""
        html = await page.content()
        return set(self.extract_job_ids_from_html(html))
