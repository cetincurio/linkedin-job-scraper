"""Unit tests for job detail extractor helpers using fakes."""

from __future__ import annotations

from typing import Any, cast

import pytest
from playwright.async_api import Page

from linkedin_scraper.browser.human import HumanBehavior
from linkedin_scraper.scrapers.base import BaseScraper
from linkedin_scraper.scrapers.detail.extractors import (
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


class _FakeScraper:
    def __init__(
        self,
        *,
        text_by_selector: dict[str, str] | None = None,
        all_text_by_selector: dict[str, list[str]] | None = None,
        selectors_present: set[str] | None = None,
    ) -> None:
        self._text_by_selector = text_by_selector or {}
        self._all_text_by_selector = all_text_by_selector or {}
        self._selectors_present = selectors_present or set()

    async def _wait_for_element(
        self, _page: Any, selector: str, *, timeout_ms: int | None = None
    ) -> bool:
        _ = timeout_ms
        return selector in self._selectors_present

    async def _extract_text(self, _page: Any, selector: str, default: str = "") -> str:
        return self._text_by_selector.get(selector, default)

    async def _extract_all_text(self, _page: Any, selector: str) -> list[str]:
        return self._all_text_by_selector.get(selector, [])


class _FakeButtonLocator:
    def __init__(self, visible: bool) -> None:
        self._visible = visible
        self.clicked = False

    @property
    def first(self) -> _FakeButtonLocator:
        return self

    async def count(self) -> int:
        return 1

    async def is_visible(self) -> bool:
        return self._visible


class _FakeCriteriaItem:
    def __init__(self, text: str) -> None:
        self._text = text

    async def inner_text(self) -> str:
        return self._text


class _FakeCriteriaLocator:
    def __init__(self, items: list[_FakeCriteriaItem]) -> None:
        self._items = items

    async def count(self) -> int:
        return len(self._items)

    def nth(self, i: int) -> _FakeCriteriaItem:
        return self._items[i]


class _FakePage:
    def __init__(self, *, expand_visible: bool, criteria_items: list[str] | None = None) -> None:
        self._expand = _FakeButtonLocator(expand_visible)
        self._criteria = _FakeCriteriaLocator(
            [_FakeCriteriaItem(t) for t in (criteria_items or [])]
        )

    def locator(self, selector: str) -> Any:
        if "job-insight" in selector or "criteria" in selector or "li" in selector:
            return self._criteria
        if selector.startswith("button") or "show-more" in selector:
            return self._expand
        return _FakeButtonLocator(False)


class _FakeHuman:
    def __init__(self) -> None:
        self.clicked = 0

    async def human_click(self, _locator: Any) -> None:
        self.clicked += 1

    async def random_delay(self, *_args: Any, **_kwargs: Any) -> None:
        pass


@pytest.mark.asyncio
async def test_wait_for_job_content_true_when_any_selector_present() -> None:
    scraper = _FakeScraper(selectors_present={".jobs-unified-top-card"})
    ok = await wait_for_job_content(
        cast(BaseScraper, scraper), cast(Page, _FakePage(expand_visible=False))
    )
    assert ok is True


@pytest.mark.asyncio
async def test_extract_basic_fields_from_first_matching_selector() -> None:
    scraper = _FakeScraper(
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
    page = cast(Page, _FakePage(expand_visible=False))

    typed_scraper = cast(BaseScraper, scraper)
    assert await extract_title(typed_scraper, page) == "Title"
    assert await extract_company(typed_scraper, page) == "Company"
    assert await extract_location(typed_scraper, page) == "Location"
    assert await extract_workplace_type(typed_scraper, page) == "Remote"
    assert await extract_posted_date(typed_scraper, page) == "1 day ago"
    assert await extract_applicant_count(typed_scraper, page) == "10 applicants"
    assert await extract_salary(typed_scraper, page) == "$100k"


@pytest.mark.asyncio
async def test_extract_job_criteria_parses_common_fields() -> None:
    page = cast(
        Page,
        _FakePage(
            expand_visible=False,
            criteria_items=[
                "Full-time",
                "Mid-Senior level",
                "Industry: Software Development",
                "Job function: Engineering",
            ],
        ),
    )
    criteria = await extract_job_criteria(page)
    assert criteria["employment_type"] == "Full-time"
    assert criteria["seniority_level"] == "Mid-Senior level"
    assert criteria["industry"] == "Software Development"
    assert criteria["job_function"] == "Engineering"


@pytest.mark.asyncio
async def test_extract_description_expands_and_returns_long_text() -> None:
    long_desc = "x" * 80
    scraper = _FakeScraper(text_by_selector={".jobs-description__content": long_desc})
    page = cast(Page, _FakePage(expand_visible=True))
    human_fake = _FakeHuman()
    human = cast(HumanBehavior, human_fake)

    desc = await extract_description(cast(BaseScraper, scraper), page, human)
    assert desc == long_desc
    assert human_fake.clicked == 1


@pytest.mark.asyncio
async def test_extract_skills_dedupes_preserving_order() -> None:
    scraper = _FakeScraper(
        all_text_by_selector={
            ".job-details-skill-match-status-list__skill": ["Python", "SQL", "Python"],
            ".skill-match-modal__skill": ["SQL", "Linux"],
        }
    )
    skills = await extract_skills(
        cast(BaseScraper, scraper), cast(Page, _FakePage(expand_visible=False))
    )
    assert skills == ["Python", "SQL", "Linux"]


@pytest.mark.asyncio
async def test_extract_raw_sections_truncates_long_text() -> None:
    scraper = _FakeScraper(
        text_by_selector={
            ".jobs-unified-top-card": "a" * 2000,
            ".jobs-description": "b" * 10,
        }
    )
    sections = await extract_raw_sections(
        cast(BaseScraper, scraper), cast(Page, _FakePage(expand_visible=False))
    )
    assert sections["top_card"] == "a" * 1000
    assert sections["description"] == "b" * 10
