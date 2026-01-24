# -*- coding: utf-8 -*-
"""
Mode Bar Widget for MassGen TUI.

Provides a horizontal bar with mode toggles for plan mode, agent mode,
refinement mode, and override functionality.
"""

from typing import TYPE_CHECKING, Optional

from textual.app import ComposeResult
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Label, Static

if TYPE_CHECKING:
    from massgen.frontend.displays.tui_modes import PlanDepth


class ModeChanged(Message):
    """Message emitted when a mode toggle changes."""

    def __init__(self, mode_type: str, value: str) -> None:
        """Initialize the message.

        Args:
            mode_type: The type of mode changed ("plan", "agent", "refinement").
            value: The new value of the mode.
        """
        self.mode_type = mode_type
        self.value = value
        super().__init__()


class PlanConfigChanged(Message):
    """Message emitted when plan configuration changes."""

    def __init__(self, depth: Optional["PlanDepth"] = None, auto_execute: Optional[bool] = None) -> None:
        """Initialize the message.

        Args:
            depth: New plan depth if changed.
            auto_execute: New auto-execute setting if changed.
        """
        self.depth = depth
        self.auto_execute = auto_execute
        super().__init__()


class OverrideRequested(Message):
    """Message emitted when user requests override."""


class PlanSettingsClicked(Message):
    """Message emitted when plan settings button is clicked."""


def _mode_log(msg: str) -> None:
    """Log to TUI debug file."""
    try:
        import logging

        log = logging.getLogger("massgen.tui.debug")
        if not log.handlers:
            handler = logging.FileHandler("/tmp/massgen_tui_debug.log", mode="a")
            handler.setFormatter(logging.Formatter("%(asctime)s [MODE] %(message)s", datefmt="%H:%M:%S"))
            log.addHandler(handler)
            log.setLevel(logging.DEBUG)
            log.propagate = False
        log.debug(msg)
    except Exception:
        pass


