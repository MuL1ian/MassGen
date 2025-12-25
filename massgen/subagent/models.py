# -*- coding: utf-8 -*-
"""
Subagent Data Models for MassGen

Provides dataclasses for configuring, tracking, and returning results from subagents.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional


@dataclass
class SubagentConfig:
    """
    Configuration for spawning a subagent.

    Attributes:
        id: Unique subagent identifier (UUID if not provided)
        task: The task/prompt for the subagent to execute
        parent_agent_id: ID of the agent that spawned this subagent
        model: Optional model override (inherits from parent if None)
        timeout_seconds: Maximum execution time (default 300s / 5 min)
        context_files: List of file paths the subagent can READ (read-only access enforced)
        use_docker: Whether to use Docker container (inherits from parent settings)
        system_prompt: Optional custom system prompt for the subagent
        context: Optional project/goal context so subagent understands what it's working on
    """

    id: str
    task: str
    parent_agent_id: str
    model: Optional[str] = None
    timeout_seconds: int = 300
    context_files: List[str] = field(default_factory=list)
    use_docker: bool = True
    system_prompt: Optional[str] = None
    context: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        task: str,
        parent_agent_id: str,
        subagent_id: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: int = 300,
        context_files: Optional[List[str]] = None,
        use_docker: bool = True,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "SubagentConfig":
        """
        Factory method to create a SubagentConfig with auto-generated ID.

        Args:
            task: The task for the subagent
            parent_agent_id: ID of the parent agent
            subagent_id: Optional custom ID (generates UUID if not provided)
            model: Optional model override
            timeout_seconds: Execution timeout
            context_files: File paths subagent can read (read-only, no write access)
            use_docker: Whether to use Docker
            system_prompt: Optional custom system prompt
            context: Project/goal context so subagent understands what it's working on
            metadata: Additional metadata

        Returns:
            Configured SubagentConfig instance
        """
        return cls(
            id=subagent_id or f"sub_{uuid.uuid4().hex[:8]}",
            task=task,
            parent_agent_id=parent_agent_id,
            model=model,
            timeout_seconds=timeout_seconds,
            context_files=context_files or [],
            use_docker=use_docker,
            system_prompt=system_prompt,
            context=context,
            metadata=metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for serialization."""
        return {
            "id": self.id,
            "task": self.task,
            "parent_agent_id": self.parent_agent_id,
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
            "context_files": self.context_files.copy(),
            "use_docker": self.use_docker,
            "system_prompt": self.system_prompt,
            "context": self.context,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata.copy(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubagentConfig":
        """Create config from dictionary."""
        return cls(
            id=data["id"],
            task=data["task"],
            parent_agent_id=data["parent_agent_id"],
            model=data.get("model"),
            timeout_seconds=data.get("timeout_seconds", 300),
            context_files=data.get("context_files", []),
            use_docker=data.get("use_docker", True),
            system_prompt=data.get("system_prompt"),
            context=data.get("context"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SubagentOrchestratorConfig:
    """
    Configuration for subagent orchestrator mode.

    When enabled, subagents use a full Orchestrator with multiple agents.
    This enables multi-agent coordination within subagent execution.

    Attributes:
        enabled: Whether orchestrator mode is enabled (default False = single agent)
        agents: List of agent configurations for the subagent orchestrator.
                Each agent config can have: id (optional, auto-generated if missing),
                backend (with type, model, base_url, etc.)
                If empty/None, inherits from parent config.
        coordination: Optional coordination config subset (broadcast, planning, etc.)
    """

    enabled: bool = False
    agents: List[Dict[str, Any]] = field(default_factory=list)
    coordination: Dict[str, Any] = field(default_factory=dict)

    @property
    def num_agents(self) -> int:
        """Number of agents configured (defaults to 1 if no agents specified)."""
        return len(self.agents) if self.agents else 1

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.agents and len(self.agents) > 10:
            raise ValueError("Cannot have more than 10 agents for subagents")

    def get_agent_config(self, agent_index: int, subagent_id: str) -> Dict[str, Any]:
        """
        Get the config for a specific agent index.

        Args:
            agent_index: 0-based index of the agent
            subagent_id: ID of the parent subagent (for auto-generating agent IDs)

        Returns:
            Agent config dict with id and backend, or empty dict if not specified
        """
        if self.agents and agent_index < len(self.agents):
            config = self.agents[agent_index].copy()
            # Auto-generate ID if not provided
            if "id" not in config:
                config["id"] = f"{subagent_id}_agent_{agent_index + 1}"
            return config
        return {}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubagentOrchestratorConfig":
        """Create config from dictionary (YAML parsing)."""
        # Note: 'blocking' key is ignored (kept for backwards compatibility)
        return cls(
            enabled=data.get("enabled", False),
            agents=data.get("agents", []),
            coordination=data.get("coordination", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for serialization."""
        return {
            "enabled": self.enabled,
            "agents": [a.copy() for a in self.agents] if self.agents else [],
            "coordination": self.coordination.copy() if self.coordination else {},
        }


@dataclass
class SubagentResult:
    """
    Structured result returned from subagent execution.

    Attributes:
        subagent_id: ID of the subagent
        status: Final status (completed/timeout/error)
        success: Whether execution was successful
        answer: Final answer text from the subagent (includes relevant file paths)
        workspace_path: Path to the subagent's workspace
        execution_time_seconds: How long the subagent ran
        error: Error message if status is error/timeout
        token_usage: Token usage statistics (if available)
    """

    subagent_id: str
    status: Literal["completed", "timeout", "error"]
    success: bool
    answer: Optional[str] = None
    workspace_path: str = ""
    execution_time_seconds: float = 0.0
    error: Optional[str] = None
    token_usage: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for tool return value."""
        return {
            "subagent_id": self.subagent_id,
            "status": self.status,
            "success": self.success,
            "answer": self.answer,
            "workspace": self.workspace_path,
            "execution_time_seconds": self.execution_time_seconds,
            "error": self.error,
            "token_usage": self.token_usage.copy(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubagentResult":
        """Create result from dictionary."""
        return cls(
            subagent_id=data["subagent_id"],
            status=data["status"],
            success=data["success"],
            answer=data.get("answer"),
            workspace_path=data.get("workspace", ""),
            execution_time_seconds=data.get("execution_time_seconds", 0.0),
            error=data.get("error"),
            token_usage=data.get("token_usage", {}),
        )

    @classmethod
    def create_success(
        cls,
        subagent_id: str,
        answer: str,
        workspace_path: str,
        execution_time_seconds: float,
        token_usage: Optional[Dict[str, int]] = None,
    ) -> "SubagentResult":
        """Create a successful result."""
        return cls(
            subagent_id=subagent_id,
            status="completed",
            success=True,
            answer=answer,
            workspace_path=workspace_path,
            execution_time_seconds=execution_time_seconds,
            token_usage=token_usage or {},
        )

    @classmethod
    def create_timeout(
        cls,
        subagent_id: str,
        workspace_path: str,
        timeout_seconds: float,
    ) -> "SubagentResult":
        """Create a timeout result."""
        return cls(
            subagent_id=subagent_id,
            status="timeout",
            success=False,
            answer=None,
            workspace_path=workspace_path,
            execution_time_seconds=timeout_seconds,
            error=f"Subagent exceeded timeout of {timeout_seconds} seconds",
        )

    @classmethod
    def create_error(
        cls,
        subagent_id: str,
        error: str,
        workspace_path: str = "",
        execution_time_seconds: float = 0.0,
    ) -> "SubagentResult":
        """Create an error result."""
        return cls(
            subagent_id=subagent_id,
            status="error",
            success=False,
            answer=None,
            workspace_path=workspace_path,
            execution_time_seconds=execution_time_seconds,
            error=error,
        )


@dataclass
class SubagentPointer:
    """
    Pointer to a subagent for tracking in plan.json.

    Used to track subagents spawned during task execution and provide
    visibility into their workspaces and results.

    Attributes:
        id: Subagent identifier
        task: Task description given to the subagent
        workspace: Path to the subagent's workspace
        status: Current status (running/completed/failed/timeout)
        created_at: When the subagent was spawned
        completed_at: When the subagent finished (if applicable)
        result_summary: Brief summary of the result (if completed)
    """

    id: str
    task: str
    workspace: str
    status: Literal["running", "completed", "failed", "timeout"]
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    result_summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert pointer to dictionary for serialization."""
        return {
            "id": self.id,
            "task": self.task,
            "workspace": self.workspace,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result_summary": self.result_summary,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubagentPointer":
        """Create pointer from dictionary."""
        return cls(
            id=data["id"],
            task=data["task"],
            workspace=data["workspace"],
            status=data["status"],
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            result_summary=data.get("result_summary"),
        )

    def mark_completed(self, result: SubagentResult) -> None:
        """Update pointer when subagent completes."""
        self.status = "completed" if result.success else ("timeout" if result.status == "timeout" else "failed")
        self.completed_at = datetime.now()
        if result.answer:
            # Truncate summary to first 200 chars
            self.result_summary = result.answer[:200] + ("..." if len(result.answer) > 200 else "")


@dataclass
class SubagentState:
    """
    Runtime state of a subagent for tracking during execution.

    Used internally by SubagentManager to track active subagents.

    Attributes:
        config: The subagent configuration
        status: Current execution status
        workspace_path: Path to subagent workspace
        started_at: When execution started
        result: Final result (when completed)
    """

    config: SubagentConfig
    status: Literal["pending", "running", "completed", "failed", "timeout"] = "pending"
    workspace_path: str = ""
    started_at: Optional[datetime] = None
    result: Optional[SubagentResult] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "config": self.config.to_dict(),
            "status": self.status,
            "workspace_path": self.workspace_path,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "result": self.result.to_dict() if self.result else None,
        }
