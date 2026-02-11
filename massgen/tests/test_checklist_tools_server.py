#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for the checklist MCP tools server.

Tests cover:
- _extract_score() from different input types
- submit_checklist verdict logic (iterate vs terminate)
- First-answer forced iterate behavior
- Codex JSON-string normalization for scores
- Improvement analysis inclusion in explanations
- write_checklist_specs() file I/O
- build_server_config() structure
"""

import json

import pytest

from massgen.mcp_tools.checklist_tools_server import (
    _extract_score,
    _read_specs,
    build_server_config,
    write_checklist_specs,
)

# ---------------------------------------------------------------------------
# _extract_score
# ---------------------------------------------------------------------------


class TestExtractScore:
    """Tests for _extract_score helper."""

    def test_int_value(self):
        assert _extract_score(80) == 80

    def test_float_value(self):
        assert _extract_score(75.9) == 75

    def test_dict_with_score(self):
        assert _extract_score({"score": 90, "reasoning": "great"}) == 90

    def test_dict_missing_score_key(self):
        assert _extract_score({"reasoning": "no score"}) == 0

    def test_string_returns_zero(self):
        assert _extract_score("not a number") == 0

    def test_none_returns_zero(self):
        assert _extract_score(None) == 0

    def test_zero_score(self):
        assert _extract_score(0) == 0

    def test_dict_with_zero_score(self):
        assert _extract_score({"score": 0, "reasoning": "failed"}) == 0


# ---------------------------------------------------------------------------
# _read_specs
# ---------------------------------------------------------------------------


class TestReadSpecs:
    """Tests for _read_specs file reader."""

    def test_reads_valid_json(self, tmp_path):
        specs_file = tmp_path / "specs.json"
        specs_file.write_text(json.dumps({"items": ["a", "b"], "state": {}}))
        result = _read_specs(specs_file)
        assert result["items"] == ["a", "b"]

    def test_returns_empty_on_missing_file(self, tmp_path):
        result = _read_specs(tmp_path / "missing.json")
        assert result == {}

    def test_returns_empty_on_invalid_json(self, tmp_path):
        specs_file = tmp_path / "bad.json"
        specs_file.write_text("not json")
        result = _read_specs(specs_file)
        assert result == {}


# ---------------------------------------------------------------------------
# submit_checklist handler (tested via direct function invocation)
# ---------------------------------------------------------------------------


def _make_specs_file(tmp_path, items, state):
    """Helper to write a checklist specs file and return its path."""
    specs_path = tmp_path / "specs.json"
    write_checklist_specs(items, state, specs_path)
    return specs_path


def _build_handler(specs_path):
    """Build the submit_checklist handler by extracting it from registration."""
    import fastmcp

    mcp = fastmcp.FastMCP("test_checklist")
    from massgen.mcp_tools.checklist_tools_server import _register_checklist_tool

    _register_checklist_tool(mcp, specs_path)

    # Extract the registered tool's handler
    # FastMCP stores tools internally; we access the handler directly
    for tool in mcp._tool_manager._tools.values():
        if tool.name == "submit_checklist":
            return tool.fn
    raise RuntimeError("submit_checklist tool not found after registration")


class TestSubmitChecklistVerdict:
    """Tests for the submit_checklist tool's verdict logic."""

    @pytest.mark.asyncio
    async def test_all_pass_returns_terminate(self, tmp_path):
        """When all items pass the cutoff, verdict should be terminate action."""
        items = ["Quality check 1", "Quality check 2"]
        state = {
            "terminate_action": "vote",
            "iterate_action": "new_answer",
            "has_existing_answers": True,
            "required": 2,
            "cutoff": 70,
        }
        handler = _build_handler(_make_specs_file(tmp_path, items, state))

        result = json.loads(
            await handler(
                scores={"T1": {"score": 80, "reasoning": "good"}, "T2": {"score": 75, "reasoning": "ok"}},
                improvements="",
            ),
        )
        assert result["verdict"] == "vote"
        assert result["true_count"] == 2

    @pytest.mark.asyncio
    async def test_partial_pass_returns_iterate(self, tmp_path):
        """When not enough items pass, verdict should be iterate action."""
        items = ["Check 1", "Check 2", "Check 3"]
        state = {
            "terminate_action": "vote",
            "iterate_action": "new_answer",
            "has_existing_answers": True,
            "required": 3,
            "cutoff": 70,
        }
        handler = _build_handler(_make_specs_file(tmp_path, items, state))

        result = json.loads(
            await handler(
                scores={"T1": {"score": 80, "reasoning": "good"}, "T2": {"score": 50, "reasoning": "bad"}, "T3": {"score": 90, "reasoning": "great"}},
                improvements="",
            ),
        )
        assert result["verdict"] == "new_answer"
        assert result["true_count"] == 2
        assert "T2" in result["explanation"]

    @pytest.mark.asyncio
    async def test_first_answer_forces_iterate(self, tmp_path):
        """When has_existing_answers is False, verdict must always iterate."""
        items = ["Check 1"]
        state = {
            "terminate_action": "vote",
            "iterate_action": "new_answer",
            "has_existing_answers": False,
            "required": 1,
            "cutoff": 70,
        }
        handler = _build_handler(_make_specs_file(tmp_path, items, state))

        result = json.loads(
            await handler(
                scores={"T1": {"score": 100, "reasoning": "perfect"}},
                improvements="",
            ),
        )
        # Even though score passes, first answer always iterates
        assert result["verdict"] == "new_answer"
        assert "First answer" in result["explanation"]

    @pytest.mark.asyncio
    async def test_codex_json_string_scores(self, tmp_path):
        """Codex sends scores as JSON string; handler should normalize."""
        items = ["Check 1"]
        state = {
            "terminate_action": "vote",
            "iterate_action": "new_answer",
            "has_existing_answers": True,
            "required": 1,
            "cutoff": 70,
        }
        handler = _build_handler(_make_specs_file(tmp_path, items, state))

        # Send scores as a JSON string (Codex behavior)
        result = json.loads(
            await handler(
                scores='{"T1": {"score": 85, "reasoning": "good"}}',
                improvements="",
            ),
        )
        assert result["verdict"] == "vote"
        assert result["true_count"] == 1

    @pytest.mark.asyncio
    async def test_invalid_json_string_returns_error(self, tmp_path):
        """Invalid JSON string for scores should return an error."""
        items = ["Check 1"]
        state = {"has_existing_answers": True, "required": 1, "cutoff": 70}
        handler = _build_handler(_make_specs_file(tmp_path, items, state))

        result = json.loads(await handler(scores="not valid json", improvements=""))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_improvements_included_in_iterate_explanation(self, tmp_path):
        """Improvement analysis text should appear in iterate explanations."""
        items = ["Check 1"]
        state = {
            "terminate_action": "vote",
            "iterate_action": "new_answer",
            "has_existing_answers": True,
            "required": 1,
            "cutoff": 70,
        }
        handler = _build_handler(_make_specs_file(tmp_path, items, state))

        result = json.loads(
            await handler(
                scores={"T1": {"score": 30, "reasoning": "bad"}},
                improvements="Add error handling and validation",
            ),
        )
        assert result["verdict"] == "new_answer"
        assert "Add error handling and validation" in result["explanation"]

    @pytest.mark.asyncio
    async def test_missing_score_keys_default_to_zero(self, tmp_path):
        """Missing score entries should default to score 0."""
        items = ["Check 1", "Check 2"]
        state = {
            "terminate_action": "vote",
            "iterate_action": "new_answer",
            "has_existing_answers": True,
            "required": 2,
            "cutoff": 70,
        }
        handler = _build_handler(_make_specs_file(tmp_path, items, state))

        # Only provide T1, T2 is missing
        result = json.loads(
            await handler(
                scores={"T1": {"score": 80, "reasoning": "good"}},
                improvements="",
            ),
        )
        assert result["true_count"] == 1
        assert result["items"][1]["score"] == 0

    @pytest.mark.asyncio
    async def test_custom_terminate_and_iterate_actions(self, tmp_path):
        """Custom action names (stop/continue) should be used in verdicts."""
        items = ["Check 1"]
        state = {
            "terminate_action": "stop",
            "iterate_action": "continue",
            "has_existing_answers": True,
            "required": 1,
            "cutoff": 70,
        }
        handler = _build_handler(_make_specs_file(tmp_path, items, state))

        result = json.loads(
            await handler(
                scores={"T1": {"score": 80, "reasoning": "good"}},
                improvements="",
            ),
        )
        assert result["verdict"] == "stop"


# ---------------------------------------------------------------------------
# write_checklist_specs & build_server_config
# ---------------------------------------------------------------------------


class TestWriteChecklistSpecs:
    """Tests for write_checklist_specs utility."""

    def test_writes_valid_json(self, tmp_path):
        items = ["Item 1", "Item 2"]
        state = {"required": 2, "cutoff": 70}
        output = write_checklist_specs(items, state, tmp_path / "out.json")
        assert output.exists()
        data = json.loads(output.read_text())
        assert data["items"] == items
        assert data["state"] == state

    def test_creates_parent_directories(self, tmp_path):
        nested = tmp_path / "deep" / "nested" / "specs.json"
        write_checklist_specs([], {}, nested)
        assert nested.exists()


class TestBuildServerConfig:
    """Tests for build_server_config utility."""

    def test_config_structure(self, tmp_path):
        specs_path = tmp_path / "specs.json"
        config = build_server_config(specs_path)
        assert config["name"] == "massgen_checklist"
        assert config["type"] == "stdio"
        assert config["command"] == "fastmcp"
        assert "--specs" in config["args"]
        assert str(specs_path) in config["args"]
