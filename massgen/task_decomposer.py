# -*- coding: utf-8 -*-
"""
Task decomposer for MassGen decomposition mode.

When coordination_mode is "decomposition" but no explicit subtasks are defined,
auto-decomposes the task using a MassGen subagent call (following the persona
generator pattern in persona_generator.py).
"""

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TaskDecomposerConfig:
    """Configuration for automatic task decomposition.

    Attributes:
        enabled: Whether auto-decomposition is enabled when no explicit subtasks given
        decomposition_guidelines: Optional custom guidelines for how to decompose
    """

    enabled: bool = True
    decomposition_guidelines: Optional[str] = None
    timeout_seconds: int = 300


class TaskDecomposer:
    """Decomposes a task into subtasks for decomposition mode agents.

    Follows the same pattern as PersonaGenerator.generate_personas_via_subagent():
    uses SubagentManager to spawn a MassGen subagent with simplified config.
    """

    def __init__(self, config: TaskDecomposerConfig):
        self.config = config
        # Exposed for diagnostics/telemetry: "subagent" | "fallback"
        self.last_generation_source: str = "unknown"

    async def generate_decomposition_via_subagent(
        self,
        task: str,
        agent_ids: List[str],
        existing_system_messages: Dict[str, Optional[str]],
        parent_agent_configs: List[Dict[str, Any]],
        parent_workspace: str,
        orchestrator_id: str,
        log_directory: Optional[str] = None,
        on_subagent_started: Optional[Callable[[str, str, int, Callable[[str], Optional[Any]], Optional[str]], None]] = None,
    ) -> Dict[str, str]:
        """Generate subtask assignments via a MassGen subagent call.

        Uses SubagentManager to spawn a full MassGen subagent with simplified config.
        Returns parsed subtasks if successful, otherwise falls back to role-based
        heuristic subtasks.

        Args:
            task: The original task/query to decompose
            agent_ids: List of agent IDs to assign subtasks to
            existing_system_messages: Existing system messages per agent
            parent_agent_configs: List of parent agent configurations to inherit models from
            parent_workspace: Path to parent workspace for subagent workspace creation
            orchestrator_id: ID of the parent orchestrator
            log_directory: Optional path to log directory for subagent logs

        Returns:
            Dictionary mapping agent_id to subtask description
        """
        self.last_generation_source = "unknown"

        if not agent_ids:
            logger.warning("[TaskDecomposer] No agent IDs provided; skipping decomposition")
            self.last_generation_source = "fallback"
            return {}

        from .subagent.manager import SubagentManager
        from .subagent.models import SubagentOrchestratorConfig

        n_agents = len(agent_ids)

        # Build agent expertise descriptions
        agent_descriptions = []
        for aid in agent_ids:
            sys_msg = existing_system_messages.get(aid)
            desc = sys_msg[:200] if sys_msg else "General-purpose agent"
            agent_descriptions.append(f"- {aid}: {desc}")

        guidelines_section = ""
        if self.config.decomposition_guidelines:
            guidelines_section = f"\nDecomposition guidelines: {self.config.decomposition_guidelines}\n"

        prompt = f"""Create a decomposition plan for {n_agents} agents.

Task: {task}

Agents and their expertise:
{chr(10).join(agent_descriptions)}
{guidelines_section}
Requirements:
- Assign exactly one subtask to each agent ID.
- Keep subtasks complementary and non-overlapping.
- Make each subtask concrete and actionable.
- Ensure subtasks are roughly equal in expected effort and completion time.
- Return valid JSON only (no markdown/prose), using this schema:
{{"subtasks": {{{", ".join(f'"{aid}": "subtask description"' for aid in agent_ids)}}}}}
"""

        # Normalize parent configs to [{id, backend}, ...]
        normalized_parent_configs: List[Dict[str, Any]] = []
        for idx, aid in enumerate(agent_ids):
            raw = parent_agent_configs[idx] if idx < len(parent_agent_configs) else {}
            if isinstance(raw, dict) and "backend" in raw:
                backend = raw.get("backend", {}) if isinstance(raw.get("backend"), dict) else {}
                normalized_parent_configs.append({"id": raw.get("id", aid), "backend": backend})
            elif isinstance(raw, dict):
                normalized_parent_configs.append({"id": aid, "backend": raw})
            else:
                normalized_parent_configs.append({"id": aid, "backend": {}})

        # Build simplified configs using same models, but strip tools.
        simplified_configs: List[Dict[str, Any]] = []
        for idx, aid in enumerate(agent_ids):
            backend = normalized_parent_configs[idx].get("backend", {}) if idx < len(normalized_parent_configs) else {}
            simplified_backend: Dict[str, Any] = {
                "type": backend.get("type", "openai"),
                "model": backend.get("model") or "gpt-4o-mini",
                "enable_mcp_command_line": False,
                "enable_code_based_tools": False,
                "exclude_file_operation_mcps": True,
            }
            base_url = backend.get("base_url")
            if base_url:
                simplified_backend["base_url"] = base_url
            simplified_configs.append({"id": aid, "backend": simplified_backend})

        # Create dedicated decomposition workspace and guaranteed CONTEXT.md.
        base_workspace = parent_workspace or os.getcwd()
        decomposer_workspace = os.path.join(base_workspace, ".decomposer")
        os.makedirs(decomposer_workspace, exist_ok=True)
        context_md = os.path.join(decomposer_workspace, "CONTEXT.md")
        with open(context_md, "w", encoding="utf-8") as f:
            f.write(
                "# Task Decomposition Context\n\n" f"Task:\n{task}\n\n" "Goal: produce a clear per-agent subtask assignment JSON.\n",
            )

        try:
            # Use orchestrator mode so decomposition itself can be multi-agent.
            subagent_orch_config = SubagentOrchestratorConfig(
                enabled=True,
                agents=simplified_configs,
                coordination={
                    "enable_subagents": False,
                    "broadcast": False,
                },
                max_new_answers=2,
            )

            manager = SubagentManager(
                parent_workspace=decomposer_workspace,
                parent_agent_id="task_decomposer",
                orchestrator_id=orchestrator_id,
                parent_agent_configs=simplified_configs,
                max_concurrent=1,
                default_timeout=self.config.timeout_seconds,
                subagent_orchestrator_config=subagent_orch_config,
                log_directory=log_directory,
            )

            def _status_callback(subagent_id: str) -> Optional[Any]:
                try:
                    return manager.get_subagent_display_data(subagent_id)
                except Exception:
                    return None

            if on_subagent_started:
                try:
                    subagent_log_path = None
                    if log_directory:
                        subagent_log_path = str(Path(log_directory) / "subagents" / "task_decomposition")
                    on_subagent_started(
                        "task_decomposition",
                        prompt,
                        self.config.timeout_seconds,
                        _status_callback,
                        subagent_log_path,
                    )
                except Exception:
                    pass

            result = await manager.spawn_subagent(
                task=prompt,
                subagent_id="task_decomposition",
                timeout_seconds=self.config.timeout_seconds,
                refine=False,
            )

            subtasks: Dict[str, str] = {}
            if result.answer:
                subtasks = self._parse_subtasks_from_text(result.answer, agent_ids)

            # Fallback parser: scan workspace for decomposition JSON files.
            if not subtasks and result.workspace_path:
                subtasks = self._parse_subtasks_from_workspace(result.workspace_path, agent_ids)

            if subtasks:
                self.last_generation_source = "subagent"
                logger.info(
                    f"[TaskDecomposer] Parsed {len(subtasks)} subtasks from decomposition subagent",
                )
                return subtasks

            logger.warning("[TaskDecomposer] Could not parse decomposition, using fallback")

        except Exception as e:
            logger.warning(f"[TaskDecomposer] Subagent failed: {e}, using fallback")

        # Fallback: generate generic subtasks based on system messages
        self.last_generation_source = "fallback"
        return self._generate_fallback_subtasks(task, agent_ids, existing_system_messages)

    def _parse_subtasks_from_text(self, text: str, agent_ids: List[str]) -> Dict[str, str]:
        """Parse decomposition JSON from model text output."""
        candidates = [text.strip()]

        # Prefer fenced JSON if present.
        for match in re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL):
            candidates.append(match.strip())

        # Fallback: first outer JSON object in the text.
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            candidates.append(text[start : end + 1].strip())

        for candidate in candidates:
            if not candidate:
                continue
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                continue

            if isinstance(payload, dict):
                subtasks_obj = payload.get("subtasks", payload)
                if isinstance(subtasks_obj, dict):
                    normalized = self._normalize_subtasks(subtasks_obj, agent_ids)
                    if normalized:
                        return normalized

        return {}

    def _parse_subtasks_from_workspace(self, workspace_path: str, agent_ids: List[str]) -> Dict[str, str]:
        """Parse decomposition JSON artifacts from subagent workspace.

        Searches three locations in order:
        1. Direct workspace files (workspace root and agent_* dirs)
        2. Log final/ directories - the orchestrator archives agent workspaces
           to final/ before clearing them, so this is the reliable source.
        """
        workspace = Path(workspace_path)
        if not workspace.exists():
            return {}

        candidate_files: List[Path] = [
            workspace / "decomposition.json",
            workspace / "subtasks.json",
        ]
        for agent_dir in workspace.glob("agent_*"):
            candidate_files.extend(
                [
                    agent_dir / "decomposition.json",
                    agent_dir / "subtasks.json",
                    agent_dir / "workspace" / "decomposition.json",
                    agent_dir / "workspace" / "subtasks.json",
                ],
            )

        # Also search the subprocess log final/ directories.
        # The orchestrator clears agent workspaces between rounds, but the
        # final/ snapshot is always preserved in the log directory.
        massgen_logs = workspace / ".massgen" / "massgen_logs"
        if massgen_logs.exists():
            for final_workspace in massgen_logs.glob("*/turn_*/attempt_*/final/*/workspace"):
                candidate_files.extend(
                    [
                        final_workspace / "decomposition.json",
                        final_workspace / "subtasks.json",
                    ],
                )

        for path in candidate_files:
            if not path.exists() or not path.is_file():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue

            if isinstance(data, dict):
                subtasks_obj = data.get("subtasks", data)
                if isinstance(subtasks_obj, dict):
                    normalized = self._normalize_subtasks(subtasks_obj, agent_ids)
                    if normalized:
                        logger.info(f"[TaskDecomposer] Found subtasks in {path}")
                        return normalized

        return {}

    def _normalize_subtasks(self, subtasks: Dict[str, Any], agent_ids: List[str]) -> Dict[str, str]:
        """Normalize parsed subtask map and ensure all agent IDs are covered."""
        cleaned: Dict[str, str] = {}

        for aid in agent_ids:
            value = subtasks.get(aid)
            if isinstance(value, str) and value.strip():
                cleaned[aid] = value.strip()

        # If partial, fill missing entries with role-aware fallbacks.
        if cleaned and len(cleaned) < len(agent_ids):
            existing_subtasks = ", ".join(f"{k}: {v[:60]}" for k, v in cleaned.items())
            for idx, aid in enumerate(agent_ids):
                if aid not in cleaned:
                    cleaned[aid] = f"Handle aspects of the task not covered by other agents " f"({existing_subtasks}). Focus on complementary work as agent '{aid}'."

        return cleaned

    def _generate_fallback_subtasks(
        self,
        task: str,
        agent_ids: List[str],
        system_messages: Dict[str, Optional[str]],
    ) -> Dict[str, str]:
        """Generate generic subtask assignments when auto-decomposition fails.

        Uses agent system messages to infer subtask roles.
        """
        subtasks = {}
        for i, aid in enumerate(agent_ids):
            sys_msg = system_messages.get(aid)
            if sys_msg:
                subtasks[aid] = "Work on your area of expertise as described in your role. " "Focus on the aspects of the task that align with your specialization: " f"{sys_msg[:100]}"
            else:
                subtasks[aid] = f"Work on part {i + 1} of {len(agent_ids)} for this task. Coordinate with other agents to avoid overlap."

        logger.info(f"[TaskDecomposer] Generated {len(subtasks)} fallback subtasks")
        return subtasks
