# -*- coding: utf-8 -*-
"""Unit tests for TaskDecomposer parsing helpers."""

import importlib.util
from pathlib import Path


def _load_task_decomposer_module():
    """Load task_decomposer module directly to avoid package import side effects."""
    module_path = Path(__file__).resolve().parents[1] / "task_decomposer.py"
    spec = importlib.util.spec_from_file_location("task_decomposer_under_test", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_subtasks_from_plain_json_text() -> None:
    module = _load_task_decomposer_module()
    decomposer = module.TaskDecomposer(module.TaskDecomposerConfig())

    text = '{"subtasks": {"agent_a": "Research data", "agent_b": "Build implementation"}}'
    parsed = decomposer._parse_subtasks_from_text(text, ["agent_a", "agent_b"])

    assert parsed == {
        "agent_a": "Research data",
        "agent_b": "Build implementation",
    }


def test_parse_subtasks_from_markdown_json_block() -> None:
    module = _load_task_decomposer_module()
    decomposer = module.TaskDecomposer(module.TaskDecomposerConfig())

    text = "Here is the plan:\n" "```json\n" '{"subtasks": {"agent_a": "Design architecture", "agent_b": "Implement UI"}}\n' "```"
    parsed = decomposer._parse_subtasks_from_text(text, ["agent_a", "agent_b"])

    assert parsed == {
        "agent_a": "Design architecture",
        "agent_b": "Implement UI",
    }


def test_normalize_subtasks_fills_missing_agents() -> None:
    module = _load_task_decomposer_module()
    decomposer = module.TaskDecomposer(module.TaskDecomposerConfig())

    parsed = decomposer._normalize_subtasks(
        {
            "agent_a": "Write tests",
        },
        ["agent_a", "agent_b", "agent_c"],
    )

    assert parsed["agent_a"] == "Write tests"
    assert "agent_b" in parsed
    assert "agent_c" in parsed
