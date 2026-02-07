# -*- coding: utf-8 -*-
"""Deterministic non-API integration tests for final presentation decision paths."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from massgen.backend.base import StreamChunk


async def _collect_chunks(stream):
    chunks = []
    async for chunk in stream:
        chunks.append(chunk)
    return chunks


@pytest.mark.asyncio
async def test_skip_final_presentation_single_agent_with_write_paths_uses_existing_answer(
    mock_orchestrator,
    monkeypatch,
):
    orchestrator = mock_orchestrator(num_agents=1)
    agent_id = "agent_a"
    orchestrator.current_task = "Finalize single-agent answer"
    orchestrator._selected_agent = agent_id
    orchestrator.agent_states[agent_id].answer = "Single-agent final answer"
    orchestrator.config.skip_voting = True
    orchestrator.config.skip_final_presentation = True
    orchestrator._save_agent_snapshot = AsyncMock(return_value="final")

    monkeypatch.setattr(orchestrator, "_has_write_context_paths", lambda _agent: True)
    monkeypatch.setattr(orchestrator, "save_coordination_logs", lambda: None)

    async def should_not_be_called(*_args, **_kwargs):
        raise AssertionError("get_final_presentation should not run in single-agent skip path")

    monkeypatch.setattr(orchestrator, "get_final_presentation", should_not_be_called)

    chunks = await _collect_chunks(orchestrator._present_final_answer())
    contents = [getattr(c, "content", "") for c in chunks if getattr(c, "type", None) == "content"]

    assert any("Single-agent final answer" in content for content in contents)
    assert chunks[-1].type == "done"
    orchestrator._save_agent_snapshot.assert_awaited_once()


@pytest.mark.asyncio
async def test_skip_final_presentation_multi_agent_with_write_paths_falls_through_to_presentation(
    mock_orchestrator,
    monkeypatch,
):
    orchestrator = mock_orchestrator(num_agents=2)
    agent_id = "agent_a"
    orchestrator.current_task = "Finalize multi-agent answer"
    orchestrator._selected_agent = agent_id
    orchestrator.agent_states[agent_id].answer = "Winning answer content"
    orchestrator.config.skip_voting = False
    orchestrator.config.skip_final_presentation = True

    monkeypatch.setattr(orchestrator, "_has_write_context_paths", lambda _agent: True)

    called = {"selected": None}

    async def fake_final_presentation(selected_agent_id, vote_results):
        called["selected"] = selected_agent_id
        _ = vote_results
        yield StreamChunk(type="content", content="Presented via final presentation")
        yield StreamChunk(type="done")

    monkeypatch.setattr(orchestrator, "get_final_presentation", fake_final_presentation)

    chunks = await _collect_chunks(orchestrator._present_final_answer())
    contents = [getattr(c, "content", "") for c in chunks if getattr(c, "type", None) == "content"]

    assert called["selected"] == agent_id
    assert any("Presented via final presentation" in content for content in contents)


@pytest.mark.asyncio
async def test_skip_final_presentation_multi_agent_without_write_paths_uses_existing_answer(
    mock_orchestrator,
    monkeypatch,
):
    orchestrator = mock_orchestrator(num_agents=2)
    agent_id = "agent_a"
    orchestrator.current_task = "Skip final presentation in multi-agent no-write mode"
    orchestrator._selected_agent = agent_id
    orchestrator.agent_states[agent_id].answer = "Existing winning answer"
    orchestrator.config.skip_voting = False
    orchestrator.config.skip_final_presentation = True
    orchestrator._save_agent_snapshot = AsyncMock(return_value="final")

    monkeypatch.setattr(orchestrator, "_has_write_context_paths", lambda _agent: False)
    monkeypatch.setattr(orchestrator, "save_coordination_logs", lambda: None)

    async def should_not_be_called(*_args, **_kwargs):
        raise AssertionError("get_final_presentation should be skipped when no write paths exist")

    monkeypatch.setattr(orchestrator, "get_final_presentation", should_not_be_called)

    chunks = await _collect_chunks(orchestrator._present_final_answer())
    contents = [getattr(c, "content", "") for c in chunks if getattr(c, "type", None) == "content"]

    assert any("Existing winning answer" in content for content in contents)
    assert chunks[-1].type == "done"
    orchestrator._save_agent_snapshot.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_final_presentation_enables_context_write_access(mock_orchestrator, monkeypatch):
    orchestrator = mock_orchestrator(num_agents=1)
    agent_id = "agent_a"
    agent = orchestrator.agents[agent_id]
    orchestrator.current_task = "Final presentation write enablement"
    orchestrator._selected_agent = agent_id
    orchestrator.agent_states[agent_id].answer = "Stored answer for final presentation"

    class DummyPathPermissionManager:
        def __init__(self):
            self.snapshot_calls = 0
            self.write_enabled = []
            self.compute_calls = 0

        def snapshot_writable_context_paths(self):
            self.snapshot_calls += 1

        def set_context_write_access_enabled(self, enabled):
            self.write_enabled.append(enabled)

        def compute_context_path_writes(self):
            self.compute_calls += 1
            return []

        def get_context_paths(self):
            return [{"permission": "write"}]

    class DummyFilesystemManager:
        def __init__(self, ppm):
            self.path_permission_manager = ppm
            self.docker_manager = None
            self.agent_temporary_workspace = "/tmp/agent-temp"

        def get_current_workspace(self):
            return "/tmp/agent-workspace"

    ppm = DummyPathPermissionManager()
    agent.backend.filesystem_manager = DummyFilesystemManager(ppm)
    agent.backend._planning_mode = True

    orchestrator._copy_all_snapshots_to_temp_workspace = AsyncMock(return_value="/tmp/final-snapshots")
    orchestrator._save_agent_snapshot = AsyncMock(return_value="final")
    monkeypatch.setattr(orchestrator, "save_coordination_logs", lambda: None)
    monkeypatch.setattr(
        orchestrator,
        "_get_system_message_builder",
        lambda: type(
            "DummyBuilder",
            (),
            {"build_presentation_message": lambda self, **_kwargs: "presentation system"},
        )(),
    )

    async def fake_chat(*_args, **_kwargs):
        yield StreamChunk(type="done")

    agent.chat = fake_chat

    chunks = await _collect_chunks(
        orchestrator.get_final_presentation(
            agent_id,
            {"vote_counts": {agent_id: 1}, "voter_details": {}, "is_tie": False},
        ),
    )

    assert ppm.snapshot_calls == 1
    assert ppm.write_enabled == [True]
    assert ppm.compute_calls >= 1
    assert agent.backend._planning_mode is False
    assert any(chunk.type == "status" for chunk in chunks)
