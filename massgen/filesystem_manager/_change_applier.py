# -*- coding: utf-8 -*-
"""
Change Applier for MassGen - Applies changes from isolated context to original paths.

This module provides the ChangeApplier class for applying approved changes from
an isolated write context (worktree or shadow repo) to the original context path.
"""

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


@dataclass
class ReviewResult:
    """Result from the change review process.

    Attributes:
        approved: Whether the user approved applying changes
        approved_files: List of specific files to apply (None = all files)
        comments: Optional user comments about the review
        metadata: Optional additional metadata from the review
    """

    approved: bool
    approved_files: Optional[List[str]] = None
    comments: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


class ChangeApplier:
    """Applies approved changes from isolated context to original paths.

    This class handles the transfer of changes from an isolated write context
    (git worktree or shadow repository) back to the original context path,
    respecting user approval decisions on a per-file basis.
    """

    def apply_changes(
        self,
        source_path: str,
        target_path: str,
        approved_files: Optional[List[str]] = None,
        context_prefix: Optional[str] = None,
    ) -> List[str]:
        """
        Apply changes from source (isolated) to target (original).

        Args:
            source_path: Isolated context path (worktree or shadow repo)
            target_path: Original context path
            approved_files: List of relative paths to apply (None = all changes)
            context_prefix: Optional repo-relative path prefix that constrains
                which changed files are eligible to apply. Use this to enforce
                context-path boundaries when source is a full repo checkout.

        Returns:
            List of applied file paths (relative to target)
        """
        source = Path(source_path)
        target = Path(target_path)
        applied: List[str] = []

        if not source.exists():
            log.warning(f"Source path does not exist: {source_path}")
            return applied

        if not target.exists():
            log.warning(f"Target path does not exist: {target_path}")
            return applied

        try:
            # Try to use git to get accurate change list
            applied = self._apply_git_changes(
                source,
                target,
                approved_files,
                context_prefix=context_prefix,
            )
        except Exception as e:
            log.warning(f"Git-based change detection failed: {e}, falling back to file comparison")
            # Fallback to file comparison if git fails
            applied = self._apply_file_changes(
                source,
                target,
                approved_files,
                context_prefix=context_prefix,
            )

        return applied

    def _apply_git_changes(
        self,
        source: Path,
        target: Path,
        approved_files: Optional[List[str]],
        context_prefix: Optional[str] = None,
    ) -> List[str]:
        """Apply changes using git diff detection."""
        from git import InvalidGitRepositoryError, Repo

        applied: List[str] = []

        try:
            repo = Repo(str(source))
        except InvalidGitRepositoryError:
            raise ValueError(f"Source is not a git repository: {source}")

        changed_files = self._collect_git_changed_files(repo)
        normalized_prefix = self._normalize_context_prefix(context_prefix)

        # Apply each change
        for rel_path, change_type in changed_files.items():
            # Skip .git and .massgen_scratch paths (matches _apply_file_changes filter)
            norm_parts = rel_path.replace("\\", "/").split("/")
            if ".git" in norm_parts or ".massgen_scratch" in norm_parts:
                continue

            mapped_path = self._map_context_path(rel_path, normalized_prefix)
            if mapped_path is None:
                log.debug(f"Skipping file outside context prefix '{normalized_prefix}': {rel_path}")
                continue

            # Filter by approved files if specified
            if not self._is_approved_path(
                repo_relative_path=rel_path,
                context_relative_path=mapped_path,
                approved_files=approved_files,
            ):
                log.debug(f"Skipping unapproved file: {rel_path}")
                continue

            src_file = source / rel_path
            dst_file = target / mapped_path if mapped_path else target

            try:
                if change_type in ("M", "A", "R", "C"):  # Modified, Added, Renamed, Copied
                    if src_file.exists():
                        dst_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dst_file)
                        applied_path = mapped_path or str(target.name)
                        applied.append(applied_path)
                        log.info(f"Applied {change_type}: {applied_path}")
                    else:
                        log.warning(f"Source file missing for {change_type}: {rel_path}")

                elif change_type == "D":  # Deleted
                    if dst_file.exists():
                        dst_file.unlink()
                        applied_path = mapped_path or str(target.name)
                        applied.append(applied_path)
                        log.info(f"Applied D: {applied_path}")
                    else:
                        log.debug(f"File already deleted: {mapped_path or str(target.name)}")

            except Exception as e:
                log.error(f"Failed to apply change for {rel_path}: {e}")

        return applied

    def _apply_file_changes(
        self,
        source: Path,
        target: Path,
        approved_files: Optional[List[str]],
        context_prefix: Optional[str] = None,
    ) -> List[str]:
        """Fallback: Apply changes by comparing file contents."""
        applied: List[str] = []
        normalized_prefix = self._normalize_context_prefix(context_prefix)

        # Walk source directory and compare with target
        for src_file in source.rglob("*"):
            if src_file.is_file():
                # Skip .git directory and .massgen_scratch
                if ".git" in src_file.parts:
                    continue
                if ".massgen_scratch" in src_file.parts:
                    continue

                rel_path = str(src_file.relative_to(source))
                mapped_path = self._map_context_path(rel_path, normalized_prefix)
                if mapped_path is None:
                    continue

                # Filter by approved files if specified
                if not self._is_approved_path(
                    repo_relative_path=rel_path,
                    context_relative_path=mapped_path,
                    approved_files=approved_files,
                ):
                    continue

                dst_file = target / mapped_path if mapped_path else target

                try:
                    # Check if file is new or modified
                    should_copy = False
                    if not dst_file.exists():
                        should_copy = True
                    else:
                        # Compare contents
                        src_content = src_file.read_bytes()
                        dst_content = dst_file.read_bytes()
                        if src_content != dst_content:
                            should_copy = True

                    if should_copy:
                        dst_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dst_file)
                        applied_path = mapped_path or str(target.name)
                        applied.append(applied_path)
                        log.info(f"Applied change: {applied_path}")

                except Exception as e:
                    log.error(f"Failed to apply {rel_path}: {e}")

        return applied

    @staticmethod
    def _normalize_context_prefix(context_prefix: Optional[str]) -> Optional[str]:
        """Normalize repo-relative context prefix for path filtering."""
        if context_prefix is None:
            return None
        normalized = context_prefix.replace("\\", "/").strip("/")
        if normalized in ("", "."):
            return None
        return normalized

    @staticmethod
    def _map_context_path(rel_path: str, context_prefix: Optional[str]) -> Optional[str]:
        """Map repo-relative path to context-relative path, or None if out of scope."""
        normalized_rel = rel_path.replace("\\", "/").strip("/")
        if not context_prefix:
            return normalized_rel

        if normalized_rel == context_prefix:
            return ""

        prefix_with_sep = f"{context_prefix}/"
        if not normalized_rel.startswith(prefix_with_sep):
            return None

        return normalized_rel[len(prefix_with_sep) :]

    @staticmethod
    def _is_approved_path(
        repo_relative_path: str,
        context_relative_path: str,
        approved_files: Optional[List[str]],
    ) -> bool:
        """Check whether a changed file is included in the approved set."""
        if approved_files is None:
            return True
        return repo_relative_path in approved_files or context_relative_path in approved_files

    @staticmethod
    def _collect_git_changed_files(repo) -> Dict[str, str]:
        """Collect staged, unstaged, and untracked changes."""
        changed_files: Dict[str, str] = {}  # path -> change_type (M, A, D, R, C)

        def _record_name_status(diff_output: str) -> None:
            for line in diff_output.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) < 2:
                    continue
                status = parts[0][:1].upper()
                rel_path = parts[-1]
                if rel_path:
                    changed_files[rel_path] = status

        try:
            _record_name_status(repo.git.diff("--name-status", "--cached"))
        except Exception:
            pass

        try:
            _record_name_status(repo.git.diff("--name-status"))
        except Exception:
            pass

        for rel_path in repo.untracked_files:
            changed_files[rel_path] = "A"  # Treat untracked as added

        return changed_files

    def get_changes_summary(
        self,
        source_path: str,
    ) -> Dict[str, List[str]]:
        """
        Get a summary of changes in the isolated context.

        Args:
            source_path: Isolated context path

        Returns:
            Dict with keys 'modified', 'added', 'deleted' containing file lists
        """
        source = Path(source_path)
        summary: Dict[str, List[str]] = {
            "modified": [],
            "added": [],
            "deleted": [],
        }

        if not source.exists():
            return summary

        try:
            from git import InvalidGitRepositoryError, Repo

            repo = Repo(str(source))

            # Unstaged changes
            for diff in repo.index.diff(None):
                rel_path = diff.a_path or diff.b_path
                if rel_path:
                    change_type = diff.change_type[0].upper()
                    if change_type == "M":
                        summary["modified"].append(rel_path)
                    elif change_type == "D":
                        summary["deleted"].append(rel_path)
                    elif change_type == "A":
                        summary["added"].append(rel_path)

            # Untracked files
            for rel_path in repo.untracked_files:
                summary["added"].append(rel_path)

        except InvalidGitRepositoryError:
            log.warning(f"Not a git repository: {source_path}")
        except Exception as e:
            log.error(f"Failed to get changes summary: {e}")

        return summary


__all__ = [
    "ChangeApplier",
    "ReviewResult",
]
