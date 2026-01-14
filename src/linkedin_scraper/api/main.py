"""FastAPI application for job analytics API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from linkedin_scraper.config import get_settings
from linkedin_scraper.logging_config import get_logger


if TYPE_CHECKING:
    from fastapi import FastAPI

__all__ = ["create_app", "get_app"]

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.middleware.cors import CORSMiddleware
    except ImportError as e:
        msg = "fastapi not installed. Run: uv sync --extra ml"
        raise ImportError(msg) from e

    from pydantic import BaseModel

    app = FastAPI(
        title="LinkedIn Job Scraper API",
        description="API for job analytics and semantic search",
        version="0.1.0",
    )

    # CORS middleware for web dashboard
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    settings = get_settings()

    # Lazy load ML components
    _vectorstore = None
    _exporter = None

    def get_vectorstore():
        nonlocal _vectorstore
        if _vectorstore is None:
            from linkedin_scraper.ml.vectorstore import JobVectorStore

            _vectorstore = JobVectorStore(settings)
        return _vectorstore

    def get_exporter():
        nonlocal _exporter
        if _exporter is None:
            from linkedin_scraper.ml.export import JobDataExporter

            _exporter = JobDataExporter(settings)
        return _exporter

    # Request/Response models
    class SearchRequest(BaseModel):
        query: str
        n_results: int = 10

    class SearchResult(BaseModel):
        job_id: str
        score: float
        title: str | None = None
        company_name: str | None = None
        location: str | None = None
        skills: str | None = None

    class StatsResponse(BaseModel):
        total_jobs: int
        unique_companies: int
        unique_locations: int
        indexed_jobs: int
        top_skills: list[tuple[str, int]]

    class SimilarJobsRequest(BaseModel):
        job_id: str
        n_results: int = 5

    # Routes
    @app.get("/")
    async def root():
        return {"message": "LinkedIn Job Scraper API", "docs": "/docs"}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.post("/search", response_model=list[SearchResult])
    async def search_jobs(request: SearchRequest):
        """Search for jobs using semantic similarity."""
        try:
            vectorstore = get_vectorstore()
            results = vectorstore.search(request.query, n_results=request.n_results)
            return [
                SearchResult(
                    job_id=r["job_id"],
                    score=r["score"],
                    title=r["metadata"].get("title"),
                    company_name=r["metadata"].get("company_name"),
                    location=r["metadata"].get("location"),
                    skills=r["metadata"].get("skills"),
                )
                for r in results
            ]
        except Exception as e:
            logger.exception("Search error")
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/similar", response_model=list[SearchResult])
    async def find_similar_jobs(request: SimilarJobsRequest):
        """Find jobs similar to a given job ID."""
        try:
            vectorstore = get_vectorstore()
            results = vectorstore.get_similar_jobs(request.job_id, n_results=request.n_results)
            return [
                SearchResult(
                    job_id=r["job_id"],
                    score=r["score"],
                    title=r["metadata"].get("title"),
                    company_name=r["metadata"].get("company_name"),
                    location=r["metadata"].get("location"),
                    skills=r["metadata"].get("skills"),
                )
                for r in results
            ]
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except Exception as e:
            logger.exception("Similar jobs error")
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.get("/stats", response_model=StatsResponse)
    async def get_stats():
        """Get job data statistics."""
        try:
            exporter = get_exporter()
            vectorstore = get_vectorstore()

            export_stats = exporter.get_stats()
            vs_stats = vectorstore.get_stats()

            return StatsResponse(
                total_jobs=export_stats.get("total_jobs", 0),
                unique_companies=export_stats.get("unique_companies", 0),
                unique_locations=export_stats.get("unique_locations", 0),
                indexed_jobs=vs_stats.get("total_documents", 0),
                top_skills=export_stats.get("top_skills", []),
            )
        except Exception as e:
            logger.exception("Stats error")
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/index")
    async def index_jobs():
        """Index all jobs into the vector store."""
        try:
            vectorstore = get_vectorstore()
            count = vectorstore.index_jobs()
            return {"indexed": count, "message": f"Indexed {count} new jobs"}
        except Exception as e:
            logger.exception("Index error")
            raise HTTPException(status_code=500, detail=str(e)) from e

    return app


# Lazy app factory - call get_app() to get the instance
def get_app() -> FastAPI:
    """Create the FastAPI app on demand."""
    return create_app()
