"""Unit tests for detail extractor helpers (core paths)."""

from __future__ import annotations

from typing import cast

import pytest
from playwright.async_api import Page

from linkedin_scraper.scrapers.base import BaseScraper
from linkedin_scraper.scrapers.detail.extractors import (
    extract_applicant_count,
    extract_company,
    extract_location,
    extract_posted_date,
    extract_raw_sections,
    extract_salary,
    extract_title,
    extract_workplace_type,
    wait_for_job_content,
)
from tests.test_fakes_detail_extractors import DetailFakePage, DetailFakeScraper


@pytest.mark.asyncio
async def test_wait_for_job_content_true_when_any_selector_present() -> None:
    scraper = DetailFakeScraper(selectors_present={".jobs-unified-top-card"})
    ok = await wait_for_job_content(
        cast(BaseScraper, scraper), cast(Page, DetailFakePage(expand_visible=False))
    )
    assert ok is True


@pytest.mark.asyncio
async def test_wait_for_job_content_false_when_no_selector_present() -> None:
    scraper = DetailFakeScraper(selectors_present=set())
    ok = await wait_for_job_content(
        cast(BaseScraper, scraper), cast(Page, DetailFakePage(expand_visible=False))
    )
    assert ok is False


@pytest.mark.asyncio
async def test_extract_basic_fields_from_first_matching_selector() -> None:
    scraper = DetailFakeScraper(
        text_by_selector={
            "h1": "Title",
            ".top-card-layout__second-subline a": "Company",
            ".top-card-layout__second-subline span": "Location",
            'span[class*="workplace-type"]': "Remote",
            'span[class*="posted"]': "1 day ago",
            'span:has-text("applicants")': "10 applicants",
            'span:has-text("$")': "$100k",
        }
    )
    page = cast(Page, DetailFakePage(expand_visible=False))

    typed_scraper = cast(BaseScraper, scraper)
    assert await extract_title(typed_scraper, page) == "Title"
    assert await extract_company(typed_scraper, page) == "Company"
    assert await extract_location(typed_scraper, page) == "Location"
    assert await extract_workplace_type(typed_scraper, page) == "Remote"
    assert await extract_posted_date(typed_scraper, page) == "1 day ago"
    assert await extract_applicant_count(typed_scraper, page) == "10 applicants"
    assert await extract_salary(typed_scraper, page) == "$100k"


@pytest.mark.asyncio
async def test_extractors_return_none_when_no_text_found() -> None:
    scraper = DetailFakeScraper()
    page = cast(Page, DetailFakePage(expand_visible=False))
    typed_scraper = cast(BaseScraper, scraper)

    assert await extract_title(typed_scraper, page) is None
    assert await extract_company(typed_scraper, page) is None
    assert await extract_location(typed_scraper, page) is None
    assert await extract_workplace_type(typed_scraper, page) is None
    assert await extract_posted_date(typed_scraper, page) is None
    assert await extract_applicant_count(typed_scraper, page) is None
    assert await extract_salary(typed_scraper, page) is None


@pytest.mark.asyncio
async def test_extract_salary_requires_currency_symbol() -> None:
    scraper = DetailFakeScraper(
        text_by_selector={".job-details-jobs-unified-top-card__job-insight--highlight": "100k"}
    )
    page = cast(Page, DetailFakePage(expand_visible=False))
    out = await extract_salary(cast(BaseScraper, scraper), page)
    assert out is None


@pytest.mark.asyncio
async def test_extract_raw_sections_omits_empty_sections() -> None:
    scraper = DetailFakeScraper(text_by_selector={".jobs-unified-top-card": ""})
    page = cast(Page, DetailFakePage(expand_visible=False))
    sections = await extract_raw_sections(cast(BaseScraper, scraper), page)
    assert sections == {}
