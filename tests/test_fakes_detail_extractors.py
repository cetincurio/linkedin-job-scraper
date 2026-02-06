"""Fakes for job detail extractor tests."""

from __future__ import annotations

from typing import Any


class DetailFakeScraper:
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


class DetailFakeButtonLocator:
    def __init__(self, visible: bool) -> None:
        self._visible = visible
        self.clicked = False

    @property
    def first(self) -> DetailFakeButtonLocator:
        return self

    async def count(self) -> int:
        return 1

    async def is_visible(self) -> bool:
        return self._visible


class DetailFakeCriteriaItem:
    def __init__(self, text: str) -> None:
        self._text = text

    async def inner_text(self) -> str:
        return self._text


class DetailFakeCriteriaLocator:
    def __init__(self, items: list[DetailFakeCriteriaItem]) -> None:
        self._items = items

    async def count(self) -> int:
        return len(self._items)

    def nth(self, i: int) -> DetailFakeCriteriaItem:
        return self._items[i]


class DetailFakePage:
    def __init__(self, *, expand_visible: bool, criteria_items: list[str] | None = None) -> None:
        self._expand = DetailFakeButtonLocator(expand_visible)
        self._criteria = DetailFakeCriteriaLocator(
            [DetailFakeCriteriaItem(t) for t in (criteria_items or [])]
        )

    def locator(self, selector: str) -> Any:
        if "job-insight" in selector or "criteria" in selector or "li" in selector:
            return self._criteria
        if selector.startswith("button") or "show-more" in selector:
            return self._expand
        return DetailFakeButtonLocator(False)


class DetailFakeHuman:
    def __init__(self) -> None:
        self.clicked = 0

    async def human_click(self, _locator: Any) -> None:
        self.clicked += 1

    async def random_delay(self, *_args: Any, **_kwargs: Any) -> None:
        pass
