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

    # Icons for different modes
    ICONS = {
        "plan": {"normal": "📋", "plan": "📝", "execute": "▶️"},
        "agent": {"multi": "👥", "single": "👤"},
        "refinement": {"on": "🔄", "off": "⏩"},
    }

    # Labels for states
    LABELS = {
        "plan": {"normal": "Normal", "plan": "Planning", "execute": "Executing"},
        "agent": {"multi": "Multi-Agent", "single": "Single"},
        "refinement": {"on": "Refine ON", "off": "Refine OFF"},
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
        width: 100%;
        layout: horizontal;
        background: $surface;
        border-bottom: solid $primary-darken-2;
        padding: 0 1;
        align: left middle;
    }

    ModeBar.hidden {
        display: none;
    }

    ModeBar ModeToggle {
        margin: 0 1;
        padding: 0 1;
        background: $surface-darken-1;
        color: $text;
    }

    ModeBar ModeToggle:hover {
        background: $primary-darken-1;
    }

    ModeBar ModeToggle.disabled {
        background: $surface-darken-2;
        color: $text-muted;
    }

    ModeBar ModeToggle.state-plan,
    ModeBar ModeToggle.state-execute {
        background: $success-darken-1;
        color: $text;
    }

    ModeBar ModeToggle.state-single {
        background: $warning-darken-1;
        color: $text;
    }

    ModeBar ModeToggle.state-off {
        background: $error-darken-2;
        color: $text;
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

        # Plan info (shown when executing plan)
        self._plan_info = Label("", id="plan_info")
        yield self._plan_info

        # Spacer to push override button to the right
        yield Static("", id="mode_spacer")

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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "override_btn":
            _mode_log("ModeBar: Override button pressed")
            self.post_message(OverrideRequested())

    def on_mode_changed(self, event: ModeChanged) -> None:
        """Let mode change messages bubble to parent."""
        _mode_log(f"ModeBar.on_mode_changed: {event.mode_type}={event.value}")
        # Don't stop - let it bubble to TextualApp
