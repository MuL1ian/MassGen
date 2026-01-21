# -*- coding: utf-8 -*-
"""
Agent Tab Bar Widget for MassGen TUI.

Provides a horizontal tab bar for switching between agent panels.
"""

from typing import Dict, List, Optional

from textual.app import ComposeResult
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


class AgentTabChanged(Message):
    """Message emitted when the active agent tab changes."""

    def __init__(self, agent_id: str) -> None:
        """Initialize the message.

        Args:
            agent_id: The ID of the newly active agent.
        """
        self.agent_id = agent_id
        super().__init__()


def _tab_log(msg: str) -> None:
    """Log to TUI debug file."""
    try:
        import logging

        log = logging.getLogger("massgen.tui.debug")
        if not log.handlers:
            handler = logging.FileHandler("/tmp/massgen_tui_debug.log", mode="a")
            handler.setFormatter(logging.Formatter("%(asctime)s [TAB] %(message)s", datefmt="%H:%M:%S"))
            log.addHandler(handler)
            log.setLevel(logging.DEBUG)
            log.propagate = False
        log.debug(msg)
    except Exception:
        pass


class AgentTab(Static):
    """Individual tab representing an agent.

    Displays agent ID with a status badge and supports click-to-select.
    Styles are defined in the TCSS theme files (dark.tcss, light.tcss).
    """

    # Enable clicking on the widget
    can_focus = True

    # Status icon mapping - use actual Unicode characters for reliable rendering
    STATUS_ICONS = {
        "waiting": "⏳",  # Hourglass
        "working": "⚙️",  # Gear
        "streaming": "📝",  # Memo/Writing
        "completed": "✅",  # Check mark
        "error": "❌",  # Cross mark
        "winner": "🏆",  # Trophy
    }

    def __init__(
        self,
        agent_id: str,
        key_index: int = 0,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """Initialize the agent tab.

        Args:
            agent_id: The agent's identifier.
            key_index: Keyboard shortcut index (1-9, 0 for none).
            id: Optional DOM ID.
            classes: Optional CSS classes.
        """
        super().__init__(id=id, classes=classes)
        self.agent_id = agent_id
        self.key_index = key_index
        self._status = "waiting"
        self._disabled = False  # For single-agent mode

    def compose(self) -> ComposeResult:
        """No child widgets needed - we use renderable."""
        return []

    def render(self) -> str:
        """Render the tab content with agent ID and status."""
        status_icon = self.STATUS_ICONS.get(self._status, "🤖")
        key_hint = f"[{self.key_index}]" if self.key_index else ""
        return f" {status_icon} {self.agent_id} {key_hint} "

    def update_status(self, status: str) -> None:
        """Update the agent's status.

        Args:
            status: One of "waiting", "working", "streaming", "completed", "error", "winner".
        """
        # Remove old status class
        self.remove_class(
            "status-waiting",
            "status-working",
            "status-streaming",
            "status-completed",
            "status-error",
            "status-winner",
        )
        self._status = status
        self.add_class(f"status-{status}")
        self.refresh()

    def set_active(self, active: bool) -> None:
        """Set whether this tab is the active (selected) tab.

        Args:
            active: True if this is the active tab.
        """
        if active:
            self.remove_class("inactive")
            self.add_class("active")
        else:
            self.remove_class("active")
            self.add_class("inactive")

    def set_disabled(self, disabled: bool) -> None:
        """Set whether this tab is disabled (greyed out in single-agent mode).

        Args:
            disabled: True to disable (grey out), False to enable.
        """
        self._disabled = disabled
        if disabled:
            self.add_class("disabled")
        else:
            self.remove_class("disabled")
        self.refresh()

    def is_disabled(self) -> bool:
        """Check if this tab is disabled."""
        return self._disabled

    async def on_click(self) -> None:
        """Handle click to select this tab.

        In single-agent mode, clicking a disabled tab selects it as the new active agent.
        """
        _tab_log(f"AgentTab.on_click: {self.agent_id} (disabled={self._disabled})")
        # Always post the message - let parent handle single-agent selection logic
        self.post_message(AgentTabChanged(self.agent_id))


class AgentTabBar(Widget):
    """Horizontal tab bar for switching between agent panels.

    Displays a row of tabs, one per agent, with status badges.
    Supports keyboard navigation (Tab, Shift+Tab, number keys).
    """

    DEFAULT_CSS = """
    AgentTabBar {
        height: 3;
        width: 100%;
        layout: horizontal;
        background: $surface;
        border-bottom: solid $primary;
        padding: 0 1;
    }
    """

    # Reactive attribute for the active agent
    active_agent: reactive[str] = reactive("")

    def __init__(
        self,
        agent_ids: List[str],
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """Initialize the tab bar.

        Args:
            agent_ids: List of agent IDs to display as tabs.
            id: Optional DOM ID.
            classes: Optional CSS classes.
        """
        super().__init__(id=id, classes=classes)
        self._agent_ids = agent_ids
        self._tabs: Dict[str, AgentTab] = {}

    def compose(self) -> ComposeResult:
        """Create agent tabs."""
        for idx, agent_id in enumerate(self._agent_ids):
            key_index = idx + 1 if idx < 9 else 0  # 1-9 for first 9 agents
            # Assign a color class based on agent index (cycles through 8 colors)
            color_class = f"agent-color-{(idx % 8) + 1}"
            tab = AgentTab(
                agent_id=agent_id,
                key_index=key_index,
                id=f"tab_{agent_id.replace(' ', '_').replace('.', '_')}",
                classes=f"inactive {color_class}",
            )
            self._tabs[agent_id] = tab
            yield tab

    def on_mount(self) -> None:
        """Set initial active agent after mounting."""
        if self._agent_ids and not self.active_agent:
            self.set_active(self._agent_ids[0])

    def set_active(self, agent_id: str) -> None:
        """Set the active (selected) agent tab.

        Args:
            agent_id: The agent to make active.
        """
        if agent_id not in self._tabs:
            return

        # Deactivate all tabs
        for tab in self._tabs.values():
            tab.set_active(False)

        # Activate the selected tab
        self._tabs[agent_id].set_active(True)
        self.active_agent = agent_id

    def update_agent_status(self, agent_id: str, status: str) -> None:
        """Update the status badge for an agent.

        Args:
            agent_id: The agent to update.
            status: One of "waiting", "working", "streaming", "completed", "error", "winner".
        """
        if agent_id in self._tabs:
            self._tabs[agent_id].update_status(status)

    def set_winner(self, agent_id: str) -> None:
        """Mark an agent as winner, dimming all others.

        Args:
            agent_id: The winning agent's ID.
        """
        if agent_id not in self._tabs:
            return

        for aid, tab in self._tabs.items():
            if aid == agent_id:
                tab.update_status("winner")
                tab.remove_class("dimmed")
            else:
                tab.add_class("dimmed")

    def clear_winner(self) -> None:
        """Reset all tabs to normal state, removing winner/dimmed styling."""
        for tab in self._tabs.values():
            tab.remove_class("dimmed")
            # If the tab was a winner, set it to completed
            if tab._status == "winner":
                tab.update_status("completed")

    def get_next_agent(self) -> Optional[str]:
        """Get the next agent ID after the currently active one.

        Returns:
            The next agent ID, wrapping to first if at end.
        """
        if not self._agent_ids:
            return None
        try:
            idx = self._agent_ids.index(self.active_agent)
            next_idx = (idx + 1) % len(self._agent_ids)
            return self._agent_ids[next_idx]
        except ValueError:
            return self._agent_ids[0] if self._agent_ids else None

    def get_previous_agent(self) -> Optional[str]:
        """Get the previous agent ID before the currently active one.

        Returns:
            The previous agent ID, wrapping to last if at start.
        """
        if not self._agent_ids:
            return None
        try:
            idx = self._agent_ids.index(self.active_agent)
            prev_idx = (idx - 1) % len(self._agent_ids)
            return self._agent_ids[prev_idx]
        except ValueError:
            return self._agent_ids[-1] if self._agent_ids else None

    def get_agent_by_index(self, index: int) -> Optional[str]:
        """Get agent ID by 1-based index.

        Args:
            index: 1-based index (1-9 for keyboard shortcuts).

        Returns:
            The agent ID at that index, or None if invalid.
        """
        zero_index = index - 1
        if 0 <= zero_index < len(self._agent_ids):
            return self._agent_ids[zero_index]
        return None

    def set_single_agent_mode(self, enabled: bool, selected_agent: Optional[str] = None) -> None:
        """Enable or disable single-agent mode with visual feedback.

        In single-agent mode, only the selected agent tab is enabled (not greyed out).
        All other tabs are disabled (greyed out) but can still be clicked to
        switch the selected agent.

        Args:
            enabled: True to enable single-agent mode, False for multi-agent mode.
            selected_agent: The agent ID to keep enabled (required when enabled=True).
        """
        _tab_log(f"AgentTabBar.set_single_agent_mode: enabled={enabled}, selected={selected_agent}")

        if enabled:
            if not selected_agent or selected_agent not in self._tabs:
                # Default to first agent if none specified
                selected_agent = self._agent_ids[0] if self._agent_ids else None

            for agent_id, tab in self._tabs.items():
                if agent_id == selected_agent:
                    tab.set_disabled(False)
                    tab.set_active(True)
                else:
                    tab.set_disabled(True)
                    tab.set_active(False)
        else:
            # Multi-agent mode: enable all tabs, keep current selection
            for tab in self._tabs.values():
                tab.set_disabled(False)

    def is_single_agent_mode(self) -> bool:
        """Check if any tabs are disabled (single-agent mode indicator)."""
        return any(tab.is_disabled() for tab in self._tabs.values())

    def get_enabled_agents(self) -> List[str]:
        """Get list of enabled (non-disabled) agent IDs.

        Returns:
            List of agent IDs that are not disabled.
        """
        return [agent_id for agent_id, tab in self._tabs.items() if not tab.is_disabled()]

    def on_agent_tab_changed(self, event: AgentTabChanged) -> None:
        """Handle tab click - let it bubble to parent.

        The parent (TextualApp) will handle the actual panel switching.
        We don't stop or re-post - just let it bubble naturally.
        """
        _tab_log(f"AgentTabBar.on_agent_tab_changed: {event.agent_id} - letting bubble to parent")
        # Don't stop or re-post - let the message bubble up naturally
        # The parent TextualApp will receive this via on_agent_tab_changed
