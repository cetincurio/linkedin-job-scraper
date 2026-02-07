"""Unit tests for RecommendedJobsScraper using fake Playwright objects."""

from __future__ import annotations

from typing import Any, cast

import pytest
from playwright.async_api import Page

from ljs.browser.context import BrowserManager
from ljs.browser.human import HumanBehavior
from ljs.models.job import JobId, JobIdSource
from ljs.scrapers.recommended import RecommendedJobsScraper
from ljs.storage.jobs import JobStorage
from tests.test_fakes import (
    FakeBrowserManager,
    FakeElement,
    FakeHuman,
    FakeLocator,
    FakePage,
    settings_for_tests,
)


@pytest.mark.asyncio
async def test_recommended_extract_from_page_discards_parent_and_sorts(
    monkeypatch, tmp_path
) -> None:
    settings = settings_for_tests(tmp_path)
    storage = JobStorage(settings)
    scraper = RecommendedJobsScraper(settings=settings, storage=storage)

    async def _fixed(_page: Any) -> set[str]:
        return {"200", "100", "123"}  # includes parent ID

    monkeypatch.setattr(scraper, "_extract_similar_jobs", _fixed)
    monkeypatch.setattr(scraper, "_extract_people_also_viewed", _fixed)
    monkeypatch.setattr(scraper, "_extract_more_jobs_at_company", _fixed)
    monkeypatch.setattr(scraper, "_extract_from_sidebar", _fixed)

    page = FakePage()
    human = FakeHuman()
    ids = await scraper.extract_from_page(
        cast(Page, page), cast(HumanBehavior, human), parent_job_id="123"
    )
    assert ids == ["100", "200"]

    saved = await storage.get_job_ids()
    assert any(j.source.value == "recommended" for j in saved)


