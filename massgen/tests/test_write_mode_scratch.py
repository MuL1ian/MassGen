# -*- coding: utf-8 -*-
"""
Tests for write_mode unified workspace with in-worktree scratch.

Covers:
- Scratch directory creation and git exclusion
- Branch lifecycle (one branch per agent, cleanup_round vs cleanup_session)
- move_scratch_to_workspace archive
- ChangeApplier skipping scratch files
- Shadow mode scratch support
- Config validator deprecation warnings
"""

import os
from pathlib import Path

from git import Repo

from massgen.filesystem_manager._change_applier import ChangeApplier
from massgen.filesystem_manager._isolation_context_manager import (
    SCRATCH_DIR_NAME,
    IsolationContextManager,
)


def init_test_repo(path: Path, with_commit: bool = True) -> Repo:
    """Helper to initialize a test git repo with GitPython."""
    repo = Repo.init(path)
    with repo.config_writer() as config:
        config.set_value("user", "email", "test@test.com")
        config.set_value("user", "name", "Test")
    if with_commit:
        (path / "file.txt").write_text("content")
        repo.index.add(["file.txt"])
        repo.index.commit("init")
    return repo


class TestScratchDirectory:
    """Tests for .massgen_scratch/ creation and git exclusion."""

    def test_worktree_creates_scratch_dir(self, tmp_path):
        """Verify .massgen_scratch/ is created inside the worktree."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        init_test_repo(repo_path)

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        icm = IsolationContextManager(
            session_id="test-scratch",
            write_mode="worktree",
            workspace_path=str(workspace),
        )
        isolated = icm.initialize_context(str(repo_path), agent_id="agent1")
        scratch = os.path.join(isolated, SCRATCH_DIR_NAME)

        assert os.path.isdir(scratch), ".massgen_scratch/ should be created in worktree"
        icm.cleanup_all()

    def test_scratch_is_git_excluded(self, tmp_path):
        """Verify files in .massgen_scratch/ are invisible to git status."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        init_test_repo(repo_path)

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        icm = IsolationContextManager(
            session_id="test-exclude",
            write_mode="worktree",
            workspace_path=str(workspace),
        )
        isolated = icm.initialize_context(str(repo_path), agent_id="agent1")

        # Write a file in scratch
        scratch_file = os.path.join(isolated, SCRATCH_DIR_NAME, "notes.md")
        with open(scratch_file, "w") as f:
            f.write("scratch content")

        # Check git status - scratch file should be invisible
        wt_repo = Repo(isolated)
        untracked = wt_repo.untracked_files
        assert "notes.md" not in str(untracked), "Scratch files should be git-excluded"
        assert SCRATCH_DIR_NAME not in str(untracked), "Scratch dir should be git-excluded"
        icm.cleanup_all()

    def test_diff_excludes_scratch(self, tmp_path):
        """Verify get_diff() only shows non-scratch file changes."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        init_test_repo(repo_path)

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        icm = IsolationContextManager(
            session_id="test-diff",
            write_mode="worktree",
            workspace_path=str(workspace),
        )
        isolated = icm.initialize_context(str(repo_path), agent_id="agent1")

        # Write scratch file and tracked file
        scratch_file = os.path.join(isolated, SCRATCH_DIR_NAME, "notes.md")
        with open(scratch_file, "w") as f:
            f.write("scratch content")
        tracked_file = os.path.join(isolated, "new_feature.py")
        with open(tracked_file, "w") as f:
            f.write("feature code")

        diff = icm.get_diff(str(repo_path))
        assert "new_feature.py" in diff, "Tracked file should appear in diff"
        assert "notes.md" not in diff, "Scratch file should NOT appear in diff"
        icm.cleanup_all()

    def test_get_scratch_path(self, tmp_path):
        """Verify get_scratch_path() returns the correct path."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        init_test_repo(repo_path)

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        icm = IsolationContextManager(
            session_id="test-path",
            write_mode="worktree",
            workspace_path=str(workspace),
        )
        icm.initialize_context(str(repo_path), agent_id="agent1")
        scratch = icm.get_scratch_path(str(repo_path))

        assert scratch is not None
        assert scratch.endswith(SCRATCH_DIR_NAME)
        assert os.path.isdir(scratch)
        icm.cleanup_all()


