# -*- coding: utf-8 -*-
"""Tests for workspace tools skill wrapper helpers."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from massgen.filesystem_manager._workspace_tools_server import (
    _read_skill_fallback,
    _run_openskills_read,
    create_server,
)


def test_run_openskills_read_returns_stdout_on_success(monkeypatch) -> None:
    """CLI wrapper should return content when openskills succeeds."""

    def _fake_run(*args, **kwargs):
        return SimpleNamespace(returncode=0, stdout="# Skill Content\n", stderr="")

    monkeypatch.setattr(
        "massgen.filesystem_manager._workspace_tools_server.subprocess.run",
        _fake_run,
    )

    content, error = _run_openskills_read("demo-skill")

    assert content == "# Skill Content\n"
    assert error == ""


def test_run_openskills_read_handles_missing_binary(monkeypatch) -> None:
    """CLI wrapper should return a friendly error when openskills is missing."""

    def _fake_run(*args, **kwargs):
        raise FileNotFoundError("openskills not found")

    monkeypatch.setattr(
        "massgen.filesystem_manager._workspace_tools_server.subprocess.run",
        _fake_run,
    )

    content, error = _run_openskills_read("demo-skill")

    assert content is None
    assert "not found" in error


def test_read_skill_fallback_matches_name_or_folder(tmp_path: Path) -> None:
    """Fallback reader should resolve by frontmatter name and directory name."""
    skill_dir = tmp_path / "my-fallback-skill"
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        "---\nname: frontmatter-name\ndescription: demo\n---\n# Demo\n",
        encoding="utf-8",
    )

    catalog = [
        {
            "name": "frontmatter-name",
            "location": "project",
            "source_path": str(skill_file),
        },
    ]

    content_by_name, skill_by_name = _read_skill_fallback("frontmatter-name", catalog)
    content_by_folder, skill_by_folder = _read_skill_fallback("my-fallback-skill", catalog)

    assert content_by_name and "# Demo" in content_by_name
    assert content_by_folder and "# Demo" in content_by_folder
    assert skill_by_name and skill_by_name.get("name") == "frontmatter-name"
    assert skill_by_folder and skill_by_folder.get("name") == "frontmatter-name"


@pytest.mark.asyncio
async def test_skills_tool_not_registered_when_disabled_by_env(monkeypatch) -> None:
    """Server should not register the skills tool when env gate is enabled."""
    monkeypatch.setenv("MASSGEN_DISABLE_SKILLS_TOOL", "1")
    monkeypatch.setattr("sys.argv", ["workspace_tools_test"])
    server = await create_server()
    tools = await server.get_tools()
    names = {tool.name for tool in tools.values()}
    assert "skills" not in names
