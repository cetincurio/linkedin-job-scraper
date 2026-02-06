"""Unit tests for HumanBehavior using fake Playwright objects."""

from __future__ import annotations

import asyncio
import random
from typing import Any, cast

import pytest
from playwright.async_api import Locator, Page

from linkedin_scraper.browser.human import HumanBehavior
from linkedin_scraper.config import Settings


class _FakeMouse:
    def __init__(self, page: _FakePage) -> None:
        self._page = page
        self.moves: list[tuple[float, float]] = []
        self.clicks: list[tuple[float, float]] = []
        self.wheels: list[tuple[int, int]] = []

    async def move(self, x: float, y: float) -> None:
        self.moves.append((x, y))

    async def click(self, x: float, y: float) -> None:
        self.clicks.append((x, y))

    async def wheel(self, dx: int, dy: int) -> None:
        self.wheels.append((dx, dy))
        self._page.scroll_y += dy


class _FakePage:
    def __init__(self) -> None:
        self.viewport_size: dict[str, int] | None = {"width": 800, "height": 600}
        self.mouse = _FakeMouse(self)
        self.scroll_y = 0
        self.scroll_height = 1000

    async def evaluate(self, expr: str) -> Any:
        if expr == "document.body.scrollHeight":
            return self.scroll_height
        if expr == "window.scrollY + window.innerHeight":
            height = self.viewport_size["height"] if self.viewport_size else 0
            return self.scroll_y + height
        raise ValueError(f"Unexpected eval: {expr}")


class _FakeLocator:
    def __init__(self, *, box: dict[str, float] | None = None) -> None:
        self._box = box
        self.cleared = False
        self.typed: list[tuple[str, int]] = []
        self.pressed: list[str] = []
        self.clicked = False

    async def clear(self) -> None:
        self.cleared = True

    async def press_sequentially(self, char: str, *, delay: int) -> None:
        self.typed.append((char, delay))

    async def press(self, key: str) -> None:
        self.pressed.append(key)

    async def bounding_box(self) -> dict[str, float] | None:
        return self._box

    async def click(self) -> None:
        self.clicked = True


def _settings(tmp_path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        headless=True,
        min_delay_ms=100,
        max_delay_ms=500,
        typing_delay_ms=20,
        mouse_movement_steps=5,
        min_request_interval_sec=0,
        max_requests_per_hour=0,
    )


@pytest.mark.asyncio
async def test_random_delay_uses_asyncio_sleep(monkeypatch, tmp_path) -> None:
    page = _FakePage()
    human = HumanBehavior(cast(Page, page), settings=_settings(tmp_path))

    slept: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(random, "randint", lambda a, b: 123)

    await human.random_delay()

    assert slept == [0.123]


@pytest.mark.asyncio
async def test_human_type_clears_and_types(monkeypatch, tmp_path) -> None:
    page = _FakePage()
    human = HumanBehavior(cast(Page, page), settings=_settings(tmp_path))
    locator = _FakeLocator()

    async def _fake_sleep(_seconds: float) -> None:
        pass

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(random, "randint", lambda a, b: 0)
    monkeypatch.setattr(random, "random", lambda: 1.0)  # no pauses, no typos

    await human.human_type(cast(Locator, locator), "abc")

    assert locator.cleared is True
    assert [c for (c, _d) in locator.typed] == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_human_click_falls_back_when_no_bounding_box(monkeypatch, tmp_path) -> None:
    page = _FakePage()
    human = HumanBehavior(cast(Page, page), settings=_settings(tmp_path))
    locator = _FakeLocator(box=None)

    async def _fake_sleep(_seconds: float) -> None:
        pass

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(random, "randint", lambda a, b: 0)

    await human.human_click(cast(Locator, locator))

    assert locator.clicked is True
    assert page.mouse.clicks == []


@pytest.mark.asyncio
async def test_move_mouse_human_generates_moves(monkeypatch, tmp_path) -> None:
    page = _FakePage()
    human = HumanBehavior(cast(Page, page), settings=_settings(tmp_path))

    async def _fake_sleep(_seconds: float) -> None:
        pass

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(random, "uniform", lambda a, b: (a + b) / 2)

    await human._move_mouse_human(400, 300)

    # steps + 1 points
    assert len(page.mouse.moves) == human._settings.mouse_movement_steps + 1


@pytest.mark.asyncio
async def test_scroll_to_bottom_reaches_bottom(monkeypatch, tmp_path) -> None:
    page = _FakePage()
    # Make it easy to reach bottom in one scroll.
    page.scroll_height = 900

    human = HumanBehavior(cast(Page, page), settings=_settings(tmp_path))

    async def _fake_sleep(_seconds: float) -> None:
        pass

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(random, "randint", lambda a, b: 300)
    monkeypatch.setattr(random, "uniform", lambda a, b: (a + b) / 2)
    monkeypatch.setattr(random, "random", lambda: 1.0)

    reached = await human.scroll_to_bottom(max_scrolls=3)
    assert reached is True


