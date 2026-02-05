"""Pydantic models for job data."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


__all__ = [
    "JobDetail",
    "JobId",
    "JobIdSource",
    "JobSearchResult",
    "ScrapingSession",
]


class JobIdSource(StrEnum):
    """Source of the job ID."""

    SEARCH = "search"
    RECOMMENDED = "recommended"
    MANUAL = "manual"


class JobId(BaseModel):
    """A LinkedIn job ID with metadata."""

    job_id: str = Field(description="LinkedIn job ID")
    source: JobIdSource = Field(description="How this job ID was discovered")
    discovered_at: datetime = Field(default_factory=datetime.now)
    search_keyword: str | None = Field(default=None, description="Search keyword if from search")
    search_country: str | None = Field(default=None, description="Country filter if from search")
    parent_job_id: str | None = Field(
        default=None, description="Parent job ID if from recommendations"
    )
    scraped: bool = Field(default=False, description="Whether details have been scraped")

    def __hash__(self) -> int:
        return hash(self.job_id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, JobId):
            return self.job_id == other.job_id
        return False


class JobDetail(BaseModel):
    """Detailed job information scraped from a job page."""

    job_id: str = Field(description="LinkedIn job ID")
    scraped_at: datetime = Field(default_factory=datetime.now)

    # Basic info
    title: str | None = Field(default=None)
    company_name: str | None = Field(default=None)
    location: str | None = Field(default=None)
    workplace_type: str | None = Field(default=None, description="Remote, Hybrid, On-site")

    # Job details
    employment_type: str | None = Field(default=None, description="Full-time, Part-time, etc.")
    seniority_level: str | None = Field(default=None)
    industry: str | None = Field(default=None)
    job_function: str | None = Field(default=None)

    # Description
    description: str | None = Field(default=None)

    # Metadata
    posted_date: str | None = Field(default=None)
    applicant_count: str | None = Field(default=None)
    salary_range: str | None = Field(default=None)

    # Skills
    skills: list[str] = Field(default_factory=list)

    # Raw data for debugging
    raw_sections: dict[str, Any] = Field(default_factory=dict)


class JobSearchResult(BaseModel):
    """Result from a job search operation."""

    keyword: str
    country: str
    total_found: int = Field(default=0)
    job_ids: list[str] = Field(default_factory=list)
    pages_scraped: int = Field(default=0)
    search_timestamp: datetime = Field(default_factory=datetime.now)


class ScrapingSession(BaseModel):
    """Metadata for a scraping session."""

    session_id: str
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: datetime | None = Field(default=None)
    jobs_found: int = Field(default=0)
    jobs_scraped: int = Field(default=0)
    recommended_found: int = Field(default=0)
    errors: list[str] = Field(default_factory=list)
