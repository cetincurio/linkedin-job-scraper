"""Unit tests for behavior and error handling in JobStorage."""

from __future__ import annotations

import gc
import json

import pytest

from linkedin_scraper.models.job import JobDetail, JobId, JobIdSource
from linkedin_scraper.storage.jobs.storage import JobStorage


class TestJobStorageBehavior:
    async def test_save_job_ids_ledger_write_failure_is_caught(
        self,
        storage: JobStorage,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        async def boom(_jobs: list[JobId]) -> None:
            raise RuntimeError("boom")

        monkeypatch.setattr(storage._ledger, "append_job_ids", boom)
        saved = await storage.save_job_ids([JobId(job_id="x", source=JobIdSource.SEARCH)])
        assert saved == 1

    async def test_mark_job_scraped_ledger_write_failure_is_caught(
        self,
        storage: JobStorage,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        async def boom(_job_id: str) -> None:
            raise RuntimeError("boom")

        monkeypatch.setattr(storage._ledger, "append_job_scrape", boom)
        await storage.mark_job_scraped("x")

    async def test_get_job_ids_self_heals_from_existing_job_detail(
        self,
        storage: JobStorage,
        test_settings,
    ) -> None:
        await storage.save_job_ids([JobId(job_id="heal1", source=JobIdSource.SEARCH)])
        # Create a minimal job detail file; this simulates a Git pull from another machine.
        path = test_settings.job_details_dir / "heal1.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        detail = JobDetail(job_id="heal1")
        path.write_text(json.dumps(detail.model_dump(mode="json")), encoding="utf-8")

        jobs = await storage.get_job_ids(source=JobIdSource.SEARCH, unscraped_only=True)
        assert jobs == []
        assert storage._index.count_unscraped(source=JobIdSource.SEARCH) == 0


def test_job_storage_del_suppresses_close_errors(test_settings) -> None:
    store = JobStorage(test_settings)
    store.close()

    def boom() -> None:
        raise RuntimeError("boom")

    store.close = boom  # type: ignore[method-assign]
    del store
    gc.collect()
