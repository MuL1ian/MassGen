# -*- coding: utf-8 -*-
"""Log analysis and display for MassGen runs.

Provides CLI commands to analyze and display metrics from MassGen run logs.
"""

import json
import platform
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def get_logs_dir() -> Path:
    """Get the logs directory, checking both relative and absolute paths."""
    # Try current directory first
    local_logs = Path(".massgen/massgen_logs")
    if local_logs.exists():
        return local_logs

    # Try home directory
    home_logs = Path.home() / ".massgen" / "massgen_logs"
    if home_logs.exists():
        return home_logs

    # Return local path (will fail later with appropriate error)
    return local_logs


class LogAnalyzer:
    """Analyze MassGen log directories."""

    def __init__(self, log_dir: Optional[Path] = None):
        """Initialize analyzer with a specific log directory or find the latest.

        Args:
            log_dir: Path to specific log attempt directory. If None, finds latest.
        """
        self.log_dir = log_dir or self._find_latest_log()
        self.metrics_summary = self._load_metrics_summary()
        self.metrics_events = self._load_metrics_events()

    def _find_latest_log(self) -> Path:
        """Find most recent log directory with metrics."""
        logs_dir = get_logs_dir()
        logs = sorted(logs_dir.glob("log_*"), reverse=True)
        if not logs:
            raise FileNotFoundError(f"No logs found in {logs_dir}")

        # Search through logs to find one with metrics
        for log in logs:
            turns = sorted(log.glob("turn_*"))
            if turns:
                attempts = sorted(turns[-1].glob("attempt_*"), reverse=True)
                for attempt in attempts:
                    if (attempt / "metrics_summary.json").exists():
                        return attempt

        # Fallback to latest log even without metrics
        log = logs[0]
        turns = sorted(log.glob("turn_*"))
        if turns:
            attempts = sorted(turns[-1].glob("attempt_*"))
            if attempts:
                return attempts[-1]
        return log

    def _load_metrics_summary(self) -> Dict[str, Any]:
        """Load metrics summary JSON."""
        path = self.log_dir / "metrics_summary.json"
        if path.exists():
            return json.loads(path.read_text())
        return {}

    def _load_metrics_events(self) -> Dict[str, Any]:
        """Load metrics events JSON."""
        path = self.log_dir / "metrics_events.json"
        if path.exists():
            return json.loads(path.read_text())
        return {}

    def get_summary(self) -> Dict[str, Any]:
        """Get summary data for display."""
        return self.metrics_summary

    def get_tools_breakdown(self, sort_by: str = "time") -> List[Dict[str, Any]]:
        """Get tool breakdown sorted by time or calls.

        Args:
            sort_by: Either "time" or "calls"

        Returns:
            List of tool metrics dicts sorted by specified key
        """
        tools = self.metrics_summary.get("tools", {}).get("by_tool", {})
        result = []
        for name, data in tools.items():
            result.append(
                {
                    "name": name,
                    "calls": data.get("call_count", 0),
                    "time_ms": data.get("total_execution_time_ms", 0),
                    "avg_ms": data.get("avg_execution_time_ms", 0),
                    "failures": data.get("failure_count", 0),
                },
            )

        key = "time_ms" if sort_by == "time" else "calls"
        return sorted(result, key=lambda x: x[key], reverse=True)

    def get_round_history(self) -> List[Dict[str, Any]]:
        """Get round history for all agents."""
        agents = self.metrics_summary.get("agents", {})
        all_rounds = []
        for agent_id, agent_data in agents.items():
            for round_data in agent_data.get("round_history", []):
                round_copy = dict(round_data)
                round_copy["agent_id"] = agent_id
                all_rounds.append(round_copy)
        return sorted(all_rounds, key=lambda x: (x.get("round_number", 0), x.get("start_time", 0)))


def format_duration(ms: float) -> str:
    """Format milliseconds as human-readable duration."""
    if ms < 1000:
        return f"{ms:.0f}ms"
    elif ms < 60000:
        return f"{ms/1000:.1f}s"
    else:
        minutes = ms / 60000
        return f"{minutes:.1f}m"


