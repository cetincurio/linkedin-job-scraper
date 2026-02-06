"""Local SQLite index derived from append-only ledgers.

This index is intentionally local-only (not meant for Git syncing). It is rebuilt
and updated by ingesting JSONL ledgers, which are merge-friendly across machines.
"""

from __future__ import annotations

import contextlib
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from linkedin_scraper.logging_config import get_logger
from linkedin_scraper.models.job import JobId, JobIdSource


logger = get_logger(__name__)

_SCHEMA_VERSION = 1


def _utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


class JobIndex:
    """SQLite-backed index for job IDs and scrape status."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), timeout=30)
        self._conn.row_factory = sqlite3.Row
        self._configure()
        self._ensure_schema()

    def _configure(self) -> None:
        cur = self._conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("PRAGMA synchronous=NORMAL;")
        cur.execute("PRAGMA foreign_keys=ON;")
        cur.execute("PRAGMA busy_timeout=30000;")
        self._conn.commit()

    def _ensure_schema(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS job_ids (
              job_id TEXT NOT NULL,
              source TEXT NOT NULL,
              discovered_at TEXT NOT NULL,
              search_keyword TEXT,
              search_country TEXT,
              parent_job_id TEXT,
              scraped INTEGER NOT NULL DEFAULT 0,
              PRIMARY KEY (job_id, source)
            );
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_job_ids_source_scraped
            ON job_ids (source, scraped);
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ledger_state (
              path TEXT NOT NULL PRIMARY KEY,
              kind TEXT NOT NULL,
              bytes_processed INTEGER NOT NULL,
              updated_at TEXT NOT NULL
            );
            """
        )
        cur.execute(
            "INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?);",
            (str(_SCHEMA_VERSION),),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __del__(self) -> None:
        # Best-effort close to avoid ResourceWarning in short-lived CLI runs/tests.
        with contextlib.suppress(Exception):
            self.close()

    def insert_job_ids(self, jobs: list[JobId]) -> list[JobId]:
        """Insert new job IDs; return only those that were newly inserted."""
        if not jobs:
            return []

        inserted: list[JobId] = []
        cur = self._conn.cursor()

        with self._conn:
            for job in jobs:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO job_ids (
                      job_id,
                      source,
                      discovered_at,
                      search_keyword,
                      search_country,
                      parent_job_id,
                      scraped
                    ) VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        job.job_id,
                        job.source.value,
                        job.discovered_at.isoformat(),
                        job.search_keyword,
                        job.search_country,
                        job.parent_job_id,
                        1 if job.scraped else 0,
                    ),
                )
                if cur.rowcount == 1:
                    inserted.append(job)

        return inserted

    def list_job_ids(
        self,
        *,
        source: JobIdSource | None = None,
        unscraped_only: bool = False,
    ) -> list[JobId]:
        """List job IDs from the index."""
        cur = self._conn.cursor()

        where = []
        params: list[object] = []
        if source is not None:
            where.append("source = ?")
            params.append(source.value)
        if unscraped_only:
            where.append("scraped = 0")

        sql = (
            "SELECT job_id, source, discovered_at, search_keyword, search_country, parent_job_id, "
            "scraped FROM job_ids"
        )
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY discovered_at ASC;"

        rows = cur.execute(sql, params).fetchall()
        # Use Pydantic parsing to keep behavior consistent with the old JSON storage.
        return [JobId.model_validate(dict(r)) for r in rows]

    def mark_job_scraped(self, job_id: str) -> int:
        """Mark a job as scraped for all sources; returns rows changed."""
        cur = self._conn.cursor()
        with self._conn:
            cur.execute(
                "UPDATE job_ids SET scraped = 1 WHERE job_id = ? AND scraped = 0;",
                (job_id,),
            )
            return int(cur.rowcount)

    def mark_jobs_scraped(self, job_ids: list[str]) -> int:
        """Mark multiple jobs scraped; returns total rows changed."""
        if not job_ids:
            return 0
        cur = self._conn.cursor()
        changed = 0
        with self._conn:
            for job_id in job_ids:
                cur.execute(
                    "UPDATE job_ids SET scraped = 1 WHERE job_id = ? AND scraped = 0;",
                    (job_id,),
                )
                changed += int(cur.rowcount)
        return changed

    def count_job_ids(self, *, source: JobIdSource | None = None) -> int:
        cur = self._conn.cursor()
        if source is None:
            row = cur.execute("SELECT COUNT(*) AS c FROM job_ids;").fetchone()
        else:
            row = cur.execute(
                "SELECT COUNT(*) AS c FROM job_ids WHERE source = ?;",
                (source.value,),
            ).fetchone()
        return int(row["c"]) if row else 0

    def count_unscraped(self, *, source: JobIdSource) -> int:
        cur = self._conn.cursor()
        row = cur.execute(
            "SELECT COUNT(*) AS c FROM job_ids WHERE source = ? AND scraped = 0;",
            (source.value,),
        ).fetchone()
        return int(row["c"]) if row else 0

    def get_ledger_offset(self, path: str, *, kind: str) -> int:
        cur = self._conn.cursor()
        row = cur.execute(
            "SELECT bytes_processed FROM ledger_state WHERE path = ? AND kind = ?;",
            (path, kind),
        ).fetchone()
        return int(row["bytes_processed"]) if row else 0

    def set_ledger_offset(self, path: str, *, kind: str, bytes_processed: int) -> None:
        cur = self._conn.cursor()
        with self._conn:
            cur.execute(
                """
                INSERT INTO ledger_state (path, kind, bytes_processed, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                  kind = excluded.kind,
                  bytes_processed = excluded.bytes_processed,
                  updated_at = excluded.updated_at;
                """,
                (path, kind, int(bytes_processed), _utc_now_iso()),
            )
