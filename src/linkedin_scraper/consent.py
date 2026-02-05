"""Consent utilities for educational-only usage."""

from __future__ import annotations

import os


ACK_ENV = "LINKEDIN_SCRAPER_ACKNOWLEDGE"
ACK_MESSAGE = (
    "This project is for offline educational use only. "
    "Only access content you are authorized to access and comply with all "
    "applicable terms, policies, and laws."
)


def is_ack_value(value: str) -> bool:
    """Return True if a string value indicates acknowledgement."""
    return value.strip().lower() in {"1", "true", "yes", "y"}


def is_acknowledged_env() -> bool:
    """Check acknowledgement based on environment variable."""
    return is_ack_value(os.getenv(ACK_ENV, ""))


def set_acknowledged_env() -> None:
    """Persist acknowledgement in the process environment."""
    os.environ[ACK_ENV] = "1"
