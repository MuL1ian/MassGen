# -*- coding: utf-8 -*-
"""
Git discovery and utility functions using GitPython.
"""

import os
from typing import Any, Dict, List, Optional

from git import InvalidGitRepositoryError, Repo


def get_git_root(path: str) -> Optional[str]:
    """
    Find the root of the git repository containing the given path.

    Args:
        path: Directory path to check

    Returns:
        Absolute path to git root, or None if not in a git repo
    """
    if not os.path.exists(path):
        return None

    try:
        repo = Repo(path, search_parent_directories=True)
        return repo.working_tree_dir
    except InvalidGitRepositoryError:
        return None


def get_git_branch(path: str) -> Optional[str]:
    """
    Get the current git branch name.

    Args:
        path: Path within the git repository

    Returns:
        Branch name, or None if not in a git repo or detached HEAD
    """
    try:
        repo = Repo(path, search_parent_directories=True)
        if repo.head.is_detached:
            return None
        return repo.active_branch.name
    except (InvalidGitRepositoryError, TypeError):
        return None


def get_git_status(path: str) -> Dict[str, bool]:
    """
    Get current git status (dirty, untracked).

    Args:
        path: Path within the git repository

    Returns:
        Dictionary with 'is_dirty' and 'has_untracked' flags
    """
    status: Dict[str, Any] = {"is_dirty": False, "has_untracked": False}
    try:
        repo = Repo(path, search_parent_directories=True)
        status["is_dirty"] = repo.is_dirty()
        status["has_untracked"] = len(repo.untracked_files) > 0
    except InvalidGitRepositoryError:
        pass
    return status


def get_current_commit(path: str) -> Optional[str]:
    """
    Get the current commit SHA.

    Args:
        path: Path within the git repository

    Returns:
        Full commit SHA, or None if not in a git repo
    """
    try:
        repo = Repo(path, search_parent_directories=True)
        return repo.head.commit.hexsha
    except (InvalidGitRepositoryError, ValueError):
        return None


def is_git_repo(path: str) -> bool:
    """Check if the given path is inside a git repository."""
    return get_git_root(path) is not None


def get_repo(path: str) -> Optional[Repo]:
    """
    Get a Repo object for the given path.

    Args:
        path: Path within the git repository

    Returns:
        Repo object, or None if not in a git repo
    """
    try:
        return Repo(path, search_parent_directories=True)
    except InvalidGitRepositoryError:
        return None


def get_changes(repo: Repo) -> List[Dict[str, str]]:
    """
    Get list of all changes (staged, unstaged, untracked) in a repo.

    Args:
        repo: GitPython Repo object

    Returns:
        List of dicts with 'status' and 'path' keys
    """
    changes = []

    # Unstaged changes (working tree vs index)
    for diff in repo.index.diff(None):
        changes.append(
            {
                "status": diff.change_type[0].upper(),  # M, A, D, R, etc.
                "path": diff.a_path or diff.b_path,
            },
        )

    # Untracked files
    for path in repo.untracked_files:
        changes.append({"status": "?", "path": path})

    return changes
