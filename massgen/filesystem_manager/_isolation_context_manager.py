# -*- coding: utf-8 -*-
"""
Isolation Context Manager for MassGen - Manages isolated write contexts for agents.

This module provides isolated write environments using git worktrees (for git repos)
or shadow repositories (for non-git directories). This enables safe review and
approval workflows before changes are applied to the original context.
"""

import logging
import os
import tempfile
from typing import Any, Dict, List, Optional

from ..infrastructure import ShadowRepo, WorktreeManager, is_git_repo

# Use module-level logger
log = logging.getLogger(__name__)


class IsolationContextManager:
    """
    Manages isolated write contexts for agent changes.

    This class creates isolated environments where agents can make changes
    without affecting the original files. Changes can be reviewed and
    selectively applied later.

    Supports two isolation modes:
    - Worktree: Uses git worktrees for git repositories (efficient, branch-based)
    - Shadow: Creates temporary git repos for non-git directories (full copy)
    """

    def __init__(
        self,
        session_id: str,
        write_mode: str = "auto",
        temp_base: Optional[str] = None,
        workspace_path: Optional[str] = None,
    ):
        """
        Initialize the IsolationContextManager.

        Args:
            session_id: Unique session identifier for naming branches/repos
            write_mode: Isolation mode - "auto", "worktree", "isolated", or "legacy"
            temp_base: Optional base directory for temporary files
            workspace_path: Optional agent workspace path. When set, worktrees are
                created inside {workspace_path}/.worktree/ instead of temp directories.
                This makes the worktree accessible to the agent as a workspace subdirectory.
        """
        self.session_id = session_id
        self.write_mode = write_mode
        self.temp_base = temp_base
        self.workspace_path = workspace_path

        # Track active contexts: original_path -> context info
        self._contexts: Dict[str, Dict[str, Any]] = {}

        # Track WorktreeManager instances by repo root
        self._worktree_managers: Dict[str, WorktreeManager] = {}

        # Counter for unique branch names
        self._branch_counter = 0

        log.info(f"IsolationContextManager initialized: session={session_id}, mode={write_mode}")

    def initialize_context(self, context_path: str, agent_id: Optional[str] = None) -> str:
        """
        Initialize an isolated context for the given path.

        Args:
            context_path: Original path to create isolated context for
            agent_id: Optional agent ID for context naming

        Returns:
            Path to the isolated context (where agent should write)

        Raises:
            ValueError: If write_mode is invalid or context already exists
            RuntimeError: If isolation setup fails
        """
        context_path = os.path.abspath(context_path)

        if context_path in self._contexts:
            # Return existing isolated path
            return self._contexts[context_path]["isolated_path"]

        if self.write_mode == "legacy":
            # No isolation - return original path
            self._contexts[context_path] = {
                "isolated_path": context_path,
                "mode": "legacy",
                "manager": None,
            }
            return context_path

        # Determine actual mode for "auto"
        actual_mode = self._determine_mode(context_path)

        if actual_mode == "worktree":
            isolated_path = self._create_worktree_context(context_path, agent_id)
        elif actual_mode == "shadow":
            isolated_path = self._create_shadow_context(context_path, agent_id)
        else:
            # Fallback to legacy (direct writes)
            isolated_path = context_path
            actual_mode = "legacy"
            self._contexts[context_path] = {
                "isolated_path": isolated_path,
                "mode": actual_mode,
                "manager": None,
                "agent_id": agent_id,
            }

        # Note: _create_worktree_context and _create_shadow_context set self._contexts
        log.info(f"Created isolated context: {context_path} -> {isolated_path} (mode={actual_mode})")
        return isolated_path

    def _determine_mode(self, context_path: str) -> str:
        """Determine the actual isolation mode based on write_mode and path type."""
        if self.write_mode == "worktree":
            if is_git_repo(context_path):
                return "worktree"
            else:
                log.warning(f"Path {context_path} is not a git repo, falling back to shadow mode")
                return "shadow"

        if self.write_mode == "isolated":
            return "shadow"

        if self.write_mode == "auto":
            if is_git_repo(context_path):
                return "worktree"
            else:
                return "shadow"

        # Unknown mode - fallback to legacy
        log.warning(f"Unknown write_mode: {self.write_mode}, falling back to legacy")
        return "legacy"

    def _create_worktree_context(self, context_path: str, agent_id: Optional[str]) -> str:
        """Create a git worktree for the context path."""
        from ..utils.git_utils import get_git_root

        repo_root = get_git_root(context_path)
        if not repo_root:
            raise RuntimeError(f"Cannot create worktree: {context_path} is not in a git repo")

        # Get or create WorktreeManager for this repo
        if repo_root not in self._worktree_managers:
            self._worktree_managers[repo_root] = WorktreeManager(repo_root)

        wm = self._worktree_managers[repo_root]

        # Generate unique branch name
        self._branch_counter += 1
        agent_suffix = f"-{agent_id}" if agent_id else ""
        branch_name = f"massgen-{self.session_id}{agent_suffix}-{self._branch_counter}"

        # Create worktree path - prefer workspace if available
        if self.workspace_path:
            # Create worktree inside agent workspace at .worktree/ctx_N
            worktree_dir = os.path.join(self.workspace_path, ".worktree")
            os.makedirs(worktree_dir, exist_ok=True)
            worktree_path = os.path.join(worktree_dir, f"ctx_{self._branch_counter}")
        else:
            # Fallback: use temp directory (Docker mode or no workspace)
            if self.temp_base:
                worktree_base = self.temp_base
            else:
                worktree_base = tempfile.gettempdir()

            worktree_path = tempfile.mkdtemp(
                prefix=f"massgen_worktree_{self._branch_counter}_",
                dir=worktree_base,
            )
            # Remove the dir since git worktree add will create it
            os.rmdir(worktree_path)

        try:
            isolated_path = wm.create_worktree(worktree_path, branch_name)

            # Store manager reference for cleanup
            self._contexts[context_path] = {
                "isolated_path": isolated_path,
                "original_path": context_path,
                "mode": "worktree",
                "manager": wm,
                "branch_name": branch_name,
                "repo_root": repo_root,
                "agent_id": agent_id,
            }

            return isolated_path

        except Exception as e:
            log.error(f"Failed to create worktree: {e}")
            raise RuntimeError(f"Failed to create worktree context: {e}")

    def _create_shadow_context(self, context_path: str, agent_id: Optional[str]) -> str:
        """Create a shadow repository for the context path."""
        try:
            shadow = ShadowRepo(context_path, temp_base=self.temp_base)
            isolated_path = shadow.initialize()

            # Store shadow repo reference for cleanup
            self._contexts[context_path] = {
                "isolated_path": isolated_path,
                "mode": "shadow",
                "manager": shadow,
                "agent_id": agent_id,
            }

            return isolated_path

        except Exception as e:
            log.error(f"Failed to create shadow repo: {e}")
            raise RuntimeError(f"Failed to create shadow context: {e}")

    def get_isolated_path(self, original_path: str) -> Optional[str]:
        """
        Get the isolated path for a given original path.

        Args:
            original_path: Original context path

        Returns:
            Isolated path if context exists, None otherwise
        """
        original_path = os.path.abspath(original_path)
        if original_path in self._contexts:
            return self._contexts[original_path]["isolated_path"]
        return None

    def get_changes(self, context_path: str) -> List[Dict[str, Any]]:
        """
        Get list of changes in the isolated context.

        Args:
            context_path: Original context path

        Returns:
            List of change dicts with 'status', 'path' keys
        """
        context_path = os.path.abspath(context_path)
        if context_path not in self._contexts:
            return []

        ctx = self._contexts[context_path]
        mode = ctx.get("mode")
        manager = ctx.get("manager")

        if mode == "legacy" or manager is None:
            return []

        if mode == "shadow" and isinstance(manager, ShadowRepo):
            return manager.get_changes()

        # For worktree, use shared git_utils
        if mode == "worktree":
            from git import InvalidGitRepositoryError, Repo

            from ..utils.git_utils import get_changes as git_get_changes

            isolated_path = ctx["isolated_path"]
            try:
                repo = Repo(isolated_path)
                return git_get_changes(repo)
            except InvalidGitRepositoryError:
                return []

        return []

    def get_diff(self, context_path: str, staged: bool = False) -> str:
        """
        Get the diff of changes in the isolated context.

        Args:
            context_path: Original context path
            staged: If True, show staged changes only

        Returns:
            Git diff output as string
        """
        context_path = os.path.abspath(context_path)
        if context_path not in self._contexts:
            return ""

        ctx = self._contexts[context_path]
        mode = ctx.get("mode")

        if mode == "legacy":
            return ""

        if mode == "shadow":
            manager = ctx.get("manager")
            if isinstance(manager, ShadowRepo):
                return manager.get_diff(staged=staged)

        if mode == "worktree":
            from git import GitCommandError, InvalidGitRepositoryError, Repo

            isolated_path = ctx["isolated_path"]
            try:
                repo = Repo(isolated_path)
                if staged:
                    return repo.git.diff("--staged")
                # Stage everything so untracked (new) files appear in the diff,
                # then unstage so ChangeApplier can still detect changes via
                # repo.index.diff(None) and repo.untracked_files.
                repo.git.add("-A")
                diff_output = repo.git.diff("--staged")
                repo.git.reset("HEAD")
                return diff_output
            except (InvalidGitRepositoryError, GitCommandError):
                return ""

        return ""

    def cleanup(self, context_path: Optional[str] = None) -> None:
        """
        Cleanup isolated context(s).

        Args:
            context_path: Specific context to cleanup, or None for all
        """
        if context_path:
            context_path = os.path.abspath(context_path)
            if context_path in self._contexts:
                self._cleanup_single_context(context_path)
        else:
            self.cleanup_all()

    def _cleanup_single_context(self, context_path: str) -> None:
        """Cleanup a single isolated context."""
        if context_path not in self._contexts:
            return

        ctx = self._contexts[context_path]
        mode = ctx.get("mode")

        if mode == "shadow":
            manager = ctx.get("manager")
            if isinstance(manager, ShadowRepo):
                manager.cleanup()

        elif mode == "worktree":
            manager = ctx.get("manager")
            isolated_path = ctx.get("isolated_path")
            if isinstance(manager, WorktreeManager) and isolated_path:
                try:
                    manager.remove_worktree(isolated_path, force=True, delete_branch=True)
                except Exception as e:
                    log.warning(f"Failed to cleanup worktree {isolated_path}: {e}")

        del self._contexts[context_path]
        log.info(f"Cleaned up isolated context: {context_path}")

    def cleanup_all(self) -> None:
        """Cleanup all isolated contexts."""
        # Copy keys to avoid modification during iteration
        paths = list(self._contexts.keys())
        for context_path in paths:
            self._cleanup_single_context(context_path)

        # Prune any stale worktree metadata
        for wm in self._worktree_managers.values():
            try:
                wm.prune()
            except Exception:
                pass

        self._worktree_managers.clear()
        log.info("Cleaned up all isolated contexts")

    def get_context_info(self, context_path: str) -> Optional[Dict[str, Any]]:
        """
        Get information about an isolated context.

        Args:
            context_path: Original context path

        Returns:
            Context info dict or None if not found
        """
        context_path = os.path.abspath(context_path)
        if context_path in self._contexts:
            ctx = self._contexts[context_path]
            return {
                "original_path": context_path,
                "isolated_path": ctx.get("isolated_path"),
                "mode": ctx.get("mode"),
                "agent_id": ctx.get("agent_id"),
                "repo_root": ctx.get("repo_root"),
            }
        return None

    def list_contexts(self) -> List[Dict[str, Any]]:
        """
        List all active isolated contexts.

        Returns:
            List of context info dicts
        """
        return [self.get_context_info(path) for path in self._contexts.keys()]

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup all contexts."""
        self.cleanup_all()
        return False
