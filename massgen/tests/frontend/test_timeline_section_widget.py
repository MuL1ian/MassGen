# -*- coding: utf-8 -*-
"""Widget-level tests for timeline rendering with Textual Pilot."""

from datetime import datetime, timezone

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Static

from massgen.events import EventType, MassGenEvent
from massgen.frontend.displays.content_handlers import ToolDisplayData
from massgen.frontend.displays.textual_widgets.collapsible_text_card import (
    CollapsibleTextCard,
)
from massgen.frontend.displays.textual_widgets.content_sections import (
    RestartBanner,
    TimelineSection,
)
from massgen.frontend.displays.textual_widgets.tool_batch_card import ToolBatchCard
from massgen.frontend.displays.textual_widgets.tool_card import ToolCallCard
from massgen.frontend.displays.tui_event_pipeline import TimelineEventAdapter


class _TimelineApp(App):
    def compose(self) -> ComposeResult:
        yield TimelineSection(id="timeline")


class _PanelStub:
    def __init__(self, timeline: TimelineSection) -> None:
        self._timeline = timeline
        self.agent_id = "agent_a"

    def _get_timeline(self) -> TimelineSection:
        return self._timeline


def _make_tool(tool_id: str, tool_name: str) -> ToolDisplayData:
    return ToolDisplayData(
        tool_id=tool_id,
        tool_name=tool_name,
        display_name=tool_name,
        tool_type="mcp" if tool_name.startswith("mcp__") else "tool",
        category="filesystem",
        icon="F",
        color="blue",
        status="running",
        start_time=datetime.now(timezone.utc),
    )


def _content_children(timeline: TimelineSection) -> list:
    return [child for child in timeline.children if child.id != "scroll_mode_indicator"]


@pytest.mark.asyncio
async def test_deferred_round_banner_renders_before_first_round_content():
    app = _TimelineApp()
    async with app.run_test(headless=True) as pilot:
        timeline = app.query_one(TimelineSection)

        timeline.defer_round_banner(2, "Round 2", "Restart: new answer received")
        await pilot.pause()
        assert not any(isinstance(child, RestartBanner) for child in _content_children(timeline))

        timeline.add_text("resuming", text_class="status", round_number=2)
        await pilot.pause()

        children = _content_children(timeline)
        assert isinstance(children[0], RestartBanner)
        assert "Round 2" in children[0].render().plain
        assert "Restart: new answer received" in children[0].render().plain
        assert "round-2" in children[0].classes
        assert "round-2" in children[1].classes


@pytest.mark.asyncio
async def test_convert_tool_to_batch_replaces_standalone_card():
    app = _TimelineApp()
    async with app.run_test(headless=True) as pilot:
        timeline = app.query_one(TimelineSection)

        timeline.add_tool(_make_tool("t1", "mcp__filesystem__read_text_file"), round_number=1)
        await pilot.pause()
        assert timeline.get_tool("t1") is not None
        assert len(list(timeline.query(ToolCallCard))) == 1

        batch = timeline.convert_tool_to_batch(
            "t1",
            _make_tool("t2", "mcp__filesystem__write_file"),
            "batch_1",
            "filesystem",
            round_number=1,
        )
        await pilot.pause()

        assert batch is not None
        assert isinstance(batch, ToolBatchCard)
        assert timeline.get_tool("t1") is None
        assert timeline.get_tool_batch("t1") == "batch_1"
        assert timeline.get_tool_batch("t2") == "batch_1"
        assert batch.tool_count == 2
        assert batch.has_tool("t1")
        assert batch.has_tool("t2")
        assert len(list(timeline.query(ToolCallCard))) == 0
        assert len(list(timeline.query(ToolBatchCard))) == 1


@pytest.mark.asyncio
async def test_event_adapter_batches_consecutive_mcp_tools_in_widget_timeline():
    app = _TimelineApp()
    async with app.run_test(headless=True) as pilot:
        timeline = app.query_one(TimelineSection)
        adapter = TimelineEventAdapter(_PanelStub(timeline))

        adapter.handle_event(
            MassGenEvent.create(
                EventType.TOOL_START,
                agent_id="agent_a",
                tool_id="t1",
                tool_name="mcp__filesystem__read_text_file",
                args={"path": "/tmp/a.txt"},
                server_name="filesystem",
            ),
        )
        adapter.handle_event(
            MassGenEvent.create(
                EventType.TOOL_START,
                agent_id="agent_a",
                tool_id="t2",
                tool_name="mcp__filesystem__write_file",
                args={"path": "/tmp/b.txt"},
                server_name="filesystem",
            ),
        )
        adapter.handle_event(
            MassGenEvent.create(
                EventType.TOOL_COMPLETE,
                agent_id="agent_a",
                tool_id="t2",
                tool_name="mcp__filesystem__write_file",
                result="ok",
                elapsed_seconds=0.01,
                is_error=False,
            ),
        )
        await pilot.pause()

        batch = timeline.get_batch("batch_1")
        assert batch is not None
        assert batch.tool_count == 2
        assert batch.get_tool("t2") is not None
        assert batch.get_tool("t2").status == "success"
        assert timeline.get_tool_batch("t1") == "batch_1"
        assert timeline.get_tool_batch("t2") == "batch_1"


