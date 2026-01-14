"""Tests for data models."""

from datetime import datetime

from linkedin_scraper.models.job import JobDetail, JobId, JobIdSource, JobSearchResult


class TestJobId:
    """Tests for JobId model."""

    def test_create_job_id(self) -> None:
        """Test creating a basic JobId."""
        job = JobId(job_id="123456", source=JobIdSource.SEARCH)

        assert job.job_id == "123456"
        assert job.source == JobIdSource.SEARCH
        assert job.scraped is False
        assert isinstance(job.discovered_at, datetime)

    def test_job_id_with_metadata(self) -> None:
        """Test JobId with search metadata."""
        job = JobId(
            job_id="789012",
            source=JobIdSource.SEARCH,
            search_keyword="python",
            search_country="germany",
        )

        assert job.search_keyword == "python"
        assert job.search_country == "germany"

    def test_job_id_recommended_source(self) -> None:
        """Test JobId from recommendations."""
        job = JobId(
            job_id="345678",
            source=JobIdSource.RECOMMENDED,
            parent_job_id="123456",
        )

        assert job.source == JobIdSource.RECOMMENDED
        assert job.parent_job_id == "123456"

    def test_job_id_equality(self) -> None:
        """Test JobId equality based on job_id."""
        job1 = JobId(job_id="123", source=JobIdSource.SEARCH)
        job2 = JobId(job_id="123", source=JobIdSource.RECOMMENDED)
        job3 = JobId(job_id="456", source=JobIdSource.SEARCH)

        assert job1 == job2  # Same job_id
        assert job1 != job3  # Different job_id

    def test_job_id_hash(self) -> None:
        """Test JobId hashing for set operations."""
        job1 = JobId(job_id="123", source=JobIdSource.SEARCH)
        job2 = JobId(job_id="123", source=JobIdSource.RECOMMENDED)

        job_set = {job1, job2}
        assert len(job_set) == 1  # Same job_id = same hash


class TestJobDetail:
    """Tests for JobDetail model."""

    def test_create_minimal_detail(self) -> None:
        """Test creating JobDetail with minimal data."""
        detail = JobDetail(job_id="123456")

        assert detail.job_id == "123456"
        assert detail.title is None
        assert detail.company_name is None
        assert detail.skills == []

    def test_create_full_detail(self) -> None:
        """Test creating JobDetail with full data."""
        detail = JobDetail(
            job_id="123456",
            title="Senior Python Developer",
            company_name="TechCorp",
            location="Berlin, Germany",
            workplace_type="Hybrid",
            employment_type="Full-time",
            seniority_level="Mid-Senior level",
            description="Build amazing things",
            skills=["Python", "Django", "PostgreSQL"],
        )

        assert detail.title == "Senior Python Developer"
        assert detail.company_name == "TechCorp"
        assert len(detail.skills) == 3
        assert "Python" in detail.skills


class TestJobSearchResult:
    """Tests for JobSearchResult model."""

    def test_create_search_result(self) -> None:
        """Test creating a search result."""
        result = JobSearchResult(
            keyword="python developer",
            country="Germany",
            total_found=42,
            job_ids=["1", "2", "3"],
            pages_scraped=5,
        )

        assert result.keyword == "python developer"
        assert result.total_found == 42
        assert len(result.job_ids) == 3
        assert result.pages_scraped == 5

    def test_empty_search_result(self) -> None:
        """Test search result with no results."""
        result = JobSearchResult(keyword="nonexistent", country="nowhere")

        assert result.total_found == 0
        assert result.job_ids == []
        assert result.pages_scraped == 0
