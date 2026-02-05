"""Typing helpers for the TUI layer."""

from __future__ import annotations

import asyncio
from typing import Any, Protocol


class TuiAppProtocol(Protocol):
    """Subset of the Textual App interface used by action mixins."""

    _running_task: asyncio.Task[None] | None
    theme: str

    def query_one(self, *args: Any, **kwargs: Any) -> Any: ...
    def log_message(self, message: str) -> None: ...
    async def _refresh_stats(self) -> None: ...
