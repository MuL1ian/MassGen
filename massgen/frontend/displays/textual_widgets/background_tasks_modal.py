# -*- coding: utf-8 -*-
"""
Background Tasks Modal Widget for MassGen TUI.

Modal overlay for viewing background/async operations like background shells.
Supports drilling down into individual tasks to see live output.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class BackgroundTaskRow(Static, can_focus=True):
    """Clickable row for a background task."""

    def __init__(
        self,
        task_data: Dict[str, Any],
        index: int,
        agent_id: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._task_data = task_data
        self.index = index
        self.agent_id = agent_id

    def compose(self) -> ComposeResult:
        yield Static(self._build_content(), classes="task-content")

    def _build_content(self) -> Text:
        """Build the task row content."""
        text = Text()
        task = self._task_data

        # Tool name (no emoji)
        tool_name = task.get("tool_name", "Unknown")
        display_name = task.get("display_name", tool_name)
        text.append("● ", style="bold #d29922")
        text.append(display_name, style="bold")

        # Async ID (e.g., shell_id)
        async_id = task.get("async_id")
        if async_id:
            text.append(f"  [{async_id}]", style="dim #d29922")

        text.append("\n")

        # Elapsed time
        start_time = task.get("start_time")
        if start_time:
            if isinstance(start_time, datetime):
                elapsed = (datetime.now() - start_time).total_seconds()
            else:
                elapsed = 0
            minutes, seconds = divmod(int(elapsed), 60)
            text.append(f"  ⏱ {minutes}m{seconds:02d}s running", style="dim")

        # Click hint
        text.append("  [click for details]", style="dim italic #d29922")

        return text

    def on_click(self) -> None:
        """Handle click to show detail view."""
        # Post message to parent modal
        self.app.push_screen(BackgroundTaskDetailModal(self._task_data, self.agent_id))


class BackgroundTaskDetailModal(ModalScreen[None]):
    """Detail modal for a single background task with live output."""

    BINDINGS = [
        ("escape", "close", "Back"),
        ("r", "refresh", "Refresh Output"),
    ]

    DEFAULT_CSS = """
    BackgroundTaskDetailModal {
        align: center middle;
    }

    BackgroundTaskDetailModal > Container {
        width: 95%;
        max-width: 140;
        height: 85%;
        background: #1c2128;
        border: solid #d29922;
        padding: 1 2;
    }

    BackgroundTaskDetailModal .modal-header {
        height: auto;
        width: 100%;
        padding: 0 1;
        margin-bottom: 1;
    }

    BackgroundTaskDetailModal .header-row {
        height: auto;
        width: 100%;
        layout: horizontal;
    }

    BackgroundTaskDetailModal .modal-title {
        text-style: bold;
        width: 1fr;
        color: #d29922;
    }

    BackgroundTaskDetailModal .modal-close {
        width: auto;
        min-width: 3;
        background: transparent;
        border: none;
        color: #8b949e;
    }

    BackgroundTaskDetailModal .modal-close:hover {
        color: #e6edf3;
    }

    BackgroundTaskDetailModal .info-section {
        height: auto;
        width: 100%;
        padding: 1;
        margin-bottom: 1;
        background: #0d1117;
        border-left: solid #d29922;
    }

    BackgroundTaskDetailModal .output-header {
        height: auto;
        width: 100%;
        padding: 0 1;
        margin-top: 1;
    }

    BackgroundTaskDetailModal .output-section {
        height: 1fr;
        width: 100%;
        background: #0d1117;
        border: solid #30363d;
        padding: 1;
        overflow-y: auto;
    }

    BackgroundTaskDetailModal .output-content {
        height: auto;
        width: 100%;
    }

    BackgroundTaskDetailModal .modal-footer {
        height: auto;
        width: 100%;
        layout: horizontal;
        align: center middle;
        margin-top: 1;
        padding-top: 1;
        border-top: solid #30363d;
    }

    BackgroundTaskDetailModal .footer-button {
        width: auto;
        min-width: 16;
        margin: 0 1;
    }

    BackgroundTaskDetailModal .status-running {
        color: #d29922;
    }

    BackgroundTaskDetailModal .status-stopped {
        color: #3fb950;
    }

    BackgroundTaskDetailModal .status-failed {
        color: #f85149;
    }

    BackgroundTaskDetailModal .no-output {
        color: #8b949e;
        text-style: italic;
    }
    """

    def __init__(self, task_data: Dict[str, Any], agent_id: Optional[str] = None) -> None:
        super().__init__()
        self._task_data = task_data
        self.agent_id = agent_id
        self._output_widget: Optional[Static] = None
        self._status_widget: Optional[Static] = None

    def compose(self) -> ComposeResult:
        task = self._task_data
        display_name = task.get("display_name", task.get("tool_name", "Unknown"))
        async_id = task.get("async_id", "")

        with Container():
            # Header
            with Container(classes="modal-header"):
                with Container(classes="header-row"):
                    title = f"Background Task . {display_name}"
                    if async_id:
                        title += f" [{async_id}]"
                    yield Static(title, classes="modal-title")
                    yield Button("✕", variant="default", classes="modal-close", id="close_btn")

            # Info section
            yield Static(self._build_info(), classes="info-section", id="info_section")

            # Output header with status
            with Container(classes="output-header"):
                yield Static(self._build_output_header(), id="output_header")

            # Output section
            with ScrollableContainer(classes="output-section"):
                self._output_widget = Static(
                    self._build_output(),
                    classes="output-content",
                    id="output_content",
                )
                yield self._output_widget

            # Footer with buttons
            with Container(classes="modal-footer"):
                yield Button("↻ Refresh (r)", variant="default", classes="footer-button", id="refresh_btn")
                yield Button("← Back (Esc)", variant="primary", classes="footer-button", id="back_btn")

    def _build_info(self) -> Text:
        """Build the info section content."""
        text = Text()
        task = self._task_data

        # Shell ID
        async_id = task.get("async_id")
        if async_id:
            text.append("Shell ID: ", style="bold")
            text.append(f"{async_id}\n", style="#d29922")

        # Start time
        start_time = task.get("start_time")
        if start_time:
            if isinstance(start_time, datetime):
                text.append("Started: ", style="bold")
                text.append(f"{start_time.strftime('%H:%M:%S')}\n")

                elapsed = (datetime.now() - start_time).total_seconds()
                minutes, seconds = divmod(int(elapsed), 60)
                hours, minutes = divmod(minutes, 60)
                if hours > 0:
                    elapsed_str = f"{hours}h {minutes}m {seconds}s"
                else:
                    elapsed_str = f"{minutes}m {seconds}s"
                text.append("Elapsed: ", style="bold")
                text.append(f"{elapsed_str}\n")

        # Original result/command info
        result = task.get("result", "")
        if result:
            # Try to extract command from result
            text.append("Command: ", style="bold")
            # Result often contains JSON with command info
            preview = result[:200] if len(result) > 200 else result
            text.append(f"{preview}", style="dim")

        return text

    def _build_output_header(self) -> Text:
        """Build the output section header with status."""
        text = Text()
        text.append("Live Output", style="bold")

        # Get current status
        status_info = self._get_shell_status()
        if status_info:
            status = status_info.get("status", "unknown")
            text.append("  [", style="dim")
            if status == "running":
                text.append("● running", style="#d29922")  # amber/orange
            elif status == "stopped":
                exit_code = status_info.get("exit_code", 0)
                if exit_code == 0:
                    text.append("✓ completed", style="#3fb950")  # green
                else:
                    text.append(f"✗ failed (exit {exit_code})", style="#f85149")  # red
            else:
                text.append(status, style="dim")
            text.append("]", style="dim")

        text.append("  (press 'r' to refresh)", style="dim italic")

        return text

    def _build_output(self) -> Text:
        """Build the output content from shell."""
        async_id = self._task_data.get("async_id")
        if not async_id:
            return Text("No shell ID available - cannot fetch output.", style="no-output")

        output_info = self._get_shell_output()
        if not output_info:
            return Text("Unable to fetch output. Shell may have been cleaned up.", style="no-output")

        text = Text()

        stdout = output_info.get("stdout", "")
        stderr = output_info.get("stderr", "")

        if not stdout and not stderr:
            return Text("No output yet...", style="no-output")

        # Show stdout
        if stdout:
            text.append("─── stdout ───\n", style="dim #3fb950")
            # Show last 100 lines to avoid overwhelming the display
            lines = stdout.split("\n")
            if len(lines) > 100:
                text.append(f"... ({len(lines) - 100} lines omitted) ...\n", style="dim italic")
                lines = lines[-100:]
            text.append("\n".join(lines), style="#c9d1d9")

        # Show stderr if present
        if stderr:
            if stdout:
                text.append("\n\n")
            text.append("─── stderr ───\n", style="dim #f85149")
            lines = stderr.split("\n")
            if len(lines) > 50:
                text.append(f"... ({len(lines) - 50} lines omitted) ...\n", style="dim italic")
                lines = lines[-50:]
            text.append("\n".join(lines), style="#f85149")

        return text

    def _get_shell_output(self) -> Optional[Dict[str, Any]]:
        """Get shell output - returns stored result since live fetch isn't available.

        Background shells run in MCP subprocesses. The TUI runs in a separate
        thread from the async orchestrator, making cross-thread MCP calls
        complex. Instead, we show the tool result that was returned when
        the shell was started.
        """
        # Return a synthetic output dict using stored result
        result = self._task_data.get("result", "")
        if result:
            return {
                "stdout": result,
                "stderr": "",
                "status": "running",
                "note": "Showing initial tool result. Use get_background_shell_output tool for live output.",
            }
        return None

    def _get_shell_status(self) -> Optional[Dict[str, Any]]:
        """Get shell status - returns basic info since live fetch isn't available."""
        async_id = self._task_data.get("async_id")
        return {
            "shell_id": async_id,
            "status": "running",
            "note": "Live status unavailable from TUI. Use get_background_shell_status tool.",
        }

    def action_refresh(self) -> None:
        """Refresh the output display."""
        try:
            # Update output
            output_widget = self.query_one("#output_content", Static)
            output_widget.update(self._build_output())

            # Update header with status
            header_widget = self.query_one("#output_header", Static)
            header_widget.update(self._build_output_header())

            # Update info section (for elapsed time)
            info_widget = self.query_one("#info_section", Static)
            info_widget.update(self._build_info())

            # Scroll to bottom
            scroll_container = self.query_one(".output-section", ScrollableContainer)
            scroll_container.scroll_end(animate=False)
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "close_btn" or event.button.id == "back_btn":
            self.dismiss()
        elif event.button.id == "refresh_btn":
            self.action_refresh()

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss()


