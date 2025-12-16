# -*- coding: utf-8 -*-
"""
Subagent Manager for MassGen

Manages the lifecycle of subagents: creation, workspace setup, execution, and result collection.
"""

import asyncio
import json
import logging
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from massgen.subagent.models import (
    SubagentConfig,
    SubagentOrchestratorConfig,
    SubagentPointer,
    SubagentResult,
    SubagentState,
)

logger = logging.getLogger(__name__)


class SubagentManager:
    """
    Manages subagent lifecycle, workspaces, and execution.

    Responsible for:
    - Creating isolated workspaces for subagents
    - Spawning and executing subagent tasks
    - Collecting and formatting results
    - Tracking active subagents
    - Cleanup on completion

    Subagents cannot spawn their own subagents (no nesting).
    """

    def __init__(
        self,
        parent_workspace: str,
        parent_agent_id: str,
        orchestrator_id: str,
        parent_backend_config: Dict[str, Any],
        max_concurrent: int = 3,
        default_timeout: int = 300,
        subagent_orchestrator_config: Optional[SubagentOrchestratorConfig] = None,
        log_directory: Optional[str] = None,
    ):
        """
        Initialize SubagentManager.

        Args:
            parent_workspace: Path to parent agent's workspace
            parent_agent_id: ID of the parent agent
            orchestrator_id: ID of the orchestrator
            parent_backend_config: Backend configuration to inherit from parent
            max_concurrent: Maximum concurrent subagents (default 3)
            default_timeout: Default timeout in seconds (default 300)
            subagent_orchestrator_config: Configuration for subagent orchestrator mode.
                When enabled, subagents use a full Orchestrator with multiple agents
                instead of a single ConfigurableAgent.
            log_directory: Path to main run's log directory for subagent logs.
                Subagent logs will be written to {log_directory}/subagents/{subagent_id}/
        """
        self.parent_workspace = Path(parent_workspace)
        self.parent_agent_id = parent_agent_id
        self.orchestrator_id = orchestrator_id
        self.parent_backend_config = parent_backend_config
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self._subagent_orchestrator_config = subagent_orchestrator_config

        # Log directory for subagent logs (in main run's log dir)
        self._log_directory = Path(log_directory) if log_directory else None
        if self._log_directory:
            self._subagent_logs_base = self._log_directory / "subagents"
            self._subagent_logs_base.mkdir(parents=True, exist_ok=True)
        else:
            self._subagent_logs_base = None

        # Base path for all subagent workspaces
        self.subagents_base = self.parent_workspace / "subagents"
        self.subagents_base.mkdir(parents=True, exist_ok=True)

        # Track active and completed subagents
        self._subagents: Dict[str, SubagentState] = {}
        # Track background tasks for non-blocking execution
        self._background_tasks: Dict[str, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)

        logger.info(
            f"[SubagentManager] Initialized for parent {parent_agent_id}, "
            f"workspace: {self.subagents_base}, max_concurrent: {max_concurrent}" + (f", log_dir: {self._subagent_logs_base}" if self._subagent_logs_base else ""),
        )

    def _create_workspace(self, subagent_id: str) -> Path:
        """
        Create isolated workspace for a subagent.

        Args:
            subagent_id: Unique subagent identifier

        Returns:
            Path to the subagent's workspace directory
        """
        subagent_dir = self.subagents_base / subagent_id
        workspace = subagent_dir / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)

        # Create metadata file
        metadata = {
            "subagent_id": subagent_id,
            "parent_agent_id": self.parent_agent_id,
            "created_at": datetime.now().isoformat(),
            "workspace_path": str(workspace),
        }
        metadata_file = subagent_dir / "_metadata.json"
        metadata_file.write_text(json.dumps(metadata, indent=2))

        logger.info(f"[SubagentManager] Created workspace for {subagent_id}: {workspace}")
        return workspace

    def _get_subagent_log_dir(self, subagent_id: str) -> Optional[Path]:
        """
        Get or create the log directory for a subagent.

        Args:
            subagent_id: Subagent identifier

        Returns:
            Path to subagent log directory, or None if logging not configured
        """
        if not self._subagent_logs_base:
            return None

        log_dir = self._subagent_logs_base / subagent_id
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    def _write_status(
        self,
        subagent_id: str,
        status: str,
        task: str,
        progress: Optional[str] = None,
        error: Optional[str] = None,
        token_usage: Optional[Dict[str, Any]] = None,
        answer: Optional[str] = None,
    ) -> None:
        """
        Write or update status.json for a subagent.

        Args:
            subagent_id: Subagent identifier
            status: Current status (pending, running, completed, failed, timeout)
            task: Task description
            progress: Optional progress message
            error: Optional error message
            token_usage: Optional token usage stats
            answer: Optional final answer (when completed)
        """
        log_dir = self._get_subagent_log_dir(subagent_id)
        if not log_dir:
            return

        status_file = log_dir / "status.json"

        # Read existing status if it exists
        existing = {}
        if status_file.exists():
            try:
                existing = json.loads(status_file.read_text())
            except json.JSONDecodeError:
                pass

        # Update status
        status_data = {
            "subagent_id": subagent_id,
            "status": status,
            "task": task,
            "started_at": existing.get("started_at", datetime.now().isoformat()),
            "updated_at": datetime.now().isoformat(),
            "progress": progress,
            "error": error,
            "token_usage": token_usage or existing.get("token_usage", {}),
        }

        if status in ("completed", "failed", "timeout"):
            status_data["completed_at"] = datetime.now().isoformat()
            if answer:
                status_data["answer"] = answer

        status_file.write_text(json.dumps(status_data, indent=2))

    def _append_conversation(
        self,
        subagent_id: str,
        role: str,
        content: str,
        agent_id: Optional[str] = None,
    ) -> None:
        """
        Append a message to the conversation log.

        Args:
            subagent_id: Subagent identifier
            role: Message role (user, assistant, system)
            content: Message content
            agent_id: Optional agent ID for multi-agent orchestrator mode
        """
        log_dir = self._get_subagent_log_dir(subagent_id)
        if not log_dir:
            return

        conversation_file = log_dir / "conversation.json"

        # Read existing conversation
        conversation = []
        if conversation_file.exists():
            try:
                conversation = json.loads(conversation_file.read_text())
            except json.JSONDecodeError:
                pass

        # Append new message
        message = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content,
        }
        if agent_id:
            message["agent_id"] = agent_id

        conversation.append(message)
        conversation_file.write_text(json.dumps(conversation, indent=2))

    def _copy_context_files(
        self,
        subagent_id: str,
        context_files: List[str],
        workspace: Path,
    ) -> List[str]:
        """
        Copy context files from parent workspace to subagent workspace.

        Args:
            subagent_id: Subagent identifier
            context_files: List of relative paths to copy
            workspace: Subagent workspace path

        Returns:
            List of successfully copied files
        """
        copied = []
        for rel_path in context_files:
            src = self.parent_workspace / rel_path
            if not src.exists():
                logger.warning(f"[SubagentManager] Context file not found: {src}")
                continue

            # Preserve directory structure
            dst = workspace / rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)

            if src.is_file():
                shutil.copy2(src, dst)
                copied.append(rel_path)
            elif src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
                copied.append(rel_path)

        logger.info(f"[SubagentManager] Copied {len(copied)} context files for {subagent_id}")
        return copied

    def _build_subagent_system_prompt(self, config: SubagentConfig) -> str:
        """
        Build system prompt for subagent.

        Subagents get a minimal system prompt focused on their specific task.
        They cannot spawn their own subagents.

        Args:
            config: Subagent configuration

        Returns:
            System prompt string
        """
        base_prompt = config.system_prompt or "You are a helpful assistant working on a specific task."

        # Build context section if provided
        context_section = ""
        if config.context:
            context_section = f"""
**Project Context:**
{config.context}

"""

        subagent_prompt = f"""{base_prompt}

## Subagent Context

You are a subagent spawned to work on a specific task. Your workspace is isolated and independent.
{context_section}
**Important:**
- Focus only on the task you were given
- Create any necessary files in your workspace
- You cannot spawn additional subagents

**Output Requirements:**
- In your final answer, clearly list all files you want the parent agent to see along with their FULL ABSOLUTE PATHS. You can also list directories if needed.
- You should NOT list every single file as the parent agent does not need to know every file you created -- this context isolation is a main feature of subagents.
- The parent agent will copy files from your workspace based on your answer
- Format file paths clearly, e.g.: "Files created: /path/to/file1.md, /path/to/file2.py"

**Your Task:**
{config.task}
"""
        return subagent_prompt

    async def _execute_subagent(
        self,
        config: SubagentConfig,
        workspace: Path,
    ) -> SubagentResult:
        """
        Execute a subagent task - routes to single agent or orchestrator mode.

        Args:
            config: Subagent configuration
            workspace: Path to subagent workspace

        Returns:
            SubagentResult with execution outcome
        """
        start_time = time.time()

        try:
            # Always use orchestrator mode for subagent execution
            return await self._execute_with_orchestrator(config, workspace, start_time)

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            return SubagentResult.create_timeout(
                subagent_id=config.id,
                workspace_path=str(workspace),
                timeout_seconds=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"[SubagentManager] Error executing subagent {config.id}: {e}")
            return SubagentResult.create_error(
                subagent_id=config.id,
                error=str(e),
                workspace_path=str(workspace),
                execution_time_seconds=execution_time,
            )

    async def _execute_with_orchestrator(
        self,
        config: SubagentConfig,
        workspace: Path,
        start_time: float,
    ) -> SubagentResult:
        """
        Execute subagent by spawning a separate MassGen process.

        This approach avoids nested MCP/async issues by running the subagent
        as a completely independent MassGen instance with its own YAML config.

        Args:
            config: Subagent configuration
            workspace: Path to subagent workspace
            start_time: Execution start time

        Returns:
            SubagentResult with execution outcome
        """
        import subprocess

        import yaml

        orch_config = self._subagent_orchestrator_config

        # Build context paths from config.context_files
        # These are ALWAYS read-only - subagents cannot write to context paths.
        # If the parent agent needs changes from the subagent, it should copy
        # the desired files from the subagent's workspace after completion.
        context_paths: List[Dict[str, str]] = []
        if config.context_files:
            for ctx_file in config.context_files:
                src_path = Path(ctx_file)
                if src_path.exists():
                    # ALWAYS read-only - no write access for subagents
                    context_paths.append(
                        {
                            "path": str(src_path.resolve()),
                            "permission": "read",  # Never "write" - enforced by design
                        },
                    )
                    logger.info(f"[SubagentManager] Adding read-only context path: {src_path}")
                else:
                    logger.warning(f"[SubagentManager] Context file not found: {ctx_file}")

        # Generate temporary YAML config for the subagent
        subagent_yaml = self._generate_subagent_yaml_config(config, workspace, context_paths)
        yaml_path = workspace / f"subagent_config_{config.id}.yaml"
        yaml_path.write_text(yaml.dump(subagent_yaml, default_flow_style=False))

        logger.info(
            f"[SubagentManager] Executing subagent {config.id} via subprocess " f"({orch_config.num_agents} agents), config: {yaml_path}",
        )

        # Build the task with system prompt context
        system_prompt = self._build_subagent_system_prompt(config)
        full_task = f"{system_prompt}\n\n---\n\nTask:\n{config.task}"

        # Build command to run MassGen as subprocess
        # Use --automation for minimal output and --output-file to capture the answer
        answer_file = workspace / "answer.txt"
        cmd = [
            "uv",
            "run",
            "massgen",
            "--config",
            str(yaml_path),
            "--automation",  # Silent mode with minimal output
            "--output-file",
            str(answer_file),  # Write final answer to file
            full_task,
        ]

        # Run the subprocess
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=config.timeout_seconds or self.default_timeout,
                    cwd=str(workspace),
                ),
            )

            if result.returncode == 0:
                # Read answer from the output file
                if answer_file.exists():
                    answer = answer_file.read_text().strip()
                else:
                    # Fallback to stdout if file wasn't created
                    answer = result.stdout.strip()

                execution_time = time.time() - start_time

                # Get token usage and log path from subprocess's status.json
                token_usage, subprocess_log_dir = self._parse_subprocess_status(workspace)

                # Write reference to subprocess log directory
                self._write_subprocess_log_reference(config.id, subprocess_log_dir)

                return SubagentResult.create_success(
                    subagent_id=config.id,
                    answer=answer,
                    workspace_path=str(workspace),
                    execution_time_seconds=execution_time,
                    token_usage=token_usage,
                )
            else:
                error_msg = result.stderr.strip() or f"Subprocess exited with code {result.returncode}"
                logger.error(f"[SubagentManager] Subagent {config.id} failed: {error_msg}")

                # Still try to get log path for debugging
                _, subprocess_log_dir = self._parse_subprocess_status(workspace)
                self._write_subprocess_log_reference(config.id, subprocess_log_dir, error=error_msg)
                return SubagentResult.create_error(
                    subagent_id=config.id,
                    error=error_msg,
                    workspace_path=str(workspace),
                    execution_time_seconds=time.time() - start_time,
                )

        except subprocess.TimeoutExpired:
            logger.error(f"[SubagentManager] Subagent {config.id} timed out")
            return SubagentResult.create_error(
                subagent_id=config.id,
                error=f"Subagent timed out after {config.timeout_seconds or self.default_timeout}s",
                workspace_path=str(workspace),
                execution_time_seconds=time.time() - start_time,
            )
        except Exception as e:
            logger.error(f"[SubagentManager] Subagent {config.id} error: {e}")
            return SubagentResult.create_error(
                subagent_id=config.id,
                error=str(e),
                workspace_path=str(workspace),
                execution_time_seconds=time.time() - start_time,
            )

    def _generate_subagent_yaml_config(
        self,
        config: SubagentConfig,
        workspace: Path,
        context_paths: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a YAML config dict for the subagent MassGen process.

        Inherits relevant settings from parent backend config but adjusts
        paths and disables subagent nesting.

        Args:
            config: Subagent configuration
            workspace: Workspace path for the subagent
            context_paths: Optional list of context path configs for file access

        Returns:
            Dictionary suitable for YAML serialization
        """
        orch_config = self._subagent_orchestrator_config

        # Build agent configs based on num_agents
        # Each agent needs a unique workspace directory
        agents = []
        for i in range(orch_config.num_agents):
            agent_id = f"{config.id}_agent_{i+1}"
            # Create unique workspace for each agent
            agent_workspace = workspace / f"agent_{i+1}"
            agent_workspace.mkdir(parents=True, exist_ok=True)

            agent_config = {
                "id": agent_id,
                "backend": {
                    "type": self.parent_backend_config.get("type", "openai"),
                    "model": orch_config.agent_model or config.model or self.parent_backend_config.get("model"),
                    "cwd": str(agent_workspace),  # Each agent gets unique workspace
                    # Inherit relevant backend settings
                    "enable_mcp_command_line": self.parent_backend_config.get("enable_mcp_command_line", False),
                    "command_line_execution_mode": self.parent_backend_config.get("command_line_execution_mode", "local"),
                },
            }

            # Copy reasoning config if present
            if "reasoning" in self.parent_backend_config:
                agent_config["backend"]["reasoning"] = self.parent_backend_config["reasoning"]

            agents.append(agent_config)

        # Build coordination config - disable subagents to prevent nesting
        coord_settings = orch_config.coordination.copy() if orch_config.coordination else {}
        coord_settings["enable_subagents"] = False  # CRITICAL: prevent nesting

        orchestrator_config = {
            "snapshot_storage": str(workspace / "snapshots"),
            "agent_temporary_workspace": str(workspace / "temp"),
            "coordination": coord_settings,
        }

        # Add context paths if provided
        if context_paths:
            orchestrator_config["context_paths"] = context_paths

        yaml_config = {
            "agents": agents,
            "orchestrator": orchestrator_config,
        }

        return yaml_config

    def _parse_subprocess_status(self, workspace: Path) -> tuple[Dict[str, Any], Optional[str]]:
        """
        Parse token usage and log path from the subprocess's status.json.

        Args:
            workspace: Workspace path where status.json might be

        Returns:
            Tuple of (token_usage dict, subprocess_log_dir path or None)
        """
        # Look for status.json in the subprocess's .massgen logs
        massgen_logs = workspace / ".massgen" / "massgen_logs"
        if not massgen_logs.exists():
            return {}, None

        # Find most recent log directory
        for log_dir in sorted(massgen_logs.glob("log_*"), reverse=True):
            status_file = log_dir / "turn_1" / "attempt_1" / "status.json"
            if status_file.exists():
                try:
                    data = json.loads(status_file.read_text())
                    costs = data.get("costs", {})
                    token_usage = {
                        "input_tokens": costs.get("total_input_tokens", 0),
                        "output_tokens": costs.get("total_output_tokens", 0),
                        "estimated_cost": costs.get("total_estimated_cost", 0.0),
                    }
                    return token_usage, str(log_dir / "turn_1" / "attempt_1")
                except Exception:
                    pass
        return {}, None

    def _write_subprocess_log_reference(
        self,
        subagent_id: str,
        subprocess_log_dir: Optional[str],
        error: Optional[str] = None,
    ) -> None:
        """
        Write a reference file pointing to the subprocess's log directory.

        Instead of maintaining our own status.json, we just point to the
        subprocess's complete logs.

        Args:
            subagent_id: Subagent identifier
            subprocess_log_dir: Path to subprocess's log directory
            error: Optional error message if subprocess failed
        """
        log_dir = self._get_subagent_log_dir(subagent_id)
        if not log_dir:
            return

        reference_file = log_dir / "subprocess_logs.json"
        reference_data = {
            "subagent_id": subagent_id,
            "subprocess_log_dir": subprocess_log_dir,
            "timestamp": datetime.now().isoformat(),
        }
        if error:
            reference_data["error"] = error

        reference_file.write_text(json.dumps(reference_data, indent=2))

    async def spawn_subagent(
        self,
        task: str,
        subagent_id: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        context_files: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
    ) -> SubagentResult:
        """
        Spawn a single subagent to work on a task.

        Args:
            task: The task for the subagent
            subagent_id: Optional custom ID
            model: Optional model override
            timeout_seconds: Optional timeout (uses default if not specified)
            context_files: Optional files to copy to subagent workspace
            system_prompt: Optional custom system prompt
            context: Optional project/goal context to provide to the subagent

        Returns:
            SubagentResult with execution outcome
        """
        # Create config
        config = SubagentConfig.create(
            task=task,
            parent_agent_id=self.parent_agent_id,
            subagent_id=subagent_id,
            model=model,
            timeout_seconds=timeout_seconds or self.default_timeout,
            context_files=context_files or [],
            system_prompt=system_prompt,
            context=context,
        )

        logger.info(f"[SubagentManager] Spawning subagent {config.id} for task: {task[:100]}...")

        # Create workspace
        workspace = self._create_workspace(config.id)

        # Copy context files if specified
        if config.context_files:
            self._copy_context_files(config.id, config.context_files, workspace)

        # Track state
        state = SubagentState(
            config=config,
            status="running",
            workspace_path=str(workspace),
            started_at=datetime.now(),
        )
        self._subagents[config.id] = state

        # Initialize logging
        self._write_status(config.id, "running", task, progress="Starting execution...")
        self._append_conversation(config.id, "user", task)

        # Execute with semaphore and timeout
        async with self._semaphore:
            try:
                result = await asyncio.wait_for(
                    self._execute_subagent(config, workspace),
                    timeout=config.timeout_seconds,
                )
            except asyncio.TimeoutError:
                result = SubagentResult.create_timeout(
                    subagent_id=config.id,
                    workspace_path=str(workspace),
                    timeout_seconds=config.timeout_seconds,
                )
                self._write_status(
                    config.id,
                    "timeout",
                    task,
                    error=f"Timed out after {config.timeout_seconds}s",
                )

        # Update state
        state.status = "completed" if result.success else ("timeout" if result.status == "timeout" else "failed")
        state.result = result

        # Log final status
        if result.success:
            self._write_status(
                config.id,
                "completed",
                task,
                token_usage=result.token_usage,
                answer=result.answer,
            )
            if result.answer:
                self._append_conversation(config.id, "assistant", result.answer)
        elif result.status != "timeout":  # timeout already logged above
            self._write_status(
                config.id,
                "failed",
                task,
                error=result.error,
            )

        logger.info(
            f"[SubagentManager] Subagent {config.id} finished with status: {result.status}, " f"time: {result.execution_time_seconds:.2f}s",
        )

        return result

    async def spawn_parallel(
        self,
        tasks: List[Dict[str, Any]],
        context: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> List[SubagentResult]:
        """
        Spawn multiple subagents to run in parallel.

        Args:
            tasks: List of task configurations, each with:
                   - task (required): Task description
                   - subagent_id (optional): Custom ID
                   - model (optional): Model override
                   - context_files (optional): Files to copy
            context: Optional project/goal context to provide to all subagents
            timeout_seconds: Optional timeout for all subagents

        Returns:
            List of SubagentResults in same order as input tasks
        """
        logger.info(f"[SubagentManager] Spawning {len(tasks)} subagents in parallel")

        # Create coroutines for each task
        coroutines = []
        for task_config in tasks:
            coro = self.spawn_subagent(
                task=task_config["task"],
                subagent_id=task_config.get("subagent_id"),
                model=task_config.get("model"),
                timeout_seconds=timeout_seconds or task_config.get("timeout_seconds"),
                context_files=task_config.get("context_files"),
                system_prompt=task_config.get("system_prompt"),
                context=context,
            )
            coroutines.append(coro)

        # Execute all in parallel (semaphore limits concurrency)
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                task_id = tasks[i].get("subagent_id", f"sub_{i}")
                final_results.append(
                    SubagentResult.create_error(
                        subagent_id=task_id,
                        error=str(result),
                    ),
                )
            else:
                final_results.append(result)

        return final_results

    def spawn_subagent_background(
        self,
        task: str,
        subagent_id: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        context_files: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Spawn a subagent in the background (non-blocking).

        Returns immediately with subagent info. Use get_subagent_status() or
        get_subagent_result() to check progress.

        Args:
            task: The task for the subagent
            subagent_id: Optional custom ID
            model: Optional model override
            timeout_seconds: Optional timeout (uses default if not specified)
            context_files: Optional files to copy to subagent workspace
            system_prompt: Optional custom system prompt

        Returns:
            Dictionary with subagent_id and status_file path
        """
        # Create config
        config = SubagentConfig.create(
            task=task,
            parent_agent_id=self.parent_agent_id,
            subagent_id=subagent_id,
            model=model,
            timeout_seconds=timeout_seconds or self.default_timeout,
            context_files=context_files or [],
            system_prompt=system_prompt,
        )

        logger.info(f"[SubagentManager] Spawning background subagent {config.id} for task: {task[:100]}...")

        # Create workspace
        workspace = self._create_workspace(config.id)

        # Copy context files if specified
        if config.context_files:
            self._copy_context_files(config.id, config.context_files, workspace)

        # Track state
        state = SubagentState(
            config=config,
            status="running",
            workspace_path=str(workspace),
            started_at=datetime.now(),
        )
        self._subagents[config.id] = state

        # Initialize logging
        self._write_status(config.id, "running", task, progress="Starting execution...")
        self._append_conversation(config.id, "user", task)

        # Create background task
        async def _run_background():
            async with self._semaphore:
                try:
                    result = await asyncio.wait_for(
                        self._execute_subagent(config, workspace),
                        timeout=config.timeout_seconds,
                    )
                except asyncio.TimeoutError:
                    result = SubagentResult.create_timeout(
                        subagent_id=config.id,
                        workspace_path=str(workspace),
                        timeout_seconds=config.timeout_seconds,
                    )
                    self._write_status(
                        config.id,
                        "timeout",
                        task,
                        error=f"Timed out after {config.timeout_seconds}s",
                    )
                except Exception as e:
                    result = SubagentResult.create_error(
                        subagent_id=config.id,
                        error=str(e),
                        workspace_path=str(workspace),
                    )
                    self._write_status(
                        config.id,
                        "failed",
                        task,
                        error=str(e),
                    )

            # Update state
            state.status = "completed" if result.success else ("timeout" if result.status == "timeout" else "failed")
            state.result = result

            # Log final status
            if result.success:
                self._write_status(
                    config.id,
                    "completed",
                    task,
                    token_usage=result.token_usage,
                    answer=result.answer,
                )
                if result.answer:
                    self._append_conversation(config.id, "assistant", result.answer)

            logger.info(
                f"[SubagentManager] Background subagent {config.id} finished with status: {result.status}, " f"time: {result.execution_time_seconds:.2f}s",
            )

            # Clean up task reference
            if config.id in self._background_tasks:
                del self._background_tasks[config.id]

            return result

        # Schedule the background task
        bg_task = asyncio.create_task(_run_background())
        self._background_tasks[config.id] = bg_task

        # Get status file path
        status_file = None
        if self._subagent_logs_base:
            status_file = str(self._subagent_logs_base / config.id / "status.json")

        return {
            "subagent_id": config.id,
            "status": "running",
            "workspace": str(workspace),
            "status_file": status_file,
        }

    def get_subagent_status(self, subagent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current status of a subagent.

        Args:
            subagent_id: Subagent identifier

        Returns:
            Status dictionary from status.json, or None if not found
        """
        # First check in-memory state
        state = self._subagents.get(subagent_id)
        if not state:
            return None

        # Try to read from status file for latest info
        if self._subagent_logs_base:
            status_file = self._subagent_logs_base / subagent_id / "status.json"
            if status_file.exists():
                try:
                    return json.loads(status_file.read_text())
                except json.JSONDecodeError:
                    pass

        # Fall back to in-memory state
        return {
            "subagent_id": subagent_id,
            "status": state.status,
            "task": state.config.task,
            "workspace": state.workspace_path,
        }

    async def wait_for_subagent(self, subagent_id: str, timeout: Optional[float] = None) -> Optional[SubagentResult]:
        """
        Wait for a background subagent to complete.

        Args:
            subagent_id: Subagent identifier
            timeout: Optional timeout in seconds

        Returns:
            SubagentResult if completed, None if not found or timeout
        """
        task = self._background_tasks.get(subagent_id)
        if not task:
            # Check if already completed
            state = self._subagents.get(subagent_id)
            if state and state.result:
                return state.result
            return None

        try:
            if timeout:
                return await asyncio.wait_for(task, timeout=timeout)
            else:
                return await task
        except asyncio.TimeoutError:
            return None

    def list_subagents(self) -> List[Dict[str, Any]]:
        """
        List all subagents spawned by this manager.

        Returns:
            List of subagent info dictionaries
        """
        return [
            {
                "subagent_id": subagent_id,
                "status": state.status,
                "workspace": state.workspace_path,
                "started_at": state.started_at.isoformat() if state.started_at else None,
                "task": state.config.task[:100] + ("..." if len(state.config.task) > 100 else ""),
            }
            for subagent_id, state in self._subagents.items()
        ]

    def get_subagent_result(self, subagent_id: str) -> Optional[SubagentResult]:
        """
        Get result for a specific subagent.

        Args:
            subagent_id: Subagent identifier

        Returns:
            SubagentResult if subagent exists and completed, None otherwise
        """
        state = self._subagents.get(subagent_id)
        if state and state.result:
            return state.result
        return None

    def get_subagent_costs_summary(self) -> Dict[str, Any]:
        """
        Get aggregated cost summary for all subagents.

        Returns:
            Dictionary with total costs and per-subagent breakdown
        """
        total_input_tokens = 0
        total_output_tokens = 0
        total_estimated_cost = 0.0
        subagent_details = []

        for subagent_id, state in self._subagents.items():
            if state.result and state.result.token_usage:
                tu = state.result.token_usage
                input_tokens = tu.get("input_tokens", 0)
                output_tokens = tu.get("output_tokens", 0)
                cost = tu.get("estimated_cost", 0.0)

                total_input_tokens += input_tokens
                total_output_tokens += output_tokens
                total_estimated_cost += cost

                subagent_details.append(
                    {
                        "subagent_id": subagent_id,
                        "status": state.result.status,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "estimated_cost": round(cost, 6),
                        "execution_time_seconds": state.result.execution_time_seconds,
                    },
                )

        return {
            "total_subagents": len(self._subagents),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_estimated_cost": round(total_estimated_cost, 6),
            "subagents": subagent_details,
        }

    def get_subagent_pointer(self, subagent_id: str) -> Optional[SubagentPointer]:
        """
        Get pointer for a subagent (for plan.json tracking).

        Args:
            subagent_id: Subagent identifier

        Returns:
            SubagentPointer if subagent exists, None otherwise
        """
        state = self._subagents.get(subagent_id)
        if not state:
            return None

        pointer = SubagentPointer(
            id=subagent_id,
            task=state.config.task,
            workspace=state.workspace_path,
            status=state.status,
            created_at=state.config.created_at,
        )

        if state.result:
            pointer.mark_completed(state.result)

        return pointer

    def cleanup_subagent(self, subagent_id: str, remove_workspace: bool = False) -> bool:
        """
        Clean up a subagent.

        Args:
            subagent_id: Subagent identifier
            remove_workspace: If True, also remove the workspace directory

        Returns:
            True if cleanup successful, False if subagent not found
        """
        if subagent_id not in self._subagents:
            return False

        if remove_workspace:
            workspace_dir = self.subagents_base / subagent_id
            if workspace_dir.exists():
                shutil.rmtree(workspace_dir)
                logger.info(f"[SubagentManager] Removed workspace for {subagent_id}")

        del self._subagents[subagent_id]
        return True

    def cleanup_all(self, remove_workspaces: bool = False) -> int:
        """
        Clean up all subagents.

        Args:
            remove_workspaces: If True, also remove workspace directories

        Returns:
            Number of subagents cleaned up
        """
        count = len(self._subagents)
        subagent_ids = list(self._subagents.keys())

        for subagent_id in subagent_ids:
            self.cleanup_subagent(subagent_id, remove_workspace=remove_workspaces)

        return count
