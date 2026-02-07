"""Tests for scraper modules."""

from ljs.scrapers.base import BaseScraper


class TestBaseScraper:
    """Tests for BaseScraper utility methods."""

    def test_extract_job_id_from_url_view(self) -> None:
        """Test extracting job ID from /jobs/view/ URL."""
        url = "https://www.linkedin.com/jobs/view/1234567890/"
        job_id = BaseScraper.extract_job_id_from_url(url)
        assert job_id == "1234567890"

    def test_extract_job_id_from_url_with_params(self) -> None:
        """Test extracting job ID from URL with query params."""
        url = "https://www.linkedin.com/jobs/view/1234567890?refId=abc"
        job_id = BaseScraper.extract_job_id_from_url(url)
        assert job_id == "1234567890"

    def test_extract_job_id_from_current_job_param(self) -> None:
        """Test extracting job ID from currentJobId parameter."""
        url = "https://www.linkedin.com/jobs/search?currentJobId=9876543210"
        job_id = BaseScraper.extract_job_id_from_url(url)
        assert job_id == "9876543210"

    def test_extract_job_id_no_match(self) -> None:
        """Test URL without job ID returns None."""
        url = "https://www.linkedin.com/feed/"
        job_id = BaseScraper.extract_job_id_from_url(url)
        assert job_id is None

    def test_extract_job_ids_from_html(self, sample_html_with_jobs: str) -> None:
        """Test extracting multiple job IDs from HTML."""
        job_ids = BaseScraper.extract_job_ids_from_html(sample_html_with_jobs)

        assert "1234567890" in job_ids
        assert "2345678901" in job_ids
        assert "3456789012" in job_ids
        assert len(job_ids) == 3

    def test_extract_job_ids_from_empty_html(self) -> None:
        """Test extracting from HTML with no job IDs."""
        html = "<html><body>No jobs here</body></html>"
        job_ids = BaseScraper.extract_job_ids_from_html(html)
        assert job_ids == []

    def test_extract_job_ids_data_entity_urn(self) -> None:
        """Test extracting from data-entity-urn attribute."""
        html = '<div data-entity-urn="urn:li:jobPosting:5555555555">Job</div>'
        job_ids = BaseScraper.extract_job_ids_from_html(html)
        assert "5555555555" in job_ids
