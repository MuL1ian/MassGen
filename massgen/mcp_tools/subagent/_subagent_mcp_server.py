#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Subagent MCP Server for MassGen

This MCP server provides tools for spawning and managing subagents,
enabling agents to delegate tasks to independent agent instances
with fresh context and isolated workspaces.

Tools provided:
- spawn_subagents: Spawn one or more subagents (runs in parallel if multiple)
- list_subagents: List all spawned subagents with their status
- get_subagent_result: Get the result from a completed subagent
- check_subagent_status: Check status of a running subagent
"""

import argparse
import asyncio
import atexit
import json
import logging
import os
import signal
from pathlib import Path
from typing import Any, Dict, List, Optional

import fastmcp

from massgen.subagent.manager import SubagentManager
from massgen.subagent.models import SubagentOrchestratorConfig

logger = logging.getLogger(__name__)

# Global storage for subagent manager (initialized per server instance)
_manager: Optional[SubagentManager] = None

# Server configuration
_workspace_path: Optional[Path] = None
_parent_agent_id: Optional[str] = None
_orchestrator_id: Optional[str] = None
_parent_agent_configs: List[Dict[str, Any]] = []
_subagent_orchestrator_config: Optional[SubagentOrchestratorConfig] = None
_log_directory: Optional[str] = None
_max_concurrent: int = 3
_default_timeout: int = 300


def _get_manager() -> SubagentManager:
    """Get or create the SubagentManager instance."""
    global _manager
    if _manager is None:
        if _workspace_path is None:
            raise RuntimeError("Subagent server not properly configured: workspace_path is None")
        _manager = SubagentManager(
            parent_workspace=str(_workspace_path),
            parent_agent_id=_parent_agent_id or "unknown",
            orchestrator_id=_orchestrator_id or "unknown",
            parent_agent_configs=_parent_agent_configs,
            subagent_orchestrator_config=_subagent_orchestrator_config,
            log_directory=_log_directory,
            max_concurrent=_max_concurrent,
            default_timeout=_default_timeout,
        )
    return _manager


def _save_subagents_to_filesystem() -> None:
    """
    Save subagent registry to filesystem for visibility.

    Writes to subagents/_registry.json in the workspace directory.
    """
    if _workspace_path is None:
        return

    manager = _get_manager()
    subagents_dir = _workspace_path / "subagents"
    subagents_dir.mkdir(exist_ok=True)

    registry = {
        "parent_agent_id": _parent_agent_id,
        "orchestrator_id": _orchestrator_id,
        "subagents": manager.list_subagents(),
    }

    registry_file = subagents_dir / "_registry.json"
    registry_file.write_text(json.dumps(registry, indent=2))


async def create_server() -> fastmcp.FastMCP:
    """Factory function to create and configure the subagent MCP server."""
    global _workspace_path, _parent_agent_id, _orchestrator_id, _parent_agent_configs, _parent_backend_config, _subagent_orchestrator_config, _log_directory, _max_concurrent, _default_timeout

    parser = argparse.ArgumentParser(description="Subagent MCP Server")
    parser.add_argument(
        "--agent-id",
        type=str,
        required=True,
        help="ID of the parent agent using this subagent server",
    )
    parser.add_argument(
        "--orchestrator-id",
        type=str,
        required=True,
        help="ID of the orchestrator managing this agent",
    )
    parser.add_argument(
        "--workspace-path",
        type=str,
        required=True,
        help="Path to parent agent workspace for subagent workspaces",
    )
    parser.add_argument(
        "--agent-configs-file",
        type=str,
        required=False,
        default="",
        help="Path to JSON file containing list of parent agent configurations",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=3,
        help="Maximum concurrent subagents (default: 3)",
    )
    parser.add_argument(
        "--default-timeout",
        type=int,
        default=300,
        help="Default timeout in seconds (default: 300)",
    )
    parser.add_argument(
        "--orchestrator-config",
        type=str,
        required=False,
        default="{}",
        help="JSON-encoded subagent orchestrator configuration",
    )
    parser.add_argument(
        "--log-directory",
        type=str,
        required=False,
        default="",
        help="Path to log directory for subagent logs",
    )
    args = parser.parse_args()

    # Set global configuration
    _workspace_path = Path(args.workspace_path)
    _parent_agent_id = args.agent_id
    _orchestrator_id = args.orchestrator_id

    # Parse agent configs from file (avoids command line / env var length limits)
    _parent_agent_configs = []
    if args.agent_configs_file:
        try:
            with open(args.agent_configs_file) as f:
                _parent_agent_configs = json.load(f)
            if not isinstance(_parent_agent_configs, list):
                _parent_agent_configs = [_parent_agent_configs]
            # Clean up the temp file after reading
            try:
                os.unlink(args.agent_configs_file)
            except OSError:
                pass  # Ignore if file already deleted
        except (json.JSONDecodeError, FileNotFoundError, OSError) as e:
            logger.warning(f"Failed to load agent configs from {args.agent_configs_file}: {e}")
            _parent_agent_configs = []

    # Parse subagent orchestrator config
    try:
        orch_cfg_data = json.loads(args.orchestrator_config)
        if orch_cfg_data:
            _subagent_orchestrator_config = SubagentOrchestratorConfig.from_dict(orch_cfg_data)
    except json.JSONDecodeError:
        pass  # Keep default None

    # Set log directory
    _log_directory = args.log_directory if args.log_directory else None

    # Set concurrency and timeout limits
    _max_concurrent = args.max_concurrent
    _default_timeout = args.default_timeout

    # Set up signal handlers for graceful shutdown
    try:
        loop = asyncio.get_running_loop()
        _setup_signal_handlers(loop)
    except RuntimeError:
        pass  # No running loop yet, handlers will be set up later if needed

    # Register atexit handler as a fallback for cleanup
    atexit.register(_sync_cleanup)

    # Create the FastMCP server
    mcp = fastmcp.FastMCP("Subagent Spawning")

    @mcp.tool()
    def spawn_subagents(
        tasks: List[Dict[str, Any]],
        context: str,
        timeout_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        f"""
        Spawn subagents to work on INDEPENDENT tasks in PARALLEL.

        CRITICAL RULES:
        1. Maximum {_max_concurrent} tasks per call (will error if exceeded)
        2. `context` is REQUIRED - subagents need to know the project/goal
        3. Tasks run SIMULTANEOUSLY - do NOT design tasks that depend on each other
        4. Each task dict MUST have a "task" field (not "description" or "id")

        PARALLEL EXECUTION WARNING:
        All tasks start at the same time! Do NOT create tasks like:
        - BAD: "Research content" then "Build website using researched content" (sequential dependency)
        - GOOD: "Research biography" and "Research discography" (independent, can run together)

        Args:
            tasks: List of task dicts (max {_max_concurrent}). Each MUST have:
                   - "task": (REQUIRED) string describing what to do
                   - "subagent_id": (optional) custom identifier
                   - "context_files": (optional) files to share
            context: (REQUIRED) Project/goal description so subagents understand the work.
                     Example: "Building a Bob Dylan tribute website with bio, discography, timeline"
            timeout_seconds: (optional) Max time per subagent, default 300s

        TIMEOUT HANDLING:
        If subagents timeout, check their workspaces anyway - they may have partial work:
        - Result includes "workspace" path for each subagent
        - Read files from that path to salvage any completed work
        - Complete remaining work yourself

        Returns:
            {{
                "success": bool,
                "results": [
                    {{
                        "subagent_id": "...",
                        "status": "completed" | "timeout" | "error",
                        "workspace": "/path/to/subagent/workspace",  # CHECK THIS ON TIMEOUT!
                        "answer": "...",
                        "execution_time_seconds": float
                    }}
                ],
                "summary": {{"total": N, "completed": N, "timeout": N}}
            }}

        Examples:
            # CORRECT: Independent parallel tasks with context
            spawn_subagents(
                tasks=[
                    {{"task": "Research and write Bob Dylan biography to bio.md", "subagent_id": "bio"}},
                    {{"task": "Create discography table in discography.md", "subagent_id": "discog"}},
                    {{"task": "List 20 famous songs with years in songs.md", "subagent_id": "songs"}}
                ],
                context="Building a Bob Dylan tribute website with biography, discography, songs, and quotes pages"
            )

            # WRONG: Sequential dependency (task 2 needs task 1's output)
            # spawn_subagents(tasks=[
            #     {{"task": "Research content"}},
            #     {{"task": "Build website using the researched content"}}  # CAN'T USE TASK 1's OUTPUT!
            # ])
        """
        try:
            manager = _get_manager()

            # Validate context is provided
            if not context or not context.strip():
                return {
                    "success": False,
                    "operation": "spawn_subagents",
                    "error": "Missing required 'context' parameter. Subagents need project context to understand " "what they're working on. Example: context='Building a Bob Dylan tribute website'",
                }

            # Validate tasks
            if not tasks:
                return {
                    "success": False,
                    "operation": "spawn_subagents",
                    "error": "No tasks provided. Must provide at least one task.",
                }

            # Enforce hard limit on number of subagents
            if len(tasks) > _max_concurrent:
                return {
                    "success": False,
                    "operation": "spawn_subagents",
                    "error": f"Too many tasks: {len(tasks)} requested but maximum is {_max_concurrent}. " f"Please reduce to {_max_concurrent} or fewer tasks per spawn_subagents call.",
                }

            for i, task_config in enumerate(tasks):
                if "task" not in task_config:
                    return {
                        "success": False,
                        "operation": "spawn_subagents",
                        "error": f"Task at index {i} missing required 'task' field",
                    }

            # Run the async spawn safely (handles both sync and nested async contexts)
            from massgen.utils import run_async_safely

            results = run_async_safely(
                manager.spawn_parallel(
                    tasks=tasks,
                    context=context,
                    timeout_seconds=timeout_seconds or _default_timeout,
                ),
            )

            # Save registry to filesystem
            _save_subagents_to_filesystem()

            # Compute summary
            completed = sum(1 for r in results if r.status == "completed")
            failed = sum(1 for r in results if r.status == "error")
            timeout = sum(1 for r in results if r.status == "timeout")
            all_success = all(r.success for r in results)

            return {
                "success": all_success,
                "operation": "spawn_subagents",
                "results": [r.to_dict() for r in results],
                "summary": {
                    "total": len(results),
                    "completed": completed,
                    "failed": failed,
                    "timeout": timeout,
                },
            }

        except Exception as e:
            logger.error(f"[SubagentMCP] Error spawning subagents: {e}")
            return {
                "success": False,
                "operation": "spawn_subagents",
                "error": str(e),
            }

    @mcp.tool()
    def list_subagents() -> Dict[str, Any]:
        """
        List all subagents spawned by this agent with their current status.

        Returns:
            Dictionary with:
            - success: bool
            - operation: str - "list_subagents"
            - subagents: list - List of subagent info with id, status, workspace, task
            - count: int - Total number of subagents

        Example:
            result = list_subagents()
            for sub in result['subagents']:
                print(f"{sub['subagent_id']}: {sub['status']}")
        """
        try:
            manager = _get_manager()
            subagents = manager.list_subagents()

            return {
                "success": True,
                "operation": "list_subagents",
                "subagents": subagents,
                "count": len(subagents),
            }

        except Exception as e:
            logger.error(f"[SubagentMCP] Error listing subagents: {e}")
            return {
                "success": False,
                "operation": "list_subagents",
                "error": str(e),
            }

    @mcp.tool()
    def get_subagent_costs() -> Dict[str, Any]:
        """
        Get aggregated cost summary for all subagents spawned by this agent.

        Returns:
            Dictionary with:
            - success: bool
            - operation: str - "get_subagent_costs"
            - total_subagents: int - Number of subagents spawned
            - total_input_tokens: int - Sum of input tokens across all subagents
            - total_output_tokens: int - Sum of output tokens across all subagents
            - total_estimated_cost: float - Sum of estimated costs
            - subagents: list - Per-subagent cost breakdown

        Example:
            costs = get_subagent_costs()
            print(f"Total subagent cost: ${costs['total_estimated_cost']:.4f}")
        """
        try:
            manager = _get_manager()
            summary = manager.get_subagent_costs_summary()

            return {
                "success": True,
                "operation": "get_subagent_costs",
                **summary,
            }

        except Exception as e:
            logger.error(f"[SubagentMCP] Error getting subagent costs: {e}")
            return {
                "success": False,
                "operation": "get_subagent_costs",
                "error": str(e),
            }

    @mcp.tool()
    def check_subagent_status(subagent_id: str) -> Dict[str, Any]:
        """
        Check the current status of a subagent (especially useful for background subagents).

        Use this to monitor progress of subagents spawned in non-blocking mode.

        Args:
            subagent_id: ID of the subagent to check

        Returns:
            Dictionary with status information:
            - success: bool
            - operation: str - "check_subagent_status"
            - subagent_id: str - The subagent ID
            - status: str - "pending", "running", "completed", "failed", or "timeout"
            - task: str - The task description
            - progress: str - Progress message (if available)
            - started_at: str - ISO timestamp
            - updated_at: str - ISO timestamp
            - completed_at: str - ISO timestamp (if finished)
            - error: str - Error message (if failed)

        Example:
            status = check_subagent_status("research_oauth")
            if status['status'] == 'completed':
                result = get_subagent_result("research_oauth")
        """
        try:
            manager = _get_manager()
            status = manager.get_subagent_status(subagent_id)

            if status is None:
                return {
                    "success": False,
                    "operation": "check_subagent_status",
                    "error": f"Subagent not found: {subagent_id}",
                }

            return {
                "success": True,
                "operation": "check_subagent_status",
                **status,
            }

        except Exception as e:
            logger.error(f"[SubagentMCP] Error checking subagent status: {e}")
            return {
                "success": False,
                "operation": "check_subagent_status",
                "error": str(e),
            }

    @mcp.tool()
    def get_subagent_result(subagent_id: str) -> Dict[str, Any]:
        """
        Get the result from a previously spawned subagent.

        Use this to retrieve results if you need to check on a subagent later.
        For background subagents, first check status with check_subagent_status().

        Args:
            subagent_id: ID of the subagent to get results for

        Returns:
            Dictionary with subagent result (same format as spawn_subagents results)

        Example:
            result = get_subagent_result("research_oauth")
            if result['success']:
                print(result['answer'])
        """
        try:
            manager = _get_manager()
            result = manager.get_subagent_result(subagent_id)

            if result is None:
                return {
                    "success": False,
                    "operation": "get_subagent_result",
                    "error": f"Subagent not found: {subagent_id}",
                }

            return {
                "success": True,
                "operation": "get_subagent_result",
                **result.to_dict(),
            }

        except Exception as e:
            logger.error(f"[SubagentMCP] Error getting subagent result: {e}")
            return {
                "success": False,
                "operation": "get_subagent_result",
                "error": str(e),
            }

    return mcp


async def _cleanup_on_shutdown():
    """Clean up subagent processes on shutdown."""
    global _manager
    if _manager is not None:
        logger.info("[SubagentMCP] Shutting down - cancelling active subagents...")
        cancelled = await _manager.cancel_all_subagents()
        if cancelled > 0:
            logger.info(f"[SubagentMCP] Cancelled {cancelled} subagent(s)")


def _setup_signal_handlers(loop: asyncio.AbstractEventLoop):
    """Set up signal handlers for graceful shutdown."""

    def handle_signal(signum, frame):
        logger.info(f"[SubagentMCP] Received signal {signum}, initiating shutdown...")
        # Schedule cleanup on the event loop
        loop.create_task(_cleanup_on_shutdown())

    # Handle SIGTERM (from process termination) and SIGINT (Ctrl+C)
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)


def _sync_cleanup():
    """Synchronous cleanup for atexit handler."""
    global _manager
    if _manager is not None and _manager._active_processes:
        logger.info("[SubagentMCP] atexit cleanup - terminating active subagents...")
        for subagent_id, process in list(_manager._active_processes.items()):
            if process.returncode is None:
                try:
                    process.terminate()
                    logger.info(f"[SubagentMCP] Terminated subagent {subagent_id}")
                except Exception as e:
                    logger.error(f"[SubagentMCP] Error terminating {subagent_id}: {e}")


if __name__ == "__main__":
    import asyncio

    import fastmcp

    asyncio.run(fastmcp.run(create_server))
