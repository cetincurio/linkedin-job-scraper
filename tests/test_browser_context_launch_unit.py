"""Unit tests for BrowserManager.launch and page event handling.

These tests fully mock Playwright so they do not open a real browser.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, cast

import pytest
from playwright.async_api import Page

import linkedin_scraper.browser.context as context_module
from linkedin_scraper.browser.context import BrowserManager
from linkedin_scraper.config import Settings


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


class _FakeContext:
    def __init__(self) -> None:
        self.closed = False
        self.handlers: list[tuple[str, Any]] = []
        self.new_pages: list[_FakePage] = []

    def on(self, event: str, handler: Any) -> None:
        self.handlers.append((event, handler))

    async def new_page(self) -> _FakePage:
        page = _FakePage()
        self.new_pages.append(page)
        return page

    async def close(self) -> None:
        self.closed = True


class _FakeBrowser:
    def __init__(self, context: _FakeContext) -> None:
        self._context = context
        self.closed = False
        self.new_context_options: dict[str, Any] | None = None

    async def new_context(self, **kwargs: Any) -> _FakeContext:
        self.new_context_options = dict(kwargs)
        return self._context

    async def close(self) -> None:
        self.closed = True


class _FakeBrowserType:
    def __init__(self, browser: _FakeBrowser) -> None:
        self._browser = browser
        self.launch_kwargs: dict[str, Any] | None = None

    async def launch(self, **kwargs: Any) -> _FakeBrowser:
        self.launch_kwargs = dict(kwargs)
        return self._browser


@dataclass
class _FakePlaywright:
    chromium: _FakeBrowserType


class _FakeAsyncPlaywrightCM:
    def __init__(self, playwright: _FakePlaywright) -> None:
        self._playwright = playwright

    async def __aenter__(self) -> _FakePlaywright:
        return self._playwright

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        _ = exc_type, exc, tb


class _FakePage:
    def __init__(self) -> None:
        self.url = "https://example.test/"


class _StealthCfg:
    def __init__(self) -> None:
        self.called = 0

    def get_context_options(self) -> dict[str, Any]:
        self.called += 1
        return {"user_agent": "ua"}


@pytest.mark.asyncio
async def test_launch_uses_async_playwright_and_cleans_up(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    mgr = BrowserManager(settings)

    fake_context = _FakeContext()
    fake_browser = _FakeBrowser(fake_context)
    fake_browser_type = _FakeBrowserType(fake_browser)
    fake_playwright = _FakePlaywright(chromium=fake_browser_type)

    monkeypatch.setattr(
        context_module, "async_playwright", lambda: _FakeAsyncPlaywrightCM(fake_playwright)
    )

    async def _noop_apply_stealth(_ctx: Any, _cfg: Any) -> None:
        pass

    async def _noop_inject(_page: Any) -> None:
        pass

    monkeypatch.setattr(context_module, "apply_stealth", _noop_apply_stealth)
    monkeypatch.setattr(context_module, "inject_evasion_scripts", _noop_inject)

    async with mgr.launch() as ctx:
        assert ctx is fake_context
        assert fake_browser_type.launch_kwargs is not None
        assert ("page", mgr._on_new_page_sync) in fake_context.handlers

    assert fake_context.closed is True
    assert fake_browser.closed is True
    assert mgr._context is None
    assert mgr._browser is None


@pytest.mark.asyncio
async def test_launch_accepts_explicit_stealth_config(monkeypatch, tmp_path) -> None:
    mgr = BrowserManager(_settings(tmp_path))

    fake_context = _FakeContext()
    fake_browser = _FakeBrowser(fake_context)
    fake_browser_type = _FakeBrowserType(fake_browser)
    fake_playwright = _FakePlaywright(chromium=fake_browser_type)

    monkeypatch.setattr(
        context_module, "async_playwright", lambda: _FakeAsyncPlaywrightCM(fake_playwright)
    )

    async def _noop_apply_stealth(_ctx: Any, _cfg: Any) -> None:
        pass

    async def _noop_inject(_page: Any) -> None:
        pass

    monkeypatch.setattr(context_module, "apply_stealth", _noop_apply_stealth)
    monkeypatch.setattr(context_module, "inject_evasion_scripts", _noop_inject)

    cfg = _StealthCfg()
    async with mgr.launch(stealth_config=cast(Any, cfg)) as _ctx:
        pass

    assert cfg.called == 1
    assert fake_browser.new_context_options == {"user_agent": "ua"}


def test_on_new_page_sync_logs_cancelled_and_exception(monkeypatch, tmp_path) -> None:
    mgr = BrowserManager(_settings(tmp_path))
    page = cast(Page, _FakePage())

    callbacks: list[Any] = []

    class _Task:
        def __init__(self, exc: BaseException | None) -> None:
            self._exc = exc

        def add_done_callback(self, cb: Any) -> None:
            callbacks.append((cb, self))

        def result(self) -> None:
            if self._exc is not None:
                raise self._exc

    def _fake_create_task(_coro: Any) -> _Task:
        # The callback behavior is the unit we care about here; the coroutine is ignored.
        _ = _coro
        return _Task(exc=asyncio.CancelledError())

    monkeypatch.setattr(context_module.asyncio, "create_task", _fake_create_task)
    mgr._on_new_page_sync(page)
    (cb, task) = callbacks.pop()
    cb(task)

    def _fake_create_task_2(_coro: Any) -> _Task:
        _ = _coro
        return _Task(exc=RuntimeError("boom"))

    monkeypatch.setattr(context_module.asyncio, "create_task", _fake_create_task_2)
    mgr._on_new_page_sync(page)
    (cb2, task2) = callbacks.pop()
    cb2(task2)


@pytest.mark.asyncio
async def test_on_new_page_injects_evasion_scripts(monkeypatch, tmp_path) -> None:
    mgr = BrowserManager(_settings(tmp_path))
    page = cast(Page, _FakePage())

    called: list[object] = []

    async def _inject(p: Any) -> None:
        called.append(p)

    monkeypatch.setattr(context_module, "inject_evasion_scripts", _inject)
    await mgr._on_new_page(page)
    assert called == [page]
