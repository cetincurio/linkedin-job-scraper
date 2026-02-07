"""Text normalization and PII redaction helpers."""

from __future__ import annotations

import re


_JOB_DETAIL_DATASET_SCHEMA_VERSION = "linkedin-job-scraper.job_detail.v1"

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_CANDIDATE_RE = re.compile(r"(?:\+?\d[\d\s().-]{8,}\d)")
_WHITESPACE_RE = re.compile(r"[ \t]+")
_MANY_NEWLINES_RE = re.compile(r"\n{3,}")


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace and collapse excess newlines."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WHITESPACE_RE.sub(" ", text)
    text = _MANY_NEWLINES_RE.sub("\n\n", text)
    return text.strip()


def redact_pii(text: str) -> str:
    """Redact email and phone-like patterns from text."""
    text = _EMAIL_RE.sub("[EMAIL]", text)

    def _phone_repl(match: re.Match[str]) -> str:
        candidate = match.group(0)

        digits = sum(char.isdigit() for char in candidate)
        if digits < 10:
            return candidate
        if all(char.isdigit() for char in candidate):
            return candidate
        return "[PHONE]"

    return _PHONE_CANDIDATE_RE.sub(_phone_repl, text)


def build_ml_text(
    *,
    title: str | None,
    company_name: str | None,
    location: str | None,
    description: str | None,
) -> str:
    """Build a combined text field for ML workloads."""
    parts: list[str] = []
    if title:
        parts.append(title)
    if company_name:
        parts.append(company_name)
    if location:
        parts.append(location)
    if description:
        parts.append(description)
    return "\n\n".join(parts)


__all__ = [
    "_JOB_DETAIL_DATASET_SCHEMA_VERSION",
    "build_ml_text",
    "normalize_whitespace",
    "redact_pii",
]
