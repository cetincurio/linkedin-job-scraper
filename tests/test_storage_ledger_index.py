"""Unit tests for ledger + index storage (option 2)."""

from __future__ import annotations

import gc
import json
from pathlib import Path

import pytest

from linkedin_scraper.models.job import JobDetail, JobId, JobIdSource
from linkedin_scraper.storage.jobs.index import JobIndex
from linkedin_scraper.storage.jobs.ledger import LedgerWriter
from linkedin_scraper.storage.jobs.storage import JobStorage


class TestLedgerWriter:
    async def test_writes_and_exposes_paths(self, tmp_path: Path) -> None:
        writer = LedgerWriter(
            job_ids_path=tmp_path / "job_ids.jsonl",
            job_scrapes_path=tmp_path / "job_scrapes.jsonl",
        )

        assert writer.job_ids_path == tmp_path / "job_ids.jsonl"
        assert writer.job_scrapes_path == tmp_path / "job_scrapes.jsonl"

        # No-op branch
        await writer.append_job_ids([])

        job = JobId(job_id="1", source=JobIdSource.SEARCH)
        await writer.append_job_ids([job])

        text = (tmp_path / "job_ids.jsonl").read_text(encoding="utf-8")
        assert '"job_id"' in text
        assert '"scraped"' not in text  # excluded on purpose

        await writer.append_job_scrape("1")
        scrape_text = (tmp_path / "job_scrapes.jsonl").read_text(encoding="utf-8")
        assert '"job_id"' in scrape_text
        assert '"scraped_at"' in scrape_text


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


class TestJobStorageLedgers:
    def test_ingest_ledger_dir_missing_is_noop(self, storage: JobStorage, tmp_path: Path) -> None:
        storage._ingest_ledger_dir(tmp_path / "does_not_exist", kind="job_ids")

    def test_ingest_ledger_dir_catches_exceptions(
        self,
        storage: JobStorage,
        test_settings,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        ledger_dir = test_settings.ledger_job_ids_dir
        ledger_dir.mkdir(parents=True, exist_ok=True)
        (ledger_dir / "a.jsonl").write_text("{}", encoding="utf-8")

        def boom(*_args, **_kwargs) -> None:
            raise RuntimeError("boom")

        monkeypatch.setattr(storage, "_ingest_ledger_file", boom)
        storage._ingest_ledger_dir(ledger_dir, kind="job_ids")

    def test_ingest_ledger_file_file_not_found_is_noop(
        self, storage: JobStorage, tmp_path: Path
    ) -> None:
        storage._ingest_ledger_file(tmp_path / "missing.jsonl", kind="job_ids")

    def test_ingest_ledger_file_offset_out_of_bounds_resets_and_ingests(
        self,
        test_settings,
    ) -> None:
        # Create storage first (so init doesn't ingest our file), then create the ledger file.
        store = JobStorage(test_settings)
        try:
            ledger_path = test_settings.ledger_job_ids_dir / "external.jsonl"
            ledger_path.parent.mkdir(parents=True, exist_ok=True)
            ledger_path.write_text(
                json.dumps(
                    {
                        "job_id": "100",
                        "source": "search",
                        "search_keyword": "k",
                        "search_country": "NL",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            store._index.set_ledger_offset(str(ledger_path), kind="job_ids", bytes_processed=999999)
            store._ingest_ledger_file(ledger_path, kind="job_ids")

            jobs = store._index.list_job_ids(source=JobIdSource.SEARCH)
            assert [j.job_id for j in jobs] == ["100"]

            # size==offset early-return branch
            store._ingest_ledger_file(ledger_path, kind="job_ids")
        finally:
            store.close()

    def test_ingest_ledger_file_without_newline_is_ignored(self, test_settings) -> None:
        store = JobStorage(test_settings)
        try:
            ledger_path = test_settings.ledger_job_ids_dir / "partial.jsonl"
            ledger_path.write_text(
                json.dumps({"job_id": "no_nl", "source": "search"}),
                encoding="utf-8",
            )
            store._ingest_ledger_file(ledger_path, kind="job_ids")
            assert store._index.list_job_ids(source=JobIdSource.SEARCH) == []
        finally:
            store.close()

    def test_ingest_ledger_file_unknown_kind_raises(self, test_settings) -> None:
        store = JobStorage(test_settings)
        try:
            ledger_path = test_settings.ledger_job_ids_dir / "k.jsonl"
            ledger_path.write_text(
                json.dumps({"job_id": "1", "source": "search"}) + "\n", encoding="utf-8"
            )
            with pytest.raises(ValueError):
                store._ingest_ledger_file(ledger_path, kind="nope")
        finally:
            store.close()

    def test_ingest_job_ids_lines_skips_bad_lines_and_flushes(self, test_settings) -> None:
        store = JobStorage(test_settings)
        try:
            # Cover: blank line, invalid JSON, non-object JSON, invalid record.
            store._ingest_job_ids_lines(
                [
                    b"",
                    b"{",
                    b"[]",
                    b"{}",
                ],
                path=Path("memory.jsonl"),
            )

            # Cover flush path (>=1000) and the `if jobs:` false branch afterwards.
            lines = [
                json.dumps({"job_id": str(i), "source": "search"}).encode("utf-8")
                for i in range(1000)
            ]
            store._ingest_job_ids_lines(lines, path=Path("memory.jsonl"))

            assert store._index.count_job_ids(source=JobIdSource.SEARCH) == 1000

            # Cover the `if jobs:` true branch.
            store._ingest_job_ids_lines(
                [json.dumps({"job_id": "1000", "source": "search"}).encode("utf-8")],
                path=Path("memory.jsonl"),
            )
            assert store._index.count_job_ids(source=JobIdSource.SEARCH) == 1001
        finally:
            store.close()

    def test_ingest_job_scrape_lines_skips_and_flushes(self, test_settings) -> None:
        store = JobStorage(test_settings)
        try:
            # Insert a job to observe scrape-marking.
            store._index.insert_job_ids([JobId(job_id="s", source=JobIdSource.SEARCH)])
            assert store._index.count_unscraped(source=JobIdSource.SEARCH) == 1

            store._ingest_job_scrape_lines(
                [
                    b"",
                    b"{",
                    json.dumps([]).encode("utf-8"),  # non-dict JSON line
                    json.dumps({"job_id": 123}).encode("utf-8"),
                    json.dumps({"job_id": "s"}).encode("utf-8"),
                ],
                path=Path("scrapes.jsonl"),
            )
            assert store._index.count_unscraped(source=JobIdSource.SEARCH) == 0

            # Flush path (>=2000) plus end-of-loop empty branch.
            many = [json.dumps({"job_id": f"x{i}"}).encode("utf-8") for i in range(2000)]
            store._ingest_job_scrape_lines(many, path=Path("scrapes.jsonl"))
        finally:
            store.close()

    def test_ingest_ledger_file_job_scrapes_kind(self, test_settings) -> None:
        store = JobStorage(test_settings)
        try:
            ledger_path = test_settings.ledger_job_scrapes_dir / "scrapes.jsonl"
            ledger_path.parent.mkdir(parents=True, exist_ok=True)
            ledger_path.write_text(json.dumps({"job_id": "s"}) + "\n", encoding="utf-8")

            store._ingest_ledger_file(ledger_path, kind="job_scrapes")
        finally:
            store.close()


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
