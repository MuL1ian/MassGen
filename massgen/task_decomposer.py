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
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

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


class TaskDecomposer:
    """Decomposes a task into subtasks for decomposition mode agents.

    Follows the same pattern as PersonaGenerator.generate_personas_via_subagent():
    uses SubagentManager to spawn a MassGen subagent with simplified config.
    """

    def __init__(self, config: TaskDecomposerConfig):
        self.config = config

    async def generate_decomposition_via_subagent(
        self,
        task: str,
        agent_ids: List[str],
        existing_system_messages: Dict[str, Optional[str]],
        parent_agent_configs: List[Dict[str, Any]],
        parent_workspace: str,
        orchestrator_id: str,
        log_directory: Optional[str] = None,
    ) -> Dict[str, str]:
        """Generate subtask assignments via a MassGen subagent call.

        Uses SubagentManager to spawn a full MassGen subagent with simplified config
        (tools stripped). If parent has 1 agent, uses single agent + skip voting.
        If parent has N agents, uses N agents with voting for redundancy.

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
        from .subagent.manager import SubagentManager

        n_agents = len(agent_ids)

        # Build agent expertise descriptions
        agent_descriptions = []
        for aid, sys_msg in existing_system_messages.items():
            desc = sys_msg[:200] if sys_msg else "General-purpose agent"
            agent_descriptions.append(f"- {aid}: {desc}")

        guidelines_section = ""
        if self.config.decomposition_guidelines:
            guidelines_section = f"\nDecomposition guidelines: {self.config.decomposition_guidelines}\n"

        prompt = f"""Decompose the following task into {n_agents} complementary subtasks.
Each subtask should be:
- Self-contained enough to work on independently
- Clearly scoped with defined deliverables
- Complementary to other subtasks (no major overlaps)

Task: {task}

Agents and their expertise:
{chr(10).join(agent_descriptions)}
{guidelines_section}
Write a JSON file to workspace/decomposition.json with this exact format:
{{"subtasks": {{{", ".join(f'"{aid}": "subtask description"' for aid in agent_ids)}}}}}

The file MUST contain valid JSON with a "subtasks" key mapping each agent ID to their subtask description."""

        # Build subagent config - inherit first parent agent's model, strip tools
        if parent_agent_configs:
            base_config = parent_agent_configs[0].copy()
        else:
            base_config = {"type": "openai", "model": "gpt-4o-mini"}

        # Strip tool-related config
        for key in [
            "mcp_servers",
            "enable_mcp_command_line",
            "cwd",
            "context_paths",
            "enable_code_based_tools",
            "custom_tools_path",
        ]:
            base_config.pop(key, None)

        # Create subagent config
        subagent_config = {
            "agents": [
                {
                    "id": "decomposer",
                    "backend": base_config,
                    "system_message": "You are a task decomposition expert. Break down complex tasks into clear, complementary subtasks.",
                },
            ],
            "orchestrator": {
                "skip_voting": True,
                "skip_final_presentation": True,
            },
        }

        # Create subagent workspace
        subagent_workspace = os.path.join(parent_workspace, ".decomposer")
        os.makedirs(subagent_workspace, exist_ok=True)

        try:
            manager = SubagentManager(
                parent_orchestrator_id=orchestrator_id,
                parent_workspace=parent_workspace,
            )

            result = await manager.run_subagent(
                task=prompt,
                config=subagent_config,
                workspace=subagent_workspace,
                timeout=120,
                log_directory=log_directory,
            )

            # Try to parse decomposition.json from workspace
            decomp_path = os.path.join(subagent_workspace, "workspace", "decomposition.json")
            if os.path.exists(decomp_path):
                with open(decomp_path) as f:
                    data = json.load(f)
                subtasks = data.get("subtasks", {})
                if subtasks and all(aid in subtasks for aid in agent_ids):
                    logger.info(f"[TaskDecomposer] Successfully decomposed task into {len(subtasks)} subtasks")
                    return subtasks

            # Try to parse from result text
            if result and hasattr(result, "final_answer") and result.final_answer:
                try:
                    # Look for JSON in the answer
                    answer = result.final_answer
                    start = answer.find("{")
                    end = answer.rfind("}") + 1
                    if start >= 0 and end > start:
                        data = json.loads(answer[start:end])
                        subtasks = data.get("subtasks", {})
                        if subtasks:
                            logger.info("[TaskDecomposer] Parsed subtasks from answer text")
                            return subtasks
                except (json.JSONDecodeError, KeyError):
                    pass

            logger.warning("[TaskDecomposer] Could not parse decomposition, using fallback")

        except Exception as e:
            logger.warning(f"[TaskDecomposer] Subagent failed: {e}, using fallback")

        # Fallback: generate generic subtasks based on system messages
        return self._generate_fallback_subtasks(task, agent_ids, existing_system_messages)

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
                subtasks[aid] = f"Work on your area of expertise as described in your role. Focus on the aspects of the task that align with your specialization: {sys_msg[:100]}"
            else:
                subtasks[aid] = f"Work on part {i + 1} of {len(agent_ids)} for this task. Coordinate with other agents to avoid overlap."

        logger.info(f"[TaskDecomposer] Generated {len(subtasks)} fallback subtasks")
        return subtasks
