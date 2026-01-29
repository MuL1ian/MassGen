# -*- coding: utf-8 -*-
"""
Unified Content Processor for MassGen TUI.

Provides a single source of truth for content processing logic, used by both
the main TUI (AgentPanel) and SubagentTuiModal. This ensures:
- Visual parity between main TUI and subagent modal
- No duplicate code to maintain
- Automatic propagation of improvements

Design Philosophy:
- Process raw content/events into structured data for TimelineSection
- Respect Timeline Chronology Rule: tools only batch when consecutive
- Handle line buffering for streaming content
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple

from massgen.events import EventType, MassGenEvent

from .content_handlers import (
    ThinkingContentHandler,
    ToolBatchTracker,
    ToolContentHandler,
    ToolDisplayData,
    format_tool_display_name,
    get_mcp_server_name,
    get_tool_category,
)
from .content_normalizer import ContentNormalizer, NormalizedContent

# Output types for ContentProcessor
OutputType = Literal[
    "tool",
    "tool_batch",
    "thinking",
    "text",
    "status",
    "presentation",
    "injection",
    "reminder",
    "separator",
    "final_answer",
    "skip",  # Filter out this content
]

# Batch actions from ToolBatchTracker
BatchAction = Literal[
    "standalone",  # Non-MCP tool, use regular ToolCallCard
    "pending",  # First MCP tool, show as ToolCallCard but track for potential batch
    "convert_to_batch",  # Second tool arrived - convert pending to batch
    "add_to_batch",  # Add to existing batch
    "update_standalone",  # Update a standalone/pending tool
    "update_batch",  # Update existing tool in batch
]


@dataclass
class ContentOutput:
    """Structured output from ContentProcessor for TimelineSection.

    This dataclass contains all the information needed to render content
    in the timeline, regardless of the content type.
    """

    output_type: OutputType
    round_number: int = 1

    # For tool content
    tool_data: Optional[ToolDisplayData] = None
    batch_action: Optional[BatchAction] = None
    batch_id: Optional[str] = None
    server_name: Optional[str] = None
    pending_tool_id: Optional[str] = None  # For convert_to_batch

    # For text content
    text_content: Optional[str] = None
    text_style: str = ""
    text_class: str = ""

    # For batched tools (multiple tools in a batch)
    batch_tools: List[ToolDisplayData] = field(default_factory=list)

    # For separators
    separator_label: str = ""
    separator_subtitle: str = ""

    # Original normalized content (for debugging/advanced use)
    normalized: Optional[NormalizedContent] = None


class ContentProcessor:
    """Unified content processing for TUI and subagent modal.

    Handles:
    - Content normalization via ContentNormalizer
    - Tool event lifecycle tracking via ToolContentHandler
    - Tool batching logic (Timeline Chronology Rule) via ToolBatchTracker
    - Thinking/content filtering via ThinkingContentHandler
    - Line buffering for streaming content

    Usage:
        processor = ContentProcessor()

        # For streaming content from orchestrator (main TUI)
        output = processor.process(content, content_type, tool_call_id, round_number)
        if output and output.output_type != "skip":
            timeline.apply_output(output)

        # For events.jsonl (subagent modal)
        output = processor.process_event(event, round_number)
        if output and output.output_type != "skip":
            timeline.apply_output(output)
    """

    def __init__(self) -> None:
        # Content handlers (shared logic)
        self._tool_handler = ToolContentHandler()
        self._thinking_handler = ThinkingContentHandler()
        self._batch_tracker = ToolBatchTracker()

        # Line buffering state for streaming
        self._line_buffer = ""
        self._last_text_class: Optional[str] = None

        # Counter for tracking events (debugging)
        self._event_counter = 0

        # Event processing state (for events.jsonl)
        self._event_tool_states: Dict[str, Dict[str, Any]] = {}
        self._event_pending_batch: List[ToolDisplayData] = []
        self._event_round_number: int = 1

    def reset(self) -> None:
        """Reset processor state (e.g., for new session/round)."""
        self._tool_handler.reset()
        self._batch_tracker.reset()
        self._line_buffer = ""
        self._last_text_class = None
        self._event_counter = 0
        self._event_tool_states.clear()
        self._event_pending_batch.clear()
        self._event_round_number = 1

    def process(
        self,
        content: str,
        content_type: str,
        tool_call_id: Optional[str] = None,
        round_number: int = 1,
    ) -> Optional[ContentOutput]:
        """Process raw content and return structured output for TimelineSection.

        This is the main entry point for processing streaming content from the
        orchestrator (used by AgentPanel.add_content).

        Args:
            content: Raw content string
            content_type: Type hint from backend (tool, thinking, text, etc.)
            tool_call_id: Optional unique ID for tool calls
            round_number: Current round number for visibility tagging

        Returns:
            ContentOutput with structured data for TimelineSection, or None if
            content should be completely filtered out.
        """
        # Normalize content
        normalized = ContentNormalizer.normalize(content, content_type, tool_call_id)

        self._event_counter += 1

        # Route based on detected content type
        if normalized.content_type.startswith("tool_"):
            return self._process_tool_content(normalized, round_number)
        elif normalized.content_type == "status":
            return self._process_status_content(normalized, round_number)
        elif normalized.content_type == "presentation":
            return self._process_presentation_content(normalized, round_number)
        elif content_type == "restart":
            return self._process_restart_content(content, round_number)
        elif normalized.content_type == "injection":
            return self._process_injection_content(normalized, round_number)
        elif normalized.content_type == "reminder":
            return self._process_reminder_content(normalized, round_number)
        elif normalized.content_type in ("thinking", "text", "content"):
            return self._process_thinking_content(normalized, content_type, round_number)
        else:
            # Fallback: route to thinking if displayable
            if normalized.should_display:
                return self._process_thinking_content(normalized, content_type, round_number)
            return ContentOutput(output_type="skip", round_number=round_number)

    def _process_tool_content(
        self,
        normalized: NormalizedContent,
        round_number: int,
    ) -> Optional[ContentOutput]:
        """Process tool-related content (start, args, complete, failed).

        Handles tool lifecycle tracking and batching decisions.
        """
        # Process through tool handler
        tool_data = self._tool_handler.process(normalized)

        if not tool_data:
            return None

        # Determine batch action
        batch_action, server_name, batch_id, pending_id = self._batch_tracker.process_tool(tool_data)

        return ContentOutput(
            output_type="tool",
            round_number=round_number,
            tool_data=tool_data,
            batch_action=batch_action,
            batch_id=batch_id,
            server_name=server_name,
            pending_tool_id=pending_id,
            normalized=normalized,
        )

    def _process_status_content(
        self,
        normalized: NormalizedContent,
        round_number: int,
    ) -> Optional[ContentOutput]:
        """Process status content (connection status, MCP status, etc.)."""
        if not normalized.should_display:
            return ContentOutput(output_type="skip", round_number=round_number)

        # Mark that non-tool content arrived (prevents future batching)
        self._batch_tracker.mark_content_arrived()
        self._batch_tracker.finalize_current_batch()

        return ContentOutput(
            output_type="status",
            round_number=round_number,
            text_content=f"● {normalized.cleaned_content}",
            text_style="dim cyan",
            text_class="status",
            normalized=normalized,
        )

    def _process_presentation_content(
        self,
        normalized: NormalizedContent,
        round_number: int,
    ) -> Optional[ContentOutput]:
        """Process presentation/final answer content."""
        if not normalized.should_display:
            return ContentOutput(output_type="skip", round_number=round_number)

        # Mark that non-tool content arrived
        self._batch_tracker.mark_content_arrived()
        self._batch_tracker.finalize_current_batch()

        return ContentOutput(
            output_type="presentation",
            round_number=round_number,
            text_content=normalized.cleaned_content,
            text_style="bold #4ec9b0",
            text_class="response",
            normalized=normalized,
        )

    def _process_restart_content(
        self,
        content: str,
        round_number: int,
    ) -> Optional[ContentOutput]:
        """Process restart/round transition content."""
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

        return ContentOutput(
            output_type="separator",
            round_number=attempt,
            separator_label=f"Round {attempt}",
            separator_subtitle="Context reset" if is_context_reset else "",
        )

    def _process_injection_content(
        self,
        normalized: NormalizedContent,
        round_number: int,
    ) -> Optional[ContentOutput]:
        """Process injection content (cross-agent context sharing)."""
        if not normalized.should_display:
            return ContentOutput(output_type="skip", round_number=round_number)

        # Mark that non-tool content arrived
        self._batch_tracker.mark_content_arrived()
        self._batch_tracker.finalize_current_batch()

        content = normalized.cleaned_content
        preview = content[:100] + "..." if len(content) > 100 else content
        preview = preview.replace("\n", " ")

        return ContentOutput(
            output_type="injection",
            round_number=round_number,
            text_content=f"📥 Context Update: {preview}",
            text_style="bold",
            text_class="injection",
            normalized=normalized,
        )

    def _process_reminder_content(
        self,
        normalized: NormalizedContent,
        round_number: int,
    ) -> Optional[ContentOutput]:
        """Process reminder content (high priority task reminders)."""
        if not normalized.should_display:
            return ContentOutput(output_type="skip", round_number=round_number)

        # Mark that non-tool content arrived
        self._batch_tracker.mark_content_arrived()
        self._batch_tracker.finalize_current_batch()

        content = normalized.cleaned_content
        preview = content[:100] + "..." if len(content) > 100 else content
        preview = preview.replace("\n", " ")

        return ContentOutput(
            output_type="reminder",
            round_number=round_number,
            text_content=f"💡 Reminder: {preview}",
            text_style="bold",
            text_class="reminder",
            normalized=normalized,
        )

    def _process_thinking_content(
        self,
        normalized: NormalizedContent,
        raw_type: str,
        round_number: int,
    ) -> Optional[ContentOutput]:
        """Process thinking/text content.

        Uses the ThinkingContentHandler for additional filtering.
        """
        # Process through handler for extra filtering
        cleaned = self._thinking_handler.process(normalized)
        if not cleaned:
            return ContentOutput(output_type="skip", round_number=round_number)

        # Mark that non-tool content arrived
        self._batch_tracker.mark_content_arrived()
        self._batch_tracker.finalize_current_batch()

        # Check if this is coordination content
        is_coordination = getattr(normalized, "is_coordination", False)

        # Determine output type and text class
        if not is_coordination and raw_type not in ("thinking", "content", "text"):
            return ContentOutput(output_type="skip", round_number=round_number)

        # Use different text_class for thinking vs content
        text_class = "thinking-inline" if normalized.content_type == "thinking" else "content-inline"

        return ContentOutput(
            output_type="thinking" if normalized.content_type == "thinking" else "text",
            round_number=round_number,
            text_content=cleaned,
            text_style="dim italic",
            text_class=text_class,
            normalized=normalized,
        )

    def process_line_buffered(
        self,
        content: str,
        content_type: str,
        tool_call_id: Optional[str] = None,
        round_number: int = 1,
        write_callback: Optional[Callable[[str, str, str, int], None]] = None,
    ) -> Tuple[Optional[ContentOutput], str]:
        """Process content with line buffering for streaming display.

        This method handles partial lines that arrive during streaming,
        buffering incomplete lines until a newline is received.

        Args:
            content: Raw content string (may be partial)
            content_type: Type hint from backend
            tool_call_id: Optional unique ID for tool calls
            round_number: Current round number
            write_callback: Optional callback (text, style, text_class, round) for immediate writes

        Returns:
            Tuple of (ContentOutput for non-text content, remaining line buffer)
        """
        # For non-text content, process normally and return
        normalized = ContentNormalizer.normalize(content, content_type, tool_call_id)

        if normalized.content_type.startswith("tool_"):
            # Flush any pending line buffer before processing tool
            if self._line_buffer.strip() and write_callback:
                text_class = self._last_text_class or "content-inline"
                write_callback(self._line_buffer, "dim italic", text_class, round_number)
                self._line_buffer = ""

            return self._process_tool_content(normalized, round_number), self._line_buffer

        # For text content, use line buffering
        if normalized.content_type in ("thinking", "text", "content"):
            cleaned = self._thinking_handler.process(normalized)
            if not cleaned:
                return None, self._line_buffer

            # Mark that non-tool content arrived
            self._batch_tracker.mark_content_arrived()
            self._batch_tracker.finalize_current_batch()

            text_class = "thinking-inline" if normalized.content_type == "thinking" else "content-inline"

            # Flush buffer if content type changed
            if self._last_text_class and self._last_text_class != text_class:
                if self._line_buffer.strip() and write_callback:
                    write_callback(self._line_buffer, "dim italic", self._last_text_class, round_number)
                    self._line_buffer = ""
            self._last_text_class = text_class

            # Process with line buffering
            self._line_buffer = _process_line_buffer(
                self._line_buffer,
                cleaned,
                lambda line: write_callback(line, "dim italic", text_class, round_number) if write_callback else None,
            )

            return None, self._line_buffer

        # For other content types, process normally
        return self.process(content, content_type, tool_call_id, round_number), self._line_buffer

    def flush_line_buffer(self, round_number: int = 1) -> Optional[ContentOutput]:
        """Flush any remaining content in the line buffer.

        Call this when content type changes or when finishing processing
        to ensure all content is written.

        Returns:
            ContentOutput with the buffered content, or None if buffer is empty.
        """
        if not self._line_buffer.strip():
            return None

        text_class = self._last_text_class or "content-inline"
        output = ContentOutput(
            output_type="text",
            round_number=round_number,
            text_content=self._line_buffer,
            text_style="dim italic",
            text_class=text_class,
        )
        self._line_buffer = ""
        return output

    def get_line_buffer(self) -> str:
        """Get the current line buffer content."""
        return self._line_buffer

    def get_pending_tool_count(self) -> int:
        """Get count of pending (running) tools."""
        return self._tool_handler.get_pending_count()

    # =========================================================================
    # Event Processing (for SubagentTuiModal reading events.jsonl)
    # =========================================================================

    def process_event(
        self,
        event: MassGenEvent,
        round_number: int = 1,
    ) -> Optional[ContentOutput]:
        """Process a structured MassGenEvent from events.jsonl.

        This is the entry point for processing events from the subagent's
        events.jsonl file. It handles the different event types and returns
        ContentOutput objects that can be applied to TimelineSection.

        Args:
            event: The MassGenEvent to process
            round_number: Current round number (overridden by ROUND_START events)

        Returns:
            ContentOutput with structured data for TimelineSection, or None if
            the event should be filtered out.
        """
        if event.event_type == EventType.TOOL_START:
            return self._handle_event_tool_start(event, round_number)
        elif event.event_type == EventType.TOOL_COMPLETE:
            return self._handle_event_tool_complete(event, round_number)
        elif event.event_type == EventType.THINKING:
            return self._handle_event_thinking(event, round_number)
        elif event.event_type == EventType.TEXT:
            return self._handle_event_text(event, round_number)
        elif event.event_type == EventType.STATUS:
            return self._handle_event_status(event, round_number)
        elif event.event_type == EventType.ROUND_START:
            return self._handle_event_round_start(event)
        elif event.event_type == EventType.FINAL_ANSWER:
            return self._handle_event_final_answer(event, round_number)
        elif event.event_type == EventType.STREAM_CHUNK:
            return self._handle_event_stream_chunk(event, round_number)
        return None

    def _handle_event_tool_start(
        self,
        event: MassGenEvent,
        round_number: int,
    ) -> Optional[ContentOutput]:
        """Handle tool_start event from events.jsonl."""
        tool_id = event.data.get("tool_id", "")
        tool_name = event.data.get("tool_name", "unknown")
        args = event.data.get("args", {})
        server_name = event.data.get("server_name")

        # Filter out internal coordination tools (task_plan, etc.)
        if ContentNormalizer.is_filtered_tool(tool_name):
            return None

        # Get category info for proper styling
        category_info = get_tool_category(tool_name)
        display_name = format_tool_display_name(tool_name)

        # Create args summary
        args_str = str(args) if not isinstance(args, str) else args
        args_summary = args_str[:77] + "..." if len(args_str) > 80 else args_str

        # Create ToolDisplayData
        tool_data = ToolDisplayData(
            tool_id=tool_id,
            tool_name=tool_name,
            display_name=display_name,
            tool_type="mcp" if server_name else "tool",
            category=category_info["category"],
            icon=category_info["icon"],
            color=category_info["color"],
            status="running",
            start_time=datetime.fromisoformat(event.timestamp) if event.timestamp else datetime.now(),
            args_summary=args_summary,
            args_full=args_str,
        )

        # Store tool state for completion matching
        self._event_tool_states[tool_id] = {
            "tool_data": tool_data,
            "start_time": event.timestamp,
        }

        # Determine batch action
        batch_action, batch_server, batch_id, pending_id = self._batch_tracker.process_tool(tool_data)

        return ContentOutput(
            output_type="tool",
            round_number=round_number,
            tool_data=tool_data,
            batch_action=batch_action,
            batch_id=batch_id,
            server_name=batch_server,
            pending_tool_id=pending_id,
        )

    def _handle_event_tool_complete(
        self,
        event: MassGenEvent,
        round_number: int,
    ) -> Optional[ContentOutput]:
        """Handle tool_complete event from events.jsonl."""
        tool_id = event.data.get("tool_id", "")
        tool_name = event.data.get("tool_name", "")
        result_text = event.data.get("result", "")
        elapsed = event.data.get("elapsed_seconds", 0)
        is_error = event.data.get("is_error", False)

        # Filter out internal coordination tools (task_plan, etc.)
        if tool_name and ContentNormalizer.is_filtered_tool(tool_name):
            # Clean up tool state if present
            self._event_tool_states.pop(tool_id, None)
            return None

        # Get stored tool state
        tool_state = self._event_tool_states.get(tool_id, {})
        original_data = tool_state.get("tool_data")

        if not original_data:
            # No matching start - create minimal tool data
            tool_name = event.data.get("tool_name", "unknown")
            category_info = get_tool_category(tool_name)
            display_name = format_tool_display_name(tool_name)
            original_data = ToolDisplayData(
                tool_id=tool_id,
                tool_name=tool_name,
                display_name=display_name,
                tool_type="tool",
                category=category_info["category"],
                icon=category_info["icon"],
                color=category_info["color"],
                status="running",
                start_time=datetime.now(),
            )

        # Create result summary
        result_summary = result_text[:100] + "..." if len(result_text) > 100 else result_text

        # Create updated ToolDisplayData
        tool_data = ToolDisplayData(
            tool_id=tool_id,
            tool_name=original_data.tool_name,
            display_name=original_data.display_name,
            tool_type=original_data.tool_type,
            category=original_data.category,
            icon=original_data.icon,
            color=original_data.color,
            status="error" if is_error else "success",
            start_time=original_data.start_time,
            end_time=datetime.fromisoformat(event.timestamp) if event.timestamp else datetime.now(),
            args_summary=original_data.args_summary,
            args_full=original_data.args_full,
            result_summary=result_summary,
            result_full=result_text,
            elapsed_seconds=elapsed,
        )

        # Determine batch action for completion
        batch_action, batch_server, batch_id, _ = self._batch_tracker.process_tool(tool_data)

        # Clean up tool state
        self._event_tool_states.pop(tool_id, None)

        return ContentOutput(
            output_type="tool",
            round_number=round_number,
            tool_data=tool_data,
            batch_action=batch_action,
            batch_id=batch_id,
            server_name=batch_server,
        )

    def _handle_event_thinking(
        self,
        event: MassGenEvent,
        round_number: int,
    ) -> Optional[ContentOutput]:
        """Handle thinking event from events.jsonl.

        Applies the same filtering as main TUI for visual parity.
        """
        content = event.data.get("content", "")
        if not content:
            return None

        # Apply same filtering as main TUI for parity
        normalized = ContentNormalizer.normalize(content, "thinking")
        if not normalized.should_display:
            return None

        cleaned = self._thinking_handler.process(normalized)
        if not cleaned:
            return None

        # Mark that content arrived (breaks tool batching)
        self._batch_tracker.mark_content_arrived()

        return ContentOutput(
            output_type="thinking",
            round_number=round_number,
            text_content=cleaned,
            text_style="dim italic",
            text_class="thinking-inline",
        )

    def _handle_event_text(
        self,
        event: MassGenEvent,
        round_number: int,
    ) -> Optional[ContentOutput]:
        """Handle text event from events.jsonl.

        Applies the same filtering as main TUI for visual parity.
        """
        content = event.data.get("content", "")
        if not content:
            return None

        # Apply same filtering as main TUI for parity
        normalized = ContentNormalizer.normalize(content, "text")
        if not normalized.should_display:
            return None

        cleaned = self._thinking_handler.process(normalized)
        if not cleaned:
            return None

        # Mark that content arrived
        self._batch_tracker.mark_content_arrived()

        return ContentOutput(
            output_type="text",
            round_number=round_number,
            text_content=cleaned,
            text_style="",
            text_class="content-inline",
        )

    def _handle_event_status(
        self,
        event: MassGenEvent,
        round_number: int,
    ) -> Optional[ContentOutput]:
        """Handle status event from events.jsonl."""
        message = event.data.get("message", "")
        level = event.data.get("level", "info")
        if not message:
            return None

        # Use ContentNormalizer as single source of truth for filtering
        normalized = ContentNormalizer.normalize(message, "status")
        if not normalized.should_display:
            return None

        return ContentOutput(
            output_type="status",
            round_number=round_number,
            text_content=f"[{level}] {normalized.cleaned_content}",
            text_style="dim cyan",
            text_class="status",
        )

    def _handle_event_round_start(
        self,
        event: MassGenEvent,
    ) -> Optional[ContentOutput]:
        """Handle round_start event from events.jsonl."""
        round_num = event.data.get("round_number", 1)

        return ContentOutput(
            output_type="separator",
            round_number=round_num,
            separator_label=f"Round {round_num}",
        )

    def _handle_event_final_answer(
        self,
        event: MassGenEvent,
        round_number: int,
    ) -> Optional[ContentOutput]:
        """Handle final_answer event from events.jsonl."""
        content = event.data.get("content", "")

        return ContentOutput(
            output_type="final_answer",
            round_number=round_number,
            text_content=content,
        )

    def _handle_event_stream_chunk(
        self,
        event: MassGenEvent,
        round_number: int,
    ) -> Optional[ContentOutput]:
        """Handle stream_chunk event from events.jsonl.

        Stream chunks from subagent events use different formats:
        - tool_calls: Tool call requests
        - function_call_output status: Tool results
        - mcp_status: MCP connection status
        - content: Regular text content
        """
        import json as json_module

        chunk = event.data.get("chunk", {})
        chunk_type = chunk.get("type", "unknown")
        content = chunk.get("content")
        status = chunk.get("status")
        tool_call_id = chunk.get("tool_call_id")

        # Skip non-display chunks (verbose diagnostic messages like "Arguments for Calling...")
        if not chunk.get("display", True):
            return None

        # Handle tool_calls - create tool start entries
        if chunk_type == "tool_calls":
            tool_calls = chunk.get("tool_calls", [])
            outputs = []
            for tc in tool_calls:
                tc_id = tc.get("id", "")
                func = tc.get("function", {})
                tool_name = func.get("name", "unknown")
                args_str = func.get("arguments", "{}")

                # Filter out internal coordination tools (task_plan, etc.)
                if ContentNormalizer.is_filtered_tool(tool_name):
                    continue

                # Parse arguments
                try:
                    args = json_module.loads(args_str) if isinstance(args_str, str) else args_str
                except Exception:
                    args = {"raw": args_str}

                # Extract server name from tool name
                server_name = get_mcp_server_name(tool_name)
                display_name = format_tool_display_name(tool_name)

                # Get actual tool name (strip mcp__ prefix)
                actual_tool_name = tool_name
                if tool_name.startswith("mcp__"):
                    parts = tool_name.split("__")
                    if len(parts) >= 3:
                        actual_tool_name = "__".join(parts[2:])

                # Get category info
                category_info = get_tool_category(actual_tool_name)

                # Create args summary
                args_full = str(args) if not isinstance(args, str) else args
                args_summary = args_full[:77] + "..." if len(args_full) > 80 else args_full

                # Create ToolDisplayData
                tool_data = ToolDisplayData(
                    tool_id=tc_id,
                    tool_name=actual_tool_name,
                    display_name=display_name,
                    tool_type="mcp" if server_name else "tool",
                    category=category_info["category"],
                    icon=category_info["icon"],
                    color=category_info["color"],
                    status="running",
                    start_time=datetime.fromisoformat(event.timestamp) if event.timestamp else datetime.now(),
                    args_summary=args_summary,
                    args_full=args_full,
                )

                # Store tool state
                self._event_tool_states[tc_id] = {
                    "tool_data": tool_data,
                    "start_time": event.timestamp,
                }

                # Determine batch action
                batch_action, batch_server, batch_id, pending_id = self._batch_tracker.process_tool(tool_data)

                outputs.append(
                    ContentOutput(
                        output_type="tool",
                        round_number=round_number,
                        tool_data=tool_data,
                        batch_action=batch_action,
                        batch_id=batch_id,
                        server_name=batch_server,
                        pending_tool_id=pending_id,
                    ),
                )

            # Return first output (caller should handle multiple if needed)
            # In practice, stream_chunk tool_calls are processed one at a time
            return outputs[0] if outputs else None

        # Handle tool results (function_call_output status)
        if status == "function_call_output" and tool_call_id:
            tool_state = self._event_tool_states.get(tool_call_id, {})
            original_data = tool_state.get("tool_data")

            if original_data:
                result_text = content or ""
                result_summary = result_text[:100] + "..." if len(result_text) > 100 else result_text

                # Create updated ToolDisplayData
                tool_data = ToolDisplayData(
                    tool_id=tool_call_id,
                    tool_name=original_data.tool_name,
                    display_name=original_data.display_name,
                    tool_type=original_data.tool_type,
                    category=original_data.category,
                    icon=original_data.icon,
                    color=original_data.color,
                    status="success",
                    start_time=original_data.start_time,
                    end_time=datetime.now(),
                    args_summary=original_data.args_summary,
                    args_full=original_data.args_full,
                    result_summary=result_summary,
                    result_full=result_text,
                    elapsed_seconds=0,
                )

                # Determine batch action
                batch_action, batch_server, batch_id, _ = self._batch_tracker.process_tool(tool_data)

                # Clean up
                self._event_tool_states.pop(tool_call_id, None)

                return ContentOutput(
                    output_type="tool",
                    round_number=round_number,
                    tool_data=tool_data,
                    batch_action=batch_action,
                    batch_id=batch_id,
                    server_name=batch_server,
                )
            return None

        # Handle tool status messages from MCP/custom tools (parse like main TUI)
        if chunk_type in ("mcp_status", "custom_tool_status", "tool") and content:
            return self.process(str(content), "tool", tool_call_id, round_number)

        # Handle reasoning/thinking stream chunks
        if (
            chunk_type
            in (
                "reasoning",
                "reasoning_done",
                "reasoning_summary",
                "reasoning_summary_done",
                "thinking",
            )
            and content
        ):
            return self.process(str(content), "thinking", tool_call_id, round_number)

        # Handle MCP status messages
        if chunk_type in ("mcp_status", "ChunkType.MCP_STATUS") and content:
            # Skip function_call_output (handled above) and tool call status
            if status in ("function_call_output", "mcp_tool_called"):
                return None

            # Use ContentNormalizer as single source of truth for filtering
            normalized = ContentNormalizer.normalize(content, "status")
            if not normalized.should_display:
                return None

            return ContentOutput(
                output_type="status",
                round_number=round_number,
                text_content=normalized.cleaned_content,
                text_style="dim cyan",
                text_class="status",
            )

        # Handle generic status chunks
        if chunk_type in ("status", "backend_status", "system_status") and content:
            return self.process(str(content), "status", tool_call_id, round_number)

        # Handle regular content
        if chunk_type in ("content", "text") and content:
            # Apply same filtering as main TUI for parity
            normalized = ContentNormalizer.normalize(content, "text")
            if not normalized.should_display:
                return None

            cleaned = self._thinking_handler.process(normalized)
            if not cleaned:
                return None

            self._batch_tracker.mark_content_arrived()
            return ContentOutput(
                output_type="text",
                round_number=round_number,
                text_content=cleaned,
                text_style="",
                text_class="content-inline",
            )

        return None

    def flush_pending_batch(self, round_number: int = 1) -> Optional[ContentOutput]:
        """Flush any pending tool batch and return it.

        Call this when done processing events to finalize any incomplete batch.

        Returns:
            ContentOutput with batch data, or None if no pending batch.
        """
        batch_id = self._batch_tracker.finalize_current_batch()
        if batch_id and self._event_pending_batch:
            tools = self._event_pending_batch.copy()
            self._event_pending_batch.clear()
            return ContentOutput(
                output_type="tool_batch",
                round_number=round_number,
                batch_tools=tools,
                batch_id=batch_id,
            )
        return None


def _process_line_buffer(
    buffer: str,
    new_content: str,
    write_callback: Callable[[str], None],
) -> str:
    """Process content through line buffer, writing complete lines.

    This function accumulates content until a newline is received,
    then calls the write callback for each complete line.

    Args:
        buffer: Current buffer content
        new_content: New content to add
        write_callback: Callback to write complete lines

    Returns:
        Remaining buffer content (incomplete line)
    """
    buffer += new_content

    # Process complete lines
    while "\n" in buffer:
        line, buffer = buffer.split("\n", 1)
        if line:  # Skip empty lines
            write_callback(line)

    return buffer
