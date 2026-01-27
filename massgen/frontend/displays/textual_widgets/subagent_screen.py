# -*- coding: utf-8 -*-
"""
Full-Screen Subagent View for MassGen TUI.

Replaces the small modal overlay with a full-screen subagent view that
looks and behaves like the main TUI using inheritance to share code.

Design:
```
+---------------------------------------------------------------------+
| <- Back | Subagent: bio_agent                  | Model: gpt-4o      |
+---------------------------------------------------------------------+
| [bio_agent] [data_agent] [research_agent]                           |
+---------------------------------------------------------------------+
| R1 * R2 * F                     | 5:30 | 2.4k | $0.003              |
+---------------------------------------------------------------------+
|                                                                     |
| [Timeline content - tools, thinking, text, etc.]                    |
|                                                                     |
+---------------------------------------------------------------------+
| * Running...                                                        |
+---------------------------------------------------------------------+
|               [Copy Answer]  [Back to Main]                         |
+---------------------------------------------------------------------+
```

Features:
- Full-screen layout with TUI parity
- Tab bar for multiple subagents (reuses AgentTabBar)
- Status ribbon with round navigation (reuses AgentStatusRibbon)
- Live updates while subagent is running
- Keyboard shortcuts (Esc to close, Tab for agent switching)
"""

import logging
from typing import Callable, Dict, List, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import Button, Static

from massgen.events import EventReader, MassGenEvent
from massgen.subagent.models import SubagentDisplayData, SubagentResult

from ..base_tui_layout import BaseTUILayoutMixin
from ..content_processor import ContentOutput, ContentProcessor
from .agent_status_ribbon import AgentStatusRibbon
from .content_sections import TimelineSection
from .tab_bar import AgentTabBar, AgentTabChanged

logger = logging.getLogger(__name__)


class SubagentHeader(Horizontal):
    """Header bar for subagent screen with back button and subagent info."""

    DEFAULT_CSS = """
    SubagentHeader {
        dock: top;
        height: 3;
        background: $surface;
        border-bottom: solid $primary-darken-2;
        padding: 0 1;
        align: center middle;
    }

    SubagentHeader .back-button {
        width: auto;
        min-width: 8;
        margin-right: 1;
    }

    SubagentHeader .subagent-title {
        width: 1fr;
        color: $primary;
        text-style: bold;
    }

    SubagentHeader .model-info {
        width: auto;
        color: $text-muted;
    }
    """

    def __init__(
        self,
        subagent: SubagentDisplayData,
        *,
        id: Optional[str] = None,
    ) -> None:
        super().__init__(id=id)
        self._subagent = subagent

    def compose(self) -> ComposeResult:
        yield Button("<- Back", variant="default", classes="back-button", id="back_btn")
        yield Static(f"Subagent: {self._subagent.id}", classes="subagent-title", id="header_title")
        # Model info would come from config - placeholder for now
        yield Static("", classes="model-info", id="model_info")

    def update_subagent(self, subagent: SubagentDisplayData) -> None:
        """Update the header for a new subagent."""
        self._subagent = subagent
        try:
            self.query_one("#header_title", Static).update(f"Subagent: {subagent.id}")
        except Exception:
            pass


