"""CLI application setup."""

from __future__ import annotations

import logging
import os
import sys
from typing import Annotated

import typer

from ljs import __version__
from ljs.config import get_settings
from ljs.log import log_info, set_log_context
from ljs.logging_config import setup_logging

from .shared import console


app = typer.Typer(
    help="Educational LinkedIn public job ads scraper",
    add_completion=False,
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"[bold blue]LinkedIn Job Scraper[/bold blue] v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    _version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-V", help="Enable verbose logging"),
    ] = False,
    acknowledge: Annotated[
        bool,
        typer.Option(
            "--i-understand",
            help="Acknowledge educational-only use and compliance responsibility",
        ),
    ] = False,
) -> None:
    """LinkedIn Job Scraper - Educational project for scraping public job ads."""
    ctx.obj = {"acknowledged": acknowledge}
    settings = get_settings()
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging(level=level, log_dir=settings.log_dir)

    set_log_context(run_id=settings.run_id, pid=os.getpid())
    log_info(
        logging.getLogger("ljs.cli"),
        "cli.start",
        argv=" ".join(sys.argv),
        verbose=verbose,
        headless=settings.headless,
        log_dir=settings.log_dir,
    )