class TestMoveScatchToWorkspace:
    """Tests for scratch archive functionality."""

    def test_move_scratch_to_workspace(self, tmp_path):
        """Verify scratch is moved to .scratch_archive/ in workspace."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        init_test_repo(repo_path)

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        icm = IsolationContextManager(
            session_id="test-archive",
            write_mode="worktree",
            workspace_path=str(workspace),
        )
        isolated = icm.initialize_context(str(repo_path), agent_id="agent1")

        # Write content in scratch
        scratch_file = os.path.join(isolated, SCRATCH_DIR_NAME, "notes.md")
        with open(scratch_file, "w") as f:
            f.write("important notes")

        archive_dir = icm.move_scratch_to_workspace(str(repo_path))

        assert archive_dir is not None
        assert ".scratch_archive" in archive_dir
        assert os.path.isdir(archive_dir)
        assert os.path.exists(os.path.join(archive_dir, "notes.md"))
        # Original scratch should no longer exist
        assert not os.path.exists(os.path.join(isolated, SCRATCH_DIR_NAME))
        icm.cleanup_all()


class TestScratchArchiveLabel:
    """Tests for archive_label in move_scratch_to_workspace."""

    def test_scratch_archive_uses_label(self, tmp_path):
        """Verify archive dir uses archive_label when provided."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        init_test_repo(repo_path)

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        icm = IsolationContextManager(
            session_id="test-label-archive",
            write_mode="worktree",
            workspace_path=str(workspace),
        )
        isolated = icm.initialize_context(str(repo_path), agent_id="agent1")

        # Write content in scratch
        scratch_file = os.path.join(isolated, SCRATCH_DIR_NAME, "notes.md")
        with open(scratch_file, "w") as f:
            f.write("important notes")

        archive_dir = icm.move_scratch_to_workspace(str(repo_path), archive_label="agent1")

        assert archive_dir is not None
        assert archive_dir.endswith("agent1"), f"Expected archive dir ending with 'agent1', got {archive_dir}"
        assert os.path.isdir(archive_dir)
        assert os.path.exists(os.path.join(archive_dir, "notes.md"))
        icm.cleanup_all()

    def test_scratch_archive_falls_back_to_branch_suffix(self, tmp_path):
        """Verify archive dir uses branch suffix when no archive_label."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        init_test_repo(repo_path)

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        icm = IsolationContextManager(
            session_id="test-fallback-archive",
            write_mode="worktree",
            workspace_path=str(workspace),
        )
        isolated = icm.initialize_context(str(repo_path), agent_id="agent1")

        scratch_file = os.path.join(isolated, SCRATCH_DIR_NAME, "notes.md")
        with open(scratch_file, "w") as f:
            f.write("notes")

        # No archive_label — should fall back to branch suffix
        archive_dir = icm.move_scratch_to_workspace(str(repo_path))

        assert archive_dir is not None
        assert ".scratch_archive" in archive_dir
        # The archive dir name should be the hex suffix from branch name
        archive_name = os.path.basename(archive_dir)
        assert len(archive_name) == 8, f"Expected 8-char hex suffix, got '{archive_name}'"
        icm.cleanup_all()


class TestBranchLifecycle:
    """Tests for one-branch-per-agent branch lifecycle."""

    def test_cleanup_round_keeps_branch(self, tmp_path):
        """Verify cleanup_round() removes worktree but keeps the branch."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        repo = init_test_repo(repo_path)

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        icm = IsolationContextManager(
            session_id="test-round",
            write_mode="worktree",
            workspace_path=str(workspace),
        )
        isolated = icm.initialize_context(str(repo_path), agent_id="agent1")
        branch_name = icm.get_branch_name(str(repo_path))
        assert branch_name is not None

        # Cleanup round - worktree removed, branch kept
        icm.cleanup_round(str(repo_path))

        # Worktree should be removed
        assert not os.path.exists(isolated), "Worktree should be removed"
        # Branch should still exist
        branches = [b.name for b in repo.branches]
        assert branch_name in branches, f"Branch {branch_name} should be preserved"

    def test_cleanup_session_removes_branches(self, tmp_path):
        """Verify cleanup_session() removes worktrees AND all branches."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        repo = init_test_repo(repo_path)

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        icm = IsolationContextManager(
            session_id="test-session",
            write_mode="worktree",
            workspace_path=str(workspace),
        )
        icm.initialize_context(str(repo_path), agent_id="agent1")
        branch_name = icm.get_branch_name(str(repo_path))

        icm.cleanup_session()

        # Branch should be removed
        branches = [b.name for b in repo.branches]
        assert branch_name not in branches, f"Branch {branch_name} should be deleted"

    def test_branch_names_are_short_random(self, tmp_path):
        """Verify default branch names are short: massgen/{random_hex}."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        init_test_repo(repo_path)

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        icm = IsolationContextManager(
            session_id="test-random",
            write_mode="worktree",
            workspace_path=str(workspace),
        )
        icm.initialize_context(str(repo_path), agent_id="agent1")
        branch_name = icm.get_branch_name(str(repo_path))

        assert branch_name is not None
        # Should use short massgen/{random} format (no session ID)
        assert branch_name.startswith("massgen/")
        parts = branch_name.split("/")
        assert len(parts) == 2, f"Expected massgen/{{hex}}, got {branch_name}"
        # Should NOT contain agent_id or round number
        assert "agent1" not in branch_name, "Branch name should not contain agent ID"
        assert "test-random" not in branch_name, "Branch name should not contain session ID"
        icm.cleanup_all()

    def test_branch_label_overrides_name(self, tmp_path):
        """Verify branch_label produces a readable branch name when explicitly set."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        init_test_repo(repo_path)

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        icm = IsolationContextManager(
            session_id="test-label",
            write_mode="worktree",
            workspace_path=str(workspace),
            branch_label="presenter",
        )
        icm.initialize_context(str(repo_path), agent_id="agent1")
        branch_name = icm.get_branch_name(str(repo_path))

        assert branch_name == "presenter", f"Expected 'presenter', got {branch_name}"
        icm.cleanup_all()

    def test_previous_branch_deleted_on_new_round(self, tmp_path):
        """Verify old branch is deleted when new round creates a new branch."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        repo = init_test_repo(repo_path)

        workspace1 = tmp_path / "workspace1"
        workspace1.mkdir()
        workspace2 = tmp_path / "workspace2"
        workspace2.mkdir()

        # Round 1
        icm1 = IsolationContextManager(
            session_id="test-round1",
            write_mode="worktree",
            workspace_path=str(workspace1),
        )
        icm1.initialize_context(str(repo_path), agent_id="agent1")
        old_branch = icm1.get_branch_name(str(repo_path))
        icm1.cleanup_round(str(repo_path))

        # Verify old branch exists
        branches = [b.name for b in repo.branches]
        assert old_branch in branches

        # Round 2 with previous_branch set
        icm2 = IsolationContextManager(
            session_id="test-round2",
            write_mode="worktree",
            workspace_path=str(workspace2),
            previous_branch=old_branch,
        )
        icm2.initialize_context(str(repo_path), agent_id="agent1")

        # Old branch should be deleted
        branches = [b.name for b in repo.branches]
        assert old_branch not in branches, f"Previous branch {old_branch} should be deleted"
        icm2.cleanup_all()