@pytest.mark.asyncio
async def test_event_adapter_does_not_batch_when_text_arrives_between_tools():
    app = _TimelineApp()
    async with app.run_test(headless=True) as pilot:
        timeline = app.query_one(TimelineSection)
        adapter = TimelineEventAdapter(_PanelStub(timeline))

        adapter.handle_event(
            MassGenEvent.create(
                EventType.TOOL_START,
                agent_id="agent_a",
                tool_id="t1",
                tool_name="mcp__filesystem__read_text_file",
                args={"path": "/tmp/a.txt"},
                server_name="filesystem",
            ),
        )
        adapter.handle_event(MassGenEvent.create(EventType.TEXT, agent_id="agent_a", content="thinking"))
        adapter.handle_event(
            MassGenEvent.create(
                EventType.TOOL_START,
                agent_id="agent_a",
                tool_id="t2",
                tool_name="mcp__filesystem__write_file",
                args={"path": "/tmp/b.txt"},
                server_name="filesystem",
            ),
        )
        await pilot.pause()

        assert timeline.get_batch("batch_1") is None
        assert timeline.get_tool("t1") is not None
        assert timeline.get_tool("t2") is not None
        assert timeline.get_tool_batch("t1") is None
        assert timeline.get_tool_batch("t2") is None


@pytest.mark.asyncio
async def test_round_separator_dedup_keeps_single_banner():
    app = _TimelineApp()
    async with app.run_test(headless=True) as pilot:
        timeline = app.query_one(TimelineSection)

        timeline.add_separator("Round 2", round_number=2)
        timeline.add_separator("Round 2", round_number=2)
        await pilot.pause()

        round_2_banners = [child for child in _content_children(timeline) if isinstance(child, RestartBanner) and "round-2" in child.classes]
        assert len(round_2_banners) == 1


@pytest.mark.asyncio
async def test_thinking_text_batches_into_single_collapsible_card():
    app = _TimelineApp()
    async with app.run_test(headless=True) as pilot:
        timeline = app.query_one(TimelineSection)

        timeline.add_text("thinking one ", text_class="thinking-inline", round_number=1)
        timeline.add_text("thinking two", text_class="thinking-inline", round_number=1)
        await pilot.pause()

        cards = list(timeline.query(CollapsibleTextCard))
        assert len(cards) == 1
        assert cards[0].label == "Thinking"
        assert cards[0].chunk_count == 1
        assert cards[0].content == "thinking one thinking two"


@pytest.mark.asyncio
async def test_lock_and_unlock_final_answer_toggles_visibility_classes():
    app = _TimelineApp()
    async with app.run_test(headless=True) as pilot:
        timeline = app.query_one(TimelineSection)

        timeline.add_widget(Static("intermediate", id="middle_card"), round_number=1)
        timeline.add_widget(Static("final", id="final_card"), round_number=1)
        await pilot.pause()

        timeline.lock_to_final_answer("final_card")
        await pilot.pause()
        assert timeline.is_answer_locked

        final_card = timeline.query_one("#final_card", Static)
        middle_card = timeline.query_one("#middle_card", Static)
        assert "answer-lock-hidden" not in final_card.classes
        assert "answer-lock-hidden" in middle_card.classes
        assert "final-card-locked" in final_card.classes or "final-card-compact" in final_card.classes

        timeline.unlock_final_answer()
        await pilot.pause()
        assert not timeline.is_answer_locked
        assert "answer-lock-hidden" not in middle_card.classes
        assert "final-card-locked" not in final_card.classes
        assert "final-card-compact" not in final_card.classes


@pytest.mark.asyncio
async def test_final_presentation_separator_prevents_extra_round_banner():
    app = _TimelineApp()
    async with app.run_test(headless=True) as pilot:
        timeline = app.query_one(TimelineSection)
        adapter = TimelineEventAdapter(_PanelStub(timeline))

        adapter.handle_event(
            MassGenEvent.create(
                EventType.FINAL_PRESENTATION_START,
                agent_id="agent_a",
                vote_counts={"agent_a": 1},
                answer_labels={"agent_a": "A1.1"},
                is_tie=False,
            ),
        )
        adapter.handle_event(
            MassGenEvent.create(
                EventType.TOOL_START,
                agent_id="agent_a",
                tool_id="t_final_1",
                tool_name="Read",
                args={"file_path": "/tmp/final.txt"},
                server_name=None,
            ),
        )
        await pilot.pause()

        round_2_banners = [child for child in _content_children(timeline) if isinstance(child, RestartBanner) and "round-2" in child.classes]
        assert len(round_2_banners) == 1
        assert "Final Answer" in round_2_banners[0].render().plain
        assert "Round 2" not in round_2_banners[0].render().plain