@pytest.mark.asyncio
async def test_human_type_respects_clear_first_false(monkeypatch, tmp_path) -> None:
    page = _FakePage()
    human = HumanBehavior(cast(Page, page), settings=_settings(tmp_path))
    locator = _FakeLocator()

    async def _fake_sleep(_seconds: float) -> None:
        pass

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(random, "randint", lambda a, b: 0)
    monkeypatch.setattr(random, "random", lambda: 1.0)  # no pauses, no typos

    await human.human_type(cast(Locator, locator), "a", clear_first=False)
    assert locator.cleared is False


@pytest.mark.asyncio
async def test_human_type_can_make_typo_and_backspace(monkeypatch, tmp_path) -> None:
    page = _FakePage()
    human = HumanBehavior(cast(Page, page), settings=_settings(tmp_path))
    locator = _FakeLocator()

    async def _fake_sleep(_seconds: float) -> None:
        pass

    # For the first character: no "thinking" pause, then do a typo; for the rest, do nothing.
    seq = iter([1.0, 0.0, 1.0, 1.0, 1.0, 1.0])

    def _rand() -> float:
        return next(seq)

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(random, "randint", lambda a, b: 0)
    monkeypatch.setattr(random, "random", _rand)
    monkeypatch.setattr(random, "choice", lambda _s: "z")
    monkeypatch.setattr(random, "uniform", lambda a, b: (a + b) / 2)

    await human.human_type(cast(Locator, locator), "ab")
    assert "Backspace" in locator.pressed


@pytest.mark.asyncio
async def test_human_type_can_pause_to_think(monkeypatch, tmp_path) -> None:
    page = _FakePage()
    human = HumanBehavior(cast(Page, page), settings=_settings(tmp_path))
    locator = _FakeLocator()

    slept: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    # First random(): trigger thinking pause; second random(): no typo.
    seq = iter([0.0, 1.0])

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(random, "randint", lambda a, b: 0)
    monkeypatch.setattr(random, "random", lambda: next(seq))
    monkeypatch.setattr(random, "uniform", lambda a, b: 0.5)

    await human.human_type(cast(Locator, locator), "a")
    assert slept


@pytest.mark.asyncio
async def test_human_click_with_bounding_box_can_skip_mouse_move(monkeypatch, tmp_path) -> None:
    page = _FakePage()
    human = HumanBehavior(cast(Page, page), settings=_settings(tmp_path))
    locator = _FakeLocator(box={"x": 10.0, "y": 20.0, "width": 100.0, "height": 200.0})

    async def _fake_sleep(_seconds: float) -> None:
        pass

    moved: list[tuple[float, float]] = []

    async def _fake_move(_x: float, _y: float) -> None:
        moved.append((_x, _y))

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(random, "randint", lambda a, b: 0)
    monkeypatch.setattr(random, "uniform", lambda a, b: 0.5)
    monkeypatch.setattr(HumanBehavior, "_move_mouse_human", _fake_move)

    await human.human_click(cast(Locator, locator), move_mouse=False)
    assert moved == []
    assert len(page.mouse.clicks) == 1


@pytest.mark.asyncio
async def test_human_click_with_bounding_box_moves_mouse_when_enabled(
    monkeypatch, tmp_path
) -> None:
    page = _FakePage()
    human = HumanBehavior(cast(Page, page), settings=_settings(tmp_path))
    locator = _FakeLocator(box={"x": 10.0, "y": 20.0, "width": 100.0, "height": 200.0})

    async def _fake_sleep(_seconds: float) -> None:
        pass

    moved: list[tuple[float, float]] = []

    async def _fake_move(self: Any, x: float, y: float) -> None:
        _ = self
        moved.append((x, y))

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(random, "randint", lambda a, b: 0)
    monkeypatch.setattr(random, "uniform", lambda a, b: 0.5)
    monkeypatch.setattr(HumanBehavior, "_move_mouse_human", _fake_move)

    await human.human_click(cast(Locator, locator), move_mouse=True)
    assert moved
    assert len(page.mouse.clicks) == 1


@pytest.mark.asyncio
async def test_move_mouse_human_uses_default_viewport_when_missing(monkeypatch, tmp_path) -> None:
    page = _FakePage()
    page.viewport_size = None
    human = HumanBehavior(cast(Page, page), settings=_settings(tmp_path))

    async def _fake_sleep(_seconds: float) -> None:
        pass

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(random, "uniform", lambda a, b: (a + b) / 2)

    await human._move_mouse_human(400, 300)
    assert len(page.mouse.moves) == human._settings.mouse_movement_steps + 1


