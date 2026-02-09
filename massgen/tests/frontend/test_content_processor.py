# -*- coding: utf-8 -*-
"""Unit tests for ContentProcessor event handling."""

from massgen.events import EventType, MassGenEvent
from massgen.frontend.displays.content_processor import ContentProcessor


def test_tool_start_creates_tool_output():
    processor = ContentProcessor()
    event = MassGenEvent.create(
        EventType.TOOL_START,
        agent_id="agent_a",
        tool_id="t1",
        tool_name="mcp__filesystem__read_text_file",
        args={"path": "/tmp/a.txt"},
        server_name="filesystem",
    )

    output = processor.process_event(event, round_number=1)
    assert output is not None
    assert output.output_type == "tool"
    assert output.tool_data is not None
    assert output.tool_data.status == "running"
    assert output.batch_action == "pending"


def test_status_info_level_is_skipped():
    processor = ContentProcessor()
    event = MassGenEvent.create(
        EventType.STATUS,
        agent_id="agent_a",
        message="Voting complete",
        level="info",
    )

    assert processor.process_event(event, round_number=1) is None


def test_thinking_whitespace_is_filtered():
    processor = ContentProcessor()
    event = MassGenEvent.create(
        EventType.THINKING,
        agent_id="agent_a",
        content="   ",
    )

    assert processor.process_event(event, round_number=1) is None


def test_two_consecutive_tools_convert_to_batch():
    processor = ContentProcessor()

    first = MassGenEvent.create(
        EventType.TOOL_START,
        agent_id="agent_a",
        tool_id="t1",
        tool_name="mcp__filesystem__read_text_file",
        args={"path": "/tmp/a.txt"},
        server_name="filesystem",
    )
    second = MassGenEvent.create(
        EventType.TOOL_START,
        agent_id="agent_a",
        tool_id="t2",
        tool_name="mcp__filesystem__write_file",
        args={"path": "/tmp/b.txt"},
        server_name="filesystem",
    )

    first_out = processor.process_event(first, round_number=1)
    second_out = processor.process_event(second, round_number=1)

    assert first_out is not None and first_out.batch_action == "pending"
    assert second_out is not None and second_out.batch_action == "convert_to_batch"
    assert second_out.pending_tool_id == "t1"


def test_content_between_tools_prevents_batch_conversion():
    processor = ContentProcessor()

    first_tool = MassGenEvent.create(
        EventType.TOOL_START,
        agent_id="agent_a",
        tool_id="t1",
        tool_name="mcp__filesystem__read_text_file",
        args={"path": "/tmp/a.txt"},
        server_name="filesystem",
    )
    # Thinking whitespace is filtered from display, but still marks content arrival.
    interleaved_content = MassGenEvent.create(
        EventType.THINKING,
        agent_id="agent_a",
        content=" \n ",
    )
    second_tool = MassGenEvent.create(
        EventType.TOOL_START,
        agent_id="agent_a",
        tool_id="t2",
        tool_name="mcp__filesystem__write_file",
        args={"path": "/tmp/b.txt"},
        server_name="filesystem",
    )

    first_out = processor.process_event(first_tool, round_number=1)
    thinking_out = processor.process_event(interleaved_content, round_number=1)
    second_out = processor.process_event(second_tool, round_number=1)

    assert first_out is not None and first_out.batch_action == "pending"
    assert thinking_out is None
    assert second_out is not None and second_out.batch_action == "pending"
