"""Tests for consent utilities."""

from __future__ import annotations

import os

from linkedin_scraper.consent import ACK_ENV, is_acknowledged_env, set_acknowledged_env


def test_set_acknowledged_env_sets_flag() -> None:
    """Ensure set_acknowledged_env updates the process environment."""
    # Start from a known state.
    if ACK_ENV in os.environ:
        del os.environ[ACK_ENV]

    assert not is_acknowledged_env()
    set_acknowledged_env()
    assert is_acknowledged_env()
