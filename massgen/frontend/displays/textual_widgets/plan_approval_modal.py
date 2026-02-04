# -*- coding: utf-8 -*-
"""
Plan Approval Modal Widget for MassGen TUI.

Modal shown after planning completes to approve/reject plan before execution.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Static


@dataclass
class PlanApprovalResult:
    """Result from the plan approval modal."""

    approved: bool
    plan_data: Optional[Dict[str, Any]] = None
    plan_path: Optional[Path] = None


class PlanApprovalModal(ModalScreen[PlanApprovalResult]):
    """Modal screen for approving a plan before execution."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "execute", "Execute"),
    ]

    # CSS moved to base.tcss for theme support
    DEFAULT_CSS = ""

    # Status indicators for task preview
    STATUS_ICONS = {
        "pending": "○",
        "in_progress": "●",
        "completed": "✓",
        "blocked": "◌",
    }

    PRIORITY_COLORS = {
        "high": "#f85149",
        "medium": "#d29922",
        "low": "#8b949e",
    }

    def __init__(
        self,
        tasks: List[Dict[str, Any]],
        plan_path: Path,
        plan_data: Dict[str, Any],
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ):
        """Initialize the plan approval modal.

        Args:
            tasks: List of task dictionaries from the plan
            plan_path: Path to the plan file
            plan_data: Full plan data dictionary
            name: Widget name
            id: Widget id
            classes: Widget CSS classes
        """
        super().__init__(name=name, id=id, classes=classes)
        self.tasks = tasks
        self.plan_path = plan_path
        self.plan_data = plan_data

    def compose(self) -> ComposeResult:
        """Compose the modal UI."""
        with Container():
            # Header
            with Container(classes="modal-header"):
                with Container(classes="header-row"):
                    yield Static("Plan Approval", classes="modal-title")
                    yield Button("✕", variant="default", classes="modal-close", id="close_btn")

            # Stats summary
            with Horizontal(classes="modal-stats"):
                yield Static(f"Tasks: {len(self.tasks)}", classes="stat-item")

                # Count by priority if available
                high_priority = sum(1 for t in self.tasks if t.get("priority") == "high")
                if high_priority > 0:
                    yield Static(f"High Priority: {high_priority}", classes="stat-item")

                # Count dependencies
                has_deps = sum(1 for t in self.tasks if t.get("dependencies"))
                if has_deps > 0:
                    yield Static(f"With Dependencies: {has_deps}", classes="stat-item")

            # Task preview (scrollable)
            with ScrollableContainer(classes="modal-body"):
                preview_count = min(15, len(self.tasks))
                for task in self.tasks[:preview_count]:
                    yield Static(self._format_task_row(task), classes="task-row")

                if len(self.tasks) > preview_count:
                    remaining = len(self.tasks) - preview_count
                    yield Static(
                        Text(f"... and {remaining} more tasks", style="dim italic"),
                        classes="task-row",
                    )

            # Footer with buttons
            with Container(classes="modal-footer"):
                with Horizontal(classes="footer-buttons"):
                    yield Button(
                        "Execute Plan (Enter)",
                        variant="success",
                        id="execute_btn",
                        classes="execute-button",
                    )
                    yield Button(
                        "Cancel (Esc)",
                        variant="error",
                        id="cancel_btn",
                    )

    def _format_task_row(self, task: Dict[str, Any]) -> Text:
        """Format a single task row for display.

        Args:
            task: Task dictionary

        Returns:
            Rich Text object with formatted task
        """
        text = Text()

        # Status icon
        status = task.get("status", "pending")
        icon = self.STATUS_ICONS.get(status, "○")
        text.append(f"{icon} ", style="dim")

        # Task ID
        task_id = task.get("id", "?")
        text.append(f"[{task_id}] ", style="cyan")

        # Priority indicator
        priority = task.get("priority", "").lower()
        if priority in self.PRIORITY_COLORS:
            text.append("● ", style=self.PRIORITY_COLORS[priority])

        # Task name/description
        name = task.get("name") or task.get("description", "Untitled task")
        # Truncate long names
        if len(name) > 60:
            name = name[:57] + "..."
        text.append(name)

        # Dependencies indicator
        deps = task.get("dependencies", [])
        if deps:
            text.append(f" (→{len(deps)})", style="dim")

        return text

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "execute_btn":
            self.dismiss(
                PlanApprovalResult(
                    approved=True,
                    plan_data=self.plan_data,
                    plan_path=self.plan_path,
                ),
            )
        elif event.button.id in ("cancel_btn", "close_btn"):
            self.dismiss(PlanApprovalResult(approved=False))

    def action_cancel(self) -> None:
        """Cancel action (ESC key)."""
        self.dismiss(PlanApprovalResult(approved=False))

    def action_execute(self) -> None:
        """Execute action (Enter key)."""
        self.dismiss(
            PlanApprovalResult(
                approved=True,
                plan_data=self.plan_data,
                plan_path=self.plan_path,
            ),
        )