class BackgroundTasksModal(ModalScreen[None]):
    """Modal screen showing background operations with status details."""

    BINDINGS = [
        ("escape", "close", "Close"),
    ]

    DEFAULT_CSS = """
    BackgroundTasksModal {
        align: center middle;
    }

    BackgroundTasksModal > Container {
        width: 90%;
        max-width: 100;
        height: auto;
        max-height: 70%;
        background: #1c2128;
        border: solid #d29922;
        padding: 1 2;
    }

    BackgroundTasksModal .modal-header {
        height: auto;
        width: 100%;
        padding: 0 1;
        margin-bottom: 1;
    }

    BackgroundTasksModal .header-row {
        height: auto;
        width: 100%;
        layout: horizontal;
    }

    BackgroundTasksModal .modal-title {
        text-style: bold;
        width: 1fr;
        color: #d29922;
    }

    BackgroundTasksModal .modal-stats {
        width: auto;
        padding-right: 2;
    }

    BackgroundTasksModal .modal-close {
        width: auto;
        min-width: 3;
        background: transparent;
        border: none;
        color: #8b949e;
    }

    BackgroundTasksModal .modal-close:hover {
        color: #e6edf3;
    }

    BackgroundTasksModal .modal-body {
        height: 1fr;
        max-height: 35;
        overflow-y: auto;
        padding: 0;
    }

    BackgroundTasksModal BackgroundTaskRow {
        height: auto;
        width: 100%;
        padding: 1;
        margin-bottom: 1;
        background: #0d1117;
        border-left: solid #d29922;
    }

    BackgroundTasksModal BackgroundTaskRow:hover {
        background: #161b22;
    }

    BackgroundTasksModal BackgroundTaskRow:focus {
        background: #21262d;
        border-left: solid #58a6ff;
    }

    BackgroundTasksModal .task-content {
        height: auto;
        width: 100%;
    }

    BackgroundTasksModal .modal-footer {
        height: auto;
        width: 100%;
        align: center middle;
        margin-top: 1;
        padding-top: 1;
        border-top: solid #30363d;
    }

    BackgroundTasksModal .close-button {
        width: auto;
        min-width: 16;
    }

    BackgroundTasksModal .empty-message {
        padding: 2;
        text-align: center;
        color: #8b949e;
    }
    """

    def __init__(
        self,
        background_tasks: List[Dict[str, Any]],
        agent_id: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.background_tasks = background_tasks or []
        self.agent_id = agent_id

    def compose(self) -> ComposeResult:
        count = len(self.background_tasks)

        with Container():
            # Header section
            with Container(classes="modal-header"):
                with Container(classes="header-row"):
                    title = "Background Operations"
                    if self.agent_id:
                        title += f" . {self.agent_id}"
                    yield Static(title, classes="modal-title")
                    yield Static(f"{count} running", classes="modal-stats")
                    yield Button("✕", variant="default", classes="modal-close", id="close_btn")

            # Task list
            with ScrollableContainer(classes="modal-body"):
                if not self.background_tasks:
                    yield Static(
                        "No background operations running.",
                        classes="empty-message",
                    )
                else:
                    for i, task in enumerate(self.background_tasks):
                        yield BackgroundTaskRow(task, i, self.agent_id, id=f"task_row_{i}")

            # Footer
            with Container(classes="modal-footer"):
                yield Button("Close (Esc)", variant="primary", classes="close-button", id="close_btn_footer")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id in ("close_btn", "close_btn_footer"):
            self.dismiss()

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss()
