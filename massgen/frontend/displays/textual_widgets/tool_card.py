# -*- coding: utf-8 -*-
"""
Tool Call Card Widget for MassGen TUI.

Provides clickable cards for displaying tool calls with their
parameters, results, and status. Clicking opens a detail modal.
"""

from datetime import datetime
from typing import Optional

from rich.text import Text
from textual.message import Message
from textual.widgets import Static

# Tool category detection - maps tool names to semantic categories
TOOL_CATEGORIES = {
    "filesystem": {
        "icon": "📁",
        "color": "#4ec9b0",
        "patterns": [
            "read_file",
            "write_file",
            "list_directory",
            "create_directory",
            "delete_file",
            "move_file",
            "copy_file",
            "file_exists",
            "get_file_info",
            "read_multiple_files",
            "edit_file",
            "directory_tree",
            "search_files",
            "find_files",
        ],
    },
    "web": {
        "icon": "🌐",
        "color": "#569cd6",
        "patterns": [
            "web_search",
            "search_web",
            "google_search",
            "fetch_url",
            "http_request",
            "browse",
            "scrape",
            "download",
        ],
    },
    "code": {
        "icon": "💻",
        "color": "#dcdcaa",
        "patterns": [
            "execute_command",
            "run_code",
            "bash",
            "python",
            "shell",
            "terminal",
            "exec",
            "run_script",
            "execute",
        ],
    },
    "database": {
        "icon": "🗄️",
        "color": "#c586c0",
        "patterns": [
            "query",
            "sql",
            "database",
            "db_",
            "select",
            "insert",
            "update",
            "delete_record",
        ],
    },
    "git": {
        "icon": "📦",
        "color": "#f14e32",
        "patterns": [
            "git_",
            "commit",
            "push",
            "pull",
            "clone",
            "branch",
            "merge",
            "checkout",
            "diff",
            "log",
            "status",
        ],
    },
    "api": {
        "icon": "🔌",
        "color": "#ce9178",
        "patterns": [
            "api_",
            "request",
            "post",
            "get",
            "put",
            "patch",
            "rest",
            "graphql",
            "endpoint",
        ],
    },
    "ai": {
        "icon": "🤖",
        "color": "#9cdcfe",
        "patterns": [
            "generate",
            "complete",
            "chat",
            "embed",
            "model",
            "inference",
            "predict",
            "classify",
        ],
    },
    "memory": {
        "icon": "🧠",
        "color": "#b5cea8",
        "patterns": [
            "memory",
            "remember",
            "recall",
            "store",
            "retrieve",
            "knowledge",
            "context",
        ],
    },
}


def get_tool_category(tool_name: str) -> dict:
    """Get category info for a tool name.

    Args:
        tool_name: The tool name to categorize.

    Returns:
        Dict with icon, color, and category name.
    """
    tool_lower = tool_name.lower()

    # Check MCP tools (format: mcp__server__tool)
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__")
        if len(parts) >= 3:
            actual_tool = parts[-1]
            tool_lower = actual_tool.lower()

    # Check against category patterns
    for category_name, info in TOOL_CATEGORIES.items():
        for pattern in info["patterns"]:
            if pattern in tool_lower:
                return {
                    "icon": info["icon"],
                    "color": info["color"],
                    "category": category_name,
                }

    # Default to generic tool
    return {"icon": "🔧", "color": "#858585", "category": "tool"}


def format_tool_display_name(tool_name: str) -> str:
    """Format tool name for display.

    Args:
        tool_name: Raw tool name.

    Returns:
        Formatted display name.
    """
    # Handle MCP tools: mcp__server__tool -> server/tool
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__")
        if len(parts) >= 3:
            return f"{parts[1]}/{parts[2]}"
        elif len(parts) == 2:
            return parts[1]

    # Handle snake_case
    return tool_name.replace("_", " ").title()