class SubagentFooter(Horizontal):
    """Footer bar with action buttons."""

    DEFAULT_CSS = """
    SubagentFooter {
        dock: bottom;
        height: 3;
        background: $surface;
        border-top: solid $primary-darken-2;
        padding: 0 1;
        align: center middle;
    }

    SubagentFooter .footer-button {
        width: auto;
        min-width: 16;
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Button("Copy Answer", variant="default", classes="footer-button", id="copy_btn")
        yield Button("Back to Main", variant="primary", classes="footer-button", id="back_btn_footer")


class SubagentStatusLine(Static):
    """Status line showing subagent execution status (pulsing dot if running)."""

    DEFAULT_CSS = """
    SubagentStatusLine {
        height: 1;
        width: 100%;
        background: $surface;
        border-top: solid $primary-darken-3;
        padding: 0 1;
    }

    SubagentStatusLine.running {
        color: $warning;
    }

    SubagentStatusLine.completed {
        color: $success;
    }

    SubagentStatusLine.error {
        color: $error;
    }
    """

    STATUS_ICONS = {
        "completed": "✓",
        "running": "●",
        "pending": "○",
        "error": "✗",
        "timeout": "⏱",
        "failed": "✗",
    }

    def __init__(self, status: str = "running", **kwargs) -> None:
        super().__init__(**kwargs)
        self._status = status
        self._elapsed = 0

    def render(self) -> Text:
        """Render the status line."""
        text = Text()
        icon = self.STATUS_ICONS.get(self._status, "●")
        text.append(f" {icon} ", style="bold")
        text.append(self._status.capitalize())
        if self._status == "running":
            text.append(f" ({self._elapsed}s)")
        return text

    def update_status(self, status: str, elapsed: int = 0) -> None:
        """Update the status display."""
        self._status = status
        self._elapsed = elapsed
        # Update CSS class
        self.remove_class("running", "completed", "error")
        if status == "running":
            self.add_class("running")
        elif status in ("completed", "success"):
            self.add_class("completed")
        elif status in ("error", "failed", "timeout"):
            self.add_class("error")
        self.refresh()


class SubagentPanel(Container, BaseTUILayoutMixin):
    """Panel for subagent content - inherits content pipeline from BaseTUILayoutMixin.

    This panel provides full content handling parity with the main TUI's AgentPanel
    by inheriting the shared BaseTUILayoutMixin.
    """

    DEFAULT_CSS = """
    SubagentPanel {
        width: 100%;
        height: 1fr;
        background: $background;
    }

    SubagentPanel #subagent-timeline {
        width: 100%;
        height: 100%;
        padding: 1 2;
        overflow-y: auto;
    }
    """

    def __init__(
        self,
        subagent: SubagentDisplayData,
        ribbon: Optional[AgentStatusRibbon] = None,
        *,
        id: Optional[str] = None,
    ) -> None:
        super().__init__(id=id)
        self.agent_id = subagent.id  # For compatibility with BaseTUILayoutMixin
        self._subagent = subagent
        self._ribbon = ribbon

        # Initialize content pipeline from mixin
        self.init_content_pipeline()

    def compose(self) -> ComposeResult:
        yield TimelineSection(id="subagent-timeline")

    # -------------------------------------------------------------------------
    # BaseTUILayoutMixin abstract method implementations
    # -------------------------------------------------------------------------

    def _get_timeline(self) -> Optional[TimelineSection]:
        """Get the TimelineSection widget (implements BaseTUILayoutMixin)."""
        try:
            return self.query_one("#subagent-timeline", TimelineSection)
        except Exception:
            return None

    def _get_ribbon(self) -> Optional[AgentStatusRibbon]:
        """Get the AgentStatusRibbon widget (implements BaseTUILayoutMixin)."""
        return self._ribbon

    def set_ribbon(self, ribbon: AgentStatusRibbon) -> None:
        """Set the ribbon reference after mounting."""
        self._ribbon = ribbon


class SubagentScreen(Screen):
    """Full-screen view for subagent execution.

    Provides full TUI parity with the main view:
    - Tab bar for multiple subagents
    - Status ribbon with round navigation
    - Timeline with tools, thinking, text
    - Live updates while running
    """

    BINDINGS = [
        ("escape", "close", "Back"),
        ("c", "copy_answer", "Copy Answer"),
        ("tab", "next_subagent", "Next Subagent"),
        ("shift+tab", "prev_subagent", "Previous Subagent"),
    ]

    DEFAULT_CSS = """
    SubagentScreen {
        width: 100%;
        height: 100%;
        background: $background;
    }

    SubagentScreen #subagent-content {
        width: 100%;
        height: 1fr;
    }
    """

    # Polling interval for live updates
    POLL_INTERVAL = 0.5

    def __init__(
        self,
        subagent: SubagentDisplayData,
        all_subagents: Optional[List[SubagentDisplayData]] = None,
        status_callback: Optional[Callable[[str], Optional[SubagentDisplayData]]] = None,
    ) -> None:
        """Initialize the subagent screen.

        Args:
            subagent: The subagent to display
            all_subagents: All subagents for navigation (tab bar)
            status_callback: Callback to get updated status
        """
        super().__init__()
        self._subagent = subagent
        self._all_subagents = all_subagents or [subagent]
        self._current_index = 0

        # Find current index
        for i, sa in enumerate(self._all_subagents):
            if sa.id == subagent.id:
                self._current_index = i
                break

        self._status_callback = status_callback
        self._poll_timer: Optional[Timer] = None
        self._event_reader: Optional[EventReader] = None
        self._content_processor: Optional[ContentProcessor] = None
        self._tool_count = 0
        self._round_number = 1
        self._final_answer: Optional[str] = None

        # References to widgets (set after compose)
        self._header: Optional[SubagentHeader] = None
        self._tab_bar: Optional[AgentTabBar] = None
        self._inner_tab_bar: Optional[AgentTabBar] = None
        self._ribbon: Optional[AgentStatusRibbon] = None
        self._panel: Optional[SubagentPanel] = None
        self._status_line: Optional[SubagentStatusLine] = None

        # Inner agent tracking
        self._inner_agents: List[str] = []
        self._inner_agent_models: Dict[str, str] = {}
        self._current_inner_agent: Optional[str] = None

    def compose(self) -> ComposeResult:
        # Build agent IDs and models for tab bar
        agent_ids = [sa.id for sa in self._all_subagents]
        agent_models: Dict[str, str] = {}  # Would come from config

        # Header with back button
        yield SubagentHeader(self._subagent, id="subagent-header")

        # Top-level subagent selector (only if multiple subagents)
        if len(self._all_subagents) > 1:
            yield AgentTabBar(
                agent_ids=agent_ids,
                agent_models=agent_models,
                tab_id_prefix="subagent_",  # Prefix to avoid ID conflicts
                id="subagent-tab-bar",
            )

        # Inner agent tabs - ALWAYS shown (this subagent's full TUI)
        # Each subagent IS a full MassGen subcall that may have multiple inner agents
        # Initialize with placeholder - will be updated in on_mount after event reader is ready
        yield AgentTabBar(
            agent_ids=[self._subagent.id],  # Placeholder, updated in on_mount
            agent_models={},
            tab_id_prefix="inner_",  # Prefix to avoid ID conflicts with outer tabs
            id="inner-agent-tabs",
        )

        # Status ribbon
        yield AgentStatusRibbon(
            agent_id=self._subagent.id,
            id="subagent-ribbon",
        )

        # Content panel
        with Vertical(id="subagent-content"):
            yield SubagentPanel(self._subagent, id="subagent-panel")

        # Execution status line
        yield SubagentStatusLine(
            status=self._subagent.status,
            id="subagent-status-line",
        )

        # Footer with buttons
        yield SubagentFooter(id="subagent-footer")

    def on_mount(self) -> None:
        """Initialize event reader and load events."""
        # Get widget references
        try:
            self._header = self.query_one("#subagent-header", SubagentHeader)
            self._panel = self.query_one("#subagent-panel", SubagentPanel)
            self._status_line = self.query_one("#subagent-status-line", SubagentStatusLine)
        except Exception:
            pass

        try:
            self._ribbon = self.query_one("#subagent-ribbon", AgentStatusRibbon)
            if self._panel and self._ribbon:
                self._panel.set_ribbon(self._ribbon)
        except Exception:
            pass

        try:
            self._tab_bar = self.query_one("#subagent-tab-bar", AgentTabBar)
            if self._tab_bar:
                self._tab_bar.set_active(self._subagent.id)
        except Exception:
            pass

        try:
            self._inner_tab_bar = self.query_one("#inner-agent-tabs", AgentTabBar)
        except Exception:
            pass

        # Initialize event reader and load content
        self._init_event_reader()

        # Detect inner agents and update the inner tab bar
        self._inner_agents, self._inner_agent_models = self._detect_inner_agents()
        self._current_inner_agent = self._inner_agents[0] if self._inner_agents else self._subagent.id

        # Update inner agent tabs with detected agents
        if self._inner_tab_bar and self._inner_agents:
            self._inner_tab_bar.update_agents(self._inner_agents, self._inner_agent_models)
            self._inner_tab_bar.set_active(self._current_inner_agent)

        self._load_initial_events()

        # Start polling if subagent is running
        if self._subagent.status in ("running", "pending"):
            self._poll_timer = self.set_interval(self.POLL_INTERVAL, self._poll_updates)

    def on_unmount(self) -> None:
        """Stop polling when unmounted."""
        if self._poll_timer is not None:
            self._poll_timer.stop()
            self._poll_timer = None

    def _detect_inner_agents(self) -> tuple[List[str], Dict[str, str]]:
        """Detect agent IDs and models from the subagent's logs.

        Tries multiple sources:
        1. execution_metadata.yaml - contains full config with agent names and models
        2. events.jsonl - has agent_id fields on events

        Returns:
            Tuple of (agent_ids list, agent_models dict mapping agent_id to model name).
            Always returns at least the subagent ID itself if no agents are found.
        """
        import yaml

        agent_ids: List[str] = []
        agent_models: Dict[str, str] = {}

        # Try to read from execution_metadata.yaml
        # log_path is now the exact path to events.jsonl, so parent is the logs directory
        from pathlib import Path

        try:
            if self._subagent.log_path:
                events_path = Path(self._subagent.log_path)
                logs_dir = events_path.parent  # e.g., .../full_logs/
                metadata_file = logs_dir / "execution_metadata.yaml"

                if metadata_file.exists():
                    with open(metadata_file, encoding="utf-8") as f:
                        metadata = yaml.safe_load(f)

                    # Extract agents from config
                    # Note: agents is a LIST, not a dict - each item has 'id' and 'backend' keys
                    config = metadata.get("config", {})
                    agents_list = config.get("agents", [])

                    if isinstance(agents_list, list) and agents_list:
                        for agent_cfg in agents_list:
                            if isinstance(agent_cfg, dict):
                                agent_id = agent_cfg.get("id")
                                if agent_id:
                                    agent_ids.append(agent_id)
                                    # Get model from nested backend config
                                    backend_cfg = agent_cfg.get("backend", {})
                                    model = backend_cfg.get("model", "")
                                    if model:
                                        # Shorten model name for display
                                        short_model = model.split("/")[-1]  # Handle "openai/gpt-4o" format
                                        agent_models[agent_id] = short_model

        except Exception as e:
            print(f"[SubagentScreen] Error detecting inner agents: {e}")

        # Fallback: detect from events if no config found
        if not agent_ids and self._event_reader:
            seen_ids: set[str] = set()
            events = self._event_reader.read_all()
            for event in events:
                # Check agent_id field
                if event.agent_id and event.agent_id not in seen_ids:
                    seen_ids.add(event.agent_id)
                # Also check data.source for backwards compatibility
                source = event.data.get("source")
                if source and source not in seen_ids:
                    seen_ids.add(source)
            agent_ids = sorted(seen_ids)

        # Always return at least the subagent ID
        if not agent_ids:
            logger.info(
                f"[SubagentScreen] No inner agents detected for {self._subagent.id}, using fallback",
            )
            return [self._subagent.id], {}

        logger.info(
            f"[SubagentScreen] Detected {len(agent_ids)} inner agents: {agent_ids}, models: {agent_models}",
        )
        return agent_ids, agent_models

    def _init_event_reader(self) -> None:
        """Initialize the event reader for the current subagent."""
        from pathlib import Path

        if not self._subagent.log_path:
            logger.warning(
                f"[SubagentScreen] No log_path for subagent {self._subagent.id}",
            )
            return

        log_path = Path(self._subagent.log_path)

        # Handle both file path and directory path (safety net for inconsistent sources)
        if log_path.is_dir():
            # Base directory - resolve to events.jsonl using shared method
            resolved = SubagentResult.resolve_events_path(log_path)
            if resolved:
                events_file = Path(resolved)
            else:
                logger.warning(
                    f"[SubagentScreen] Could not resolve events.jsonl from directory: {log_path}",
                )
                return
        else:
            # Already a file path
            events_file = log_path

        if events_file.exists():
            logger.info(f"[SubagentScreen] Using events file: {events_file}")
            self._event_reader = EventReader(events_file)
            self._content_processor = ContentProcessor()
        else:
            logger.warning(
                f"[SubagentScreen] Events file does not exist: {events_file}",
            )

    def _load_initial_events(self) -> None:
        """Load all existing events and build timeline."""
        if not self._event_reader or not self._content_processor:
            return

        events = self._event_reader.read_all()
        self._process_events(events)

    def _process_events(self, events: List[MassGenEvent]) -> None:
        """Process events and add to timeline."""
        if not self._content_processor or not self._panel:
            logger.warning(
                f"[SubagentScreen] Cannot process events: processor={self._content_processor is not None}, panel={self._panel is not None}",
            )
            return

        logger.info(f"[SubagentScreen] Processing {len(events)} events")
        output_count = 0
        for event in events:
            output = self._content_processor.process_event(event, self._round_number)
            if output:
                output_count += 1
                logger.debug(f"[SubagentScreen] Got output: {output.output_type}")
                # Update round number from round_start events
                if output.output_type == "separator" and output.round_number:
                    self._round_number = output.round_number

                self._apply_output_to_panel(output)
        logger.info(f"[SubagentScreen] Generated {output_count} outputs from {len(events)} events")

        # Flush any remaining batch
        final_output = self._content_processor.flush_pending_batch(self._round_number)
        if final_output:
            self._apply_output_to_panel(final_output)

    def _apply_output_to_panel(self, output: ContentOutput) -> None:
        """Apply a ContentOutput to the panel using BaseTUILayoutMixin methods."""
        if not self._panel:
            return

        round_number = output.round_number or self._round_number

        try:
            timeline = self._panel._get_timeline()
            if timeline is None:
                return

            if output.output_type == "tool" and output.tool_data:
                self._tool_count += 1
                tool_data = output.tool_data
                batch_action = output.batch_action

                if batch_action in ("pending", "standalone"):
                    timeline.add_tool(tool_data, round_number=round_number)
                elif batch_action == "convert_to_batch" and output.batch_id and output.pending_tool_id:
                    timeline.convert_tool_to_batch(
                        output.pending_tool_id,
                        tool_data,
                        output.batch_id,
                        output.server_name or "tools",
                        round_number=round_number,
                    )
                elif batch_action == "add_to_batch" and output.batch_id:
                    timeline.add_tool_to_batch(output.batch_id, tool_data)
                elif batch_action == "update_batch":
                    timeline.update_tool_in_batch(tool_data.tool_id, tool_data)
                elif batch_action == "update_standalone":
                    timeline.update_tool(tool_data.tool_id, tool_data)
                else:
                    timeline.add_tool(tool_data, round_number=round_number)

            elif output.output_type == "tool_batch" and output.batch_tools:
                self._tool_count += len(output.batch_tools)
                batch_id = output.batch_id or f"batch_{self._tool_count}"
                server_name = output.server_name or "tools"

                timeline.add_batch(batch_id, server_name, round_number=round_number)
                for tool_data in output.batch_tools:
                    timeline.add_tool_to_batch(batch_id, tool_data)
                    if tool_data.status in ("success", "error"):
                        timeline.update_tool_in_batch(tool_data.tool_id, tool_data)

            elif output.output_type == "thinking" and output.text_content:
                timeline.add_text(
                    output.text_content,
                    style=output.text_style,
                    text_class=output.text_class or "thinking-inline",
                    round_number=round_number,
                )

            elif output.output_type == "text" and output.text_content:
                timeline.add_text(
                    output.text_content,
                    style=output.text_style,
                    text_class=output.text_class or "content-inline",
                    round_number=round_number,
                )

            elif output.output_type == "status" and output.text_content:
                timeline.add_text(
                    output.text_content,
                    style=output.text_style,
                    text_class=output.text_class or "status",
                    round_number=round_number,
                )

            elif output.output_type == "presentation" and output.text_content:
                timeline.add_text(
                    output.text_content,
                    style=output.text_style,
                    text_class=output.text_class or "response",
                    round_number=round_number,
                )

            elif output.output_type == "injection" and output.text_content:
                timeline.add_text(
                    output.text_content,
                    style=output.text_style,
                    text_class=output.text_class or "injection",
                    round_number=round_number,
                )

            elif output.output_type == "reminder" and output.text_content:
                timeline.add_text(
                    output.text_content,
                    style=output.text_style,
                    text_class=output.text_class or "reminder",
                    round_number=round_number,
                )

            elif output.output_type == "separator":
                self._round_number = output.round_number
                timeline.add_separator(
                    output.separator_label,
                    round_number=output.round_number,
                    subtitle=output.separator_subtitle,
                )

            elif output.output_type == "final_answer" and output.text_content:
                self._final_answer = output.text_content
                timeline.add_text(
                    f"✓ FINAL ANSWER\n{output.text_content}",
                    style="bold green",
                    text_class="final-answer",
                    round_number=round_number,
                )

        except Exception:
            pass

        # Update ribbon
        self._update_status_display()

    def _poll_updates(self) -> None:
        """Poll for status and event updates."""
        # Update status if callback available
        if self._status_callback:
            new_data = self._status_callback(self._subagent.id)
            if new_data:
                self._subagent = new_data
                self._update_status_display()

        # Read new events
        if self._event_reader and self._content_processor:
            new_events = self._event_reader.get_new_events()
            if new_events:
                self._process_events(new_events)

        # Stop polling if completed
        if self._subagent.status not in ("running", "pending"):
            if self._poll_timer:
                self._poll_timer.stop()
                self._poll_timer = None

    def _update_status_display(self) -> None:
        """Update status displays."""
        # Update status line
        if self._status_line:
            self._status_line.update_status(
                self._subagent.status,
                int(self._subagent.elapsed_seconds),
            )

        # Update ribbon
        if self._ribbon:
            self._ribbon.set_round(self._subagent.id, self._round_number, False)

        # Update tab bar status
        if self._tab_bar:
            self._tab_bar.update_agent_status(self._subagent.id, self._subagent.status)

    def _switch_subagent(self, index: int) -> None:
        """Switch to a different subagent."""
        if 0 <= index < len(self._all_subagents):
            self._current_index = index
            self._subagent = self._all_subagents[index]

            # Reset state
            self._tool_count = 0
            self._round_number = 1
            self._final_answer = None
            self._content_processor = ContentProcessor()

            # Re-initialize event reader
            self._init_event_reader()

            # Detect inner agents for the new subagent
            self._inner_agents, self._inner_agent_models = self._detect_inner_agents()
            self._current_inner_agent = self._inner_agents[0] if self._inner_agents else self._subagent.id

            # Update inner agent tabs
            if self._inner_tab_bar and self._inner_agents:
                self._inner_tab_bar.update_agents(self._inner_agents, self._inner_agent_models)
                self._inner_tab_bar.set_active(self._current_inner_agent)

            # Clear and reload timeline
            try:
                if self._panel:
                    timeline = self._panel._get_timeline()
                    if timeline:
                        timeline.clear()
                self._load_initial_events()
            except Exception:
                pass

            # Update header
            if self._header:
                self._header.update_subagent(self._subagent)

            # Update tab bar
            if self._tab_bar:
                self._tab_bar.set_active(self._subagent.id)

            # Update ribbon agent
            if self._ribbon:
                self._ribbon.set_agent(self._subagent.id)

            # Update status
            self._update_status_display()

            # Restart polling if needed
            if self._subagent.status in ("running", "pending") and not self._poll_timer:
                self._poll_timer = self.set_interval(self.POLL_INTERVAL, self._poll_updates)

    def _switch_inner_agent(self, agent_id: str) -> None:
        """Switch to a different inner agent's timeline.

        This filters the timeline to show only events from the selected agent.

        Args:
            agent_id: The agent ID to switch to
        """
        if agent_id == self._current_inner_agent:
            return

        self._current_inner_agent = agent_id

        # Reset content processor and reload events filtered by agent
        self._tool_count = 0
        self._round_number = 1
        self._content_processor = ContentProcessor()

        # Clear and reload timeline with filtered events
        try:
            if self._panel:
                timeline = self._panel._get_timeline()
                if timeline:
                    timeline.clear()
            self._load_events_for_agent(agent_id)
        except Exception:
            pass

        # Update ribbon to show selected agent
        if self._ribbon:
            self._ribbon.set_agent(agent_id)

        # Update inner tab bar selection
        if self._inner_tab_bar:
            self._inner_tab_bar.set_active(agent_id)

    def _load_events_for_agent(self, agent_id: Optional[str]) -> None:
        """Load events filtered by agent ID.

        Args:
            agent_id: The agent ID to filter by, or None for all events
        """
        if not self._event_reader or not self._content_processor:
            return

        events = self._event_reader.read_all()

        # Filter by agent if specified
        if agent_id:
            events = [e for e in events if e.agent_id == agent_id or e.data.get("source") == agent_id]

        self._process_events(events)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id in ("back_btn", "back_btn_footer"):
            self.dismiss()
        elif event.button.id == "copy_btn":
            self._copy_answer()

    def on_agent_tab_changed(self, event: AgentTabChanged) -> None:
        """Handle tab bar agent selection."""
        event.stop()

        # Determine which tab bar sent the event
        # Check by comparing the control's ID or parent
        control_id = event.control.id if event.control else None

        if control_id == "subagent-tab-bar":
            # Top-level subagent selector - switch to different subagent
            for i, sa in enumerate(self._all_subagents):
                if sa.id == event.agent_id:
                    self._switch_subagent(i)
                    break
        elif control_id == "inner-agent-tabs":
            # Inner agent tabs - switch to different inner agent within same subagent
            self._switch_inner_agent(event.agent_id)
        else:
            # Fallback: try to determine by checking if agent_id matches a subagent
            for i, sa in enumerate(self._all_subagents):
                if sa.id == event.agent_id:
                    self._switch_subagent(i)
                    return
            # Otherwise assume it's an inner agent
            if event.agent_id in self._inner_agents:
                self._switch_inner_agent(event.agent_id)

    def action_close(self) -> None:
        """Close the screen and return to main view."""
        self.dismiss()

    def action_next_subagent(self) -> None:
        """Navigate to next subagent."""
        self._switch_subagent((self._current_index + 1) % len(self._all_subagents))

    def action_prev_subagent(self) -> None:
        """Navigate to previous subagent."""
        self._switch_subagent((self._current_index - 1) % len(self._all_subagents))

    def action_copy_answer(self) -> None:
        """Copy answer to clipboard."""
        self._copy_answer()

    def _copy_answer(self) -> None:
        """Copy the answer to clipboard."""
        content = self._final_answer or self._subagent.answer_preview
        if content:
            try:
                import pyperclip

                pyperclip.copy(content)
                self.notify("Answer copied to clipboard!")
            except ImportError:
                self.notify("pyperclip not installed - cannot copy", severity="warning")
            except Exception as e:
                self.notify(f"Failed to copy: {e}", severity="error")
