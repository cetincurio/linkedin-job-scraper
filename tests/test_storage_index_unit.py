"""Unit tests for the local SQLite index used by job storage."""

from __future__ import annotations

import gc
from pathlib import Path

from ljs.models.job import JobId, JobIdSource
from ljs.storage.jobs.index import JobIndex


class TestJobIndex:
    def test_smoke_and_branches(self, tmp_path: Path) -> None:
        idx = JobIndex(tmp_path / "job_index.sqlite3")

        assert idx.insert_job_ids([]) == []
        assert idx.mark_jobs_scraped([]) == 0

        assert idx.count_job_ids() == 0
        assert idx.count_job_ids(source=JobIdSource.SEARCH) == 0
        assert idx.count_unscraped(source=JobIdSource.SEARCH) == 0

        assert idx.get_ledger_offset("missing", kind="job_ids") == 0
        idx.set_ledger_offset("missing", kind="job_ids", bytes_processed=12)
        assert idx.get_ledger_offset("missing", kind="job_ids") == 12

        job = JobId(job_id="a", source=JobIdSource.SEARCH, search_keyword="k", search_country="DE")
        inserted = idx.insert_job_ids([job])
        assert inserted == [job]

        rows = idx.list_job_ids(source=JobIdSource.SEARCH)
        assert [r.job_id for r in rows] == ["a"]

        assert idx.count_job_ids() == 1
        assert idx.count_job_ids(source=JobIdSource.SEARCH) == 1
        assert idx.count_unscraped(source=JobIdSource.SEARCH) == 1

        assert idx.mark_job_scraped("a") == 1
        assert idx.count_unscraped(source=JobIdSource.SEARCH) == 0
        assert idx.mark_jobs_scraped(["a"]) == 0

        idx.close()
        del idx
        gc.collect()

        # Cover the defensive exception handling branch in __del__.
        idx2 = JobIndex(tmp_path / "job_index_2.sqlite3")
        idx2._conn.close()

        def boom() -> None:
            raise RuntimeError("boom")

        idx2.close = boom  # type: ignore[method-assign]
        del idx2
        gc.collect()
