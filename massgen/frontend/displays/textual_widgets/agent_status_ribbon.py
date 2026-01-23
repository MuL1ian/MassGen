# -*- coding: utf-8 -*-
"""
Agent Status Ribbon Widget for MassGen TUI.

Displays real-time status bar below tabs with round dropdown, activity indicator,
timeout display, tasks progress, and token/cost tracking.
"""

import logging
from typing import Dict, List, Optional, Tuple

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, Static

logger = logging.getLogger(__name__)


class RoundSelected(Message):
    """Message emitted when a round is selected from the dropdown."""

    def __init__(self, round_number: int, agent_id: str) -> None:
        self.round_number = round_number
        self.agent_id = agent_id
        super().__init__()


class TasksClicked(Message):
    """Message emitted when tasks section is clicked."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        super().__init__()


class AgentStatusRibbon(Widget):
    """Real-time status bar below tabs.

    Design:
    ```
    ┌──────────────────────────────────────────────────────────────────────────┐
    │ Round 2 ▾ │ ◉ Streaming... 12s │ ⏱ 5:30 │ Tasks: 3/7 ━━░░ │ 2.4k │ $0.003 │
    └──────────────────────────────────────────────────────────────────────────┘
    ```
    """

    DEFAULT_CSS = """
    AgentStatusRibbon {
        width: 100%;
        height: auto;
        min-height: 1;
        background: $surface;
        border-bottom: solid $primary-darken-3;
        padding: 0 1;
    }

    AgentStatusRibbon .ribbon-container {
        width: 100%;
        height: auto;
        layout: horizontal;
    }

    AgentStatusRibbon .ribbon-section {
        width: auto;
        height: auto;
        padding: 0 1;
    }

    AgentStatusRibbon .ribbon-divider {
        width: auto;
        height: auto;
        color: $text-muted;
    }

    AgentStatusRibbon #round_selector {
        color: $text;
    }

    AgentStatusRibbon #round_selector:hover {
        color: $primary;
        text-style: underline;
    }

    AgentStatusRibbon #timeout_display {
        width: auto;
    }

    AgentStatusRibbon #timeout_display.warning {
        color: $warning;
    }

    AgentStatusRibbon #timeout_display.critical {
        color: $error;
    }

    AgentStatusRibbon #token_count {
        color: $text-muted;
        width: auto;
    }

    AgentStatusRibbon #cost_display {
        color: $text-muted;
        width: auto;
    }
    """

    # Reactive attributes
    current_agent: reactive[str] = reactive("")
    activity_status: reactive[str] = reactive("idle")
    elapsed_seconds: reactive[int] = reactive(0)

    # Activity status icons
    ACTIVITY_ICONS = {
        "streaming": "◉",
        "thinking": "⏳",
        "idle": "○",
        "canceled": "⏹",
        "error": "✗",
    }

    ACTIVITY_LABELS = {
        "streaming": "Streaming...",
        "thinking": "Thinking...",
        "idle": "Idle",
        "canceled": "Canceled",
        "error": "Error",
    }

    def __init__(
        self,
        agent_id: str = "",
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.current_agent = agent_id
        self._rounds: Dict[str, List[Tuple[int, bool]]] = {}  # agent_id -> [(round_num, is_context_reset)]
        self._current_round: Dict[str, int] = {}  # agent_id -> current round
        self._tasks_complete: Dict[str, int] = {}
        self._tasks_total: Dict[str, int] = {}
        self._tokens: Dict[str, int] = {}
        self._cost: Dict[str, float] = {}
        self._timeout_remaining: Dict[str, Optional[int]] = {}
        self._start_time: Optional[float] = None
        self._timer_handle = None

    def compose(self) -> ComposeResult:
        with Horizontal(classes="ribbon-container"):
            yield Label("Round 1 ▾", id="round_selector", classes="ribbon-section")
            yield Static("│", classes="ribbon-divider")
            yield Label("⏱ --:--", id="timeout_display", classes="ribbon-section")
            yield Static("│", classes="ribbon-divider")
            yield Label("-", id="token_count", classes="ribbon-section")
            yield Static("│", classes="ribbon-divider")
            yield Label("$--.---", id="cost_display", classes="ribbon-section")

    def on_mount(self) -> None:
        """Start the elapsed time timer."""
        self._timer_handle = self.set_interval(1.0, self._update_elapsed_time)

    def on_unmount(self) -> None:
        """Clean up timer."""
        if self._timer_handle:
            self._timer_handle.stop()

    def _update_elapsed_time(self) -> None:
        """Update the elapsed time display."""
        if self.activity_status in ("streaming", "thinking"):
            self.elapsed_seconds += 1
            self._update_activity_display()

    def set_agent(self, agent_id: str) -> None:
        """Switch to displaying status for a different agent."""
        self.current_agent = agent_id
        self._refresh_all_displays()

    def set_activity(self, agent_id: str, status: str) -> None:
        """Set the activity status for an agent.

        Args:
            agent_id: The agent ID
            status: One of "streaming", "thinking", "idle", "canceled", "error"
        """
        if agent_id == self.current_agent:
            # Reset elapsed time when activity changes
            if status != self.activity_status:
                self.elapsed_seconds = 0
            self.activity_status = status
            self._update_activity_display()

    def _update_activity_display(self) -> None:
        """Update the activity indicator display."""
        try:
            indicator = self.query_one("#activity_indicator", Label)
            icon = self.ACTIVITY_ICONS.get(self.activity_status, "○")
            label = self.ACTIVITY_LABELS.get(self.activity_status, "Unknown")

            # Add elapsed time for active states
            if self.activity_status in ("streaming", "thinking") and self.elapsed_seconds > 0:
                text = f"{icon} {label} {self.elapsed_seconds}s"
            else:
                text = f"{icon} {label}"

            indicator.update(text)

            # Update styling
            for status_class in ("streaming", "thinking", "idle", "canceled", "error"):
                indicator.remove_class(status_class)
            indicator.add_class(self.activity_status)
        except Exception:
            pass

    def set_round(self, agent_id: str, round_number: int, is_context_reset: bool = False) -> None:
        """Set the current round for an agent.

        Args:
            agent_id: The agent ID
            round_number: The round number
            is_context_reset: Whether this round started with a context reset
        """
        if agent_id not in self._rounds:
            self._rounds[agent_id] = []

        # Add round if new
        existing_rounds = [r[0] for r in self._rounds[agent_id]]
        if round_number not in existing_rounds:
            self._rounds[agent_id].append((round_number, is_context_reset))

        self._current_round[agent_id] = round_number

        if agent_id == self.current_agent:
            self._update_round_display()

    def _update_round_display(self) -> None:
        """Update the round selector display."""
        try:
            selector = self.query_one("#round_selector", Label)
            round_num = self._current_round.get(self.current_agent, 1)
            selector.update(f"Round {round_num} ▾")
        except Exception:
            pass

    def set_tasks(self, agent_id: str, complete: int, total: int) -> None:
        """Set the task progress for an agent.

        Args:
            agent_id: The agent ID
            complete: Number of completed tasks
            total: Total number of tasks
        """
        self._tasks_complete[agent_id] = complete
        self._tasks_total[agent_id] = total

        if agent_id == self.current_agent:
            self._update_tasks_display()

    def _update_tasks_display(self) -> None:
        """Update the tasks progress display."""
        try:
            tasks_label = self.query_one("#tasks_progress", Label)
            complete = self._tasks_complete.get(self.current_agent, 0)
            total = self._tasks_total.get(self.current_agent, 0)

            if total > 0:
                # Mini progress bar: ━━░░ (4 chars)
                filled = int((complete / total) * 4)
                bar = "━" * filled + "░" * (4 - filled)
                tasks_label.update(f"Tasks: {complete}/{total} {bar}")
            else:
                tasks_label.update("Tasks: -/-")
        except Exception:
            pass

    def set_timeout(self, agent_id: str, remaining_seconds: Optional[int]) -> None:
        """Set the timeout remaining for an agent.

        Args:
            agent_id: The agent ID
            remaining_seconds: Seconds remaining, or None if no timeout
        """
        self._timeout_remaining[agent_id] = remaining_seconds

        if agent_id == self.current_agent:
            self._update_timeout_display()

    def _update_timeout_display(self) -> None:
        """Update the timeout display."""
        try:
            timeout_label = self.query_one("#timeout_display", Label)
            remaining = self._timeout_remaining.get(self.current_agent)

            if remaining is None:
                timeout_label.update("⏱ --:--")
                timeout_label.remove_class("warning", "critical")
            else:
                mins = remaining // 60
                secs = remaining % 60
                timeout_label.update(f"⏱ {mins}:{secs:02d}")

                # Color coding based on time remaining
                timeout_label.remove_class("warning", "critical")
                if remaining <= 30:
                    timeout_label.add_class("critical")
                elif remaining <= 60:
                    timeout_label.add_class("warning")
        except Exception:
            pass

    def set_tokens(self, agent_id: str, tokens: int) -> None:
        """Set the token count for an agent.

        Args:
            agent_id: The agent ID
            tokens: Total tokens used
        """
        self._tokens[agent_id] = tokens

        if agent_id == self.current_agent:
            self._update_token_display()

    def _update_token_display(self) -> None:
        """Update the token count display."""
        try:
            token_label = self.query_one("#token_count", Label)
            tokens = self._tokens.get(self.current_agent, 0)

            if tokens >= 1000:
                token_label.update(f"{tokens / 1000:.1f}k")
            else:
                token_label.update(str(tokens) if tokens > 0 else "-")
        except Exception:
            pass

    def set_cost(self, agent_id: str, cost: float) -> None:
        """Set the cost for an agent.

        Args:
            agent_id: The agent ID
            cost: Total cost in dollars
        """
        self._cost[agent_id] = cost

        if agent_id == self.current_agent:
            self._update_cost_display()

    def _update_cost_display(self) -> None:
        """Update the cost display."""
        try:
            cost_label = self.query_one("#cost_display", Label)
            cost = self._cost.get(self.current_agent, 0.0)

            if cost > 0:
                cost_label.update(f"${cost:.3f}")
            else:
                cost_label.update("$--.---")
        except Exception:
            pass

    def _refresh_all_displays(self) -> None:
        """Refresh all displays for the current agent."""
        self._update_round_display()
        self._update_activity_display()
        self._update_timeout_display()
        self._update_tasks_display()
        self._update_token_display()
        self._update_cost_display()

    async def on_click(self, event) -> None:
        """Handle clicks on ribbon sections."""
        # Check if click was on tasks section
        try:
            tasks_label = self.query_one("#tasks_progress", Label)
            if hasattr(tasks_label, "region") and tasks_label.region.contains(event.x, event.y):
                self.post_message(TasksClicked(self.current_agent))
                return
        except Exception:
            pass

        # Check if click was on round selector (for future dropdown)
        try:
            round_selector = self.query_one("#round_selector", Label)
            if hasattr(round_selector, "region") and round_selector.region.contains(event.x, event.y):
                # TODO: Show round dropdown
                pass
        except Exception:
            pass
