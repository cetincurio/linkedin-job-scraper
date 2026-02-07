"""Stealth configuration for avoiding bot detection."""

import random
from dataclasses import dataclass, field
from typing import Any

from playwright.async_api import BrowserContext, Page
from playwright_stealth import Stealth

from ljs.logging_config import get_logger


__all__ = ["USER_AGENTS", "StealthConfig", "apply_stealth", "get_random_user_agent"]

logger = get_logger(__name__)

USER_AGENTS: list[str] = [
    # Chrome on Windows
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    ),
    # Chrome on macOS
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    ),
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Firefox on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Edge on Windows
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
    ),
]

VIEWPORTS: list[dict[str, int]] = [
    {"width": 1920, "height": 1080},
    {"width": 1680, "height": 1050},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
]

LANGUAGES: list[tuple[str, ...]] = [
    ("en-US", "en"),
    ("en-GB", "en"),
    ("en-US", "en-GB", "en"),
]


@dataclass
class StealthConfig:
    """Configuration for stealth browser behavior."""

    user_agent: str = field(default_factory=lambda: random.choice(USER_AGENTS))
    viewport: dict[str, int] = field(default_factory=lambda: random.choice(VIEWPORTS))
    languages: tuple[str, ...] = field(default_factory=lambda: random.choice(LANGUAGES))
    timezone_id: str = "Europe/London"
    locale: str = "en-GB"

    # Stealth evasion toggles
    webdriver_undefined: bool = True
    chrome_runtime: bool = True
    navigator_plugins: bool = True
    webgl_vendor: bool = True
    permissions_api: bool = True

    def get_context_options(self) -> dict[str, Any]:
        """Get browser context options for Playwright."""
        return {
            "user_agent": self.user_agent,
            "viewport": self.viewport,
            "locale": self.locale,
            "timezone_id": self.timezone_id,
            "permissions": ["geolocation"],
            "color_scheme": "light",
            "device_scale_factor": random.choice([1, 1.25, 1.5, 2]),
        }


def get_random_user_agent() -> str:
    """Get a random user agent string."""
    return random.choice(USER_AGENTS)


async def apply_stealth(context: BrowserContext, config: StealthConfig | None = None) -> None:
    """
    Apply stealth modifications to a browser context.

    Uses playwright-stealth library combined with custom evasions.
    """
    config = config or StealthConfig()
    logger.debug("Applying stealth configuration")

    stealth = Stealth(
        navigator_webdriver=config.webdriver_undefined,
        chrome_runtime=config.chrome_runtime,
        navigator_plugins=config.navigator_plugins,
        webgl_vendor=config.webgl_vendor,
        navigator_permissions=config.permissions_api,
        navigator_languages=True,
        navigator_platform=True,
        navigator_vendor=True,
        navigator_hardware_concurrency=True,
        navigator_languages_override=config.languages[:2]
        if len(config.languages) >= 2
        else ("en-US", "en"),
        webgl_vendor_override="Intel Inc.",
        webgl_renderer_override="Intel Iris OpenGL Engine",
    )

    await stealth.apply_stealth_async(context)
    logger.debug("Stealth configuration applied successfully")


async def inject_evasion_scripts(page: Page) -> None:
    """
    Inject additional evasion scripts into a page.

    These scripts run before any page JavaScript.
    """
    await page.add_init_script("""
        // Override navigator.webdriver
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true
        });

        // Add missing chrome object for Chromium
        if (!window.chrome) {
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
        }

        // Override permissions query
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );

        // Spoof plugins length
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const plugins = [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                    { name: 'Native Client', filename: 'internal-nacl-plugin' }
                ];
                plugins.item = (i) => plugins[i];
                plugins.namedItem = (name) => plugins.find(p => p.name === name);
                plugins.refresh = () => {};
                return plugins;
            }
        });

        // Spoof languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });

        // Hide automation indicators
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
    """)
