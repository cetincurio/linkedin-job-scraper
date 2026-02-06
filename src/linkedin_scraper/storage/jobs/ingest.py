"""Ingest append-only JSONL ledgers into the local SQLite index.

Ledgers are the merge-friendly, cross-machine source of truth; the index is a
local derived cache for fast queries.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from linkedin_scraper.logging_config import get_logger
from linkedin_scraper.models.job import JobId

from .index import JobIndex


logger = get_logger(__name__)


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def ingest_ledger_dir(
    ledger_dir: Path,
    *,
    kind: str,
    ingest_file_fn: Callable[[Path, str], None],
) -> None:
    if not ledger_dir.exists():
        return

    for path in sorted(ledger_dir.glob("*.jsonl")):
        try:
            ingest_file_fn(path, kind)
        except Exception:
            logger.exception("Failed ingesting ledger %s (%s)", path, kind)


def ingest_ledger_file(index: JobIndex, path: Path, *, kind: str) -> None:
    path_str = str(path)
    offset = index.get_ledger_offset(path_str, kind=kind)

    try:
        size = path.stat().st_size
    except FileNotFoundError:
        return

    if offset < 0 or offset > size:
        offset = 0

    if size == offset:
        return

    # Read only complete JSONL lines so a partial trailing write does not poison ingestion.
    with path.open("rb") as f:
        f.seek(offset)
        data = f.read()

    last_nl = data.rfind(b"\n")
    if last_nl == -1:
        return

    chunk = data[: last_nl + 1]
    new_offset = offset + len(chunk)

    if kind == "job_ids":
        ingest_job_ids_lines(index, chunk.splitlines(), path=path)
    elif kind == "job_scrapes":
        ingest_job_scrape_lines(index, chunk.splitlines(), path=path)
    else:
        raise ValueError(f"Unknown ledger kind: {kind}")

    index.set_ledger_offset(path_str, kind=kind, bytes_processed=new_offset)


def ingest_job_ids_lines(index: JobIndex, lines: list[bytes], *, path: Path) -> None:
    jobs: list[JobId] = []
    for raw in lines:
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw.decode("utf-8"))
        except Exception as e:
            logger.warning("Skipping invalid JSON in %s: %s", path, e)
            continue

        if not isinstance(obj, dict):
            logger.warning("Skipping non-object JSON line in %s", path)
            continue

        obj.setdefault("discovered_at", _utc_now().isoformat())
        obj.setdefault("scraped", False)
        try:
            jobs.append(JobId.model_validate(obj))
        except Exception as e:
            logger.warning("Skipping invalid job id record in %s: %s", path, e)
            continue

        if len(jobs) >= 1000:
            index.insert_job_ids(jobs)
            jobs = []

    if jobs:
        index.insert_job_ids(jobs)


def ingest_job_scrape_lines(index: JobIndex, lines: list[bytes], *, path: Path) -> None:
    job_ids: list[str] = []
    for raw in lines:
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw.decode("utf-8"))
        except Exception as e:
            logger.warning("Skipping invalid JSON in %s: %s", path, e)
            continue

        if isinstance(obj, dict):
            jid = obj.get("job_id")
            if isinstance(jid, str) and jid:
                job_ids.append(jid)

        if len(job_ids) >= 2000:
            index.mark_jobs_scraped(job_ids)
            job_ids = []

    if job_ids:
        index.mark_jobs_scraped(job_ids)
