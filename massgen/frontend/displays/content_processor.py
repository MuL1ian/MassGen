# -*- coding: utf-8 -*-
"""
Unified Content Processor for MassGen TUI.

Provides a single source of truth for content processing logic, used by both
the main TUI (AgentPanel) and SubagentTuiModal. This ensures:
- Visual parity between main TUI and subagent modal
- No duplicate code to maintain
- Automatic propagation of improvements

Design Philosophy:
- Process structured events into data for TimelineSection
- Respect Timeline Chronology Rule: tools only batch when consecutive
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from massgen.events import EventType, MassGenEvent

from .content_handlers import (
    ThinkingContentHandler,
    ToolBatchTracker,
    ToolDisplayData,
    format_tool_display_name,
    get_tool_category,
)
from .content_normalizer import ContentNormalizer, NormalizedContent
from .task_plan_support import is_planning_tool

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
    - Tool event lifecycle tracking via structured events
    - Tool batching logic (Timeline Chronology Rule) via ToolBatchTracker
    - Thinking/content filtering via ThinkingContentHandler

    Usage:
        processor = ContentProcessor()

        # For structured events
        output = processor.process_event(event, round_number)
        if output and output.output_type != "skip":
            timeline.apply_output(output)
    """

    def __init__(self) -> None:
        # Content handlers (shared logic)
        self._thinking_handler = ThinkingContentHandler()
        self._batch_tracker = ToolBatchTracker()

        # Counter for tracking events (debugging)
        self._event_counter = 0

        # Event processing state
        self._event_tool_states: Dict[str, Dict[str, Any]] = {}
        self._event_pending_batch: List[ToolDisplayData] = []
        self._event_round_number: int = 1

    def reset(self) -> None:
        """Reset processor state (e.g., for new session/round)."""
        self._batch_tracker.reset()
        self._event_counter = 0
        self._event_tool_states.clear()
        self._event_pending_batch.clear()
        self._event_round_number = 1

    def get_pending_tool_count(self) -> int:
        """Get count of pending (running) tools."""
        return len(self._event_tool_states)

    # =========================================================================
    # Event Processing
    # =========================================================================

    def process_event(
        self,
        event: MassGenEvent,
        round_number: int = 1,
    ) -> Optional[Union[ContentOutput, List[ContentOutput]]]:
        """Process a structured MassGenEvent.

        This is the entry point for processing events. It handles the different
        event types and returns ContentOutput objects that can be applied to
        TimelineSection.

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
            # Legacy STREAM_CHUNK events — skip gracefully
            return None
        elif event.event_type == EventType.WORKSPACE_ACTION:
            return self._handle_event_workspace_action(event, round_number)
        elif event.event_type == EventType.RESTART_BANNER:
            return self._handle_event_restart_banner(event, round_number)
        elif event.event_type == EventType.PRESENTATION_START:
            return self._handle_event_presentation_start(event, round_number)
        elif event.event_type == EventType.AGENT_RESTART:
            return self._handle_event_agent_restart(event, round_number)
        elif event.event_type == EventType.PHASE_CHANGE:
            return self._handle_event_phase_change(event, round_number)
        return None

    def _handle_event_tool_start(
        self,
        event: MassGenEvent,
        round_number: int,
    ) -> Optional[ContentOutput]:
        """Handle tool_start event."""
        tool_id = event.data.get("tool_id", "")
        tool_name = event.data.get("tool_name", "unknown")
        args = event.data.get("args", {})
        server_name = event.data.get("server_name")

        # Filter out internal coordination tools (task_plan, etc.),
        # but keep planning tools so task plans can update.
        if ContentNormalizer.is_filtered_tool(tool_name) and not is_planning_tool(tool_name):
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
        """Handle tool_complete event."""
        tool_id = event.data.get("tool_id", "")
        tool_name = event.data.get("tool_name", "")
        result_text = event.data.get("result", "")
        elapsed = event.data.get("elapsed_seconds", 0)
        is_error = event.data.get("is_error", False)

        # Filter out internal coordination tools (task_plan, etc.),
        # but keep planning tools so task plans can update.
        if tool_name and ContentNormalizer.is_filtered_tool(tool_name) and not is_planning_tool(tool_name):
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
            error=result_text if is_error else None,
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
        """Handle thinking event.

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
        """Handle text event.

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
        """Handle status event."""
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
        """Handle round_start event."""
        # round_number is a top-level field on MassGenEvent, not in data
        round_num = event.round_number

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
        """Handle final_answer event."""
        content = event.data.get("content", "")

        return ContentOutput(
            output_type="final_answer",
            round_number=round_number,
            text_content=content,
        )

    def _handle_event_workspace_action(
        self,
        event: MassGenEvent,
        round_number: int,
    ) -> Optional[ContentOutput]:
        """Handle workspace_action event."""
        action_type = event.data.get("action_type", "unknown")
        params = event.data.get("params")
        label = f"workspace/{action_type}"
        if params:
            label += f" {params}"

        self._batch_tracker.mark_content_arrived()
        return ContentOutput(
            output_type="status",
            round_number=round_number,
            text_content=f"🔧 {label}",
            text_style="dim cyan",
            text_class="status",
        )

    def _handle_event_restart_banner(
        self,
        event: MassGenEvent,
        round_number: int,
    ) -> Optional[ContentOutput]:
        """Handle restart_banner event."""
        attempt = event.data.get("attempt", 1)
        max_attempts = event.data.get("max_attempts", 3)
        reason = event.data.get("reason", "")

        return ContentOutput(
            output_type="separator",
            round_number=attempt,
            separator_label=f"Restart Attempt {attempt}/{max_attempts}",
            separator_subtitle=reason,
        )

    def _handle_event_presentation_start(
        self,
        event: MassGenEvent,
        round_number: int,
    ) -> Optional[ContentOutput]:
        """Handle presentation_start event."""
        self._batch_tracker.mark_content_arrived()
        return ContentOutput(
            output_type="separator",
            round_number=round_number,
            separator_label="Final Presentation",
            separator_subtitle="",
        )

    def _handle_event_agent_restart(
        self,
        event: MassGenEvent,
        round_number: int,
    ) -> Optional[ContentOutput]:
        """Handle agent_restart event."""
        agent_round = event.data.get("restart_round", round_number)

        return ContentOutput(
            output_type="separator",
            round_number=agent_round,
            separator_label=f"Round {agent_round}",
            separator_subtitle="Agent restart",
        )

    def _handle_event_phase_change(
        self,
        event: MassGenEvent,
        round_number: int,
    ) -> Optional[ContentOutput]:
        """Handle phase_change event."""
        phase = event.data.get("phase", "unknown")

        return ContentOutput(
            output_type="status",
            round_number=round_number,
            text_content=f"Phase: {phase}",
            text_style="dim cyan",
            text_class="status",
        )

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
