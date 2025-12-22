# -*- coding: utf-8 -*-
"""Share MassGen sessions via GitHub Gist.

This module provides functionality to upload MassGen session logs to GitHub Gist
for easy sharing. Viewers can access shared sessions without authentication.
"""

import fnmatch
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console

from .filesystem_manager._constants import MAX_FILE_SIZE_FOR_SHARING as MAX_FILE_SIZE
from .filesystem_manager._constants import MAX_FILES_FOR_SHARING as MAX_FILES
from .filesystem_manager._constants import MAX_TOTAL_SIZE_FOR_SHARING as MAX_TOTAL_SIZE
from .filesystem_manager._constants import SHARE_EXCLUDE_DIRS as EXCLUDE_PATTERNS
from .filesystem_manager._constants import (
    SHARE_EXCLUDE_EXTENSIONS as EXCLUDE_EXTENSIONS,
)
from .filesystem_manager._constants import WORKSPACE_INCLUDE_EXTENSIONS

# Priority files to always include (most important first)
PRIORITY_FILES = [
    "metrics_summary.json",
    "status.json",
    "coordination_events.json",
    "snapshot_mappings.json",
    "coordination_table.txt",
    "execution_metadata.yaml",
]

# Pattern to match redundant final presentation files in agent_outputs
EXCLUDE_FILE_PATTERN = "final_presentation_*_latest.txt"

# Viewer URL base (hosted on MassGen org GitHub Pages)
VIEWER_URL_BASE = "https://massgen.github.io/MassGen-Viewer/"


class ShareError(Exception):
    """Error during share operation."""


def should_exclude(path: Path, rel_path: str) -> bool:
    """Check if file should be excluded from upload.

    Args:
        path: Absolute path to the file
        rel_path: Relative path from log directory

    Returns:
        True if file should be excluded
    """
    # Check excluded files by pattern
    if fnmatch.fnmatch(path.name, EXCLUDE_FILE_PATTERN):
        return True

    # Check directory patterns (but allow workspace files with allowed extensions)
    for pattern in EXCLUDE_PATTERNS:
        if pattern in rel_path:
            # Allow workspace files with allowed extensions
            # Paths like: agent_a/20251218_170133/workspace/file.txt
            #         or: final/agent_a/workspace/file.txt
            if pattern == "workspace":
                suffix = path.suffix.lower()
                if suffix in WORKSPACE_INCLUDE_EXTENSIONS:
                    return False  # Include this workspace file
            return True

    # Check extensions
    for ext in EXCLUDE_EXTENSIONS:
        if path.name.endswith(ext):
            return True

    # Exclude massgen.log (usually large)
    if path.name == "massgen.log":
        return True

    # Exclude MCP stderr logs (debug noise)
    if path.name.startswith("mcp_") and path.name.endswith("_stderr.log"):
        return True

    return False


def collect_files(log_dir: Path) -> Tuple[Dict[str, str], List[Tuple[str, int]]]:
    """Collect and flatten files for gist upload.

    Args:
        log_dir: Path to the log attempt directory

    Returns:
        Tuple of (files dict, skipped list)
        - files: Dict mapping flattened filenames to content
        - skipped: List of (rel_path, size) tuples for skipped files
    """
    files: Dict[str, str] = {}
    skipped: List[Tuple[str, int]] = []
    total_size = 0

    # First pass: collect all eligible files with sizes
    candidates = []
    for file_path in log_dir.rglob("*"):
        if not file_path.is_file():
            continue

        rel_path = str(file_path.relative_to(log_dir))

        # Check exclusion patterns
        if should_exclude(file_path, rel_path):
            continue

        try:
            size = file_path.stat().st_size
            # Skip empty files (gist doesn't allow blank files)
            if size == 0:
                continue
            # Skip files over size limit
            if size > MAX_FILE_SIZE:
                skipped.append((rel_path, size))
                continue
            candidates.append((rel_path, file_path, size))
        except OSError:
            continue

    # Sort: priority files first, then by size (smaller first)
    def sort_key(item: Tuple[str, Path, int]) -> Tuple[int, int, int]:
        rel_path, _, size = item
        filename = Path(rel_path).name
        if filename in PRIORITY_FILES:
            return (0, PRIORITY_FILES.index(filename), size)
        return (1, 0, size)

    candidates.sort(key=sort_key)

    # Second pass: add files within limits
    for rel_path, file_path, size in candidates:
        if len(files) >= MAX_FILES:
            skipped.append((rel_path, size))
            continue
        if total_size + size > MAX_TOTAL_SIZE:
            skipped.append((rel_path, size))
            continue

        try:
            content = file_path.read_text(errors="replace")
            # Skip files that are effectively empty (only whitespace)
            if not content.strip():
                continue
            # Flatten path: agent_a/timestamp/answer.txt → agent_a__timestamp__answer.txt
            flat_name = rel_path.replace("/", "__").replace("\\", "__")
            files[flat_name] = content
            total_size += size
        except (OSError, UnicodeDecodeError):
            skipped.append((rel_path, size))
            continue

    return files, skipped


