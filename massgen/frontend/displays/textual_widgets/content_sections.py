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

import logging
from typing import Dict, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import RichLog, Static

from ..content_handlers import ToolDisplayData, get_mcp_tool_name
from .tool_batch_card import ToolBatchCard, ToolBatchItem
from .tool_card import ToolCallCard

logger = logging.getLogger(__name__)


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
        yield Static(
            self._build_header(),
            id="tool_section_header",
            classes="section-header",
        )
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
            text.append(
                f"{self.tool_count} call{'s' if self.tool_count != 1 else ''}",
                style="cyan",
            )

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

        # Apply args if available and not already set on card
        if tool_data.args_full and not card._params_full:
            args_summary = tool_data.args_summary or (tool_data.args_full[:77] + "..." if len(tool_data.args_full) > 80 else tool_data.args_full)
            card.set_params(args_summary, tool_data.args_full)

        if tool_data.status == "success":
            card.set_result(tool_data.result_summary or "", tool_data.result_full)
        elif tool_data.status == "error":
            card.set_error(tool_data.error or "Unknown error")
        elif tool_data.status == "background":
            card.set_background_result(
                tool_data.result_summary or "",
                tool_data.result_full,
                tool_data.async_id,
            )

        # Auto-scroll after update
        try:
            container = self.query_one("#tool_container", ScrollableContainer)
            container.scroll_end(animate=False)
        except Exception:
            pass

    def get_tool(self, tool_id: str) -> Optional[ToolCallCard]:
        """Get a tool card by ID."""
        return self._tools.get(tool_id)

    def get_running_tools_count(self) -> int:
        """Count tools that are currently running."""
        return sum(1 for card in self._tools.values() if card.status == "running")

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

    # Start expanded, auto-collapse after threshold
    is_collapsed = reactive(False)
    item_count = reactive(0)
    COLLAPSE_THRESHOLD = 5  # Auto-collapse after this many items
    PREVIEW_LINES = 2  # Show this many lines when collapsed

    DEFAULT_CSS = """
    ReasoningSection {
        height: auto;
        max-height: 30%;
        margin: 0 0 1 0;
        padding: 0;
        border: solid #30363d;
        border-left: thick #484f58;
        background: #161b22;
    }

    ReasoningSection.collapsed #reasoning_content {
        max-height: 2;
        overflow: hidden;
    }

    ReasoningSection.hidden {
        display: none;
    }

    ReasoningSection #reasoning_header {
        height: 1;
        width: 100%;
        padding: 0 1;
        background: #21262d;
        color: #8b949e;
    }

    ReasoningSection #reasoning_header:hover {
        background: #30363d;
    }

    ReasoningSection #reasoning_content {
        height: auto;
        max-height: 100%;
        padding: 0 1;
        overflow-y: auto;
        background: #0d1117;
    }

    ReasoningSection .reasoning-text {
        width: 100%;
        padding: 0;
        color: #8b949e;
    }
    """

    def __init__(self, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self._items: list = []
        # Start expanded (not collapsed) but hidden until content arrives
        self.add_class("hidden")

    def compose(self) -> ComposeResult:
        yield Static(self._build_header(), id="reasoning_header")
        yield ScrollableContainer(id="reasoning_content")

    def _build_header(self) -> Text:
        """Build the section header text."""
        text = Text()

        # Collapse indicator
        indicator = "▶" if self.is_collapsed else "▼"
        text.append(f"{indicator} ", style="cyan")

        # Icon and title
        text.append("💭 ", style="")
        text.append("Reasoning", style="bold #c9d1d9")

        # Count badge - show hidden count when collapsed
        if self.item_count > 0:
            if self.is_collapsed and self.item_count > self.PREVIEW_LINES:
                hidden = self.item_count - self.PREVIEW_LINES
                text.append(f"  (+{hidden} more)", style="dim cyan")
            else:
                text.append(f"  ({self.item_count})", style="dim")

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

            # Format content with bullet point for structure
            formatted = Text()
            formatted.append("• ", style="cyan")
            formatted.append(content, style="#c9d1d9")

            widget = Static(
                formatted,
                id=f"reasoning_{self.item_count}",
                classes="reasoning-text",
            )
            container.mount(widget)

            # Auto-collapse after threshold (but still show preview)
            if self.item_count > self.COLLAPSE_THRESHOLD and not self.is_collapsed:
                self.is_collapsed = True

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


class TimelineScrollContainer(ScrollableContainer):
    """ScrollableContainer that detects scroll mode via scroll position changes.

    This container monitors the scroll_y reactive property to detect when the user
    scrolls away from the bottom (entering scroll mode) or returns to the bottom
    (exiting scroll mode). It posts messages that parent widgets can handle.

    The _auto_scrolling flag is used to distinguish programmatic scrolls (from
    auto-scroll) from user-initiated scrolls.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._user_scrolled_up = False
        self._auto_scrolling = False
        self._scroll_pending = False
        self._debug_scroll = True  # Debug flag

    def _log(self, msg: str) -> None:
        """Debug logging helper."""
        if self._debug_scroll:
            from datetime import datetime

            with open("/tmp/scroll_debug.log", "a") as f:
                f.write(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}\n")

    def on_mount(self) -> None:
        """Log container info on mount."""
        self._log(f"MOUNT: id={self.id} size={self.size} content_size={self.content_size}")
        self._log(f"MOUNT: virtual_size={self.virtual_size} container_size={self.container_size}")
        self._log(f"MOUNT: scrollbar_gutter={self.scrollbar_gutter} show_vertical_scrollbar={self.show_vertical_scrollbar}")
        # Log parent chain and check for other scrollable containers
        parent = self.parent
        chain = []
        while parent:
            pinfo = f"{parent.__class__.__name__}(id={getattr(parent, 'id', None)})"
            # Check if parent has scrolling
            if hasattr(parent, "scroll_y"):
                pinfo += f" scroll_y={parent.scroll_y}"
            if hasattr(parent, "max_scroll_y"):
                pinfo += f" max_scroll_y={parent.max_scroll_y}"
            if hasattr(parent, "vertical_scrollbar"):
                try:
                    vs = parent.vertical_scrollbar
                    if vs:
                        pinfo += f" HAS_SCROLLBAR(pos={vs.position},display={vs.display})"
                except Exception:
                    pass
            chain.append(pinfo)
            parent = getattr(parent, "parent", None)
        self._log(f"MOUNT: parent_chain={' -> '.join(chain)}")
        # Log scrollbar info
        try:
            vscroll = self.vertical_scrollbar
            self._log(f"MOUNT: vertical_scrollbar={vscroll} visible={vscroll.display if vscroll else 'N/A'}")
        except Exception as e:
            self._log(f"MOUNT: vertical_scrollbar error: {e}")

    def on_resize(self, event) -> None:
        """Log resize events to see size changes."""
        self._log(f"RESIZE: size={self.size} content_size={self.content_size} max_scroll_y={self.max_scroll_y}")
        try:
            vscroll = self.vertical_scrollbar
            if vscroll:
                self._log(f"RESIZE: scrollbar size={vscroll.size} visible={vscroll.display}")
        except Exception as e:
            self._log(f"RESIZE: scrollbar error: {e}")

    def watch_scroll_y(self, old_value: float, new_value: float) -> None:
        """Detect when user scrolls away from bottom."""
        try:
            vscroll = self.vertical_scrollbar
            scrollbar_pos = vscroll.position if vscroll else "N/A"
            window_size = vscroll.window_size if vscroll else "N/A"
            window_virtual_size = vscroll.window_virtual_size if vscroll else "N/A"
            self._log(f"watch_scroll_y: scroll_y={new_value:.1f} max={self.max_scroll_y:.1f} | scrollbar pos={scrollbar_pos} window_size={window_size} virtual={window_virtual_size}")
            # Manually sync scrollbar position (Textual might not be doing this automatically)
            if vscroll and self.max_scroll_y > 0:
                # position is in units of the scrollbar, need to map scroll_y to position
                # position should go from 0 to (virtual_size - window_size)
                new_pos = int(new_value)
                if vscroll.position != new_pos:
                    vscroll.position = new_pos
                    self._log(f"watch_scroll_y: SET scrollbar.position = {new_pos}")
        except Exception as e:
            self._log(f"watch_scroll_y: old={old_value:.1f} new={new_value:.1f} max={self.max_scroll_y:.1f} auto={self._auto_scrolling} (scrollbar error: {e})")

        if self._auto_scrolling:
            return  # Ignore programmatic scrolls

        # Don't trigger scroll mode if there's no scrollable content yet
        if self.max_scroll_y <= 0:
            return

        # Check if at top/bottom (with tolerance for float precision)
        at_top = new_value <= 2
        at_bottom = new_value >= self.max_scroll_y - 2

        # Phase 11.2: Post scroll position for scroll indicators
        self.post_message(self.ScrollPositionChanged(at_top=at_top, at_bottom=at_bottom))

        if new_value < old_value and not at_bottom:
            # User scrolled up - enter scroll mode
            if not self._user_scrolled_up:
                self._user_scrolled_up = True
                self.post_message(self.ScrollModeEntered())
        elif at_bottom and self._user_scrolled_up:
            # User scrolled to bottom - exit scroll mode
            self._user_scrolled_up = False
            self.post_message(self.ScrollModeExited())

    def scroll_end(self, animate: bool = False) -> None:
        """Auto-scroll to end, marking it as programmatic."""
        self._log(f"scroll_end called: pending={self._scroll_pending} max_scroll_y={self.max_scroll_y:.1f} current_scroll_y={self.scroll_y:.1f}")

        # Debounce: if scroll is already pending, don't queue another
        if self._scroll_pending:
            self._log("scroll_end: SKIPPED (pending)")
            return

        self._scroll_pending = True

        def do_scroll() -> None:
            self._log(f"do_scroll executing: max_scroll_y={self.max_scroll_y:.1f} scroll_y before={self.scroll_y:.1f}")
            self._scroll_pending = False
            # Set flag BEFORE scroll - it stays set until reset_auto_scroll is called
            self._auto_scrolling = True
            super(TimelineScrollContainer, self).scroll_end(animate=animate)
            self._log(f"do_scroll after super().scroll_end: scroll_y={self.scroll_y:.1f}")
            # Force scrollbar refresh
            try:
                if self.vertical_scrollbar:
                    self.vertical_scrollbar.refresh()
                    self._log("do_scroll: forced scrollbar refresh")
            except Exception as e:
                self._log(f"do_scroll: scrollbar refresh error: {e}")
            # Reset flag after a brief delay to allow scroll events to be processed
            self.set_timer(0.1, self._reset_auto_scroll)

        # Defer scroll until after layout is complete
        self.call_after_refresh(do_scroll)

    def _reset_auto_scroll(self) -> None:
        """Reset auto-scrolling flag after scroll completes."""
        self._log(f"_reset_auto_scroll: scroll_y={self.scroll_y:.1f}")
        self._auto_scrolling = False

    def reset_scroll_mode(self) -> None:
        """Reset scroll mode tracking state."""
        self._user_scrolled_up = False

    class ScrollModeEntered(Message):
        """Posted when user enters scroll mode by scrolling up."""

    class ScrollModeExited(Message):
        """Posted when user exits scroll mode by scrolling to bottom."""

    class ScrollPositionChanged(Message):
        """Posted when scroll position changes - for scroll indicators.

        Phase 11.2: Scroll indicators support.
        """

        def __init__(self, at_top: bool, at_bottom: bool) -> None:
            self.at_top = at_top
            self.at_bottom = at_bottom
            super().__init__()


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
        width: 100%;
        height: 1fr;
        padding: 0;
        margin: 0;
    }

    TimelineSection #timeline_container {
        width: 100%;
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

    TimelineSection .timeline-text.reasoning-inline {
        color: #8b949e;
        border-left: thick #484f58;
        padding-left: 1;
        margin: 0 0 1 0;
    }

    /* Phase 11.2: Scroll arrow indicators */
    TimelineSection .scroll-arrow-indicator {
        width: 100%;
        height: 1;
        text-align: center;
        color: #8b949e;
        background: transparent;
    }

    TimelineSection .scroll-arrow-indicator.hidden {
        display: none;
    }

    TimelineSection #scroll_top_indicator {
        dock: top;
    }

    TimelineSection #scroll_bottom_indicator {
        dock: bottom;
    }

    /* Phase 12: Generic hidden rule for round-based visibility */
    TimelineSection .hidden {
        display: none;
    }

    TimelineSection #timeline_container .hidden {
        display: none;
    }
    """

    # Maximum number of items to keep in timeline (prevents memory/performance issues)
    MAX_TIMELINE_ITEMS = 75

    def __init__(self, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self._tools: Dict[str, ToolCallCard] = {}
        self._batches: Dict[str, ToolBatchCard] = {}  # batch_id -> ToolBatchCard
        self._tool_to_batch: Dict[str, str] = {}  # tool_id -> batch_id mapping
        self._item_count = 0
        self._reasoning_section_id = f"reasoning_{id}" if id else "reasoning_section"
        # Scroll mode: when True, auto-scroll is paused (user is reading history)
        self._scroll_mode = False
        self._new_content_count = 0  # Count of new items since entering scroll mode
        self._truncation_shown = False  # Track if we've shown truncation message
        # Phase 12: View-based round navigation
        self._viewed_round: int = 1  # Which round is currently being displayed

    def compose(self) -> ComposeResult:
        # Phase 11.2: Top scroll indicator (hidden by default - shows ▲ when content above)
        yield Static("▲ more above", id="scroll_top_indicator", classes="scroll-arrow-indicator hidden")
        # Scroll mode indicator (hidden by default)
        yield Static("", id="scroll_mode_indicator", classes="scroll-indicator hidden")
        # Main timeline content with scroll detection
        yield TimelineScrollContainer(id="timeline_container")
        # Phase 11.2: Bottom scroll indicator (hidden by default - shows ▼ when content below)
        yield Static("▼ more below", id="scroll_bottom_indicator", classes="scroll-arrow-indicator hidden")

    def on_timeline_scroll_container_scroll_mode_entered(
        self,
        event: TimelineScrollContainer.ScrollModeEntered,
    ) -> None:
        """Handle entering scroll mode when user scrolls up."""
        if not self._scroll_mode:
            self._scroll_mode = True
            self._new_content_count = 0
            self._update_scroll_indicator()

    def on_timeline_scroll_container_scroll_mode_exited(
        self,
        event: TimelineScrollContainer.ScrollModeExited,
    ) -> None:
        """Handle exiting scroll mode when user scrolls to bottom."""
        if self._scroll_mode:
            self._scroll_mode = False
            self._new_content_count = 0
            self._update_scroll_indicator()

    def on_timeline_scroll_container_scroll_position_changed(
        self,
        event: TimelineScrollContainer.ScrollPositionChanged,
    ) -> None:
        """Handle scroll position changes - show/hide scroll arrow indicators.

        Phase 11.2: Scroll indicators.
        """
        try:
            top_indicator = self.query_one("#scroll_top_indicator", Static)
            bottom_indicator = self.query_one("#scroll_bottom_indicator", Static)

            # Show top indicator when NOT at top (content above)
            if event.at_top:
                top_indicator.add_class("hidden")
            else:
                top_indicator.remove_class("hidden")

            # Show bottom indicator when NOT at bottom (content below)
            if event.at_bottom:
                bottom_indicator.add_class("hidden")
            else:
                bottom_indicator.remove_class("hidden")
        except Exception:
            pass

    def _update_scroll_indicator(self) -> None:
        """Update the scroll mode indicator in the UI."""
        try:
            indicator = self.query_one("#scroll_mode_indicator", Static)
            if self._scroll_mode:
                # Compact pill format
                if self._new_content_count > 0:
                    msg = f"↑ Scrolling ({self._new_content_count} new) · q/Esc"
                else:
                    msg = "↑ Scrolling · q/Esc"
                indicator.update(msg)
                indicator.remove_class("hidden")
            else:
                indicator.add_class("hidden")
        except Exception:
            pass

    def _auto_scroll(self) -> None:
        """Scroll to end only if not in scroll mode."""
        if self._scroll_mode:
            self._new_content_count += 1
            self._update_scroll_indicator()  # Update to show new content count
            return
        try:
            container = self.query_one("#timeline_container", TimelineScrollContainer)
            # Use smooth animated scrolling for better UX
            container.scroll_end(animate=True)
        except Exception:
            pass

    def exit_scroll_mode(self) -> None:
        """Exit scroll mode and scroll to bottom."""
        self._scroll_mode = False
        self._new_content_count = 0
        try:
            container = self.query_one("#timeline_container", TimelineScrollContainer)
            container.reset_scroll_mode()  # Reset container state
            container.scroll_end(animate=False)
        except Exception:
            pass
        self._update_scroll_indicator()

    def scroll_to_widget(self, widget_id: str) -> None:
        """Scroll to bring a specific widget to the top of the view.

        Args:
            widget_id: The ID of the widget to scroll to (without #)
        """
        try:
            container = self.query_one("#timeline_container", TimelineScrollContainer)
            # Find the widget by ID
            target = container.query_one(f"#{widget_id}")
            if target:
                # Scroll so the widget is at the top
                target.scroll_visible(top=True, animate=False)
        except Exception:
            pass

    @property
    def in_scroll_mode(self) -> bool:
        """Whether scroll mode is active."""
        return self._scroll_mode

    @property
    def new_content_count(self) -> int:
        """Number of new items since entering scroll mode."""
        return self._new_content_count

    def _trim_old_items(self) -> None:
        """Remove oldest items if we exceed MAX_TIMELINE_ITEMS."""
        try:
            container = self.query_one("#timeline_container", TimelineScrollContainer)
            children = list(container.children)

            # Skip the scroll indicator and truncation notice if present
            content_children = [c for c in children if "scroll-indicator" not in c.classes and "truncation-notice" not in c.classes]

            # Check if we exceed the limit
            if len(content_children) <= self.MAX_TIMELINE_ITEMS:
                return

            # Calculate how many to remove
            items_to_remove = len(content_children) - self.MAX_TIMELINE_ITEMS

            if items_to_remove <= 0:
                return

            # Track which rounds have truncation notices
            if not hasattr(self, "_truncation_shown_rounds"):
                self._truncation_shown_rounds = set()

            # First, determine which rounds will have items removed
            rounds_being_truncated = set()
            for child in content_children[:items_to_remove]:
                round_classes = [c for c in child.classes if c.startswith("round-")]
                for rc in round_classes:
                    try:
                        round_num = int(rc.replace("round-", ""))
                        rounds_being_truncated.add(round_num)
                    except ValueError:
                        pass

            # Remove the oldest items (from the beginning of the list)
            removed_count = 0
            for child in content_children[:items_to_remove]:
                # Don't remove tool cards that might still be running
                if hasattr(child, "tool_id") and child.tool_id in self._tools:
                    tool_card = self._tools.get(child.tool_id)
                    if tool_card and hasattr(tool_card, "_status") and tool_card._status == "running":
                        continue
                    # Remove from tools dict
                    self._tools.pop(child.tool_id, None)
                child.remove()
                removed_count += 1

            # Add truncation notices only for rounds that actually had items removed
            if removed_count > 0:
                from textual.widgets import Static

                for truncated_round in rounds_being_truncated:
                    if truncated_round not in self._truncation_shown_rounds:
                        self._truncation_shown_rounds.add(truncated_round)

                        truncation_notice = Static(
                            f"[dim]⋯ Earlier output truncated (showing last {self.MAX_TIMELINE_ITEMS} items)[/]",
                            classes="truncation-notice",
                            markup=True,
                        )
                        # Tag with the round whose items were truncated
                        truncation_notice.add_class(f"round-{truncated_round}")

                        # Find the first remaining item of this round to insert before
                        remaining_children = list(container.children)
                        round_items = [c for c in remaining_children if f"round-{truncated_round}" in c.classes and "truncation-notice" not in c.classes]
                        if round_items:
                            container.mount(truncation_notice, before=round_items[0])

                container.refresh(layout=True)

        except Exception:
            pass

    def add_tool(self, tool_data: ToolDisplayData, round_number: int = 1) -> ToolCallCard:
        """Add a tool card to the timeline.

        Args:
            tool_data: Tool display data
            round_number: The round this content belongs to (for view switching)

        Returns:
            The created ToolCallCard
        """
        # Debug logging - include widget ID to identify which panel
        widget_id = self.id or "unknown"
        with open("/tmp/tui_debug.log", "a") as f:
            f.write(f"DEBUG: TimelineSection.add_tool: panel={widget_id}, tool={tool_data.tool_name}, round={round_number}, viewed={self._viewed_round}\n")

        card = ToolCallCard(
            tool_name=tool_data.tool_name,
            tool_type=tool_data.tool_type,
            call_id=tool_data.tool_id,
            id=f"tl_card_{tool_data.tool_id}",
        )

        if tool_data.args_summary:
            card.set_params(tool_data.args_summary, tool_data.args_full)

        # Phase 12: Tag with round class for CSS visibility switching
        card.add_class(f"round-{round_number}")
        # Hide if viewing a different round
        if round_number != self._viewed_round:
            card.add_class("hidden")

        self._tools[tool_data.tool_id] = card
        self._item_count += 1

        try:
            container = self.query_one("#timeline_container", TimelineScrollContainer)
            container.mount(card)
            self._auto_scroll()
            self._trim_old_items()  # Keep timeline size bounded
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

        # Apply args if available and not already set on card
        if tool_data.args_full and not card._params_full:
            args_summary = tool_data.args_summary or (tool_data.args_full[:77] + "..." if len(tool_data.args_full) > 80 else tool_data.args_full)
            card.set_params(args_summary, tool_data.args_full)

        if tool_data.status == "success":
            card.set_result(tool_data.result_summary or "", tool_data.result_full)
        elif tool_data.status == "error":
            card.set_error(tool_data.error or "Unknown error")
        elif tool_data.status == "background":
            card.set_background_result(
                tool_data.result_summary or "",
                tool_data.result_full,
                tool_data.async_id,
            )

        self._auto_scroll()

    def get_tool(self, tool_id: str) -> Optional[ToolCallCard]:
        """Get a tool card by ID."""
        return self._tools.get(tool_id)

    def get_running_tools_count(self) -> int:
        """Count tools that are currently running or running in background."""
        return sum(1 for card in self._tools.values() if card.status in ("running", "background"))

    def get_background_tools_count(self) -> int:
        """Count tools that are running in background (async operations).

        Note: We don't check if shells are still alive because background shells
        run in separate MCP subprocess(es), not in the main TUI process.
        The shell manager singleton is per-process, so we can't check cross-process.
        """
        return sum(1 for card in self._tools.values() if card.status == "background")

    def get_background_tools(self) -> list:
        """Get list of background tool data for modal display.

        Note: We don't filter by shell alive status because shells run in MCP
        subprocesses with their own BackgroundShellManager singleton.
        """
        bg_tools = []
        for card in self._tools.values():
            if card.status == "background":
                bg_tools.append(
                    {
                        "tool_name": card.tool_name,
                        "display_name": card._display_name,
                        "async_id": card._async_id,
                        "start_time": card._start_time,
                        "result": card._result,
                    },
                )
        return bg_tools

    # === Batch Card Methods ===

    def add_batch(self, batch_id: str, server_name: str, round_number: int = 1) -> ToolBatchCard:
        """Create a new batch card for grouping MCP tools from the same server.

        Args:
            batch_id: Unique ID for this batch
            server_name: MCP server name (e.g., "filesystem")
            round_number: Round number for CSS visibility

        Returns:
            The created ToolBatchCard
        """
        card = ToolBatchCard(
            server_name=server_name,
            id=f"batch_{batch_id}",
        )

        # Phase 12: Tag with round class for CSS visibility
        card.add_class(f"round-{round_number}")
        if round_number != self._viewed_round:
            card.add_class("hidden")

        self._batches[batch_id] = card
        self._item_count += 1

        try:
            container = self.query_one("#timeline_container", TimelineScrollContainer)
            container.mount(card)
            self._auto_scroll()
            self._trim_old_items()
        except Exception:
            pass

        return card

    def add_tool_to_batch(
        self,
        batch_id: str,
        tool_data: ToolDisplayData,
    ) -> None:
        """Add a tool to an existing batch card.

        Args:
            batch_id: ID of the batch to add to
            tool_data: Tool display data
        """
        if batch_id not in self._batches:
            return

        batch_card = self._batches[batch_id]

        # Create ToolBatchItem from ToolDisplayData
        from datetime import datetime

        mcp_tool_name = get_mcp_tool_name(tool_data.tool_name) or tool_data.tool_name
        item = ToolBatchItem(
            tool_id=tool_data.tool_id,
            tool_name=tool_data.tool_name,
            display_name=mcp_tool_name,
            status=tool_data.status,
            args_summary=tool_data.args_summary,
            args_full=tool_data.args_full,
            start_time=tool_data.start_time or datetime.now(),
        )

        batch_card.add_tool(item)
        self._tool_to_batch[tool_data.tool_id] = batch_id
        self._auto_scroll()

    def update_tool_in_batch(self, tool_id: str, tool_data: ToolDisplayData) -> bool:
        """Update a tool within a batch card.

        Args:
            tool_id: ID of the tool to update
            tool_data: Updated tool data

        Returns:
            True if tool was found and updated, False otherwise
        """
        batch_id = self._tool_to_batch.get(tool_id)
        if not batch_id or batch_id not in self._batches:
            return False

        batch_card = self._batches[batch_id]
        mcp_tool_name = get_mcp_tool_name(tool_data.tool_name) or tool_data.tool_name

        # Calculate elapsed time
        elapsed_seconds = None
        if tool_data.elapsed_seconds is not None:
            elapsed_seconds = tool_data.elapsed_seconds
        elif tool_data.start_time and tool_data.end_time:
            elapsed_seconds = (tool_data.end_time - tool_data.start_time).total_seconds()

        item = ToolBatchItem(
            tool_id=tool_data.tool_id,
            tool_name=tool_data.tool_name,
            display_name=mcp_tool_name,
            status=tool_data.status,
            args_summary=tool_data.args_summary,
            args_full=tool_data.args_full,
            result_summary=tool_data.result_summary,
            result_full=tool_data.result_full,
            error=tool_data.error,
            start_time=tool_data.start_time,
            end_time=tool_data.end_time,
            elapsed_seconds=elapsed_seconds,
        )

        batch_card.update_tool(tool_id, item)
        self._auto_scroll()
        return True

    def get_batch(self, batch_id: str) -> Optional[ToolBatchCard]:
        """Get a batch card by ID."""
        return self._batches.get(batch_id)

    def get_tool_batch(self, tool_id: str) -> Optional[str]:
        """Get the batch ID for a tool, if it's in a batch."""
        return self._tool_to_batch.get(tool_id)

    def convert_tool_to_batch(
        self,
        pending_tool_id: str,
        new_tool_data: ToolDisplayData,
        batch_id: str,
        server_name: str,
        round_number: int = 1,
    ) -> Optional[ToolBatchCard]:
        """Convert a standalone tool card to a batch and add a second tool.

        This is called when a second consecutive MCP tool from the same server arrives.
        It removes the original standalone ToolCallCard and creates a ToolBatchCard
        containing both tools.

        Args:
            pending_tool_id: ID of the existing standalone tool to convert
            new_tool_data: The second tool's data
            batch_id: ID for the new batch
            server_name: MCP server name
            round_number: Round number for CSS visibility

        Returns:
            The created ToolBatchCard, or None if conversion failed
        """
        from datetime import datetime

        # Get the existing tool card
        existing_card = self._tools.get(pending_tool_id)
        if not existing_card:
            return None

        # Extract data from existing card to create batch item
        first_item = ToolBatchItem(
            tool_id=pending_tool_id,
            tool_name=existing_card.tool_name,
            display_name=get_mcp_tool_name(existing_card.tool_name) or existing_card._display_name,
            status=existing_card.status,
            args_summary=existing_card._params,
            args_full=existing_card._params_full,
            result_summary=existing_card._result,
            result_full=existing_card._result_full,
            start_time=existing_card._start_time,
        )

        # Create second item from new tool data
        second_item = ToolBatchItem(
            tool_id=new_tool_data.tool_id,
            tool_name=new_tool_data.tool_name,
            display_name=get_mcp_tool_name(new_tool_data.tool_name) or new_tool_data.tool_name,
            status=new_tool_data.status,
            args_summary=new_tool_data.args_summary,
            args_full=new_tool_data.args_full,
            start_time=new_tool_data.start_time or datetime.now(),
        )

        # Create batch card
        batch_card = ToolBatchCard(
            server_name=server_name,
            id=f"batch_{batch_id}",
        )

        # Tag with round class for CSS visibility
        batch_card.add_class(f"round-{round_number}")
        if round_number != self._viewed_round:
            batch_card.add_class("hidden")

        # Add both tools to batch
        batch_card.add_tool(first_item)
        batch_card.add_tool(second_item)

        # Track in our dictionaries
        self._batches[batch_id] = batch_card
        self._tool_to_batch[pending_tool_id] = batch_id
        self._tool_to_batch[new_tool_data.tool_id] = batch_id

        # Mount batch card right after the existing tool card, then remove the old card
        try:
            container = self.query_one("#timeline_container", TimelineScrollContainer)
            container.mount(batch_card, after=existing_card)
            existing_card.remove()
            del self._tools[pending_tool_id]
            self._auto_scroll()
        except Exception:
            pass

        return batch_card

    def add_hook_to_tool(self, tool_call_id: Optional[str], hook_info: dict) -> None:
        """Add hook execution info to a tool card.

        Args:
            tool_call_id: The tool call ID to attach the hook to
            hook_info: Hook execution information dict with keys:
                - hook_name: Name of the hook
                - hook_type: "pre" or "post"
                - decision: "allow", "deny", or "error"
                - reason: Optional reason string
                - execution_time_ms: Optional execution time
                - injection_preview: Optional preview of injected content
                - injection_content: Optional full injection content
        """
        from massgen.logger_config import logger

        # Find the tool card to attach the hook to
        tool_card = None
        if tool_call_id:
            tool_card = self._tools.get(tool_call_id)

        # If no specific tool_id, attach to the most recent tool
        if not tool_card and self._tools:
            # Get the most recently added tool
            tool_card = list(self._tools.values())[-1] if self._tools else None

        hook_name = hook_info.get("hook_name", "unknown")
        has_content = bool(hook_info.get("injection_content"))
        logger.info(
            f"[TimelineSection] add_hook_to_tool: tool_call_id={tool_call_id}, "
            f"hook={hook_name}, has_content={has_content}, tool_found={tool_card is not None}, "
            f"known_tools={list(self._tools.keys())}",
        )

        if tool_card:
            hook_type = hook_info.get("hook_type", "pre")
            hook_name = hook_info.get("hook_name", "unknown")
            decision = hook_info.get("decision", "allow")
            reason = hook_info.get("reason")
            injection_preview = hook_info.get("injection_preview")
            injection_content = hook_info.get("injection_content")
            execution_time_ms = hook_info.get("execution_time_ms")

            if hook_type == "pre":
                tool_card.add_pre_hook(
                    hook_name=hook_name,
                    decision=decision,
                    reason=reason,
                    execution_time_ms=execution_time_ms,
                    injection_content=injection_content,
                )
            else:
                tool_card.add_post_hook(
                    hook_name=hook_name,
                    injection_preview=injection_preview,
                    execution_time_ms=execution_time_ms,
                    injection_content=injection_content,
                )

    def add_text(self, content: str, style: str = "", text_class: str = "", round_number: int = 1) -> None:
        """Add text content to the timeline.

        Args:
            content: Text content
            style: Rich style string
            text_class: CSS class (status, thinking, response)
            round_number: The round this content belongs to (for view switching)
        """
        # Clean up excessive whitespace - collapse multiple newlines to single
        import re

        content = re.sub(r"\n{3,}", "\n\n", content)  # Max 2 consecutive newlines
        content = content.strip()

        if not content:
            return

        self._item_count += 1
        widget_id = f"tl_text_{self._item_count}"

        try:
            container = self.query_one("#timeline_container", TimelineScrollContainer)

            classes = "timeline-text"
            if text_class:
                classes += f" {text_class}"

            if style:
                widget = Static(
                    Text(content, style=style),
                    id=widget_id,
                    classes=classes,
                )
            else:
                widget = Static(content, id=widget_id, classes=classes)

            # Phase 12: Tag with round class for CSS visibility switching
            widget.add_class(f"round-{round_number}")
            # Hide if viewing a different round
            if round_number != self._viewed_round:
                widget.add_class("hidden")

            container.mount(widget)
            self._auto_scroll()
            self._trim_old_items()  # Keep timeline size bounded
        except Exception:
            pass

    def add_separator(self, label: str = "", round_number: int = 1, subtitle: str = "") -> None:
        """Add a visual separator to the timeline.

        Args:
            label: Optional label for the separator
            round_number: The round this content belongs to (for view switching)
            subtitle: Optional subtitle (e.g., "Restart • Context cleared")
        """
        from massgen.logger_config import logger

        self._item_count += 1
        widget_id = f"tl_sep_{self._item_count}"

        logger.debug(
            f"TimelineSection.add_separator: label='{label}', round={round_number}, " f"viewed_round={self._viewed_round}, widget_id={widget_id}",
        )

        try:
            container = self.query_one("#timeline_container", TimelineScrollContainer)

            # Check if this is a round/restart/final separator (should be prominent)
            is_round = label.upper().startswith("ROUND") if label else False
            is_restart = "RESTART" in label.upper() if label else False
            is_final = "FINAL" in label.upper() if label else False

            if is_round or is_restart or is_final:
                # Create prominent round/restart/final banner
                widget = RestartBanner(label=label, subtitle=subtitle, id=widget_id)
                logger.debug(f"TimelineSection.add_separator: Created RestartBanner for '{label}' subtitle='{subtitle}'")
            else:
                # Regular separator
                sep_text = Text()
                sep_text.append("─" * 50, style="dim")
                if label:
                    sep_text.append(f" {label} ", style="dim italic")
                    sep_text.append("─" * 10, style="dim")
                widget = Static(sep_text, id=widget_id)

            # Phase 12: Tag with round class for CSS visibility switching
            widget.add_class(f"round-{round_number}")
            # Hide if viewing a different round
            if round_number != self._viewed_round:
                widget.add_class("hidden")
                logger.debug(f"TimelineSection.add_separator: Hiding widget (round {round_number} != viewed {self._viewed_round})")
            else:
                logger.debug(f"TimelineSection.add_separator: Widget visible (round {round_number} == viewed {self._viewed_round})")

            container.mount(widget)
            self._auto_scroll()
            self._trim_old_items()  # Keep timeline size bounded
            logger.debug(f"TimelineSection.add_separator: Successfully mounted {widget_id}")
        except Exception as e:
            # Log the error but don't crash
            logger.error(f"TimelineSection.add_separator failed: {e}")

    def add_reasoning(self, content: str, round_number: int = 1) -> None:
        """Add coordination/reasoning content inline with subtle styling.

        Args:
            content: Reasoning/voting/coordination text
            round_number: The round this content belongs to (for view switching)
        """
        if not content.strip():
            return

        self._item_count += 1
        widget_id = f"tl_reasoning_{self._item_count}"

        try:
            container = self.query_one("#timeline_container", TimelineScrollContainer)
            # Subtle inline styling - dim italic with thinking emoji
            widget = Static(
                Text(f"💭 {content}", style="dim italic #8b949e"),
                id=widget_id,
                classes="timeline-text thinking-inline",
            )
            # Phase 12: Tag with round class for CSS visibility switching
            widget.add_class(f"round-{round_number}")
            # Hide if viewing a different round
            if round_number != self._viewed_round:
                widget.add_class("hidden")
            container.mount(widget)
            self._auto_scroll()
        except Exception:
            pass

    def add_widget(self, widget, round_number: int = 1) -> None:
        """Add a generic widget to the timeline.

        Args:
            widget: Any Textual widget to add to the timeline
            round_number: The round this content belongs to (for view switching)
        """
        self._item_count += 1

        # Phase 12: Tag with round class for CSS visibility switching
        widget.add_class(f"round-{round_number}")
        # Hide if viewing a different round
        if round_number != self._viewed_round:
            widget.add_class("hidden")

        try:
            container = self.query_one("#timeline_container", TimelineScrollContainer)
            container.mount(widget)
            self._auto_scroll()
        except Exception as e:
            import sys

            print(f"[ERROR] add_widget failed: {e}", file=sys.stderr)

    def clear(self) -> None:
        """Clear all timeline content."""
        try:
            container = self.query_one("#timeline_container", TimelineScrollContainer)
            container.remove_children()
        except Exception:
            pass
        self._tools.clear()
        self._item_count = 0

    def clear_tools_tracking(self) -> None:
        """Clear just the tools tracking dict without removing UI elements.

        Used when a round completes to reset background tool counts while
        keeping the visual timeline history intact.
        """
        self._tools.clear()

    def set_viewed_round(self, round_number: int) -> None:
        """Update which round is currently being viewed.

        Phase 12: Called when a new round starts to track the active round.
        New content will use this round number for visibility tagging.

        Args:
            round_number: The round number being viewed
        """
        self._viewed_round = round_number

    def switch_to_round(self, round_number: int) -> None:
        """Switch visibility to show only the specified round.

        Phase 12: CSS-based visibility switching. All round content stays in DOM,
        we just toggle the 'hidden' class based on round tags.

        Args:
            round_number: The round number to display
        """
        from massgen.logger_config import logger

        self._viewed_round = round_number

        logger.debug(f"TimelineSection.switch_to_round: switching to round {round_number}")

        # Debug logging - include widget ID to identify which panel
        widget_id = self.id or "unknown"
        with open("/tmp/tui_debug.log", "a") as f:
            f.write(f"DEBUG: TimelineSection.switch_to_round called! panel={widget_id}, round={round_number}\n")

        try:
            container = self.query_one("#timeline_container", TimelineScrollContainer)

            # Query ALL descendants (not just direct children) to handle nested widgets
            # like tool cards that have nested content
            widgets_found = 0
            widgets_hidden = 0
            widgets_shown = 0

            for widget in container.query("*"):
                # Check if widget has any round class
                round_classes = [c for c in widget.classes if c.startswith("round-")]
                if round_classes:
                    widgets_found += 1
                    # Widget is tagged with a round - show/hide based on match
                    if f"round-{round_number}" in widget.classes:
                        widget.remove_class("hidden")
                        widgets_shown += 1
                    else:
                        widget.add_class("hidden")
                        widgets_hidden += 1
                # Widgets without round tags (e.g., scroll indicators) stay visible

            with open("/tmp/tui_debug.log", "a") as f:
                f.write(f"DEBUG: TimelineSection.switch_to_round: panel={widget_id}, found={widgets_found}, hidden={widgets_hidden}, shown={widgets_shown}\n")

            # Reset scroll indicators when switching rounds
            # They will be re-shown by the scroll position handler if needed
            try:
                top_indicator = self.query_one("#scroll_top_indicator", Static)
                bottom_indicator = self.query_one("#scroll_bottom_indicator", Static)
                top_indicator.add_class("hidden")
                bottom_indicator.add_class("hidden")
            except Exception:
                pass

            # Scroll to top of new round's content
            container.scroll_home(animate=False)

            logger.debug(f"TimelineSection.switch_to_round: done switching to round {round_number}")
        except Exception as e:
            with open("/tmp/tui_debug.log", "a") as f:
                f.write(f"DEBUG: TimelineSection.switch_to_round ERROR: {e}\n")
            logger.error(f"TimelineSection.switch_to_round error: {e}")


class ThinkingSection(Vertical):
    """Section for streaming thinking/reasoning content.

    Phase 11.1: Now collapsible - auto-collapses when content exceeds threshold.
    Click header to toggle expanded/collapsed state.

    Design (collapsed):
    ```
    ▶ 💭 Reasoning [+12 more lines] ──────────────────────────────────────
    │ First few lines of reasoning visible here...
    ```

    Design (expanded):
    ```
    ▼ 💭 Reasoning ───────────────────────────────────────────────────────
    │ Full reasoning content visible...
    │ Multiple lines of thinking...
    │ ...
    ```
    """

    # Collapse threshold - auto-collapse when exceeding this many lines
    COLLAPSE_THRESHOLD = 5
    # Preview lines to show when collapsed
    PREVIEW_LINES = 3

    is_collapsed = reactive(False)

    DEFAULT_CSS = """
    ThinkingSection {
        height: auto;
        max-height: 50%;
        padding: 0;
        margin: 0 0 1 0;
        border-left: thick #484f58;
        background: #161b22;
    }

    ThinkingSection.hidden {
        display: none;
    }

    ThinkingSection #thinking_header {
        height: 1;
        width: 100%;
        padding: 0 1;
        background: #21262d;
        color: #8b949e;
    }

    ThinkingSection #thinking_header:hover {
        background: #30363d;
        color: #c9d1d9;
    }

    ThinkingSection #thinking_content {
        height: auto;
        max-height: 100%;
        padding: 0 1;
        overflow-y: auto;
    }

    ThinkingSection.collapsed #thinking_content {
        max-height: 3;
        overflow: hidden;
    }

    ThinkingSection #thinking_log {
        height: auto;
        padding: 0;
    }
    """

    def __init__(self, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self._line_count = 0
        self._auto_collapsed = False  # Track if we auto-collapsed
        self.add_class("hidden")  # Start hidden until content arrives

    def compose(self) -> ComposeResult:
        yield Static(self._build_header(), id="thinking_header", classes="section-header")
        yield ScrollableContainer(
            RichLog(id="thinking_log", highlight=False, wrap=True, markup=True),
            id="thinking_content",
        )

    def _build_header(self) -> Text:
        """Build the section header text."""
        text = Text()

        # Collapse indicator
        indicator = "▶" if self.is_collapsed else "▼"
        text.append(f"{indicator} ", style="dim")

        # Icon and title
        text.append("💭 ", style="")
        text.append("Reasoning", style="bold dim")

        # Show hidden line count when collapsed
        if self.is_collapsed and self._line_count > self.PREVIEW_LINES:
            hidden_count = self._line_count - self.PREVIEW_LINES
            text.append(" ─" + "─" * 20 + "─ ", style="dim")
            text.append(f"[+{hidden_count} more lines]", style="dim cyan")

        return text

    def watch_is_collapsed(self, collapsed: bool) -> None:
        """Update UI when collapse state changes."""
        if collapsed:
            self.add_class("collapsed")
        else:
            self.remove_class("collapsed")

        # Update header
        try:
            header = self.query_one("#thinking_header", Static)
            header.update(self._build_header())
        except Exception:
            pass

    def on_click(self, event) -> None:
        """Toggle collapsed state on header click."""
        try:
            header = self.query_one("#thinking_header", Static)
            # Check if click was on header area
            if event.widget == header or (hasattr(event, "widget") and event.widget.id == "thinking_header"):
                self.is_collapsed = not self.is_collapsed
        except Exception:
            pass

    def append(self, content: str, style: str = "") -> None:
        """Append content to the thinking log.

        Args:
            content: Text content to append
            style: Optional Rich style string
        """
        try:
            # Show section when content arrives
            self.remove_class("hidden")

            log = self.query_one("#thinking_log", RichLog)
            if style:
                log.write(Text(content, style=style))
            else:
                log.write(content)
            self._line_count += 1

            # Auto-collapse when exceeding threshold (only once)
            if not self._auto_collapsed and self._line_count > self.COLLAPSE_THRESHOLD:
                self._auto_collapsed = True
                self.is_collapsed = True

            # Update header to show line count
            try:
                header = self.query_one("#thinking_header", Static)
                header.update(self._build_header())
            except Exception:
                pass

        except Exception:
            pass

    def append_text(self, text: Text) -> None:
        """Append a Rich Text object.

        Args:
            text: Pre-styled Rich Text
        """
        try:
            # Show section when content arrives
            self.remove_class("hidden")

            log = self.query_one("#thinking_log", RichLog)
            log.write(text)
            self._line_count += 1

            # Auto-collapse when exceeding threshold (only once)
            if not self._auto_collapsed and self._line_count > self.COLLAPSE_THRESHOLD:
                self._auto_collapsed = True
                self.is_collapsed = True

            # Update header to show line count
            try:
                header = self.query_one("#thinking_header", Static)
                header.update(self._build_header())
            except Exception:
                pass

        except Exception:
            pass

    def clear(self) -> None:
        """Clear the thinking log."""
        try:
            log = self.query_one("#thinking_log", RichLog)
            log.clear()
            self._line_count = 0
            self._auto_collapsed = False
            self.is_collapsed = False
            self.add_class("hidden")
        except Exception:
            pass

    @property
    def line_count(self) -> int:
        """Get the number of lines written."""
        return self._line_count

    def expand(self) -> None:
        """Expand the section (show all content)."""
        self.is_collapsed = False

    def collapse(self) -> None:
        """Collapse the section (show preview only)."""
        self.is_collapsed = True


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

    def __init__(
        self,
        initial_status: str = "waiting",
        id: Optional[str] = None,
    ) -> None:
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


class RestartBanner(Static):
    """Subtle, professional restart separator banner.

    Design - understated gradient style:
    ```
    ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
                        ⟳ Round 1 Complete
    ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
    ```
    """

    DEFAULT_CSS = """
    RestartBanner {
        width: 100%;
        height: 1;
        margin: 1 0;
        padding: 0;
        background: transparent;
    }

    RestartBanner.hidden {
        display: none;
    }
    """

    def __init__(self, label: str = "", subtitle: str = "", id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self._label = label
        self._subtitle = subtitle

    def render(self) -> Text:
        """Render a clean, inline separator with centered label."""
        import re

        text = Text()

        # Clean up the label - extract meaningful info
        display_label = self._label
        is_final = "FINAL" in display_label.upper()

        if is_final:
            # Final Presentation - prominent green styling
            display_label = "🏆 Final Presentation"
            label_color = "#4ade80"  # Green for success
            line_color = "#22c55e"  # Green for lines
        elif "RESTART" in display_label.upper():
            # Extract round number for restart
            match = re.search(r"ROUND\s*(\d+)", display_label, re.IGNORECASE)
            if match:
                round_num = match.group(1)
                display_label = f"Round {round_num}"
            else:
                display_label = "New Round"
            label_color = "#9ca3af"  # Muted gray
            line_color = "#4b5563"  # Dim gray
        elif display_label.upper().startswith("ROUND"):
            # Simple "Round X" label
            match = re.search(r"ROUND\s*(\d+)", display_label, re.IGNORECASE)
            if match:
                round_num = match.group(1)
                display_label = f"Round {round_num}"
            label_color = "#9ca3af"  # Muted gray
            line_color = "#4b5563"  # Dim gray
        else:
            label_color = "#9ca3af"  # Muted gray
            line_color = "#4b5563"  # Dim gray

        # Single-line inline separator: ──── ▸ Round 1 ────────────────
        line_char = "─"
        total_width = 70
        label_with_arrow = f" ▸ {display_label} "
        label_len = len(label_with_arrow)

        # Calculate line lengths (left shorter, right fills remaining)
        left_len = 4
        right_len = max(4, total_width - left_len - label_len)

        text.append(line_char * left_len, style=f"dim {line_color}")
        text.append(label_with_arrow, style=label_color)
        text.append(line_char * right_len, style=f"dim {line_color}")

        return text


class FinalPresentationCard(Vertical):
    """Unified card widget for displaying the final answer presentation.

    Shows a header with trophy icon, vote summary, streaming content area,
    collapsible post-evaluation section, action buttons (Copy/Workspace), and continue message.

    Design:
    ```
    ┌─ 🏆 FINAL ANSWER ─────────────────────────────────────────────────┐
    │  Winner: Agent A (2 votes)  |  Votes: A(2), B(1)                  │
    ├───────────────────────────────────────────────────────────────────┤
    │  [Final answer content with markdown rendering...]                │
    │                                                                   │
    ├───────────────────────────────────────────────────────────────────┤
    │  ✓ Verified by Post-Evaluation                    [▾ Show Details]│
    │  [Collapsible evaluation content...]                              │
    ├───────────────────────────────────────────────────────────────────┤
    │  [📋 Copy]  [📂 Workspace]                                        │
    │  💬 Type below to continue the conversation                       │
    └───────────────────────────────────────────────────────────────────┘
    ```
    """

    DEFAULT_CSS = """
    FinalPresentationCard {
        width: 100%;
        height: auto;
        margin: 1 0;
        padding: 0;
        border: solid #ffd700;
        background: #1a1a1a;
    }

    FinalPresentationCard.streaming {
        border: double #ffd700;
    }

    FinalPresentationCard.completed {
        border: solid #3fb950;
        background: #0d1f14;
    }

    FinalPresentationCard #final_card_header {
        width: 100%;
        height: auto;
        padding: 0 1;
        background: #2d2510;
        border-bottom: solid #ffd700 50%;
    }

    FinalPresentationCard.completed #final_card_header {
        background: #1a4d2e;
        border-bottom: solid #3fb950 50%;
    }

    FinalPresentationCard #final_card_title {
        color: #ffd700;
        text-style: bold;
    }

    FinalPresentationCard.completed #final_card_title {
        color: #3fb950;
    }

    FinalPresentationCard #final_card_votes {
        color: #8b949e;
        height: 1;
    }

    FinalPresentationCard #final_card_content {
        width: 100%;
        height: auto;
        min-height: 5;
        max-height: 25;
        padding: 1 2;
        background: #1e1e1e;
        overflow-y: auto;
    }

    FinalPresentationCard #final_card_text {
        width: 100%;
        height: auto;
        min-height: 3;
        background: #1e1e1e;
        color: #e6e6e6;
    }

    FinalPresentationCard #final_card_post_eval {
        width: 100%;
        height: auto;
        padding: 0;
        background: #161b22;
        border-top: dashed #30363d;
    }

    FinalPresentationCard #final_card_post_eval.hidden {
        display: none;
    }

    FinalPresentationCard #post_eval_header {
        width: 100%;
        height: 2;
        padding: 0 2;
        background: #161b22;
    }

    FinalPresentationCard #post_eval_status {
        color: #3fb950;
        width: auto;
    }

    FinalPresentationCard #post_eval_status.evaluating {
        color: #58a6ff;
    }

    FinalPresentationCard #post_eval_toggle {
        color: #8b949e;
        width: auto;
        text-align: right;
        margin-left: 1;
    }

    FinalPresentationCard #post_eval_toggle:hover {
        color: #c9d1d9;
        text-style: underline;
    }

    FinalPresentationCard #post_eval_details {
        width: 100%;
        height: auto;
        max-height: 10;
        padding: 0 2 1 2;
        overflow-y: auto;
    }

    FinalPresentationCard #post_eval_details.collapsed {
        display: none;
    }

    FinalPresentationCard #post_eval_content {
        color: #8b949e;
        height: auto;
    }

    FinalPresentationCard #final_card_footer {
        width: 100%;
        height: auto;
        padding: 1 2;
        background: #21262d;
        border-top: solid #30363d;
    }

    FinalPresentationCard #final_card_footer.hidden {
        display: none;
    }

    FinalPresentationCard #final_card_buttons {
        width: 100%;
        height: 3;
    }

    FinalPresentationCard #final_card_buttons Button {
        margin-right: 1;
        min-width: 12;
    }

    FinalPresentationCard #final_card_copy_btn {
        background: #238636;
        color: #ffffff;
    }

    FinalPresentationCard #final_card_copy_btn:hover {
        background: #2ea043;
    }

    FinalPresentationCard #continue_message {
        color: #58a6ff;
        text-style: italic;
        height: 1;
        margin-top: 1;
    }
    """

    def __init__(
        self,
        agent_id: str,
        model_name: str = "",
        vote_results: Optional[Dict] = None,
        id: Optional[str] = None,
    ) -> None:
        super().__init__(id=id or "final_presentation_card")
        self.agent_id = agent_id
        self.model_name = model_name
        self.vote_results = vote_results or {}
        self._final_content: list = []
        self._post_eval_content: list = []
        self._is_streaming = True
        self._post_eval_expanded = False
        self._post_eval_status = "none"  # none, evaluating, verified
        self.add_class("streaming")

    def compose(self) -> ComposeResult:
        from textual.containers import Horizontal, ScrollableContainer
        from textual.widgets import Button, Label

        # Header section
        with Vertical(id="final_card_header"):
            yield Label(self._build_title(), id="final_card_title")
            yield Label(self._build_vote_summary(), id="final_card_votes")

        # Content section with Static text (scrollable)
        with ScrollableContainer(id="final_card_content"):
            yield Static("", id="final_card_text", markup=True)

        # Post-evaluation section (hidden until post-eval content arrives)
        with Vertical(id="final_card_post_eval", classes="hidden"):
            with Horizontal(id="post_eval_header"):
                yield Label("🔍 Evaluating...", id="post_eval_status", classes="evaluating")
                yield Label("", id="post_eval_toggle")
            with ScrollableContainer(id="post_eval_details", classes="collapsed"):
                yield Static("", id="post_eval_content")

        # Footer with buttons and continue message (hidden until complete)
        with Vertical(id="final_card_footer", classes="hidden"):
            with Horizontal(id="final_card_buttons"):
                yield Button("📋 Copy", id="final_card_copy_btn")
                yield Button("📂 Workspace", id="final_card_workspace_btn")
            yield Label("💬 Type below to continue the conversation", id="continue_message")

    def _build_title(self) -> str:
        """Build the title with trophy icon."""
        return "🏆 FINAL ANSWER"

    def _build_vote_summary(self) -> str:
        """Build the vote summary line."""
        if not self.vote_results:
            return ""

        vote_counts = self.vote_results.get("vote_counts", {})
        winner = self.vote_results.get("winner", "")
        is_tie = self.vote_results.get("is_tie", False)

        if not vote_counts:
            return ""

        # Format: "Winner: agent_a (2v) | Votes: agent_a(2), agent_b(1)"
        winner_count = vote_counts.get(winner, 0)
        tie_note = " (tie-breaker)" if is_tie else ""
        counts_str = ", ".join(f"{aid}({count})" for aid, count in vote_counts.items())

        return f"Winner: {winner} ({winner_count}v){tie_note} | Votes: {counts_str}"

    def append_chunk(self, chunk: str) -> None:
        """Append streaming content to the card.

        Args:
            chunk: Text chunk to append
        """
        if not chunk:
            return

        try:
            text_widget = self.query_one("#final_card_text", Static)

            # Accumulate content
            self._final_content.append(chunk)

            # Update the Static widget with all accumulated content
            full_text = "".join(self._final_content)
            text_widget.update(full_text)

            # Auto-scroll to show latest content
            try:
                content = self.query_one("#final_card_content", ScrollableContainer)
                content.scroll_end(animate=False)
            except Exception:
                pass

        except Exception as e:
            logger.error(f"FinalPresentationCard.append_chunk error: {e}")

    def complete(self) -> None:
        """Mark the presentation as complete and show action buttons."""
        from textual.widgets import Label

        self._is_streaming = False

        # Update styling
        self.remove_class("streaming")
        self.add_class("completed")

        # Update title to show completed
        try:
            title = self.query_one("#final_card_title", Label)
            title.update("✅ FINAL ANSWER")
        except Exception:
            pass

        # Show footer with buttons and continue message
        try:
            footer = self.query_one("#final_card_footer")
            footer.remove_class("hidden")
        except Exception:
            pass

    def get_content(self) -> str:
        """Get the full content for copy operation."""
        # Join chunks directly since they may already contain newlines
        return "".join(self._final_content)

    def on_click(self, event) -> None:
        """Handle clicks on the post-eval toggle."""
        from textual.widgets import Label

        # Check if click was on the toggle label
        try:
            toggle = self.query_one("#post_eval_toggle", Label)
            if toggle.region.contains(event.x, event.y):
                self._toggle_post_eval_details()
        except Exception:
            pass

    def _toggle_post_eval_details(self) -> None:
        """Toggle the post-evaluation details visibility."""
        from textual.containers import ScrollableContainer
        from textual.widgets import Label

        try:
            details = self.query_one("#post_eval_details", ScrollableContainer)
            toggle = self.query_one("#post_eval_toggle", Label)

            if self._post_eval_expanded:
                details.add_class("collapsed")
                toggle.update("▸ Show Details")
                self._post_eval_expanded = False
            else:
                details.remove_class("collapsed")
                toggle.update("▾ Hide Details")
                self._post_eval_expanded = True
        except Exception:
            pass

    def on_button_pressed(self, event) -> None:
        """Handle button presses."""
        from textual.widgets import Button

        if not isinstance(event, Button.Pressed):
            return

        if event.button.id == "final_card_copy_btn":
            self._copy_to_clipboard()
        elif event.button.id == "final_card_workspace_btn":
            self._open_workspace()

    def _copy_to_clipboard(self) -> None:
        """Copy final answer to system clipboard."""
        import platform
        import subprocess

        full_content = self.get_content()
        try:
            system = platform.system()
            if system == "Darwin":
                process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                process.communicate(full_content.encode("utf-8"))
            elif system == "Windows":
                process = subprocess.Popen(["clip"], stdin=subprocess.PIPE, shell=True)
                process.communicate(full_content.encode("utf-8"))
            else:
                process = subprocess.Popen(
                    ["xclip", "-selection", "clipboard"],
                    stdin=subprocess.PIPE,
                )
                process.communicate(full_content.encode("utf-8"))
            self.app.notify(
                f"Copied {len(self._final_content)} lines to clipboard",
                severity="information",
            )
        except Exception as e:
            self.app.notify(f"Failed to copy: {e}", severity="error")

    def _open_workspace(self) -> None:
        """Open workspace browser for the winning agent."""
        try:
            app = self.app
            if hasattr(app, "_show_workspace_browser_for_agent"):
                app._show_workspace_browser_for_agent(self.agent_id)
            else:
                self.app.notify("Workspace browser not available", severity="warning")
        except Exception as e:
            self.app.notify(f"Failed to open workspace: {e}", severity="error")

    def set_post_eval_status(self, status: str, content: str = "") -> None:
        """Set the post-evaluation status and optionally add content.

        Args:
            status: One of "evaluating", "verified", "restart"
            content: Optional content to display in the details section
        """
        from textual.widgets import Label

        self._post_eval_status = status

        try:
            # Show the post-eval section
            post_eval_section = self.query_one("#final_card_post_eval")
            post_eval_section.remove_class("hidden")

            # Update status label
            status_label = self.query_one("#post_eval_status", Label)
            toggle_label = self.query_one("#post_eval_toggle", Label)

            if status == "evaluating":
                status_label.update("🔍 Evaluating...")
                status_label.add_class("evaluating")
                toggle_label.update("")
            elif status == "verified":
                status_label.update("✓ Verified by Post-Evaluation")
                status_label.remove_class("evaluating")
                if self._post_eval_content:
                    toggle_label.update("▸ Show Details")
            elif status == "restart":
                status_label.update("🔄 Restart Requested")
                status_label.remove_class("evaluating")
                if self._post_eval_content:
                    toggle_label.update("▸ Show Details")

            # Add content if provided
            if content and content.strip():
                self._post_eval_content.append(content)
                post_eval_static = self.query_one("#post_eval_content", Static)
                full_content = "\n".join(self._post_eval_content)
                post_eval_static.update(full_content)

        except Exception:
            pass

    def add_post_evaluation(self, content: str) -> None:
        """Add post-evaluation content to the card (legacy method).

        Args:
            content: The post-evaluation text to display
        """
        if not content.strip():
            return

        # If status not set, set to evaluating
        if self._post_eval_status == "none":
            self.set_post_eval_status("evaluating", content)
        else:
            self.set_post_eval_status(self._post_eval_status, content)

    def get_post_evaluation_content(self) -> str:
        """Get the full post-evaluation content."""
        return "\n".join(self._post_eval_content)
