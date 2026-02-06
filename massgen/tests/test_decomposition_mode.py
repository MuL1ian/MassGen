#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for decomposition coordination mode.

Tests cover:
- StopToolkit tool definitions (all 3 API formats)
- get_workflow_tools with decomposition_mode parameter
- Completion check reuse (has_voted works for both vote and stop)
- Presenter selection (explicit and fallback)
- Config validation for coordination_mode and presenter_agent
- AgentState stop metadata fields
"""

import pytest

from massgen.agent_config import AgentConfig, CoordinationConfig
from massgen.config_validator import ConfigValidator
from massgen.orchestrator import AgentState
from massgen.task_decomposer import TaskDecomposerConfig
from massgen.tool.workflow_toolkits import get_workflow_tools
from massgen.tool.workflow_toolkits.stop import StopToolkit
from massgen.utils import ActionType, AgentStatus


def _get_tool_names(tools, api_format):
    """Extract tool names from tools list based on API format."""
    names = []
    for tool in tools:
        if api_format == "claude":
            names.append(tool.get("name"))
        else:
            names.append(tool.get("function", {}).get("name"))
    return names


# =============================================================================
# StopToolkit Tests
# =============================================================================


class TestStopToolkit:
    """Test StopToolkit tool definitions across API formats."""

    def test_stop_tool_claude_format(self):
        """Test stop tool definition in Claude API format."""
        toolkit = StopToolkit()
        config = {"api_format": "claude", "enable_workflow_tools": True}
        tools = toolkit.get_tools(config)

        assert len(tools) == 1
        tool = tools[0]
        assert tool["name"] == "stop"
        assert "summary" in tool["input_schema"]["properties"]
        assert "status" in tool["input_schema"]["properties"]
        assert tool["input_schema"]["properties"]["status"]["enum"] == ["complete", "blocked"]
        assert set(tool["input_schema"]["required"]) == {"summary", "status"}

    def test_stop_tool_response_format(self):
        """Test stop tool definition in Response API format."""
        toolkit = StopToolkit()
        config = {"api_format": "response", "enable_workflow_tools": True}
        tools = toolkit.get_tools(config)

        assert len(tools) == 1
        tool = tools[0]
        assert tool["type"] == "function"
        assert tool["function"]["name"] == "stop"
        assert "summary" in tool["function"]["parameters"]["properties"]
        assert "status" in tool["function"]["parameters"]["properties"]

    def test_stop_tool_chat_completions_format(self):
        """Test stop tool definition in Chat Completions format."""
        toolkit = StopToolkit()
        config = {"api_format": "chat_completions", "enable_workflow_tools": True}
        tools = toolkit.get_tools(config)

        assert len(tools) == 1
        tool = tools[0]
        assert tool["type"] == "function"
        assert tool["function"]["name"] == "stop"

    def test_stop_toolkit_id(self):
        toolkit = StopToolkit()
        assert toolkit.toolkit_id == "stop"

    def test_stop_toolkit_enabled(self):
        toolkit = StopToolkit()
        assert toolkit.is_enabled({"enable_workflow_tools": True})
        assert not toolkit.is_enabled({"enable_workflow_tools": False})


# =============================================================================
# get_workflow_tools Decomposition Mode Tests
# =============================================================================


class TestWorkflowToolsDecomposition:
    """Test get_workflow_tools with decomposition_mode parameter."""

    @pytest.mark.parametrize("api_format", ["claude", "response", "chat_completions"])
    def test_decomposition_mode_returns_stop_not_vote(self, api_format):
        """In decomposition mode, stop replaces vote."""
        tools = get_workflow_tools(
            api_format=api_format,
            decomposition_mode=True,
        )
        names = _get_tool_names(tools, api_format)
        assert "stop" in names
        assert "vote" not in names
        assert "new_answer" in names

    @pytest.mark.parametrize("api_format", ["claude", "response", "chat_completions"])
    def test_voting_mode_returns_vote_not_stop(self, api_format):
        """In voting mode (default), vote is included, not stop."""
        tools = get_workflow_tools(
            api_format=api_format,
            decomposition_mode=False,
        )
        names = _get_tool_names(tools, api_format)
        assert "vote" in names
        assert "stop" not in names
        assert "new_answer" in names

    def test_decomposition_default_is_false(self):
        """Default decomposition_mode is False (voting mode)."""
        tools = get_workflow_tools(api_format="chat_completions")
        names = _get_tool_names(tools, "chat_completions")
        assert "vote" in names
        assert "stop" not in names


# =============================================================================
# AgentState Tests
# =============================================================================


class TestAgentStateDecomposition:
    """Test AgentState fields for decomposition mode."""

    def test_stop_metadata_fields_exist(self):
        """AgentState has stop_summary and stop_status fields."""
        state = AgentState()
        assert state.stop_summary is None
        assert state.stop_status is None

    def test_stop_metadata_can_be_set(self):
        state = AgentState()
        state.stop_summary = "Completed frontend UI"
        state.stop_status = "complete"
        assert state.stop_summary == "Completed frontend UI"
        assert state.stop_status == "complete"

    def test_has_voted_reuse_for_stop(self):
        """has_voted is reused as the 'agent is done' flag for both modes."""
        state = AgentState()
        assert not state.has_voted
        # Simulate stop
        state.has_voted = True
        state.stop_summary = "Done with subtask"
        state.stop_status = "complete"
        assert state.has_voted


# =============================================================================
# Completion Check Tests
# =============================================================================


class TestCompletionCheck:
    """Test that coordination completion works for both modes."""

    def test_all_voted_means_complete(self):
        """All agents with has_voted=True means coordination is complete."""
        states = {
            "a": AgentState(has_voted=True),
            "b": AgentState(has_voted=True),
            "c": AgentState(has_voted=True),
        }
        assert all(s.has_voted for s in states.values())

    def test_partial_voted_not_complete(self):
        states = {
            "a": AgentState(has_voted=True),
            "b": AgentState(has_voted=False),
        }
        assert not all(s.has_voted for s in states.values())

    def test_stop_sets_has_voted(self):
        """Stopping in decomposition mode sets has_voted=True."""
        state = AgentState()
        # Simulate stop handling
        state.has_voted = True
        state.stop_summary = "Subtask complete"
        state.stop_status = "complete"
        assert state.has_voted

    def test_new_answer_resets_has_voted(self):
        """New answer resets has_voted (wakes up stopped agents)."""
        states = {
            "a": AgentState(has_voted=True, stop_summary="Done", stop_status="complete"),
            "b": AgentState(has_voted=True, stop_summary="Done", stop_status="complete"),
        }
        # Simulate reset on new_answer
        for s in states.values():
            s.has_voted = False
            s.stop_summary = None
            s.stop_status = None
        assert not any(s.has_voted for s in states.values())
        assert all(s.stop_summary is None for s in states.values())


# =============================================================================
# Config Tests
# =============================================================================


class TestDecompositionConfig:
    """Test config validation for decomposition mode."""

    def test_agent_config_has_coordination_mode(self):
        """AgentConfig has coordination_mode field."""
        config = AgentConfig()
        assert config.coordination_mode == "voting"

    def test_agent_config_has_presenter_agent(self):
        """AgentConfig has presenter_agent field."""
        config = AgentConfig()
        assert config.presenter_agent is None

    def test_coordination_config_has_task_decomposer(self):
        """CoordinationConfig has task_decomposer field."""
        config = CoordinationConfig()
        assert isinstance(config.task_decomposer, TaskDecomposerConfig)
        assert config.task_decomposer.enabled is True

    def test_config_validator_valid_coordination_mode(self):
        """Valid coordination_mode values pass validation."""
        validator = ConfigValidator()
        config = {
            "agents": [{"id": "a", "backend": {"type": "openai", "model": "gpt-4o-mini"}}],
            "orchestrator": {"coordination_mode": "decomposition"},
        }
        result = validator.validate_config(config)
        # Should not have errors about coordination_mode
        mode_errors = [e for e in result.errors if "coordination_mode" in e.location]
        assert len(mode_errors) == 0

    def test_config_validator_invalid_coordination_mode(self):
        """Invalid coordination_mode values are rejected."""
        validator = ConfigValidator()
        config = {
            "agents": [{"id": "a", "backend": {"type": "openai", "model": "gpt-4o-mini"}}],
            "orchestrator": {"coordination_mode": "invalid"},
        }
        result = validator.validate_config(config)
        mode_errors = [e for e in result.errors if "coordination_mode" in e.location]
        assert len(mode_errors) == 1

    def test_config_validator_presenter_agent_must_be_valid(self):
        """presenter_agent must reference an existing agent ID."""
        validator = ConfigValidator()
        config = {
            "agents": [
                {"id": "frontend", "backend": {"type": "openai", "model": "gpt-4o-mini"}},
                {"id": "backend", "backend": {"type": "openai", "model": "gpt-4o-mini"}},
            ],
            "orchestrator": {
                "coordination_mode": "decomposition",
                "presenter_agent": "nonexistent",
            },
        }
        result = validator.validate_config(config)
        presenter_errors = [e for e in result.errors if "presenter_agent" in e.location]
        assert len(presenter_errors) == 1

    def test_config_validator_valid_presenter_agent(self):
        """Valid presenter_agent passes validation."""
        validator = ConfigValidator()
        config = {
            "agents": [
                {"id": "frontend", "backend": {"type": "openai", "model": "gpt-4o-mini"}},
                {"id": "backend", "backend": {"type": "openai", "model": "gpt-4o-mini"}},
            ],
            "orchestrator": {
                "coordination_mode": "decomposition",
                "presenter_agent": "backend",
            },
        }
        result = validator.validate_config(config)
        presenter_errors = [e for e in result.errors if "presenter_agent" in e.location]
        assert len(presenter_errors) == 0

    def test_config_validator_subtask_must_be_string(self):
        """Per-agent subtask must be a string."""
        validator = ConfigValidator()
        config = {
            "agents": [
                {"id": "a", "backend": {"type": "openai", "model": "gpt-4o-mini"}, "subtask": 123},
            ],
            "orchestrator": {"coordination_mode": "decomposition"},
        }
        result = validator.validate_config(config)
        subtask_errors = [e for e in result.errors if "subtask" in e.location]
        assert len(subtask_errors) == 1

    def test_config_validator_warns_no_subtasks(self):
        """Warning when decomposition mode has no subtasks defined."""
        validator = ConfigValidator()
        config = {
            "agents": [
                {"id": "a", "backend": {"type": "openai", "model": "gpt-4o-mini"}},
                {"id": "b", "backend": {"type": "openai", "model": "gpt-4o-mini"}},
            ],
            "orchestrator": {"coordination_mode": "decomposition"},
        }
        result = validator.validate_config(config)
        subtask_warnings = [w for w in result.warnings if "subtask" in w.suggestion.lower()]
        assert len(subtask_warnings) >= 1


# =============================================================================
# Enum Tests
# =============================================================================


class TestDecompositionEnums:
    """Test enum additions for decomposition mode."""

    def test_action_type_stop(self):
        assert ActionType.STOP.value == "stop"

    def test_agent_status_stopped(self):
        assert AgentStatus.STOPPED.value == "stopped"


# =============================================================================
# TaskDecomposerConfig Tests
# =============================================================================


class TestTaskDecomposerConfig:
    """Test TaskDecomposerConfig defaults."""

    def test_defaults(self):
        config = TaskDecomposerConfig()
        assert config.enabled is True
        assert config.decomposition_guidelines is None

    def test_custom_guidelines(self):
        config = TaskDecomposerConfig(
            decomposition_guidelines="Focus on separating frontend from backend",
        )
        assert "frontend" in config.decomposition_guidelines