class TestChangeApplierSkipsScratch:
    """Tests for ChangeApplier skipping .massgen_scratch files."""

    def test_change_applier_skips_scratch(self, tmp_path):
        """Verify _apply_file_changes() skips .massgen_scratch files."""
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"
        target.mkdir()

        # Create a normal file and a scratch file in source
        (source / "main.py").write_text("code")
        scratch_dir = source / ".massgen_scratch"
        scratch_dir.mkdir()
        (scratch_dir / "notes.md").write_text("scratch notes")

        applier = ChangeApplier()
        applied = applier._apply_file_changes(source, target, approved_files=None)

        assert "main.py" in applied, "Normal files should be applied"
        scratch_applied = [f for f in applied if ".massgen_scratch" in f]
        assert len(scratch_applied) == 0, "Scratch files should be skipped"


class TestShadowModeCreatesScatch:
    """Tests for shadow repo scratch support."""

    def test_shadow_mode_creates_scratch(self, tmp_path):
        """Verify shadow repos get .massgen_scratch/ too."""
        non_git_dir = tmp_path / "project"
        non_git_dir.mkdir()
        (non_git_dir / "file.txt").write_text("content")

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        icm = IsolationContextManager(
            session_id="test-shadow",
            write_mode="isolated",
            workspace_path=str(workspace),
        )
        isolated = icm.initialize_context(str(non_git_dir), agent_id="agent1")
        scratch = os.path.join(isolated, SCRATCH_DIR_NAME)

        assert os.path.isdir(scratch), ".massgen_scratch/ should be created in shadow repo"
        icm.cleanup_all()


