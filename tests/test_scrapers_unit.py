"""Unit tests for scrapers using fake Playwright objects.

These tests focus on core control-flow and parsing logic without requiring a real browser.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pytest
from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

import linkedin_scraper.scrapers.base as base_module
from linkedin_scraper.browser.human import HumanBehavior
from linkedin_scraper.config import Settings
from linkedin_scraper.models.job import JobDetail, JobId, JobIdSource, JobSearchResult
from linkedin_scraper.scrapers.base import BaseScraper
from linkedin_scraper.scrapers.detail import JobDetailScraper
from linkedin_scraper.scrapers.recommended import RecommendedJobsScraper
from linkedin_scraper.scrapers.search import JobSearchScraper
from linkedin_scraper.storage.jobs import JobStorage


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        headless=True,
        slow_mo=0,
        browser_type="chromium",
        disable_browser_sandbox=False,
        min_delay_ms=100,
        max_delay_ms=500,
        typing_delay_ms=20,
        mouse_movement_steps=5,
        min_request_interval_sec=0,
        max_requests_per_hour=0,
    )


@dataclass
class _FakeResponse:
    status: int = 200


class _FakeElement:
    def __init__(self, *, text: str = "", href: str | None = None, visible: bool = True) -> None:
        self._text = text
        self._href = href
        self._visible = visible
        self.clicked = False

    async def inner_text(self) -> str:
        return self._text

    async def get_attribute(self, name: str) -> str | None:
        if name == "href":
            return self._href
        return None

    async def is_visible(self) -> bool:
        return self._visible

    async def scroll_into_view_if_needed(self) -> None:
        pass


class _FakeLocator:
    def __init__(self, elements: list[_FakeElement]) -> None:
        self._elements = elements

    @property
    def first(self) -> _FakeLocator:
        return _FakeLocator(self._elements[:1])

    async def count(self) -> int:
        return len(self._elements)

    def nth(self, i: int) -> _FakeLocator:
        return _FakeLocator([self._elements[i]])

    async def inner_text(self) -> str:
        return (await self._elements[0].inner_text()) if self._elements else ""

    async def get_attribute(self, name: str) -> str | None:
        return (await self._elements[0].get_attribute(name)) if self._elements else None

    async def all(self) -> list[_FakeElement]:
        return list(self._elements)


class _FakePage:
    def __init__(self, *, html: str = "", links: list[str] | None = None) -> None:
        self._html = html
        self._links = links or []
        self.goto_urls: list[str] = []
        self.screenshots: list[str] = []
        self.url = "about:blank"

    async def goto(self, url: str, *, wait_until: str | None = None) -> _FakeResponse:
        self.url = url
        self.goto_urls.append(url)
        _ = wait_until
        return _FakeResponse(status=200)

    async def content(self) -> str:
        return self._html

    async def wait_for_selector(self, _selector: str, *, timeout: int | None = None) -> None:
        _ = timeout
        # Default: selector is present immediately in these unit tests.

    def locator(self, selector: str) -> _FakeLocator:
        if selector == 'a[href*="/jobs/view/"]':
            elements = [_FakeElement(href=href) for href in self._links]
            return _FakeLocator(elements)
        return _FakeLocator([])

    async def screenshot(self, *, path: str, full_page: bool | None = None) -> None:
        _ = full_page
        self.screenshots.append(path)


class _FakeHuman:
    async def random_delay(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    async def simulate_reading(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    async def human_scroll(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    async def scroll_to_bottom(self, *_args: Any, **_kwargs: Any) -> bool:
        return True

    async def human_click(self, *_args: Any, **_kwargs: Any) -> None:
        pass


class _FakeBrowserManager:
    def __init__(self, page: _FakePage, human: _FakeHuman) -> None:
        self._page = page
        self._human = human

    @asynccontextmanager
    async def new_page(self, *_args: Any, **_kwargs: Any):
        yield self._page, self._human


class _DummyScraper(BaseScraper):
    async def run(self, **_kwargs: Any) -> None:
        pass


@pytest.mark.asyncio
async def test_safe_goto_success_and_http_error(tmp_path) -> None:
    settings = _settings(tmp_path)
    storage = JobStorage(settings)
    scraper = _DummyScraper(settings=settings, storage=storage)

    page = _FakePage()
    human = _FakeHuman()
    ok = await scraper._safe_goto(
        cast(Page, page), "https://example.com", cast(HumanBehavior, human)
    )
    assert ok is True

    class _BadPage(_FakePage):
        async def goto(self, url: str, *, wait_until: str | None = None) -> _FakeResponse:
            await super().goto(url, wait_until=wait_until)
            return _FakeResponse(status=500)

    bad_page = _BadPage()
    bad = await scraper._safe_goto(
        cast(Page, bad_page), "https://example.com/bad", cast(HumanBehavior, human)
    )
    assert bad is False


@pytest.mark.asyncio
async def test_wait_for_element_handles_timeout(tmp_path) -> None:
    settings = _settings(tmp_path)
    storage = JobStorage(settings)
    scraper = _DummyScraper(settings=settings, storage=storage)

    class _TimeoutPage(_FakePage):
        async def wait_for_selector(self, _selector: str, *, timeout: int | None = None) -> None:
            _ = timeout
            raise PlaywrightTimeout("boom")

    timeout_page = _TimeoutPage()
    ok = await scraper._wait_for_element(cast(Page, timeout_page), "div", timeout_ms=1)
    assert ok is False


@pytest.mark.asyncio
async def test_extract_text_and_all_text_strip_and_collect(tmp_path) -> None:
    settings = _settings(tmp_path)
    scraper = _DummyScraper(settings=settings, storage=JobStorage(settings))

    class _TextPage(_FakePage):
        def locator(self, selector: str) -> _FakeLocator:
            _ = selector
            return _FakeLocator([_FakeElement(text="  hello  "), _FakeElement(text="world")])

    page = _TextPage()
    assert await scraper._extract_text(cast(Page, page), "any") == "hello"
    assert await scraper._extract_all_text(cast(Page, page), "any") == ["hello", "world"]


@pytest.mark.asyncio
async def test_check_rate_limit_respects_min_interval(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    settings.min_request_interval_sec = 1.0

    scraper = _DummyScraper(settings=settings, storage=JobStorage(settings))
    scraper._last_request_time_mono = 0.0

    slept: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(base_module.time, "monotonic", lambda: 0.5)

    await scraper._check_rate_limit()
    assert slept == [0.5]


@pytest.mark.asyncio
async def test_take_debug_screenshot_records_path(tmp_path) -> None:
    settings = _settings(tmp_path)
    scraper = _DummyScraper(settings=settings, storage=JobStorage(settings))

    page = _FakePage()
    await scraper._take_debug_screenshot(cast(Page, page), "x")
    assert page.screenshots
    assert page.screenshots[0].endswith(".png")


def test_job_search_build_search_url_unknown_country_logs_warning(tmp_path, caplog) -> None:
    settings = _settings(tmp_path)
    scraper = JobSearchScraper(settings=settings, storage=JobStorage(settings))

    url = scraper._build_search_url("python dev", "unknownland")
    assert "keywords=python%20dev" in url
    assert "geoId=" in url  # empty geo ID

    assert any("Unknown country" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_job_search_run_extracts_and_saves_ids(tmp_path) -> None:
    settings = _settings(tmp_path)
    storage = JobStorage(settings)
    scraper = JobSearchScraper(settings=settings, storage=storage)

    html = '<div data-job-id="111">a</div><div data-job-id="222">b</div>'
    page = _FakePage(html=html, links=["/jobs/view/222/", "/jobs/view/333/"])
    scraper._browser_manager = _FakeBrowserManager(page, _FakeHuman())

    result = await scraper.run(keyword="python", country="germany", max_pages=1)
    assert result.total_found == 3
    assert result.job_ids == ["111", "222", "333"]

    saved_ids = await storage.get_job_ids()
    assert {j.job_id for j in saved_ids} >= {"111", "222", "333"}


@pytest.mark.asyncio
async def test_job_search_load_all_results_clicks_show_more_once(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
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

    class _PageWithButton(_FakePage):
        def locator(self, selector: str) -> Any:
            if selector.startswith("button") or "show-more" in selector:
                return _ButtonLocator()
            return super().locator(selector)

    async def _noop_extract(*_args: Any, **_kwargs: Any) -> None:
        pass

    monkeypatch.setattr(scraper, "_extract_job_ids_from_page", _noop_extract)

    page = _PageWithButton()
    human = _FakeHuman()
    pages_loaded = await scraper._load_all_results(
        cast(Page, page), cast(HumanBehavior, human), max_pages=2
    )
    assert pages_loaded == 2


@pytest.mark.asyncio
async def test_recommended_extract_from_page_discards_parent_and_sorts(tmp_path) -> None:
    settings = _settings(tmp_path)
    storage = JobStorage(settings)
    scraper = RecommendedJobsScraper(settings=settings, storage=storage)

    async def _fixed(_page: Any) -> set[str]:
        return {"200", "100", "123"}  # includes parent ID

    scraper._extract_similar_jobs = _fixed  # type: ignore[method-assign]
    scraper._extract_people_also_viewed = _fixed  # type: ignore[method-assign]
    scraper._extract_more_jobs_at_company = _fixed  # type: ignore[method-assign]
    scraper._extract_from_sidebar = _fixed  # type: ignore[method-assign]

    page = _FakePage()
    human = _FakeHuman()
    ids = await scraper.extract_from_page(
        cast(Page, page), cast(HumanBehavior, human), parent_job_id="123"
    )
    assert ids == ["100", "200"]

    saved = await storage.get_job_ids()
    assert any(j.source.value == "recommended" for j in saved)


@pytest.mark.asyncio
async def test_recommended_extract_job_ids_from_selector(tmp_path) -> None:
    settings = _settings(tmp_path)
    scraper = RecommendedJobsScraper(settings=settings, storage=JobStorage(settings))

    class _Page(_FakePage):
        def locator(self, selector: str) -> _FakeLocator:
            _ = selector
            return _FakeLocator(
                [
                    _FakeElement(href="/jobs/view/1/"),
                    _FakeElement(href="/jobs/view/2/"),
                    _FakeElement(href="/jobs/view/2/"),
                ]
            )

    page = _Page()
    ids = await scraper._extract_job_ids_from_selector(cast(Page, page), "any")
    assert ids == {"1", "2"}


@pytest.mark.asyncio
async def test_recommended_run_uses_scraped_search_ids_and_dedupes(tmp_path) -> None:
    settings = _settings(tmp_path)
    storage = JobStorage(settings)
    await storage.save_job_ids(
        [
            JobId(job_id="111", source=JobIdSource.SEARCH, scraped=True),
            JobId(job_id="222", source=JobIdSource.SEARCH, scraped=True),
            JobId(job_id="333", source=JobIdSource.SEARCH, scraped=False),
        ]
    )

    scraper = RecommendedJobsScraper(settings=settings, storage=storage)
    page = _FakePage()
    scraper._browser_manager = _FakeBrowserManager(page, _FakeHuman())

    async def _fake_extract_from_page(_page: Any, _human: Any, _parent_job_id: str) -> list[str]:
        return ["200", "100", "100"]

    scraper.extract_from_page = _fake_extract_from_page  # type: ignore[method-assign]

    out = await scraper.run(limit=1)
    assert out == ["200", "100"]
    assert len(page.goto_urls) == 1
    assert page.goto_urls[0].startswith("https://www.linkedin.com/jobs/view/")


@pytest.mark.asyncio
async def test_job_detail_run_respects_limit_and_saves_detail(tmp_path) -> None:
    settings = _settings(tmp_path)
    storage = JobStorage(settings)
    scraper = JobDetailScraper(settings=settings, storage=storage)

    page = _FakePage()
    scraper._browser_manager = _FakeBrowserManager(page, _FakeHuman())

    async def _fake_scrape_job_detail(_page: Any, _human: Any, job_id: str) -> JobDetail:
        return JobDetail(job_id=job_id, title="t", company_name="c", location="l")

    async def _fake_recommended(*_args: Any, **_kwargs: Any) -> list[str]:
        return ["999"]

    scraper._scrape_job_detail = _fake_scrape_job_detail  # type: ignore[method-assign]
    scraper._recommended_scraper.extract_from_page = _fake_recommended  # type: ignore[method-assign]

    details = await scraper.run(job_ids=["101", "202"], limit=1, extract_recommended=True)
    assert [d.job_id for d in details] == ["101"]

    assert (settings.job_details_dir / "101.json").exists()


@pytest.mark.asyncio
async def test_invalid_limits_raise(tmp_path) -> None:
    settings = _settings(tmp_path)

    search = JobSearchScraper(settings=settings, storage=JobStorage(settings))
    with pytest.raises(ValueError):
        await search.run(keyword="x", country="germany", max_pages=0)

    detail = JobDetailScraper(settings=settings, storage=JobStorage(settings))
    with pytest.raises(ValueError):
        await detail.run(job_ids=["1"], limit=0)

    recommended = RecommendedJobsScraper(settings=settings, storage=JobStorage(settings))
    with pytest.raises(ValueError):
        await recommended.run(parent_job_ids=["1"], limit=0)
