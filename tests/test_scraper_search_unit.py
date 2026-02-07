"""Unit tests for JobSearchScraper using fake Playwright objects."""

from __future__ import annotations

from typing import Any, cast

import pytest
from playwright.async_api import Page

from ljs.browser.context import BrowserManager
from ljs.browser.human import HumanBehavior
from ljs.models.job import JobSearchResult
from ljs.scrapers.search import JobSearchScraper
from ljs.storage.jobs import JobStorage
from tests.test_fakes import (
    FakeBrowserManager,
    FakeElement,
    FakeHuman,
    FakeLocator,
    FakePage,
    settings_for_tests,
)


def test_job_search_build_search_url_unknown_country_logs_warning(tmp_path, caplog) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = JobSearchScraper(settings=settings, storage=JobStorage(settings))

    url = scraper._build_search_url("python dev", "unknownland")
    assert "keywords=python%20dev" in url
    assert "geoId=" in url  # empty geo ID

    assert any("Unknown country" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_job_search_run_extracts_and_saves_ids(tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    storage = JobStorage(settings)
    scraper = JobSearchScraper(settings=settings, storage=storage)

    html = '<div data-job-id="111">a</div><div data-job-id="222">b</div>'
    page = FakePage(html=html, links=["/jobs/view/222/", "/jobs/view/333/"])
    scraper._browser_manager = cast(BrowserManager, FakeBrowserManager(page, FakeHuman()))

    result = await scraper.run(keyword="python", country="germany", max_pages=1)
    assert result.total_found == 3
    assert result.job_ids == ["111", "222", "333"]

    saved_ids = await storage.get_job_ids()
    assert {j.job_id for j in saved_ids} >= {"111", "222", "333"}


def test_job_search_build_search_url_known_country_includes_geo_id(tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = JobSearchScraper(settings=settings, storage=JobStorage(settings))
    url = scraper._build_search_url("python", "germany")
    assert "geoId=" in url
    assert "geoId=&" not in url


@pytest.mark.asyncio
async def test_job_search_run_requires_string_keyword_and_country(tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = JobSearchScraper(settings=settings, storage=JobStorage(settings))
    with pytest.raises(ValueError, match="keyword and country"):
        # Exercise runtime validation while keeping static typing satisfied.
        bad_keyword = cast(str, 1)
        await scraper.run(keyword=bad_keyword, country="germany", max_pages=1)


@pytest.mark.asyncio
async def test_job_search_run_uses_default_max_pages_when_omitted(monkeypatch, tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    settings.max_pages_per_session = 7
    scraper = JobSearchScraper(settings=settings, storage=JobStorage(settings))
    scraper._browser_manager = cast(BrowserManager, FakeBrowserManager(FakePage(), FakeHuman()))

    async def _safe_goto_ok(*_a: Any, **_k: Any) -> bool:
        return True

    async def _noop(*_a: Any, **_k: Any) -> None:
        pass

    captured: dict[str, int] = {}

    async def _load(_page: Any, _human: Any, max_pages: int) -> int:
        captured["max_pages"] = max_pages
        return 1

    monkeypatch.setattr(scraper, "_safe_goto", _safe_goto_ok)
    monkeypatch.setattr(scraper, "_wait_for_job_listings", _noop)
    monkeypatch.setattr(scraper, "_extract_job_ids_from_page", _noop)
    monkeypatch.setattr(scraper, "_load_all_results", _load)

    out = await scraper.run(keyword="python", country="germany")
    assert out.pages_scraped == 1
    assert captured["max_pages"] == 7


@pytest.mark.asyncio
async def test_job_search_run_returns_result_when_safe_goto_fails(monkeypatch, tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = JobSearchScraper(settings=settings, storage=JobStorage(settings))
    scraper._browser_manager = cast(BrowserManager, FakeBrowserManager(FakePage(), FakeHuman()))

    async def _safe_goto_fail(*_args: Any, **_kwargs: Any) -> bool:
        return False

    monkeypatch.setattr(scraper, "_safe_goto", _safe_goto_fail)
    result = await scraper.run(keyword="python", country="germany", max_pages=1)
    assert result.total_found == 0
    assert result.job_ids == []


@pytest.mark.asyncio
async def test_job_search_wait_for_listings_success_and_failure(monkeypatch, tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = JobSearchScraper(settings=settings, storage=JobStorage(settings))

    class _Human:
        def __init__(self) -> None:
            self.read_calls = 0

        async def simulate_reading(self, *_a: Any, **_k: Any) -> None:
            self.read_calls += 1

    human = _Human()

    async def _wait_ok(_page: Any, selector: str, *, timeout_ms: int | None = None) -> bool:
        _ = timeout_ms
        return selector == ".jobs-search__results-list"

    monkeypatch.setattr(scraper, "_wait_for_element", _wait_ok)
    ok = await scraper._wait_for_job_listings(cast(Page, FakePage()), cast(HumanBehavior, human))
    assert ok is True
    assert human.read_calls == 1

    shots: list[str] = []

    async def _shot(_page: Any, name: str) -> None:
        shots.append(name)

    async def _wait_nope(_page: Any, _selector: str, *, timeout_ms: int | None = None) -> bool:
        _ = timeout_ms
        return False

    monkeypatch.setattr(scraper, "_wait_for_element", _wait_nope)
    monkeypatch.setattr(scraper, "_take_debug_screenshot", _shot)
    ok2 = await scraper._wait_for_job_listings(cast(Page, FakePage()), cast(HumanBehavior, human))
    assert ok2 is False
    assert shots == ["no_job_listings"]


@pytest.mark.asyncio
async def test_job_search_extract_job_ids_from_page_handles_link_extraction_error(tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = JobSearchScraper(settings=settings, storage=JobStorage(settings))
    scraper._current_result = JobSearchResult(keyword="k", country="c")

    html = '<div data-job-id="111">a</div><div data-job-id="222">b</div>'

    class _BadLinks:
        async def all(self) -> list[Any]:
            raise RuntimeError("boom")

    class _Page(FakePage):
        def __init__(self) -> None:
            super().__init__(html=html)

        def locator(self, selector: str) -> Any:
            if selector == 'a[href*="/jobs/view/"]':
                return _BadLinks()
            return super().locator(selector)

    await scraper._extract_job_ids_from_page(cast(Page, _Page()), "k", "c")
    assert scraper._current_result.job_ids == ["111", "222"]


@pytest.mark.asyncio
async def test_job_search_extract_job_ids_from_page_covers_missing_and_invalid_hrefs(
    tmp_path,
) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = JobSearchScraper(settings=settings, storage=JobStorage(settings))
    scraper._current_result = JobSearchResult(keyword="k", country="c")

    html = '<div data-job-id="111">a</div>'

    class _Page(FakePage):
        def __init__(self) -> None:
            super().__init__(html=html)

        def locator(self, selector: str) -> FakeLocator:
            if selector == 'a[href*="/jobs/view/"]':
                return FakeLocator(
                    [
                        FakeElement(href=None),
                        FakeElement(href="/jobs/view/not-a-number/"),
                        FakeElement(href="/jobs/view/222/"),
                    ]
                )
            return super().locator(selector)

    await scraper._extract_job_ids_from_page(cast(Page, _Page()), "k", "c")
    assert scraper._current_result.job_ids == ["111", "222"]
