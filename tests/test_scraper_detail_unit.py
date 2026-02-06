"""Unit tests for JobDetailScraper using fake Playwright objects."""

from __future__ import annotations

from typing import Any, cast

import pytest
from playwright.async_api import Page

import linkedin_scraper.scrapers.base as base_module
from linkedin_scraper.browser.context import BrowserManager
from linkedin_scraper.browser.human import HumanBehavior
from linkedin_scraper.models.job import JobDetail, JobId, JobIdSource
from linkedin_scraper.scrapers.detail import JobDetailScraper
from linkedin_scraper.storage.jobs import JobStorage
from tests.test_fakes import FakeBrowserManager, FakeHuman, FakePage, settings_for_tests


@pytest.mark.asyncio
async def test_job_detail_run_respects_limit_and_saves_detail(monkeypatch, tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    storage = JobStorage(settings)
    scraper = JobDetailScraper(settings=settings, storage=storage)

    page = FakePage()
    scraper._browser_manager = cast(BrowserManager, FakeBrowserManager(page, FakeHuman()))

    async def _fake_scrape_job_detail(_page: Any, _human: Any, job_id: str) -> JobDetail:
        return JobDetail(job_id=job_id, title="t", company_name="c", location="l")

    async def _fake_recommended(*_args: Any, **_kwargs: Any) -> list[str]:
        return ["999"]

    monkeypatch.setattr(scraper, "_scrape_job_detail", _fake_scrape_job_detail)
    monkeypatch.setattr(scraper._recommended_scraper, "extract_from_page", _fake_recommended)

    details = await scraper.run(job_ids=["101", "202"], limit=1, extract_recommended=True)
    assert [d.job_id for d in details] == ["101"]

    assert (settings.job_details_dir / "101.json").exists()


@pytest.mark.asyncio
async def test_job_detail_run_extract_recommended_true_with_no_results(
    monkeypatch, tmp_path
) -> None:
    settings = settings_for_tests(tmp_path)
    storage = JobStorage(settings)
    scraper = JobDetailScraper(settings=settings, storage=storage)

    page = FakePage()
    scraper._browser_manager = cast(BrowserManager, FakeBrowserManager(page, FakeHuman()))

    async def _fake_scrape_job_detail(_page: Any, _human: Any, job_id: str) -> JobDetail:
        return JobDetail(job_id=job_id, title="t")

    async def _none(*_args: Any, **_kwargs: Any) -> list[str]:
        return []

    monkeypatch.setattr(scraper, "_scrape_job_detail", _fake_scrape_job_detail)
    monkeypatch.setattr(scraper._recommended_scraper, "extract_from_page", _none)

    out = await scraper.run(job_ids=["101"], extract_recommended=True)
    assert [d.job_id for d in out] == ["101"]


@pytest.mark.asyncio
async def test_job_detail_run_loads_unscraped_ids_from_storage(monkeypatch, tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    storage = JobStorage(settings)
    await storage.save_job_ids(
        [
            JobId(job_id="101", source=JobIdSource.SEARCH, scraped=False),
            JobId(job_id="202", source=JobIdSource.SEARCH, scraped=False),
        ]
    )

    scraper = JobDetailScraper(settings=settings, storage=storage)
    scraper._browser_manager = cast(BrowserManager, FakeBrowserManager(FakePage(), FakeHuman()))

    async def _fake_scrape_job_detail(_page: Any, _human: Any, job_id: str) -> JobDetail:
        return JobDetail(job_id=job_id, title="t")

    monkeypatch.setattr(scraper, "_scrape_job_detail", _fake_scrape_job_detail)
    out = await scraper.run(job_ids=None, limit=1, extract_recommended=False)
    assert [d.job_id for d in out] == ["101"]


@pytest.mark.asyncio
async def test_job_detail_run_continues_when_scrape_returns_none(monkeypatch, tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    storage = JobStorage(settings)
    scraper = JobDetailScraper(settings=settings, storage=storage)

    class _Human(FakeHuman):
        def __init__(self) -> None:
            super().__init__()
            self.delays = 0

        async def random_delay(self, *_a: Any, **_k: Any) -> None:
            self.delays += 1

    human = _Human()
    scraper._browser_manager = cast(BrowserManager, FakeBrowserManager(FakePage(), human))

    async def _none(*_a: Any, **_k: Any) -> Any:
        return None

    monkeypatch.setattr(scraper, "_scrape_job_detail", _none)
    out = await scraper.run(job_ids=["101"], extract_recommended=False)
    assert out == []
    assert human.delays == 1


@pytest.mark.asyncio
async def test_job_detail_run_returns_empty_when_no_job_ids(tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    storage = JobStorage(settings)
    scraper = JobDetailScraper(settings=settings, storage=storage)
    out = await scraper.run(job_ids=[])
    assert out == []


@pytest.mark.asyncio
async def test_job_detail_run_skips_if_already_scraped(monkeypatch, tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    storage = JobStorage(settings)
    await storage.save_job_detail(JobDetail(job_id="101", title="t"))

    scraper = JobDetailScraper(settings=settings, storage=storage)
    scraper._browser_manager = cast(BrowserManager, FakeBrowserManager(FakePage(), FakeHuman()))

    async def _boom(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("should not be called")

    monkeypatch.setattr(scraper, "_scrape_job_detail", _boom)
    out = await scraper.run(job_ids=["101"], extract_recommended=False)
    assert out == []


@pytest.mark.asyncio
async def test_job_detail_run_handles_scrape_errors_and_screenshots(monkeypatch, tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    storage = JobStorage(settings)
    scraper = JobDetailScraper(settings=settings, storage=storage)
    page = FakePage()
    scraper._browser_manager = cast(BrowserManager, FakeBrowserManager(page, FakeHuman()))

    async def _boom(*_a: Any, **_k: Any) -> Any:
        raise RuntimeError("boom")

    shots: list[str] = []

    async def _shot(_page: Any, name: str) -> None:
        shots.append(name)

    monkeypatch.setattr(scraper, "_scrape_job_detail", _boom)
    monkeypatch.setattr(scraper, "_take_debug_screenshot", _shot)

    out = await scraper.run(job_ids=["101"], extract_recommended=False)
    assert out == []
    assert shots and shots[0].startswith("error_101")


@pytest.mark.asyncio
async def test_job_detail_scrape_job_detail_returns_none_when_safe_goto_fails(
    monkeypatch, tmp_path
) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = JobDetailScraper(settings=settings, storage=JobStorage(settings))

    async def _nope(*_a: Any, **_k: Any) -> bool:
        return False

    monkeypatch.setattr(scraper, "_safe_goto", _nope)
    detail = await scraper._scrape_job_detail(
        cast(Page, FakePage()), cast(HumanBehavior, FakeHuman()), "1"
    )
    assert detail is None


@pytest.mark.asyncio
async def test_job_detail_scrape_job_detail_returns_none_when_content_missing(
    monkeypatch, tmp_path
) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = JobDetailScraper(settings=settings, storage=JobStorage(settings))
    page = FakePage()

    async def _ok(*_a: Any, **_k: Any) -> bool:
        return True

    async def _no_content(*_a: Any, **_k: Any) -> bool:
        return False

    shots: list[str] = []

    async def _shot(_page: Any, name: str) -> None:
        shots.append(name)

    monkeypatch.setattr(scraper, "_safe_goto", _ok)
    monkeypatch.setattr(base_module, "time", base_module.time)
    monkeypatch.setattr(
        "linkedin_scraper.scrapers.detail.scraper.wait_for_job_content", _no_content
    )
    monkeypatch.setattr(scraper, "_take_debug_screenshot", _shot)

    out = await scraper._scrape_job_detail(cast(Page, page), cast(HumanBehavior, FakeHuman()), "1")
    assert out is None
    assert shots == ["no_content_1"]


@pytest.mark.asyncio
async def test_job_detail_scrape_job_detail_success_sets_fields(monkeypatch, tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = JobDetailScraper(settings=settings, storage=JobStorage(settings))
    page = FakePage()

    async def _ok(*_a: Any, **_k: Any) -> bool:
        return True

    async def _loaded(*_a: Any, **_k: Any) -> bool:
        return True

    async def _noop_read(*_a: Any, **_k: Any) -> None:
        pass

    monkeypatch.setattr(scraper, "_safe_goto", _ok)
    monkeypatch.setattr("linkedin_scraper.scrapers.detail.scraper.wait_for_job_content", _loaded)
    monkeypatch.setattr(FakeHuman, "simulate_reading", _noop_read, raising=False)

    async def _title(*_a: Any, **_k: Any) -> str:
        return "t"

    async def _company(*_a: Any, **_k: Any) -> str:
        return "c"

    async def _loc(*_a: Any, **_k: Any) -> str:
        return "l"

    async def _wt(*_a: Any, **_k: Any) -> str:
        return "Remote"

    async def _criteria(*_a: Any, **_k: Any) -> dict[str, str | None]:
        return {
            "employment_type": "Full-time",
            "seniority_level": "Senior",
            "industry": "Software",
            "job_function": "Engineering",
        }

    async def _desc(*_a: Any, **_k: Any) -> str:
        return "d"

    async def _posted(*_a: Any, **_k: Any) -> str:
        return "today"

    async def _apps(*_a: Any, **_k: Any) -> str:
        return "10 applicants"

    async def _salary(*_a: Any, **_k: Any) -> str:
        return "$1"

    async def _skills(*_a: Any, **_k: Any) -> list[str]:
        return ["Python"]

    async def _raw(*_a: Any, **_k: Any) -> dict[str, Any]:
        return {"x": "y"}

    monkeypatch.setattr("linkedin_scraper.scrapers.detail.scraper.extract_title", _title)
    monkeypatch.setattr("linkedin_scraper.scrapers.detail.scraper.extract_company", _company)
    monkeypatch.setattr("linkedin_scraper.scrapers.detail.scraper.extract_location", _loc)
    monkeypatch.setattr("linkedin_scraper.scrapers.detail.scraper.extract_workplace_type", _wt)
    monkeypatch.setattr("linkedin_scraper.scrapers.detail.scraper.extract_job_criteria", _criteria)
    monkeypatch.setattr("linkedin_scraper.scrapers.detail.scraper.extract_description", _desc)
    monkeypatch.setattr("linkedin_scraper.scrapers.detail.scraper.extract_posted_date", _posted)
    monkeypatch.setattr("linkedin_scraper.scrapers.detail.scraper.extract_applicant_count", _apps)
    monkeypatch.setattr("linkedin_scraper.scrapers.detail.scraper.extract_salary", _salary)
    monkeypatch.setattr("linkedin_scraper.scrapers.detail.scraper.extract_skills", _skills)
    monkeypatch.setattr("linkedin_scraper.scrapers.detail.scraper.extract_raw_sections", _raw)

    out = await scraper._scrape_job_detail(cast(Page, page), cast(HumanBehavior, FakeHuman()), "1")
    assert out is not None
    assert out.title == "t"
    assert out.company_name == "c"
    assert out.location == "l"
    assert out.skills == ["Python"]
