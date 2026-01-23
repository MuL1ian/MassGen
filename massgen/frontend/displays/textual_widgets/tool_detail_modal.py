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
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from massgen.frontend.displays.content_normalizer import ContentNormalizer
from massgen.frontend.displays.textual_widgets.result_renderer import ResultRenderer


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

    DEFAULT_CSS = """
    ToolDetailModal {
        align: center middle;
    }

    ToolDetailModal > Container {
        width: 80%;
        max-width: 100;
        height: auto;
        max-height: 80%;
        background: #1c2128;
        border: solid #58a6ff;
        padding: 1 2;
    }

    ToolDetailModal .modal-header {
        height: auto;
        width: 100%;
        padding: 0 1;
        layout: horizontal;
    }

    ToolDetailModal .modal-title {
        text-style: bold;
        width: 1fr;
    }

    ToolDetailModal .modal-close {
        width: auto;
        min-width: 3;
        background: transparent;
        border: none;
        color: #8b949e;
    }

    ToolDetailModal .modal-close:hover {
        color: #e6edf3;
    }

    ToolDetailModal .modal-divider {
        height: 1;
        width: 100%;
        color: #30363d;
    }

    ToolDetailModal .modal-body {
        height: 1fr;
        max-height: 40;
        overflow-y: auto;
    }

    ToolDetailModal .modal-section-title {
        height: 1;
        margin-top: 1;
        text-style: bold;
        color: #39c5cf;
    }

    ToolDetailModal .modal-content {
        height: auto;
        padding: 0 1;
    }

    ToolDetailModal .args-content {
        color: #8b949e;
    }

    ToolDetailModal .result-content {
        color: #e6edf3;
    }

    ToolDetailModal .error-content {
        color: #f85149;
    }

    ToolDetailModal .modal-footer {
        height: auto;
        width: 100%;
        align: center middle;
        margin-top: 1;
    }

    ToolDetailModal .close-button {
        width: auto;
        min-width: 16;
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
        # Clean result text by stripping injection markers and other noise
        self.result = ContentNormalizer.strip_injection_markers(result) if result else None
        self.error = error

    def compose(self) -> ComposeResult:
        with Container():
            # Header with icon, name, status
            with Container(classes="modal-header"):
                yield Static(self._build_header(), classes="modal-title")
                yield Button("✕", variant="default", classes="modal-close", id="close_btn")

            yield Static("─" * 60, classes="modal-divider")

            # Scrollable body containing all sections
            with ScrollableContainer(classes="modal-body"):
                # Arguments section - always show, with placeholder if not available
                yield Static("ARGUMENTS", classes="modal-section-title")
                with Container(classes="modal-content"):
                    if self.args:
                        # Use ResultRenderer to format arguments (often JSON)
                        rendered_args, _ = ResultRenderer.render(self.args, max_lines=30)
                        yield Static(rendered_args, classes="args-content")
                    else:
                        yield Static("[dim]Arguments not captured[/]", classes="args-content", markup=True)

                # Result/Error section - always show, with status-based placeholder
                if self.error:
                    yield Static("ERROR", classes="modal-section-title")
                    with Container(classes="modal-content"):
                        yield Static(self.error, classes="error-content")
                else:
                    yield Static("OUTPUT", classes="modal-section-title")
                    with Container(classes="modal-content"):
                        if self.result:
                            # Use ResultRenderer to format result with syntax highlighting
                            rendered_result, was_truncated = ResultRenderer.render(self.result)
                            yield Static(rendered_result, classes="result-content")
                        elif self.status == "running":
                            yield Static("[dim]Waiting for output...[/]", classes="result-content", markup=True)
                        else:
                            yield Static("[dim]No output captured[/]", classes="result-content", markup=True)

            # Footer with close button - always visible at bottom
            with Container(classes="modal-footer"):
                yield Button("Close (Esc)", variant="primary", classes="close-button", id="close_btn_footer")

    def _build_header(self) -> Text:
        """Build the header text with name and status (no emoji)."""
        text = Text()
        text.append(self.tool_name, style="bold")

        # Add status with appropriate styling (text symbols, no emoji)
        if self.status == "success":
            text.append("  ✓", style="bold green")
        elif self.status == "error":
            text.append("  ✗", style="bold red")
        else:
            text.append("  ...", style="bold yellow")

        if self.elapsed:
            text.append(f" {self.elapsed}", style="dim")

        return text

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id in ("close_btn", "close_btn_footer"):
            self.dismiss()

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss()
