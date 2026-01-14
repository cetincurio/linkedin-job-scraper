"""FastAPI application for serving job analytics."""

from linkedin_scraper.api.main import create_app, get_app


__all__ = ["create_app", "get_app"]
