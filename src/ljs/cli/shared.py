"""Shared CLI helpers."""

from __future__ import annotations

from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel

from ljs.consent import ACK_MESSAGE, is_acknowledged_env


console = Console()


def is_acknowledged(ctx: typer.Context) -> bool:
    """Check whether user has acknowledged educational-only use."""
    if is_acknowledged_env():
        return True
    ctx_obj: dict[str, Any] = ctx.obj or {}
    return bool(ctx_obj.get("acknowledged"))


def require_acknowledgement(ctx: typer.Context) -> None:
    """Prompt for acknowledgement if not yet provided."""
    if is_acknowledged(ctx):
        return
    console.print(Panel(ACK_MESSAGE, title="Educational Use Only", border_style="yellow"))
    if not typer.confirm("Do you understand and want to proceed?"):
        raise typer.Exit(1)
