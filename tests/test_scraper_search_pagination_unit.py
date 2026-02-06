"""Unit tests for JobSearchScraper pagination/loading logic."""

from __future__ import annotations

from typing import Any, cast

import pytest
from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

from linkedin_scraper.browser.human import HumanBehavior
from linkedin_scraper.models.job import JobSearchResult
from linkedin_scraper.scrapers.search import JobSearchScraper
from linkedin_scraper.storage.jobs import JobStorage
from tests.test_fakes import FakeHuman, FakePage, settings_for_tests


@pytest.mark.asyncio
async def test_job_search_load_all_results_reaches_max_failures(monkeypatch, tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = JobSearchScraper(settings=settings, storage=JobStorage(settings))
    scraper._current_result = JobSearchResult(keyword="k", country="c")

    class _TimeoutButton:
        @property
        def first(self) -> _TimeoutButton:
            return self

        async def count(self) -> int:
            raise PlaywrightTimeout("boom")

    class _Page(FakePage):
        def locator(self, selector: str) -> Any:
            if selector.startswith("button") or "show-more" in selector:
                return _TimeoutButton()
            return super().locator(selector)

    async def _noop_extract(*_args: Any, **_kwargs: Any) -> None:
        pass

    monkeypatch.setattr(scraper, "_extract_job_ids_from_page", _noop_extract)
    pages_loaded = await scraper._load_all_results(
        cast(Page, _Page()), cast(HumanBehavior, FakeHuman()), max_pages=10
    )
    assert pages_loaded == 1


@pytest.mark.asyncio
async def test_job_search_load_all_results_handles_generic_click_errors(
    monkeypatch, tmp_path
) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = JobSearchScraper(settings=settings, storage=JobStorage(settings))
    scraper._current_result = JobSearchResult(keyword="k", country="c")

    class _ExplodingButton:
        @property
        def first(self) -> _ExplodingButton:
            return self

        async def count(self) -> int:
            return 1

        async def is_visible(self) -> bool:
            raise RuntimeError("boom")

    class _Page(FakePage):
        def locator(self, selector: str) -> Any:
            if selector.startswith("button") or "show-more" in selector:
                return _ExplodingButton()
            return super().locator(selector)

    async def _noop_extract(*_a: Any, **_k: Any) -> None:
        pass

    monkeypatch.setattr(scraper, "_extract_job_ids_from_page", _noop_extract)
    pages_loaded = await scraper._load_all_results(
        cast(Page, _Page()), cast(HumanBehavior, FakeHuman()), max_pages=2
    )
    assert pages_loaded == 1


@pytest.mark.asyncio
async def test_job_search_load_all_results_increments_when_new_content_loaded(
    monkeypatch, tmp_path
) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = JobSearchScraper(settings=settings, storage=JobStorage(settings))
    scraper._current_result = JobSearchResult(keyword="k", country="c")

    async def _extract(_page: Any, _k: str, _c: str) -> None:
        assert scraper._current_result is not None
        if scraper._current_result.total_found == 0:
            scraper._current_result.job_ids.append("1")
            scraper._current_result.total_found = 1

    monkeypatch.setattr(scraper, "_extract_job_ids_from_page", _extract)
    pages_loaded = await scraper._load_all_results(
        cast(Page, FakePage()), cast(HumanBehavior, FakeHuman()), max_pages=2
    )
    assert pages_loaded == 2


@pytest.mark.asyncio
async def test_job_search_load_all_results_clicks_show_more_once(monkeypatch, tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = JobSearchScraper(settings=settings, storage=JobStorage(settings))
    scraper._current_result = JobSearchResult(keyword="k", country="c")

    class _ButtonLocator:
        @property
        def first(self) -> _ButtonLocator:
            return self

        async def count(self) -> int:
            return 1

        async def is_visible(self) -> bool:
            return True

        async def scroll_into_view_if_needed(self) -> None:
            pass

    class _PageWithButton(FakePage):
        def locator(self, selector: str) -> Any:
            if selector.startswith("button") or "show-more" in selector:
                return _ButtonLocator()
            return super().locator(selector)

    async def _noop_extract(*_args: Any, **_kwargs: Any) -> None:
        pass

    monkeypatch.setattr(scraper, "_extract_job_ids_from_page", _noop_extract)

    page = _PageWithButton()
    human = FakeHuman()
    pages_loaded = await scraper._load_all_results(
        cast(Page, page), cast(HumanBehavior, human), max_pages=2
    )
    assert pages_loaded == 2
