"""Feature 2: Job detail scraper - extracts full job information."""

from __future__ import annotations

from typing import Any

from playwright.async_api import Page

from linkedin_scraper.browser.human import HumanBehavior
from linkedin_scraper.logging_config import get_logger
from linkedin_scraper.models.job import JobDetail
from linkedin_scraper.scrapers.base import BaseScraper
from linkedin_scraper.scrapers.recommended import RecommendedJobsScraper

from .extractors import (
    extract_applicant_count,
    extract_company,
    extract_description,
    extract_job_criteria,
    extract_location,
    extract_posted_date,
    extract_raw_sections,
    extract_salary,
    extract_skills,
    extract_title,
    extract_workplace_type,
    wait_for_job_content,
)


logger = get_logger(__name__)


class JobDetailScraper(BaseScraper):
    """
    Feature 2: Scrape detailed job information from job pages.

    Also integrates with Feature 3 to extract recommended job IDs.
    """

    JOB_URL_TEMPLATE = "https://www.linkedin.com/jobs/view/{job_id}/"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._recommended_scraper = RecommendedJobsScraper(self._settings, self._storage)

    async def run(self, **kwargs: Any) -> list[JobDetail]:
        """
        Scrape job details for given job IDs.

        Args:
            job_ids: Specific job IDs to scrape, or None to use stored unscraped IDs
            source: Filter stored job IDs by source
            limit: Maximum number of jobs to scrape
            extract_recommended: Whether to extract recommended job IDs (Feature 3)

        Returns:
            List of scraped JobDetail objects
        """
        job_ids = kwargs.get("job_ids")
        source = kwargs.get("source")
        limit = kwargs.get("limit")
        extract_recommended = kwargs.get("extract_recommended", True)

        if job_ids is None:
            stored_jobs = await self._storage.get_job_ids(source=source, unscraped_only=True)
            job_ids = [j.job_id for j in stored_jobs]

        if limit is not None:
            if not isinstance(limit, int) or limit < 1:
                raise ValueError("limit must be an integer >= 1")
            job_ids = job_ids[:limit]

        if not job_ids:
            logger.info("No job IDs to scrape")
            return []

        logger.info(f"Scraping details for {len(job_ids)} jobs")
        results: list[JobDetail] = []

        async with self._browser_manager.new_page() as (page, human):
            for i, job_id in enumerate(job_ids, 1):
                logger.info(f"[{i}/{len(job_ids)}] Scraping job: {job_id}")

                if await self._storage.job_detail_exists(job_id):
                    logger.debug(f"Job {job_id} already scraped, skipping")
                    continue

                try:
                    detail = await self._scrape_job_detail(page, human, job_id)
                    if detail:
                        await self._storage.save_job_detail(detail)
                        await self._storage.mark_job_scraped(job_id)
                        results.append(detail)

                        if extract_recommended:
                            recommended_ids = await self._recommended_scraper.extract_from_page(
                                page, human, job_id
                            )
                            if recommended_ids:
                                logger.info(f"Found {len(recommended_ids)} recommended jobs")

                except Exception:
                    logger.exception("Error scraping job %s", job_id)
                    await self._take_debug_screenshot(page, f"error_{job_id}")

                await human.random_delay(2000, 4000)

        logger.info(f"Scraped {len(results)} job details")
        return results

    async def _scrape_job_detail(
        self,
        page: Page,
        human: HumanBehavior,
        job_id: str,
    ) -> JobDetail | None:
        """Scrape details from a single job page."""
        url = self.JOB_URL_TEMPLATE.format(job_id=job_id)

        if not await self._safe_goto(page, url, human):
            return None

        loaded = await wait_for_job_content(self, page)
        if not loaded:
            logger.warning(f"Job content did not load for {job_id}")
            await self._take_debug_screenshot(page, f"no_content_{job_id}")
            return None

        await human.simulate_reading(2, 4)

        detail = JobDetail(job_id=job_id)

        detail.title = await extract_title(self, page)
        detail.company_name = await extract_company(self, page)
        detail.location = await extract_location(self, page)
        detail.workplace_type = await extract_workplace_type(self, page)

        criteria = await extract_job_criteria(page)
        detail.employment_type = criteria.get("employment_type")
        detail.seniority_level = criteria.get("seniority_level")
        detail.industry = criteria.get("industry")
        detail.job_function = criteria.get("job_function")

        detail.description = await extract_description(self, page, human)

        detail.posted_date = await extract_posted_date(self, page)
        detail.applicant_count = await extract_applicant_count(self, page)
        detail.salary_range = await extract_salary(self, page)

        detail.skills = await extract_skills(self, page)
        detail.raw_sections = await extract_raw_sections(self, page)

        logger.debug(f"Extracted: {detail.title} at {detail.company_name}")
        return detail
