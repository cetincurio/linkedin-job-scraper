"""Unit tests for BrowserManager that avoid launching a real browser."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, cast

import pytest
from playwright.async_api import Browser, BrowserContext

from linkedin_scraper.browser.context import BrowserManager
from linkedin_scraper.config import Settings


class _DummyClosable:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class _FakePage:
    def __init__(self) -> None:
        self.default_timeout_ms: int | None = None
        self.default_nav_timeout_ms: int | None = None
        self.closed = False

    def set_default_timeout(self, timeout_ms: int) -> None:
        self.default_timeout_ms = timeout_ms

    def set_default_navigation_timeout(self, timeout_ms: int) -> None:
        self.default_nav_timeout_ms = timeout_ms

    async def close(self) -> None:
        self.closed = True


class _FakeContext:
    def __init__(self, page: _FakePage) -> None:
        self._page = page

    async def new_page(self) -> _FakePage:
        return self._page


def _settings(tmp_path) -> Settings:
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
    )


def test_get_launch_options_chromium_sandbox_enabled(tmp_path) -> None:
    settings = _settings(tmp_path)
    manager = BrowserManager(settings)

    opts = manager._get_launch_options()
    assert opts["headless"] is True
    assert opts["slow_mo"] == 0
    assert "--no-sandbox" not in opts["args"]
    assert "--disable-setuid-sandbox" not in opts["args"]


def test_get_launch_options_chromium_sandbox_disabled(tmp_path) -> None:
    settings = _settings(tmp_path)
    settings.disable_browser_sandbox = True
    manager = BrowserManager(settings)

    opts = manager._get_launch_options()
    assert "--no-sandbox" in opts["args"]
    assert "--disable-setuid-sandbox" in opts["args"]


def test_get_launch_options_non_chromium_has_no_args(tmp_path) -> None:
    settings = _settings(tmp_path)
    settings.browser_type = "firefox"
    manager = BrowserManager(settings)

    opts = manager._get_launch_options()
    assert opts["args"] == []


@pytest.mark.asyncio
async def test_cleanup_closes_context_and_browser(tmp_path) -> None:
    manager = BrowserManager(_settings(tmp_path))

    ctx = _DummyClosable()
    browser = _DummyClosable()
    manager._context = cast(BrowserContext, ctx)
    manager._browser = cast(Browser, browser)

    await manager._cleanup()

    assert ctx.closed is True
    assert browser.closed is True
    assert manager._context is None
    assert manager._browser is None


@pytest.mark.asyncio
async def test_cleanup_handles_missing_browser_or_context(tmp_path) -> None:
    manager = BrowserManager(_settings(tmp_path))

    ctx = _DummyClosable()
    manager._context = cast(BrowserContext, ctx)
    manager._browser = None
    await manager._cleanup()
    assert ctx.closed is True

    browser = _DummyClosable()
    manager._context = None
    manager._browser = cast(Browser, browser)
    await manager._cleanup()
    assert browser.closed is True


@pytest.mark.asyncio
async def test_new_page_sets_timeouts_and_closes_page(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    manager = BrowserManager(settings)

    page = _FakePage()
    context = _FakeContext(page)

    @asynccontextmanager
    async def _fake_launch(self: Any, _stealth_config: object | None = None):
        yield context

    monkeypatch.setattr(BrowserManager, "launch", _fake_launch)

    async with manager.new_page() as (p, _human):
        assert p is page
        assert page.default_timeout_ms == settings.page_load_timeout_ms
        assert page.default_nav_timeout_ms == settings.page_load_timeout_ms

    assert page.closed is True


@pytest.mark.asyncio
async def test_new_page_closes_page_on_exception(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    manager = BrowserManager(settings)

    page = _FakePage()
    context = _FakeContext(page)

    @asynccontextmanager
    async def _fake_launch(self: Any, _stealth_config: object | None = None):
        yield context

    monkeypatch.setattr(BrowserManager, "launch", _fake_launch)

    with pytest.raises(RuntimeError, match="boom"):
        async with manager.new_page() as (_p, _human):
            raise RuntimeError("boom")

    assert page.closed is True