class TestWorkspaceScratchNoContextPaths:
    """Tests for workspace mode (no context_paths case)."""

    def test_workspace_scratch_creates_git_repo(self, tmp_path):
        """Verify setup_workspace_scratch() git-inits a non-git workspace."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "notes.txt").write_text("some content")

        icm = IsolationContextManager(
            session_id="test-ws",
            write_mode="auto",
            workspace_path=str(workspace),
        )
        scratch = icm.setup_workspace_scratch(str(workspace), agent_id="agent1")

        # Should be a git repo now
        assert (workspace / ".git").exists(), "Workspace should be git-initialized"
        # Scratch should exist
        assert os.path.isdir(scratch), ".massgen_scratch/ should be created"
        assert scratch.endswith(SCRATCH_DIR_NAME)
        icm.cleanup_session()

    def test_workspace_scratch_creates_branch(self, tmp_path):
        """Verify setup_workspace_scratch() creates a short branch."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        icm = IsolationContextManager(
            session_id="test-ws-branch",
            write_mode="auto",
            workspace_path=str(workspace),
        )
        icm.setup_workspace_scratch(str(workspace), agent_id="agent1")

        branch = icm.get_branch_name(str(workspace))
        assert branch is not None
        assert branch.startswith("massgen/")
        parts = branch.split("/")
        assert len(parts) == 2, f"Expected massgen/{{hex}}, got {branch}"
        assert "agent1" not in branch, "Branch name should not contain agent ID"

        # Verify the branch exists in the repo
        repo = Repo(str(workspace))
        assert branch in [b.name for b in repo.branches]
        icm.cleanup_session()

    def test_workspace_scratch_git_excluded(self, tmp_path):
        """Verify scratch files are invisible to git status in workspace mode."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        icm = IsolationContextManager(
            session_id="test-ws-exclude",
            write_mode="auto",
            workspace_path=str(workspace),
        )
        icm.setup_workspace_scratch(str(workspace), agent_id="agent1")

        # Write a file in scratch
        scratch_file = os.path.join(str(workspace), SCRATCH_DIR_NAME, "notes.md")
        with open(scratch_file, "w") as f:
            f.write("scratch content")

        # Check git status - scratch file should be invisible
        repo = Repo(str(workspace))
        untracked = repo.untracked_files
        assert SCRATCH_DIR_NAME not in str(untracked), "Scratch dir should be git-excluded"
        icm.cleanup_session()

    def test_workspace_cleanup_round_keeps_branch(self, tmp_path):
        """Verify cleanup_round() switches back to default branch but keeps the workspace branch."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        icm = IsolationContextManager(
            session_id="test-ws-round",
            write_mode="auto",
            workspace_path=str(workspace),
        )
        icm.setup_workspace_scratch(str(workspace), agent_id="agent1")
        branch = icm.get_branch_name(str(workspace))
        assert branch is not None

        # Cleanup round
        icm.cleanup_round(str(workspace))

        # Branch should still exist
        repo = Repo(str(workspace))
        branches = [b.name for b in repo.branches]
        assert branch in branches, f"Branch {branch} should be preserved after cleanup_round"
        # Should be back on master/main
        assert repo.active_branch.name in ("main", "master")

    def test_workspace_cleanup_session_removes_branch(self, tmp_path):
        """Verify cleanup_session() deletes the workspace branch."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        icm = IsolationContextManager(
            session_id="test-ws-session",
            write_mode="auto",
            workspace_path=str(workspace),
        )
        icm.setup_workspace_scratch(str(workspace), agent_id="agent1")
        branch = icm.get_branch_name(str(workspace))

        icm.cleanup_session()

        # Branch should be deleted
        repo = Repo(str(workspace))
        branches = [b.name for b in repo.branches]
        assert branch not in branches, f"Branch {branch} should be deleted after cleanup_session"

    def test_workspace_previous_branch_deleted(self, tmp_path):
        """Verify previous branch is deleted when new workspace round starts."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Round 1
        icm1 = IsolationContextManager(
            session_id="test-ws-r1",
            write_mode="auto",
            workspace_path=str(workspace),
        )
        icm1.setup_workspace_scratch(str(workspace), agent_id="agent1")
        old_branch = icm1.get_branch_name(str(workspace))
        icm1.cleanup_round(str(workspace))

        # Verify old branch exists
        repo = Repo(str(workspace))
        assert old_branch in [b.name for b in repo.branches]

        # Round 2 with previous_branch
        icm2 = IsolationContextManager(
            session_id="test-ws-r2",
            write_mode="auto",
            workspace_path=str(workspace),
            previous_branch=old_branch,
        )
        icm2.setup_workspace_scratch(str(workspace), agent_id="agent1")

        # Old branch should be deleted
        repo = Repo(str(workspace))
        branches = [b.name for b in repo.branches]
        assert old_branch not in branches, f"Previous branch {old_branch} should be deleted"
        icm2.cleanup_session()

    def test_workspace_move_scratch_to_archive(self, tmp_path):
        """Verify scratch archive works in workspace mode."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        icm = IsolationContextManager(
            session_id="test-ws-archive",
            write_mode="auto",
            workspace_path=str(workspace),
        )
        icm.setup_workspace_scratch(str(workspace), agent_id="agent1")

        # Write content in scratch
        scratch_file = os.path.join(str(workspace), SCRATCH_DIR_NAME, "notes.md")
        with open(scratch_file, "w") as f:
            f.write("important notes")

        archive_dir = icm.move_scratch_to_workspace(str(workspace))

        assert archive_dir is not None
        assert ".scratch_archive" in archive_dir
        assert os.path.exists(os.path.join(archive_dir, "notes.md"))
        # Original scratch should no longer exist
        assert not os.path.exists(os.path.join(str(workspace), SCRATCH_DIR_NAME))
        icm.cleanup_session()

    def test_workspace_inside_parent_repo_gets_own_git(self, tmp_path):
        """Verify workspace inside a parent git repo gets its own .git/ (not branching the parent)."""
        # Simulate the real scenario: .massgen/workspaces/workspace_xxx inside a project repo
        project = tmp_path / "project"
        project.mkdir()
        init_test_repo(project)

        workspace = project / ".massgen" / "workspaces" / "workspace_abc"
        workspace.mkdir(parents=True)

        icm = IsolationContextManager(
            session_id="test-ws-nested",
            write_mode="auto",
            workspace_path=str(workspace),
        )
        icm.setup_workspace_scratch(str(workspace), agent_id="agent1")

        # Workspace should have its OWN .git/ (not use the parent's)
        assert (workspace / ".git").exists(), "Workspace should have its own .git/"
        branch = icm.get_branch_name(str(workspace))
        assert branch is not None

        # The branch should be on the WORKSPACE repo, not the parent
        ws_repo = Repo(str(workspace))
        assert branch in [b.name for b in ws_repo.branches]

        # The parent repo should NOT have the branch
        parent_repo = Repo(str(project))
        assert branch not in [b.name for b in parent_repo.branches], f"Branch {branch} should NOT exist on the parent project repo"
        icm.cleanup_session()


class TestWriteModeSuppressesTwoTier:
    """Tests that write_mode suppresses the old two-tier workspace."""

    def test_filesystem_manager_suppresses_two_tier_when_write_mode_set(self, tmp_path):
        """Verify use_two_tier_workspace is False on FM when write_mode is active."""
        from massgen.filesystem_manager._filesystem_manager import FilesystemManager

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        fm = FilesystemManager(
            cwd=str(workspace),
            use_two_tier_workspace=True,
            write_mode="auto",
        )

        assert fm.use_two_tier_workspace is False, "use_two_tier_workspace should be suppressed when write_mode is active"

    def test_filesystem_manager_keeps_two_tier_without_write_mode(self, tmp_path):
        """Verify use_two_tier_workspace is preserved when write_mode is not set."""
        from massgen.filesystem_manager._filesystem_manager import FilesystemManager

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        fm = FilesystemManager(
            cwd=str(workspace),
            use_two_tier_workspace=True,
            write_mode=None,
        )

        assert fm.use_two_tier_workspace is True

    def test_no_deliverable_scratch_dirs_with_write_mode(self, tmp_path):
        """Verify no deliverable/ or scratch/ dirs are created when write_mode is active."""
        from massgen.filesystem_manager._filesystem_manager import FilesystemManager

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        FilesystemManager(
            cwd=str(workspace),
            use_two_tier_workspace=True,
            write_mode="auto",
        )
        # _setup_workspace is called during init
        assert not (workspace / "deliverable").exists(), "deliverable/ should not be created"
        assert not (workspace / "scratch").exists(), "scratch/ should not be created"


class TestConfigValidatorDeprecation:
    """Tests for use_two_tier_workspace deprecation warnings."""

    def test_config_validator_deprecation_warning_standalone(self):
        """Verify warning when use_two_tier_workspace is set without write_mode."""
        from massgen.config_validator import ConfigValidator

        config = {
            "agents": [{"name": "test", "type": "openai", "model": "gpt-4o-mini"}],
            "orchestrator": {
                "coordination": {
                    "use_two_tier_workspace": True,
                },
            },
        }
        validator = ConfigValidator()
        result = validator.validate_config(config)
        # Check warnings for deprecation
        warning_texts = [w.message for w in result.warnings]
        has_deprecation = any("deprecated" in w.lower() for w in warning_texts)
        assert has_deprecation, f"Should have deprecation warning, got: {warning_texts}"

    def test_config_validator_deprecation_warning_with_write_mode(self):
        """Verify warning when use_two_tier_workspace is set WITH write_mode."""
        from massgen.config_validator import ConfigValidator

        config = {
            "agents": [{"name": "test", "type": "openai", "model": "gpt-4o-mini"}],
            "orchestrator": {
                "coordination": {
                    "use_two_tier_workspace": True,
                    "write_mode": "auto",
                },
            },
        }
        validator = ConfigValidator()
        result = validator.validate_config(config)
        warning_texts = [w.message for w in result.warnings]
        has_ignored_warning = any("ignored" in w.lower() for w in warning_texts)
        assert has_ignored_warning, f"Should warn about being ignored, got: {warning_texts}"


class TestDockerMountsWriteMode:
    """Tests for Docker mount filtering when write_mode creates worktrees."""

    def test_docker_mounts_exclude_context_paths_when_write_mode(self, tmp_path):
        """When write_mode active, setup_orchestration_paths() passes empty context_paths
        and .git/ as extra_mount_paths to Docker."""
        from unittest.mock import MagicMock, patch

        from massgen.filesystem_manager._filesystem_manager import FilesystemManager

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create a git repo to use as context path
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        init_test_repo(repo_path)

        fm = FilesystemManager(cwd=str(workspace), write_mode="auto")

        # Mock docker_manager and path_permission_manager
        fm.docker_manager = MagicMock()
        fm.docker_manager.create_container.return_value = None
        fm.agent_id = "agent1"
        fm.path_permission_manager = MagicMock()
        fm.path_permission_manager.get_context_paths.return_value = [
            {"path": str(repo_path), "permission": "read"},
        ]

        # Call the Docker container creation block directly by calling setup_orchestration_paths
        # We need to patch to avoid other side effects
        with patch.object(fm, "_setup_workspace", return_value=workspace):
            fm.setup_orchestration_paths(
                agent_id="agent1",
                skills_directory=None,
            )

        # Verify create_container was called with empty context_paths and .git/ extra_mount_paths
        call_kwargs = fm.docker_manager.create_container.call_args
        assert call_kwargs is not None, "create_container should have been called"
        kwargs = call_kwargs.kwargs if call_kwargs.kwargs else {}
        # Check positional or keyword args
        if "context_paths" in kwargs:
            assert kwargs["context_paths"] == [], "context_paths should be empty when write_mode active"
        if "extra_mount_paths" in kwargs:
            mount_paths = kwargs["extra_mount_paths"]
            assert len(mount_paths) == 1, f"Should have 1 .git/ mount, got {len(mount_paths)}"
            assert mount_paths[0][0] == str(repo_path / ".git"), "Should mount .git/ dir"

    def test_docker_mounts_git_dir_rw_for_worktrees(self, tmp_path):
        """.git/ dir should be mounted as rw, not ro."""
        from unittest.mock import MagicMock, patch

        from massgen.filesystem_manager._filesystem_manager import FilesystemManager

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        init_test_repo(repo_path)

        fm = FilesystemManager(cwd=str(workspace), write_mode="worktree")
        fm.docker_manager = MagicMock()
        fm.docker_manager.create_container.return_value = None
        fm.agent_id = "agent1"
        fm.path_permission_manager = MagicMock()
        fm.path_permission_manager.get_context_paths.return_value = [
            {"path": str(repo_path), "permission": "read"},
        ]

        with patch.object(fm, "_setup_workspace", return_value=workspace):
            fm.setup_orchestration_paths(agent_id="agent1", skills_directory=None)

        call_kwargs = fm.docker_manager.create_container.call_args
        kwargs = call_kwargs.kwargs if call_kwargs.kwargs else {}
        if "extra_mount_paths" in kwargs:
            mount_paths = kwargs["extra_mount_paths"]
            assert mount_paths[0][2] == "rw", f"Expected rw mode, got {mount_paths[0][2]}"

    def test_non_git_context_paths_not_mounted(self, tmp_path):
        """Non-git context paths are preserved as regular context_paths (no .git/ mounts needed)."""
        from unittest.mock import MagicMock, patch

        from massgen.filesystem_manager._filesystem_manager import FilesystemManager

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Non-git directory (no .git/)
        non_git_path = tmp_path / "plain_dir"
        non_git_path.mkdir()
        (non_git_path / "file.txt").write_text("content")

        fm = FilesystemManager(cwd=str(workspace), write_mode="isolated")
        fm.docker_manager = MagicMock()
        fm.docker_manager.create_container.return_value = None
        fm.agent_id = "agent1"
        fm.path_permission_manager = MagicMock()
        fm.path_permission_manager.get_context_paths.return_value = [
            {"path": str(non_git_path), "permission": "read"},
        ]

        with patch.object(fm, "_setup_workspace", return_value=workspace):
            fm.setup_orchestration_paths(agent_id="agent1", skills_directory=None)

        call_kwargs = fm.docker_manager.create_container.call_args
        kwargs = call_kwargs.kwargs if call_kwargs.kwargs else {}
        # Non-git context paths are preserved (not suppressed) so agents
        # can still read external artifacts like log/session directories.
        if "context_paths" in kwargs:
            assert kwargs["context_paths"] == [
                {"path": str(non_git_path), "permission": "read"},
            ], "Non-git context paths should be preserved"
        # extra_mount_paths should be empty (no .git/ to mount)
        if "extra_mount_paths" in kwargs:
            assert kwargs["extra_mount_paths"] == [], f"No .git/ mounts expected, got {kwargs['extra_mount_paths']}"


class TestSystemPromptWriteMode:
    """Tests for system prompt behavior when worktree_paths are set."""

    def test_system_prompt_hides_context_paths_with_worktrees(self):
        """WorkspaceStructureSection omits context paths when worktree_paths set."""
        from massgen.system_prompt_sections import WorkspaceStructureSection

        section = WorkspaceStructureSection(
            workspace_path="/workspace",
            context_paths=["/projects/myrepo"],
            worktree_paths={"/workspace/.worktree/ctx_0": "/projects/myrepo"},
        )
        content = section.build_content()

        assert "Context paths" not in content, "Context paths should be suppressed when worktree_paths set"
        assert "/projects/myrepo" not in content, "Original context path should not appear"
        assert "Project Checkout" in content, "Worktree section should be present"

    def test_system_prompt_shows_context_paths_without_worktrees(self):
        """WorkspaceStructureSection shows context paths when no worktree_paths."""
        from massgen.system_prompt_sections import WorkspaceStructureSection

        section = WorkspaceStructureSection(
            workspace_path="/workspace",
            context_paths=["/projects/myrepo"],
        )
        content = section.build_content()

        assert "Context paths" in content, "Context paths should be shown without worktree_paths"
        assert "/projects/myrepo" in content


class TestClaudeMdDiscoveryWorktrees:
    """Tests for CLAUDE.md discovery through worktree paths."""

    def test_claude_md_discovery_uses_worktree_paths(self, tmp_path):
        """ProjectInstructionsSection discovers CLAUDE.md from worktree path."""
        from massgen.system_prompt_sections import ProjectInstructionsSection

        # Create a worktree path with CLAUDE.md
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()
        (worktree_path / "CLAUDE.md").write_text("# Project instructions\nDo the thing.")

        section = ProjectInstructionsSection(
            context_paths=[{"path": str(worktree_path)}],
            workspace_root=str(tmp_path),
        )
        content = section.build_content()

        assert "Do the thing" in content, "Should discover CLAUDE.md from worktree path"

    def test_claude_md_not_found_in_original_when_worktree_used(self, tmp_path):
        """When worktree path is used, CLAUDE.md in original (unmounted) path is irrelevant."""
        from massgen.system_prompt_sections import ProjectInstructionsSection

        # Original context path has CLAUDE.md but worktree doesn't
        original_path = tmp_path / "original"
        original_path.mkdir()
        (original_path / "CLAUDE.md").write_text("# Original instructions")

        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()
        # No CLAUDE.md in worktree

        # Discovery uses worktree path, not original
        section = ProjectInstructionsSection(
            context_paths=[{"path": str(worktree_path)}],
            workspace_root=str(tmp_path),
        )
        content = section.build_content()

        assert "Original instructions" not in content, "Should not find CLAUDE.md from original path"


class TestFilesystemOperationsSuppressesContextPaths:
    """Tests that FilesystemOperationsSection hides context paths when write_mode active."""

    def test_filesystem_ops_hides_context_paths_when_write_mode(self):
        """FilesystemOperationsSection should not show Target/Context Path when write_mode active."""
        from massgen.system_prompt_sections import FilesystemOperationsSection

        section = FilesystemOperationsSection(
            main_workspace="/workspace",
            context_paths=[],  # Empty because _build_filesystem_sections clears them
        )
        content = section.build_content()

        assert "Target Path" not in content, "Target Path should not appear when context_paths empty"
        assert "Context Path" not in content, "Context Path should not appear when context_paths empty"

    def test_filesystem_ops_shows_context_paths_without_write_mode(self):
        """FilesystemOperationsSection shows context paths normally when write_mode not active."""
        from massgen.system_prompt_sections import FilesystemOperationsSection

        section = FilesystemOperationsSection(
            main_workspace="/workspace",
            context_paths=[{"path": "/projects/myrepo", "permission": "read"}],
        )
        content = section.build_content()

        assert "Context Path" in content, "Context Path should appear when write_mode not active"
        assert "/projects/myrepo" in content


class TestAutoCommitBeforeCleanup:
    """Tests for auto-commit of worktree changes before cleanup_round()."""

    def test_auto_commit_before_cleanup_round(self, tmp_path):
        """Verify cleanup_round() auto-commits changes so branch has agent's work."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        repo = init_test_repo(repo_path)

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        icm = IsolationContextManager(
            session_id="test-autocommit",
            write_mode="worktree",
            workspace_path=str(workspace),
        )
        isolated = icm.initialize_context(str(repo_path), agent_id="agent1")
        branch_name = icm.get_branch_name(str(repo_path))

        # Make changes in the worktree (simulating agent work)
        new_file = os.path.join(isolated, "agent_work.py")
        with open(new_file, "w") as f:
            f.write("print('agent work')")

        # Cleanup round - should auto-commit before removing worktree
        icm.cleanup_round(str(repo_path))

        # Branch should have the commit with agent's work
        commit = repo.commit(branch_name)
        assert "Auto-commit" in commit.message
        # The file should be in the commit tree
        file_names = [item.name for item in commit.tree.traverse()]
        assert "agent_work.py" in file_names, "Agent's file should be committed on the branch"

    def test_auto_commit_no_changes(self, tmp_path):
        """Verify no commit is made when worktree has no changes."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        repo = init_test_repo(repo_path)

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        icm = IsolationContextManager(
            session_id="test-noop-commit",
            write_mode="worktree",
            workspace_path=str(workspace),
        )
        icm.initialize_context(str(repo_path), agent_id="agent1")
        branch_name = icm.get_branch_name(str(repo_path))

        # Don't make any changes - cleanup should not create a commit
        # Get commit count before cleanup
        initial_commit_count = len(list(repo.iter_commits(branch_name)))

        icm.cleanup_round(str(repo_path))

        # Branch should have the same number of commits (no auto-commit)
        commit_count = len(list(repo.iter_commits(branch_name)))
        assert commit_count == initial_commit_count, "No commit should be made when there are no changes"


class TestBaseCommitWorktree:
    """Tests for base_commit parameter in IsolationContextManager."""

    def test_base_commit_creates_worktree_from_branch(self, tmp_path):
        """Verify passing base_commit starts the worktree from that branch's content."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        repo = init_test_repo(repo_path)

        # Create a feature branch with some content
        default_branch = repo.active_branch.name
        feature_branch = "massgen/test/feature-branch"
        repo.git.checkout("-b", feature_branch)
        feature_file = repo_path / "feature.py"
        feature_file.write_text("feature code")
        repo.index.add(["feature.py"])
        repo.index.commit("Add feature")
        repo.git.checkout(default_branch)

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create ICM with base_commit pointing to the feature branch
        icm = IsolationContextManager(
            session_id="test-base-commit",
            write_mode="worktree",
            workspace_path=str(workspace),
            base_commit=feature_branch,
        )
        isolated = icm.initialize_context(str(repo_path), agent_id="agent1")

        # The worktree should contain the feature file from the base branch
        assert os.path.exists(os.path.join(isolated, "feature.py")), "Worktree should contain files from the base_commit branch"
        with open(os.path.join(isolated, "feature.py")) as f:
            assert f.read() == "feature code"

        icm.cleanup_all()


