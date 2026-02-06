"""Manual stealth check against common bot-detection signals.

This is intentionally kept out of the library code to avoid shipping debug-only
logic as part of the public API.
"""

from __future__ import annotations

import asyncio

from linkedin_scraper.browser.context import BrowserManager
from linkedin_scraper.config import get_settings
from linkedin_scraper.logging_config import get_logger, setup_logging


logger = get_logger(__name__)


async def main() -> None:
    manager = BrowserManager()

    async with manager.new_page() as (page, human):
        logger.info("Testing stealth configuration...")

        await page.goto("https://bot.sannysoft.com/")
        await human.simulate_reading(3, 5)

        settings = get_settings()
        screenshot_path = settings.screenshots_dir / "stealth_test.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        logger.info("Screenshot saved to %s", screenshot_path)

        webdriver = await page.evaluate("navigator.webdriver")
        logger.info("navigator.webdriver = %s", webdriver)

        if webdriver:
            logger.warning("Stealth may not be fully effective!")
        else:
            logger.info("Stealth check passed: webdriver is undefined")


if __name__ == "__main__":
    setup_logging()
    asyncio.run(main())
