# -*- coding: utf-8 -*-
"""
Subagent Card Widget for MassGen TUI.

Rich display for spawned subagents with live progress bars, activity streaming,
and click-to-expand modal for detailed log viewing.
"""

from typing import Any, Callable, Dict, List, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.message import Message
from textual.timer import Timer
from textual.widgets import Static

from massgen.frontend.displays.log_streamer import LogStreamer
from massgen.subagent.models import SubagentDisplayData


class SubagentCard(Static, can_focus=True):
    """Rich card displaying spawned subagents with live progress.

    Design:
    ```
    ┌─ 🚀 Spawn Subagents ──────────────────────────── 3/5 ● 2 active ┐
    │                                                                  │
    │  ✓ bio_researcher        ████████████ 100%  12.3s   47 files    │
    │    └─ "Completed analysis of Bob's research papers..."          │
    │                                                                  │
    │  ● discog_researcher     ████████░░░░  68%  8.2s    23 files    │
    │    └─ Tool: read_file → workspace/temp/discog_researc...        │
    │                                                                  │
    │  ○ summarizer            ░░░░░░░░░░░░   0%  waiting...          │
    └──────────────────────────────────────────────────────────────────┘
    ```

    Features:
    - Progress bars per subagent (time-based: elapsed/timeout)
    - Live activity display (last log line)
    - Workspace file count
    - Single click to expand inline, double click for modal
    - Keyboard navigation: Up/Down to select, Enter for modal, Space to expand
    - Auto-polling every 500ms while any subagent is running
    """

    BINDINGS = [
        ("up", "select_prev", "Previous"),
        ("down", "select_next", "Next"),
        ("enter", "open_selected", "Open Modal"),
        ("space", "toggle_expand", "Expand"),
    ]

    class OpenModal(Message):
        """Message posted when user clicks to open subagent modal."""

        def __init__(self, subagent: SubagentDisplayData, all_subagents: List[SubagentDisplayData]) -> None:
            self.subagent = subagent
            self.all_subagents = all_subagents
            super().__init__()

    DEFAULT_CSS = """
    SubagentCard {
        width: 100%;
        height: auto;
        min-height: 3;
        padding: 0 1;
        margin: 0 0 1 1;
        background: #1a1f2e;
        border-left: thick #7c3aed;
    }

    SubagentCard:hover {
        background: #1e2436;
    }

    SubagentCard .subagent-header {
        text-style: bold;
        color: #7c3aed;
        margin-bottom: 1;
    }

    SubagentCard .subagent-completed {
        color: #7ee787;
    }

    SubagentCard .subagent-running {
        color: #a371f7;
        text-style: bold;
    }

    SubagentCard .subagent-pending {
        color: #6e7681;
    }

    SubagentCard .subagent-error {
        color: #f85149;
    }

    SubagentCard .subagent-timeout {
        color: #d29922;
    }

    SubagentCard .progress-bar {
        color: #a371f7;
    }

    SubagentCard .progress-empty {
        color: #30363d;
    }

    SubagentCard .activity-line {
        color: #8b949e;
        text-style: italic;
    }

    SubagentCard .file-count {
        color: #6e7681;
    }
    """

    # Status indicators
    STATUS_ICONS = {
        "completed": "✓",
        "running": "●",
        "pending": "○",
        "error": "✗",
        "timeout": "⏱",
        "failed": "✗",
    }

    # Progress bar characters
    PROGRESS_FILLED = "█"
    PROGRESS_EMPTY = "░"
    PROGRESS_BAR_WIDTH = 12

    # Polling interval in seconds
    POLL_INTERVAL = 0.5

    def __init__(
        self,
        subagents: Optional[List[SubagentDisplayData]] = None,
        tool_call_id: Optional[str] = None,
        status_callback: Optional[Callable[[str], Optional[SubagentDisplayData]]] = None,
        id: Optional[str] = None,
    ) -> None:
        """Initialize the subagent card.

        Args:
            subagents: List of SubagentDisplayData objects
            tool_call_id: ID of the tool call that spawned these subagents
            status_callback: Callback to get updated status for a subagent ID
            id: Widget ID
        """
        super().__init__(id=id)
        self._subagents = subagents or []
        self._tool_call_id = tool_call_id
        self._status_callback = status_callback
        self._poll_timer: Optional[Timer] = None
        self._log_streamers: Dict[str, LogStreamer] = {}
        self._selected_index = 0  # For keyboard navigation
        self._expanded = False  # Expandable inline view state
        self._last_click_time = 0.0  # For double-click detection

    def compose(self) -> ComposeResult:
        yield Static(self._build_content())

    def on_mount(self) -> None:
        """Start polling when mounted if any subagents are running."""
        self._start_polling_if_needed()

    def on_unmount(self) -> None:
        """Stop polling when unmounted."""
        self._stop_polling()

    def on_click(self) -> None:
        """Handle click: single click toggles expand, double click opens modal."""
        import time

        current_time = time.time()
        time_since_last = current_time - self._last_click_time
        self._last_click_time = current_time

        # Double click detection (within 0.4 seconds)
        if time_since_last < 0.4:
            # Double click - open modal
            self._open_modal()
        else:
            # Single click - toggle expand
            self._toggle_expand()

    def _toggle_expand(self) -> None:
        """Toggle the expanded state to show/hide inline details."""
        self._expanded = not self._expanded
        self._refresh_content()

    def _open_modal(self) -> None:
        """Open the subagent modal for detailed view."""
        if self._subagents:
            # Get the first running subagent, or first overall
            selected = None
            for sa in self._subagents:
                if sa.status == "running":
                    selected = sa
                    break
            if not selected:
                selected = self._subagents[0]

            self.post_message(self.OpenModal(selected, self._subagents))

    def _start_polling_if_needed(self) -> None:
        """Start the polling timer if any subagent is still running."""
        if self._poll_timer is not None:
            return  # Already polling

        has_running = any(sa.status in ("running", "pending") for sa in self._subagents)
        if has_running:
            self._poll_timer = self.set_interval(self.POLL_INTERVAL, self._poll_status)

    def _stop_polling(self) -> None:
        """Stop the polling timer."""
        if self._poll_timer is not None:
            self._poll_timer.stop()
            self._poll_timer = None

    def _poll_status(self) -> None:
        """Poll for updated subagent status."""
        if not self._status_callback:
            return

        updated = False
        new_subagents = []

        for sa in self._subagents:
            if sa.status in ("running", "pending"):
                # Get updated status
                new_data = self._status_callback(sa.id)
                if new_data:
                    new_subagents.append(new_data)
                    updated = True
                else:
                    new_subagents.append(sa)
            else:
                new_subagents.append(sa)

        if updated:
            self._subagents = new_subagents
            self._refresh_content()

            # Check if we should stop polling
            if not any(sa.status in ("running", "pending") for sa in self._subagents):
                self._stop_polling()

    def _refresh_content(self) -> None:
        """Refresh the displayed content."""
        try:
            content_widget = self.query_one(Static)
            content_widget.update(self._build_content())
        except Exception:
            pass

    def _build_content(self) -> Text:
        """Build the card content as Rich Text."""
        text = Text()

        if not self._subagents:
            text.append("🚀 No subagents spawned", style="dim")
            return text

        # Count statistics
        total = len(self._subagents)
        completed = sum(1 for sa in self._subagents if sa.status == "completed")
        running = sum(1 for sa in self._subagents if sa.status == "running")
        errors = sum(1 for sa in self._subagents if sa.status in ("error", "failed", "timeout"))

        # Header with expand indicator
        expand_indicator = "▼" if self._expanded else "▶"
        status_text = ""
        if running > 0:
            status_text = f" ● {running} active"
        elif errors > 0:
            status_text = f" ✗ {errors} failed"

        text.append(f"{expand_indicator} ", style="dim")
        text.append(f"🚀 Spawn Subagents ({completed}/{total}){status_text}\n", style="bold #7c3aed")

        # Render each subagent
        for idx, sa in enumerate(self._subagents):
            is_selected = idx == self._selected_index
            self._render_subagent_row(text, sa, is_selected)

        # Footer hint
        if self._expanded:
            text.append("\n  (click to collapse, double-click for full modal)", style="dim italic")
        else:
            text.append("\n  (click to expand, double-click for full modal)", style="dim italic")

        return text

    def _render_subagent_row(self, text: Text, sa: SubagentDisplayData, is_selected: bool = False) -> None:
        """Render a single subagent row.

        Format (collapsed):
          ● subagent_id        ████████░░░░  68%  8.2s   23 files
            └─ Last activity or message...

        Format (expanded):
          ● subagent_id        ████████░░░░  68%  8.2s   23 files
            Task: Research topic X
            └─ [Recent log lines]

        Args:
            text: Rich Text to append to
            sa: SubagentDisplayData object
            is_selected: Whether this row is currently selected
        """
        # Status icon and color
        icon = self.STATUS_ICONS.get(sa.status, "○")
        if sa.status == "completed":
            style = "#7ee787"
        elif sa.status == "running":
            style = "bold #a371f7"
        elif sa.status in ("error", "failed"):
            style = "#f85149"
        elif sa.status == "timeout":
            style = "#d29922"
        else:
            style = "#6e7681"

        # Selection indicator
        selection_marker = "» " if is_selected else "  "

        # Truncate ID for display
        display_id = sa.id[:20] if len(sa.id) > 20 else sa.id
        display_id = display_id.ljust(20)

        # Progress bar
        progress_bar = self._render_progress_bar(sa.progress_percent)

        # Time display
        if sa.status == "pending":
            time_str = "waiting..."
        else:
            time_str = f"{sa.elapsed_seconds:.1f}s"

        # File count
        file_str = f"{sa.workspace_file_count} files" if sa.workspace_file_count > 0 else ""

        # Main row with selection marker
        text.append(selection_marker, style="bold #58a6ff" if is_selected else "")
        text.append(f"{icon} ", style=style)
        text.append(f"{display_id} ", style=style)
        text.append(f"{progress_bar} ", style="#a371f7")
        text.append(f"{sa.progress_percent:3d}%  ", style="#8b949e")
        text.append(f"{time_str:10s}", style="#8b949e")
        if file_str:
            text.append(f"  {file_str}", style="#6e7681")
        text.append("\n")

        # Show more details when expanded
        if self._expanded:
            # Show task description
            if sa.task:
                task_preview = sa.task[:70] + "..." if len(sa.task) > 70 else sa.task
                text.append(f"      Task: {task_preview}\n", style="#8b949e")

            # Show workspace path
            if sa.workspace_path:
                text.append(f"      Path: {sa.workspace_path}\n", style="dim #6e7681")

            # Show error if any
            if sa.status in ("error", "failed") and sa.error:
                error_preview = sa.error[:100] + "..." if len(sa.error) > 100 else sa.error
                text.append(f"      Error: {error_preview}\n", style="#f85149")

            # Show answer preview if completed
            if sa.status == "completed" and sa.answer_preview:
                answer_preview = sa.answer_preview[:100] + "..." if len(sa.answer_preview) > 100 else sa.answer_preview
                text.append(f"      Result: {answer_preview}\n", style="#7ee787")

        # Activity line (always show, but shorter when collapsed)
        activity = self._get_activity_line(sa)
        if activity:
            text.append(f"      └─ {activity}\n", style="italic #8b949e")

    def _render_progress_bar(self, percent: int) -> str:
        """Render a progress bar string.

        Args:
            percent: Progress percentage (0-100)

        Returns:
            Progress bar string like "████████░░░░"
        """
        filled = int(self.PROGRESS_BAR_WIDTH * percent / 100)
        empty = self.PROGRESS_BAR_WIDTH - filled
        return self.PROGRESS_FILLED * filled + self.PROGRESS_EMPTY * empty

    def _get_activity_line(self, sa: SubagentDisplayData) -> str:
        """Get the activity line to display for a subagent.

        Args:
            sa: SubagentDisplayData object

        Returns:
            Activity string to display (truncated to ~60 chars)
        """
        max_len = 60

        if sa.status == "completed" and sa.answer_preview:
            preview = sa.answer_preview.replace("\n", " ").strip()
            if len(preview) > max_len:
                preview = preview[: max_len - 3] + "..."
            return f'"{preview}"'

        if sa.status in ("error", "failed") and sa.error:
            error = sa.error.replace("\n", " ").strip()
            if len(error) > max_len:
                error = error[: max_len - 3] + "..."
            return f"Error: {error}"

        if sa.status == "timeout":
            return "Timed out"

        if sa.status == "running" and sa.last_log_line:
            line = sa.last_log_line.replace("\n", " ").strip()
            if len(line) > max_len:
                line = line[: max_len - 3] + "..."
            return line

        if sa.status == "pending":
            return "Queued"

        return ""

    @property
    def subagents(self) -> List[SubagentDisplayData]:
        """Get the current list of subagents."""
        return self._subagents

    def update_subagents(self, subagents: List[SubagentDisplayData]) -> None:
        """Update the list of subagents.

        Args:
            subagents: New list of SubagentDisplayData objects
        """
        self._subagents = subagents
        self._refresh_content()
        self._start_polling_if_needed()

    def update_subagent(self, subagent_id: str, data: SubagentDisplayData) -> None:
        """Update a specific subagent's data.

        Args:
            subagent_id: ID of the subagent to update
            data: New SubagentDisplayData
        """
        for i, sa in enumerate(self._subagents):
            if sa.id == subagent_id:
                self._subagents[i] = data
                break
        self._refresh_content()

    def set_status_callback(self, callback: Callable[[str], Optional[SubagentDisplayData]]) -> None:
        """Set the callback for getting updated subagent status.

        Args:
            callback: Function that takes subagent_id and returns SubagentDisplayData
        """
        self._status_callback = callback
        self._start_polling_if_needed()

    # --- Keyboard navigation actions ---

    def action_select_prev(self) -> None:
        """Select the previous subagent in the list."""
        if not self._subagents:
            return
        self._selected_index = (self._selected_index - 1) % len(self._subagents)
        self._refresh_content()

    def action_select_next(self) -> None:
        """Select the next subagent in the list."""
        if not self._subagents:
            return
        self._selected_index = (self._selected_index + 1) % len(self._subagents)
        self._refresh_content()

    def action_open_selected(self) -> None:
        """Open the modal for the currently selected subagent."""
        if not self._subagents:
            return
        selected = self._subagents[self._selected_index]
        self.post_message(self.OpenModal(selected, self._subagents))

    def action_toggle_expand(self) -> None:
        """Toggle the expanded state."""
        self._toggle_expand()

    @classmethod
    def from_spawn_result(
        cls,
        result: Dict[str, Any],
        tool_call_id: Optional[str] = None,
        status_callback: Optional[Callable[[str], Optional[SubagentDisplayData]]] = None,
    ) -> "SubagentCard":
        """Create a SubagentCard from spawn_subagents tool result.

        Args:
            result: Result dictionary from spawn_subagents tool
            tool_call_id: ID of the tool call
            status_callback: Callback for status updates

        Returns:
            Configured SubagentCard instance
        """
        subagents = []

        # Parse spawned subagents from result
        spawned = result.get("spawned_subagents", result.get("subagents", []))
        for sa_data in spawned:
            subagents.append(
                SubagentDisplayData(
                    id=sa_data.get("id", sa_data.get("subagent_id", "unknown")),
                    task=sa_data.get("task", ""),
                    status="running",  # Just spawned, assume running
                    progress_percent=0,
                    elapsed_seconds=0.0,
                    timeout_seconds=sa_data.get("timeout_seconds", 300),
                    workspace_path=sa_data.get("workspace", ""),
                    workspace_file_count=0,
                    last_log_line="",
                ),
            )

        return cls(
            subagents=subagents,
            tool_call_id=tool_call_id,
            status_callback=status_callback,
        )
