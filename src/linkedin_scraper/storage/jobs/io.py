"""Small async I/O helpers used by job storage."""

from __future__ import annotations

from pathlib import Path

import aiofiles


async def atomic_write_text(path: Path, text: str) -> None:
    """Write text to a file atomically (best-effort) to avoid partial writes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")

    async with aiofiles.open(tmp_path, "w", encoding="utf-8") as f:
        await f.write(text)

    tmp_path.replace(path)
