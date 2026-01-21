# -*- coding: utf-8 -*-
"""
Tool Call Card Widget for MassGen TUI.

Provides clickable cards for displaying tool calls with their
parameters, results, and status. Clicking opens a detail modal.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Callable, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.events import Click
from textual.message import Message
from textual.widgets import Static

if TYPE_CHECKING:
    pass


class InjectionToggle(Static):
    """Clickable widget for toggling injection content expansion.

    This widget handles its own click event to toggle expansion,
    preventing the click from bubbling up to the parent ToolCallCard.
    """

    DEFAULT_CSS = """
    InjectionToggle {
        width: 100%;
        height: auto;
        min-height: 1;
        padding: 0;
        margin: 0;
    }

    InjectionToggle:hover {
        background: #21262d;
    }

    InjectionToggle.expanded {
        min-height: 5;
    }
    """

    def __init__(
        self,
        content: Text,
        toggle_callback: Callable[[], None],
        *,
        id: Optional[str] = None,
    ) -> None:
        """Initialize the injection toggle.

        Args:
            content: The Rich Text content to display.
            toggle_callback: Callback to invoke when clicked.
            id: Optional DOM ID.
        """
        super().__init__(id=id)
        self._content = content
        self._toggle_callback = toggle_callback

    def render(self) -> Text:
        """Render the injection toggle content."""
        return self._content

    def update_content(self, content: Text) -> None:
        """Update the displayed content."""
        self._content = content
        self.refresh()

    def on_click(self, event: Click) -> None:
        """Handle click - toggle injection and stop propagation."""
        from massgen.logger_config import logger

        logger.info("[InjectionToggle] on_click triggered!")
        event.stop()  # Prevent bubbling to parent ToolCallCard
        self._toggle_callback()
        logger.info("[InjectionToggle] callback completed")


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
        "background": "⚙️",  # For async/background operations (e.g., background shells)
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
        self._injection_expanded: bool = False  # Track if injection content is expanded

        # Subagent-specific state
        self._is_subagent = self._category["category"] == "subagent"
        self._expanded = False  # For showing workspace inline
        self._subagent_tasks: list[dict] = []  # Parsed subagent task list
        self._workspace_content: Optional[str] = None  # Subagent workspace output

        # Injection toggle widget (managed separately for click handling)
        self._injection_toggle: Optional[InjectionToggle] = None

        # Timer for updating elapsed time while running
        self._elapsed_timer = None

        # Background/async operation tracking
        self._async_id: Optional[str] = None  # e.g., shell_id for background shells
        self._is_background = False  # True if this is an async operation

    def on_mount(self) -> None:
        """Start the elapsed time timer when mounted."""
        if self._status == "running":
            self._start_elapsed_timer()

    def on_unmount(self) -> None:
        """Stop the timer when unmounted."""
        self._stop_elapsed_timer()

    def _start_elapsed_timer(self) -> None:
        """Start periodic refresh for elapsed time display."""
        if self._elapsed_timer is None:
            # Update every 100ms for smooth display
            self._elapsed_timer = self.set_interval(0.1, self._refresh_elapsed)

    def _stop_elapsed_timer(self) -> None:
        """Stop the elapsed time timer."""
        if self._elapsed_timer is not None:
            self._elapsed_timer.stop()
            self._elapsed_timer = None

    def _refresh_elapsed(self) -> None:
        """Refresh the display to update elapsed time."""
        if self._status == "running":
            self._refresh_main_content()
        else:
            # Tool completed, stop the timer
            self._stop_elapsed_timer()

    def _refresh_main_content(self) -> None:
        """Refresh the main content widget."""
        try:
            main_content = self.query_one("#tool-main-content", Static)
            main_content.update(self._render_main_content())
        except Exception:
            # Fallback if widget not found (e.g., not yet mounted)
            self.refresh()

    def _refresh_injection_toggle(self) -> None:
        """Refresh the injection toggle widget if it exists."""
        if self._injection_toggle:
            self._injection_toggle.update_content(self._render_injection_content())

    def _ensure_injection_toggle(self) -> None:
        """Ensure injection toggle exists if we have injection content."""
        if self._has_injection_content() and not self._injection_toggle:
            # Need to mount the injection toggle into the container
            try:
                container = self.query_one("#tool-card-content", Vertical)
                injection_content = self._render_injection_content()
                self._injection_toggle = InjectionToggle(
                    content=injection_content,
                    toggle_callback=self._toggle_injection,
                    id="injection-toggle",
                )
                container.mount(self._injection_toggle)
            except Exception as e:
                from massgen.logger_config import logger

                logger.warning(f"[ToolCallCard] _ensure_injection_toggle failed: {e}")

    def compose(self) -> ComposeResult:
        """Compose the card with optional injection toggle child."""
        # Use a Vertical container to stack main content and injection toggle
        with Vertical(id="tool-card-content"):
            # Main content widget
            yield Static(self._render_main_content(), id="tool-main-content")

            # Injection toggle (if we have injection content)
            if self._has_injection_content():
                injection_content = self._render_injection_content()
                self._injection_toggle = InjectionToggle(
                    content=injection_content,
                    toggle_callback=self._toggle_injection,
                    id="injection-toggle",
                )
                yield self._injection_toggle

    def _render_main_content(self) -> Text:
        """Render the main card content (without injection)."""
        if self._is_subagent:
            return self._render_subagent()
        return self._render_collapsed_without_injection()

    def _toggle_injection(self) -> None:
        """Toggle injection expansion (called by InjectionToggle)."""
        from massgen.logger_config import logger

        self._injection_expanded = not self._injection_expanded
        logger.info(f"[ToolCallCard] _toggle_injection: expanded={self._injection_expanded}")

        # Update CSS class for height adjustment
        if self._injection_expanded:
            self.add_class("has-injection")
        else:
            self.remove_class("has-injection")

        # Update injection toggle content and CSS class
        if self._injection_toggle:
            new_content = self._render_injection_content()
            logger.info(f"[ToolCallCard] updating toggle content, length={len(str(new_content))}")
            self._injection_toggle.update_content(new_content)
            # Add/remove expanded class for CSS height adjustment
            if self._injection_expanded:
                self._injection_toggle.add_class("expanded")
            else:
                self._injection_toggle.remove_class("expanded")
        else:
            logger.warning("[ToolCallCard] _injection_toggle is None!")

    def _render_collapsed_without_injection(self) -> Text:
        """Render card view without injection content (injection is in separate widget).

        Design with hooks:
        ```
        🪝 timeout_hard: allowed
        ▶ 📁 filesystem/write_file                              ⏳ running...
          {"content": "In circuits humming...", "path": "/tmp/poem.txt"}
        ```
        or completed:
        ```
          📁 filesystem/read_file                               ✓ (0.3s)
          {"path": "/tmp/example.txt"}
          → File contents: Hello world...
        ```
        Note: Injection content is rendered separately in InjectionToggle widget.
        """
        text = Text()

        # Low-value hooks to hide (these just add noise without useful info)
        # Use prefix matching for patterns like round_timeout_hard_agent_a
        hidden_hook_prefixes = {
            "timeout_allowed",
            "round_allowed",
            "per_round_allowed",
            "timeout_hard",
            "timeout_soft",
            "round_timeout_hard",
            "round_timeout_soft",
        }

        # Pre-hooks (shown above tool line) - only show interesting ones
        for hook in self._pre_hooks:
            hook_name = hook.get("hook_name", "unknown")
            decision = hook.get("decision", "allow")
            reason = hook.get("reason", "")

            # Skip low-value hooks that just show "allowed" (use prefix matching)
            if decision != "deny" and any(hook_name.startswith(prefix) for prefix in hidden_hook_prefixes):
                continue

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
        # Increased from 90 to 120 to push time further right on wide terminals
        name_len = len(self._display_name) + 4
        padding = max(1, 120 - name_len)
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

        # Note: Injection content is now rendered in a separate InjectionToggle widget
        return text

    def _render_injection_content(self) -> Text:
        """Render the injection content for the InjectionToggle widget.

        Returns:
            Rich Text with injection preview (collapsed) or full content (expanded).
        """
        from massgen.logger_config import logger

        text = Text()
        logger.info(
            f"[ToolCallCard] _render_injection_content: expanded={self._injection_expanded}, " f"num_hooks={len(self._post_hooks)}",
        )

        for hook in self._post_hooks:
            injection_content = hook.get("injection_content")
            if injection_content:
                logger.info(
                    f"[ToolCallCard] rendering injection: hook={hook.get('hook_name')}, " f"content_len={len(injection_content)}",
                )
                # Generate clean preview without decorative lines
                preview = self._generate_injection_preview(injection_content)

                if self._injection_expanded:
                    # Expanded view - show full content
                    text.append("  ▼ ", style="dim")
                    text.append("📥 ", style="bold #d2a8ff")
                    text.append(hook.get("hook_name", "injection"), style="bold #d2a8ff")
                    text.append(" (click to collapse)", style="dim italic")
                    execution_time = hook.get("execution_time_ms")
                    if execution_time:
                        text.append(f" ({execution_time:.1f}ms)", style="dim")
                    text.append("\n")

                    # Render content lines (limit to prevent huge displays)
                    max_lines = 20
                    content_lines = injection_content.split("\n")
                    for i, line in enumerate(content_lines[:max_lines]):
                        text.append("    ", style="dim")
                        text.append(line, style="#c9b8e0")
                        if i < min(len(content_lines), max_lines) - 1:
                            text.append("\n")

                    if len(content_lines) > max_lines:
                        text.append("\n")
                        text.append(f"    ... ({len(content_lines) - max_lines} more lines)", style="dim italic")
                else:
                    # Collapsed view - show arrow and preview with hint
                    text.append("  ▶ ", style="dim")
                    text.append("📥 ", style="bold #d2a8ff")
                    text.append(hook.get("hook_name", "injection"), style="bold #d2a8ff")
                    text.append(": ", style="dim")
                    text.append(preview, style="#c9b8e0")
                    text.append(" (click to expand)", style="dim italic")

        return text

    def _generate_injection_preview(self, content: str, max_length: int = 60) -> str:
        """Generate a clean preview from injection content."""
        # Split into lines and filter out decorative/empty lines
        lines = content.split("\n")
        meaningful_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("=") and stripped.count("=") > 10:
                continue
            if stripped.startswith("-") and stripped.count("-") > 10:
                continue
            meaningful_lines.append(stripped)

        if meaningful_lines:
            preview = " ".join(meaningful_lines)
        else:
            preview = content.replace("\n", " ").strip()

        if len(preview) > max_length:
            return preview[:max_length] + "..."
        return preview

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
        if self._expanded:
            content = self._workspace_content or self._get_formatted_result()
            if content:
                text.append("\n    ┌─ Details ──────────────────────────────────\n", style="dim #a371f7")
                # Show workspace content with indentation
                lines = content.split("\n")[:15]  # Limit lines
                for line in lines:
                    if len(line) > 70:
                        line = line[:67] + "..."
                    text.append(f"    │ {line}\n", style="dim")
                if len(content.split("\n")) > 15:
                    text.append("    │ ...(more)...\n", style="dim italic")
                text.append("    └──────────────────────────────────────────", style="dim #a371f7")
        elif not self._expanded and (self._workspace_content or self._result):
            # Show expand hint
            text.append("\n    ", style="dim")
            text.append("[click to expand]", style="dim italic #a371f7")

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
        """Handle click - toggle expansion for subagents, or show modal for others.

        Note: Injection content expansion is handled by the InjectionToggle widget,
        which intercepts clicks on the injection area. Clicks elsewhere on the card
        will open the detail modal.
        """
        if self._is_subagent:
            self.toggle_expanded()
        else:
            # Always open modal for non-subagent cards
            # (injection area has its own click handler via InjectionToggle)
            self.post_message(self.ToolCardClicked(self))

    def _has_injection_content(self) -> bool:
        """Check if any post-hook has injection content."""
        for hook in self._post_hooks:
            if hook.get("injection_content"):
                return True
        return False

    def set_params(self, params: str, params_full: Optional[str] = None) -> None:
        """Set the tool parameters.

        Args:
            params: Truncated parameters for card display.
            params_full: Full parameters for modal (if different from params).
        """
        self._params = params
        self._params_full = params_full if params_full else params
        self._refresh_main_content()

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
        self._stop_elapsed_timer()  # Stop the timer now that tool is complete
        self.remove_class("status-running")
        self.add_class("status-success")
        self._refresh_main_content()

    def set_error(self, error: str) -> None:
        """Set error result.

        Args:
            error: Error message to display.
        """
        self._status = "error"
        self._error = error
        self._end_time = datetime.now()
        self._stop_elapsed_timer()  # Stop the timer now that tool is complete
        self.remove_class("status-running")
        self.add_class("status-error")
        self._refresh_main_content()

    def set_background_result(
        self,
        result: str,
        result_full: Optional[str] = None,
        async_id: Optional[str] = None,
    ) -> None:
        """Set result for a background/async operation.

        Unlike set_result(), this keeps the timer running since the operation
        continues in the background. Use this for operations like background shells
        that return immediately but continue executing.

        Args:
            result: Truncated result for card display (e.g., "Started: shell_abc123").
            result_full: Full result for modal.
            async_id: Optional identifier for the async operation (e.g., shell_id).
        """
        self._status = "background"
        self._result = result
        self._result_full = result_full if result_full else result
        self._async_id = async_id
        self._is_background = True
        # NOTE: We do NOT stop the timer - background operations are still running
        # NOTE: We do NOT set _end_time - operation is ongoing
        self.remove_class("status-running")
        self.add_class("status-background")
        self._refresh_main_content()

    def add_pre_hook(
        self,
        hook_name: str,
        decision: str,
        reason: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
        injection_content: Optional[str] = None,
    ) -> None:
        """Add a pre-tool hook execution to display.

        Args:
            hook_name: Name of the hook
            decision: "allow", "deny", or "error"
            reason: Reason for the decision (if any)
            execution_time_ms: How long the hook took
            injection_content: Full injection content (if any)
        """
        self._pre_hooks.append(
            {
                "hook_name": hook_name,
                "decision": decision,
                "reason": reason,
                "execution_time_ms": execution_time_ms,
                "injection_content": injection_content,
                "timestamp": datetime.now(),
            },
        )
        self._refresh_main_content()

    def add_post_hook(
        self,
        hook_name: str,
        injection_preview: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
        injection_content: Optional[str] = None,
    ) -> None:
        """Add a post-tool hook execution to display.

        Args:
            hook_name: Name of the hook
            injection_preview: Preview of injected content (if any)
            execution_time_ms: How long the hook took
            injection_content: Full injection content (if any)
        """
        from massgen.logger_config import logger

        logger.info(
            f"[ToolCallCard] add_post_hook: tool={self.tool_name}, hook={hook_name}, " f"has_content={bool(injection_content)}, is_mounted={self.is_mounted}",
        )
        self._post_hooks.append(
            {
                "hook_name": hook_name,
                "injection_preview": injection_preview,
                "injection_content": injection_content,
                "execution_time_ms": execution_time_ms,
                "timestamp": datetime.now(),
            },
        )
        self._refresh_main_content()

        # If this hook has injection content, ensure the toggle widget exists
        if injection_content:
            self._ensure_injection_toggle()
            self._refresh_injection_toggle()

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
        self._refresh_main_content()

    def update_subagent_task_status(self, task_index: int, status: str) -> None:
        """Update the status of a specific subagent task.

        Args:
            task_index: Index of the task to update
            status: New status ("pending", "running", "completed", "error")
        """
        if 0 <= task_index < len(self._subagent_tasks):
            self._subagent_tasks[task_index]["status"] = status
            self._refresh_main_content()

    def _get_formatted_result(self) -> Optional[str]:
        """Get a formatted version of the result, parsing JSON if applicable.

        For subagent tools, this extracts meaningful information from the JSON result.
        For broadcast/ask_others tools, this formats responses nicely.
        """
        if not self._result:
            return None

        import json

        try:
            data = json.loads(self._result)
            if isinstance(data, dict):
                lines = []

                # Check for broadcast/ask_others responses first
                if "responses" in data and isinstance(data.get("responses"), list):
                    # Format broadcast responses nicely
                    status = data.get("status", "unknown")
                    lines.append(f"Status: {status}")

                    responses = data["responses"]
                    if responses:
                        lines.append("")
                        for resp in responses:
                            responder = resp.get("responder_id", "unknown")
                            content = resp.get("content", "")
                            is_human = resp.get("is_human", False)

                            if is_human:
                                lines.append("👤 Human response:")
                            else:
                                lines.append(f"🤖 {responder}:")

                            # Show response content with some formatting
                            content_lines = content.strip().split("\n")
                            for cl in content_lines[:10]:  # Limit lines
                                if len(cl) > 80:
                                    cl = cl[:77] + "..."
                                lines.append(f"   {cl}")
                            if len(content_lines) > 10:
                                lines.append(f"   ... ({len(content_lines) - 10} more lines)")
                            lines.append("")
                    else:
                        lines.append("No responses received.")

                    # Show Q&A history if present
                    qa_history = data.get("human_qa_history", [])
                    if qa_history:
                        lines.append("─" * 40)
                        lines.append("Previous Q&A this session:")
                        for qa in qa_history[-3:]:  # Last 3
                            q = qa.get("question", "")[:50]
                            a = qa.get("answer", "")[:50]
                            lines.append(f"  Q: {q}...")
                            lines.append(f"  A: {a}...")

                    return "\n".join(lines)

                # Format subagent-specific results nicely
                if "subagent_id" in data:
                    lines.append(f"Subagent: {data['subagent_id']}")
                if "status" in data:
                    lines.append(f"Status: {data['status']}")
                if "message" in data:
                    lines.append(f"Message: {data['message']}")
                if "result" in data:
                    result = data["result"]
                    if isinstance(result, str):
                        lines.append(f"Result: {result[:200]}")
                    elif isinstance(result, dict):
                        lines.append("Result:")
                        for k, v in list(result.items())[:5]:
                            v_str = str(v)[:60]
                            lines.append(f"  {k}: {v_str}")
                if "error" in data:
                    lines.append(f"Error: {data['error']}")
                if "spawned_subagents" in data:
                    lines.append("Spawned Subagents:")
                    for sa in data["spawned_subagents"][:5]:
                        sa_id = sa.get("id", sa.get("subagent_id", "unknown"))
                        sa_prompt = sa.get("prompt", sa.get("task", ""))[:50]
                        lines.append(f"  • {sa_id}: {sa_prompt}")

                if lines:
                    return "\n".join(lines)

                # Fallback: pretty print JSON
                return json.dumps(data, indent=2)[:500]
        except (json.JSONDecodeError, TypeError):
            pass

        # Return raw result if not JSON
        return self._result[:500] if self._result else None

    def set_workspace_content(self, content: str) -> None:
        """Set the workspace content for expanded view.

        Args:
            content: The workspace/output content to display when expanded.
        """
        self._workspace_content = content
        self._refresh_main_content()

    def toggle_expanded(self) -> None:
        """Toggle the expanded state of the subagent card."""
        self._expanded = not self._expanded
        if self._expanded:
            self.add_class("expanded")
        else:
            self.remove_class("expanded")
        self._refresh_main_content()

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
