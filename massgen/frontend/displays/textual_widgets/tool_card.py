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
    "workspace": {
        "icon": "📝",
        "color": "#4fc1ff",
        "patterns": [
            "workspace",
            "new_answer",
            "vote",
            "answer",
            "coordination",
        ],
    },
    "subagent": {
        "icon": "🚀",
        "color": "#a371f7",
        "patterns": [
            "spawn_subagent",
            "subagent",
            "list_subagents",
            "get_subagent_result",
            "check_subagent_status",
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

        # Hook execution tracking (for display in TUI)
        self._pre_hooks: list = []  # Hooks that ran before tool
        self._post_hooks: list = []  # Hooks that ran after tool

        # Subagent-specific state
        self._is_subagent = self._category["category"] == "subagent"
        self._expanded = False  # For showing workspace inline
        self._subagent_tasks: list[dict] = []  # Parsed subagent task list
        self._workspace_content: Optional[str] = None  # Subagent workspace output

    def render(self) -> Text:
        """Render the card as a single-line summary."""
        if self._is_subagent:
            return self._render_subagent()
        return self._render_collapsed()

    def _render_collapsed(self) -> Text:
        """Render card view: with pre-hooks, tool info, and post-hooks.

        Design with hooks:
        ```
        🪝 timeout_hard: allowed
        ▶ 📁 filesystem/write_file                              ⏳ running...
          {"content": "In circuits humming...", "path": "/tmp/poem.txt"}
        ```
        or completed with post-hooks:
        ```
          📁 filesystem/read_file                               ✓ (0.3s)
          {"path": "/tmp/example.txt"}
          → File contents: Hello world...
        🪝 mid_stream: +context from agent_b
        ```
        """
        text = Text()

        # Pre-hooks (shown above tool line)
        for hook in self._pre_hooks:
            hook_name = hook.get("hook_name", "unknown")
            decision = hook.get("decision", "allow")
            reason = hook.get("reason", "")

            if decision == "deny":
                text.append("  🚫 ", style="bold red")
                text.append(f"{hook_name}: ", style="red")
                text.append("BLOCKED", style="bold red")
                if reason:
                    text.append(f" - {reason[:40]}...\n" if len(reason) > 40 else f" - {reason}\n", style="dim red")
                else:
                    text.append("\n")
            else:
                text.append("  🪝 ", style="dim magenta")
                text.append(f"{hook_name}: ", style="dim magenta")
                text.append("allowed\n", style="dim")

        # Tool card content
        icon = self._category["icon"]
        status_icon = self.STATUS_ICONS.get(self._status, "⏳")
        elapsed = self._get_elapsed_str()

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

        # Padding to align status on right (use wider terminal width)
        name_len = len(self._display_name) + 4
        padding = max(1, 90 - name_len)
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
            if len(args_display) > 120:
                args_display = args_display[:117] + "..."
            text.append(args_display, style="dim")

        # Line 3: Result or error preview (if completed)
        if self._result:
            text.append("\n    → ")
            result_preview = self._result.replace("\n", " ")
            if len(result_preview) > 110:
                result_preview = result_preview[:107] + "..."
            text.append(result_preview, style="dim green")
        elif self._error:
            text.append("\n    ✗ ")
            error_preview = self._error.replace("\n", " ")
            if len(error_preview) > 110:
                error_preview = error_preview[:107] + "..."
            text.append(error_preview, style="dim red")

        # Post-hooks (shown below result)
        for hook in self._post_hooks:
            hook_name = hook.get("hook_name", "unknown")
            injection_preview = hook.get("injection_preview", "")

            text.append("\n  🪝 ", style="dim magenta")
            text.append(f"{hook_name}", style="dim magenta")

            if injection_preview:
                preview = injection_preview[:40] + "..." if len(injection_preview) > 40 else injection_preview
                preview = preview.replace("\n", " ")
                text.append(f": +{preview}", style="dim")

        return text

    def _render_subagent(self) -> Text:
        """Render specialized subagent card with task bullets and workspace.

        Design:
        ```
        🚀 Spawn Subagents                                    ⏳ running...
          • Task 1: Research competitor analysis
          • Task 2: Analyze market trends
          • Task 3: Generate summary report
        [Click to expand workspace]
        ```
        """
        text = Text()

        # Header line with pulsing indicator when running
        icon = self._category["icon"]
        status_icon = self.STATUS_ICONS.get(self._status, "⏳")
        elapsed = self._get_elapsed_str()

        # Running indicator
        if self._status == "running":
            text.append("▶ ", style="bold #a371f7")
        else:
            text.append("  ")

        text.append(f"{icon} ", style=self._category["color"])

        if self._status == "running":
            text.append(self._display_name, style="bold #a371f7")
        else:
            text.append(self._display_name, style="bold")

        # Padding for status alignment (use wider terminal width)
        name_len = len(self._display_name) + 4
        padding = max(1, 90 - name_len)
        text.append(" " * padding)

        if self._status == "success":
            text.append(f"{status_icon}", style="bold green")
        elif self._status == "error":
            text.append(f"{status_icon}", style="bold red")
        elif self._status == "running":
            text.append(f"{status_icon}", style="bold #a371f7")
        else:
            text.append(f"{status_icon}", style="#a371f7")

        if elapsed:
            text.append(f" {elapsed}", style="dim")
        elif self._status == "running":
            text.append(" spawning...", style="italic #a371f7")

        # Render bullet list of subagent tasks
        if self._subagent_tasks:
            for i, task in enumerate(self._subagent_tasks):
                task_desc = task.get("description", task.get("prompt", f"Task {i + 1}"))
                task_status = task.get("status", "pending")

                # Status indicator for each task
                if task_status == "running":
                    bullet = "◉"
                    style = "bold #a371f7"
                elif task_status == "completed":
                    bullet = "✓"
                    style = "green"
                elif task_status == "error":
                    bullet = "✗"
                    style = "red"
                else:
                    bullet = "○"
                    style = "dim"

                text.append(f"\n    {bullet} ", style=style)
                # Truncate long descriptions
                if len(task_desc) > 60:
                    task_desc = task_desc[:57] + "..."
                text.append(task_desc, style="dim" if task_status == "pending" else style)
        elif self._params:
            # Fallback: show params if no parsed tasks
            text.append("\n    ")
            args_display = self._params
            if len(args_display) > 70:
                args_display = args_display[:67] + "..."
            text.append(args_display, style="dim")

        # Expanded workspace content
        if self._expanded and self._workspace_content:
            text.append("\n    ┌─ Workspace ─────────────────────────────────\n", style="dim #a371f7")
            # Show workspace content with indentation
            lines = self._workspace_content.split("\n")[:10]  # Limit lines
            for line in lines:
                if len(line) > 65:
                    line = line[:62] + "..."
                text.append(f"    │ {line}\n", style="dim")
            if len(self._workspace_content.split("\n")) > 10:
                text.append("    │ ...(more)...\n", style="dim italic")
            text.append("    └──────────────────────────────────────────", style="dim #a371f7")
        elif not self._expanded and (self._workspace_content or self._result):
            # Show expand hint
            text.append("\n    ", style="dim")
            text.append("[click to expand workspace]", style="dim italic #a371f7")

        # Result/error summary (when completed)
        if self._result and not self._expanded:
            text.append("\n    → ")
            result_preview = self._result.replace("\n", " ")
            if len(result_preview) > 55:
                result_preview = result_preview[:52] + "..."
            text.append(result_preview, style="dim green")
        elif self._error:
            text.append("\n    ✗ ")
            error_preview = self._error.replace("\n", " ")
            if len(error_preview) > 55:
                error_preview = error_preview[:52] + "..."
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
        """Handle click - toggle expansion for subagents, or show modal for others."""
        if self._is_subagent:
            self.toggle_expanded()
        else:
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

    def add_pre_hook(
        self,
        hook_name: str,
        decision: str,
        reason: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
    ) -> None:
        """Add a pre-tool hook execution to display.

        Args:
            hook_name: Name of the hook
            decision: "allow", "deny", or "error"
            reason: Reason for the decision (if any)
            execution_time_ms: How long the hook took
        """
        self._pre_hooks.append(
            {
                "hook_name": hook_name,
                "decision": decision,
                "reason": reason,
                "execution_time_ms": execution_time_ms,
                "timestamp": datetime.now(),
            },
        )
        self.refresh()

    def add_post_hook(
        self,
        hook_name: str,
        injection_preview: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
    ) -> None:
        """Add a post-tool hook execution to display.

        Args:
            hook_name: Name of the hook
            injection_preview: Preview of injected content (if any)
            execution_time_ms: How long the hook took
        """
        self._post_hooks.append(
            {
                "hook_name": hook_name,
                "injection_preview": injection_preview,
                "execution_time_ms": execution_time_ms,
                "timestamp": datetime.now(),
            },
        )
        self.refresh()

    # === Subagent-specific methods ===

    def set_subagent_tasks(self, tasks: list[dict]) -> None:
        """Set the list of subagent tasks for display.

        Args:
            tasks: List of task dicts with keys:
                - description or prompt: Task description text
                - status: "pending", "running", "completed", or "error"
                - agent_id: Optional agent identifier
        """
        self._subagent_tasks = tasks
        self.refresh()

    def update_subagent_task_status(self, task_index: int, status: str) -> None:
        """Update the status of a specific subagent task.

        Args:
            task_index: Index of the task to update
            status: New status ("pending", "running", "completed", "error")
        """
        if 0 <= task_index < len(self._subagent_tasks):
            self._subagent_tasks[task_index]["status"] = status
            self.refresh()

    def set_workspace_content(self, content: str) -> None:
        """Set the workspace content for expanded view.

        Args:
            content: The workspace/output content to display when expanded.
        """
        self._workspace_content = content
        self.refresh()

    def toggle_expanded(self) -> None:
        """Toggle the expanded state of the subagent card."""
        self._expanded = not self._expanded
        if self._expanded:
            self.add_class("expanded")
        else:
            self.remove_class("expanded")
        self.refresh()

    @property
    def is_expanded(self) -> bool:
        """Check if the subagent card is expanded."""
        return self._expanded

    @property
    def subagent_tasks(self) -> list[dict]:
        """Get the list of subagent tasks."""
        return self._subagent_tasks

    @property
    def workspace_content(self) -> Optional[str]:
        """Get the workspace content."""
        return self._workspace_content

    @property
    def pre_hooks(self) -> list:
        """Get list of pre-hooks for modal display."""
        return self._pre_hooks

    @property
    def post_hooks(self) -> list:
        """Get list of post-hooks for modal display."""
        return self._post_hooks

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
