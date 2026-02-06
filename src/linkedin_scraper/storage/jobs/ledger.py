"""Append-only JSONL ledgers.

Ledgers are the sync-friendly source of truth across machines (Git merges well).
The SQLite index is derived from these ledgers and can be deleted/rebuilt.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import aiofiles

from linkedin_scraper.models.job import JobId


def _utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


class LedgerWriter:
    """Write discovery/scrape events to append-only JSONL files."""

    def __init__(
        self,
        *,
        job_ids_path: Path,
        job_scrapes_path: Path,
    ) -> None:
        self._job_ids_path = job_ids_path
        self._job_scrapes_path = job_scrapes_path
        self._job_ids_path.parent.mkdir(parents=True, exist_ok=True)
        self._job_scrapes_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def job_ids_path(self) -> Path:
        return self._job_ids_path

    @property
    def job_scrapes_path(self) -> Path:
        return self._job_scrapes_path

    async def append_job_ids(self, jobs: list[JobId]) -> None:
        if not jobs:
            return

        # Discovery ledger intentionally excludes mutable fields like `scraped`.
        async with aiofiles.open(self._job_ids_path, "a", encoding="utf-8") as f:
            for job in jobs:
                record = job.model_dump(
                    mode="json",
                    exclude={"scraped"},
                )
                await f.write(json.dumps(record, ensure_ascii=False) + "\n")

    async def append_job_scrape(self, job_id: str) -> None:
        record = {
            "job_id": job_id,
            "scraped_at": _utc_now_iso(),
        }
        async with aiofiles.open(self._job_scrapes_path, "a", encoding="utf-8") as f:
            await f.write(json.dumps(record, ensure_ascii=False) + "\n")
