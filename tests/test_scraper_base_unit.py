"""Unit tests for BaseScraper helpers using fake Playwright objects."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import cast

import pytest
from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

import ljs.scrapers.base as base_module
from ljs.browser.human import HumanBehavior
from ljs.storage.jobs import JobStorage
from tests.test_fakes import (
    DummyScraper,
    FakeElement,
    FakeHuman,
    FakeLocator,
    FakePage,
    FakeResponse,
    settings_for_tests,
)


@pytest.mark.asyncio
async def test_safe_goto_success_and_http_error(tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    storage = JobStorage(settings)
    scraper = DummyScraper(settings=settings, storage=storage)

    page = FakePage()
    human = FakeHuman()
    ok = await scraper._safe_goto(
        cast(Page, page), "https://example.com", cast(HumanBehavior, human)
    )
    assert ok is True

    class _BadPage(FakePage):
        async def goto(self, url: str, *, wait_until: str | None = None) -> FakeResponse:
            await super().goto(url, wait_until=wait_until)
            return FakeResponse(status=500)

    bad_page = _BadPage()
    bad = await scraper._safe_goto(
        cast(Page, bad_page), "https://example.com/bad", cast(HumanBehavior, human)
    )
    assert bad is False


@pytest.mark.asyncio
async def test_wait_for_element_handles_timeout(tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    storage = JobStorage(settings)
    scraper = DummyScraper(settings=settings, storage=storage)

    class _TimeoutPage(FakePage):
        async def wait_for_selector(self, _selector: str, *, timeout: int | None = None) -> None:
            _ = timeout
            raise PlaywrightTimeout("boom")

    timeout_page = _TimeoutPage()
    ok = await scraper._wait_for_element(cast(Page, timeout_page), "div", timeout_ms=1)
    assert ok is False


@pytest.mark.asyncio
async def test_extract_text_and_all_text_strip_and_collect(tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = DummyScraper(settings=settings, storage=JobStorage(settings))

    class _TextPage(FakePage):
        def locator(self, selector: str) -> FakeLocator:
            _ = selector
            return FakeLocator(
                [
                    FakeElement(text="  hello  "),
                    FakeElement(text=""),
                    FakeElement(text="world"),
                ]
            )

    page = _TextPage()
    assert await scraper._extract_text(cast(Page, page), "any") == "hello"
    assert await scraper._extract_all_text(cast(Page, page), "any") == ["hello", "world"]


@pytest.mark.asyncio
async def test_check_rate_limit_respects_min_interval(monkeypatch, tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    settings.min_request_interval_sec = 1.0

    scraper = DummyScraper(settings=settings, storage=JobStorage(settings))
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
    settings = settings_for_tests(tmp_path)
    settings.min_request_interval_sec = 1.0
    settings.max_requests_per_hour = 0

    scraper = DummyScraper(settings=settings, storage=JobStorage(settings))
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
    settings = settings_for_tests(tmp_path)
    settings.max_requests_per_hour = 1
    settings.min_request_interval_sec = 0

    scraper = DummyScraper(settings=settings, storage=JobStorage(settings))
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
    settings = settings_for_tests(tmp_path)
    settings.max_requests_per_hour = 10_000
    settings.min_request_interval_sec = 1.0

    scraper = DummyScraper(settings=settings, storage=JobStorage(settings))
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
    settings = settings_for_tests(tmp_path)
    scraper = DummyScraper(settings=settings, storage=JobStorage(settings))
    human = FakeHuman()

    class _TimeoutPage(FakePage):
        async def goto(self, url: str, *, wait_until: str | None = None) -> FakeResponse:
            _ = url, wait_until
            raise PlaywrightTimeout("boom")

    ok = await scraper._safe_goto(
        cast(Page, _TimeoutPage()), "https://example.com", cast(HumanBehavior, human)
    )
    assert ok is False

    class _ErrPage(FakePage):
        async def goto(self, url: str, *, wait_until: str | None = None) -> FakeResponse:
            _ = url, wait_until
            raise RuntimeError("boom")

    ok2 = await scraper._safe_goto(
        cast(Page, _ErrPage()), "https://example.com", cast(HumanBehavior, human)
    )
    assert ok2 is False


@pytest.mark.asyncio
async def test_extract_text_and_all_text_return_defaults_on_errors(tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = DummyScraper(settings=settings, storage=JobStorage(settings))

    class _EmptyPage(FakePage):
        # Keep arg name `selector` for keyword-arg compatibility with FakePage.locator().
        def locator(self, selector: str) -> FakeLocator:
            _ = selector
            return FakeLocator([])

    assert await scraper._extract_text(cast(Page, _EmptyPage()), "x", default="d") == "d"

    class _ExplodingElement(FakeElement):
        async def inner_text(self) -> str:
            raise RuntimeError("boom")

    class _ExplodingTextPage(FakePage):
        def locator(self, selector: str) -> FakeLocator:
            _ = selector
            return FakeLocator([_ExplodingElement(text="x")])

    assert await scraper._extract_text(cast(Page, _ExplodingTextPage()), "x", default="d") == "d"

    class _ExplodingLocatorPage(FakePage):
        def locator(self, selector: str) -> FakeLocator:
            _ = selector
            raise RuntimeError("boom")

    assert await scraper._extract_all_text(cast(Page, _ExplodingLocatorPage()), "x") == []


@pytest.mark.asyncio
async def test_take_debug_screenshot_records_path(tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = DummyScraper(settings=settings, storage=JobStorage(settings))

    page = FakePage()
    await scraper._take_debug_screenshot(cast(Page, page), "x")
    assert page.screenshots
    assert page.screenshots[0].endswith(".png")
