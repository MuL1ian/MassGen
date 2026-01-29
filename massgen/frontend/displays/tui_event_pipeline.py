# -*- coding: utf-8 -*-
"""
Unified TUI event pipeline adapter.

Bridges MassGen events (including stream chunks) into TimelineSection updates
using ContentProcessor as the single source of truth for parsing.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from massgen.events import EventType, MassGenEvent

from .content_processor import ContentOutput, ContentProcessor


class TimelineEventAdapter:
    """Apply MassGen events to a TimelineSection with shared parsing logic.

    This adapter is used by both the main TUI and subagent views to ensure
    parity. It handles stream chunk events (line-buffered) and structured
    events, and applies ContentOutput updates to the timeline.
    """

    def __init__(
        self,
        panel: Any,
        *,
        agent_id: Optional[str] = None,
        on_output_applied: Optional[Callable[[ContentOutput], None]] = None,
    ) -> None:
        self._panel = panel
        self._agent_id = agent_id or getattr(panel, "agent_id", None)
        self._processor = ContentProcessor()
        self._round_number = 1
        self._tool_count = 0
        self._final_answer: Optional[str] = None
        self._on_output_applied = on_output_applied

    @property
    def round_number(self) -> int:
        return self._round_number

    @property
    def final_answer(self) -> Optional[str]:
        return self._final_answer

    def reset(self) -> None:
        """Reset parser state (e.g., when switching agents)."""
        self._processor.reset()
        self._round_number = 1
        self._tool_count = 0
        self._final_answer = None

    def set_round_number(self, round_number: int) -> None:
        """Set the current round number (e.g., on restart)."""
        self._round_number = max(1, int(round_number))

    def handle_stream_content(
        self,
        content: str,
        content_type: str,
        tool_call_id: Optional[str] = None,
        *,
        source: Optional[str] = None,
    ) -> None:
        """Handle raw stream content from the main TUI buffer."""
        if content is None:
            return
        chunk = {
            "type": content_type,
            "content": content,
            "tool_call_id": tool_call_id,
            "source": source or self._agent_id,
            "display": True,
        }
        event = MassGenEvent.create(
            event_type=EventType.STREAM_CHUNK,
            agent_id=self._agent_id,
            chunk=chunk,
        )
        self.handle_event(event)

    def handle_event(self, event: MassGenEvent) -> None:
        """Process a MassGen event and update the timeline."""
        if event.event_type == EventType.STREAM_CHUNK:
            self._handle_stream_chunk(event)
            return

        output = self._processor.process_event(event, self._round_number)
        if output and output.output_type != "skip":
            self._apply_output(output)

    def flush(self) -> None:
        """Flush any buffered text or pending tool batches."""
        buffered = self._processor.flush_line_buffer(self._round_number)
        if buffered and buffered.output_type != "skip":
            self._apply_output(buffered)

        batch = self._processor.flush_pending_batch(self._round_number)
        if batch:
            self._apply_output(batch)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_timeline(self) -> Optional[Any]:
        if hasattr(self._panel, "_get_timeline"):
            return self._panel._get_timeline()
        return None

    def _handle_stream_chunk(self, event: MassGenEvent) -> None:
        data = event.data or {}
        chunk = data.get("chunk")
        if isinstance(chunk, dict):
            chunk_dict = chunk
        elif isinstance(data, dict):
            chunk_dict = data
        else:
            return

        if not chunk_dict.get("display", True):
            return

        chunk_type = chunk_dict.get("type", "")
        content = chunk_dict.get("content")
        status = chunk_dict.get("status")
        tool_call_id = chunk_dict.get("tool_call_id")

        # Structured tool calls / function outputs (Responses API)
        if chunk_type == "tool_calls" or (status == "function_call_output" and tool_call_id):
            output = self._processor.process_event(event, self._round_number)
            if output and output.output_type != "skip":
                self._apply_output(output)
            return

        # Map chunk types to ContentNormalizer raw types
        raw_type = self._map_chunk_type(chunk_type)
        if raw_type is None:
            return

        if content is None:
            return

        # Route through line-buffered processing for parity with main TUI
        output, _ = self._processor.process_line_buffered(
            str(content),
            raw_type,
            tool_call_id,
            self._round_number,
            write_callback=self._write_line,
        )
        if output and output.output_type != "skip":
            self._apply_output(output)

        # Update any legacy line buffer display if present
        if hasattr(self._panel, "current_line_label"):
            try:
                self._panel.current_line_label.update(self._processor.get_line_buffer())
            except Exception:
                pass

    def _map_chunk_type(self, chunk_type: str) -> Optional[str]:
        chunk_type = (chunk_type or "").lower()
        if chunk_type in ("mcp_status", "custom_tool_status", "tool"):
            return "tool"
        if "mcp_status" in chunk_type or "custom_tool_status" in chunk_type:
            return "tool"
        if chunk_type in (
            "reasoning",
            "reasoning_done",
            "reasoning_summary",
            "reasoning_summary_done",
            "thinking",
        ):
            return "thinking"
        if chunk_type in ("content", "text"):
            return "content"
        if chunk_type in ("status", "system_status", "backend_status", "agent_status", "compression_status", "error"):
            return "status"
        if chunk_type in ("presentation", "final_answer"):
            return "presentation"
        return None

    def _write_line(self, text: str, style: str, text_class: str, round_number: int) -> None:
        timeline = self._get_timeline()
        if timeline is None:
            return
        try:
            timeline.add_text(
                text,
                style=style,
                text_class=text_class,
                round_number=round_number,
            )
        except Exception:
            pass

    def _apply_output(self, output: ContentOutput) -> None:
        timeline = self._get_timeline()
        if timeline is None:
            return

        if hasattr(self._panel, "_hide_loading"):
            try:
                self._panel._hide_loading()
            except Exception:
                pass

        round_number = output.round_number or self._round_number

        if output.output_type == "tool" and output.tool_data:
            self._apply_tool_output(output, round_number, timeline)
        elif output.output_type == "tool_batch" and output.batch_tools:
            self._tool_count += len(output.batch_tools)
            batch_id = output.batch_id or f"batch_{self._tool_count}"
            server_name = output.server_name or "tools"
            try:
                timeline.add_batch(batch_id, server_name, round_number=round_number)
                for tool_data in output.batch_tools:
                    timeline.add_tool_to_batch(batch_id, tool_data)
                    if tool_data.status in ("success", "error"):
                        timeline.update_tool_in_batch(tool_data.tool_id, tool_data)
            except Exception:
                pass
        elif output.output_type in ("thinking", "text", "status", "presentation") and output.text_content:
            try:
                timeline.add_text(
                    output.text_content,
                    style=output.text_style,
                    text_class=output.text_class or "content-inline",
                    round_number=round_number,
                )
            except Exception:
                pass
        elif output.output_type == "injection":
            if output.normalized is not None and hasattr(self._panel, "_add_injection_content"):
                try:
                    self._panel._add_injection_content(output.normalized)
                except Exception:
                    pass
            elif output.text_content:
                try:
                    timeline.add_text(
                        output.text_content,
                        style=output.text_style,
                        text_class=output.text_class or "injection",
                        round_number=round_number,
                    )
                except Exception:
                    pass
        elif output.output_type == "reminder":
            if output.normalized is not None and hasattr(self._panel, "_add_reminder_content"):
                try:
                    self._panel._add_reminder_content(output.normalized)
                except Exception:
                    pass
            elif output.text_content:
                try:
                    timeline.add_text(
                        output.text_content,
                        style=output.text_style,
                        text_class=output.text_class or "reminder",
                        round_number=round_number,
                    )
                except Exception:
                    pass
        elif output.output_type == "separator":
            self._round_number = output.round_number or self._round_number
            if hasattr(self._panel, "start_new_round"):
                try:
                    self._panel.start_new_round(self._round_number, is_context_reset=False)
                except Exception:
                    pass
            else:
                try:
                    timeline.add_separator(
                        output.separator_label,
                        round_number=self._round_number,
                        subtitle=output.separator_subtitle,
                    )
                except Exception:
                    pass
        elif output.output_type == "final_answer" and output.text_content:
            self._final_answer = output.text_content
            try:
                timeline.add_text(
                    f"✓ FINAL ANSWER\n{output.text_content}",
                    style="bold green",
                    text_class="final-answer",
                    round_number=round_number,
                )
            except Exception:
                pass

        if self._on_output_applied:
            try:
                self._on_output_applied(output)
            except Exception:
                pass

    def _apply_tool_output(self, output: ContentOutput, round_number: int, timeline: Any) -> None:
        tool_data = output.tool_data
        if tool_data is None:
            return

        is_planning_tool = False
        if hasattr(self._panel, "_is_planning_mcp_tool"):
            try:
                is_planning_tool = self._panel._is_planning_mcp_tool(tool_data.tool_name)
            except Exception:
                is_planning_tool = False

        is_subagent_tool = False
        if hasattr(self._panel, "_is_subagent_tool"):
            try:
                is_subagent_tool = self._panel._is_subagent_tool(tool_data.tool_name)
            except Exception:
                is_subagent_tool = False

        skip_batching = is_planning_tool or is_subagent_tool

        if tool_data.status == "running":
            try:
                existing_card = timeline.get_tool(tool_data.tool_id)
            except Exception:
                existing_card = None
            try:
                existing_batch = timeline.get_tool_batch(tool_data.tool_id) if not skip_batching else None
            except Exception:
                existing_batch = None

            if existing_card:
                if tool_data.args_summary:
                    try:
                        existing_card.set_params(tool_data.args_summary, tool_data.args_full)
                    except Exception:
                        pass
            elif existing_batch:
                try:
                    timeline.update_tool_in_batch(tool_data.tool_id, tool_data)
                except Exception:
                    pass
            elif is_subagent_tool and hasattr(self._panel, "_show_subagent_card_from_args"):
                try:
                    self._panel._show_subagent_card_from_args(tool_data, timeline)
                except Exception:
                    pass
            elif is_planning_tool:
                pass
            else:
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
                else:
                    timeline.add_tool(tool_data, round_number=round_number)
        else:
            if not is_planning_tool and not is_subagent_tool:
                if output.batch_action == "update_batch":
                    try:
                        timeline.update_tool_in_batch(tool_data.tool_id, tool_data)
                    except Exception:
                        timeline.update_tool(tool_data.tool_id, tool_data)
                else:
                    timeline.update_tool(tool_data.tool_id, tool_data)

            if tool_data.status == "success":
                if hasattr(self._panel, "_check_and_display_task_plan"):
                    try:
                        self._panel._check_and_display_task_plan(tool_data, timeline)
                    except Exception:
                        pass
                if is_subagent_tool and hasattr(self._panel, "_update_subagent_card_with_results"):
                    try:
                        self._panel._update_subagent_card_with_results(tool_data, timeline)
                    except Exception:
                        pass

                tool_name_lower = tool_data.tool_name.lower()
                if "new_answer" in tool_name_lower or "vote" in tool_name_lower:
                    if hasattr(self._panel, "mark_terminal_tool_complete"):
                        try:
                            self._panel.mark_terminal_tool_complete()
                        except Exception:
                            pass

            if tool_data.status == "background" and hasattr(self._panel, "_refresh_header"):
                try:
                    self._panel._refresh_header()
                except Exception:
                    pass

        if hasattr(self._panel, "_update_running_tools_count"):
            try:
                self._panel._update_running_tools_count()
            except Exception:
                pass
