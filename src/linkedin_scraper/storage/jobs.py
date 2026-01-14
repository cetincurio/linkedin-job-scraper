"""Job data storage and retrieval."""

import hashlib
import json
import re
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiofiles

from linkedin_scraper import __version__
from linkedin_scraper.config import Settings, get_settings
from linkedin_scraper.logging_config import get_logger
from linkedin_scraper.models.job import JobDetail, JobId, JobIdSource


__all__ = ["JobStorage"]

logger = get_logger(__name__)


_JOB_DETAIL_DATASET_SCHEMA_VERSION = "linkedin-job-scraper.job_detail.v1"

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_CANDIDATE_RE = re.compile(r"(?:\+?\d[\d\s().-]{8,}\d)")
_WHITESPACE_RE = re.compile(r"[ \t]+")
_MANY_NEWLINES_RE = re.compile(r"\n{3,}")


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WHITESPACE_RE.sub(" ", text)
    text = _MANY_NEWLINES_RE.sub("\n\n", text)
    return text.strip()


def _redact_pii(text: str) -> str:
    text = _EMAIL_RE.sub("[EMAIL]", text)

    def _phone_repl(match: re.Match[str]) -> str:
        candidate = match.group(0)

        digits = sum(char.isdigit() for char in candidate)
        if digits < 10:
            return candidate
        if all(char.isdigit() for char in candidate):
            return candidate
        return "[PHONE]"

    return _PHONE_CANDIDATE_RE.sub(_phone_repl, text)


def _build_ml_text(
    *,
    title: str | None,
    company_name: str | None,
    location: str | None,
    description: str | None,
) -> str:
    parts: list[str] = []
    if title:
        parts.append(title)
    if company_name:
        parts.append(company_name)
    if location:
        parts.append(location)
    if description:
        parts.append(description)
    return "\n\n".join(parts)