@pytest.mark.asyncio
async def test_human_scroll_up_uses_negative_amount(monkeypatch, tmp_path) -> None:
    page = _FakePage()
    human = HumanBehavior(cast(Page, page), settings=_settings(tmp_path))

    async def _fake_sleep(_seconds: float) -> None:
        pass

    # amount=300, chunks=3
    seq = iter([300, 3])

    def _randint(_a: int, _b: int) -> int:
        return next(seq)

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(random, "randint", _randint)
    monkeypatch.setattr(random, "uniform", lambda a, b: (a + b) / 2)

    await human.human_scroll("up")
    assert page.scroll_y < 0
    assert any(dy < 0 for (_dx, dy) in page.mouse.wheels)


@pytest.mark.asyncio
async def test_scroll_to_bottom_returns_false_when_max_scrolls_exceeded(
    monkeypatch, tmp_path
) -> None:
    page = _FakePage()
    page.scroll_height = 1_000_000
    human = HumanBehavior(cast(Page, page), settings=_settings(tmp_path))

    async def _fake_sleep(_seconds: float) -> None:
        pass

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(random, "randint", lambda a, b: 300)
    monkeypatch.setattr(random, "uniform", lambda a, b: (a + b) / 2)
    monkeypatch.setattr(random, "random", lambda: 1.0)

    reached = await human.scroll_to_bottom(max_scrolls=2)
    assert reached is False


@pytest.mark.asyncio
async def test_scroll_to_bottom_covers_height_change_branch(monkeypatch, tmp_path) -> None:
    class _ChangingPage(_FakePage):
        def __init__(self) -> None:
            super().__init__()
            self._calls = 0

        async def evaluate(self, expr: str) -> Any:
            if expr == "document.body.scrollHeight":
                self._calls += 1
                if self._calls == 2:
                    # Height changes once.
                    return self.scroll_height + 100
                return self.scroll_height
            return await super().evaluate(expr)

    page = _ChangingPage()
    page.scroll_height = 1_000_000
    human = HumanBehavior(cast(Page, page), settings=_settings(tmp_path))

    async def _fake_sleep(_seconds: float) -> None:
        pass

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(random, "randint", lambda a, b: 300)
    monkeypatch.setattr(random, "uniform", lambda a, b: (a + b) / 2)
    monkeypatch.setattr(random, "random", lambda: 1.0)

    out = await human.scroll_to_bottom(max_scrolls=1)
    assert out is False


@pytest.mark.asyncio
async def test_random_mouse_movement_returns_when_no_viewport(monkeypatch, tmp_path) -> None:
    page = _FakePage()
    page.viewport_size = None
    human = HumanBehavior(cast(Page, page), settings=_settings(tmp_path))

    async def _boom(_x: float, _y: float) -> None:
        raise AssertionError("should not be called")

    monkeypatch.setattr(HumanBehavior, "_move_mouse_human", _boom)
    await human.random_mouse_movement()


@pytest.mark.asyncio
async def test_random_mouse_movement_moves_when_viewport_present(monkeypatch, tmp_path) -> None:
    page = _FakePage()
    human = HumanBehavior(cast(Page, page), settings=_settings(tmp_path))

    moved: list[tuple[float, float]] = []

    async def _fake_move(self: Any, x: float, y: float) -> None:
        _ = self
        moved.append((x, y))

    monkeypatch.setattr(random, "uniform", lambda a, b: (a + b) / 2)
    monkeypatch.setattr(HumanBehavior, "_move_mouse_human", _fake_move)

    await human.random_mouse_movement()
    assert moved


@pytest.mark.asyncio
async def test_simulate_reading_may_move_mouse(monkeypatch, tmp_path) -> None:
    page = _FakePage()
    human = HumanBehavior(cast(Page, page), settings=_settings(tmp_path))

    async def _fake_sleep(_seconds: float) -> None:
        pass

    moved: list[int] = []

    async def _fake_random_mouse_movement(self: Any) -> None:
        _ = self
        moved.append(1)

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(random, "uniform", lambda a, b: (a + b) / 2)
    monkeypatch.setattr(random, "random", lambda: 0.0)  # trigger movement
    monkeypatch.setattr(HumanBehavior, "random_mouse_movement", _fake_random_mouse_movement)

    await human.simulate_reading(2, 5)
    assert moved == [1]


@pytest.mark.asyncio
async def test_simulate_reading_can_skip_mouse_movement(monkeypatch, tmp_path) -> None:
    page = _FakePage()
    human = HumanBehavior(cast(Page, page), settings=_settings(tmp_path))

    async def _fake_sleep(_seconds: float) -> None:
        pass

    async def _boom() -> None:
        raise AssertionError("should not be called")

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(random, "uniform", lambda a, b: (a + b) / 2)
    monkeypatch.setattr(random, "random", lambda: 1.0)  # skip movement
    monkeypatch.setattr(HumanBehavior, "random_mouse_movement", _boom)

    await human.simulate_reading(2, 5)
