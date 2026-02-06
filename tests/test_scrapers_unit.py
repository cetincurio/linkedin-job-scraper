"""Unit tests for scrapers using fake Playwright objects.

These tests focus on core control-flow and parsing logic without requiring a real browser.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pytest
from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

import linkedin_scraper.scrapers.base as base_module
from linkedin_scraper.browser.context import BrowserManager
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
            return _FakeLocator(
                [
                    _FakeElement(text="  hello  "),
                    _FakeElement(text=""),
                    _FakeElement(text="world"),
                ]
            )

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
async def test_check_rate_limit_does_not_sleep_when_elapsed_exceeds_min_interval(
    monkeypatch, tmp_path
) -> None:
    settings = _settings(tmp_path)
    settings.min_request_interval_sec = 1.0
    settings.max_requests_per_hour = 0

    scraper = _DummyScraper(settings=settings, storage=JobStorage(settings))
    scraper._last_request_time_mono = 0.0

    slept: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(base_module.time, "monotonic", lambda: 2.0)

    await scraper._check_rate_limit()
    assert slept == []


@pytest.mark.asyncio
async def test_check_rate_limit_hourly_limit_can_wait(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    settings.max_requests_per_hour = 1
    settings.min_request_interval_sec = 0

    scraper = _DummyScraper(settings=settings, storage=JobStorage(settings))
    scraper._request_count = 100
    scraper._session_start = datetime(2026, 2, 6, 12, 0, 0)

    slept: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    class _DT:
        @staticmethod
        def now() -> datetime:
            return datetime(2026, 2, 6, 12, 0, 0)

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(base_module, "datetime", _DT)
    monkeypatch.setattr(base_module.time, "monotonic", lambda: 123.0)

    await scraper._check_rate_limit()
    assert slept and slept[0] > 0
    assert scraper._last_request_time_mono == 123.0


@pytest.mark.asyncio
async def test_check_rate_limit_sets_session_start_and_skips_wait_when_under_limit(
    monkeypatch, tmp_path
) -> None:
    settings = _settings(tmp_path)
    settings.max_requests_per_hour = 10_000
    settings.min_request_interval_sec = 1.0

    scraper = _DummyScraper(settings=settings, storage=JobStorage(settings))
    # No prior request timestamp: the min-interval branch should be skipped.
    scraper._last_request_time_mono = None

    slept: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    class _DT:
        @staticmethod
        def now() -> datetime:
            return datetime(2026, 2, 6, 12, 0, 0)

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(base_module, "datetime", _DT)
    monkeypatch.setattr(base_module.time, "monotonic", lambda: 5.0)

    await scraper._check_rate_limit()
    assert scraper._session_start == datetime(2026, 2, 6, 12, 0, 0)
    assert scraper._request_count == 1
    assert slept == []


@pytest.mark.asyncio
async def test_safe_goto_handles_timeout_and_exception(tmp_path) -> None:
    settings = _settings(tmp_path)
    scraper = _DummyScraper(settings=settings, storage=JobStorage(settings))
    human = _FakeHuman()

    class _TimeoutPage(_FakePage):
        async def goto(self, url: str, *, wait_until: str | None = None) -> _FakeResponse:
            _ = url, wait_until
            raise PlaywrightTimeout("boom")

    ok = await scraper._safe_goto(
        cast(Page, _TimeoutPage()), "https://example.com", cast(HumanBehavior, human)
    )
    assert ok is False

    class _ErrPage(_FakePage):
        async def goto(self, url: str, *, wait_until: str | None = None) -> _FakeResponse:
            _ = url, wait_until
            raise RuntimeError("boom")

    ok2 = await scraper._safe_goto(
        cast(Page, _ErrPage()), "https://example.com", cast(HumanBehavior, human)
    )
    assert ok2 is False


@pytest.mark.asyncio
async def test_extract_text_and_all_text_return_defaults_on_errors(tmp_path) -> None:
    settings = _settings(tmp_path)
    scraper = _DummyScraper(settings=settings, storage=JobStorage(settings))

    class _EmptyPage(_FakePage):
        # Keep arg name `selector` for keyword-arg compatibility with _FakePage.locator().
        def locator(self, selector: str) -> _FakeLocator:
            _ = selector
            return _FakeLocator([])

    assert await scraper._extract_text(cast(Page, _EmptyPage()), "x", default="d") == "d"

    class _ExplodingElement(_FakeElement):
        async def inner_text(self) -> str:
            raise RuntimeError("boom")

    class _ExplodingTextPage(_FakePage):
        def locator(self, selector: str) -> _FakeLocator:
            _ = selector
            return _FakeLocator([_ExplodingElement(text="x")])

    assert await scraper._extract_text(cast(Page, _ExplodingTextPage()), "x", default="d") == "d"

    class _ExplodingLocatorPage(_FakePage):
        def locator(self, selector: str) -> _FakeLocator:
            _ = selector
            raise RuntimeError("boom")

    assert await scraper._extract_all_text(cast(Page, _ExplodingLocatorPage()), "x") == []


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
    scraper._browser_manager = cast(BrowserManager, _FakeBrowserManager(page, _FakeHuman()))

    result = await scraper.run(keyword="python", country="germany", max_pages=1)
    assert result.total_found == 3
    assert result.job_ids == ["111", "222", "333"]

    saved_ids = await storage.get_job_ids()
    assert {j.job_id for j in saved_ids} >= {"111", "222", "333"}


def test_job_search_build_search_url_known_country_includes_geo_id(tmp_path) -> None:
    settings = _settings(tmp_path)
    scraper = JobSearchScraper(settings=settings, storage=JobStorage(settings))
    url = scraper._build_search_url("python", "germany")
    assert "geoId=" in url
    assert "geoId=&" not in url


@pytest.mark.asyncio
async def test_job_search_run_requires_string_keyword_and_country(tmp_path) -> None:
    settings = _settings(tmp_path)
    scraper = JobSearchScraper(settings=settings, storage=JobStorage(settings))
    with pytest.raises(ValueError, match="keyword and country"):
        await scraper.run(keyword=1, country="germany", max_pages=1)


@pytest.mark.asyncio
async def test_job_search_run_uses_default_max_pages_when_omitted(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    settings.max_pages_per_session = 7
    scraper = JobSearchScraper(settings=settings, storage=JobStorage(settings))
    scraper._browser_manager = cast(BrowserManager, _FakeBrowserManager(_FakePage(), _FakeHuman()))

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
    settings = _settings(tmp_path)
    scraper = JobSearchScraper(settings=settings, storage=JobStorage(settings))
    scraper._browser_manager = cast(BrowserManager, _FakeBrowserManager(_FakePage(), _FakeHuman()))

    async def _safe_goto_fail(*_args: Any, **_kwargs: Any) -> bool:
        return False

    monkeypatch.setattr(scraper, "_safe_goto", _safe_goto_fail)
    result = await scraper.run(keyword="python", country="germany", max_pages=1)
    assert result.total_found == 0
    assert result.job_ids == []


@pytest.mark.asyncio
async def test_job_search_wait_for_listings_success_and_failure(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
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
    ok = await scraper._wait_for_job_listings(cast(Page, _FakePage()), cast(HumanBehavior, human))
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
    ok2 = await scraper._wait_for_job_listings(cast(Page, _FakePage()), cast(HumanBehavior, human))
    assert ok2 is False
    assert shots == ["no_job_listings"]


@pytest.mark.asyncio
async def test_job_search_extract_job_ids_from_page_handles_link_extraction_error(tmp_path) -> None:
    settings = _settings(tmp_path)
    scraper = JobSearchScraper(settings=settings, storage=JobStorage(settings))
    scraper._current_result = JobSearchResult(keyword="k", country="c")

    html = '<div data-job-id="111">a</div><div data-job-id="222">b</div>'

    class _BadLinks:
        async def all(self) -> list[Any]:
            raise RuntimeError("boom")

    class _Page(_FakePage):
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
    settings = _settings(tmp_path)
    scraper = JobSearchScraper(settings=settings, storage=JobStorage(settings))
    scraper._current_result = JobSearchResult(keyword="k", country="c")

    html = '<div data-job-id="111">a</div>'

    class _Page(_FakePage):
        def __init__(self) -> None:
            super().__init__(html=html)

        def locator(self, selector: str) -> _FakeLocator:
            if selector == 'a[href*="/jobs/view/"]':
                return _FakeLocator(
                    [
                        _FakeElement(href=None),
                        _FakeElement(href="/jobs/view/not-a-number/"),
                        _FakeElement(href="/jobs/view/222/"),
                    ]
                )
            return super().locator(selector)

    await scraper._extract_job_ids_from_page(cast(Page, _Page()), "k", "c")
    assert scraper._current_result.job_ids == ["111", "222"]


@pytest.mark.asyncio
async def test_job_search_load_all_results_reaches_max_failures(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    scraper = JobSearchScraper(settings=settings, storage=JobStorage(settings))
    scraper._current_result = JobSearchResult(keyword="k", country="c")

    class _TimeoutButton:
        @property
        def first(self) -> _TimeoutButton:
            return self

        async def count(self) -> int:
            raise PlaywrightTimeout("boom")

    class _Page(_FakePage):
        def locator(self, selector: str) -> Any:
            if selector.startswith("button") or "show-more" in selector:
                return _TimeoutButton()
            return super().locator(selector)

    async def _noop_extract(*_args: Any, **_kwargs: Any) -> None:
        pass

    monkeypatch.setattr(scraper, "_extract_job_ids_from_page", _noop_extract)
    pages_loaded = await scraper._load_all_results(
        cast(Page, _Page()), cast(HumanBehavior, _FakeHuman()), max_pages=10
    )
    assert pages_loaded == 1


@pytest.mark.asyncio
async def test_job_search_load_all_results_handles_generic_click_errors(
    monkeypatch, tmp_path
) -> None:
    settings = _settings(tmp_path)
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

    class _Page(_FakePage):
        def locator(self, selector: str) -> Any:
            if selector.startswith("button") or "show-more" in selector:
                return _ExplodingButton()
            return super().locator(selector)

    async def _noop_extract(*_a: Any, **_k: Any) -> None:
        pass

    monkeypatch.setattr(scraper, "_extract_job_ids_from_page", _noop_extract)
    pages_loaded = await scraper._load_all_results(
        cast(Page, _Page()), cast(HumanBehavior, _FakeHuman()), max_pages=2
    )
    assert pages_loaded == 1


@pytest.mark.asyncio
async def test_job_search_load_all_results_increments_when_new_content_loaded(
    monkeypatch, tmp_path
) -> None:
    settings = _settings(tmp_path)
    scraper = JobSearchScraper(settings=settings, storage=JobStorage(settings))
    scraper._current_result = JobSearchResult(keyword="k", country="c")

    async def _extract(_page: Any, _k: str, _c: str) -> None:
        assert scraper._current_result is not None
        if scraper._current_result.total_found == 0:
            scraper._current_result.job_ids.append("1")
            scraper._current_result.total_found = 1

    monkeypatch.setattr(scraper, "_extract_job_ids_from_page", _extract)
    pages_loaded = await scraper._load_all_results(
        cast(Page, _FakePage()), cast(HumanBehavior, _FakeHuman()), max_pages=2
    )
    assert pages_loaded == 2


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
async def test_recommended_extract_from_page_discards_parent_and_sorts(
    monkeypatch, tmp_path
) -> None:
    settings = _settings(tmp_path)
    storage = JobStorage(settings)
    scraper = RecommendedJobsScraper(settings=settings, storage=storage)

    async def _fixed(_page: Any) -> set[str]:
        return {"200", "100", "123"}  # includes parent ID

    monkeypatch.setattr(scraper, "_extract_similar_jobs", _fixed)
    monkeypatch.setattr(scraper, "_extract_people_also_viewed", _fixed)
    monkeypatch.setattr(scraper, "_extract_more_jobs_at_company", _fixed)
    monkeypatch.setattr(scraper, "_extract_from_sidebar", _fixed)

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
async def test_recommended_extract_job_ids_from_selector_skips_missing_and_invalid_hrefs(
    tmp_path,
) -> None:
    settings = _settings(tmp_path)
    scraper = RecommendedJobsScraper(settings=settings, storage=JobStorage(settings))

    class _Page(_FakePage):
        def locator(self, selector: str) -> _FakeLocator:
            _ = selector
            return _FakeLocator(
                [
                    _FakeElement(href=None),
                    _FakeElement(href="/jobs/view/not-a-number/"),
                    _FakeElement(href="/jobs/view/42/"),
                ]
            )

    out = await scraper._extract_job_ids_from_selector(cast(Page, _Page()), "x")
    assert out == {"42"}


@pytest.mark.asyncio
async def test_recommended_run_uses_scraped_search_ids_and_dedupes(monkeypatch, tmp_path) -> None:
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
    scraper._browser_manager = cast(BrowserManager, _FakeBrowserManager(page, _FakeHuman()))

    async def _fake_extract_from_page(_page: Any, _human: Any, _parent_job_id: str) -> list[str]:
        return ["200", "100", "100"]

    monkeypatch.setattr(scraper, "extract_from_page", _fake_extract_from_page)

    out = await scraper.run(limit=1)
    assert out == ["200", "100"]
    assert len(page.goto_urls) == 1
    assert page.goto_urls[0].startswith("https://www.linkedin.com/jobs/view/")


@pytest.mark.asyncio
async def test_recommended_run_returns_empty_when_no_scraped_search_ids(tmp_path) -> None:
    settings = _settings(tmp_path)
    storage = JobStorage(settings)
    await storage.save_job_ids([JobId(job_id="111", source=JobIdSource.SEARCH, scraped=False)])

    scraper = RecommendedJobsScraper(settings=settings, storage=storage)
    scraper._browser_manager = cast(BrowserManager, _FakeBrowserManager(_FakePage(), _FakeHuman()))
    out = await scraper.run()
    assert out == []


@pytest.mark.asyncio
async def test_recommended_run_skips_extract_when_safe_goto_fails(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    storage = JobStorage(settings)
    scraper = RecommendedJobsScraper(settings=settings, storage=storage)
    scraper._browser_manager = cast(BrowserManager, _FakeBrowserManager(_FakePage(), _FakeHuman()))

    async def _nope(*_a: Any, **_k: Any) -> bool:
        return False

    called: list[str] = []

    async def _extract(*_a: Any, **_k: Any) -> list[str]:
        called.append("x")
        return []

    monkeypatch.setattr(scraper, "_safe_goto", _nope)
    monkeypatch.setattr(scraper, "extract_from_page", _extract)

    out = await scraper.run(parent_job_ids=["1"], limit=1)
    assert out == []
    assert called == []


@pytest.mark.asyncio
async def test_recommended_section_extractors_call_selector_helper(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    scraper = RecommendedJobsScraper(settings=settings, storage=JobStorage(settings))

    calls: list[str] = []

    async def _helper(_page: Any, selector: str) -> set[str]:
        calls.append(selector)
        return (
            {"1"}
            if selector.startswith(".similar-jobs") or 'data-test="similar-jobs"' in selector
            else set()
        )

    monkeypatch.setattr(scraper, "_extract_job_ids_from_selector", _helper)
    page = cast(Page, _FakePage())

    out1 = await scraper._extract_similar_jobs(page)
    out2 = await scraper._extract_people_also_viewed(page)
    out3 = await scraper._extract_more_jobs_at_company(page)
    out4 = await scraper._extract_from_sidebar(page)

    assert out1 == {"1"}
    assert out2 == set()
    assert out3 == set()
    assert out4 == set()
    assert calls


@pytest.mark.asyncio
async def test_recommended_debug_branches_for_other_sections(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    scraper = RecommendedJobsScraper(settings=settings, storage=JobStorage(settings))

    async def _helper(_page: Any, selector: str) -> set[str]:
        if "also-viewed" in selector:
            return {"1"}
        if "more-jobs" in selector or "company-jobs" in selector or "jobs-company" in selector:
            return {"2"}
        return set()

    monkeypatch.setattr(scraper, "_extract_job_ids_from_selector", _helper)
    page = cast(Page, _FakePage())

    assert await scraper._extract_people_also_viewed(page) == {"1"}
    assert await scraper._extract_more_jobs_at_company(page) == {"2"}


@pytest.mark.asyncio
async def test_recommended_debug_branch_for_sidebar(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    scraper = RecommendedJobsScraper(settings=settings, storage=JobStorage(settings))

    async def _helper(_page: Any, selector: str) -> set[str]:
        return {"9"} if selector.startswith("aside") else set()

    monkeypatch.setattr(scraper, "_extract_job_ids_from_selector", _helper)
    page = cast(Page, _FakePage())
    assert await scraper._extract_from_sidebar(page) == {"9"}


@pytest.mark.asyncio
async def test_recommended_section_extractors_can_return_empty_sets(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    scraper = RecommendedJobsScraper(settings=settings, storage=JobStorage(settings))

    async def _helper(_page: Any, _selector: str) -> set[str]:
        return set()

    monkeypatch.setattr(scraper, "_extract_job_ids_from_selector", _helper)
    page = cast(Page, _FakePage())

    assert await scraper._extract_similar_jobs(page) == set()
    assert await scraper._extract_people_also_viewed(page) == set()
    assert await scraper._extract_more_jobs_at_company(page) == set()
    assert await scraper._extract_from_sidebar(page) == set()


@pytest.mark.asyncio
async def test_recommended_extract_from_page_empty_does_not_save(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    storage = JobStorage(settings)
    scraper = RecommendedJobsScraper(settings=settings, storage=storage)

    async def _none(_page: Any) -> set[str]:
        return set()

    monkeypatch.setattr(scraper, "_extract_similar_jobs", _none)
    monkeypatch.setattr(scraper, "_extract_people_also_viewed", _none)
    monkeypatch.setattr(scraper, "_extract_more_jobs_at_company", _none)
    monkeypatch.setattr(scraper, "_extract_from_sidebar", _none)

    out = await scraper.extract_from_page(
        cast(Page, _FakePage()), cast(HumanBehavior, _FakeHuman()), "1"
    )
    assert out == []
    assert await storage.get_job_ids() == []


@pytest.mark.asyncio
async def test_recommended_extract_job_ids_from_selector_handles_page_errors(tmp_path) -> None:
    settings = _settings(tmp_path)
    scraper = RecommendedJobsScraper(settings=settings, storage=JobStorage(settings))

    class _Page(_FakePage):
        def locator(self, selector: str) -> _FakeLocator:
            _ = selector
            raise RuntimeError("boom")

    ids = await scraper._extract_job_ids_from_selector(cast(Page, _Page()), "x")
    assert ids == set()


@pytest.mark.asyncio
async def test_recommended_extract_all_from_html_parses_ids(tmp_path) -> None:
    settings = _settings(tmp_path)
    scraper = RecommendedJobsScraper(settings=settings, storage=JobStorage(settings))
    page = _FakePage(html='<a href="/jobs/view/123/">x</a><div data-job-id="456"></div>')
    out = await scraper._extract_all_from_html(cast(Page, page))
    assert {"123", "456"} <= out


@pytest.mark.asyncio
async def test_job_detail_run_respects_limit_and_saves_detail(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    storage = JobStorage(settings)
    scraper = JobDetailScraper(settings=settings, storage=storage)

    page = _FakePage()
    scraper._browser_manager = cast(BrowserManager, _FakeBrowserManager(page, _FakeHuman()))

    async def _fake_scrape_job_detail(_page: Any, _human: Any, job_id: str) -> JobDetail:
        return JobDetail(job_id=job_id, title="t", company_name="c", location="l")

    async def _fake_recommended(*_args: Any, **_kwargs: Any) -> list[str]:
        return ["999"]

    monkeypatch.setattr(scraper, "_scrape_job_detail", _fake_scrape_job_detail)
    monkeypatch.setattr(scraper._recommended_scraper, "extract_from_page", _fake_recommended)

    details = await scraper.run(job_ids=["101", "202"], limit=1, extract_recommended=True)
    assert [d.job_id for d in details] == ["101"]

    assert (settings.job_details_dir / "101.json").exists()


@pytest.mark.asyncio
async def test_job_detail_run_extract_recommended_true_with_no_results(
    monkeypatch, tmp_path
) -> None:
    settings = _settings(tmp_path)
    storage = JobStorage(settings)
    scraper = JobDetailScraper(settings=settings, storage=storage)

    page = _FakePage()
    scraper._browser_manager = cast(BrowserManager, _FakeBrowserManager(page, _FakeHuman()))

    async def _fake_scrape_job_detail(_page: Any, _human: Any, job_id: str) -> JobDetail:
        return JobDetail(job_id=job_id, title="t")

    async def _none(*_args: Any, **_kwargs: Any) -> list[str]:
        return []

    monkeypatch.setattr(scraper, "_scrape_job_detail", _fake_scrape_job_detail)
    monkeypatch.setattr(scraper._recommended_scraper, "extract_from_page", _none)

    out = await scraper.run(job_ids=["101"], extract_recommended=True)
    assert [d.job_id for d in out] == ["101"]


@pytest.mark.asyncio
async def test_job_detail_run_loads_unscraped_ids_from_storage(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    storage = JobStorage(settings)
    await storage.save_job_ids(
        [
            JobId(job_id="101", source=JobIdSource.SEARCH, scraped=False),
            JobId(job_id="202", source=JobIdSource.SEARCH, scraped=False),
        ]
    )

    scraper = JobDetailScraper(settings=settings, storage=storage)
    scraper._browser_manager = cast(BrowserManager, _FakeBrowserManager(_FakePage(), _FakeHuman()))

    async def _fake_scrape_job_detail(_page: Any, _human: Any, job_id: str) -> JobDetail:
        return JobDetail(job_id=job_id, title="t")

    monkeypatch.setattr(scraper, "_scrape_job_detail", _fake_scrape_job_detail)
    out = await scraper.run(job_ids=None, limit=1, extract_recommended=False)
    assert [d.job_id for d in out] == ["101"]


@pytest.mark.asyncio
async def test_job_detail_run_continues_when_scrape_returns_none(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    storage = JobStorage(settings)
    scraper = JobDetailScraper(settings=settings, storage=storage)

    class _Human(_FakeHuman):
        def __init__(self) -> None:
            super().__init__()
            self.delays = 0

        async def random_delay(self, *_a: Any, **_k: Any) -> None:
            self.delays += 1

    human = _Human()
    scraper._browser_manager = cast(BrowserManager, _FakeBrowserManager(_FakePage(), human))

    async def _none(*_a: Any, **_k: Any) -> Any:
        return None

    monkeypatch.setattr(scraper, "_scrape_job_detail", _none)
    out = await scraper.run(job_ids=["101"], extract_recommended=False)
    assert out == []
    assert human.delays == 1


@pytest.mark.asyncio
async def test_job_detail_run_returns_empty_when_no_job_ids(tmp_path) -> None:
    settings = _settings(tmp_path)
    storage = JobStorage(settings)
    scraper = JobDetailScraper(settings=settings, storage=storage)
    out = await scraper.run(job_ids=[])
    assert out == []


@pytest.mark.asyncio
async def test_job_detail_run_skips_if_already_scraped(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    storage = JobStorage(settings)
    await storage.save_job_detail(JobDetail(job_id="101", title="t"))

    scraper = JobDetailScraper(settings=settings, storage=storage)
    scraper._browser_manager = cast(BrowserManager, _FakeBrowserManager(_FakePage(), _FakeHuman()))

    async def _boom(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("should not be called")

    monkeypatch.setattr(scraper, "_scrape_job_detail", _boom)
    out = await scraper.run(job_ids=["101"], extract_recommended=False)
    assert out == []


@pytest.mark.asyncio
async def test_job_detail_run_handles_scrape_errors_and_screenshots(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    storage = JobStorage(settings)
    scraper = JobDetailScraper(settings=settings, storage=storage)
    page = _FakePage()
    scraper._browser_manager = cast(BrowserManager, _FakeBrowserManager(page, _FakeHuman()))

    async def _boom(*_a: Any, **_k: Any) -> Any:
        raise RuntimeError("boom")

    shots: list[str] = []

    async def _shot(_page: Any, name: str) -> None:
        shots.append(name)

    monkeypatch.setattr(scraper, "_scrape_job_detail", _boom)
    monkeypatch.setattr(scraper, "_take_debug_screenshot", _shot)

    out = await scraper.run(job_ids=["101"], extract_recommended=False)
    assert out == []
    assert shots and shots[0].startswith("error_101")


@pytest.mark.asyncio
async def test_job_detail_scrape_job_detail_returns_none_when_safe_goto_fails(
    monkeypatch, tmp_path
) -> None:
    settings = _settings(tmp_path)
    scraper = JobDetailScraper(settings=settings, storage=JobStorage(settings))

    async def _nope(*_a: Any, **_k: Any) -> bool:
        return False

    monkeypatch.setattr(scraper, "_safe_goto", _nope)
    detail = await scraper._scrape_job_detail(
        cast(Page, _FakePage()), cast(HumanBehavior, _FakeHuman()), "1"
    )
    assert detail is None


@pytest.mark.asyncio
async def test_job_detail_scrape_job_detail_returns_none_when_content_missing(
    monkeypatch, tmp_path
) -> None:
    settings = _settings(tmp_path)
    scraper = JobDetailScraper(settings=settings, storage=JobStorage(settings))
    page = _FakePage()

    async def _ok(*_a: Any, **_k: Any) -> bool:
        return True

    async def _no_content(*_a: Any, **_k: Any) -> bool:
        return False

    shots: list[str] = []

    async def _shot(_page: Any, name: str) -> None:
        shots.append(name)

    monkeypatch.setattr(scraper, "_safe_goto", _ok)
    monkeypatch.setattr(base_module, "time", base_module.time)
    monkeypatch.setattr(
        "linkedin_scraper.scrapers.detail.scraper.wait_for_job_content", _no_content
    )
    monkeypatch.setattr(scraper, "_take_debug_screenshot", _shot)

    out = await scraper._scrape_job_detail(cast(Page, page), cast(HumanBehavior, _FakeHuman()), "1")
    assert out is None
    assert shots == ["no_content_1"]


@pytest.mark.asyncio
async def test_job_detail_scrape_job_detail_success_sets_fields(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    scraper = JobDetailScraper(settings=settings, storage=JobStorage(settings))
    page = _FakePage()

    async def _ok(*_a: Any, **_k: Any) -> bool:
        return True

    async def _loaded(*_a: Any, **_k: Any) -> bool:
        return True

    async def _noop_read(*_a: Any, **_k: Any) -> None:
        pass

    monkeypatch.setattr(scraper, "_safe_goto", _ok)
    monkeypatch.setattr("linkedin_scraper.scrapers.detail.scraper.wait_for_job_content", _loaded)
    monkeypatch.setattr(_FakeHuman, "simulate_reading", _noop_read, raising=False)

    async def _title(*_a: Any, **_k: Any) -> str:
        return "t"

    async def _company(*_a: Any, **_k: Any) -> str:
        return "c"

    async def _loc(*_a: Any, **_k: Any) -> str:
        return "l"

    async def _wt(*_a: Any, **_k: Any) -> str:
        return "Remote"

    async def _criteria(*_a: Any, **_k: Any) -> dict[str, str | None]:
        return {
            "employment_type": "Full-time",
            "seniority_level": "Senior",
            "industry": "Software",
            "job_function": "Engineering",
        }

    async def _desc(*_a: Any, **_k: Any) -> str:
        return "d"

    async def _posted(*_a: Any, **_k: Any) -> str:
        return "today"

    async def _apps(*_a: Any, **_k: Any) -> str:
        return "10 applicants"

    async def _salary(*_a: Any, **_k: Any) -> str:
        return "$1"

    async def _skills(*_a: Any, **_k: Any) -> list[str]:
        return ["Python"]

    async def _raw(*_a: Any, **_k: Any) -> dict[str, Any]:
        return {"x": "y"}

    monkeypatch.setattr("linkedin_scraper.scrapers.detail.scraper.extract_title", _title)
    monkeypatch.setattr("linkedin_scraper.scrapers.detail.scraper.extract_company", _company)
    monkeypatch.setattr("linkedin_scraper.scrapers.detail.scraper.extract_location", _loc)
    monkeypatch.setattr("linkedin_scraper.scrapers.detail.scraper.extract_workplace_type", _wt)
    monkeypatch.setattr("linkedin_scraper.scrapers.detail.scraper.extract_job_criteria", _criteria)
    monkeypatch.setattr("linkedin_scraper.scrapers.detail.scraper.extract_description", _desc)
    monkeypatch.setattr("linkedin_scraper.scrapers.detail.scraper.extract_posted_date", _posted)
    monkeypatch.setattr("linkedin_scraper.scrapers.detail.scraper.extract_applicant_count", _apps)
    monkeypatch.setattr("linkedin_scraper.scrapers.detail.scraper.extract_salary", _salary)
    monkeypatch.setattr("linkedin_scraper.scrapers.detail.scraper.extract_skills", _skills)
    monkeypatch.setattr("linkedin_scraper.scrapers.detail.scraper.extract_raw_sections", _raw)

    out = await scraper._scrape_job_detail(cast(Page, page), cast(HumanBehavior, _FakeHuman()), "1")
    assert out is not None
    assert out.title == "t"
    assert out.company_name == "c"
    assert out.location == "l"
    assert out.skills == ["Python"]


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
