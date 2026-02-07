"""Tests for storage module."""

import hashlib
import json

import pytest

from ljs.config import Settings
from ljs.models.job import JobDetail, JobId, JobIdSource
from ljs.storage.jobs import JobStorage


class TestJobStorage:
    """Tests for JobStorage."""

    async def test_save_and_retrieve_job_id(self, storage: JobStorage) -> None:
        """Test saving and retrieving a job ID."""
        job = JobId(
            job_id="test123",
            source=JobIdSource.SEARCH,
            search_keyword="python",
            search_country="germany",
        )

        await storage.save_job_id(job)
        retrieved = await storage.get_job_ids(source=JobIdSource.SEARCH)

        assert len(retrieved) == 1
        assert retrieved[0].job_id == "test123"
        assert retrieved[0].search_keyword == "python"

    async def test_save_multiple_job_ids(self, storage: JobStorage) -> None:
        """Test saving multiple job IDs at once."""
        jobs = [JobId(job_id=f"job{i}", source=JobIdSource.SEARCH) for i in range(5)]

        saved_count = await storage.save_job_ids(jobs)
        assert saved_count == 5

        retrieved = await storage.get_job_ids(source=JobIdSource.SEARCH)
        assert len(retrieved) == 5

    async def test_no_duplicate_job_ids(self, storage: JobStorage) -> None:
        """Test that duplicate job IDs are not saved."""
        job = JobId(job_id="duplicate123", source=JobIdSource.SEARCH)

        await storage.save_job_id(job)
        await storage.save_job_id(job)  # Try saving again

        retrieved = await storage.get_job_ids(source=JobIdSource.SEARCH)
        assert len(retrieved) == 1

    async def test_save_job_ids_empty_list_returns_zero(self, storage: JobStorage) -> None:
        """Test saving an empty list of job IDs."""
        saved_count = await storage.save_job_ids([])
        assert saved_count == 0

    async def test_save_job_ids_skips_existing_for_source(self, storage: JobStorage) -> None:
        """Test save_job_ids does not re-save duplicates for a source."""
        job = JobId(job_id="dup-source", source=JobIdSource.SEARCH)
        await storage.save_job_id(job)

        saved_count = await storage.save_job_ids([job])
        assert saved_count == 0

    async def test_filter_unscraped_jobs(self, storage: JobStorage) -> None:
        """Test filtering for unscraped job IDs."""
        jobs = [
            JobId(job_id="scraped1", source=JobIdSource.SEARCH, scraped=True),
            JobId(job_id="unscraped1", source=JobIdSource.SEARCH, scraped=False),
            JobId(job_id="unscraped2", source=JobIdSource.SEARCH, scraped=False),
        ]

        await storage.save_job_ids(jobs)

        all_jobs = await storage.get_job_ids(source=JobIdSource.SEARCH)
        unscraped = await storage.get_job_ids(source=JobIdSource.SEARCH, unscraped_only=True)

        assert len(all_jobs) == 3
        assert len(unscraped) == 2

    async def test_mark_job_scraped(self, storage: JobStorage) -> None:
        """Test marking a job as scraped."""
        job = JobId(job_id="tomark123", source=JobIdSource.SEARCH)
        await storage.save_job_id(job)

        await storage.mark_job_scraped("tomark123")

        unscraped = await storage.get_job_ids(source=JobIdSource.SEARCH, unscraped_only=True)
        assert len(unscraped) == 0

    async def test_mark_job_scraped_missing_job_is_noop(self, storage: JobStorage) -> None:
        """Test marking a missing job ID does nothing."""
        await storage.mark_job_scraped("missing")
        all_jobs = await storage.get_job_ids(source=JobIdSource.SEARCH)
        assert all_jobs == []

    async def test_mark_job_scraped_skips_already_scraped(self, storage: JobStorage) -> None:
        """Test marking an already scraped job does not change it."""
        job = JobId(job_id="already", source=JobIdSource.SEARCH, scraped=True)
        await storage.save_job_id(job)

        await storage.mark_job_scraped("already")
        jobs = await storage.get_job_ids(source=JobIdSource.SEARCH)
        assert jobs[0].scraped is True

    async def test_save_and_retrieve_job_detail(self, storage: JobStorage) -> None:
        """Test saving and retrieving job details."""
        detail = JobDetail(
            job_id="detail123",
            title="Software Engineer",
            company_name="TechCorp",
            location="Berlin",
            skills=["Python", "Django"],
        )

        await storage.save_job_detail(detail)
        retrieved = await storage.get_job_detail("detail123")

        assert retrieved is not None
        assert retrieved.title == "Software Engineer"
        assert retrieved.company_name == "TechCorp"
        assert len(retrieved.skills) == 2

    async def test_job_detail_not_found(self, storage: JobStorage) -> None:
        """Test retrieving non-existent job detail."""
        retrieved = await storage.get_job_detail("nonexistent")
        assert retrieved is None

    async def test_job_detail_invalid_json_returns_none(
        self, storage: JobStorage, test_settings: Settings
    ) -> None:
        """Test retrieving a job detail with invalid JSON."""
        bad_path = test_settings.job_details_dir / "bad.json"
        bad_path.parent.mkdir(parents=True, exist_ok=True)
        bad_path.write_text("{not json", encoding="utf-8")

        retrieved = await storage.get_job_detail("bad")
        assert retrieved is None

    async def test_job_detail_exists(self, storage: JobStorage) -> None:
        """Test checking if job detail exists."""
        detail = JobDetail(job_id="exists123", title="Test Job")
        await storage.save_job_detail(detail)

        assert await storage.job_detail_exists("exists123") is True
        assert await storage.job_detail_exists("notexists") is False

    async def test_get_stats(self, storage: JobStorage) -> None:
        """Test getting storage statistics."""
        # Add some test data
        search_jobs = [JobId(job_id=f"search{i}", source=JobIdSource.SEARCH) for i in range(3)]
        recommended_jobs = [
            JobId(job_id=f"rec{i}", source=JobIdSource.RECOMMENDED) for i in range(2)
        ]

        await storage.save_job_ids(search_jobs)
        await storage.save_job_ids(recommended_jobs)

        detail = JobDetail(job_id="detail1", title="Test")
        await storage.save_job_detail(detail)

        stats = await storage.get_stats()

        assert stats["search_job_ids"] == 3
        assert stats["recommended_job_ids"] == 2
        assert stats["job_details"] == 1

    async def test_get_job_ids_invalid_json_returns_empty(
        self, storage: JobStorage, test_settings: Settings
    ) -> None:
        """Test invalid job ID JSON is handled gracefully."""
        bad_path = test_settings.job_ids_dir / "search_job_ids.json"
        bad_path.parent.mkdir(parents=True, exist_ok=True)
        bad_path.write_text("{bad json", encoding="utf-8")

        jobs = await storage.get_job_ids(source=JobIdSource.SEARCH)
        assert jobs == []

    async def test_get_job_ids_all_sources(self, storage: JobStorage) -> None:
        """Test retrieving job IDs across all sources."""
        await storage.save_job_ids(
            [
                JobId(job_id="s1", source=JobIdSource.SEARCH),
                JobId(job_id="r1", source=JobIdSource.RECOMMENDED),
            ]
        )

        jobs = await storage.get_job_ids()
        assert {job.job_id for job in jobs} == {"s1", "r1"}

    async def test_export_job_details_jsonl_creates_dataset_and_manifest(
        self,
        storage: JobStorage,
        test_settings: Settings,
    ) -> None:
        await storage.save_job_detail(
            JobDetail(
                job_id="detail_email",
                title="Engineer",
                company_name="Acme",
                location="Berlin",
                description="Please email hr@example.com for details.",
            )
        )
        await storage.save_job_detail(
            JobDetail(
                job_id="detail_phone",
                title="Analyst",
                company_name="Beta",
                location="London",
                description="Call +1 (555) 123-4567 to apply.",
            )
        )

        output_path = test_settings.data_dir / "datasets" / "job_details.jsonl"
        manifest = await storage.export_job_details_jsonl(
            output_path=output_path,
            redact_pii=True,
            include_raw_sections=False,
        )

        assert output_path.exists() is True
        assert output_path.with_suffix(".manifest.json").exists() is True
        assert manifest["record_count"] == 2
        assert manifest["sha256"] == hashlib.sha256(output_path.read_bytes()).hexdigest()

        records = [
            json.loads(line)
            for line in output_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        by_id = {r["job_id"]: r for r in records}
        assert set(by_id.keys()) == {"detail_email", "detail_phone"}

        email_rec = by_id["detail_email"]
        assert email_rec["schema_version"] == "linkedin-job-scraper.job_detail.v1"
        assert email_rec["source_url"].endswith("/detail_email/")
        assert "raw_sections" not in email_rec
        assert "hr@example.com" not in email_rec["description"]
        assert "[EMAIL]" in email_rec["description"]
        assert "[EMAIL]" in email_rec["text"]

        phone_rec = by_id["detail_phone"]
        assert "raw_sections" not in phone_rec
        assert "[PHONE]" in phone_rec["description"]
        assert "[PHONE]" in phone_rec["text"]

    async def test_export_job_details_includes_raw_sections_when_enabled(
        self,
        storage: JobStorage,
        test_settings: Settings,
    ) -> None:
        await storage.save_job_detail(
            JobDetail(
                job_id="detail_raw",
                title="Test",
                raw_sections={"section": "value"},
            )
        )

        output_path = test_settings.data_dir / "datasets" / "job_details_with_raw.jsonl"
        await storage.export_job_details_jsonl(
            output_path=output_path,
            include_raw_sections=True,
        )

        records = [
            json.loads(line)
            for line in output_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert len(records) == 1
        assert records[0]["job_id"] == "detail_raw"
        assert records[0]["raw_sections"] == {"section": "value"}

    async def test_export_job_details_respects_limit(
        self,
        storage: JobStorage,
        test_settings: Settings,
    ) -> None:
        for i in range(3):
            await storage.save_job_detail(JobDetail(job_id=f"detail_{i}"))

        output_path = test_settings.data_dir / "datasets" / "job_details_limited.jsonl"
        manifest = await storage.export_job_details_jsonl(output_path=output_path, limit=2)

        assert manifest["record_count"] == 2
        assert len(output_path.read_text(encoding="utf-8").splitlines()) == 2

    async def test_export_job_details_invalid_json_raises(
        self, storage: JobStorage, test_settings: Settings
    ) -> None:
        """Test export raises when encountering invalid job detail JSON."""
        bad_detail = test_settings.job_details_dir / "bad_detail.json"
        bad_detail.parent.mkdir(parents=True, exist_ok=True)
        bad_detail.write_text("{bad json", encoding="utf-8")

        output_path = test_settings.data_dir / "datasets" / "job_details_bad.jsonl"
        with pytest.raises(ValueError):
            await storage.export_job_details_jsonl(output_path=output_path)
