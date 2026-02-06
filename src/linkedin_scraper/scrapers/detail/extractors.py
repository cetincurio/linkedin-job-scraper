"""Extraction helpers for job detail pages."""

from __future__ import annotations

from typing import Any

from playwright.async_api import Page

from linkedin_scraper.browser.human import HumanBehavior
from linkedin_scraper.scrapers.base import BaseScraper


def _unique_list(items: list[str]) -> list[str]:
    # Preserve first-seen order for stable output.
    return list(dict.fromkeys(items))


async def wait_for_job_content(scraper: BaseScraper, page: Page) -> bool:
    """Wait for job content to load."""
    selectors = [
        ".job-view-layout",
        ".jobs-unified-top-card",
        '[class*="job-details"]',
        ".top-card-layout",
    ]

    for selector in selectors:
        if await scraper._wait_for_element(page, selector, timeout_ms=10000):
            return True

    return False


async def extract_title(scraper: BaseScraper, page: Page) -> str | None:
    """Extract job title."""
    selectors = [
        ".job-details-jobs-unified-top-card__job-title",
        ".jobs-unified-top-card__job-title",
        ".top-card-layout__title",
        "h1.job-title",
        "h1",
    ]

    for selector in selectors:
        title = await scraper._extract_text(page, selector)
        if title:
            return title
    return None


async def extract_company(scraper: BaseScraper, page: Page) -> str | None:
    """Extract company name."""
    selectors = [
        ".job-details-jobs-unified-top-card__company-name",
        ".jobs-unified-top-card__company-name",
        ".topcard__org-name-link",
        'a[data-tracking-control-name*="company"]',
        ".top-card-layout__second-subline a",
    ]

    for selector in selectors:
        company = await scraper._extract_text(page, selector)
        if company:
            return company
    return None


async def extract_location(scraper: BaseScraper, page: Page) -> str | None:
    """Extract job location."""
    selectors = [
        ".job-details-jobs-unified-top-card__bullet",
        ".jobs-unified-top-card__bullet",
        ".topcard__flavor--bullet",
        ".top-card-layout__second-subline span",
    ]

    for selector in selectors:
        location = await scraper._extract_text(page, selector)
        if location:
            return location
    return None


async def extract_workplace_type(scraper: BaseScraper, page: Page) -> str | None:
    """Extract workplace type (Remote, Hybrid, On-site)."""
    selectors = [
        ".job-details-jobs-unified-top-card__workplace-type",
        ".jobs-unified-top-card__workplace-type",
        'span[class*="workplace-type"]',
    ]

    for selector in selectors:
        workplace = await scraper._extract_text(page, selector)
        if workplace:
            return workplace
    return None


async def extract_job_criteria(page: Page) -> dict[str, str | None]:
    """Extract job criteria section (employment type, seniority, etc.)."""
    criteria: dict[str, str | None] = {
        "employment_type": None,
        "seniority_level": None,
        "industry": None,
        "job_function": None,
    }

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


async def extract_description(
    scraper: BaseScraper,
    page: Page,
    human: HumanBehavior,
) -> str | None:
    """Extract job description, expanding if necessary."""
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

    description_selectors = [
        ".jobs-description__content",
        ".jobs-description-content__text",
        ".description__text",
        ".show-more-less-html__markup",
        '[class*="job-description"]',
    ]

    for selector in description_selectors:
        desc = await scraper._extract_text(page, selector)
        if desc and len(desc) > 50:
            return desc

    return None


async def extract_posted_date(scraper: BaseScraper, page: Page) -> str | None:
    """Extract when the job was posted."""
    selectors = [
        ".jobs-unified-top-card__posted-date",
        ".posted-time-ago__text",
        'span[class*="posted"]',
    ]

    for selector in selectors:
        date = await scraper._extract_text(page, selector)
        if date:
            return date
    return None


async def extract_applicant_count(scraper: BaseScraper, page: Page) -> str | None:
    """Extract number of applicants."""
    selectors = [
        ".jobs-unified-top-card__applicant-count",
        'span[class*="applicant"]',
        'span:has-text("applicants")',
    ]

    for selector in selectors:
        count = await scraper._extract_text(page, selector)
        if count:
            return count
    return None


async def extract_salary(scraper: BaseScraper, page: Page) -> str | None:
    """Extract salary range if available."""
    selectors = [
        ".job-details-jobs-unified-top-card__job-insight--highlight",
        'span[class*="salary"]',
        'span:has-text("$")',
        'span:has-text("€")',
        'span:has-text("£")',
    ]

    for selector in selectors:
        salary = await scraper._extract_text(page, selector)
        if salary and any(c in salary for c in "$€£"):
            return salary
    return None


async def extract_skills(scraper: BaseScraper, page: Page) -> list[str]:
    """Extract required skills."""
    skills: list[str] = []

    skill_selectors = [
        ".job-details-skill-match-status-list__skill",
        '.job-details-how-you-match__skills-item span[aria-hidden="true"]',
        ".skill-match-modal__skill",
    ]

    for selector in skill_selectors:
        found = await scraper._extract_all_text(page, selector)
        skills.extend(found)

    return _unique_list(skills)


async def extract_raw_sections(scraper: BaseScraper, page: Page) -> dict[str, Any]:
    """Extract raw sections for debugging/completeness."""
    sections: dict[str, Any] = {}

    section_selectors = {
        "top_card": ".jobs-unified-top-card",
        "description": ".jobs-description",
        "criteria": ".job-criteria-list",
        "skills": ".job-details-skill-match-status-list",
    }

    for name, selector in section_selectors.items():
        text = await scraper._extract_text(page, selector)
        if text:
            sections[name] = text[:1000]

    return sections
