# -*- coding: utf-8 -*-
"""
Content Section Widgets for MassGen TUI.

Composable UI sections for displaying different content types:
- ToolSection: Collapsible box containing tool cards
- TimelineSection: Chronological view with interleaved tools and text
- ThinkingSection: Streaming content area
- ResponseSection: Clean response display area
- StatusBadge: Compact inline status indicator
- CompletionFooter: Subtle completion indicator
"""

from typing import Dict, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.widgets import RichLog, Static

from ..content_handlers import ToolDisplayData
from .tool_card import ToolCallCard


class ToolSection(Vertical):
    """Collapsible section containing tool call cards.

    Design:
    ```
    ┌ Tools ──────────────────────────────────────────────── 2 calls ┐
    │ 📁 read_file                                       ✓ 0.3s      │
    │ 💻 execute_command                                 ✓ 1.2s      │
    └────────────────────────────────────────────────────────────────┘
    ```

    When expanded, individual tools can also be expanded to show details.
    """

    is_collapsed = reactive(False)  # Default expanded to show tool activity
    tool_count = reactive(0)

    DEFAULT_CSS = """
    ToolSection {
        height: auto;
        max-height: 40%;
        margin: 0 0 1 0;
        padding: 0;
    }

    ToolSection.collapsed {
        height: 3;
        overflow: hidden;
    }

    ToolSection.hidden {
        display: none;
    }

    ToolSection .section-header {
        height: 1;
        width: 100%;
        padding: 0 1;
    }

    ToolSection #tool_container {
        height: auto;
        max-height: 100%;
        padding: 0 1;
        overflow-y: auto;
    }
    """

    def __init__(self, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self._tools: Dict[str, ToolCallCard] = {}
        self.add_class("collapsed")
        self.add_class("hidden")  # Start hidden until first tool

    def compose(self) -> ComposeResult:
        yield Static(self._build_header(), id="tool_section_header", classes="section-header")
        yield ScrollableContainer(id="tool_container")

    def _build_header(self) -> Text:
        """Build the section header text."""
        text = Text()

        # Collapse indicator
        indicator = "▶" if self.is_collapsed else "▼"
        text.append(f"{indicator} ", style="dim")

        # Title
        text.append("Tools", style="bold")

        # Count badge
        if self.tool_count > 0:
            text.append(" ─" + "─" * 40 + "─ ", style="dim")
            text.append(f"{self.tool_count} call{'s' if self.tool_count != 1 else ''}", style="cyan")

        return text

    def watch_is_collapsed(self, collapsed: bool) -> None:
        """Update UI when collapse state changes."""
        if collapsed:
            self.add_class("collapsed")
        else:
            self.remove_class("collapsed")

        # Update header
        try:
            header = self.query_one("#tool_section_header", Static)
            header.update(self._build_header())
        except Exception:
            pass

    def watch_tool_count(self, count: int) -> None:
        """Update header when tool count changes."""
        # Show section when we have tools
        if count > 0:
            self.remove_class("hidden")
        else:
            self.add_class("hidden")

        try:
            header = self.query_one("#tool_section_header", Static)
            header.update(self._build_header())
        except Exception:
            pass

    def on_click(self, event) -> None:
        """Toggle collapsed state on header click."""
        # Only toggle if clicking the header area
        try:
            header = self.query_one("#tool_section_header", Static)
            if event.widget == header or event.widget == self:
                self.is_collapsed = not self.is_collapsed
        except Exception:
            pass

    def add_tool(self, tool_data: ToolDisplayData) -> ToolCallCard:
        """Add a new tool card.

        Args:
            tool_data: Tool display data from handler

        Returns:
            The created ToolCallCard for later updates
        """
        card = ToolCallCard(
            tool_name=tool_data.tool_name,
            tool_type=tool_data.tool_type,
            call_id=tool_data.tool_id,
            id=f"card_{tool_data.tool_id}",
        )

        # Set args preview if available (both truncated and full)
        if tool_data.args_summary:
            card.set_params(tool_data.args_summary, tool_data.args_full)

        self._tools[tool_data.tool_id] = card
        self.tool_count = len(self._tools)

        try:
            container = self.query_one("#tool_container", ScrollableContainer)
            container.mount(card)
            # Auto-scroll to show new tool
            container.scroll_end(animate=False)
        except Exception:
            pass

        return card

    def update_tool(self, tool_id: str, tool_data: ToolDisplayData) -> None:
        """Update an existing tool card.

        Args:
            tool_id: The tool ID to update
            tool_data: Updated tool data
        """
        if tool_id not in self._tools:
            return

        card = self._tools[tool_id]

        if tool_data.status == "success":
            card.set_result(tool_data.result_summary or "", tool_data.result_full)
        elif tool_data.status == "error":
            card.set_error(tool_data.error or "Unknown error")

        # Auto-scroll after update
        try:
            container = self.query_one("#tool_container", ScrollableContainer)
            container.scroll_end(animate=False)
        except Exception:
            pass

    def get_tool(self, tool_id: str) -> Optional[ToolCallCard]:
        """Get a tool card by ID."""
        return self._tools.get(tool_id)

    def clear(self) -> None:
        """Clear all tool cards."""
        try:
            container = self.query_one("#tool_container", ScrollableContainer)
            container.remove_children()
        except Exception:
            pass
        self._tools.clear()
        self.tool_count = 0
        self.add_class("hidden")


class ReasoningSection(Vertical):
    """Collapsible section for agent coordination/reasoning content.

    Groups voting, reasoning, and internal coordination content together
    in a collapsible section. Collapsed by default but can be expanded
    to see the full reasoning.

    Design (collapsed):
    ```
    ▶ 🧠 Reasoning (5 items) ─────────────────────────────────────────
    ```

    Design (expanded):
    ```
    ▼ 🧠 Reasoning ───────────────────────────────────────────────────
    │ I'll vote for Agent 1 because the answer is clear...
    │ The existing answers are correct and complete.
    │ Agent 2 provides a concise explanation.
    │ ...
    └─────────────────────────────────────────────────────────────────
    ```
    """

    is_collapsed = reactive(True)  # Collapsed by default
    item_count = reactive(0)

    DEFAULT_CSS = """
    ReasoningSection {
        height: auto;
        max-height: 30%;
        margin: 0 0 1 0;
        padding: 0;
        border: dashed $primary-darken-3;
    }

    ReasoningSection.collapsed #reasoning_content {
        display: none;
    }

    ReasoningSection.hidden {
        display: none;
    }

    ReasoningSection #reasoning_header {
        height: 1;
        width: 100%;
        padding: 0 1;
        background: $surface-darken-1;
    }

    ReasoningSection #reasoning_content {
        height: auto;
        max-height: 100%;
        padding: 0 1;
        overflow-y: auto;
    }

    ReasoningSection .reasoning-text {
        width: 100%;
        padding: 0;
        color: $text-muted;
    }
    """

    def __init__(self, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self._items: list = []
        self.add_class("collapsed")
        self.add_class("hidden")  # Start hidden until content arrives

    def compose(self) -> ComposeResult:
        yield Static(self._build_header(), id="reasoning_header")
        yield ScrollableContainer(id="reasoning_content")

    def _build_header(self) -> Text:
        """Build the section header text."""
        text = Text()

        # Collapse indicator
        indicator = "▶" if self.is_collapsed else "▼"
        text.append(f"{indicator} ", style="dim")

        # Icon and title
        text.append("🧠 ", style="")
        text.append("Reasoning", style="bold dim")

        # Count badge
        if self.item_count > 0:
            text.append(" ─" + "─" * 30 + "─ ", style="dim")
            text.append(f"({self.item_count} item{'s' if self.item_count != 1 else ''})", style="dim cyan")

        return text

    def watch_is_collapsed(self, collapsed: bool) -> None:
        """Update UI when collapse state changes."""
        if collapsed:
            self.add_class("collapsed")
        else:
            self.remove_class("collapsed")

        try:
            header = self.query_one("#reasoning_header", Static)
            header.update(self._build_header())
        except Exception:
            pass

    def watch_item_count(self, count: int) -> None:
        """Update header when item count changes."""
        if count > 0:
            self.remove_class("hidden")
        else:
            self.add_class("hidden")

        try:
            header = self.query_one("#reasoning_header", Static)
            header.update(self._build_header())
        except Exception:
            pass

    def on_click(self, event) -> None:
        """Toggle collapsed state on header click."""
        try:
            header = self.query_one("#reasoning_header", Static)
            if event.widget == header or event.widget == self:
                self.is_collapsed = not self.is_collapsed
        except Exception:
            pass

    def add_content(self, content: str) -> None:
        """Add reasoning content.

        Args:
            content: Reasoning/coordination text
        """
        if not content.strip():
            return

        self._items.append(content)
        self.item_count = len(self._items)

        try:
            container = self.query_one("#reasoning_content", ScrollableContainer)
            widget = Static(
                Text(content, style="dim"),
                id=f"reasoning_{self.item_count}",
                classes="reasoning-text",
            )
            container.mount(widget)
        except Exception:
            pass

    def clear(self) -> None:
        """Clear all reasoning content."""
        try:
            container = self.query_one("#reasoning_content", ScrollableContainer)
            container.remove_children()
        except Exception:
            pass
        self._items.clear()
        self.item_count = 0
        self.add_class("hidden")


class TimelineSection(Vertical):
    """Chronological timeline showing tools and text interleaved.

    This widget displays content in the order it arrives, preserving
    the natural flow of agent activity. Tool cards and text blocks
    appear inline as they occur.

    Coordination/reasoning content is grouped into a collapsible
    ReasoningSection at the top of the timeline.

    Design:
    ```
    ▶ 🧠 Reasoning (5 items) ─────────────────────────────────────────

    │ Let me help you with that...                                    │
    │                                                                 │
    │ ▶ 📁 filesystem/read_file                         ⏳ running... │
    │   {"path": "/tmp/test.txt"}                                     │
    │                                                                 │
    │   📁 filesystem/read_file                              ✓ (0.3s) │
    │   {"path": "/tmp/test.txt"}                                     │
    │   → File contents: Hello world...                               │
    │                                                                 │
    │ The file contains: Hello world                                  │
    ```
    """

    DEFAULT_CSS = """
    TimelineSection {
        height: 1fr;
        padding: 0;
        margin: 0;
    }

    TimelineSection #timeline_container {
        height: 1fr;
        padding: 0 1;
        overflow-y: auto;
    }

    TimelineSection .timeline-text {
        width: 100%;
        padding: 0 0 1 0;
    }

    TimelineSection .timeline-text.status {
        color: #569cd6;
    }

    TimelineSection .timeline-text.thinking {
        color: #858585;
    }

    TimelineSection .timeline-text.response {
        color: #4ec9b0;
    }

    TimelineSection .timeline-text.coordination {
        color: #858585;
        background: $surface-darken-1;
        padding: 0 1;
    }
    """

    def __init__(self, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self._tools: Dict[str, ToolCallCard] = {}
        self._item_count = 0
        self._reasoning_section_id = f"reasoning_{id}" if id else "reasoning_section"

    def compose(self) -> ComposeResult:
        # Reasoning section at the top (collapsible)
        yield ReasoningSection(id=self._reasoning_section_id)
        # Main timeline content
        yield ScrollableContainer(id="timeline_container")

    def add_tool(self, tool_data: ToolDisplayData) -> ToolCallCard:
        """Add a tool card to the timeline.

        Args:
            tool_data: Tool display data

        Returns:
            The created ToolCallCard
        """
        card = ToolCallCard(
            tool_name=tool_data.tool_name,
            tool_type=tool_data.tool_type,
            call_id=tool_data.tool_id,
            id=f"tl_card_{tool_data.tool_id}",
        )

        if tool_data.args_summary:
            card.set_params(tool_data.args_summary, tool_data.args_full)

        self._tools[tool_data.tool_id] = card
        self._item_count += 1

        try:
            container = self.query_one("#timeline_container", ScrollableContainer)
            container.mount(card)
            container.scroll_end(animate=False)
        except Exception:
            pass

        return card

    def update_tool(self, tool_id: str, tool_data: ToolDisplayData) -> None:
        """Update an existing tool card.

        Args:
            tool_id: Tool ID to update
            tool_data: Updated tool data
        """
        if tool_id not in self._tools:
            return

        card = self._tools[tool_id]

        if tool_data.status == "success":
            card.set_result(tool_data.result_summary or "", tool_data.result_full)
        elif tool_data.status == "error":
            card.set_error(tool_data.error or "Unknown error")

        try:
            container = self.query_one("#timeline_container", ScrollableContainer)
            container.scroll_end(animate=False)
        except Exception:
            pass

    def get_tool(self, tool_id: str) -> Optional[ToolCallCard]:
        """Get a tool card by ID."""
        return self._tools.get(tool_id)

    def add_text(self, content: str, style: str = "", text_class: str = "") -> None:
        """Add text content to the timeline.

        Args:
            content: Text content
            style: Rich style string
            text_class: CSS class (status, thinking, response)
        """
        if not content.strip():
            return

        self._item_count += 1
        widget_id = f"tl_text_{self._item_count}"

        try:
            container = self.query_one("#timeline_container", ScrollableContainer)

            classes = "timeline-text"
            if text_class:
                classes += f" {text_class}"

            if style:
                widget = Static(Text(content, style=style), id=widget_id, classes=classes)
            else:
                widget = Static(content, id=widget_id, classes=classes)

            container.mount(widget)
            container.scroll_end(animate=False)
        except Exception:
            pass

    def add_separator(self, label: str = "") -> None:
        """Add a visual separator to the timeline.

        Args:
            label: Optional label for the separator
        """
        self._item_count += 1
        widget_id = f"tl_sep_{self._item_count}"

        try:
            container = self.query_one("#timeline_container", ScrollableContainer)

            sep_text = Text()
            sep_text.append("─" * 50, style="dim")
            if label:
                sep_text.append(f" {label} ", style="dim italic")
                sep_text.append("─" * 10, style="dim")

            container.mount(Static(sep_text, id=widget_id))
            container.scroll_end(animate=False)
        except Exception:
            pass

    def add_reasoning(self, content: str) -> None:
        """Add coordination/reasoning content to the collapsible reasoning section.

        Args:
            content: Reasoning/voting/coordination text
        """
        try:
            reasoning = self.query_one(f"#{self._reasoning_section_id}", ReasoningSection)
            reasoning.add_content(content)
        except Exception:
            pass

    def clear(self) -> None:
        """Clear all timeline content."""
        try:
            container = self.query_one("#timeline_container", ScrollableContainer)
            container.remove_children()
        except Exception:
            pass
        # Also clear reasoning section
        try:
            reasoning = self.query_one(f"#{self._reasoning_section_id}", ReasoningSection)
            reasoning.clear()
        except Exception:
            pass
        self._tools.clear()
        self._item_count = 0


class ThinkingSection(Vertical):
    """Section for streaming thinking/reasoning content.

    Wraps a RichLog for streaming compatibility while providing
    clean visual treatment.
    """

    DEFAULT_CSS = """
    ThinkingSection {
        height: auto;
        max-height: 50%;
        padding: 0;
    }

    ThinkingSection #thinking_log {
        height: auto;
        max-height: 100%;
        padding: 0 1;
    }
    """

    def __init__(self, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self._line_count = 0

    def compose(self) -> ComposeResult:
        yield RichLog(id="thinking_log", highlight=False, wrap=True, markup=True)

    def append(self, content: str, style: str = "") -> None:
        """Append content to the thinking log.

        Args:
            content: Text content to append
            style: Optional Rich style string
        """
        try:
            log = self.query_one("#thinking_log", RichLog)
            if style:
                log.write(Text(content, style=style))
            else:
                log.write(content)
            self._line_count += 1
        except Exception:
            pass

    def append_text(self, text: Text) -> None:
        """Append a Rich Text object.

        Args:
            text: Pre-styled Rich Text
        """
        try:
            log = self.query_one("#thinking_log", RichLog)
            log.write(text)
            self._line_count += 1
        except Exception:
            pass

    def clear(self) -> None:
        """Clear the thinking log."""
        try:
            log = self.query_one("#thinking_log", RichLog)
            log.clear()
            self._line_count = 0
        except Exception:
            pass

    @property
    def line_count(self) -> int:
        """Get the number of lines written."""
        return self._line_count


class ResponseSection(Vertical):
    """Section for displaying final agent responses.

    Provides a clean, visually distinct area for the agent's answer
    separate from status updates and thinking content.

    Design:
    ```
    ╭─────────────────────────────────────────────────────────────────╮
    │ Response                                                         │
    ├─────────────────────────────────────────────────────────────────┤
    │                                                                  │
    │ The answer to your question is 42.                               │
    │                                                                  │
    │ Here's why:                                                      │
    │ - First reason                                                   │
    │ - Second reason                                                  │
    │                                                                  │
    ╰─────────────────────────────────────────────────────────────────╯
    ```
    """

    DEFAULT_CSS = """
    ResponseSection {
        height: auto;
        max-height: 50%;
        margin: 1 0;
        padding: 0;
        border: round $primary-lighten-2;
        background: $surface;
    }

    ResponseSection.hidden {
        display: none;
    }

    ResponseSection #response_header {
        height: 1;
        width: 100%;
        padding: 0 1;
        background: $primary-darken-2;
        color: $text;
    }

    ResponseSection #response_content {
        height: auto;
        max-height: 100%;
        padding: 1 2;
        overflow-y: auto;
    }

    ResponseSection #response_content Static {
        width: 100%;
    }
    """

    def __init__(self, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self._content_parts: list = []
        self.add_class("hidden")  # Start hidden until content arrives

    def compose(self) -> ComposeResult:
        yield Static("📝 Response", id="response_header")
        yield ScrollableContainer(id="response_content")

    def set_content(self, content: str, style: str = "") -> None:
        """Set the response content (replaces existing).

        Args:
            content: Response text
            style: Optional Rich style
        """
        try:
            container = self.query_one("#response_content", ScrollableContainer)
            container.remove_children()

            if content.strip():
                self.remove_class("hidden")
                if style:
                    container.mount(Static(Text(content, style=style)))
                else:
                    container.mount(Static(content))
            else:
                self.add_class("hidden")
        except Exception:
            pass

    def append_content(self, content: str, style: str = "") -> None:
        """Append to response content.

        Args:
            content: Text to append
            style: Optional Rich style
        """
        try:
            container = self.query_one("#response_content", ScrollableContainer)
            self.remove_class("hidden")

            if style:
                container.mount(Static(Text(content, style=style)))
            else:
                container.mount(Static(content))

            # Auto-scroll to bottom
            container.scroll_end(animate=False)
        except Exception:
            pass

    def clear(self) -> None:
        """Clear response content."""
        try:
            container = self.query_one("#response_content", ScrollableContainer)
            container.remove_children()
            self.add_class("hidden")
        except Exception:
            pass


class StatusBadge(Static):
    """Compact inline status indicator.

    Design: `● Connected` or `⟳ Working` - small, not prominent.
    """

    DEFAULT_CSS = """
    StatusBadge {
        width: auto;
        height: 1;
        padding: 0 1;
        text-align: right;
    }

    StatusBadge.status-connected {
        color: #4ec9b0;
    }

    StatusBadge.status-working {
        color: #dcdcaa;
    }

    StatusBadge.status-streaming {
        color: #569cd6;
    }

    StatusBadge.status-completed {
        color: #4ec9b0;
    }

    StatusBadge.status-error {
        color: #f44747;
    }

    StatusBadge.status-waiting {
        color: #858585;
    }
    """

    status = reactive("waiting")

    STATUS_DISPLAY = {
        "connected": ("●", "Connected"),
        "working": ("⟳", "Working"),
        "streaming": ("▶", "Streaming"),
        "completed": ("✓", "Complete"),
        "error": ("✗", "Error"),
        "waiting": ("○", "Waiting"),
    }

    def __init__(self, initial_status: str = "waiting", id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self.status = initial_status
        self.add_class(f"status-{initial_status}")

    def render(self) -> Text:
        """Render the status badge."""
        icon, label = self.STATUS_DISPLAY.get(self.status, ("?", "Unknown"))
        return Text(f"{icon} {label}")

    def watch_status(self, old_status: str, new_status: str) -> None:
        """Update styling when status changes."""
        self.remove_class(f"status-{old_status}")
        self.add_class(f"status-{new_status}")
        self.refresh()

    def set_status(self, status: str) -> None:
        """Set the status.

        Args:
            status: One of: connected, working, streaming, completed, error, waiting
        """
        self.status = status


class CompletionFooter(Static):
    """Subtle completion indicator at bottom of panel.

    Design: `────────────────────────────────────── ✓ Complete ───`
    """

    DEFAULT_CSS = """
    CompletionFooter {
        height: 1;
        width: 100%;
        padding: 0 1;
        text-align: center;
    }

    CompletionFooter.hidden {
        display: none;
    }

    CompletionFooter.status-completed {
        color: #4ec9b0;
    }

    CompletionFooter.status-error {
        color: #f44747;
    }
    """

    is_visible = reactive(False)
    status = reactive("completed")

    def __init__(self, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self.add_class("hidden")

    def render(self) -> Text:
        """Render the footer line."""
        if self.status == "completed":
            return Text("─" * 30 + " ✓ Complete " + "─" * 30, style="dim green")
        elif self.status == "error":
            return Text("─" * 30 + " ✗ Error " + "─" * 30, style="dim red")
        else:
            return Text("")

    def watch_is_visible(self, visible: bool) -> None:
        """Show/hide footer."""
        if visible:
            self.remove_class("hidden")
        else:
            self.add_class("hidden")

    def watch_status(self, old_status: str, new_status: str) -> None:
        """Update styling on status change."""
        self.remove_class(f"status-{old_status}")
        self.add_class(f"status-{new_status}")
        self.refresh()

    def show_completed(self) -> None:
        """Show completion indicator."""
        self.status = "completed"
        self.is_visible = True

    def show_error(self) -> None:
        """Show error indicator."""
        self.status = "error"
        self.is_visible = True

    def hide(self) -> None:
        """Hide the footer."""
        self.is_visible = False
