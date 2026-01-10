# -*- coding: utf-8 -*-
"""
Tool Detail Modal Widget for MassGen TUI.

Full-screen modal overlay for viewing complete tool call details
including arguments, results, and timing information.
"""

from typing import Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ToolDetailModal(ModalScreen[None]):
    """Modal screen showing full tool call details.

    Design:
    ```
    ┌─────────────────────────────────────────────────────────────────────┐
    │                                                              [X]    │
    │  📁 read_file                                          ✓ 0.3s      │
    │  ───────────────────────────────────────────────────────────────   │
    │                                                                     │
    │  ARGUMENTS                                                          │
    │  ──────────────────────────────────────────────────────────────    │
    │  path: /tmp/example.txt                                             │
    │  encoding: utf-8                                                    │
    │                                                                     │
    │  RESULT                                                             │
    │  ──────────────────────────────────────────────────────────────    │
    │  Hello world, this is the file content...                           │
    │                                                                     │
    │                                                                     │
    │                          [ Close (Esc) ]                            │
    └─────────────────────────────────────────────────────────────────────┘
    ```
    """

    BINDINGS = [
        ("escape", "close", "Close"),
    ]

    # Threshold for showing expand button (chars)
    LONG_CONTENT_THRESHOLD = 500

    # Track expanded state
    is_expanded = reactive(False)

    DEFAULT_CSS = """
    ToolDetailModal {
        align: center middle;
    }

    ToolDetailModal > Container {
        width: 80%;
        max-width: 100;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    ToolDetailModal.expanded > Container {
        max-height: 95%;
    }

    ToolDetailModal .modal-header {
        height: 3;
        width: 100%;
        padding: 0 1;
    }

    ToolDetailModal .modal-title {
        text-style: bold;
    }

    ToolDetailModal .modal-close {
        dock: right;
        width: auto;
        min-width: 5;
    }

    ToolDetailModal .modal-divider {
        height: 1;
        width: 100%;
        color: $primary-darken-2;
    }

    ToolDetailModal .modal-section-title {
        height: 1;
        margin-top: 1;
        text-style: bold;
        color: $secondary;
    }

    ToolDetailModal .modal-content {
        height: auto;
        max-height: 15;
        padding: 0 1;
        overflow-y: auto;
    }

    ToolDetailModal.expanded .modal-content {
        max-height: 40;
    }

    ToolDetailModal .args-content {
        color: $text-muted;
    }

    ToolDetailModal .result-content {
        color: $text;
    }

    ToolDetailModal .error-content {
        color: $error;
    }

    ToolDetailModal .modal-footer {
        height: 3;
        width: 100%;
        align: center middle;
        margin-top: 1;
    }

    ToolDetailModal .close-button {
        width: auto;
        min-width: 16;
    }

    ToolDetailModal .expand-button {
        width: auto;
        min-width: 12;
        margin-right: 2;
    }
    """

    def __init__(
        self,
        tool_name: str,
        icon: str = "🔧",
        status: str = "running",
        elapsed: Optional[str] = None,
        args: Optional[str] = None,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Initialize the modal.

        Args:
            tool_name: Display name of the tool
            icon: Category icon
            status: Current status (running, success, error)
            elapsed: Elapsed time string
            args: Full arguments text
            result: Full result text
            error: Error message if failed
        """
        super().__init__()
        self.tool_name = tool_name
        self.icon = icon
        self.status = status
        self.elapsed = elapsed
        self.args = args
        self.result = result
        self.error = error

        # Check if content is long enough to warrant expand button
        total_len = len(args or "") + len(result or "") + len(error or "")
        self._has_long_content = total_len > self.LONG_CONTENT_THRESHOLD

    def compose(self) -> ComposeResult:
        with Container():
            # Header with icon, name, status
            with Container(classes="modal-header"):
                yield Static(self._build_header(), classes="modal-title")
                yield Button("✕", variant="default", classes="modal-close", id="close_btn")

            yield Static("─" * 60, classes="modal-divider")

            # Arguments section
            if self.args:
                yield Static("ARGUMENTS", classes="modal-section-title")
                with ScrollableContainer(classes="modal-content"):
                    yield Static(self.args, classes="args-content")

            # Result or Error section
            if self.error:
                yield Static("ERROR", classes="modal-section-title")
                with ScrollableContainer(classes="modal-content"):
                    yield Static(self.error, classes="error-content")
            elif self.result:
                yield Static("RESULT", classes="modal-section-title")
                with ScrollableContainer(classes="modal-content"):
                    yield Static(self.result, classes="result-content")
            elif self.status == "running":
                yield Static("STATUS", classes="modal-section-title")
                with Container(classes="modal-content"):
                    yield Static("⏳ Tool is running...", classes="args-content")

            # Footer with expand (if long content) and close button
            with Container(classes="modal-footer"):
                if self._has_long_content:
                    yield Button(
                        "⤢ Expand" if not self.is_expanded else "⤡ Collapse",
                        variant="default",
                        classes="expand-button",
                        id="expand_btn",
                    )
                yield Button("Close (Esc)", variant="primary", classes="close-button", id="close_btn_footer")

    def _build_header(self) -> Text:
        """Build the header text with icon, name, and status."""
        text = Text()
        text.append(f"{self.icon} ", style="bold")
        text.append(self.tool_name, style="bold")

        # Add status with appropriate styling
        if self.status == "success":
            text.append("  ✓", style="bold green")
        elif self.status == "error":
            text.append("  ✗", style="bold red")
        else:
            text.append("  ⏳", style="bold yellow")

        if self.elapsed:
            text.append(f" {self.elapsed}", style="dim")

        return text

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id in ("close_btn", "close_btn_footer"):
            self.dismiss()
        elif event.button.id == "expand_btn":
            self.is_expanded = not self.is_expanded

    def watch_is_expanded(self, expanded: bool) -> None:
        """Update UI when expanded state changes."""
        if expanded:
            self.add_class("expanded")
        else:
            self.remove_class("expanded")

        # Update expand button text
        try:
            expand_btn = self.query_one("#expand_btn", Button)
            expand_btn.label = "⤡ Collapse" if expanded else "⤢ Expand"
        except Exception:
            pass

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss()