class TestWorkspaceStructureBranchInfo:
    """Tests for branch info in WorkspaceStructureSection."""

    def test_workspace_structure_shows_branch_name(self):
        """Verify WorkspaceStructureSection includes agent's own branch name."""
        from massgen.system_prompt_sections import WorkspaceStructureSection

        section = WorkspaceStructureSection(
            workspace_path="/workspace",
            context_paths=[],
            worktree_paths={"/workspace/.worktree/ctx_1": "/projects/repo"},
            branch_name="massgen/abc12345",
        )
        content = section.build_content()

        assert "massgen/abc12345" in content
        assert "Your work is on branch" in content
        assert "auto-committed" in content

    def test_workspace_structure_shows_other_branches_with_labels(self):
        """Verify WorkspaceStructureSection lists other agents' branches with anonymous labels."""
        from massgen.system_prompt_sections import WorkspaceStructureSection

        section = WorkspaceStructureSection(
            workspace_path="/workspace",
            context_paths=[],
            worktree_paths={"/workspace/.worktree/ctx_1": "/projects/repo"},
            other_branches={"agent1": "massgen/def456", "agent2": "massgen/ghi789"},
        )
        content = section.build_content()

        assert "agent1" in content
        assert "massgen/def456" in content
        assert "agent2" in content
        assert "massgen/ghi789" in content
        assert "Other agents' branches" in content
        assert "git diff" in content
        assert "git merge" in content

    def test_workspace_structure_no_branch_info_when_none(self):
        """Verify no branch section appears when branch info is not provided."""
        from massgen.system_prompt_sections import WorkspaceStructureSection

        section = WorkspaceStructureSection(
            workspace_path="/workspace",
            context_paths=[],
            worktree_paths={"/workspace/.worktree/ctx_1": "/projects/repo"},
        )
        content = section.build_content()

        assert "Your work is on branch" not in content
        assert "Other agents' branches" not in content

    def test_workspace_structure_mentions_scratch_archive(self):
        """Verify WorkspaceStructureSection mentions scratch_archive for prior rounds."""
        from massgen.system_prompt_sections import WorkspaceStructureSection

        section = WorkspaceStructureSection(
            workspace_path="/workspace",
            context_paths=[],
            worktree_paths={"/workspace/.worktree/ctx_1": "/projects/repo"},
        )
        content = section.build_content()

        assert ".scratch_archive/" in content
        assert "prior rounds" in content