def display_summary(analyzer: LogAnalyzer, console: Console) -> None:
    """Display run summary using Rich."""
    data = analyzer.get_summary()

    if not data:
        console.print("[yellow]No metrics data found in this log directory.[/yellow]")
        console.print(f"Log directory: {analyzer.log_dir}")
        return

    meta = data.get("meta", {})
    totals = data.get("totals", {})
    data.get("tools", {})
    rounds = data.get("rounds", {})

    # Header panel
    question = meta.get("question", "Unknown")
    if len(question) > 70:
        question = question[:67] + "..."
    winner = meta.get("winner", "N/A")
    cost = totals.get("estimated_cost", 0)
    num_agents = meta.get("num_agents", 1)

    # Calculate duration from round history
    round_history = analyzer.get_round_history()
    if round_history:
        total_duration_ms = sum(r.get("duration_ms", 0) for r in round_history)
        duration_str = format_duration(total_duration_ms)
    else:
        duration_str = "N/A"

    console.print(
        Panel(
            f"[bold]{question}[/bold]\n\n"
            f"Winner: [cyan]{winner}[/cyan] | "
            f"Agents: [yellow]{num_agents}[/yellow] | "
            f"Duration: [magenta]{duration_str}[/magenta] | "
            f"Cost: [green]${cost:.2f}[/green]",
            title="MassGen Run Summary",
            border_style="blue",
        ),
    )

    # Tokens section
    console.print(
        f"\n[bold]Tokens:[/bold] "
        f"Input: [cyan]{totals.get('input_tokens', 0):,}[/cyan] | "
        f"Output: [cyan]{totals.get('output_tokens', 0):,}[/cyan] | "
        f"Reasoning: [cyan]{totals.get('reasoning_tokens', 0):,}[/cyan]",
    )

    # Rounds section
    by_outcome = rounds.get("by_outcome", {})
    total_rounds = rounds.get("total_rounds", 0)
    errors = by_outcome.get("error", 0)
    timeouts = by_outcome.get("timeout", 0)

    outcome_parts = []
    for outcome, count in by_outcome.items():
        if count > 0 and outcome not in ("error", "timeout"):
            outcome_parts.append(f"{outcome}: {count}")

    console.print(
        f"\n[bold]Rounds ({total_rounds}):[/bold] " + " | ".join(outcome_parts) + f"\n  Errors: [{'red' if errors else 'green'}]{errors}[/] | "
        f"Timeouts: [{'red' if timeouts else 'green'}]{timeouts}[/]",
    )

    # Tools table (top 5)
    tool_data = analyzer.get_tools_breakdown()[:5]
    if tool_data:
        console.print()
        table = Table(title="Top Tools by Time", border_style="dim")
        table.add_column("Tool", style="cyan", max_width=45)
        table.add_column("Calls", justify="right")
        table.add_column("Time", justify="right")
        table.add_column("Avg", justify="right")
        table.add_column("Fail", justify="right", style="red")

        for t in tool_data:
            name = t["name"]
            if len(name) > 45:
                name = "..." + name[-42:]
            fail_str = str(t["failures"]) if t["failures"] else ""
            table.add_row(
                name,
                str(t["calls"]),
                format_duration(t["time_ms"]),
                f"{t['avg_ms']:.0f}ms",
                fail_str,
            )
        console.print(table)

    # Subagents section
    subagents_data = data.get("subagents", {})
    if subagents_data and subagents_data.get("total_subagents", 0) > 0:
        total_subagents = subagents_data.get("total_subagents", 0)
        subagent_cost = subagents_data.get("total_estimated_cost", 0)
        agent_cost = totals.get("agent_cost", 0)

        console.print(
            f"\n[bold]Subagents ({total_subagents}):[/bold] " f"Cost: [green]${subagent_cost:.3f}[/green] " f"[dim](parent: ${agent_cost:.2f})[/dim]",
        )

        # Show subagent table
        subagent_list = subagents_data.get("subagents", [])
        if subagent_list:
            sub_table = Table(border_style="dim", show_header=True, header_style="bold")
            sub_table.add_column("Subagent", style="cyan", max_width=20)
            sub_table.add_column("Status", justify="center", max_width=10)
            sub_table.add_column("Time", justify="right")
            sub_table.add_column("Tokens", justify="right")
            sub_table.add_column("Cost", justify="right", style="green")
            sub_table.add_column("Task", max_width=50)

            for sub in subagent_list:
                status = sub.get("status", "unknown")
                status_style = "green" if status == "completed" else "yellow" if status == "running" else "red"
                elapsed = sub.get("elapsed_seconds", 0)
                time_str = f"{elapsed:.1f}s" if elapsed < 60 else f"{elapsed/60:.1f}m"
                input_tok = sub.get("input_tokens", 0)
                output_tok = sub.get("output_tokens", 0)
                tokens_str = f"{input_tok:,}→{output_tok:,}"
                cost_val = sub.get("estimated_cost", 0)
                task = sub.get("task", "")
                if len(task) > 50:
                    task = task[:47] + "..."

                sub_table.add_row(
                    sub.get("subagent_id", "?"),
                    f"[{status_style}]{status}[/{status_style}]",
                    time_str,
                    tokens_str,
                    f"${cost_val:.4f}",
                    task,
                )

            console.print(sub_table)

    # API Timing section
    api_timing = data.get("api_timing", {})
    if api_timing and api_timing.get("total_calls", 0) > 0:
        total_api_time = api_timing.get("total_time_ms", 0)
        total_api_calls = api_timing.get("total_calls", 0)
        avg_api_time = api_timing.get("avg_time_ms", 0)
        avg_ttft = api_timing.get("avg_ttft_ms", 0)

        console.print(
            f"\n[bold]API Calls:[/bold] "
            f"Count: [cyan]{total_api_calls}[/cyan] | "
            f"Total Time: [cyan]{format_duration(total_api_time)}[/cyan] | "
            f"Avg: [cyan]{format_duration(avg_api_time)}[/cyan] | "
            f"Avg TTFT: [cyan]{avg_ttft:.0f}ms[/cyan]",
        )

        # Show breakdown by backend if available
        by_backend = api_timing.get("by_backend", {})
        if by_backend and len(by_backend) > 1:
            backend_parts = []
            for backend, stats in by_backend.items():
                calls = stats.get("calls", 0)
                avg_ms = stats.get("avg_time_ms", 0)
                backend_parts.append(f"{backend}: {calls} calls, avg {format_duration(avg_ms)}")
            console.print(f"  [dim]{' | '.join(backend_parts)}[/dim]")

    # Show log directory
    console.print(f"\n[dim]Log: {analyzer.log_dir}[/dim]")


