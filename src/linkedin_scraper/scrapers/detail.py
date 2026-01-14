"""Feature 2: Job detail scraper - extracts full job information."""

from typing import Any

from playwright.async_api import Page

from linkedin_scraper.browser.human import HumanBehavior
from linkedin_scraper.logging_config import get_logger
from linkedin_scraper.models.job import JobDetail, JobIdSource
from linkedin_scraper.scrapers.base import BaseScraper
from linkedin_scraper.scrapers.recommended import RecommendedJobsScraper


__all__ = ["JobDetailScraper"]

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

    async def run(  # type: ignore[override]
        self,
        job_ids: list[str] | None = None,
        source: JobIdSource | None = None,
        limit: int | None = None,
        extract_recommended: bool = True,
    ) -> list[JobDetail]:
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
        # Get job IDs to scrape
        if job_ids is None:
            stored_jobs = await self._storage.get_job_ids(source=source, unscraped_only=True)
            job_ids = [j.job_id for j in stored_jobs]

        if limit:
            job_ids = job_ids[:limit]

        if not job_ids:
            logger.info("No job IDs to scrape")
            return []

        logger.info(f"Scraping details for {len(job_ids)} jobs")
        results: list[JobDetail] = []

        async with self._browser_manager.new_page() as (page, human):
            for i, job_id in enumerate(job_ids, 1):
                logger.info(f"[{i}/{len(job_ids)}] Scraping job: {job_id}")

                # Check if already scraped
                if await self._storage.job_detail_exists(job_id):
                    logger.debug(f"Job {job_id} already scraped, skipping")
                    continue

                try:
                    detail = await self._scrape_job_detail(page, human, job_id)
                    if detail:
                        await self._storage.save_job_detail(detail)
                        await self._storage.mark_job_scraped(job_id)
                        results.append(detail)

                        # Feature 3: Extract recommended job IDs
                        if extract_recommended:
                            recommended_ids = await self._recommended_scraper.extract_from_page(
                                page, human, job_id
                            )
                            if recommended_ids:
                                logger.info(f"Found {len(recommended_ids)} recommended jobs")

                except Exception as e:
                    logger.error(f"Error scraping job {job_id}: {e}")
                    await self._take_debug_screenshot(page, f"error_{job_id}")

                # Delay between jobs
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

        # Wait for job details to load
        loaded = await self._wait_for_job_content(page)
        if not loaded:
            logger.warning(f"Job content did not load for {job_id}")
            await self._take_debug_screenshot(page, f"no_content_{job_id}")
            return None

        # Simulate reading behavior
        await human.simulate_reading(2, 4)

        # Extract all job information
        detail = JobDetail(job_id=job_id)

        # Basic info
        detail.title = await self._extract_title(page)
        detail.company_name = await self._extract_company(page)
        detail.location = await self._extract_location(page)
        detail.workplace_type = await self._extract_workplace_type(page)

        # Job criteria
        criteria = await self._extract_job_criteria(page)
        detail.employment_type = criteria.get("employment_type")
        detail.seniority_level = criteria.get("seniority_level")
        detail.industry = criteria.get("industry")
        detail.job_function = criteria.get("job_function")

        # Description - may need to expand
        detail.description = await self._extract_description(page, human)

        # Metadata
        detail.posted_date = await self._extract_posted_date(page)
        detail.applicant_count = await self._extract_applicant_count(page)
        detail.salary_range = await self._extract_salary(page)

        # Skills
        detail.skills = await self._extract_skills(page)

        # Store raw sections for debugging
        detail.raw_sections = await self._extract_raw_sections(page)

        logger.debug(f"Extracted: {detail.title} at {detail.company_name}")
        return detail

    async def _wait_for_job_content(self, page: Page) -> bool:
        """Wait for job content to load."""
        selectors = [
            ".job-view-layout",
            ".jobs-unified-top-card",
            '[class*="job-details"]',
            ".top-card-layout",
        ]

        for selector in selectors:
            if await self._wait_for_element(page, selector, timeout_ms=10000):
                return True

        return False

    async def _extract_title(self, page: Page) -> str | None:
        """Extract job title."""
        selectors = [
            ".job-details-jobs-unified-top-card__job-title",
            ".jobs-unified-top-card__job-title",
            ".top-card-layout__title",
            "h1.job-title",
            "h1",
        ]

        for selector in selectors:
            title = await self._extract_text(page, selector)
            if title:
                return title
        return None

    async def _extract_company(self, page: Page) -> str | None:
        """Extract company name."""
        selectors = [
            ".job-details-jobs-unified-top-card__company-name",
            ".jobs-unified-top-card__company-name",
            ".topcard__org-name-link",
            'a[data-tracking-control-name*="company"]',
            ".top-card-layout__second-subline a",
        ]

        for selector in selectors:
            company = await self._extract_text(page, selector)
            if company:
                return company
        return None

    async def _extract_location(self, page: Page) -> str | None:
        """Extract job location."""
        selectors = [
            ".job-details-jobs-unified-top-card__bullet",
            ".jobs-unified-top-card__bullet",
            ".topcard__flavor--bullet",
            ".top-card-layout__second-subline span",
        ]

        for selector in selectors:
            location = await self._extract_text(page, selector)
            if location:
                return location
        return None

    async def _extract_workplace_type(self, page: Page) -> str | None:
        """Extract workplace type (Remote, Hybrid, On-site)."""
        selectors = [
            ".job-details-jobs-unified-top-card__workplace-type",
            ".jobs-unified-top-card__workplace-type",
            'span[class*="workplace-type"]',
        ]

        for selector in selectors:
            workplace = await self._extract_text(page, selector)
            if workplace:
                return workplace
        return None

    async def _extract_job_criteria(self, page: Page) -> dict[str, str | None]:
        """Extract job criteria section (employment type, seniority, etc.)."""
        criteria: dict[str, str | None] = {
            "employment_type": None,
            "seniority_level": None,
            "industry": None,
            "job_function": None,
        }

        # Try to find criteria list
        criteria_selectors = [
            ".job-details-jobs-unified-top-card__job-insight",
            ".jobs-unified-top-card__job-insight",
            ".description__job-criteria-list li",
            ".job-criteria-list li",
        ]

        for selector in criteria_selectors:
            try:
                items = page.locator(selector)
                count = await items.count()

                for i in range(count):
                    item = items.nth(i)
                    text = await item.inner_text()
                    text_lower = text.lower()

                    if (
                        "full-time" in text_lower
                        or "part-time" in text_lower
                        or "contract" in text_lower
                    ):
                        criteria["employment_type"] = text.strip()
                    elif (
                        "entry" in text_lower
                        or "senior" in text_lower
                        or "director" in text_lower
                        or "mid-senior" in text_lower
                    ):
                        criteria["seniority_level"] = text.strip()
                    elif "industry" in text_lower:
                        criteria["industry"] = text.replace("Industry:", "").strip()
                    elif "function" in text_lower:
                        criteria["job_function"] = text.replace("Job function:", "").strip()
            except Exception:
                continue

        return criteria

    async def _extract_description(self, page: Page, human: HumanBehavior) -> str | None:
        """Extract job description, expanding if necessary."""
        # Try to click "See more" button if present
        expand_selectors = [
            'button[aria-label*="Show more"]',
            'button:has-text("See more")',
            'button:has-text("Show more")',
            ".show-more-less-html__button",
        ]

        for selector in expand_selectors:
            try:
                button = page.locator(selector).first
                if await button.count() > 0 and await button.is_visible():
                    await human.human_click(button)
                    await human.random_delay(500, 1000)
                    break
            except Exception:
                continue

        # Extract description
        description_selectors = [
            ".jobs-description__content",
            ".jobs-description-content__text",
            ".description__text",
            ".show-more-less-html__markup",
            '[class*="job-description"]',
        ]

        for selector in description_selectors:
            desc = await self._extract_text(page, selector)
            if desc and len(desc) > 50:
                return desc

        return None

    async def _extract_posted_date(self, page: Page) -> str | None:
        """Extract when the job was posted."""
        selectors = [
            ".jobs-unified-top-card__posted-date",
            ".posted-time-ago__text",
            'span[class*="posted"]',
        ]

        for selector in selectors:
            date = await self._extract_text(page, selector)
            if date:
                return date
        return None

    async def _extract_applicant_count(self, page: Page) -> str | None:
        """Extract number of applicants."""
        selectors = [
            ".jobs-unified-top-card__applicant-count",
            'span[class*="applicant"]',
            'span:has-text("applicants")',
        ]

        for selector in selectors:
            count = await self._extract_text(page, selector)
            if count:
                return count
        return None

    async def _extract_salary(self, page: Page) -> str | None:
        """Extract salary range if available."""
        selectors = [
            ".job-details-jobs-unified-top-card__job-insight--highlight",
            'span[class*="salary"]',
            'span:has-text("$")',
            'span:has-text("€")',
            'span:has-text("£")',
        ]

        for selector in selectors:
            salary = await self._extract_text(page, selector)
            if salary and any(c in salary for c in "$€£"):
                return salary
        return None

    async def _extract_skills(self, page: Page) -> list[str]:
        """Extract required skills."""
        skills: list[str] = []

        skill_selectors = [
            ".job-details-skill-match-status-list__skill",
            '.job-details-how-you-match__skills-item span[aria-hidden="true"]',
            ".skill-match-modal__skill",
        ]

        for selector in skill_selectors:
            found = await self._extract_all_text(page, selector)
            skills.extend(found)

        return list(set(skills))

    async def _extract_raw_sections(self, page: Page) -> dict[str, Any]:
        """Extract raw sections for debugging/completeness."""
        sections: dict[str, Any] = {}

        # Try to capture main content areas
        section_selectors = {
            "top_card": ".jobs-unified-top-card",
            "description": ".jobs-description",
            "criteria": ".job-criteria-list",
            "skills": ".job-details-skill-match-status-list",
        }

        for name, selector in section_selectors.items():
            text = await self._extract_text(page, selector)
            if text:
                sections[name] = text[:1000]  # Limit size

        return sections
