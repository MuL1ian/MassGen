# -*- coding: utf-8 -*-
"""TUI Mode State management for MassGen Textual terminal display.

This module provides the TuiModeState dataclass that tracks mode configuration
and generates orchestrator overrides based on current mode settings.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

if TYPE_CHECKING:
    from massgen.plan_storage import PlanSession

# Type alias for plan depth
PlanDepth = Literal["shallow", "medium", "deep"]


@dataclass
class PlanConfig:
    """Configuration for plan mode behavior.

    Attributes:
        depth: Plan granularity level
            - "shallow": 5-10 high-level tasks
            - "medium": 20-50 tasks (default)
            - "deep": 100-200+ granular tasks
        auto_execute: If True, skip approval and auto-execute after planning
        broadcast: Broadcast mode for planning phase
            - "human": Agents can ask human questions (default)
            - "agents": Agents debate among themselves
            - False: Fully autonomous, no questions
    """

    depth: PlanDepth = "medium"
    auto_execute: bool = False
    broadcast: Any = "human"  # "human" | "agents" | False

    def get_depth_description(self) -> str:
        """Get human-readable description of current depth."""
        descriptions = {
            "shallow": "5-10 tasks",
            "medium": "20-50 tasks",
            "deep": "100-200+ tasks",
        }
        return descriptions.get(self.depth, "20-50 tasks")


@dataclass
class TuiModeState:
    """Tracks TUI mode configuration.

    Manages state for:
    - Plan mode: normal → plan → execute workflow
    - Agent mode: single vs multi-agent
    - Refinement mode: enable/disable voting
    - Override state: human override of final answer selection
    """

    # Plan mode: "normal" | "plan" | "plan_and_execute" | "execute"
    # - "normal": Standard mode, no planning
    # - "plan": Planning mode, will show approval before execute
    # - "plan_and_execute": Planning mode, auto-execute without approval
    # - "execute": Currently executing a plan
    plan_mode: str = "normal"
    plan_session: Optional["PlanSession"] = None
    pending_plan_approval: bool = False
    plan_config: PlanConfig = field(default_factory=PlanConfig)

    # Selected plan ID for execution (None = use latest, "new" = create new)
    selected_plan_id: Optional[str] = None

    # Track the original question for plan execution prompt
    last_planning_question: Optional[str] = None
    # Track which turn planning was initiated on
    planning_started_turn: Optional[int] = None
    # Store context paths from planning phase for execution
    planning_context_paths: Optional[List[Dict[str, Any]]] = None

    # Agent mode: "multi" | "single"
    agent_mode: str = "multi"
    selected_single_agent: Optional[str] = None

    # Refinement mode: True = normal voting, False = disabled
    refinement_enabled: bool = True

    # Override state
    override_pending: bool = False
    override_selected_agent: Optional[str] = None

    # Track if override is available (after voting, before presentation)
    override_available: bool = False

    # Track cancelled state - persists until user provides new input
    was_cancelled: bool = False

    # Execution lock - prevents mode changes during agent execution
    execution_locked: bool = False

    def is_locked(self) -> bool:
        """Check if mode changes are locked (during execution)."""
        return self.execution_locked

    def lock(self) -> None:
        """Lock mode changes (call when execution starts)."""
        self.execution_locked = True

    def unlock(self) -> None:
        """Unlock mode changes (call when execution completes or is cancelled)."""
        self.execution_locked = False

    def get_orchestrator_overrides(self) -> Dict[str, Any]:
        """Generate orchestrator config overrides based on current mode state.

        Returns:
            Dictionary of config overrides to apply to the orchestrator.

        Behavior matrix:
        - Single agent + refinement ON: Keep voting (vote = "I'm done refining")
        - Single agent + refinement OFF: max_new_answers_per_agent=1, skip_voting=True,
          skip_final_presentation=True (quick mode: one answer → done, no extra LLM call)
        - Multi-agent + refinement ON: Normal behavior
        - Multi-agent + refinement OFF: max_new_answers_per_agent=1, skip_final_presentation=True,
          disable_injection=True, defer_voting_until_all_answered=True
          (quick mode: agents work independently, vote once after all answered)
        """
        overrides: Dict[str, Any] = {}

        # Refinement disabled = quick mode
        if not self.refinement_enabled:
            # Limit to one answer per agent
            overrides["max_new_answers_per_agent"] = 1
            # Skip the final presentation LLM call - use existing answer directly
            overrides["skip_final_presentation"] = True

            if self.agent_mode == "single":
                # Single agent + refinement off = one answer, skip voting enforcement
                # Agent submits new_answer → immediate use as final answer
                overrides["skip_voting"] = True
            else:
                # Multi-agent + refinement off = agents work independently
                # No injection (each agent sees only the original task)
                overrides["disable_injection"] = True
                # Defer voting until all agents have answered (avoid wasteful restarts)
                overrides["defer_voting_until_all_answered"] = True
        # Note: Single agent + refinement ON keeps voting - vote signals "I'm done refining"

        return overrides

    def get_coordination_overrides(self) -> Dict[str, Any]:
        """Generate coordination config overrides for plan mode.

        Returns:
            Dictionary of coordination config overrides to apply.
            Returns empty dict if plan mode is not active.

        When plan mode is active, enables:
        - enable_agent_task_planning: True
        - task_planning_filesystem_mode: True
        - plan_depth: From plan_config
        - broadcast: From plan_config
        """
        if self.plan_mode not in ("plan", "plan_and_execute"):
            return {}

        return {
            "enable_agent_task_planning": True,
            "task_planning_filesystem_mode": True,
            "plan_depth": self.plan_config.depth,
            "broadcast": self.plan_config.broadcast,
        }

    def get_effective_agents(self, all_agents: Dict[str, Any]) -> Dict[str, Any]:
        """Return active agents based on mode.

        Args:
            all_agents: Dictionary mapping agent_id to agent config/object.

        Returns:
            Filtered dictionary containing only active agents.
        """
        if self.agent_mode == "single" and self.selected_single_agent:
            if self.selected_single_agent in all_agents:
                return {self.selected_single_agent: all_agents[self.selected_single_agent]}
        return all_agents

    def get_effective_agent_ids(self, all_agent_ids: List[str]) -> List[str]:
        """Return active agent IDs based on mode.

        Args:
            all_agent_ids: List of all agent IDs from config.

        Returns:
            List containing only active agent IDs.
        """
        if self.agent_mode == "single" and self.selected_single_agent:
            if self.selected_single_agent in all_agent_ids:
                return [self.selected_single_agent]
        return all_agent_ids

    def reset_plan_state(self) -> None:
        """Reset plan-related state after plan completion or cancellation."""
        self.plan_mode = "normal"
        self.plan_session = None
        self.pending_plan_approval = False
        self.last_planning_question = None
        self.planning_started_turn = None
        self.selected_plan_id = None
        self.planning_context_paths = None

    def reset_plan_state_with_error(self, error_msg: str) -> str:
        """Reset plan state due to an error.

        Logs the error and resets to normal mode.

        Args:
            error_msg: Description of what went wrong.

        Returns:
            The error message (for chaining with notifications).
        """
        import logging

        logger = logging.getLogger("massgen.tui.modes")
        logger.error(f"[TuiModeState] Plan error - resetting state: {error_msg}")
        self.reset_plan_state()
        return error_msg

    def reset_override_state(self) -> None:
        """Reset override-related state after override completion or cancellation."""
        self.override_pending = False
        self.override_selected_agent = None
        self.override_available = False

    def reset_cancelled_state(self) -> None:
        """Reset cancelled state when user starts a new turn."""
        self.was_cancelled = False

    def is_plan_active(self) -> bool:
        """Check if plan mode is active (not normal)."""
        return self.plan_mode != "normal"

    def is_single_agent_mode(self) -> bool:
        """Check if single-agent mode is active."""
        return self.agent_mode == "single"

    def get_mode_summary(self) -> str:
        """Return a human-readable summary of current mode state."""
        parts = []

        # Plan mode
        if self.plan_mode == "plan":
            parts.append("Plan: Creating")
        elif self.plan_mode == "execute":
            parts.append("Plan: Executing")

        # Agent mode
        if self.agent_mode == "single":
            agent_name = self.selected_single_agent or "None"
            parts.append(f"Agent: {agent_name}")
        else:
            parts.append("Agents: Multi")

        # Refinement mode
        if not self.refinement_enabled:
            parts.append("Refine: OFF")

        if not parts:
            return "Normal mode"

        return " | ".join(parts)
