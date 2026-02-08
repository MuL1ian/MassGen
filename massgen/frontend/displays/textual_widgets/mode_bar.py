# -*- coding: utf-8 -*-
"""
Mode Bar Widget for MassGen TUI.

Provides a horizontal bar with mode toggles for plan mode, agent mode,
coordination mode, refinement mode, and override functionality.
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
            mode_type: The type of mode changed ("plan", "agent", "coordination", "refinement", "personas").
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


class ModeHelpClicked(Message):
    """Message emitted when mode bar help button is clicked."""


class SubtasksClicked(Message):
    """Message emitted when subtasks button is clicked."""


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
        "coordination": {"parallel": "◉", "decomposition": "○"},
        "refinement": {"on": "◉", "off": "○"},
        "personas": {"off": "○", "on": "◉"},
    }

    # Labels for states - concise without redundant ON/OFF
    LABELS = {
        "plan": {"normal": "Normal", "plan": "Planning", "execute": "Executing"},
        "agent": {"multi": "Multi-Agent", "single": "Single"},
        "coordination": {"parallel": "Parallel", "decomposition": "Decomposition"},
        "refinement": {"on": "Refine", "off": "Refine OFF"},
        "personas": {"off": "Personas OFF", "on": "Personas"},
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
            mode_type: The type of mode ("plan", "agent", "coordination", "refinement").
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

        # For plan mode, cycle through: normal → plan → execute → normal
        if self.mode_type == "plan":
            if self._current_state == "normal":
                new_state = "plan"
            elif self._current_state == "plan":
                new_state = "execute"
            elif self._current_state == "execute":
                new_state = "normal"
            else:
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
    - Coordination mode: parallel ↔ decomposition
    - Personas toggle (parallel mode only)
    - Subtasks button (shown in decomposition mode)
    - Help button for mode bar explanations
    - Override button (shown when override is available)
    """

    # CSS moved to base.tcss for theme support
    DEFAULT_CSS = ""

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
        self._coordination_toggle: Optional[ModeToggle] = None
        self._refinement_toggle: Optional[ModeToggle] = None
        self._persona_toggle: Optional[ModeToggle] = None
        self._subtasks_btn: Optional[Button] = None
        self._mode_help_btn: Optional[Button] = None
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

        # Coordination mode toggle (parallel voting vs decomposition subtasks)
        self._coordination_toggle = ModeToggle(
            mode_type="coordination",
            initial_state="parallel",
            states=["parallel", "decomposition"],
            id="coordination_toggle",
        )
        yield self._coordination_toggle

        # Parallel persona generation toggle (off by default)
        self._persona_toggle = ModeToggle(
            mode_type="personas",
            initial_state="off",
            states=["off", "on"],
            id="persona_toggle",
        )
        yield self._persona_toggle

        # Subtasks editor button (decomposition mode only)
        self._subtasks_btn = Button("Subtasks", id="subtasks_btn", variant="default")
        self._subtasks_btn.add_class("hidden")
        yield self._subtasks_btn

        # Plan settings button (hidden when plan mode is "normal")
        self._plan_settings_btn = Button("⋮", id="plan_settings_btn", variant="default")
        self._plan_settings_btn.add_class("hidden")
        yield self._plan_settings_btn

        # Mode bar help button
        self._mode_help_btn = Button("?", id="mode_help_btn", variant="default")
        yield self._mode_help_btn

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

    def set_coordination_mode(self, mode: str) -> None:
        """Set the coordination mode state.

        Args:
            mode: "parallel" or "decomposition".
        """
        if self._coordination_toggle:
            self._coordination_toggle.set_state(mode)
        self._update_coordination_aux_controls(mode)

    def set_parallel_personas_enabled(self, enabled: bool) -> None:
        """Set the parallel persona toggle state."""
        if self._persona_toggle:
            self._persona_toggle.set_state("on" if enabled else "off")

    def _update_coordination_aux_controls(self, mode: str) -> None:
        """Update controls that depend on coordination mode."""
        if not self._subtasks_btn:
            pass
        elif mode == "decomposition":
            self._subtasks_btn.remove_class("hidden")
        else:
            self._subtasks_btn.add_class("hidden")

        if self._persona_toggle:
            if mode == "parallel":
                self._persona_toggle.remove_class("hidden")
            else:
                self._persona_toggle.add_class("hidden")

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable all mode toggles.

        Args:
            enabled: True to enable all toggles, False to disable.
        """
        if self._plan_toggle:
            self._plan_toggle.set_enabled(enabled)
        if self._agent_toggle:
            self._agent_toggle.set_enabled(enabled)
        if self._coordination_toggle:
            self._coordination_toggle.set_enabled(enabled)
        if self._refinement_toggle:
            self._refinement_toggle.set_enabled(enabled)
        if self._persona_toggle:
            self._persona_toggle.set_enabled(enabled)
        if self._subtasks_btn:
            self._subtasks_btn.disabled = not enabled

    def get_plan_mode(self) -> str:
        """Get current plan mode."""
        return self._plan_toggle.get_state() if self._plan_toggle else "normal"

    def get_agent_mode(self) -> str:
        """Get current agent mode."""
        return self._agent_toggle.get_state() if self._agent_toggle else "multi"

    def get_coordination_mode(self) -> str:
        """Get current coordination mode."""
        return self._coordination_toggle.get_state() if self._coordination_toggle else "parallel"

    def get_refinement_enabled(self) -> bool:
        """Get current refinement mode."""
        return self._refinement_toggle.get_state() == "on" if self._refinement_toggle else True

    def get_parallel_personas_enabled(self) -> bool:
        """Get current parallel persona toggle state."""
        return self._persona_toggle.get_state() == "on" if self._persona_toggle else False

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
        elif event.button.id == "mode_help_btn":
            _mode_log("ModeBar: Help button pressed")
            self.post_message(ModeHelpClicked())
        elif event.button.id == "subtasks_btn":
            _mode_log("ModeBar: Subtasks button pressed")
            self.post_message(SubtasksClicked())

    def on_mode_changed(self, event: ModeChanged) -> None:
        """Let mode change messages bubble to parent."""
        _mode_log(f"ModeBar.on_mode_changed: {event.mode_type}={event.value}")
        if event.mode_type == "coordination":
            self._update_coordination_aux_controls(event.value)
        # Don't stop - let it bubble to TextualApp
