"""Export job data to ML-ready formats using Polars."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

from linkedin_scraper.logging_config import get_logger


if TYPE_CHECKING:
    import polars as pl

    from linkedin_scraper.config import Settings

__all__ = ["JobDataExporter"]

logger = get_logger(__name__)


class JobDataExporter:
    """Export scraped job data to ML-ready formats."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._job_details_dir = settings.job_details_dir

    def _load_job_details(self) -> list[dict]:
        """Load all job details from JSON files."""
        jobs = []
        for json_file in self._job_details_dir.glob("*.json"):
            try:
                with json_file.open(encoding="utf-8") as f:
                    job = json.load(f)
                    jobs.append(job)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load %s: %s", json_file, e)
        return jobs

    def _clean_text(self, text: str | None) -> str:
        """Clean and normalize text for ML processing."""
        if not text:
            return ""
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _extract_skills(self, description: str) -> list[str]:
        """Extract potential skills from job description."""
        # Common tech skills patterns (simplified)
        skill_patterns = [
            r"\b(python|java|javascript|typescript|go|rust|c\+\+|ruby|php)\b",
            r"\b(react|angular|vue|nextjs|fastapi|django|flask|spring)\b",
            r"\b(aws|azure|gcp|kubernetes|docker|terraform)\b",
            r"\b(sql|postgresql|mysql|mongodb|redis|elasticsearch)\b",
            r"\b(machine learning|deep learning|nlp|computer vision)\b",
            r"\b(pytorch|tensorflow|scikit-learn|pandas|numpy)\b",
            r"\b(git|ci/cd|agile|scrum|devops)\b",
        ]
        skills = set()
        description_lower = description.lower()
        for pattern in skill_patterns:
            matches = re.findall(pattern, description_lower)
            skills.update(matches)
        return sorted(skills)

    def to_polars(self) -> pl.DataFrame:
        """Convert job data to Polars DataFrame."""
        try:
            import polars as pl
        except ImportError as e:
            msg = "polars not installed. Run: uv sync --extra ml"
            raise ImportError(msg) from e

        jobs = self._load_job_details()
        if not jobs:
            logger.warning("No job details found")
            return pl.DataFrame()

        # Transform to flat records
        records = []
        for job in jobs:
            description = self._clean_text(job.get("description", ""))
            records.append(
                {
                    "job_id": job.get("job_id", ""),
                    "title": job.get("title", ""),
                    "company_name": job.get("company_name", ""),
                    "location": job.get("location", ""),
                    "description": description,
                    "employment_type": job.get("employment_type", ""),
                    "seniority_level": job.get("seniority_level", ""),
                    "industries": ",".join(job.get("industries", [])),
                    "job_functions": ",".join(job.get("job_functions", [])),
                    "skills": ",".join(self._extract_skills(description)),
                    "applicant_count": job.get("applicant_count"),
                    "scraped_at": job.get("scraped_at", ""),
                    "ml_text": (
                        f"{job.get('title', '')} {job.get('company_name', '')} {description}"
                    ),
                }
            )

        return pl.DataFrame(records)

    def export_parquet(self, output_path: Path | str | None = None) -> Path:
        """Export job data to Parquet format."""
        df = self.to_polars()
        if df.is_empty():
            msg = "No data to export"
            raise ValueError(msg)

        if output_path is None:
            output_path = self._settings.data_dir / "datasets" / "jobs.parquet"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        df.write_parquet(output_path, compression="zstd")
        logger.info("Exported %d jobs to %s", len(df), output_path)
        return output_path

    def export_jsonl(self, output_path: Path | str | None = None) -> Path:
        """Export job data to JSONL format (for training)."""
        df = self.to_polars()
        if df.is_empty():
            msg = "No data to export"
            raise ValueError(msg)

        if output_path is None:
            output_path = self._settings.data_dir / "datasets" / "jobs.jsonl"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        df.write_ndjson(output_path)
        logger.info("Exported %d jobs to %s", len(df), output_path)
        return output_path

    def get_stats(self) -> dict:
        """Get statistics about the exported data."""
        df = self.to_polars()
        if df.is_empty():
            return {"total_jobs": 0}

        return {
            "total_jobs": len(df),
            "unique_companies": df["company_name"].n_unique(),
            "unique_locations": df["location"].n_unique(),
            "avg_description_length": int(df["description"].str.len_chars().mean() or 0),
            "top_skills": self._get_top_skills(df, n=10),
        }

    def _get_top_skills(self, df: pl.DataFrame, n: int = 10) -> list[tuple[str, int]]:
        """Get most common skills from the dataset."""
        try:
            import polars as pl
        except ImportError:
            return []

        all_skills: list[str] = []
        for skills_str in df["skills"].to_list():
            if skills_str:
                all_skills.extend(skills_str.split(","))

        if not all_skills:
            return []

        skill_counts = pl.DataFrame({"skill": all_skills}).group_by("skill").len()
        top = skill_counts.sort("len", descending=True).head(n)
        return list(zip(top["skill"].to_list(), top["len"].to_list(), strict=False))
