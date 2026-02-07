"""Small validation/guardrail tests for scraper inputs."""

from __future__ import annotations

import pytest

from ljs.scrapers.detail import JobDetailScraper
from ljs.scrapers.recommended import RecommendedJobsScraper
from ljs.scrapers.search import JobSearchScraper
from ljs.storage.jobs import JobStorage
from tests.test_fakes import settings_for_tests


@pytest.mark.asyncio
async def test_invalid_limits_raise(tmp_path) -> None:
    settings = settings_for_tests(tmp_path)

    search = JobSearchScraper(settings=settings, storage=JobStorage(settings))
    with pytest.raises(ValueError):
        await search.run(keyword="x", country="germany", max_pages=0)

    detail = JobDetailScraper(settings=settings, storage=JobStorage(settings))
    with pytest.raises(ValueError):
        await detail.run(job_ids=["1"], limit=0)

    recommended = RecommendedJobsScraper(settings=settings, storage=JobStorage(settings))
    with pytest.raises(ValueError):
        await recommended.run(parent_job_ids=["1"], limit=0)


@pytest.mark.asyncio
async def test_invalid_job_id_inputs_raise(tmp_path) -> None:
    settings = settings_for_tests(tmp_path)

    detail = JobDetailScraper(settings=settings, storage=JobStorage(settings))
    with pytest.raises(ValueError):
        await detail.run(job_ids="1")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        await detail.run(job_ids=[1])  # type: ignore[list-item]

    recommended = RecommendedJobsScraper(settings=settings, storage=JobStorage(settings))
    with pytest.raises(ValueError):
        await recommended.run(parent_job_ids="1")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        await recommended.run(parent_job_ids=[1])  # type: ignore[list-item]