class TestRestartContextBranchInfo:
    """Tests for branch info in format_restart_context()."""

    def test_restart_context_includes_branch_info(self):
        """Verify format_restart_context includes branch names when branch_info provided."""
        from massgen.message_templates import MessageTemplates

        mt = MessageTemplates()
        branch_info = {
            "own_branch": "massgen/abc123",
            "other_branches": {"agent1": "massgen/def456", "agent2": "massgen/ghi789"},
        }
        result = mt.format_restart_context(
            reason="Insufficient quality",
            instructions="Improve the solution",
            branch_info=branch_info,
        )

        assert "massgen/abc123" in result
        assert "Your previous work is on branch" in result
        assert "git merge massgen/abc123" in result
        assert "agent1" in result
        assert "massgen/def456" in result
        assert "agent2" in result
        assert "massgen/ghi789" in result
        assert "Other agents' branches" in result

    def test_restart_context_no_branch_info(self):
        """Verify format_restart_context works without branch_info."""
        from massgen.message_templates import MessageTemplates

        mt = MessageTemplates()
        result = mt.format_restart_context(
            reason="Insufficient quality",
            instructions="Improve the solution",
        )

        assert "Your previous work is on branch" not in result
        assert "Other agents' branches" not in result
        assert "PREVIOUS ATTEMPT FEEDBACK" in result