@pytest.mark.asyncio
async def test_recommended_extract_job_ids_from_selector(tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = RecommendedJobsScraper(settings=settings, storage=JobStorage(settings))

    class _Page(FakePage):
        def locator(self, selector: str) -> FakeLocator:
            _ = selector
            return FakeLocator(
                [
                    FakeElement(href="/jobs/view/1/"),
                    FakeElement(href="/jobs/view/2/"),
                    FakeElement(href="/jobs/view/2/"),
                ]
            )

    page = _Page()
    ids = await scraper._extract_job_ids_from_selector(cast(Page, page), "any")
    assert ids == {"1", "2"}


@pytest.mark.asyncio
async def test_recommended_extract_job_ids_from_selector_skips_missing_and_invalid_hrefs(
    tmp_path,
) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = RecommendedJobsScraper(settings=settings, storage=JobStorage(settings))

    class _Page(FakePage):
        def locator(self, selector: str) -> FakeLocator:
            _ = selector
            return FakeLocator(
                [
                    FakeElement(href=None),
                    FakeElement(href="/jobs/view/not-a-number/"),
                    FakeElement(href="/jobs/view/42/"),
                ]
            )

    out = await scraper._extract_job_ids_from_selector(cast(Page, _Page()), "x")
    assert out == {"42"}


@pytest.mark.asyncio
async def test_recommended_run_uses_scraped_search_ids_and_dedupes(monkeypatch, tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    storage = JobStorage(settings)
    await storage.save_job_ids(
        [
            JobId(job_id="111", source=JobIdSource.SEARCH, scraped=True),
            JobId(job_id="222", source=JobIdSource.SEARCH, scraped=True),
            JobId(job_id="333", source=JobIdSource.SEARCH, scraped=False),
        ]
    )

    scraper = RecommendedJobsScraper(settings=settings, storage=storage)
    page = FakePage()
    scraper._browser_manager = cast(BrowserManager, FakeBrowserManager(page, FakeHuman()))

    async def _fake_extract_from_page(_page: Any, _human: Any, _parent_job_id: str) -> list[str]:
        return ["200", "100", "100"]

    monkeypatch.setattr(scraper, "extract_from_page", _fake_extract_from_page)

    out = await scraper.run(limit=1)
    assert out == ["200", "100"]
    assert len(page.goto_urls) == 1
    assert page.goto_urls[0].startswith("https://www.linkedin.com/jobs/view/")


@pytest.mark.asyncio
async def test_recommended_run_returns_empty_when_no_scraped_search_ids(tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    storage = JobStorage(settings)
    await storage.save_job_ids([JobId(job_id="111", source=JobIdSource.SEARCH, scraped=False)])

    scraper = RecommendedJobsScraper(settings=settings, storage=storage)
    scraper._browser_manager = cast(BrowserManager, FakeBrowserManager(FakePage(), FakeHuman()))
    out = await scraper.run()
    assert out == []


@pytest.mark.asyncio
async def test_recommended_run_skips_extract_when_safe_goto_fails(monkeypatch, tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    storage = JobStorage(settings)
    scraper = RecommendedJobsScraper(settings=settings, storage=storage)
    scraper._browser_manager = cast(BrowserManager, FakeBrowserManager(FakePage(), FakeHuman()))

    async def _nope(*_a: Any, **_k: Any) -> bool:
        return False

    called: list[str] = []

    async def _extract(*_a: Any, **_k: Any) -> list[str]:
        called.append("x")
        return []

    monkeypatch.setattr(scraper, "_safe_goto", _nope)
    monkeypatch.setattr(scraper, "extract_from_page", _extract)

    out = await scraper.run(parent_job_ids=["1"], limit=1)
    assert out == []
    assert called == []


@pytest.mark.asyncio
async def test_recommended_section_extractors_call_selector_helper(monkeypatch, tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = RecommendedJobsScraper(settings=settings, storage=JobStorage(settings))

    calls: list[str] = []

    async def _helper(_page: Any, selector: str) -> set[str]:
        calls.append(selector)
        return (
            {"1"}
            if selector.startswith(".similar-jobs") or 'data-test="similar-jobs"' in selector
            else set()
        )

    monkeypatch.setattr(scraper, "_extract_job_ids_from_selector", _helper)
    page = cast(Page, FakePage())

    out1 = await scraper._extract_similar_jobs(page)
    out2 = await scraper._extract_people_also_viewed(page)
    out3 = await scraper._extract_more_jobs_at_company(page)
    out4 = await scraper._extract_from_sidebar(page)

    assert out1 == {"1"}
    assert out2 == set()
    assert out3 == set()
    assert out4 == set()
    assert calls


@pytest.mark.asyncio
async def test_recommended_debug_branches_for_other_sections(monkeypatch, tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = RecommendedJobsScraper(settings=settings, storage=JobStorage(settings))

    async def _helper(_page: Any, selector: str) -> set[str]:
        if "also-viewed" in selector:
            return {"1"}
        if "more-jobs" in selector or "company-jobs" in selector or "jobs-company" in selector:
            return {"2"}
        return set()

    monkeypatch.setattr(scraper, "_extract_job_ids_from_selector", _helper)
    page = cast(Page, FakePage())

    assert await scraper._extract_people_also_viewed(page) == {"1"}
    assert await scraper._extract_more_jobs_at_company(page) == {"2"}


@pytest.mark.asyncio
async def test_recommended_debug_branch_for_sidebar(monkeypatch, tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = RecommendedJobsScraper(settings=settings, storage=JobStorage(settings))

    async def _helper(_page: Any, selector: str) -> set[str]:
        return {"9"} if selector.startswith("aside") else set()

    monkeypatch.setattr(scraper, "_extract_job_ids_from_selector", _helper)
    page = cast(Page, FakePage())
    assert await scraper._extract_from_sidebar(page) == {"9"}


@pytest.mark.asyncio
async def test_recommended_section_extractors_can_return_empty_sets(monkeypatch, tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = RecommendedJobsScraper(settings=settings, storage=JobStorage(settings))

    async def _helper(_page: Any, _selector: str) -> set[str]:
        return set()

    monkeypatch.setattr(scraper, "_extract_job_ids_from_selector", _helper)
    page = cast(Page, FakePage())

    assert await scraper._extract_similar_jobs(page) == set()
    assert await scraper._extract_people_also_viewed(page) == set()
    assert await scraper._extract_more_jobs_at_company(page) == set()
    assert await scraper._extract_from_sidebar(page) == set()


@pytest.mark.asyncio
async def test_recommended_extract_from_page_empty_does_not_save(monkeypatch, tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    storage = JobStorage(settings)
    scraper = RecommendedJobsScraper(settings=settings, storage=storage)

    async def _none(_page: Any) -> set[str]:
        return set()

    monkeypatch.setattr(scraper, "_extract_similar_jobs", _none)
    monkeypatch.setattr(scraper, "_extract_people_also_viewed", _none)
    monkeypatch.setattr(scraper, "_extract_more_jobs_at_company", _none)
    monkeypatch.setattr(scraper, "_extract_from_sidebar", _none)

    out = await scraper.extract_from_page(
        cast(Page, FakePage()), cast(HumanBehavior, FakeHuman()), "1"
    )
    assert out == []
    assert await storage.get_job_ids() == []


@pytest.mark.asyncio
async def test_recommended_extract_job_ids_from_selector_handles_page_errors(tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = RecommendedJobsScraper(settings=settings, storage=JobStorage(settings))

    class _Page(FakePage):
        def locator(self, selector: str) -> FakeLocator:
            _ = selector
            raise RuntimeError("boom")

    ids = await scraper._extract_job_ids_from_selector(cast(Page, _Page()), "x")
    assert ids == set()


@pytest.mark.asyncio
async def test_recommended_extract_all_from_html_parses_ids(tmp_path) -> None:
    settings = settings_for_tests(tmp_path)
    scraper = RecommendedJobsScraper(settings=settings, storage=JobStorage(settings))
    page = FakePage(html='<a href="/jobs/view/123/">x</a><div data-job-id="456"></div>')
    out = await scraper._extract_all_from_html(cast(Page, page))
    assert {"123", "456"} <= out