def display_tools(analyzer: LogAnalyzer, console: Console, sort_by: str) -> None:
    """Display full tool breakdown."""
    tool_data = analyzer.get_tools_breakdown(sort_by)

    if not tool_data:
        console.print("[yellow]No tool data found.[/yellow]")
        return

    table = Table(title=f"Tool Breakdown (sorted by {sort_by})", border_style="dim")
    table.add_column("Tool", style="cyan")
    table.add_column("Calls", justify="right")
    table.add_column("Time", justify="right")
    table.add_column("Avg", justify="right")
    table.add_column("Fail", justify="right", style="red")

    total_calls = 0
    total_time = 0.0
    total_fail = 0

    for t in tool_data:
        fail_str = str(t["failures"]) if t["failures"] else ""
        table.add_row(
            t["name"],
            str(t["calls"]),
            format_duration(t["time_ms"]),
            f"{t['avg_ms']:.0f}ms",
            fail_str,
        )
        total_calls += t["calls"]
        total_time += t["time_ms"]
        total_fail += t["failures"]

    table.add_section()
    fail_total = f"[bold red]{total_fail}[/bold red]" if total_fail else ""
    table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{total_calls}[/bold]",
        f"[bold]{format_duration(total_time)}[/bold]",
        "",
        fail_total,
    )

    console.print(table)
    console.print(f"\n[dim]Log: {analyzer.log_dir}[/dim]")


