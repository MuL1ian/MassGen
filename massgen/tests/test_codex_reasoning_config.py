# -*- coding: utf-8 -*-
"""Tests for Codex reasoning effort config mapping."""

from pathlib import Path
from types import SimpleNamespace

import pytest

try:
    import tomllib
except ImportError:  # pragma: no cover - Python < 3.11 fallback
    import tomli as tomllib

from massgen.backend.codex import CodexBackend


@pytest.fixture(autouse=True)
def _mock_codex_cli(monkeypatch):
    """Avoid requiring a real Codex CLI install in tests."""
    monkeypatch.setattr(CodexBackend, "_find_codex_cli", lambda self: "/usr/bin/codex")
    monkeypatch.setattr(CodexBackend, "_has_cached_credentials", lambda self: True)


def _read_workspace_codex_config(workspace: Path) -> dict:
    config_path = workspace / ".codex" / "config.toml"
    return tomllib.loads(config_path.read_text())


def test_codex_accepts_openai_style_reasoning_effort(tmp_path: Path):
    backend = CodexBackend(
        cwd=str(tmp_path),
        reasoning={"effort": "high", "summary": "auto"},
    )
    backend._write_workspace_config()

    config = _read_workspace_codex_config(tmp_path)
    assert config["model_reasoning_effort"] == "high"


def test_codex_model_reasoning_effort_takes_precedence(tmp_path: Path):
    backend = CodexBackend(
        cwd=str(tmp_path),
        model_reasoning_effort="xhigh",
        reasoning={"effort": "low", "summary": "auto"},
    )
    backend._write_workspace_config()

    config = _read_workspace_codex_config(tmp_path)
    assert config["model_reasoning_effort"] == "xhigh"


def test_codex_skips_reasoning_effort_when_not_provided(tmp_path: Path):
    backend = CodexBackend(
        cwd=str(tmp_path),
        reasoning={"summary": "auto"},
    )
    backend._write_workspace_config()

    config = _read_workspace_codex_config(tmp_path)
    assert "model_reasoning_effort" not in config


def test_codex_writes_instructions_file_under_codex_home(tmp_path: Path):
    backend = CodexBackend(cwd=str(tmp_path))
    backend.system_prompt = "system instructions"
    backend._write_workspace_config()

    config = _read_workspace_codex_config(tmp_path)
    instructions_path = tmp_path / ".codex" / "AGENTS.md"
    assert config["model_instructions_file"] == str(instructions_path)
    assert instructions_path.read_text() == "system instructions"
    assert not (tmp_path / "AGENTS.md").exists()


def test_codex_mirrors_local_skills_into_codex_home(tmp_path: Path):
    backend = CodexBackend(cwd=str(tmp_path))

    project_skills = tmp_path / ".agent" / "skills"
    project_skill = project_skills / "demo-skill"
    project_skill.mkdir(parents=True)
    (project_skill / "SKILL.md").write_text("# Demo Skill\n")

    backend.filesystem_manager = SimpleNamespace(
        local_skills_directory=project_skills,
        docker_manager=None,
        get_current_workspace=lambda: tmp_path,
    )
    assert backend._resolve_codex_skills_source() == project_skills
    backend._sync_skills_into_codex_home(tmp_path / ".codex")

    mirrored_skill = tmp_path / ".codex" / "skills" / "demo-skill" / "SKILL.md"
    assert mirrored_skill.exists()
    assert mirrored_skill.read_text() == "# Demo Skill\n"