class JobStorage:
    """Handles persistence of job IDs and job details."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._settings.ensure_directories()

    def _get_job_ids_file(self, source: JobIdSource) -> Path:
        """Get the file path for job IDs of a specific source."""
        return self._settings.job_ids_dir / f"{source.value}_job_ids.json"

    def _get_job_detail_file(self, job_id: str) -> Path:
        """Get the file path for a job detail."""
        return self._settings.job_details_dir / f"{job_id}.json"

    async def save_job_id(self, job: JobId) -> None:
        """Save a single job ID to storage."""
        file_path = self._get_job_ids_file(job.source)

        # Load existing job IDs
        existing = await self._load_job_ids_from_file(file_path)

        # Check for duplicates
        existing_ids = {j.job_id for j in existing}
        if job.job_id in existing_ids:
            logger.debug(f"Job ID {job.job_id} already exists, skipping")
            return

        existing.append(job)

        # Save back
        await self._save_job_ids_to_file(file_path, existing)
        logger.debug(f"Saved job ID: {job.job_id} (source: {job.source.value})")

    async def save_job_ids(self, jobs: list[JobId]) -> int:
        """
        Save multiple job IDs to storage.

        Returns the number of new job IDs saved.
        """
        if not jobs:
            return 0

        # Group by source
        by_source: dict[JobIdSource, list[JobId]] = {}
        for job in jobs:
            by_source.setdefault(job.source, []).append(job)

        saved_count = 0

        for source, source_jobs in by_source.items():
            file_path = self._get_job_ids_file(source)
            existing = await self._load_job_ids_from_file(file_path)
            existing_ids = {j.job_id for j in existing}

            new_jobs = [j for j in source_jobs if j.job_id not in existing_ids]
            if new_jobs:
                existing.extend(new_jobs)
                await self._save_job_ids_to_file(file_path, existing)
                saved_count += len(new_jobs)
                logger.info(f"Saved {len(new_jobs)} new job IDs (source: {source.value})")

        return saved_count

    async def _load_job_ids_from_file(self, file_path: Path) -> list[JobId]:
        """Load job IDs from a JSON file."""
        if not file_path.exists():
            return []

        try:
            async with aiofiles.open(file_path) as f:
                content = await f.read()
                data = json.loads(content)
                return [JobId.model_validate(item) for item in data]
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error loading job IDs from {file_path}: {e}")
            return []

    async def _save_job_ids_to_file(self, file_path: Path, jobs: list[JobId]) -> None:
        """Save job IDs to a JSON file."""
        data = [job.model_dump(mode="json") for job in jobs]
        async with aiofiles.open(file_path, "w") as f:
            await f.write(json.dumps(data, indent=2, default=str))

    async def get_job_ids(
        self,
        source: JobIdSource | None = None,
        unscraped_only: bool = False,
    ) -> list[JobId]:
        """
        Retrieve job IDs from storage.

        Args:
            source: Filter by source, or None for all sources
            unscraped_only: If True, only return job IDs not yet scraped
        """
        if source:
            jobs = await self._load_job_ids_from_file(self._get_job_ids_file(source))
        else:
            jobs = []
            for src in JobIdSource:
                jobs.extend(await self._load_job_ids_from_file(self._get_job_ids_file(src)))

        if unscraped_only:
            jobs = [j for j in jobs if not j.scraped]

        return jobs

    async def mark_job_scraped(self, job_id: str) -> None:
        """Mark a job ID as scraped in all source files."""
        for source in JobIdSource:
            file_path = self._get_job_ids_file(source)
            jobs = await self._load_job_ids_from_file(file_path)

            modified = False
            for job in jobs:
                if job.job_id == job_id and not job.scraped:
                    job.scraped = True
                    modified = True

            if modified:
                await self._save_job_ids_to_file(file_path, jobs)
                logger.debug(f"Marked job {job_id} as scraped in {source.value}")

    async def save_job_detail(self, detail: JobDetail) -> None:
        """Save job detail to storage."""
        file_path = self._get_job_detail_file(detail.job_id)
        data = detail.model_dump(mode="json")

        async with aiofiles.open(file_path, "w") as f:
            await f.write(json.dumps(data, indent=2, default=str))

        logger.debug(f"Saved job detail: {detail.job_id}")

    async def get_job_detail(self, job_id: str) -> JobDetail | None:
        """Retrieve a job detail from storage."""
        file_path = self._get_job_detail_file(job_id)
        if not file_path.exists():
            return None

        try:
            async with aiofiles.open(file_path) as f:
                content = await f.read()
                data = json.loads(content)
                return JobDetail.model_validate(data)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error loading job detail {job_id}: {e}")
            return None

    async def job_detail_exists(self, job_id: str) -> bool:
        """Check if a job detail already exists in storage."""
        return self._get_job_detail_file(job_id).exists()

    def iter_job_details(self) -> Iterator[Path]:
        """Iterate over all job detail files."""
        return self._settings.job_details_dir.glob("*.json")

    async def get_stats(self) -> dict[str, int]:
        """Get storage statistics."""
        search_ids = await self.get_job_ids(JobIdSource.SEARCH)
        recommended_ids = await self.get_job_ids(JobIdSource.RECOMMENDED)
        detail_count = sum(1 for _ in self.iter_job_details())

        return {
            "search_job_ids": len(search_ids),
            "recommended_job_ids": len(recommended_ids),
            "unscraped_search": len([j for j in search_ids if not j.scraped]),
            "unscraped_recommended": len([j for j in recommended_ids if not j.scraped]),
            "job_details": detail_count,
        }

    async def export_job_details_jsonl(
        self,
        output_path: Path,
        *,
        manifest_path: Path | None = None,
        redact_pii: bool = False,
        include_raw_sections: bool = False,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Export stored job details into a JSONL dataset file plus a manifest."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_path or output_path.with_suffix(".manifest.json")
        manifest_path.parent.mkdir(parents=True, exist_ok=True)

        detail_files = sorted(self.iter_job_details())
        if limit is not None:
            detail_files = detail_files[:limit]

        hasher = hashlib.sha256()
        record_count = 0
        fields: list[str] | None = None

        async with aiofiles.open(output_path, "w", encoding="utf-8") as out_file:
            for detail_path in detail_files:
                async with aiofiles.open(detail_path, encoding="utf-8") as detail_file:
                    content = await detail_file.read()

                try:
                    detail = JobDetail.model_validate(json.loads(content))
                except (json.JSONDecodeError, ValueError) as err:
                    raise ValueError(f"Invalid job detail JSON in {detail_path}: {err}") from err

                record = detail.model_dump(mode="json")

                if not include_raw_sections:
                    record.pop("raw_sections", None)

                description = record.get("description")
                if redact_pii and isinstance(description, str):
                    record["description"] = _redact_pii(description)

                record["source_url"] = f"https://www.linkedin.com/jobs/view/{detail.job_id}/"
                record["schema_version"] = _JOB_DETAIL_DATASET_SCHEMA_VERSION
                record["scraper_version"] = __version__

                text = _build_ml_text(
                    title=record.get("title"),
                    company_name=record.get("company_name"),
                    location=record.get("location"),
                    description=record.get("description"),
                )
                if redact_pii:
                    text = _redact_pii(text)
                record["text"] = _normalize_whitespace(text)

                line = json.dumps(record, ensure_ascii=False) + "\n"
                await out_file.write(line)
                hasher.update(line.encode("utf-8"))

                record_count += 1
                if fields is None:
                    fields = sorted(record.keys())

        generated_at = datetime.now(tz=UTC).isoformat()
        manifest: dict[str, Any] = {
            "schema_version": _JOB_DETAIL_DATASET_SCHEMA_VERSION,
            "format": "jsonl",
            "generated_at": generated_at,
            "record_count": record_count,
            "dataset_file": str(output_path),
            "manifest_file": str(manifest_path),
            "sha256": hasher.hexdigest(),
            "pii_redacted": redact_pii,
            "include_raw_sections": include_raw_sections,
            "fields": fields or [],
            "scraper_version": __version__,
        }

        async with aiofiles.open(manifest_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

        return manifest