def create_gist(files: Dict[str, str], description: str) -> str:
    """Create a secret gist and return the gist ID.

    Args:
        files: Dict mapping filenames to content
        description: Gist description

    Returns:
        Gist ID

    Raises:
        ShareError: If gist creation fails
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Write files to temp directory
        for name, content in files.items():
            (tmpdir_path / name).write_text(content, encoding="utf-8")

        file_args = [str(tmpdir_path / name) for name in files.keys()]

        try:
            # Note: gh gist create defaults to secret, no flag needed
            result = subprocess.run(
                ["gh", "gist", "create", "-d", description] + file_args,
                capture_output=True,
                text=True,
                check=True,
            )

            # Output is the gist URL: https://gist.github.com/username/abc123
            gist_url = result.stdout.strip()
            gist_id = gist_url.split("/")[-1]
            return gist_id

        except subprocess.CalledProcessError as e:
            stderr = e.stderr or ""
            if "gh auth login" in stderr or "not logged in" in stderr.lower():
                raise ShareError(
                    "Not authenticated with GitHub.\n" "Run 'gh auth login' to enable sharing.",
                )
            raise ShareError(f"Failed to create gist: {stderr}")
        except FileNotFoundError:
            raise ShareError(
                "GitHub CLI (gh) not found.\n" "Install it from https://cli.github.com/",
            )


def share_session(log_dir: Path | str, console: Optional[Console] = None) -> str:
    """Upload session to GitHub Gist and return viewer URL.

    Args:
        log_dir: Path to log attempt directory
        console: Optional console for status messages

    Returns:
        Viewer URL

    Raises:
        ShareError: If sharing fails
    """
    # Ensure log_dir is a Path object
    if isinstance(log_dir, str):
        log_dir = Path(log_dir)

    if console:
        console.print("[dim]Collecting files...[/dim]")

    files, skipped = collect_files(log_dir)

    if not files:
        raise ShareError("No files to upload")

    total_size = sum(len(c) for c in files.values())

    # Warn if files were skipped
    if skipped and console:
        console.print(f"[yellow]Skipped {len(skipped)} files (too large or over limit):[/yellow]")
        # Sort by size descending to show biggest first
        skipped_sorted = sorted(skipped, key=lambda x: x[1], reverse=True)
        for path, size in skipped_sorted[:5]:
            console.print(f"  [dim]- {path} ({size:,} bytes)[/dim]")
        if len(skipped_sorted) > 5:
            console.print(f"  [dim]... and {len(skipped_sorted) - 5} more[/dim]")
        console.print()

    if console:
        console.print(f"[dim]Uploading {len(files)} files ({total_size:,} bytes)...[/dim]")

    # Get session info for description
    description = "MassGen Session"
    if "metrics_summary.json" in files:
        try:
            metrics = json.loads(files["metrics_summary.json"])
            question = metrics.get("meta", {}).get("question", "")
            if question:
                # Truncate and clean up question for description
                question_clean = question.replace("\n", " ").strip()
                if len(question_clean) > 50:
                    question_clean = question_clean[:47] + "..."
                description = f"MassGen: {question_clean}"
        except (json.JSONDecodeError, KeyError):
            pass

    gist_id = create_gist(files, description)

    return f"{VIEWER_URL_BASE}?gist={gist_id}"


def list_shares(console: Console) -> int:
    """List all MassGen gists for current user.

    Args:
        console: Rich console for output

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        result = subprocess.run(
            ["gh", "gist", "list", "--limit", "50"],
            capture_output=True,
            text=True,
            check=True,
        )

        if not result.stdout.strip():
            console.print("[dim]No gists found.[/dim]")
            return 0

        # Filter for MassGen gists
        lines = result.stdout.strip().split("\n")
        massgen_gists = [line for line in lines if "MassGen" in line]

        if not massgen_gists:
            console.print("[dim]No shared MassGen sessions found.[/dim]")
            console.print("[dim]Share a session with: massgen export --share[/dim]")
            return 0

        console.print("[bold]Shared Sessions:[/bold]\n")
        for line in massgen_gists:
            parts = line.split("\t")
            gist_id = parts[0] if parts else ""
            desc = parts[1] if len(parts) > 1 else ""
            files_info = parts[2] if len(parts) > 2 else ""
            visibility = parts[3] if len(parts) > 3 else ""
            updated = parts[4] if len(parts) > 4 else ""

            console.print(f"  [cyan]{gist_id}[/cyan]")
            console.print(f"    {desc}")
            console.print(f"    [dim]{files_info} files • {visibility} • {updated}[/dim]")
            console.print(f"    [dim]View: {VIEWER_URL_BASE}?gist={gist_id}[/dim]")
            console.print()

        return 0

    except subprocess.CalledProcessError as e:
        stderr = e.stderr or ""
        if "gh auth login" in stderr or "not logged in" in stderr.lower():
            console.print("[red]Not authenticated with GitHub.[/red]")
            console.print("Run 'gh auth login' to enable sharing.")
            return 1
        console.print(f"[red]Error listing gists:[/red] {stderr}")
        return 1
    except FileNotFoundError:
        console.print("[red]GitHub CLI (gh) not found.[/red]")
        console.print("Install it from https://cli.github.com/")
        return 1


def delete_share(gist_id: str, console: Console) -> int:
    """Delete a shared session gist.

    Args:
        gist_id: Gist ID to delete
        console: Rich console for output

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        subprocess.run(
            ["gh", "gist", "delete", gist_id, "--yes"],
            capture_output=True,
            text=True,
            check=True,
        )
        console.print(f"[green]Deleted gist {gist_id}[/green]")
        return 0

    except subprocess.CalledProcessError as e:
        stderr = e.stderr or ""
        if "gh auth login" in stderr or "not logged in" in stderr.lower():
            console.print("[red]Not authenticated with GitHub.[/red]")
            console.print("Run 'gh auth login' to enable sharing.")
            return 1
        if "not found" in stderr.lower() or "404" in stderr:
            console.print(f"[red]Gist not found:[/red] {gist_id}")
            return 1
        console.print(f"[red]Error deleting gist:[/red] {stderr}")
        return 1
    except FileNotFoundError:
        console.print("[red]GitHub CLI (gh) not found.[/red]")
        console.print("Install it from https://cli.github.com/")
        return 1
