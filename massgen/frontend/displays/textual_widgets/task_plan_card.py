# -*- coding: utf-8 -*-
"""
Task Plan Card Widget for MassGen TUI.

Visual todo list display for Planning MCP integration.
Shows tasks from create_task_plan, update_task_status, etc.
"""

from typing import Any, Dict, List, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static


class TaskPlanCard(Static):
    """Card displaying a visual todo list from Planning MCP.

    Design:
    ```
    ┌─ Tasks ────────────────────────────────────┐
    │ ✓ Research OAuth providers                 │  ← completed (dimmed)
    │ ✓ Compare authentication methods           │  ← completed (dimmed)
    │ ● Implement OAuth flow                     │  ← in_progress (highlighted)
    │ ○ Write integration tests                  │  ← pending (ready)
    │ ○ Deploy to staging                        │  ← pending (blocked)
    └────────────────────────────────────────────┘
    ```

    Display Logic:
    - On create_task_plan: Show first N tasks (based on terminal size)
    - On update_task_status/edit_task: Show neighborhood around focused task
      (2 above, focused task, 2 below)
    - Click to open full task plan modal
    """

    class OpenModal(Message):
        """Message posted when user clicks to open the task plan modal."""

        def __init__(self, tasks: List[Dict[str, Any]], focused_task_id: Optional[str] = None) -> None:
            self.tasks = tasks
            self.focused_task_id = focused_task_id
            super().__init__()

    DEFAULT_CSS = """
    TaskPlanCard {
        width: 100%;
        height: auto;
        min-height: 3;
        padding: 0 1;
        margin: 0 0 1 1;
        background: #1a1f2e;
        border-left: thick #a371f7;
    }

    TaskPlanCard:hover {
        background: #1e2436;
    }

    TaskPlanCard .task-header {
        text-style: bold;
        color: #a371f7;
        margin-bottom: 1;
    }

    TaskPlanCard .task-item {
        height: auto;
        padding: 0;
    }

    TaskPlanCard .task-completed {
        color: #6e7681;
    }

    TaskPlanCard .task-in-progress {
        color: #58a6ff;
        text-style: bold;
    }

    TaskPlanCard .task-pending {
        color: #8b949e;
    }

    TaskPlanCard .task-blocked {
        color: #6e7681;
        text-style: italic;
    }

    TaskPlanCard .task-focused {
        background: #21262d;
    }

    TaskPlanCard .task-count {
        color: #6e7681;
        text-style: italic;
    }

    TaskPlanCard .task-reminder {
        background: #4a3d2d;
        color: #ffa657;
        padding: 0 1;
        margin-top: 1;
    }
    """

    # Status indicators
    STATUS_ICONS = {
        "completed": "✓",
        "in_progress": "●",
        "pending": "○",
        "blocked": "◌",
    }

    # Default maximum tasks to show (used if terminal size unavailable)
    DEFAULT_MAX_VISIBLE = 5

    # Reactive properties
    tasks: reactive[List[Dict[str, Any]]] = reactive(list, always_update=True)
    focused_task_id: reactive[Optional[str]] = reactive(None)
    expanded: reactive[bool] = reactive(False)

    def __init__(
        self,
        tasks: Optional[List[Dict[str, Any]]] = None,
        focused_task_id: Optional[str] = None,
        operation: str = "create",
        id: Optional[str] = None,
    ) -> None:
        """Initialize the task plan card.

        Args:
            tasks: List of task dictionaries with id, description, status, priority
            focused_task_id: ID of the task to focus on (for update operations)
            operation: Type of operation (create, update, edit)
            id: Widget ID
        """
        super().__init__(id=id)
        self._tasks = tasks or []
        self._focused_task_id = focused_task_id
        self._operation = operation
        self._reminder: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield Static(self._build_content())

    def on_click(self) -> None:
        """Open the task plan modal when clicked."""
        self.post_message(self.OpenModal(self._tasks, self._focused_task_id))

    def _refresh_content(self) -> None:
        """Refresh the displayed content."""
        try:
            content_widget = self.query_one(Static)
            content_widget.update(self._build_content())
        except Exception:
            pass

    def set_reminder(self, content: str) -> None:
        """Set a high priority task reminder to display at the bottom of the card.

        Args:
            content: The reminder text to display
        """
        self._reminder = content
        self._refresh_content()

    def _get_max_visible(self) -> int:
        """Get maximum visible tasks based on terminal size."""
        try:
            # Try to get terminal height from app
            if self.app and hasattr(self.app, "size"):
                terminal_height = self.app.size.height
                # Reserve space for header, footer, and other UI elements
                # Allocate roughly 1/3 of terminal height to task list
                available = max(3, (terminal_height - 10) // 3)
                return min(available, 10)  # Cap at 10 tasks
        except Exception:
            pass
        return self.DEFAULT_MAX_VISIBLE

    def _get_max_description_length(self) -> int:
        """Get maximum description length based on terminal width."""
        try:
            if self.app and hasattr(self.app, "size"):
                terminal_width = self.app.size.width
                # Reserve space for icon, priority, padding, etc. (~10 chars)
                available = terminal_width - 15
                return max(30, min(available, 120))  # Between 30 and 120 chars
        except Exception:
            pass
        return 60  # Default reasonable width

    def _build_content(self) -> Text:
        """Build the card content as Rich Text."""
        text = Text()

        if not self._tasks:
            text.append("📋 No tasks", style="dim")
            return text

        # Header with expand/collapse indicator
        total = len(self._tasks)
        completed = sum(1 for t in self._tasks if t.get("status") == "completed")
        in_progress = sum(1 for t in self._tasks if t.get("status") == "in_progress")

        # Show expand/collapse arrow if there are more tasks than max visible
        max_visible = self._get_max_visible()
        has_hidden = total > max_visible and not self.expanded

        arrow = "▼" if self.expanded else "▶" if has_hidden else ""
        header_prefix = f"{arrow} " if arrow else ""

        # Show in-progress indicator in header
        progress_indicator = ""
        if in_progress > 0:
            progress_indicator = f" ● {in_progress} active"

        text.append(f"{header_prefix}📋 Tasks ({completed}/{total}){progress_indicator}\n", style="bold #a371f7")

        # Get visible tasks based on operation and expanded state
        visible_tasks, start_idx = self._get_visible_tasks()

        # Get dynamic description length
        max_desc_len = self._get_max_description_length()

        # Show "more above" indicator
        if start_idx > 0 and not self.expanded:
            text.append(f"  ↑ {start_idx} more above\n", style="dim italic")

        # Render each visible task
        for i, task in enumerate(visible_tasks):
            is_focused = task.get("id") == self._focused_task_id

            # Status icon
            status = task.get("status", "pending")
            icon = self.STATUS_ICONS.get(status, "○")

            # Description (truncate based on terminal width)
            desc = task.get("description", "Untitled task")
            if len(desc) > max_desc_len:
                desc = desc[: max_desc_len - 3] + "..."

            # Style based on status and focus
            if is_focused and status == "completed":
                # Focused completed task - subtle highlight (just completed!)
                style = "bold #7ee787"  # Soft green text, no background
                icon = "✓"
            elif status == "completed":
                style = "dim #6e7681"
            elif status == "in_progress":
                style = "bold #58a6ff"
            elif status == "blocked":
                style = "italic #6e7681"
            else:
                style = "#8b949e"

            # Add focus highlight for non-completed focused tasks
            if is_focused and status != "completed":
                style = f"{style} on #21262d"

            # Priority indicator
            priority = task.get("priority", "medium")
            priority_marker = ""
            if priority == "high":
                priority_marker = " !"

            # Extra visual indicator for focused task
            prefix = "▶ " if is_focused else "  "
            text.append(f"{prefix}{icon} {desc}{priority_marker}\n", style=style)

        # Show "more below" indicator or click hint
        remaining = total - (start_idx + len(visible_tasks))
        if remaining > 0 and not self.expanded:
            text.append(f"  ↓ {remaining} more below (click to expand)", style="dim italic")
        elif self.expanded and total > max_visible:
            text.append("  (click to collapse)", style="dim italic")

        # Render reminder at bottom if set
        if self._reminder:
            text.append("\n")
            # Truncate reminder if too long
            reminder_text = self._reminder.replace("\n", " ").strip()
            max_len = self._get_max_description_length() + 10  # Allow slightly more for reminder
            if len(reminder_text) > max_len:
                reminder_text = reminder_text[: max_len - 3] + "..."
            text.append(f"💡 {reminder_text}", style="bold #ffa657 on #4a3d2d")

        return text

    def _get_visible_tasks(self) -> tuple[List[Dict[str, Any]], int]:
        """Get the visible subset of tasks based on operation type and expanded state.

        Returns:
            Tuple of (visible_tasks, start_index)
        """
        total = len(self._tasks)
        max_visible = self._get_max_visible()

        # If expanded, show all tasks
        if self.expanded:
            return self._tasks, 0

        if total <= max_visible:
            return self._tasks, 0

        if self._operation == "create" or not self._focused_task_id:
            # Show first max_visible tasks
            return self._tasks[:max_visible], 0

        # Find focused task index
        focused_idx = 0
        for i, task in enumerate(self._tasks):
            if task.get("id") == self._focused_task_id:
                focused_idx = i
                break

        # Calculate window: 2 above, focused, 2 below
        context_above = 2
        context_below = 2

        start = max(0, focused_idx - context_above)
        end = min(total, focused_idx + context_below + 1)

        # Adjust if we're at the edges
        if end - start < max_visible:
            if start == 0:
                end = min(total, max_visible)
            elif end == total:
                start = max(0, total - max_visible)

        return self._tasks[start:end], start

    def update_tasks(self, tasks: List[Dict[str, Any]], focused_task_id: Optional[str] = None, operation: str = "update") -> None:
        """Update the displayed tasks.

        Args:
            tasks: New list of tasks
            focused_task_id: Task to focus on
            operation: Type of operation
        """
        self._tasks = tasks
        self._focused_task_id = focused_task_id
        self._operation = operation

        # Update display
        try:
            content_widget = self.query_one(Static)
            content_widget.update(self._build_content())
        except Exception:
            pass

    @classmethod
    def from_mcp_result(cls, result: Dict[str, Any], operation: str = "create") -> "TaskPlanCard":
        """Create a TaskPlanCard from MCP tool result.

        Args:
            result: Result dictionary from Planning MCP tool
            operation: Type of operation (create, update, add, edit)

        Returns:
            Configured TaskPlanCard instance
        """
        tasks = []
        focused_task_id = None

        # Extract tasks from result
        if "tasks" in result:
            tasks = result["tasks"]
        elif "plan" in result and "tasks" in result["plan"]:
            tasks = result["plan"]["tasks"]

        # Extract focused task from update operations
        if operation in ("update", "edit") and "task" in result:
            focused_task_id = result["task"].get("id")

        return cls(tasks=tasks, focused_task_id=focused_task_id, operation=operation)
