"""Shared test fakes for unit tests (no real Playwright/browser needed)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from linkedin_scraper.browser.human import HumanBehavior
from linkedin_scraper.config import Settings
from linkedin_scraper.scrapers.base import BaseScraper


def settings_for_tests(tmp_path: Path) -> Settings:
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
class FakeResponse:
    status: int = 200


class FakeElement:
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


class FakeLocator:
    def __init__(self, elements: list[FakeElement]) -> None:
        self._elements = elements

    @property
    def first(self) -> FakeLocator:
        return FakeLocator(self._elements[:1])

    async def count(self) -> int:
        return len(self._elements)

    def nth(self, i: int) -> FakeLocator:
        return FakeLocator([self._elements[i]])

    async def inner_text(self) -> str:
        return (await self._elements[0].inner_text()) if self._elements else ""

    async def get_attribute(self, name: str) -> str | None:
        return (await self._elements[0].get_attribute(name)) if self._elements else None

    async def all(self) -> list[FakeElement]:
        return list(self._elements)


class FakePage:
    def __init__(self, *, html: str = "", links: list[str] | None = None) -> None:
        self._html = html
        self._links = links or []
        self.goto_urls: list[str] = []
        self.screenshots: list[str] = []
        self.url = "about:blank"

    async def goto(self, url: str, *, wait_until: str | None = None) -> FakeResponse:
        self.url = url
        self.goto_urls.append(url)
        _ = wait_until
        return FakeResponse(status=200)

    async def content(self) -> str:
        return self._html

    async def wait_for_selector(self, _selector: str, *, timeout: int | None = None) -> None:
        _ = timeout
        # Default: selector is present immediately in these unit tests.

    def locator(self, selector: str) -> FakeLocator:
        if selector == 'a[href*="/jobs/view/"]':
            elements = [FakeElement(href=href) for href in self._links]
            return FakeLocator(elements)
        return FakeLocator([])

    async def screenshot(self, *, path: str, full_page: bool | None = None) -> None:
        _ = full_page
        self.screenshots.append(path)


class FakeHuman:
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


class FakeBrowserManager:
    def __init__(self, page: FakePage, human: FakeHuman) -> None:
        self._page = page
        self._human = human

    @asynccontextmanager
    async def new_page(self, *_args: Any, **_kwargs: Any):
        yield self._page, self._human


class DummyScraper(BaseScraper):
    async def run(self, **_kwargs: Any) -> None:
        pass


def as_human(human: FakeHuman) -> HumanBehavior:
    # Convenience helper for tests to keep casts in one place.
    return human  # type: ignore[return-value]
