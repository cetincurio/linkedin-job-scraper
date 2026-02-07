"""CLI command: export."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.panel import Panel
from rich.table import Table

from ljs.config import get_settings
from ljs.storage.jobs import JobStorage

from .app import app
from .shared import console


@app.command()
def export(
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output JSONL file path"),
    ] = None,
    manifest: Annotated[
        Path | None,
        typer.Option("--manifest", help="Optional manifest JSON path"),
    ] = None,
    redact_pii: Annotated[
        bool,
        typer.Option("--redact-pii", help="Redact email/phone-like PII from text fields"),
    ] = False,
    include_raw_sections: Annotated[
        bool,
        typer.Option("--include-raw-sections", help="Include raw_sections field in export"),
    ] = False,
    limit: Annotated[
        int | None,
        typer.Option("--limit", "-l", help="Limit number of job details to export"),
    ] = None,
) -> None:
    """Export stored job details as an ML-ready JSONL dataset with a manifest."""
    settings = get_settings()
    storage = JobStorage(settings)

    output_path = output or (settings.data_dir / "datasets" / "job_details.jsonl")

    console.print(
        Panel(
            f"[bold]Dataset:[/bold] {output_path}\n"
            f"[bold]Manifest:[/bold] {manifest or output_path.with_suffix('.manifest.json')}\n"
            f"[bold]Redact PII:[/bold] {redact_pii}\n"
            f"[bold]Include raw_sections:[/bold] {include_raw_sections}\n"
            f"[bold]Limit:[/bold] {limit or 'All'}",
            title="Export Dataset",
            border_style="blue",
        )
    )

    try:
        result = asyncio.run(
            storage.export_job_details_jsonl(
                output_path=output_path,
                manifest_path=manifest,
                redact_pii=redact_pii,
                include_raw_sections=include_raw_sections,
                limit=limit,
            )
        )
    except Exception as err:
        console.print(f"[red]Export failed:[/red] {err}")
        raise typer.Exit(1) from err

    table = Table(title="Export Result", show_header=True, header_style="bold green")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Records", str(result.get("record_count", 0)))
    table.add_row("Dataset", str(result.get("dataset_file", output_path)))
    table.add_row("Manifest", str(result.get("manifest_file", "")))
    table.add_row("SHA256", str(result.get("sha256", "")))
    console.print(table)