def display_list(console: Console, limit: int) -> None:
    """Display list of recent runs."""
    logs_dir = get_logs_dir()

    if not logs_dir.exists():
        console.print(f"[red]Logs directory not found:[/red] {logs_dir}")
        return

    logs = sorted(logs_dir.glob("log_*"), reverse=True)[:limit]

    if not logs:
        console.print("[yellow]No logs found.[/yellow]")
        return

    table = Table(title="Recent Runs", border_style="dim")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Timestamp", style="cyan")
    table.add_column("Duration", justify="right")
    table.add_column("Cost", justify="right", style="green")
    table.add_column("Question", max_width=40)

    for i, log_dir in enumerate(logs, 1):
        # Find metrics in this log
        metrics_path = None
        for turn in sorted(log_dir.glob("turn_*")):
            for attempt in sorted(turn.glob("attempt_*"), reverse=True):
                p = attempt / "metrics_summary.json"
                if p.exists():
                    metrics_path = p
                    break
            if metrics_path:
                break

        # Parse timestamp from directory name: log_YYYYMMDD_HHMMSS_microseconds
        dir_name = log_dir.name
        try:
            parts = dir_name.replace("log_", "").split("_")
            date_part = parts[0]  # YYYYMMDD
            time_part = parts[1] if len(parts) > 1 else "000000"  # HHMMSS
            timestamp = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:]} {time_part[:2]}:{time_part[2:4]}"
        except (IndexError, ValueError):
            timestamp = dir_name

        if metrics_path:
            try:
                data = json.loads(metrics_path.read_text())
                meta = data.get("meta", {})
                totals = data.get("totals", {})

                question = meta.get("question", "")
                if len(question) > 40:
                    question = question[:37] + "..."

                cost = totals.get("estimated_cost", 0)

                # Calculate duration
                agents = data.get("agents", {})
                total_duration_ms = 0.0
                for agent_data in agents.values():
                    for round_data in agent_data.get("round_history", []):
                        total_duration_ms += round_data.get("duration_ms", 0)

                duration_str = format_duration(total_duration_ms) if total_duration_ms > 0 else "-"

                table.add_row(str(i), timestamp, duration_str, f"${cost:.2f}", question)
            except Exception:
                table.add_row(str(i), timestamp, "?", "?", "[red]Error reading metrics[/red]")
        else:
            table.add_row(str(i), timestamp, "-", "-", "[dim]No metrics[/dim]")

    console.print(table)


def open_log_directory(log_dir: Path, console: Console) -> int:
    """Open log directory in system file manager.

    Args:
        log_dir: Path to the log directory to open
        console: Rich console for output

    Returns:
        Exit code (0 for success, 1 for error)
    """
    if not log_dir.exists():
        console.print(f"[red]Error:[/red] Log directory not found: {log_dir}")
        return 1

    system = platform.system()
    try:
        if system == "Darwin":  # macOS
            subprocess.run(["open", str(log_dir)], check=True)
        elif system == "Windows":
            subprocess.run(["explorer", str(log_dir)], check=True)
        else:  # Linux and others
            subprocess.run(["xdg-open", str(log_dir)], check=True)

        console.print(f"[green]Opened:[/green] {log_dir}")
        return 0
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error opening directory:[/red] {e}")
        return 1
    except FileNotFoundError:
        console.print("[red]Error:[/red] Could not find file manager command")
        console.print(f"Log directory: {log_dir}")
        return 1


def logs_command(args) -> int:
    """Handle logs subcommand.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    console = Console()

    try:
        logs_cmd = getattr(args, "logs_command", None)

        if logs_cmd == "list":
            limit = getattr(args, "limit", 10)
            display_list(console, limit)
        elif logs_cmd == "open":
            log_dir = None
            if hasattr(args, "log_dir") and args.log_dir:
                log_dir = Path(args.log_dir)
            else:
                # Find the latest log directory
                analyzer = LogAnalyzer(None)
                log_dir = analyzer.log_dir
            return open_log_directory(log_dir, console)
        else:
            log_dir = None
            if hasattr(args, "log_dir") and args.log_dir:
                log_dir = Path(args.log_dir)

            analyzer = LogAnalyzer(log_dir)

            if hasattr(args, "json") and args.json:
                console.print_json(data=analyzer.get_summary())
            elif logs_cmd == "tools":
                sort_by = getattr(args, "sort", "time")
                display_tools(analyzer, console, sort_by)
            else:  # summary (default)
                display_summary(analyzer, console)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        return 1
    except json.JSONDecodeError as e:
        console.print(f"[red]Error parsing metrics file:[/red] {e}")
        return 1

    return 0
