"""Browser context management with stealth capabilities."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from ljs.browser.human import HumanBehavior
from ljs.browser.stealth import StealthConfig, apply_stealth, inject_evasion_scripts
from ljs.config import Settings, get_settings
from ljs.log import log_debug, log_exception, log_info, log_warning, timed
from ljs.logging_config import get_logger


__all__ = ["BrowserManager"]

logger = get_logger(__name__)


class BrowserManager:
    """Manages browser lifecycle with stealth and human-like behavior."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._stealth_config: StealthConfig | None = None

    def _get_launch_options(self) -> dict[str, Any]:
        """Build Playwright launch options based on current settings."""
        args: list[str] = []
        if self._settings.browser_type == "chromium":
            args = [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--disable-extensions",
                "--disable-gpu",
                "--window-size=1920,1080",
            ]

            if self._settings.disable_browser_sandbox:
                log_warning(
                    logger,
                    "browser.sandbox.disabled",
                    browser_type=self._settings.browser_type,
                    note=(
                        "Chromium sandbox disabled (unsafe). Enable only when required "
                        "(e.g., some containers)."
                    ),
                )
                args.extend(["--no-sandbox", "--disable-setuid-sandbox"])

        return {
            "headless": self._settings.headless,
            "slow_mo": self._settings.slow_mo,
            "args": args,
        }

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
            launch_options = self._get_launch_options()
            log_info(
                logger,
                "browser.launch",
                browser_type=self._settings.browser_type,
                headless=self._settings.headless,
                slow_mo=self._settings.slow_mo,
            )

            browser_type = getattr(playwright, self._settings.browser_type)
            with timed(logger, "browser.launch", browser_type=self._settings.browser_type):
                self._browser = await browser_type.launch(**launch_options)
            assert self._browser is not None, "Browser launch failed"

            # Create context with stealth options
            context_options = self._stealth_config.get_context_options()
            with timed(logger, "browser.new_context", browser_type=self._settings.browser_type):
                self._context = await self._browser.new_context(**context_options)
            assert self._context is not None, "Context creation failed"

            # Apply stealth modifications
            with timed(logger, "browser.apply_stealth"):
                await apply_stealth(self._context, self._stealth_config)

            # Set up page event handlers
            # Playwright event handlers are invoked synchronously; schedule async work explicitly.
            self._context.on("page", self._on_new_page_sync)

            log_info(logger, "browser.ready", browser_type=self._settings.browser_type)

            try:
                yield self._context
            finally:
                await self._cleanup()

    def _on_new_page_sync(self, page: Page) -> None:
        """Sync wrapper for Playwright events: schedule async script injection."""
        task = asyncio.create_task(self._on_new_page(page))

        def _log_failure(t: asyncio.Task[None]) -> None:
            try:
                t.result()
            except asyncio.CancelledError:
                return
            except Exception:
                log_exception(logger, "browser.page.evasion_inject.error")

        task.add_done_callback(_log_failure)

    async def _on_new_page(self, page: Page) -> None:
        """Handle new page creation - inject evasion scripts."""
        with timed(logger, "browser.page.evasion_inject"):
            await inject_evasion_scripts(page)
        # Some unit tests stub `Page` objects without a `url` attribute.
        log_debug(logger, "browser.page.ready", url=getattr(page, "url", None))

    async def _cleanup(self) -> None:
        """Clean up browser resources."""
        if self._context:
            log_debug(logger, "browser.context.close")
            await self._context.close()
            self._context = None
            log_debug(logger, "browser.context.closed")

        if self._browser:
            log_info(logger, "browser.close")
            await self._browser.close()
            self._browser = None
            log_info(logger, "browser.closed")

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
            with timed(logger, "browser.new_page"):
                page = await context.new_page()
            human = HumanBehavior(page, settings=self._settings)

            # Set default timeouts
            page.set_default_timeout(self._settings.page_load_timeout_ms)
            page.set_default_navigation_timeout(self._settings.page_load_timeout_ms)
            log_debug(
                logger,
                "browser.page.timeouts",
                default_timeout_ms=self._settings.page_load_timeout_ms,
            )

            try:
                yield page, human
            finally:
                # Some unit tests stub `Page` objects without a `url` attribute.
                log_debug(logger, "browser.page.close", url=getattr(page, "url", None))
                await page.close()
