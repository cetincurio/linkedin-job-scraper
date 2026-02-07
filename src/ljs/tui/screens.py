"""TUI modal screens."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from .constants import ACK_MESSAGE


class ConsentScreen(ModalScreen[bool]):
    """Modal screen to confirm educational-only usage."""

    def compose(self) -> ComposeResult:
        yield Container(
            Static("[bold]Educational Use Only[/bold]\n\n" + ACK_MESSAGE),
            Horizontal(
                Button("I Understand", id="btn-ack", variant="primary"),
                Button("Exit", id="btn-exit", variant="error"),
                classes="consent-buttons",
            ),
            id="consent-dialog",
        )

    @on(Button.Pressed, "#btn-ack")
    def on_ack_pressed(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#btn-exit")
    def on_exit_pressed(self) -> None:
        self.dismiss(False)
