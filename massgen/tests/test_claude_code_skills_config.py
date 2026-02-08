# -*- coding: utf-8 -*-
"""Tests for Claude Code skill discovery configuration."""

from pathlib import Path
from types import SimpleNamespace

from massgen.backend.claude_code import ClaudeCodeBackend


def _build_filesystem_manager_stub(workspace: Path, local_skills_directory: Path) -> SimpleNamespace:
    return SimpleNamespace(
        local_skills_directory=local_skills_directory,
        docker_manager=None,
        agent_id="agent_a",
        get_current_workspace=lambda: workspace,
        get_claude_code_hooks_config=lambda: {},
        path_permission_manager=SimpleNamespace(get_writable_paths=lambda: [str(workspace)]),
    )


def test_claude_code_enables_setting_sources_when_skill_allowed(tmp_path: Path):
    backend = ClaudeCodeBackend(cwd=str(tmp_path))

    project_skills = tmp_path / ".agent" / "skills"
    project_skill = project_skills / "demo-skill"
    project_skill.mkdir(parents=True)
    (project_skill / "SKILL.md").write_text("# Demo Skill\n")

    backend.filesystem_manager = _build_filesystem_manager_stub(tmp_path, project_skills)
    options = backend._build_claude_options(allowed_tools=["Skill"])

    assert list(options.setting_sources) == ["user", "project"]
    mirrored_skill = tmp_path / ".claude" / "skills" / "demo-skill" / "SKILL.md"
    assert mirrored_skill.exists()
    assert mirrored_skill.read_text() == "# Demo Skill\n"


def test_claude_code_keeps_settings_disabled_without_skill_tool(tmp_path: Path):
    backend = ClaudeCodeBackend(cwd=str(tmp_path))

    project_skills = tmp_path / ".agent" / "skills"
    project_skill = project_skills / "demo-skill"
    project_skill.mkdir(parents=True)
    (project_skill / "SKILL.md").write_text("# Demo Skill\n")

    backend.filesystem_manager = _build_filesystem_manager_stub(tmp_path, project_skills)
    options = backend._build_claude_options(allowed_tools=["Task"])

    assert list(options.setting_sources) == []
    assert not (tmp_path / ".claude" / "skills").exists()


def test_claude_code_does_not_disallow_skill_tool(tmp_path: Path):
    backend = ClaudeCodeBackend(cwd=str(tmp_path))
    assert "Skill" not in backend.get_disallowed_tools({})
