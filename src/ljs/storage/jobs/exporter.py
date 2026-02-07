"""JSONL export for job detail datasets."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiofiles

from ljs import __version__
from ljs.models.job import JobDetail

from .text import (
    _JOB_DETAIL_DATASET_SCHEMA_VERSION,
    build_ml_text,
    normalize_whitespace,
    redact_pii,
)


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _prepare_paths(output_path: Path, manifest_path: Path | None) -> Path:
    _ensure_parent(output_path)
    final_manifest = manifest_path or output_path.with_suffix(".manifest.json")
    _ensure_parent(final_manifest)
    return final_manifest


async def export_job_details_jsonl(
    detail_files: list[Path],
    output_path: Path,
    *,
    manifest_path: Path | None = None,
    redact_pii: bool = False,
    include_raw_sections: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    """Export stored job details into a JSONL dataset file plus a manifest."""
    manifest_path = _prepare_paths(output_path, manifest_path)

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
                record["description"] = redact_pii_text(description)

            record["source_url"] = f"https://www.linkedin.com/jobs/view/{detail.job_id}/"
            record["schema_version"] = _JOB_DETAIL_DATASET_SCHEMA_VERSION
            record["scraper_version"] = __version__

            text = build_ml_text(
                title=record.get("title"),
                company_name=record.get("company_name"),
                location=record.get("location"),
                description=record.get("description"),
            )
            if redact_pii:
                text = redact_pii_text(text)
            record["text"] = normalize_whitespace(text)

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


def redact_pii_text(text: str) -> str:
    """Redact PII in a text string."""
    return redact_pii(text)
