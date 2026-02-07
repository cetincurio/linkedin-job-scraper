"""Job data storage and retrieval."""

from __future__ import annotations

import contextlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import aiofiles

from ljs.config import Settings, get_settings
from ljs.log import log_debug, log_error, log_exception, log_info, timed
from ljs.logging_config import get_logger
from ljs.models.job import JobDetail, JobId, JobIdSource

from . import ingest
from .exporter import export_job_details_jsonl
from .index import JobIndex
from .io import atomic_write_text
from .ledger import LedgerWriter


logger = get_logger(__name__)


class JobStorage:
    """Handles persistence of job IDs and job details.

    Storage strategy (option 2):
    - Append-only JSONL ledgers under `data/ledger/...` are merge-friendly across machines.
    - A local-only SQLite index under `data/index/...` is derived from ledgers for fast querying.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._settings.ensure_directories()
        self._index = JobIndex(self._settings.index_db_path)
        self._ledger = LedgerWriter(
            job_ids_path=self._settings.ledger_job_ids_dir / f"{self._settings.run_id}.jsonl",
            job_scrapes_path=self._settings.ledger_job_scrapes_dir
            / f"{self._settings.run_id}.jsonl",
        )
        log_debug(
            logger,
            "storage.init",
            run_id=self._settings.run_id,
            index_db_path=self._settings.index_db_path,
            ledger_job_ids_dir=self._settings.ledger_job_ids_dir,
            ledger_job_scrapes_dir=self._settings.ledger_job_scrapes_dir,
        )
        self._ingest_ledgers()

    def close(self) -> None:
        self._index.close()

    def __del__(self) -> None:
        # Best-effort close to avoid ResourceWarning in short-lived CLI runs/tests.
        with contextlib.suppress(Exception):
            self.close()

    def _get_job_detail_file(self, job_id: str) -> Path:
        """Get the file path for a job detail."""
        return self._settings.job_details_dir / f"{job_id}.json"

    def _ingest_ledgers(self) -> None:
        """Ingest any new ledger data into the local index (idempotent)."""
        with timed(logger, "storage.ingest_ledgers"):
            self._ingest_ledger_dir(self._settings.ledger_job_ids_dir, kind="job_ids")
            self._ingest_ledger_dir(self._settings.ledger_job_scrapes_dir, kind="job_scrapes")

    def _ingest_ledger_dir(self, ledger_dir: Path, *, kind: str) -> None:
        ingest.ingest_ledger_dir(
            ledger_dir,
            kind=kind,
            ingest_file_fn=lambda path, kind: self._ingest_ledger_file(path, kind=kind),
        )

    def _ingest_ledger_file(self, path: Path, *, kind: str) -> None:
        ingest.ingest_ledger_file(self._index, path, kind=kind)

    def _ingest_job_ids_lines(self, lines: list[bytes], *, path: Path) -> None:
        ingest.ingest_job_ids_lines(self._index, lines, path=path)

    def _ingest_job_scrape_lines(self, lines: list[bytes], *, path: Path) -> None:
        ingest.ingest_job_scrape_lines(self._index, lines, path=path)

    async def save_job_id(self, job: JobId) -> None:
        """Save a single job ID to storage."""
        await self.save_job_ids([job])

    async def save_job_ids(self, jobs: list[JobId]) -> int:
        """
        Save multiple job IDs to storage.

        Returns the number of new job IDs saved.
        """
        if not jobs:
            return 0

        log_debug(logger, "storage.save_job_ids.input", count=len(jobs))
        # De-duplicate within the input batch to avoid noisy ledgers and redundant DB writes.
        by_source: dict[JobIdSource, dict[str, JobId]] = {}
        for job in jobs:
            by_source.setdefault(job.source, {})
            by_source[job.source].setdefault(job.job_id, job)

        deduped: list[JobId] = []
        for source_jobs_by_id in by_source.values():
            deduped.extend(source_jobs_by_id.values())

        log_debug(logger, "storage.save_job_ids.deduped", count=len(deduped))
        with timed(logger, "storage.index.insert_job_ids", count=len(deduped)):
            inserted = self._index.insert_job_ids(deduped)
        if inserted:
            try:
                with timed(logger, "storage.ledger.append_job_ids", count=len(inserted)):
                    await self._ledger.append_job_ids(inserted)
            except Exception:
                # The DB is still correct; ledger write failures only impact cross-machine syncing.
                log_exception(logger, "storage.ledger.append_job_ids.error")
            log_info(logger, "storage.save_job_ids.saved", saved=len(inserted))
        else:
            log_debug(logger, "storage.save_job_ids.saved", saved=0)

        return len(inserted)

    async def get_job_ids(
        self,
        source: JobIdSource | None = None,
        unscraped_only: bool = False,
    ) -> list[JobId]:
        """
        Retrieve job IDs from storage.

        Args:
            source: Filter by source, or None for all sources
            unscraped_only: If True, only return job IDs not yet scraped
        """
        jobs = self._index.list_job_ids(source=source, unscraped_only=unscraped_only)
        log_debug(
            logger,
            "storage.get_job_ids",
            source=(source.value if source else None),
            unscraped_only=unscraped_only,
            count=len(jobs),
        )
        if not unscraped_only:
            return jobs

        # Self-heal: if job details exist (synced from another machine),
        # mark as scraped and filter out.
        remaining: list[JobId] = []
        for job in jobs:
            if self._get_job_detail_file(job.job_id).exists():
                self._index.mark_job_scraped(job.job_id)
                continue
            remaining.append(job)
        log_debug(
            logger,
            "storage.get_job_ids.unscraped_filtered",
            source=(source.value if source else None),
            remaining=len(remaining),
            initial=len(jobs),
        )
        return remaining

    async def mark_job_scraped(self, job_id: str) -> None:
        """Mark a job ID as scraped in the index and emit a scrape ledger event."""
        try:
            with timed(logger, "storage.ledger.append_job_scrape", job_id=job_id):
                await self._ledger.append_job_scrape(job_id)
        except Exception:
            log_exception(logger, "storage.ledger.append_job_scrape.error", job_id=job_id)
        with timed(logger, "storage.index.mark_job_scraped", job_id=job_id):
            self._index.mark_job_scraped(job_id)

    async def save_job_detail(self, detail: JobDetail) -> None:
        """Save job detail to storage."""
        file_path = self._get_job_detail_file(detail.job_id)
        data = detail.model_dump(mode="json")

        await atomic_write_text(file_path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")

        log_debug(logger, "storage.save_job_detail.saved", job_id=detail.job_id, path=file_path)

    async def get_job_detail(self, job_id: str) -> JobDetail | None:
        """Retrieve a job detail from storage."""
        file_path = self._get_job_detail_file(job_id)
        if not file_path.exists():
            return None

        try:
            async with aiofiles.open(file_path, encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)
                return JobDetail.model_validate(data)
        except (json.JSONDecodeError, ValueError) as e:
            log_error(logger, "storage.get_job_detail.error", job_id=job_id, error=str(e))
            return None

    async def job_detail_exists(self, job_id: str) -> bool:
        """Check if a job detail already exists in storage."""
        return self._get_job_detail_file(job_id).exists()

    def iter_job_details(self) -> Iterator[Path]:
        """Iterate over all job detail files."""
        return self._settings.job_details_dir.glob("*.json")

    async def get_stats(self) -> dict[str, int]:
        """Get storage statistics."""
        # Reconcile scraped status from job detail files (merge-friendly sync artifact).
        detail_job_ids = [p.stem for p in self.iter_job_details()]
        if detail_job_ids:
            self._index.mark_jobs_scraped(detail_job_ids)
        detail_count = len(detail_job_ids)

        return {
            "search_job_ids": self._index.count_job_ids(source=JobIdSource.SEARCH),
            "recommended_job_ids": self._index.count_job_ids(source=JobIdSource.RECOMMENDED),
            "unscraped_search": self._index.count_unscraped(source=JobIdSource.SEARCH),
            "unscraped_recommended": self._index.count_unscraped(source=JobIdSource.RECOMMENDED),
            "job_details": detail_count,
        }

    async def export_job_details_jsonl(
        self,
        output_path: Path,
        *,
        manifest_path: Path | None = None,
        redact_pii: bool = False,
        include_raw_sections: bool = False,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Export stored job details into a JSONL dataset file plus a manifest."""
        detail_files = sorted(self.iter_job_details())
        return await export_job_details_jsonl(
            detail_files,
            output_path,
            manifest_path=manifest_path,
            redact_pii=redact_pii,
            include_raw_sections=include_raw_sections,
            limit=limit,
        )
