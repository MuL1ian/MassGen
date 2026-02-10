# -*- coding: utf-8 -*-
"""Deterministic non-API integration tests for restart and external tool passthrough."""

from __future__ import annotations

import pytest


def _configure_agent_script(agent, scripted_tool_calls, responses=None):
    """Attach deterministic per-call tool scripts to a mock-backed agent."""
    agent.backend.tool_call_responses = scripted_tool_calls
    agent.backend.responses = responses or ["ok"] * len(scripted_tool_calls)


async def _collect_stream(stream):
    emitted = []
    async for item in stream:
        emitted.append(item)
    return emitted


@pytest.mark.asyncio
async def test_stream_agent_execution_vote_only_restart_short_circuits(mock_orchestrator, monkeypatch):
    orchestrator = mock_orchestrator(num_agents=1)
    orchestrator.current_task = "Vote-only restart path"
    agent_id = "agent_a"

    state = orchestrator.agent_states[agent_id]
    state.restart_pending = True
    state.injection_count = 2

    monkeypatch.setattr(orchestrator, "_is_vote_only_mode", lambda _aid: True)

    emitted = await _collect_stream(
        orchestrator._stream_agent_execution(agent_id, orchestrator.current_task, {}),
    )

    assert emitted == [("done", None)]
    assert state.restart_pending is False
    assert orchestrator.agents[agent_id].backend._call_count == 0


@pytest.mark.asyncio
async def test_stream_agent_execution_first_restart_increments_injection_count(mock_orchestrator, monkeypatch):
    orchestrator = mock_orchestrator(num_agents=1)
    orchestrator.current_task = "First restart path"
    agent_id = "agent_a"

    state = orchestrator.agent_states[agent_id]
    state.restart_pending = True
    state.injection_count = 0

    monkeypatch.setattr(orchestrator, "_is_vote_only_mode", lambda _aid: False)

    emitted = await _collect_stream(
        orchestrator._stream_agent_execution(agent_id, orchestrator.current_task, {}),
    )

    assert emitted == [("done", None)]
    assert state.restart_pending is False
    assert state.injection_count == 1
    assert orchestrator.agents[agent_id].backend._call_count == 0


@pytest.mark.asyncio
async def test_stream_agent_execution_surfaces_external_tool_calls(mock_orchestrator):
    orchestrator = mock_orchestrator(num_agents=1)
    orchestrator.current_task = "External passthrough"
    orchestrator._external_tools = [
        {
            "type": "function",
            "function": {
                "name": "external_lookup",
                "description": "Caller-executed external tool",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    ]

    agent_id = "agent_a"
    _configure_agent_script(
        orchestrator.agents[agent_id],
        scripted_tool_calls=[
            [{"id": "ext-1", "name": "external_lookup", "arguments": {"query": "latest"}}],
        ],
    )

    emitted = await _collect_stream(
        orchestrator._stream_agent_execution(agent_id, orchestrator.current_task, {}),
    )

    external_items = [item for item in emitted if item[0] == "external_tool_calls"]
    assert len(external_items) == 1
    assert external_items[0][1][0]["name"] == "external_lookup"
    assert emitted[-1] == ("done", None)
    assert not any(item[0] == "result" for item in emitted)


@pytest.mark.asyncio
async def test_stream_coordination_surfaces_external_tool_calls_and_stops(mock_orchestrator):
    orchestrator = mock_orchestrator(num_agents=1)
    orchestrator.current_task = "Coordination external passthrough"
    orchestrator._external_tools = [
        {
            "type": "function",
            "function": {
                "name": "external_lookup",
                "description": "Caller-executed external tool",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    ]

    _configure_agent_script(
        orchestrator.agents["agent_a"],
        scripted_tool_calls=[
            [{"id": "ext-2", "name": "external_lookup", "arguments": {"query": "deploy status"}}],
        ],
    )

    votes = {}
    chunks = []
    async for chunk in orchestrator._stream_coordination_with_agents(votes, {}):
        chunks.append(chunk)

    tool_chunks = [chunk for chunk in chunks if getattr(chunk, "type", None) == "tool_calls"]
    assert len(tool_chunks) == 1
    assert tool_chunks[0].source == "agent_a"
    assert tool_chunks[0].tool_calls[0]["name"] == "external_lookup"
    assert chunks[-1].type == "done"
    assert votes == {}
