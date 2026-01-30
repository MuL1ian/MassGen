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
import time
from typing import Dict, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.widgets import RichLog, Static

from ..content_handlers import ToolDisplayData, get_mcp_tool_name
from .collapsible_text_card import CollapsibleTextCard
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


class TimelineSection(ScrollableContainer):
    """Chronological timeline showing tools and text interleaved.

    This widget displays content in the order it arrives, preserving
    the natural flow of agent activity. Tool cards and text blocks
    appear inline as they occur.

    Coordination/reasoning content is grouped into a collapsible
    ReasoningSection at the top of the timeline.

    Note: TimelineSection inherits from ScrollableContainer directly,
    eliminating the nested container architecture that caused scrollbar
    thumb position sync issues. All content is mounted directly into
    this widget.

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
        padding: 0 2 1 2;
        margin: 0;
        overflow-y: auto;
        scrollbar-size: 1 3;
        scrollbar-gutter: stable;
    }

    TimelineSection .timeline-text {
        width: 100%;
        padding: 1 1;
        margin: 1 0;
    }

    TimelineSection .timeline-text.status {
        color: #569cd6;
    }

    TimelineSection .timeline-text.thinking {
        color: #9ca3af;
    }

    TimelineSection .timeline-text.response {
        color: #4ec9b0;
    }

    TimelineSection .timeline-text.coordination {
        color: #858585;
        background: $surface-darken-1;
        /* Inherit base padding/margin for consistency */
    }

    TimelineSection .timeline-text.reasoning-inline {
        color: #8b949e;
        border-left: thick #484f58;
        padding-left: 1;
        /* Inherit base margin (1 0) for consistent spacing */
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

    /* Answer lock mode: final card fills the space */
    TimelineSection.answer-locked {
        overflow-y: hidden;
        padding: 0;
    }

    /* Hidden class for non-locked items */
    TimelineSection .answer-lock-hidden {
        display: none;
    }

    /* ARCH-001: Viewport culling - hide items outside visible area */
    TimelineSection .viewport-culled {
        display: none;
    }

    /* Locked final card fills available space */
    TimelineSection .final-card-locked {
        height: 1fr;
        margin: 0;
    }
    """

    # Maximum number of items to keep in timeline (prevents memory/performance issues)
    MAX_TIMELINE_ITEMS = 30  # Viewport culling threshold
    SCROLL_DEBOUNCE_MS = 25  # Minimum gap between scroll operations (reduced for responsiveness)
    SCROLL_ANIMATION_THRESHOLD_MS = 300  # Threshold for animation vs instant scroll

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
        # Removed widgets cache for scroll-back (widget ID -> widget)
        self._removed_widgets: Dict[str, any] = {}
        self._truncation_shown = False  # Track if we've shown truncation message
        # Phase 12: View-based round navigation
        self._viewed_round: int = 1  # Which round is currently being displayed
        # Content batch: accumulates consecutive thinking/content into single card
        self._current_reasoning_card: Optional[CollapsibleTextCard] = None
        self._current_batch_label: Optional[str] = None  # Track label for batch switching
        # Scroll detection flags (moved from TimelineScrollContainer)
        self._user_scrolled_up = False
        self._auto_scrolling = False
        self._scroll_pending = False
        self._debug_scroll = True  # Debug flag (enabled for debugging compression)
        # Performance: Time-based scroll debouncing (QUICK-002)
        self._last_scroll_time: float = 0.0
        # Performance: Cancel previous timer before creating new one (QUICK-004)
        self._scroll_timer = None
        # Deferred scroll pattern: ensures scroll happens even when debounced
        self._scroll_requested = False
        self._debounce_timer = None
        # Answer lock mode: when True, timeline shows only the final answer card
        self._answer_lock_mode = False
        self._locked_card_id: Optional[str] = None
        # Track if Round 1 banner has been shown
        self._round_1_shown = False

    def compose(self) -> ComposeResult:
        # Scroll mode indicator (hidden by default)
        yield Static("", id="scroll_mode_indicator", classes="scroll-indicator hidden")
        # Content is mounted directly into TimelineSection (no nested container)

    def _ensure_round_1_shown(self) -> None:
        """Ensure Round 1 banner is shown before any content."""
        if not self._round_1_shown:
            self._round_1_shown = True
            self.add_separator("Round 1", round_number=1)

    def _log(self, msg: str) -> None:
        """Debug logging helper."""
        if self._debug_scroll:
            from datetime import datetime

            with open("/tmp/scroll_debug.log", "a") as f:
                f.write(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}\n")

    def watch_scroll_y(self, old_value: float, new_value: float) -> None:
        """Detect when user scrolls away from bottom.

        IMPORTANT: Must call super() to update the scrollbar position!
        """
        # Call parent's watch_scroll_y to update scrollbar position
        super().watch_scroll_y(old_value, new_value)

        self._log(f"watch_scroll_y: scroll_y={new_value:.1f} max={self.max_scroll_y:.1f} auto={self._auto_scrolling}")

        if self._auto_scrolling:
            return  # Ignore programmatic scrolls

        # Don't trigger scroll mode if there's no scrollable content yet
        if self.max_scroll_y <= 0:
            return

        # Check if at bottom (with tolerance for float precision)
        at_bottom = new_value >= self.max_scroll_y - 2

        if new_value < old_value and not at_bottom:
            # User scrolled up - enter scroll mode
            if not self._user_scrolled_up:
                self._user_scrolled_up = True
                if not self._scroll_mode:
                    self._scroll_mode = True
                    self._new_content_count = 0
                    self._update_scroll_indicator()
        elif at_bottom and self._user_scrolled_up:
            # User scrolled to bottom - exit scroll mode
            self._user_scrolled_up = False
            if self._scroll_mode:
                self._scroll_mode = False
                self._new_content_count = 0
                self._update_scroll_indicator()

    def refresh_scrollbar(self) -> None:
        """Force refresh of the vertical scrollbar.

        Call this after mounting content to ensure the scrollbar
        position indicator reflects the new content size and scroll position.
        Textual automatically syncs scrollbar position from scroll_y.
        """
        try:
            vscroll = self.vertical_scrollbar
            if vscroll:
                vscroll.refresh()
                self._log(f"refresh_scrollbar: scroll_y={self.scroll_y:.1f} max={self.max_scroll_y:.1f}")
        except Exception as e:
            self._log(f"refresh_scrollbar error: {e}")

    def _reset_auto_scroll(self) -> None:
        """Reset auto-scrolling flag after scroll completes."""
        self._log(f"_reset_auto_scroll: scroll_y={self.scroll_y:.1f}")
        self._auto_scrolling = False

    def reset_scroll_mode(self) -> None:
        """Reset scroll mode tracking state."""
        self._user_scrolled_up = False

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
        self._log(f"[AUTO_SCROLL] Called: scroll_mode={self._scroll_mode}, max_scroll_y={self.max_scroll_y:.2f}, scroll_y={self.scroll_y:.2f}")
        if self._scroll_mode:
            self._new_content_count += 1
            self._update_scroll_indicator()  # Update to show new content count
            return
        # Use smooth animated scrolling for better UX
        self._scroll_to_end(animate=True)

    def _scroll_to_end(self, animate: bool = True, duration: float = 0.15, force: bool = False) -> None:
        """Auto-scroll to end with smooth animation.

        Uses a deferred scroll pattern: if called during debounce window,
        marks that scroll is needed and ensures it happens after debounce.

        Args:
            animate: Whether to animate the scroll (default True for smooth UX)
            duration: Animation duration in seconds (default 0.15s)
            force: If True, bypass debounce (e.g., when switching tabs)
        """
        self._log(f"_scroll_to_end called: pending={self._scroll_pending} force={force} max_scroll_y={self.max_scroll_y:.1f} current_scroll_y={self.scroll_y:.1f}")

        current_time = time.monotonic()
        time_since_last = current_time - self._last_scroll_time

        # Force mode bypasses debounce (e.g., explicit user actions like tab switching)
        if not force:
            # If scroll already pending, mark that we need another scroll after
            if self._scroll_pending:
                self._scroll_requested = True
                self._log("_scroll_to_end: marked for deferred scroll (pending)")
                return

            # Time-based debouncing - but DON'T drop the request, defer it
            if time_since_last < (self.SCROLL_DEBOUNCE_MS / 1000.0):
                self._scroll_requested = True
                self._log(f"_scroll_to_end: deferred (debounce: {time_since_last*1000:.1f}ms < {self.SCROLL_DEBOUNCE_MS}ms)")
                # Schedule deferred scroll if not already scheduled
                if self._debounce_timer is None:
                    remaining_ms = self.SCROLL_DEBOUNCE_MS - (time_since_last * 1000)
                    self._debounce_timer = self.set_timer(
                        remaining_ms / 1000.0,
                        self._execute_deferred_scroll,
                    )
                return

        self._scroll_pending = True
        self._scroll_requested = False  # Clear any pending request

        def do_scroll() -> None:
            self._log(f"do_scroll executing: max_scroll_y={self.max_scroll_y:.1f} scroll_y before={self.scroll_y:.1f}")
            self._scroll_pending = False
            self._last_scroll_time = time.monotonic()
            self._auto_scrolling = True

            # Use named constant for animation threshold
            use_animation = animate and self.max_scroll_y > 0 and time_since_last > (self.SCROLL_ANIMATION_THRESHOLD_MS / 1000.0)

            if use_animation:
                self.scroll_to(y=self.max_scroll_y, animate=True, duration=duration, easing="out_cubic")
            else:
                # Fast path: no animation during streaming
                self.scroll_end(animate=False)

            self._log(f"do_scroll after scroll: scroll_y={self.scroll_y:.1f}")

            # QUICK-004: Cancel previous timer before creating new one
            if self._scroll_timer is not None:
                try:
                    self._scroll_timer.stop()
                except Exception:
                    pass  # Timer may have already completed
            self._scroll_timer = self.set_timer(
                duration + 0.1 if use_animation else 0.1,
                self._reset_auto_scroll,
            )

            # Check if another scroll was requested while we were pending
            if self._scroll_requested:
                self._scroll_requested = False
                self.call_after_refresh(lambda: self._scroll_to_end(animate=False))

        # Defer scroll until after layout is complete
        self.call_after_refresh(do_scroll)

    def _execute_deferred_scroll(self) -> None:
        """Execute a deferred scroll after debounce period."""
        self._debounce_timer = None
        if self._scroll_requested:
            self._scroll_requested = False
            self._scroll_to_end(animate=False)

    def exit_scroll_mode(self) -> None:
        """Exit scroll mode and scroll to bottom."""
        self._scroll_mode = False
        self._new_content_count = 0
        self.reset_scroll_mode()  # Reset scroll state
        self._scroll_to_end(animate=False, force=True)
        self._update_scroll_indicator()

    def scroll_to_widget(self, widget_id: str) -> None:
        """Scroll to bring a specific widget to the top of the view.

        Args:
            widget_id: The ID of the widget to scroll to (without #)
        """
        try:
            # Find the widget by ID (content is mounted directly in TimelineSection)
            target = self.query_one(f"#{widget_id}")
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

    @property
    def is_answer_locked(self) -> bool:
        """Whether the timeline is locked to show only the final answer."""
        return self._answer_lock_mode

    def lock_to_final_answer(self, card_id: str) -> None:
        """Lock timeline to show only the final answer card.

        Hides all other timeline content and makes the final card fill
        the available space for better readability.

        Args:
            card_id: The ID of the FinalPresentationCard to lock to
        """
        if self._answer_lock_mode:
            return  # Already locked

        self._answer_lock_mode = True
        self._locked_card_id = card_id

        # Add lock mode class to timeline
        self.add_class("answer-locked")

        # Hide all children except the final card
        for child in self.children:
            child_id = getattr(child, "id", None)
            if child_id != card_id:
                child.add_class("answer-lock-hidden")
            else:
                child.add_class("final-card-locked")

    def unlock_final_answer(self) -> None:
        """Unlock timeline to show all content.

        Restores normal timeline view with all tools and text visible.
        """
        if not self._answer_lock_mode:
            return  # Already unlocked

        self._answer_lock_mode = False

        # Remove lock mode class from timeline
        self.remove_class("answer-locked")

        # Show all children again
        for child in self.children:
            child.remove_class("answer-lock-hidden")
            child.remove_class("final-card-locked")

        self._locked_card_id = None

        # Scroll to show the final card
        self._scroll_to_end(animate=False, force=True)

    def _trim_old_items(self) -> None:
        """ARCH-001: Cull items outside viewport using visibility toggling.

        Instead of removing items from DOM, we hide them with CSS display:none.
        This preserves scroll-back capability and tool state while maintaining
        performance by not rendering hidden items.
        """
        try:
            children = list(self.children)

            # Skip special UI elements
            content_children = [c for c in children if "scroll-indicator" not in c.classes and "truncation-notice" not in c.classes]

            total_items = len(content_children)

            self._log(f"[TRIM] Starting trim: total_items={total_items}, MAX={self.MAX_TIMELINE_ITEMS}, max_scroll_y_before={self.max_scroll_y:.2f}")

            # If under limit, restore any removed items
            if total_items <= self.MAX_TIMELINE_ITEMS:
                # Check if we have removed widgets to restore
                if self._removed_widgets:
                    self._log(f"[TRIM] Under limit, restoring {len(self._removed_widgets)} removed widgets")
                    # Note: Restoring would require preserving original order, which is complex
                    # For now, just clear the cache when we go back under limit
                    # In practice, items rarely go back under the limit
                return

            # Calculate how many to hide
            items_to_hide = total_items - self.MAX_TIMELINE_ITEMS

            if items_to_hide <= 0:
                return

            self._log(f"[TRIM] Hiding {items_to_hide} items (keeping {self.MAX_TIMELINE_ITEMS})")

            # Remove oldest items from DOM (but keep in cache for scroll-back)
            hidden_count = 0
            for child in content_children[:items_to_hide]:
                # Don't hide tool cards that are still running
                if hasattr(child, "tool_id") and child.tool_id in self._tools:
                    tool_card = self._tools.get(child.tool_id)
                    if tool_card and hasattr(tool_card, "_status") and tool_card._status == "running":
                        self._log(f"[TRIM] Skipping running tool: {child.tool_id}")
                        continue

                # Actually remove from DOM to free up space
                # Cache it for potential scroll-back restoration
                if child.id and child in self.children:
                    self._removed_widgets[child.id] = child
                    child.remove()
                    hidden_count += 1

            # Note: We don't need to "show" remaining items since they're already in DOM

            self._log(f"[TRIM] Actually hid {hidden_count} items")

        except Exception as e:
            self._log(f"[TRIM] Exception: {e}")

    def add_tool(self, tool_data: ToolDisplayData, round_number: int = 1) -> ToolCallCard:
        """Add a tool card to the timeline.

        Args:
            tool_data: Tool display data
            round_number: The round this content belongs to (for view switching)

        Returns:
            The created ToolCallCard
        """
        # Ensure Round 1 banner is shown before first content
        self._ensure_round_1_shown()

        # Close any open reasoning batch when tool arrives
        self._close_reasoning_batch()

        card = ToolCallCard(
            tool_name=tool_data.tool_name,
            tool_type=tool_data.tool_type,
            call_id=tool_data.tool_id,
            id=f"tl_card_{tool_data.tool_id}",
        )

        if tool_data.args_summary:
            card.set_params(tool_data.args_summary, tool_data.args_full)

        # Tag with round class for navigation (scroll-to behavior)
        card.add_class(f"round-{round_number}")

        self._tools[tool_data.tool_id] = card
        self._item_count += 1

        try:
            self.mount(card)

            # Defer trim and scroll until after mount completes
            def trim_and_scroll():
                self._trim_old_items()
                self._auto_scroll()

            self.call_after_refresh(trim_and_scroll)
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
        # Ensure Round 1 banner is shown before first content
        self._ensure_round_1_shown()

        card = ToolBatchCard(
            server_name=server_name,
            id=f"batch_{batch_id}",
        )

        # Tag with round class for navigation (scroll-to behavior)
        card.add_class(f"round-{round_number}")

        self._batches[batch_id] = card
        self._item_count += 1

        try:
            self.mount(card)

            # Defer trim and scroll until after mount completes
            def trim_and_scroll():
                self._trim_old_items()
                self._auto_scroll()

            self.call_after_refresh(trim_and_scroll)
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

        # Tag with round class for navigation (scroll-to behavior)
        batch_card.add_class(f"round-{round_number}")

        # Add both tools to batch
        batch_card.add_tool(first_item)
        batch_card.add_tool(second_item)

        # Track in our dictionaries
        self._batches[batch_id] = batch_card
        self._tool_to_batch[pending_tool_id] = batch_id
        self._tool_to_batch[new_tool_data.tool_id] = batch_id

        # Mount batch card right after the existing tool card, then remove the old card
        try:
            self.mount(batch_card, after=existing_card)
            existing_card.remove()
            del self._tools[pending_tool_id]

            # Defer trim and scroll until after mount completes
            def trim_and_scroll():
                self._trim_old_items()
                self._auto_scroll()

            self.call_after_refresh(trim_and_scroll)
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
            text_class: CSS class (status, thinking-inline, content-inline, response)
            round_number: The round this content belongs to (for view switching)
        """
        # Ensure Round 1 banner is shown before first content
        self._ensure_round_1_shown()

        # Clean up excessive newlines only - preserve all spacing
        import re

        content = re.sub(r"\n{3,}", "\n\n", content)  # Max 2 consecutive newlines

        if not content.strip():  # Check if effectively empty
            return

        # Check if this is thinking or content - route to appropriate batching
        is_thinking = "thinking" in text_class
        is_content = "content" in text_class and "content-inline" in text_class

        if is_thinking:
            self.add_reasoning(content, round_number=round_number, label="Thinking")
            return
        elif is_content:
            self.add_reasoning(content, round_number=round_number, label="Content")
            return

        # Other content - close any open batch
        self._close_reasoning_batch()

        self._item_count += 1
        widget_id = f"tl_text_{self._item_count}"

        try:
            classes = "timeline-text"
            if text_class:
                classes += f" {text_class}"

            if style:
                # Short content with explicit style
                widget = Static(
                    Text(content, style=style),
                    id=widget_id,
                    classes=classes,
                )
            else:
                # Short content - simple inline display
                widget = Static(content, id=widget_id, classes=classes)

            # Tag with round class for navigation (scroll-to behavior)
            widget.add_class(f"round-{round_number}")

            self.mount(widget)

            # Defer trim and scroll until after mount completes
            def trim_and_scroll():
                self._trim_old_items()
                self._auto_scroll()

            self.call_after_refresh(trim_and_scroll)
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

        # Close any open reasoning batch
        self._close_reasoning_batch()

        self._item_count += 1
        widget_id = f"tl_sep_{self._item_count}"

        logger.debug(
            f"TimelineSection.add_separator: label='{label}', round={round_number}, " f"viewed_round={self._viewed_round}, widget_id={widget_id}",
        )

        try:
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

            # Tag with round class for navigation (scroll-to behavior)
            widget.add_class(f"round-{round_number}")
            logger.debug(f"TimelineSection.add_separator: Adding widget for round {round_number}")

            self.mount(widget)

            # Defer trim and scroll until after mount completes
            def trim_and_scroll():
                self._trim_old_items()
                self._auto_scroll()

            self.call_after_refresh(trim_and_scroll)
            logger.debug(f"TimelineSection.add_separator: Successfully mounted {widget_id}")
        except Exception as e:
            # Log the error but don't crash
            logger.error(f"TimelineSection.add_separator failed: {e}")

    def _close_reasoning_batch(self) -> None:
        """Close current reasoning batch when non-reasoning content arrives.

        This ends the accumulation of content into a single card, so the next
        content will start a new batch.
        """
        self._current_reasoning_card = None
        self._current_batch_label = None

    def add_reasoning(self, content: str, round_number: int = 1, label: str = "Thinking") -> None:
        """Add thinking/content - accumulates into single collapsible card.

        Consecutive statements with the same label are batched into ONE CollapsibleTextCard.
        The batch closes when:
        - Non-batched content (tools, separators) arrives
        - The label changes (Thinking → Content or vice versa)

        Args:
            content: Text content
            round_number: The round this content belongs to (for view switching)
            label: Label for the card ("Thinking" or "Content")
        """
        if not content.strip():
            return

        # Ensure Round 1 banner is shown before first content
        self._ensure_round_1_shown()

        try:
            # Close batch if label changed
            if self._current_reasoning_card is not None and self._current_batch_label != label:
                self._close_reasoning_batch()

            if self._current_reasoning_card is not None:
                # Append to existing batch
                self._current_reasoning_card.append_content(content)
                # Just scroll for append case (no mount, no trim needed)
                self._auto_scroll()
            else:
                # Start new batch
                self._item_count += 1
                widget_id = f"tl_reasoning_{self._item_count}"

                self._current_reasoning_card = CollapsibleTextCard(
                    content,
                    label=label,
                    id=widget_id,
                    classes="timeline-text thinking-inline",
                )
                self._current_reasoning_card.add_class(f"round-{round_number}")
                self._current_batch_label = label
                self.mount(self._current_reasoning_card)

                # Defer trim and scroll until after mount completes
                def trim_and_scroll():
                    self._trim_old_items()
                    self._auto_scroll()

                self.call_after_refresh(trim_and_scroll)
        except Exception:
            pass

    def add_widget(self, widget, round_number: int = 1) -> None:
        """Add a generic widget to the timeline.

        Args:
            widget: Any Textual widget to add to the timeline
            round_number: The round this content belongs to (for view switching)
        """
        # Ensure Round 1 banner is shown before first content
        self._ensure_round_1_shown()

        self._item_count += 1

        # Tag with round class for navigation (scroll-to behavior)
        widget.add_class(f"round-{round_number}")

        try:
            self.mount(widget)
            self._log(f"Timeline items: {len(list(self.children))}")
            self._trim_old_items()  # Keep timeline size bounded (do before scroll)
            # Defer scroll to ensure trim's layout refresh completes first
            self.call_after_refresh(self._auto_scroll)
        except Exception:
            pass

    def clear(self, add_round_1: bool = True) -> None:
        """Clear all timeline content.

        Args:
            add_round_1: If True, add a "Round 1" separator after clearing (default: True)
        """
        from massgen.logger_config import logger

        logger.info(f"[TimelineSection] clear() called with add_round_1={add_round_1}")

        # Close any open reasoning batch
        self._close_reasoning_batch()

        try:
            # Keep the scroll indicator, remove everything else
            indicator = None
            try:
                indicator = self.query_one("#scroll_mode_indicator", Static)
            except Exception:
                pass
            child_count_before = len(self.children)
            self.remove_children()
            logger.info(f"[TimelineSection] Removed {child_count_before} children")
            if indicator:
                self.mount(indicator)
                logger.info("[TimelineSection] Re-mounted scroll indicator")
        except Exception as e:
            logger.error(f"[TimelineSection] Error during clear: {e}", exc_info=True)
        self._tools.clear()
        self._batches.clear()  # Also clear batch tracking
        self._tool_to_batch.clear()  # Clear tool-to-batch mapping
        self._removed_widgets.clear()  # Clear removed widgets cache
        self._item_count = 0
        logger.info("[TimelineSection] Cleared tracking dicts, reset _item_count to 0")
        # Reset truncation tracking to avoid stale state
        if hasattr(self, "_truncation_shown_rounds"):
            self._truncation_shown_rounds.clear()

        # Reset Round 1 shown flag
        self._round_1_shown = False
        logger.info("[TimelineSection] Set _round_1_shown = False")

        # CRITICAL FIX: Force layout refresh after clearing and defer Round 1 separator
        # This ensures max_scroll_y is recalculated before any new content tries to scroll
        self.refresh()
        self._log(f"[CLEAR] Before call_after_refresh: max_scroll_y={self.max_scroll_y:.2f}")

        # Defer Round 1 separator addition until after layout refresh completes
        if add_round_1:

            def add_round_1_separator():
                self._log(f"[CLEAR] After refresh: max_scroll_y={self.max_scroll_y:.2f}")
                logger.info("[TimelineSection] Adding initial Round 1 separator (from clear)")
                self._round_1_shown = True  # Set flag before adding to avoid re-entry
                self.add_separator("Round 1", round_number=1)
                logger.info("[TimelineSection] Round 1 separator added (from clear)")

            self.call_after_refresh(add_round_1_separator)

    def reset_round_state(self) -> None:
        """Reset round tracking state for a new turn."""
        from massgen.logger_config import logger

        logger.info("[TimelineSection] reset_round_state() called")
        logger.info(f"[TimelineSection] Before reset: _viewed_round={self._viewed_round}, _round_1_shown={self._round_1_shown}")

        self._viewed_round = 1
        # NOTE: Don't reset _round_1_shown here - it's managed by clear() and prepare_for_new_turn()
        # Resetting it here would cause duplicate "Round 1" separators
        # Clear tools/batch tracking to prevent ID collisions
        self._tools.clear()
        self._batches.clear()
        self._tool_to_batch.clear()

        logger.info(f"[TimelineSection] After reset: _viewed_round={self._viewed_round}, _round_1_shown={self._round_1_shown}")

    def clear_tools_tracking(self) -> None:
        """Clear tools and batch tracking dicts without removing UI elements.

        Used when a new round starts to reset tool/batch ID tracking while
        keeping the visual timeline history intact. This prevents tool_id
        and batch_id collisions between rounds.
        """
        self._tools.clear()
        self._batches.clear()
        self._tool_to_batch.clear()

    def set_viewed_round(self, round_number: int) -> None:
        """Update which round is currently being viewed.

        Phase 12: Called when a new round starts to track the active round.
        New content will use this round number for visibility tagging.

        Args:
            round_number: The round number being viewed
        """
        self._viewed_round = round_number

    def switch_to_round(self, round_number: int) -> None:
        """Scroll to the specified round's content.

        All rounds stay visible in a unified timeline. Selecting a round
        smoothly scrolls to that round's separator banner.

        Args:
            round_number: The round number to scroll to
        """
        from massgen.logger_config import logger

        self._viewed_round = round_number

        logger.debug(f"TimelineSection.switch_to_round: scrolling to round {round_number}")

        try:
            # Find the RestartBanner for this round and scroll to it
            # RestartBanners are tagged with round-X class
            found_separator = False
            for widget in self.query(f".round-{round_number}"):
                # Look for RestartBanner (has the round separator banner)
                if isinstance(widget, RestartBanner):
                    widget.scroll_visible(animate=True, top=True)
                    found_separator = True
                    break

            # If no RestartBanner found (e.g., round 1 which may not have one),
            # find the first widget for this round
            if not found_separator:
                for widget in self.query(f".round-{round_number}"):
                    widget.scroll_visible(animate=True, top=True)
                    break

            logger.debug(f"TimelineSection.switch_to_round: done scrolling to round {round_number}")
        except Exception as e:
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
    """Prominent round separator banner - single strong line spanning full width.

    Design:
    ```
    ━━━━━━━━━━ Round 2 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Context reset ━━
    ```

    For Final Answer:
    ```
    ━━━━━━━━━━ ✓ Final Answer ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ A1.1 won (2) ━━━━━
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
        """Render a single strong line separator with label and subtitle."""
        import re

        # Use no_wrap to prevent line breaking
        text = Text(no_wrap=True)

        # Clean up the label - extract meaningful info
        display_label = self._label
        is_final = "FINAL" in display_label.upper()

        # Thin line character for minimalist look
        line_char = "─"
        # Get actual widget width dynamically
        try:
            total_width = self.size.width
            if total_width < 40:
                # Fallback if width not yet computed or too small
                total_width = 200
        except Exception:
            total_width = 200  # Fallback

        if is_final:
            # Final Presentation - muted green styling
            display_label = "✓ Final Answer"
            line_color = "#4b5563"  # Neutral gray line
            label_color = "#6b9e7a"  # Muted green for label
            subtitle_color = "#9ca3af"  # Gray for subtitle
        elif "RESTART" in display_label.upper():
            # Extract round number for restart - neutral gray styling
            match = re.search(r"ROUND\s*(\d+)", display_label, re.IGNORECASE)
            if match:
                round_num = match.group(1)
                display_label = f"Round {round_num}"
            else:
                display_label = "New Round"
            line_color = "#4b5563"  # Neutral gray line
            label_color = "#9ca3af"  # Gray for label
            subtitle_color = "#6b7280"  # Dim gray for subtitle
        elif display_label.upper().startswith("ROUND"):
            # Simple "Round X" label - neutral gray styling
            match = re.search(r"ROUND\s*(\d+)", display_label, re.IGNORECASE)
            if match:
                round_num = match.group(1)
                display_label = f"Round {round_num}"
            line_color = "#4b5563"  # Neutral gray line
            label_color = "#9ca3af"  # Gray for label
            subtitle_color = "#6b7280"  # Dim gray for subtitle
        else:
            line_color = "#4b5563"  # Neutral gray
            label_color = "#9ca3af"  # Gray
            subtitle_color = "#6b7280"  # Dim gray

        # Build single line: ━━━━━ Label ━━━━━━━━━━━━━━━━━━━━━ Subtitle ━━━━━
        left_line_len = 6
        label_text = f" {display_label} "

        # Start with left segment - use same color as label for visibility
        text.append(line_char * left_line_len, style=line_color)
        text.append(label_text, style=f"bold {label_color}")

        if self._subtitle:
            subtitle_text = f" {self._subtitle} "
            # Middle segment fills the space
            middle_len = total_width - left_line_len - len(label_text) - len(subtitle_text) - 6
            if middle_len < 4:
                middle_len = 4

            text.append(line_char * middle_len, style=line_color)
            text.append(subtitle_text, style=f"italic {subtitle_color}")
            text.append(line_char * 6, style=line_color)
        else:
            # No subtitle - just fill with line
            remaining = total_width - left_line_len - len(label_text)
            text.append(line_char * remaining, style=line_color)

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
        border: solid #fab387;
        background: transparent;
    }

    FinalPresentationCard.streaming {
        border: double #fab387;
    }

    FinalPresentationCard.completed {
        border: solid #a6e3a1;
        background: transparent;
    }

    /* Hide post_eval and context_paths in completed mode when they have hidden class */
    FinalPresentationCard.completed #final_card_post_eval.hidden,
    FinalPresentationCard.completed #final_card_context_paths.hidden {
        display: none;
        height: 0;
        padding: 0;
        margin: 0;
    }

    FinalPresentationCard #final_card_header {
        width: 100%;
        height: auto;
        padding: 0 1;
        background: transparent;
    }

    FinalPresentationCard.completed #final_card_header {
        background: transparent;
    }

    FinalPresentationCard #final_card_title {
        color: #fab387;
        text-style: bold;
    }

    FinalPresentationCard.completed #final_card_title {
        color: #a6e3a1;
    }

    FinalPresentationCard #final_card_votes {
        color: #8b949e;
        height: 1;
        border-bottom: solid #45475a;
        padding-bottom: 1;
        margin-bottom: 1;
    }

    FinalPresentationCard #final_card_content {
        width: 100%;
        height: auto;
        max-height: 30;
        padding: 1 2 0 2;
        background: transparent;
        overflow-y: auto;
    }

    FinalPresentationCard #final_card_text {
        width: 100%;
        height: auto;
        background: transparent;
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

    FinalPresentationCard #final_card_context_paths {
        width: 100%;
        height: auto;
        padding: 1 2;
        background: #161b22;
        border-top: dashed #30363d;
    }

    FinalPresentationCard #final_card_context_paths.hidden {
        display: none;
    }

    FinalPresentationCard #context_paths_header {
        color: #58a6ff;
        text-style: bold;
        margin-bottom: 1;
    }

    FinalPresentationCard #context_paths_list {
        height: auto;
    }

    FinalPresentationCard .context-path-new {
        color: #3fb950;
    }

    FinalPresentationCard .context-path-modified {
        color: #d29922;
    }

    FinalPresentationCard #final_card_footer {
        width: 100%;
        height: auto;
        padding: 1 2;
        background: transparent;
    }

    FinalPresentationCard #final_card_footer.hidden {
        display: none;
    }

    FinalPresentationCard #final_card_buttons {
        width: 100%;
        height: 1;
    }

    /* Footer links - consistent clickable link style */
    FinalPresentationCard .footer-link {
        width: auto;
        height: 1;
        color: #89b4fa;
        text-style: underline;
        padding: 0 1;
    }

    FinalPresentationCard .footer-link:hover {
        color: #b4befe;
        text-style: bold underline;
    }

    FinalPresentationCard #continue_message {
        display: none;
    }

    /* Full-width mode - fills available vertical space */
    FinalPresentationCard.full-width-mode {
        height: 1fr;
        min-height: 20;
    }

    FinalPresentationCard.full-width-mode #final_card_content {
        height: 1fr;
        overflow-y: auto;
    }

    /* Enhanced prominence styling for full-width mode */
    FinalPresentationCard.full-width-mode.streaming {
        border: double #fab387;
    }

    FinalPresentationCard.full-width-mode.completed {
        border: double #a6e3a1;
        background: transparent;
    }

    FinalPresentationCard.full-width-mode #final_card_header {
        background: transparent;
        padding: 0 1;
    }

    FinalPresentationCard.full-width-mode #final_card_title {
        color: #a6e3a1;
    }

    /* Completion-only mode - minimal footer bar */
    /* Content already shown through normal pipeline, just show action buttons */
    FinalPresentationCard.completion-only {
        border: none;
        background: transparent;
        margin: 0;
        padding: 0;
    }

    FinalPresentationCard.completion-only #final_card_header {
        display: none;
    }

    FinalPresentationCard.completion-only #final_card_content {
        display: none;
    }

    FinalPresentationCard.completion-only #final_card_post_eval {
        display: none;
    }

    FinalPresentationCard.completion-only #final_card_context_paths {
        display: none;
    }

    FinalPresentationCard.completion-only #final_card_footer {
        display: block;
        background: #161b22;
        border: solid #30363d;
        padding: 1 2;
    }

    /* Spacer to push unlock button to the right in footer */
    FinalPresentationCard #final_card_button_spacer {
        width: 1fr;
        height: 1;
    }

    FinalPresentationCard.locked-mode #final_card_content {
        height: 1fr;
        max-height: 999;
    }

    FinalPresentationCard.locked-mode {
        height: 1fr;
    }
    """

    def __init__(
        self,
        agent_id: str,
        model_name: str = "",
        vote_results: Optional[Dict] = None,
        context_paths: Optional[Dict] = None,
        completion_only: bool = False,
        id: Optional[str] = None,
    ) -> None:
        super().__init__(id=id or "final_presentation_card")
        self.agent_id = agent_id
        self.model_name = model_name
        self.vote_results = vote_results or {}
        self.context_paths = context_paths or {}
        self._final_content: list = []
        self._post_eval_content: list = []
        self._is_streaming = not completion_only
        self._post_eval_expanded = False
        self._post_eval_status = "none"  # none, evaluating, verified
        self._text_widget: Optional[Static] = None  # Direct reference to text widget
        if completion_only:
            self.add_class("completion-only")
        else:
            self.add_class("streaming")

    def compose(self) -> ComposeResult:
        from textual.containers import Horizontal, ScrollableContainer
        from textual.widgets import Label

        # Header section - compact single line
        with Vertical(id="final_card_header"):
            yield Label(self._build_title(), id="final_card_title")
            yield Label(self._build_vote_summary(), id="final_card_votes")

        # Content section with Static text (scrollable)
        # NOTE: markup=False to avoid Rich markup parsing issues with special characters
        # Store direct reference for faster updates
        self._text_widget = Static("", id="final_card_text", markup=False)
        with ScrollableContainer(id="final_card_content"):
            yield self._text_widget

        # Post-evaluation section (hidden until post-eval content arrives)
        with Vertical(id="final_card_post_eval", classes="hidden"):
            with Horizontal(id="post_eval_header"):
                yield Label("🔍 Evaluating...", id="post_eval_status", classes="evaluating")
                yield Label("", id="post_eval_toggle")
            with ScrollableContainer(id="post_eval_details", classes="collapsed"):
                yield Static("", id="post_eval_content")

        # Context paths section (hidden if no paths)
        has_paths = bool(self.context_paths.get("new") or self.context_paths.get("modified"))
        with Vertical(id="final_card_context_paths", classes="" if has_paths else "hidden"):
            new_count = len(self.context_paths.get("new", []))
            mod_count = len(self.context_paths.get("modified", []))
            total = new_count + mod_count
            yield Label(f"📂 Files Written ({total})", id="context_paths_header")
            with Vertical(id="context_paths_list"):
                for path in self.context_paths.get("new", []):
                    yield Label(f"  ✚ {path}", classes="context-path-new")
                for path in self.context_paths.get("modified", []):
                    yield Label(f"  ✎ {path}", classes="context-path-modified")

        # Footer with link-style actions and continue message (hidden until complete)
        with Vertical(id="final_card_footer", classes="hidden"):
            with Horizontal(id="final_card_buttons"):
                yield Static("📋 Copy", id="final_card_copy_btn", classes="footer-link")
                yield Static("📂 Workspace", id="final_card_workspace_btn", classes="footer-link")
                # Spacer to push unlock button to the right
                yield Static("", id="final_card_button_spacer")
                # Unlock button - hidden initially, shown when locked
                link = Static("↩ Previous Work", id="final_card_unlock_btn", classes="footer-link")
                link.display = False
                yield link
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

        # Format: "Winner: agent_a | Votes: agent_a (2), agent_b (1)"
        tie_note = " (tie-breaker)" if is_tie else ""
        counts_str = ", ".join(f"{aid} ({count})" for aid, count in vote_counts.items())

        return f"Winner: {winner}{tie_note} | Votes: {counts_str}"

    def append_chunk(self, chunk: str) -> None:
        """Append streaming content to the card.

        Args:
            chunk: Text chunk to append
        """
        if not chunk:
            return

        # Always accumulate content first (even if widget not ready yet)
        self._final_content.append(chunk)

        # Try to update the widget directly
        if not self._try_update_text():
            # Widget not ready - compose might not have run yet
            # Try to force recompose and schedule retry
            try:
                if self._text_widget is None:
                    # Compose hasn't run - try to trigger it
                    self.recompose()
                self.set_timer(0.1, self._try_update_text)
            except Exception:
                pass  # Ignore if timer/recompose can't be set

    def _try_update_text(self) -> bool:
        """Try to update the text widget with accumulated content.

        Called after each chunk arrives. Silently fails if widget not ready yet.

        Returns:
            True if update succeeded, False if widget not ready.
        """
        if not self._final_content:
            return True  # Nothing to update

        full_text = "".join(self._final_content)

        # Use direct reference if available (set in compose)
        if self._text_widget is not None:
            try:
                self._text_widget.update(full_text)
                self._text_widget.refresh()
                return True
            except Exception:
                pass

        # Fallback to query
        try:
            text_widget = self.query_one("#final_card_text", Static)
            text_widget.update(full_text)
            text_widget.refresh()
            return True
        except Exception:
            pass

        # Last resort: manually create the text widget if compose didn't run
        try:
            # Check if we have any children at all
            if not list(self.children):
                # Create a simple Static widget directly
                self._text_widget = Static(full_text, id="final_card_text_manual", markup=False)
                self.mount(self._text_widget)
                return True
        except Exception:
            pass

        return False

    def on_mount(self) -> None:
        """Flush any pending content when the widget is mounted."""
        # Flush any buffered content that arrived before mount
        self._try_update_text()

        # In completion-only mode, show footer immediately and mark as completed
        # (content has already been shown through the normal pipeline)
        if self.has_class("completion-only"):
            self.complete()

    def _on_compose(self) -> None:
        """Called after compose() completes - use this to flush content."""
        # Try to update after compose completes
        if self._final_content:
            self._try_update_text()

    def complete(self) -> None:
        """Mark the presentation as complete and show action buttons."""
        from textual.widgets import Label

        self._is_streaming = False

        # Update styling
        self.remove_class("streaming")
        # Only add completed class if not in completion-only mode
        # (completion-only mode has its own styling via the class)
        if not self.has_class("completion-only"):
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
        """Handle clicks on footer links and post-eval toggle."""
        from textual.widgets import Label

        widget_id = getattr(event.widget, "id", None) if hasattr(event, "widget") else None

        # Handle footer link clicks
        if widget_id == "final_card_unlock_btn":
            self._toggle_lock()
            event.stop()
            return
        elif widget_id == "final_card_copy_btn":
            self._copy_to_clipboard()
            event.stop()
            return
        elif widget_id == "final_card_workspace_btn":
            self._open_workspace()
            event.stop()
            return

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

    def _toggle_lock(self) -> None:
        """Toggle between locked (answer-only) and unlocked (full timeline) view."""
        # Find parent TimelineSection
        timeline = None
        parent = self.parent
        while parent:
            if isinstance(parent, TimelineSection):
                timeline = parent
                break
            parent = parent.parent

        if not timeline:
            return

        try:
            link = self.query_one("#final_card_unlock_btn", Static)
            link.display = True  # Always keep visible once shown

            if timeline.is_answer_locked:
                # Unlock: show full timeline
                timeline.unlock_final_answer()
                self.remove_class("locked-mode")
                link.update("⎯ Answer Only")
            else:
                # Lock: show only final answer
                timeline.lock_to_final_answer(self.id or "final_presentation_card")
                self.add_class("locked-mode")
                link.update("↩ Previous Work")
        except Exception:
            pass

    def set_locked_mode(self, locked: bool) -> None:
        """Set the locked mode state programmatically.

        Called by textual_terminal_display when auto-locking after final answer.

        Args:
            locked: Whether to enable locked mode
        """
        if locked:
            self.add_class("locked-mode")
            try:
                link = self.query_one("#final_card_unlock_btn", Static)
                link.display = True
                link.update("↩ Previous Work")
            except Exception:
                pass
        else:
            self.remove_class("locked-mode")
            try:
                link = self.query_one("#final_card_unlock_btn", Static)
                link.display = False
                link.update("⎯ Answer Only")
            except Exception:
                pass

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
