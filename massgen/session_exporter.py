# -*- coding: utf-8 -*-
"""Session export functionality for MassGen runs.

Exports MassGen sessions by sharing via GitHub Gist.
"""

import json
from pathlib import Path
from typing import Optional

from rich.console import Console

from .logs_analyzer import get_logs_dir


def find_latest_log() -> Path:
    """Find the most recent log directory with data."""
    logs_dir = get_logs_dir()
    logs = sorted(logs_dir.glob("log_*"), reverse=True)

    if not logs:
        raise FileNotFoundError(f"No logs found in {logs_dir}")

    # Search through logs to find one with metrics
    for log in logs:
        turns = sorted(log.glob("turn_*"), reverse=True)  # Check turns in reverse order
        for turn in turns:
            attempts = sorted(turn.glob("attempt_*"), reverse=True)
            for attempt in attempts:
                if (attempt / "metrics_summary.json").exists() or (attempt / "status.json").exists():
                    return attempt

    # Fallback to latest log even without metrics
    log = logs[0]
    turns = sorted(log.glob("turn_*"))
    if turns:
        attempts = sorted(turns[-1].glob("attempt_*"))
        if attempts:
            return attempts[-1]

    raise FileNotFoundError(f"No valid log attempt found in {logs_dir}")


def resolve_log_dir(log_dir_arg: Optional[str]) -> Path:
    """Resolve log directory from argument or find latest.

    Args:
        log_dir_arg: User-provided log directory path or name

    Returns:
        Path to the log attempt directory
    """
    if not log_dir_arg:
        return find_latest_log()

    path = Path(log_dir_arg)

    # If it's an absolute path, use it directly
    if path.is_absolute():
        if path.exists():
            # Check if this is already an attempt directory
            if (path / "metrics_summary.json").exists() or (path / "status.json").exists():
                return path
            # Check if it's a turn directory
            attempts = sorted(path.glob("attempt_*"))
            if attempts:
                return attempts[-1]
            # Check if it's a log directory
            turns = sorted(path.glob("turn_*"))
            if turns:
                attempts = sorted(turns[-1].glob("attempt_*"))
                if attempts:
                    return attempts[-1]
        raise FileNotFoundError(f"Log directory not found: {path}")

    # Try as a log directory name
    logs_dir = get_logs_dir()

    # Try exact name
    log_path = logs_dir / log_dir_arg
    if log_path.exists():
        turns = sorted(log_path.glob("turn_*"))
        if turns:
            attempts = sorted(turns[-1].glob("attempt_*"))
            if attempts:
                return attempts[-1]

    # Try with log_ prefix
    if not log_dir_arg.startswith("log_"):
        log_path = logs_dir / f"log_{log_dir_arg}"
        if log_path.exists():
            turns = sorted(log_path.glob("turn_*"))
            if turns:
                attempts = sorted(turns[-1].glob("attempt_*"))
                if attempts:
                    return attempts[-1]

    raise FileNotFoundError(f"Log directory not found: {log_dir_arg}")


def export_command(args) -> int:
    """Handle export subcommand - shares session via GitHub Gist.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    from .share import ShareError, share_session

    console = Console()

    try:
        # Resolve log directory
        log_dir_arg = getattr(args, "log_dir", None)
        log_dir = resolve_log_dir(log_dir_arg)

        console.print(f"[blue]Sharing session from: {log_dir}[/blue]")

        try:
            url = share_session(log_dir, console)
            console.print()
            console.print(f"[bold green]Share URL: {url}[/bold green]")
            console.print()
            console.print("[dim]Anyone with this link can view the session (no login required).[/dim]")
            return 0
        except ShareError as e:
            console.print(f"[red]Error:[/red] {e}")
            return 1

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        return 1
    except json.JSONDecodeError as e:
        console.print(f"[red]Error parsing JSON file:[/red] {e}")
        return 1
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        return 1
