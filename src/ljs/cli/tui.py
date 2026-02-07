"""CLI command: tui."""

from __future__ import annotations

import os

import typer

from ljs.consent import ACK_ENV
from ljs.tui import LinkedInScraperApp

from .app import app
from .shared import is_acknowledged


@app.command()
def tui(ctx: typer.Context) -> None:
    """Launch the interactive TUI (Terminal User Interface)."""
    if is_acknowledged(ctx):
        os.environ[ACK_ENV] = "1"

    app_instance = LinkedInScraperApp()
    app_instance.run()