class ToolCallCard(Static):
    """Clickable card showing a tool call with status, params, and result.

    Clicking the card posts a ToolCardClicked message that can be
    handled to show a detail modal.

    Attributes:
        tool_name: Name of the tool being called.
        tool_type: Type of tool (mcp, custom, etc.).
        status: Current status (running, success, error).
    """

    class ToolCardClicked(Message):
        """Posted when a tool card is clicked."""

        def __init__(self, card: "ToolCallCard") -> None:
            self.card = card
            super().__init__()

    # Enable clicking on the widget
    can_focus = True

    STATUS_ICONS = {
        "running": "⏳",
        "success": "✓",
        "error": "✗",
    }

    def __init__(
        self,
        tool_name: str,
        tool_type: str = "unknown",
        call_id: Optional[str] = None,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """Initialize the tool card.

        Args:
            tool_name: Name of the tool.
            tool_type: Type (mcp, custom, etc.).
            call_id: Optional unique call identifier.
            id: Optional DOM ID.
            classes: Optional CSS classes.
        """
        super().__init__(id=id, classes=classes)
        self.tool_name = tool_name
        self.tool_type = tool_type
        self.call_id = call_id
        self._status = "running"
        self._start_time = datetime.now()
        self._end_time: Optional[datetime] = None
        self._params: Optional[str] = None  # Truncated for display
        self._params_full: Optional[str] = None  # Full args for modal
        self._result: Optional[str] = None  # Truncated for display
        self._result_full: Optional[str] = None  # Full result for modal
        self._error: Optional[str] = None

        # Get category info for styling
        self._category = get_tool_category(tool_name)
        self._display_name = format_tool_display_name(tool_name)

        # Add type class for styling
        self.add_class(f"type-{self._category['category']}")
        self.add_class("status-running")

    def render(self) -> Text:
        """Render the card as a single-line summary."""
        return self._render_collapsed()

    def _render_collapsed(self) -> Text:
        """Render card view: 2-3 lines with name, args, result.

        Design (2-3 lines per tool):
        ```
        ▶ 📁 filesystem/write_file                              ⏳ running...
          {"content": "In circuits humming...", "path": "/tmp/poem.txt"}
        ```
        or completed:
        ```
          📁 filesystem/read_file                               ✓ (0.3s)
          {"path": "/tmp/example.txt"}
          → File contents: Hello world...
        ```
        """
        icon = self._category["icon"]
        status_icon = self.STATUS_ICONS.get(self._status, "⏳")
        elapsed = self._get_elapsed_str()

        text = Text()

        # Line 1: Icon + name + status
        if self._status == "running":
            text.append("▶ ", style="bold cyan")
        else:
            text.append("  ")

        text.append(f"{icon} ", style=self._category["color"])

        if self._status == "running":
            text.append(self._display_name, style="bold cyan")
        else:
            text.append(self._display_name, style="bold")

        # Padding to align status on right
        name_len = len(self._display_name) + 4
        padding = max(1, 55 - name_len)
        text.append(" " * padding)

        if self._status == "success":
            text.append(f"{status_icon}", style="bold green")
        elif self._status == "error":
            text.append(f"{status_icon}", style="bold red")
        elif self._status == "running":
            text.append(f"{status_icon}", style="bold yellow")
        else:
            text.append(f"{status_icon}", style="yellow")

        if elapsed:
            text.append(f" {elapsed}", style="dim")
        elif self._status == "running":
            text.append(" running...", style="italic yellow")

        # Line 2: Args (if available) - show more content
        if self._params:
            text.append("\n    ")
            args_display = self._params
            if len(args_display) > 70:
                args_display = args_display[:67] + "..."
            text.append(args_display, style="dim")

        # Line 3: Result or error preview (if completed)
        if self._result:
            text.append("\n    → ")
            result_preview = self._result.replace("\n", " ")
            if len(result_preview) > 60:
                result_preview = result_preview[:57] + "..."
            text.append(result_preview, style="dim green")
        elif self._error:
            text.append("\n    ✗ ")
            error_preview = self._error.replace("\n", " ")
            if len(error_preview) > 60:
                error_preview = error_preview[:57] + "..."
            text.append(error_preview, style="dim red")

        return text

    def _get_elapsed_str(self) -> str:
        """Get elapsed time as formatted string."""
        end = self._end_time or datetime.now()
        elapsed = (end - self._start_time).total_seconds()

        if elapsed < 60:
            return f"({elapsed:.1f}s)"
        else:
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            return f"({mins}m{secs}s)"

    def on_click(self) -> None:
        """Handle click to show detail modal."""
        self.post_message(self.ToolCardClicked(self))

    def set_params(self, params: str, params_full: Optional[str] = None) -> None:
        """Set the tool parameters.

        Args:
            params: Truncated parameters for card display.
            params_full: Full parameters for modal (if different from params).
        """
        self._params = params
        self._params_full = params_full if params_full else params
        self.refresh()

    def set_result(self, result: str, result_full: Optional[str] = None) -> None:
        """Set successful result.

        Args:
            result: Truncated result for card display.
            result_full: Full result for modal (if different from result).
        """
        self._status = "success"
        self._result = result
        self._result_full = result_full if result_full else result
        self._end_time = datetime.now()
        self.remove_class("status-running")
        self.add_class("status-success")
        self.refresh()

    def set_error(self, error: str) -> None:
        """Set error result.

        Args:
            error: Error message to display.
        """
        self._status = "error"
        self._error = error
        self._end_time = datetime.now()
        self.remove_class("status-running")
        self.add_class("status-error")
        self.refresh()

    @property
    def status(self) -> str:
        """Get current status."""
        return self._status

    @property
    def display_name(self) -> str:
        """Get display name."""
        return self._display_name

    @property
    def icon(self) -> str:
        """Get category icon."""
        return self._category["icon"]

    @property
    def params(self) -> Optional[str]:
        """Get full parameters string for modal."""
        return self._params_full or self._params

    @property
    def result(self) -> Optional[str]:
        """Get full result string for modal."""
        return self._result_full or self._result

    @property
    def error(self) -> Optional[str]:
        """Get error message."""
        return self._error

    @property
    def elapsed_str(self) -> str:
        """Get elapsed time string for modal."""
        return self._get_elapsed_str()
