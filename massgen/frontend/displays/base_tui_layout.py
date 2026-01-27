# -*- coding: utf-8 -*-
"""
Base TUI Layout Mixin for MassGen TUI.

Provides the shared content pipeline for TUI panels with timeline content display.
Both AgentPanel (main TUI) and SubagentPanel (subagent screen) inherit this mixin
to ensure consistent content handling.

Features:
- Content routing (add_content -> TimelineSection)
- Tool/thinking/status/presentation handling
- Tool batching (Timeline Chronology Rule) via ToolBatchTracker
- Line buffering for streaming text

Usage:
    class AgentPanel(Container, BaseTUILayoutMixin):
        def _get_timeline(self) -> TimelineSection:
            return self.query_one("#my_timeline", TimelineSection)

        def _get_ribbon(self) -> Optional[AgentStatusRibbon]:
            return self.app._status_ribbon
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional

from .content_handlers import (
    ThinkingContentHandler,
    ToolBatchTracker,
    ToolContentHandler,
    ToolDisplayData,
)
from .content_normalizer import ContentNormalizer, NormalizedContent


def _process_line_buffer(
    buffer: str,
    new_content: str,
    write_func,
) -> str:
    """Process streaming content with line buffering.

    Accumulates content until newlines are found, then writes complete lines.
    Returns the remaining buffer (incomplete line).

    Args:
        buffer: Current buffer contents
        new_content: New content to add
        write_func: Function to call with complete lines

    Returns:
        Updated buffer with any incomplete line content
    """
    buffer += new_content
    while "\n" in buffer:
        line, buffer = buffer.split("\n", 1)
        line = line.rstrip()
        if line:
            write_func(line)
    return buffer


def tui_log(msg: str) -> None:
    """Log to TUI debug file."""
    try:
        with open("/tmp/tui_debug.log", "a") as f:
            f.write(f"[BaseTUILayout] {msg}\n")
    except Exception:
        pass


class BaseTUILayoutMixin:
    """Mixin class providing content pipeline for TUI panels.

    This mixin extracts ~350 lines of shared content handling logic from
    AgentPanel. Both AgentPanel and SubagentPanel inherit this mixin for
    consistent content display.

    Subclasses must implement:
    - _get_timeline(): Return the TimelineSection widget
    - _get_ribbon(): Return the AgentStatusRibbon widget (or None)

    State provided by mixin:
    - _current_round: Which round content is being received
    - _viewed_round: Which round is currently displayed
    - _tool_handler: ToolContentHandler instance
    - _thinking_handler: ThinkingContentHandler instance
    - _batch_tracker: ToolBatchTracker instance
    - _line_buffer: Buffer for streaming text
    - _last_text_class: Last text class used for flushing
    - _context_by_round: Context sources per round
    """

    def init_content_pipeline(self) -> None:
        """Initialize the content pipeline state.

        Call this in __init__ after super().__init__().
        """
        # Content handlers
        self._tool_handler = ToolContentHandler()
        self._thinking_handler = ThinkingContentHandler()
        self._batch_tracker = ToolBatchTracker()

        # Line buffering for streaming
        self._line_buffer = ""
        self._last_text_class = "content-inline"

        # Round tracking
        self._current_round: int = 1
        self._viewed_round: int = 1

        # Context tracking per round
        self._context_by_round: Dict[int, List[str]] = {}

        # Timeline event counter for debugging
        self._timeline_event_counter = 0

    # -------------------------------------------------------------------------
    # Abstract methods - subclasses must implement
    # -------------------------------------------------------------------------

    @abstractmethod
    def _get_timeline(self):
        """Get the TimelineSection widget.

        Returns:
            TimelineSection: The timeline widget for content display
        """
        raise NotImplementedError

    @abstractmethod
    def _get_ribbon(self):
        """Get the AgentStatusRibbon widget (or None).

        Returns:
            Optional[AgentStatusRibbon]: The status ribbon widget, or None
        """
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Main content routing
    # -------------------------------------------------------------------------

    def add_content(self, content: str, content_type: str, tool_call_id: Optional[str] = None):
        """Add content to the panel using section-based routing.

        Content is normalized and routed to appropriate sections:
        - Tool content -> ToolSection (collapsible tool cards)
        - Thinking/text -> TimelineSection (streaming text)
        - Status -> Updates status display
        - Presentation -> TimelineSection with completion styling
        - Restart -> Round separator

        Args:
            content: The content to add
            content_type: Type hint from backend
            tool_call_id: Optional unique ID for this tool call
        """
        # Normalize content first, passing tool_call_id
        normalized = ContentNormalizer.normalize(content, content_type, tool_call_id)

        # Debug: Log timeline order
        if not normalized.content_type.startswith("tool_"):
            self._timeline_event_counter += 1
            preview = content[:80].replace("\n", "\\n") if content else ""
            try:
                with open("/tmp/tui_timeline_trace.log", "a") as f:
                    f.write(
                        f"[{self._timeline_event_counter:04d}] type={normalized.content_type} " f"raw={content_type} preview={preview}\n",
                    )
            except Exception:
                pass

        # Route based on detected content type
        if normalized.content_type.startswith("tool_"):
            self._add_tool_content(normalized, content, content_type)
        elif normalized.content_type == "status":
            self._add_status_content(normalized)
        elif normalized.content_type == "presentation":
            self._add_presentation_content(normalized)
        elif content_type == "restart":
            self._add_restart_content(content)
        elif normalized.content_type == "injection":
            self._add_injection_content(normalized)
        elif normalized.content_type == "reminder":
            self._add_reminder_content(normalized)
        elif normalized.content_type in ("thinking", "text", "content"):
            self._add_thinking_content(normalized, content_type)
        else:
            # Fallback: route to thinking section if displayable
            if normalized.should_display:
                self._add_thinking_content(normalized, content_type)

    # -------------------------------------------------------------------------
    # Content type handlers
    # -------------------------------------------------------------------------

    def _add_tool_content(self, normalized: NormalizedContent, raw_content: str, raw_type: str):
        """Route tool content to TimelineSection (chronologically).

        MCP tools from the same server are batched into ToolBatchCard when 2+
        consecutive tools arrive. Single tools appear as normal ToolCallCard.
        """
        # Flush any pending line buffer content before processing tool
        self._flush_line_buffer_to_timeline()

        # Process through handler
        tool_data = self._tool_handler.process(normalized)

        if not tool_data:
            return

        try:
            timeline = self._get_timeline()
            if timeline is None:
                return

            # Check if this should skip batching (e.g., planning tools)
            skip_batching = self._should_skip_batching(tool_data)

            # Debug: Log tool content
            if tool_data.status == "running":
                existing_card = timeline.get_tool(tool_data.tool_id)
                existing_batch = timeline.get_tool_batch(tool_data.tool_id) if not skip_batching else None
                is_args_update = existing_card is not None or existing_batch is not None

                if not is_args_update:
                    self._timeline_event_counter += 1
                    try:
                        with open("/tmp/tui_timeline_trace.log", "a") as f:
                            f.write(
                                f"[{self._timeline_event_counter:04d}] type=tool_{tool_data.status} " f"tool={tool_data.display_name} tool_id={tool_data.tool_id}\n",
                            )
                    except Exception:
                        pass

            if tool_data.status == "running":
                # Tool starting - handle batching or add as standalone
                existing_card = timeline.get_tool(tool_data.tool_id)
                existing_batch = timeline.get_tool_batch(tool_data.tool_id) if not skip_batching else None

                if existing_card:
                    # Update existing standalone card with args
                    if tool_data.args_summary:
                        existing_card.set_params(tool_data.args_summary, tool_data.args_full)
                elif existing_batch:
                    # Update existing tool in batch with args
                    timeline.update_tool_in_batch(tool_data.tool_id, tool_data)
                elif not skip_batching:
                    # Check if this MCP tool should be batched
                    action, server_name, batch_id, pending_id = self._batch_tracker.process_tool(
                        tool_data,
                    )

                    if action == "pending":
                        # First MCP tool - show as normal card, track for potential batch
                        timeline.add_tool(tool_data, round_number=self._current_round)
                    elif action == "convert_to_batch" and server_name and batch_id and pending_id:
                        # Second tool from same server - convert to batch
                        timeline.convert_tool_to_batch(
                            pending_id,
                            tool_data,
                            batch_id,
                            server_name,
                            round_number=self._current_round,
                        )
                    elif action == "add_to_batch" and batch_id:
                        # Add to existing batch
                        timeline.add_tool_to_batch(batch_id, tool_data)
                    else:
                        # Standalone non-MCP tool
                        timeline.add_tool(tool_data, round_number=self._current_round)
                else:
                    # Fallback for other special tools
                    timeline.add_tool(tool_data, round_number=self._current_round)
            else:
                # Tool completed/failed - update the card in timeline
                if not skip_batching:
                    # Use batch tracker to determine if this is a batch or standalone update
                    action, server_name, batch_id, _ = self._batch_tracker.process_tool(tool_data)

                    if action == "update_batch" and timeline.get_tool_batch(tool_data.tool_id):
                        timeline.update_tool_in_batch(tool_data.tool_id, tool_data)
                    else:
                        # Update standalone tool card with result/error
                        timeline.update_tool(tool_data.tool_id, tool_data)
                else:
                    # Update standalone tool card
                    timeline.update_tool(tool_data.tool_id, tool_data)

                # Post-completion hooks (override in subclass)
                self._on_tool_completed(tool_data, timeline)

        except Exception as e:
            tui_log(f"Tool content error: {e}")

        self._line_buffer = ""

    def _add_status_content(self, normalized: NormalizedContent):
        """Route status content to TimelineSection with subtle display."""
        if not normalized.should_display:
            return

        # Mark that non-tool content arrived (prevents future batching)
        self._batch_tracker.mark_content_arrived()
        self._batch_tracker.finalize_current_batch()

        try:
            timeline = self._get_timeline()
            if timeline is None:
                return
            timeline.add_text(
                f"● {normalized.cleaned_content}",
                style="dim cyan",
                text_class="status",
                round_number=self._current_round,
            )
        except Exception:
            pass

        self._line_buffer = ""

    def _add_presentation_content(self, normalized: NormalizedContent):
        """Route presentation content to TimelineSection."""
        if not normalized.should_display:
            return

        # Mark that non-tool content arrived
        self._batch_tracker.mark_content_arrived()
        self._batch_tracker.finalize_current_batch()

        try:
            timeline = self._get_timeline()
            if timeline is None:
                return
            timeline.add_text(
                normalized.cleaned_content,
                style="bold #4ec9b0",
                text_class="response",
                round_number=self._current_round,
            )
        except Exception:
            pass

        self._line_buffer = ""

    def _add_restart_content(self, content: str):
        """Handle round transition - start a new round.

        Args:
            content: The restart content with round info
        """
        # Parse attempt number
        attempt = 1
        is_context_reset = "context" in content.lower() or "reset" in content.lower()

        if "attempt:" in content:
            try:
                parts = content.split("attempt:")
                if len(parts) > 1:
                    attempt_part = parts[1].split()[0]
                    attempt = int(attempt_part)
            except (ValueError, IndexError):
                pass

        # Start the new round
        self.start_new_round(attempt, is_context_reset)
        self._line_buffer = ""

    def _add_thinking_content(self, normalized: NormalizedContent, raw_type: str):
        """Route thinking/text content to TimelineSection."""
        # Process through handler for extra filtering
        cleaned = self._thinking_handler.process(normalized)
        if not cleaned:
            return

        # Mark that non-tool content arrived
        self._batch_tracker.mark_content_arrived()
        self._batch_tracker.finalize_current_batch()

        # Check if this is coordination content
        is_coordination = getattr(normalized, "is_coordination", False)

        # Only display thinking and content types
        if not is_coordination and raw_type not in ("thinking", "content", "text"):
            return

        try:
            timeline = self._get_timeline()
            if timeline is None:
                return

            current_round = self._current_round

            # Use different text_class for thinking vs content
            text_class = "thinking-inline" if normalized.content_type == "thinking" else "content-inline"

            # Flush line buffer if content type changed
            if self._last_text_class != text_class and self._line_buffer.strip():
                prev_text_class = self._last_text_class
                timeline.add_text(
                    self._line_buffer,
                    style="dim italic",
                    text_class=prev_text_class,
                    round_number=current_round,
                )
                self._line_buffer = ""
            self._last_text_class = text_class

            def write_line(line: str):
                timeline.add_text(
                    line,
                    style="dim italic",
                    text_class=text_class,
                    round_number=current_round,
                )

            self._line_buffer = _process_line_buffer(
                self._line_buffer,
                cleaned,
                write_line,
            )
        except Exception:
            pass

    def _add_injection_content(self, normalized: NormalizedContent):
        """Add injection content (cross-agent context sharing) to timeline."""
        if not normalized.should_display:
            return

        # Mark that non-tool content arrived
        self._batch_tracker.mark_content_arrived()
        self._batch_tracker.finalize_current_batch()

        content = normalized.cleaned_content
        preview = content[:100] + "..." if len(content) > 100 else content
        preview = preview.replace("\n", " ")

        try:
            timeline = self._get_timeline()
            if timeline is None:
                return
            timeline.add_text(
                f"📥 Context Update: {preview}",
                style="bold",
                text_class="injection",
                round_number=self._current_round,
            )
        except Exception:
            pass

    def _add_reminder_content(self, normalized: NormalizedContent):
        """Add reminder content (high priority task reminders) to timeline."""
        if not normalized.should_display:
            return

        # Mark that non-tool content arrived
        self._batch_tracker.mark_content_arrived()
        self._batch_tracker.finalize_current_batch()

        content = normalized.cleaned_content
        preview = content[:100] + "..." if len(content) > 100 else content
        preview = preview.replace("\n", " ")

        try:
            timeline = self._get_timeline()
            if timeline is None:
                return
            timeline.add_text(
                f"💡 Reminder: {preview}",
                style="bold",
                text_class="reminder",
                round_number=self._current_round,
            )
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Helper methods
    # -------------------------------------------------------------------------

    def _flush_line_buffer_to_timeline(self, text_class: Optional[str] = None) -> None:
        """Flush any remaining line buffer content to the timeline.

        Called when content type changes to ensure all content is written.

        Args:
            text_class: CSS class for the content. If None, uses last text_class.
        """
        if self._line_buffer.strip():
            if text_class is None:
                text_class = self._last_text_class
            try:
                timeline = self._get_timeline()
                if timeline is None:
                    return
                timeline.add_text(
                    self._line_buffer,
                    style="dim italic",
                    text_class=text_class,
                    round_number=self._current_round,
                )
            except Exception:
                pass
            self._line_buffer = ""

    def _should_skip_batching(self, tool_data: ToolDisplayData) -> bool:
        """Check if a tool should skip batching.

        Override in subclass for custom tool handling (e.g., planning tools).

        Args:
            tool_data: The tool data to check

        Returns:
            True if batching should be skipped for this tool
        """
        return False

    def _on_tool_completed(self, tool_data: ToolDisplayData, timeline: Any) -> None:
        """Hook called when a tool completes.

        Override in subclass for custom post-completion behavior.

        Args:
            tool_data: The completed tool data
            timeline: The timeline widget
        """

    # -------------------------------------------------------------------------
    # Round management
    # -------------------------------------------------------------------------

    def start_new_round(self, round_number: int, is_context_reset: bool = False) -> None:
        """Start a new round - update tracking and switch visibility.

        Args:
            round_number: The new round number
            is_context_reset: Whether this round started with a context reset
        """
        # Update round tracking
        self._current_round = round_number
        self._viewed_round = round_number

        try:
            timeline = self._get_timeline()
            if timeline is None:
                return
            timeline.switch_to_round(round_number)

            # Clear tools tracking for new round
            if hasattr(timeline, "clear_tools_tracking"):
                timeline.clear_tools_tracking()

            # Add "Round X" banner
            if round_number > 1:
                subtitle = "Restart"
                if is_context_reset:
                    subtitle += " • Context cleared"
                timeline.add_separator(
                    f"Round {round_number}",
                    round_number=round_number,
                    subtitle=subtitle,
                )
        except Exception as e:
            tui_log(f"start_new_round error: {e}")

        # Reset per-round state
        self._tool_handler.reset()
        self._batch_tracker.reset()

        # Update ribbon if available
        self._update_ribbon_round(round_number, is_context_reset)

    def _update_ribbon_round(self, round_number: int, is_context_reset: bool = False) -> None:
        """Update the status ribbon with the new round number.

        Args:
            round_number: The round number
            is_context_reset: Whether this was a context reset
        """
        ribbon = self._get_ribbon()
        if ribbon is not None:
            try:
                # Get agent_id if available
                agent_id = getattr(self, "agent_id", None) or ""
                ribbon.set_round(agent_id, round_number, is_context_reset)
            except Exception:
                pass

    def show_restart_separator(self, attempt: int = 1, reason: str = "") -> None:
        """Handle restart - start new round.

        Args:
            attempt: The attempt/round number
            reason: Reason for restart
        """
        # Mark that non-tool content arrived
        self._batch_tracker.mark_content_arrived()
        self._batch_tracker.finalize_current_batch()

        # Determine if this was a context reset
        is_context_reset = "context" in reason.lower() or "reset" in reason.lower()

        # Start the new round
        self.start_new_round(attempt, is_context_reset)
