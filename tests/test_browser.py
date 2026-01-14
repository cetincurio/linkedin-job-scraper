"""Tests for browser stealth configuration."""

from linkedin_scraper.browser.stealth import (
    USER_AGENTS,
    VIEWPORTS,
    StealthConfig,
    get_random_user_agent,
)


class TestStealthConfig:
    """Test StealthConfig dataclass and browser context options."""

    def test_default_config_uses_valid_user_agent(self) -> None:
        """Verify default config selects from known user agents."""
        config = StealthConfig()
        assert config.user_agent in USER_AGENTS
        assert "Mozilla" in config.user_agent  # All UAs have this

    def test_default_config_uses_valid_viewport(self) -> None:
        """Verify default config selects realistic viewport."""
        config = StealthConfig()
        assert config.viewport in VIEWPORTS
        assert 1000 <= config.viewport["width"] <= 2560
        assert 700 <= config.viewport["height"] <= 1600

    def test_custom_user_agent_override(self) -> None:
        """Verify custom user agent overrides default."""
        custom = "CustomBot/1.0"
        config = StealthConfig(user_agent=custom)
        assert config.user_agent == custom

    def test_custom_viewport_override(self) -> None:
        """Verify custom viewport overrides default."""
        custom = {"width": 800, "height": 600}
        config = StealthConfig(viewport=custom)
        assert config.viewport == custom

    def test_context_options_contains_required_fields(self) -> None:
        """Verify get_context_options returns all Playwright context fields."""
        config = StealthConfig()
        options = config.get_context_options()

        # Required for Playwright browser context
        assert options["user_agent"] == config.user_agent
        assert options["viewport"] == config.viewport
        assert options["locale"] == "en-GB"
        assert options["timezone_id"] == "Europe/London"
        assert options["color_scheme"] == "light"
        assert "geolocation" in options["permissions"]
        assert options["device_scale_factor"] in [1, 1.25, 1.5, 2]

    def test_stealth_evasion_flags_enabled_by_default(self) -> None:
        """Verify all stealth evasion techniques enabled by default."""
        config = StealthConfig()
        assert config.webdriver_undefined is True
        assert config.chrome_runtime is True
        assert config.navigator_plugins is True
        assert config.webgl_vendor is True
        assert config.permissions_api is True

    def test_languages_is_tuple_of_locale_codes(self) -> None:
        """Verify languages attribute contains valid locale codes."""
        config = StealthConfig()
        assert isinstance(config.languages, tuple)
        assert len(config.languages) >= 1
        # All should be language codes like 'en-US', 'en'
        for lang in config.languages:
            assert isinstance(lang, str)
            assert len(lang) >= 2


class TestUserAgentSelection:
    """Test user agent randomization."""

    def test_get_random_user_agent_returns_valid(self) -> None:
        """Verify random selection returns known user agent."""
        ua = get_random_user_agent()
        assert ua in USER_AGENTS

    def test_user_agents_all_contain_browser_identifier(self) -> None:
        """Verify all user agents identify as real browsers."""
        browsers = ["Chrome", "Firefox", "Safari", "Edg"]
        for ua in USER_AGENTS:
            assert any(b in ua for b in browsers), f"Invalid UA: {ua[:50]}..."
