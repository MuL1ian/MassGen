# -*- coding: utf-8 -*-
"""Unit tests for ToolBatchTracker timeline batching behavior."""

from datetime import datetime, timezone

from massgen.frontend.displays.content_handlers import ToolBatchTracker, ToolDisplayData


def _make_tool(tool_id: str, tool_name: str, status: str = "running") -> ToolDisplayData:
    return ToolDisplayData(
        tool_id=tool_id,
        tool_name=tool_name,
        display_name=tool_name,
        tool_type="mcp" if tool_name.startswith("mcp__") else "tool",
        category="filesystem",
        icon="F",
        color="blue",
        status=status,
        start_time=datetime.now(timezone.utc),
    )


def test_consecutive_mcp_tools_convert_to_batch():
    tracker = ToolBatchTracker()

    action1, server1, batch_id1, pending_id1 = tracker.process_tool(_make_tool("t1", "mcp__filesystem__read_text_file"))
    assert action1 == "pending"
    assert server1 == "filesystem"
    assert batch_id1 is None
    assert pending_id1 is None

    action2, server2, batch_id2, pending_id2 = tracker.process_tool(_make_tool("t2", "mcp__filesystem__write_file"))
    assert action2 == "convert_to_batch"
    assert server2 == "filesystem"
    assert batch_id2 == "batch_1"
    assert pending_id2 == "t1"


def test_content_breaks_batching_sequence():
    tracker = ToolBatchTracker()
    tracker.process_tool(_make_tool("t1", "mcp__filesystem__read_text_file"))

    # Chronology rule: non-tool content between tools prevents batch conversion.
    tracker.mark_content_arrived()

    action, server, batch_id, pending_id = tracker.process_tool(_make_tool("t2", "mcp__filesystem__write_file"))
    assert action == "pending"
    assert server == "filesystem"
    assert batch_id is None
    assert pending_id is None


def test_non_mcp_tools_are_standalone():
    tracker = ToolBatchTracker()

    action, server, batch_id, pending_id = tracker.process_tool(_make_tool("t1", "web_search"))
    assert action == "standalone"
    assert server is None
    assert batch_id is None
    assert pending_id is None


def test_third_consecutive_tool_adds_to_existing_batch():
    tracker = ToolBatchTracker()
    tracker.process_tool(_make_tool("t1", "mcp__filesystem__read_text_file"))
    tracker.process_tool(_make_tool("t2", "mcp__filesystem__write_file"))

    action, server, batch_id, pending_id = tracker.process_tool(_make_tool("t3", "mcp__filesystem__list_directory"))
    assert action == "add_to_batch"
    assert server == "filesystem"
    assert batch_id == "batch_1"
    assert pending_id is None


def test_status_update_for_batched_tool_uses_update_batch_action():
    tracker = ToolBatchTracker()
    tracker.process_tool(_make_tool("t1", "mcp__filesystem__read_text_file"))
    tracker.process_tool(_make_tool("t2", "mcp__filesystem__write_file"))
    tracker.process_tool(_make_tool("t3", "mcp__filesystem__list_directory"))

    action, server, batch_id, pending_id = tracker.process_tool(_make_tool("t2", "mcp__filesystem__write_file", status="success"))
    assert action == "update_batch"
    assert server == "filesystem"
    assert batch_id == "batch_1"
    assert pending_id is None


def test_reset_clears_batch_state():
    tracker = ToolBatchTracker()
    tracker.process_tool(_make_tool("t1", "mcp__filesystem__read_text_file"))
    tracker.process_tool(_make_tool("t2", "mcp__filesystem__write_file"))
    assert tracker.current_batch_id == "batch_1"

    tracker.reset()
    assert tracker.current_batch_id is None
    assert tracker.current_server is None

    action, server, batch_id, pending_id = tracker.process_tool(_make_tool("t3", "mcp__filesystem__list_directory"))
    assert action == "pending"
    assert server == "filesystem"
    assert batch_id is None
    assert pending_id is None
