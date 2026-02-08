# -*- coding: utf-8 -*-
"""Unit tests for workspace-browser scanning safeguards."""

from massgen.frontend.displays.textual.widgets.modals.browser_modals import (
    WorkspaceBrowserModal,
)


def _make_modal() -> WorkspaceBrowserModal:
    return WorkspaceBrowserModal(
        answers=[],
        agent_ids=["agent_a"],
        default_agent="agent_a",
    )


def test_workspace_browser_scan_limits_file_count(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    modal = _make_modal()
    max_files = modal._MAX_SCAN_FILES

    for idx in range(max_files + 50):
        (workspace / f"file_{idx:04d}.txt").write_text("x", encoding="utf-8")

    files, truncated = modal._scan_workspace_files(str(workspace))

    assert truncated is True
    assert len(files) == max_files


def test_workspace_browser_scan_limits_depth(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    modal = _make_modal()

    deep_dir = workspace
    for level in range(modal._MAX_SCAN_DEPTH + 2):
        deep_dir = deep_dir / f"lvl_{level}"
        deep_dir.mkdir()

    shallow_file = workspace / "top.txt"
    deep_file = deep_dir / "too_deep.txt"
    shallow_file.write_text("top", encoding="utf-8")
    deep_file.write_text("deep", encoding="utf-8")

    files, _ = modal._scan_workspace_files(str(workspace))
    rel_paths = {item["rel_path"] for item in files}

    assert "top.txt" in rel_paths
    assert deep_file.relative_to(workspace).as_posix() not in rel_paths
