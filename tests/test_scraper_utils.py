"""Tests for scraper utility methods (no browser required)."""

from ljs.scrapers.base import BaseScraper
from ljs.scrapers.search import COUNTRY_GEO_IDS


class TestBaseScraperInit:
    """Test BaseScraper initialization."""

    def test_base_scraper_urls(self) -> None:
        """Test base URL constants."""
        assert BaseScraper.LINKEDIN_BASE_URL == "https://www.linkedin.com"
        assert BaseScraper.JOBS_BASE_URL == "https://www.linkedin.com/jobs"


class TestJobIdExtraction:
    """Test job ID extraction utilities."""

    def test_extract_job_id_from_url_standard(self) -> None:
        """Test extracting job ID from standard LinkedIn URL."""
        url = "https://www.linkedin.com/jobs/view/1234567890/"
        result = BaseScraper.extract_job_id_from_url(url)
        assert result == "1234567890"

    def test_extract_job_id_from_url_with_params(self) -> None:
        """Test extracting job ID from URL with query parameters."""
        url = "https://www.linkedin.com/jobs/view/1234567890?refId=abc&trackingId=xyz"
        result = BaseScraper.extract_job_id_from_url(url)
        assert result == "1234567890"

    def test_extract_job_id_from_url_no_trailing_slash(self) -> None:
        """Test extracting job ID from URL without trailing slash."""
        url = "https://www.linkedin.com/jobs/view/9876543210"
        result = BaseScraper.extract_job_id_from_url(url)
        assert result == "9876543210"

    def test_extract_job_id_from_url_invalid(self) -> None:
        """Test that invalid URLs return None."""
        invalid_urls = [
            "https://www.linkedin.com/jobs/",
            "https://www.linkedin.com/in/cetincurio/",
            "https://www.google.com/",
            "",
            "not-a-url",
        ]
        for url in invalid_urls:
            assert BaseScraper.extract_job_id_from_url(url) is None

    def test_extract_job_ids_from_html_single(self) -> None:
        """Test extracting single job ID from HTML."""
        html = '<div data-job-id="123456">Job</div>'
        result = BaseScraper.extract_job_ids_from_html(html)
        assert "123456" in result

    def test_extract_job_ids_from_html_multiple(self) -> None:
        """Test extracting multiple job IDs from HTML."""
        html = """
        <div>
            <a href="/jobs/view/111111/">Job 1</a>
            <a href="/jobs/view/222222/">Job 2</a>
            <a href="/jobs/view/333333/">Job 3</a>
        </div>
        """
        result = BaseScraper.extract_job_ids_from_html(html)
        assert len(result) >= 3
        assert "111111" in result
        assert "222222" in result
        assert "333333" in result

    def test_extract_job_ids_from_html_deduplicates(self) -> None:
        """Test that duplicate job IDs are removed."""
        html = """
        <a href="/jobs/view/123456/">Job</a>
        <a href="/jobs/view/123456/">Same Job</a>
        """
        result = BaseScraper.extract_job_ids_from_html(html)
        # Count occurrences of 123456
        count = result.count("123456")
        assert count == 1

    def test_extract_job_ids_from_html_empty(self) -> None:
        """Test extracting from HTML with no job links."""
        html = "<div>No jobs here</div>"
        result = BaseScraper.extract_job_ids_from_html(html)
        assert len(result) == 0

    def test_extract_job_ids_from_data_attributes(self) -> None:
        """Test extracting job IDs from data attributes."""
        html = """
        <div data-job-id="444444">Job card</div>
        <div data-entity-urn="urn:li:jobPosting:555555">Another card</div>
        """
        result = BaseScraper.extract_job_ids_from_html(html)
        assert "444444" in result
        assert "555555" in result


class TestCountryGeoIds:
    """Test country geo ID mapping."""

    def test_country_geo_ids_import(self) -> None:
        """Test that country geo IDs can be imported."""
        assert len(COUNTRY_GEO_IDS) > 0

    def test_common_countries_exist(self) -> None:
        """Test that common countries are in the mapping."""
        common = ["germany", "us", "uk", "france", "canada"]
        for country in common:
            assert country in COUNTRY_GEO_IDS, f"{country} not found"

    def test_geo_ids_are_numeric_strings(self) -> None:
        """Test that geo IDs are numeric strings."""
        for country, geo_id in COUNTRY_GEO_IDS.items():
            assert geo_id.isdigit(), f"Invalid geo_id for {country}: {geo_id}"
