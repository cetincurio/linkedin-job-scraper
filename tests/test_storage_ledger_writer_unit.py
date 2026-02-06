"""Unit tests for the append-only JSONL ledger writer."""

from __future__ import annotations

from pathlib import Path

from linkedin_scraper.models.job import JobId, JobIdSource
from linkedin_scraper.storage.jobs.ledger import LedgerWriter


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
