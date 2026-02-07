"""Small structured logging helpers.

Goals:
- Very low call-site bloat (1 line per event).
- Self-explanatory, scan-friendly messages for live tailing.
- Safe by default: redact likely secrets, truncate very long values.
"""

from __future__ import annotations

import contextvars
import logging
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any


__all__ = [
    "bind_log_context",
    "get_log_context",
    "log_debug",
    "log_error",
    "log_exception",
    "log_info",
    "log_warning",
    "set_log_context",
    "timed",
]


_CTX: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "ljs_log_ctx",
    default=None,
)

# Keep messages compact and safe. This isn't meant to be perfect, just protective.
_SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "passwd",
    "pass",
    "token",
    "secret",
    "cookie",
    "session",
    "csrf",
    "auth",
    "bearer",
)

_DEFAULT_TRUNCATE_AT = 240
_MAX_LIST_ITEMS = 4

# Keys we want to float to the front to reduce hunting in live logs.
_KEY_PRIORITY: dict[str, int] = {
    "run_id": 0,
    "op": 1,
    "phase": 2,
    "status": 3,
    "duration_ms": 4,
    "job_id": 10,
    "parent_job_id": 11,
    "keyword": 12,
    "country": 13,
    "url": 14,
    "selector": 15,
    "path": 16,
    "count": 17,
    "saved": 18,
    "skipped": 19,
    "attempt": 20,
    "timeout_ms": 21,
    "http_status": 22,
    "error": 90,
    "exc": 91,
}


def bind_log_context(**fields: Any):
    """Bind fields to the current async/task context (contextvars-based)."""

    @contextmanager
    def _cm():
        current = _CTX.get() or {}
        merged = dict(current)
        merged.update({k: v for k, v in fields.items() if v is not None})
        token = _CTX.set(merged)
        try:
            yield
        finally:
            _CTX.reset(token)

    return _cm()


def set_log_context(**fields: Any) -> None:
    """Set fields on the current context without automatic reset."""
    current = _CTX.get() or {}
    merged = dict(current)
    merged.update({k: v for k, v in fields.items() if v is not None})
    _CTX.set(merged)


def get_log_context() -> dict[str, Any]:
    """Fetch the current bound context (primarily for testing/debugging)."""
    return dict(_CTX.get() or {})


def _is_sensitive_key(key: str) -> bool:
    k = key.lower()
    return any(fragment in k for fragment in _SENSITIVE_KEY_FRAGMENTS)


def _shorten_str(s: str, *, limit: int = _DEFAULT_TRUNCATE_AT) -> str:
    if len(s) <= limit:
        return s
    # Prefix is usually the useful part for URLs/selectors; keep a small suffix for IDs.
    head = s[: max(0, limit - 20)]
    tail = s[-17:]
    return f"{head}...{tail}"


def _fmt_value(value: Any) -> str:
    out: str
    if value is None:
        out = "null"
    elif isinstance(value, bool):
        out = "true" if value else "false"
    elif isinstance(value, (int, float)):
        out = str(value)
    elif isinstance(value, Path):
        out = _shorten_str(str(value))
    elif isinstance(value, str):
        out = _shorten_str(value)
    elif isinstance(value, (list, tuple, set)):
        seq = list(value)
        if len(seq) <= _MAX_LIST_ITEMS:
            inner = ",".join(_fmt_value(v) for v in seq)
            out = f"[{inner}]"
        else:
            out = f"[len={len(seq)}]"
    elif isinstance(value, dict):
        out = f"{{len={len(value)}}}"
    else:
        out = _shorten_str(repr(value))
    return out


def _sorted_kv_items(fields: dict[str, Any]) -> list[tuple[str, Any]]:
    def _key(item: tuple[str, Any]) -> tuple[int, str]:
        k, _ = item
        return (_KEY_PRIORITY.get(k, 50), k)

    return sorted(fields.items(), key=_key)


def _format_event(event: str, fields: dict[str, Any]) -> str:
    ctx = _CTX.get() or {}
    merged = dict(ctx)
    merged.update(fields)
    merged = {k: v for k, v in merged.items() if v is not None}

    parts: list[str] = [event]
    for k, v in _sorted_kv_items(merged):
        if _is_sensitive_key(k):
            parts.append(f"{k}=***")
            continue
        parts.append(f"{k}={_fmt_value(v)}")
    # Space-separated k=v pairs are easier to scan quickly in live logs.
    return " ".join(parts)


def _log(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    if not logger.isEnabledFor(level):
        return
    logger.log(level, _format_event(event, fields))


def log_debug(logger: logging.Logger, event: str, **fields: Any) -> None:
    _log(logger, logging.DEBUG, event, **fields)


def log_info(logger: logging.Logger, event: str, **fields: Any) -> None:
    _log(logger, logging.INFO, event, **fields)


def log_warning(logger: logging.Logger, event: str, **fields: Any) -> None:
    _log(logger, logging.WARNING, event, **fields)


def log_error(logger: logging.Logger, event: str, **fields: Any) -> None:
    _log(logger, logging.ERROR, event, **fields)


def log_exception(logger: logging.Logger, event: str, **fields: Any) -> None:
    # Keep traceback, but preserve the scan-friendly event line.
    if not logger.isEnabledFor(logging.ERROR):
        return
    logger.exception(_format_event(event, fields))


@contextmanager
def timed(
    logger: logging.Logger,
    op: str,
    *,
    level: int = logging.DEBUG,
    **fields: Any,
):
    """Time an operation and log start/end at the given level.

    This is intentionally DEBUG by default to avoid noisy INFO logs during normal runs.
    """
    start = time.perf_counter()
    _log(logger, level, f"{op}.start", **fields)
    try:
        yield
    except Exception as exc:
        duration_ms = int((time.perf_counter() - start) * 1000.0)
        _log(
            logger,
            logging.ERROR,
            f"{op}.error",
            duration_ms=duration_ms,
            exc=type(exc).__name__,
            **fields,
        )
        raise
    else:
        duration_ms = int((time.perf_counter() - start) * 1000.0)
        _log(logger, level, f"{op}.ok", duration_ms=duration_ms, **fields)
