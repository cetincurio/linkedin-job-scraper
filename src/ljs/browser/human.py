"""Human-like behavior simulation for avoiding bot detection."""

import asyncio
import math
import random

from playwright.async_api import Locator, Page

from ljs.config import Settings, get_settings
from ljs.logging_config import get_logger


__all__ = ["HumanBehavior"]

logger = get_logger(__name__)


class HumanBehavior:
    """Simulates human-like interactions with web pages."""

    def __init__(self, page: Page, settings: Settings | None = None) -> None:
        self.page = page
        self._settings = settings or get_settings()
        self._last_action_time: float = 0

    async def random_delay(self, min_ms: int | None = None, max_ms: int | None = None) -> None:
        """Wait a random amount of time to simulate human thinking/reaction."""
        min_ms = min_ms or self._settings.min_delay_ms
        max_ms = max_ms or self._settings.max_delay_ms
        delay = random.randint(min_ms, max_ms)
        logger.debug(f"Random delay: {delay}ms")
        await asyncio.sleep(delay / 1000)

    async def human_type(
        self,
        locator: Locator,
        text: str,
        clear_first: bool = True,
    ) -> None:
        """
        Type text with human-like delays between keystrokes.

        Includes occasional typos and corrections for realism.
        """
        await self.random_delay(200, 500)

        if clear_first:
            await locator.clear()
            await self.random_delay(100, 300)

        # Type with variable delays
        for i, char in enumerate(text):
            # Occasional longer pause (thinking)
            if random.random() < 0.05:
                await asyncio.sleep(random.uniform(0.3, 0.8))

            # Variable typing speed
            delay = self._settings.typing_delay_ms + random.randint(-30, 50)
            await locator.press_sequentially(char, delay=max(20, delay))

            # Simulate occasional typo and backspace (rare)
            if random.random() < 0.02 and i < len(text) - 1:
                wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz")
                await locator.press_sequentially(wrong_char, delay=delay)
                await asyncio.sleep(random.uniform(0.1, 0.3))
                await locator.press("Backspace")

        logger.debug(f"Typed text: {text[:20]}...")

    async def human_click(
        self,
        locator: Locator,
        move_mouse: bool = True,
    ) -> None:
        """
        Click an element with human-like mouse movement.

        Moves the mouse in a curved path before clicking.
        """
        await self.random_delay(100, 400)

        # Get element bounding box
        box = await locator.bounding_box()
        if not box:
            logger.warning("Could not get bounding box, falling back to direct click")
            await locator.click()
            return

        # Calculate target position with slight randomness
        target_x = box["x"] + box["width"] * random.uniform(0.3, 0.7)
        target_y = box["y"] + box["height"] * random.uniform(0.3, 0.7)

        if move_mouse:
            await self._move_mouse_human(target_x, target_y)

        # Small delay before click
        await asyncio.sleep(random.uniform(0.05, 0.15))

        # Click with slight position variation
        await self.page.mouse.click(target_x, target_y)
        logger.debug(f"Clicked at ({target_x:.0f}, {target_y:.0f})")

    async def _move_mouse_human(self, target_x: float, target_y: float) -> None:
        """Move mouse in a natural curved path using Bezier curves."""
        # Get current mouse position (or start from random edge position)
        viewport = self.page.viewport_size
        if not viewport:
            viewport = {"width": 1280, "height": 720}

        # Start from a reasonable position
        start_x = random.uniform(viewport["width"] * 0.2, viewport["width"] * 0.8)
        start_y = random.uniform(viewport["height"] * 0.2, viewport["height"] * 0.8)

        # Generate control points for Bezier curve
        ctrl1_x = start_x + (target_x - start_x) * random.uniform(0.2, 0.4)
        ctrl1_y = start_y + random.uniform(-100, 100)
        ctrl2_x = start_x + (target_x - start_x) * random.uniform(0.6, 0.8)
        ctrl2_y = target_y + random.uniform(-100, 100)

        steps = self._settings.mouse_movement_steps
        for i in range(steps + 1):
            t = i / steps

            # Cubic Bezier curve
            x = (
                (1 - t) ** 3 * start_x
                + 3 * (1 - t) ** 2 * t * ctrl1_x
                + 3 * (1 - t) * t**2 * ctrl2_x
                + t**3 * target_x
            )
            y = (
                (1 - t) ** 3 * start_y
                + 3 * (1 - t) ** 2 * t * ctrl1_y
                + 3 * (1 - t) * t**2 * ctrl2_y
                + t**3 * target_y
            )

            await self.page.mouse.move(x, y)

            # Variable speed (slower at start and end)
            speed_factor = math.sin(t * math.pi)
            delay = 0.005 + 0.015 * (1 - speed_factor)
            await asyncio.sleep(delay)

    async def human_scroll(
        self,
        direction: str = "down",
        amount: int | None = None,
    ) -> None:
        """Scroll the page in a human-like manner with variable speed."""
        if amount is None:
            amount = random.randint(200, 500)

        if direction == "up":
            amount = -amount

        # Scroll in chunks with variable delays
        chunks = random.randint(3, 6)
        chunk_size = amount // chunks

        for _ in range(chunks):
            await self.page.mouse.wheel(0, chunk_size)
            await asyncio.sleep(random.uniform(0.02, 0.08))

        logger.debug(f"Scrolled {direction} by ~{abs(amount)}px")

    async def scroll_to_bottom(self, max_scrolls: int = 50) -> bool:
        """
        Scroll to the bottom of the page like a human would.

        Returns True if reached bottom, False if max_scrolls exceeded.
        """
        last_height = await self.page.evaluate("document.body.scrollHeight")
        scrolls = 0

        while scrolls < max_scrolls:
            # Variable scroll amount
            await self.human_scroll("down", random.randint(300, 700))
            await self.random_delay(500, 1500)

            # Check if we've reached the bottom
            new_height = await self.page.evaluate("document.body.scrollHeight")
            current_scroll = await self.page.evaluate("window.scrollY + window.innerHeight")

            if current_scroll >= new_height - 10:
                logger.debug("Reached bottom of page")
                return True

            if new_height == last_height:
                # Page height unchanged, might be at bottom
                scrolls += 1

            last_height = new_height

        logger.warning(f"Max scrolls ({max_scrolls}) reached without hitting bottom")
        return False

    async def random_mouse_movement(self) -> None:
        """Make random mouse movements to appear more human."""
        viewport = self.page.viewport_size
        if not viewport:
            return

        # Random movement within viewport
        x = random.uniform(100, viewport["width"] - 100)
        y = random.uniform(100, viewport["height"] - 100)

        await self._move_mouse_human(x, y)
        logger.debug("Performed random mouse movement")

    async def simulate_reading(self, min_sec: float = 2, max_sec: float = 5) -> None:
        """Simulate a user reading content on the page."""
        read_time = random.uniform(min_sec, max_sec)
        logger.debug(f"Simulating reading for {read_time:.1f}s")

        # Occasionally move mouse while reading
        if random.random() < 0.3:
            await self.random_mouse_movement()

        await asyncio.sleep(read_time)