class ModeToggle(Static):
    """A clickable toggle button for a mode.

    Displays current state and cycles through states on click.
    """

    can_focus = True

    # Icons for different modes - using radio indicators for clean look
    ICONS = {
        "plan": {"normal": "○", "plan": "◉", "execute": "◉"},
        "agent": {"multi": "◉", "single": "○"},
        "refinement": {"on": "◉", "off": "○"},
    }

    # Labels for states - concise without redundant ON/OFF
    LABELS = {
        "plan": {"normal": "Normal", "plan": "Planning", "execute": "Executing"},
        "agent": {"multi": "Multi-Agent", "single": "Single"},
        "refinement": {"on": "Refine", "off": "Refine OFF"},
    }

    def __init__(
        self,
        mode_type: str,
        initial_state: str,
        states: list[str],
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """Initialize the mode toggle.

        Args:
            mode_type: The type of mode ("plan", "agent", "refinement").
            initial_state: The initial state value.
            states: List of valid states to cycle through.
            id: Optional DOM ID.
            classes: Optional CSS classes.
        """
        super().__init__(id=id, classes=classes)
        self.mode_type = mode_type
        self._states = states
        self._current_state = initial_state
        self._enabled = True

    def on_mount(self) -> None:
        """Apply initial style class on mount."""
        self._update_style()

    def render(self) -> str:
        """Render the toggle button."""
        icon = self.ICONS.get(self.mode_type, {}).get(self._current_state, "⚙️")
        label = self.LABELS.get(self.mode_type, {}).get(self._current_state, self._current_state)
        return f" {icon} {label} "

    def set_state(self, state: str) -> None:
        """Set the toggle state.

        Args:
            state: The new state value.
        """
        if state in self._states:
            self._current_state = state
            self._update_style()
            self.refresh()

    def get_state(self) -> str:
        """Get the current state."""
        return self._current_state

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the toggle.

        Args:
            enabled: True to enable, False to disable.
        """
        self._enabled = enabled
        if enabled:
            self.remove_class("disabled")
        else:
            self.add_class("disabled")

    def _update_style(self) -> None:
        """Update CSS classes based on current state."""
        # Remove all state classes
        for state in self._states:
            self.remove_class(f"state-{state}")
        # Add current state class
        self.add_class(f"state-{self._current_state}")

    async def on_click(self) -> None:
        """Handle click to cycle to next state."""
        if not self._enabled:
            return

        _mode_log(f"ModeToggle.on_click: {self.mode_type} current={self._current_state}")

        # For plan mode, only allow toggling between normal and plan (not execute)
        if self.mode_type == "plan":
            if self._current_state == "normal":
                new_state = "plan"
            elif self._current_state == "plan":
                new_state = "normal"
            else:
                # In execute mode, clicking does nothing
                return
        else:
            # Cycle through states
            current_idx = self._states.index(self._current_state)
            next_idx = (current_idx + 1) % len(self._states)
            new_state = self._states[next_idx]

        self._current_state = new_state
        self._update_style()
        self.refresh()
        self.post_message(ModeChanged(self.mode_type, new_state))


class ModeBar(Widget):
    """Horizontal bar with mode toggles positioned above the input area.

    Contains toggles for:
    - Plan mode: normal → plan → execute
    - Agent mode: multi ↔ single
    - Refinement mode: on ↔ off
    - Override button (shown when override is available)
    """

    DEFAULT_CSS = """
    ModeBar {
        height: 2;
        width: auto;
        layout: horizontal;
        background: transparent;
        border-bottom: none;
        padding: 0 1;
        align: left middle;
    }

    ModeBar.hidden {
        display: none;
    }

    /* Base toggle - minimal, no background */
    ModeBar ModeToggle {
        margin: 0 1;
        padding: 0 1;
        background: transparent;
        color: $text-muted;
        border: solid $surface-lighten-2;
    }

    /* Hover - subtle border highlight */
    ModeBar ModeToggle:hover {
        border: solid $primary-lighten-1;
        color: $text;
    }

    /* Focus - visible focus ring */
    ModeBar ModeToggle:focus {
        border: solid $primary;
    }

    /* Disabled - very muted */
    ModeBar ModeToggle.disabled {
        color: $text-disabled;
        border: solid $surface;
    }

    /* Plan mode active - green text */
    ModeBar ModeToggle.state-plan {
        color: $success;
        border: solid $success;
    }

    /* Execute mode - green text (same as plan) */
    ModeBar ModeToggle.state-execute {
        color: $success;
        border: solid $success;
    }

    /* Single agent - warning color */
    ModeBar ModeToggle.state-single {
        color: $warning;
        border: solid $warning;
    }

    /* Multi-agent (default) - normal text */
    ModeBar ModeToggle.state-multi {
        color: $text;
        border: solid $surface-lighten-2;
    }

    /* Refinement on - green */
    ModeBar ModeToggle.state-on {
        color: $success;
        border: solid $success;
    }

    /* Refinement off - muted */
    ModeBar ModeToggle.state-off {
        color: $text-muted;
        border: solid $surface-lighten-2;
    }

    /* Normal (inactive plan) - muted */
    ModeBar ModeToggle.state-normal {
        color: $text-muted;
        border: solid $surface-lighten-2;
    }

    ModeBar #mode_spacer {
        width: 1fr;
    }

    ModeBar #override_btn {
        background: $warning;
        color: $text;
        margin-left: 1;
    }

    ModeBar #override_btn.hidden {
        display: none;
    }

    ModeBar #mode_info {
        color: $text-muted;
        margin-left: 2;
    }

    ModeBar #plan_info {
        color: $success;
        margin-left: 1;
    }

    /* Plan settings button - minimal style to match toggles */
    ModeBar #plan_settings_btn {
        width: auto;
        height: 1;
        min-width: 3;
        background: transparent;
        color: $text-muted;
        border: solid $surface-lighten-2;
        padding: 0 1;
        margin-left: 1;
    }

    ModeBar #plan_settings_btn:hover {
        border: solid $primary-lighten-1;
        color: $text;
    }

    ModeBar #plan_settings_btn.hidden {
        display: none;
    }

    ModeBar #plan_status {
        color: $text-muted;
        text-style: italic;
        padding: 0 1;
    }

    ModeBar #plan_status.hidden {
        display: none;
    }
    """

    # Reactive for override button visibility
    override_available: reactive[bool] = reactive(False)

    def __init__(
        self,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """Initialize the mode bar."""
        super().__init__(id=id, classes=classes)
        self._plan_toggle: Optional[ModeToggle] = None
        self._agent_toggle: Optional[ModeToggle] = None
        self._refinement_toggle: Optional[ModeToggle] = None
        self._override_btn: Optional[Button] = None
        self._plan_info: Optional[Label] = None
        self._plan_settings_btn: Optional[Button] = None
        self._plan_status: Optional[Static] = None

    def compose(self) -> ComposeResult:
        """Create mode bar contents."""
        # Plan mode toggle
        self._plan_toggle = ModeToggle(
            mode_type="plan",
            initial_state="normal",
            states=["normal", "plan", "execute"],
            id="plan_toggle",
        )
        yield self._plan_toggle

        # Agent mode toggle
        self._agent_toggle = ModeToggle(
            mode_type="agent",
            initial_state="multi",
            states=["multi", "single"],
            id="agent_toggle",
        )
        yield self._agent_toggle

        # Refinement mode toggle
        self._refinement_toggle = ModeToggle(
            mode_type="refinement",
            initial_state="on",
            states=["on", "off"],
            id="refinement_toggle",
        )
        yield self._refinement_toggle

        # Plan settings button (hidden when plan mode is "normal")
        self._plan_settings_btn = Button("⋮", id="plan_settings_btn", variant="default")
        self._plan_settings_btn.add_class("hidden")
        yield self._plan_settings_btn

        # Plan info (shown when executing plan)
        self._plan_info = Label("", id="plan_info")
        yield self._plan_info

        # Spacer to push status and override button to the right
        yield Static("", id="mode_spacer")

        # Plan status text (right-aligned, shows plan being executed)
        self._plan_status = Static("", id="plan_status", classes="hidden")
        yield self._plan_status

        # Override button (hidden by default)
        self._override_btn = Button("Override [Ctrl+O]", id="override_btn", variant="warning")
        self._override_btn.add_class("hidden")
        yield self._override_btn

    def watch_override_available(self, available: bool) -> None:
        """React to override availability changes."""
        if self._override_btn:
            if available:
                self._override_btn.remove_class("hidden")
            else:
                self._override_btn.add_class("hidden")

    def set_plan_mode(self, mode: str, plan_info: str = "") -> None:
        """Set the plan mode state.

        Args:
            mode: "normal", "plan", or "execute".
            plan_info: Optional plan info text (shown in execute mode).
        """
        if self._plan_toggle:
            self._plan_toggle.set_state(mode)
        if self._plan_info:
            if mode == "execute" and plan_info:
                self._plan_info.update(f"📂 {plan_info}")
            else:
                self._plan_info.update("")

        # Show/hide plan settings button based on mode
        if self._plan_settings_btn:
            if mode != "normal":
                self._plan_settings_btn.remove_class("hidden")
            else:
                self._plan_settings_btn.add_class("hidden")

    def set_agent_mode(self, mode: str) -> None:
        """Set the agent mode state.

        Args:
            mode: "multi" or "single".
        """
        if self._agent_toggle:
            self._agent_toggle.set_state(mode)

    def set_refinement_mode(self, enabled: bool) -> None:
        """Set the refinement mode state.

        Args:
            enabled: True for "on", False for "off".
        """
        if self._refinement_toggle:
            self._refinement_toggle.set_state("on" if enabled else "off")

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable all mode toggles.

        Args:
            enabled: True to enable all toggles, False to disable.
        """
        if self._plan_toggle:
            self._plan_toggle.set_enabled(enabled)
        if self._agent_toggle:
            self._agent_toggle.set_enabled(enabled)
        if self._refinement_toggle:
            self._refinement_toggle.set_enabled(enabled)

    def get_plan_mode(self) -> str:
        """Get current plan mode."""
        return self._plan_toggle.get_state() if self._plan_toggle else "normal"

    def get_agent_mode(self) -> str:
        """Get current agent mode."""
        return self._agent_toggle.get_state() if self._agent_toggle else "multi"

    def get_refinement_enabled(self) -> bool:
        """Get current refinement mode."""
        return self._refinement_toggle.get_state() == "on" if self._refinement_toggle else True

    def set_plan_status(self, status: str) -> None:
        """Set the plan status text shown on the right side.

        Args:
            status: Status text to display, or empty to hide.
        """
        if self._plan_status:
            if status:
                self._plan_status.update(status)
                self._plan_status.remove_class("hidden")
            else:
                self._plan_status.update("")
                self._plan_status.add_class("hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "override_btn":
            _mode_log("ModeBar: Override button pressed")
            self.post_message(OverrideRequested())
        elif event.button.id == "plan_settings_btn":
            _mode_log("ModeBar: Plan settings button pressed")
            self.post_message(PlanSettingsClicked())

    def on_mode_changed(self, event: ModeChanged) -> None:
        """Let mode change messages bubble to parent."""
        _mode_log(f"ModeBar.on_mode_changed: {event.mode_type}={event.value}")
        # Don't stop - let it bubble to TextualApp


class WorkflowStatusLine(Static):
    """Conversational status line explaining the multi-agent workflow.

    Displays human-readable messages like:
    - "3 agents are thinking about this..."
    - "They can see each other's ideas now. Claude is refining..."
    - "Gemini thinks Claude's approach is best. Waiting for GPT..."
    - "They agreed! Here's the final answer."
    """

    DEFAULT_CSS = """
    WorkflowStatusLine {
        height: 2;
        width: 1fr;
        padding: 0 1;
        text-align: right;
        content-align: right middle;
        color: $text-muted;
        text-style: italic;
        background: transparent;
    }

    WorkflowStatusLine.hidden {
        display: none;
    }

    WorkflowStatusLine.active {
        color: $primary;
    }

    WorkflowStatusLine.consensus {
        color: $success;
        text-style: bold;
    }
    """

    def __init__(self, id: Optional[str] = None) -> None:
        """Initialize the workflow status line."""
        super().__init__("", id=id or "workflow_status")
        self._agent_count = 0
        self._agent_names: dict[str, str] = {}  # agent_id -> display name
        self._working_agents: set[str] = set()
        self._voted_agents: dict[str, str] = {}  # voter_id -> voted_for_id
        self._current_phase = "idle"

    def set_agents(self, agent_ids: list[str], agent_names: Optional[dict[str, str]] = None) -> None:
        """Set the agents in the workflow.

        Args:
            agent_ids: List of agent IDs
            agent_names: Optional mapping of agent_id -> display name
        """
        self._agent_count = len(agent_ids)
        self._agent_names = agent_names or {}
        self._working_agents = set(agent_ids)
        self._voted_agents = {}
        _mode_log(f"WorkflowStatusLine.set_agents: count={self._agent_count}, names={self._agent_names}")
        self._update_message()

    def _get_agent_name(self, agent_id: str) -> str:
        """Get display name for an agent."""
        if agent_id in self._agent_names:
            return self._agent_names[agent_id]
        # Extract model name if in "agent_X" format
        # Or use the ID directly if it's a model name
        if agent_id.startswith("agent_"):
            return agent_id.replace("agent_", "Agent ")
        return agent_id

    def set_phase(self, phase: str) -> None:
        """Update the workflow phase.

        Args:
            phase: Current phase - "idle", "coordinating", "presenting" (from orchestrator)
        """
        _mode_log(f"WorkflowStatusLine.set_phase: '{phase}' (was '{self._current_phase}')")
        self._current_phase = phase
        self._update_message()

    def set_agent_working(self, agent_id: str) -> None:
        """Mark an agent as actively working."""
        self._working_agents.add(agent_id)
        self._update_message()

    def set_agent_idle(self, agent_id: str) -> None:
        """Mark an agent as idle (finished working)."""
        self._working_agents.discard(agent_id)
        self._update_message()

    def record_vote(self, voter_id: str, voted_for_id: str) -> None:
        """Record a vote from one agent for another.

        Args:
            voter_id: The agent casting the vote
            voted_for_id: The agent being voted for
        """
        _mode_log(f"WorkflowStatusLine.record_vote: {voter_id} -> {voted_for_id}")
        self._voted_agents[voter_id] = voted_for_id
        self._update_message()

    def show_consensus(self, winner_name: str = "") -> None:
        """Show that consensus was reached."""
        _mode_log(f"WorkflowStatusLine.show_consensus: winner='{winner_name}'")
        self._current_phase = "consensus"
        self.remove_class("active")
        self.add_class("consensus")
        if winner_name:
            self.update(f'"They agreed! {winner_name} presents the final answer."')
        else:
            self.update('"They agreed! Here\'s the final answer."')

    def reset(self) -> None:
        """Reset the status line for a new session."""
        self._working_agents.clear()
        self._voted_agents.clear()
        self._current_phase = "idle"
        self.remove_class("active")
        self.remove_class("consensus")
        self.update("")

    def _update_message(self) -> None:
        """Update the displayed message based on current state."""
        if self._agent_count == 0:
            _mode_log("WorkflowStatusLine._update_message: agent_count=0, hiding")
            self.update("")
            self.add_class("hidden")
            return

        self.remove_class("hidden")
        self.remove_class("consensus")

        message = self._generate_message()
        _mode_log(f"WorkflowStatusLine._update_message: phase='{self._current_phase}', votes={len(self._voted_agents)}, msg='{message[:50] if message else ''}'")
        if message:
            self.add_class("active")
            self.update(f'"{message}"')
        else:
            self.remove_class("active")
            self.update("")

    def _generate_message(self) -> str:
        """Generate the appropriate conversational message."""
        if self._current_phase == "idle":
            return ""

        # Handle both fine-grained phases (initial_answer, enforcement) and
        # coarse phases (coordinating) from orchestrator.workflow_phase
        if self._current_phase in ("initial_answer", "coordinating"):
            # If we have votes, we're actually in enforcement/voting phase
            if self._voted_agents:
                return self._generate_voting_message()

            # Agents are working on initial answers
            if self._agent_count > 0:
                return f"{self._agent_count} agents are thinking about this..."
            return ""

        if self._current_phase == "enforcement":
            return self._generate_voting_message()

        if self._current_phase in ("presenting", "presentation"):
            return "They agreed! Presenting the final answer..."

        return ""

    def _generate_voting_message(self) -> str:
        """Generate message for the voting/enforcement phase."""
        if not self._voted_agents:
            return "They can see each other's ideas now. Deciding what to do..."

        # Show voting status
        voted_count = len(self._voted_agents)
        remaining = self._agent_count - voted_count

        if voted_count > 0 and remaining > 0:
            # Show who voted for whom
            last_voter, voted_for = list(self._voted_agents.items())[-1]
            voter_name = self._get_agent_name(last_voter)
            target_name = self._get_agent_name(voted_for)

            if remaining == 1:
                waiting_agents = [a for a in self._working_agents if a not in self._voted_agents]
                if waiting_agents:
                    waiting_name = self._get_agent_name(waiting_agents[0])
                    return f"{voter_name} thinks {target_name}'s approach is best. Waiting for {waiting_name}..."
            return f"{voter_name} voted for {target_name}. {remaining} still deciding..."

        return f"{voted_count} agents have voted. Waiting for consensus..."
