"""Browser context management with stealth capabilities."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from linkedin_scraper.browser.human import HumanBehavior
from linkedin_scraper.browser.stealth import StealthConfig, apply_stealth, inject_evasion_scripts
from linkedin_scraper.config import Settings, get_settings
from linkedin_scraper.logging_config import get_logger


__all__ = ["BrowserManager"]

logger = get_logger(__name__)


class BrowserManager:
    """Manages browser lifecycle with stealth and human-like behavior."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._stealth_config: StealthConfig | None = None

    @asynccontextmanager
    async def launch(
        self,
        stealth_config: StealthConfig | None = None,
    ) -> AsyncGenerator[BrowserContext]:
        """
        Launch browser with stealth configuration.

        Usage:
            async with browser_manager.launch() as context:
                page = await context.new_page()
                ...
        """
        self._stealth_config = stealth_config or StealthConfig()

        async with async_playwright() as playwright:
            logger.info(f"Launching {self._settings.browser_type} browser")

            # Browser launch options
            launch_options = {
                "headless": self._settings.headless,
                "slow_mo": self._settings.slow_mo,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars",
                    "--disable-extensions",
                    "--disable-gpu",
                    "--window-size=1920,1080",
                ],
            }

            browser_type = getattr(playwright, self._settings.browser_type)
            self._browser = await browser_type.launch(**launch_options)
            assert self._browser is not None, "Browser launch failed"

            # Create context with stealth options
            context_options = self._stealth_config.get_context_options()
            self._context = await self._browser.new_context(**context_options)
            assert self._context is not None, "Context creation failed"

            # Apply stealth modifications
            await apply_stealth(self._context, self._stealth_config)

            # Set up page event handlers
            self._context.on("page", self._on_new_page)

            logger.info("Browser launched with stealth configuration")

            try:
                yield self._context
            finally:
                await self._cleanup()

    async def _on_new_page(self, page: Page) -> None:
        """Handle new page creation - inject evasion scripts."""
        await inject_evasion_scripts(page)
        logger.debug(f"Evasion scripts injected into new page: {page.url}")

    async def _cleanup(self) -> None:
        """Clean up browser resources."""
        if self._context:
            await self._context.close()
            self._context = None
            logger.debug("Browser context closed")

        if self._browser:
            await self._browser.close()
            self._browser = None
            logger.info("Browser closed")

    @asynccontextmanager
    async def new_page(
        self,
        stealth_config: StealthConfig | None = None,
    ) -> AsyncGenerator[tuple[Page, HumanBehavior]]:
        """
        Convenience method to get a new page with human behavior helper.

        Usage:
            async with browser_manager.new_page() as (page, human):
                await page.goto("https://example.com")
                await human.random_delay()
        """
        async with self.launch(stealth_config) as context:
            page = await context.new_page()
            human = HumanBehavior(page)

            # Set default timeouts
            page.set_default_timeout(self._settings.page_load_timeout_ms)
            page.set_default_navigation_timeout(self._settings.page_load_timeout_ms)

            try:
                yield page, human
            finally:
                await page.close()


async def test_stealth() -> None:
    """Test stealth configuration against bot detection sites."""
    manager = BrowserManager()

    async with manager.new_page() as (page, human):
        logger.info("Testing stealth configuration...")

        # Test against bot detection site
        await page.goto("https://bot.sannysoft.com/")
        await human.simulate_reading(3, 5)

        # Take screenshot for verification
        settings = get_settings()
        screenshot_path = settings.screenshots_dir / "stealth_test.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        logger.info(f"Screenshot saved to {screenshot_path}")

        # Check webdriver flag
        webdriver = await page.evaluate("navigator.webdriver")
        logger.info(f"navigator.webdriver = {webdriver}")

        if webdriver:
            logger.warning("Stealth may not be fully effective!")
        else:
            logger.info("Stealth check passed: webdriver is undefined")


if __name__ == "__main__":
    from linkedin_scraper.logging_config import setup_logging

    setup_logging()
    asyncio.run(test_stealth())
