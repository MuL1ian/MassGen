# -*- coding: utf-8 -*-
"""
Unified TUI event pipeline adapter.

Bridges structured MassGen events into TimelineSection updates
using ContentProcessor as the single source of truth for parsing.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from massgen.events import MassGenEvent

from .content_processor import ContentOutput, ContentProcessor


class TimelineEventAdapter:
    """Apply MassGen events to a TimelineSection with shared parsing logic.

    This adapter is used by both the main TUI and subagent views to ensure
    parity. It handles structured events and applies ContentOutput updates
    to the timeline.
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
        self._last_separator_round = 0
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
        self._last_separator_round = 0

    def set_round_number(self, round_number: int) -> None:
        """Set the current round number (e.g., on restart)."""
        self._round_number = max(1, int(round_number))

    def handle_event(self, event: MassGenEvent) -> None:
        """Process a MassGen event and update the timeline."""
        output = self._processor.process_event(event, self._round_number)
        if not output:
            return
        if isinstance(output, list):
            for item in output:
                if item and item.output_type != "skip":
                    self._apply_output(item)
            return
        if output.output_type != "skip":
            self._apply_output(output)

    def flush(self) -> None:
        """Flush any pending tool batches."""
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
        elif output.output_type == "thinking_done":
            # Close the current reasoning batch so the next summary starts fresh
            try:
                if hasattr(timeline, "_close_reasoning_batch"):
                    timeline._close_reasoning_batch()
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
            round_number = output.round_number or self._round_number
            label = output.separator_label or ""
            if label.startswith("Round ") and round_number <= self._last_separator_round:
                return
            if label.startswith("Round "):
                self._last_separator_round = round_number
            self._round_number = round_number
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
            # Store for retrieval but don't render inline — a dedicated
            # final answer card handles display separately.
            self._final_answer = output.text_content
        elif output.output_type == "final_presentation_start":
            self._apply_final_presentation_start(output, round_number, timeline)
        elif output.output_type == "final_presentation_chunk":
            self._apply_final_presentation_chunk(output)
        elif output.output_type == "final_presentation_end":
            self._apply_final_presentation_end(output)
        elif output.output_type == "answer_locked":
            self._apply_answer_locked(output, timeline)

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
                # Check if this tool already exists in the timeline
                try:
                    existing = timeline.get_tool(tool_data.tool_id)
                except Exception:
                    existing = None

                if existing is None:
                    # Tool arrived already completed (e.g., coordination events
                    # like workspace/vote and workspace/new_answer). Add it
                    # and immediately update so it shows the correct status
                    # (green checkmark) instead of staying at "running" (orange dot).
                    timeline.add_tool(tool_data, round_number=round_number)
                    timeline.update_tool(tool_data.tool_id, tool_data)
                elif output.batch_action == "update_batch":
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

    # --- Final presentation / answer lock handlers ---

    def _apply_final_presentation_start(
        self,
        output: ContentOutput,
        round_number: int,
        timeline: Any,
    ) -> None:
        """Create a FinalPresentationCard and mount it in the timeline.

        Skips if a card was already created by the StreamChunk pipeline
        (show_final_presentation_start) to avoid double-rendering.
        """
        # Check if a FinalPresentationCard already exists in this timeline
        if getattr(self, "_final_presentation_card", None) is not None:
            return
        try:
            from .textual_widgets.content_sections import FinalPresentationCard

            existing = timeline.query(FinalPresentationCard)
            if existing:
                # Card was already created by the StreamChunk pipeline
                self._final_presentation_card = existing.first()
                return
        except Exception:
            pass

        extra = output.extra or {}
        agent_id = extra.get("agent_id", self._agent_id or "")
        vote_counts = extra.get("vote_counts", {})
        answer_labels = extra.get("answer_labels", {})
        is_tie = extra.get("is_tie", False)

        # Build formatted vote results matching the format MassGenApp uses
        formatted_vote_results = {
            "vote_counts": {answer_labels.get(aid, aid): cnt for aid, cnt in vote_counts.items()} if vote_counts else {},
            "winner": answer_labels.get(agent_id, agent_id),
            "is_tie": is_tie,
        }

        try:
            from .textual_widgets.content_sections import FinalPresentationCard

            card = FinalPresentationCard(
                agent_id=agent_id,
                vote_results=formatted_vote_results,
                id="final_presentation_card",
            )
            card.add_class(f"round-{round_number}")
            if extra.get("completion_only"):
                card.add_class("completion-only")
            timeline.mount(card)
            self._final_presentation_card = card
        except Exception:
            pass

    def _apply_final_presentation_chunk(self, output: ContentOutput) -> None:
        """Stream content into the FinalPresentationCard."""
        card = getattr(self, "_final_presentation_card", None)
        if card and output.text_content:
            try:
                card.append_content(output.text_content)
            except Exception:
                pass

    def _apply_final_presentation_end(self, output: ContentOutput) -> None:
        """Mark the FinalPresentationCard as complete."""
        card = getattr(self, "_final_presentation_card", None)
        if card:
            try:
                card.set_post_eval_status("verified")
                card.complete()
            except Exception:
                pass

    def _apply_answer_locked(self, output: ContentOutput, timeline: Any) -> None:
        """Lock the timeline to the final answer."""
        card = getattr(self, "_final_presentation_card", None)
        try:
            if hasattr(timeline, "lock_to_final_answer"):
                timeline.lock_to_final_answer("final_presentation_card")
            if card and hasattr(card, "set_locked_mode"):
                card.set_locked_mode(True)
        except Exception:
            pass
