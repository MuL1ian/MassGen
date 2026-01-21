# -*- coding: utf-8 -*-
"""System message builder for MassGen orchestration.

This module provides the SystemMessageBuilder class which centralizes all system
message construction logic for different orchestration phases (coordination,
presentation, and post-evaluation).

This was extracted from orchestrator.py to improve separation of concerns and
reduce coupling between orchestration logic and prompt construction.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from massgen.system_prompt_sections import (
    AgentIdentitySection,
    BroadcastCommunicationSection,
    CodeBasedToolsSection,
    CommandExecutionSection,
    CoreBehaviorsSection,
    EvaluationSection,
    EvolvingSkillsSection,
    FileSearchSection,
    FilesystemBestPracticesSection,
    FilesystemOperationsSection,
    GPT5GuidanceSection,
    GrokGuidanceSection,
    MemorySection,
    MultimodalToolsSection,
    OutputFirstVerificationSection,
    PlanningModeSection,
    PostEvaluationSection,
    ProjectInstructionsSection,
    SkillsSection,
    SubagentSection,
    SystemPromptBuilder,
    TaskContextSection,
    TaskPlanningSection,
    WorkspaceStructureSection,
)


class SystemMessageBuilder:
    """Builds system messages for different orchestration phases.

    This class centralizes all system message construction logic and consolidates
    duplicated code across the three main phases:
    - Coordination: Complex multi-agent collaboration with skills, memory, evaluation
    - Presentation: Final answer presentation with media generation capabilities
    - Post-evaluation: Answer verification and quality checking

    Args:
        config: Orchestrator configuration
        message_templates: MessageTemplates instance for presentation logic
        agents: Dictionary of agent_id -> ChatAgent for memory scanning
    """

    def __init__(
        self,
        config,  # CoordinationConfig type
        message_templates,  # MessageTemplates type
        agents: Dict[str, Any],  # Dict[str, ChatAgent]
        snapshot_storage: Optional[str] = None,
        session_id: Optional[str] = None,
        agent_temporary_workspace: Optional[str] = None,
    ):
        """Initialize the system message builder.

        Args:
            config: Orchestrator coordination configuration
            message_templates: MessageTemplates instance
            agents: Dictionary of agents for memory scanning
            snapshot_storage: Path to snapshot storage directory (for archived memories)
            session_id: Session ID (for archived memories)
            agent_temporary_workspace: Path to temp workspace directory (for current agent memories)
        """
        self.config = config
        self.message_templates = message_templates
        self.agents = agents
        self.snapshot_storage = snapshot_storage
        self.session_id = session_id
        self.agent_temporary_workspace = agent_temporary_workspace

    def build_coordination_message(
        self,
        agent,  # ChatAgent
        agent_id: str,
        answers: Optional[Dict[str, str]],
        planning_mode_enabled: bool,
        use_skills: bool,
        enable_memory: bool,
        enable_task_planning: bool,
        previous_turns: List[Dict[str, Any]],
        human_qa_history: Optional[List[Dict[str, str]]] = None,
        vote_only: bool = False,
        agent_mapping: Optional[Dict[str, str]] = None,
    ) -> str:
        """Build system message for coordination phase.

        This method assembles the system prompt using priority-based sections with
        XML structure, ensuring critical instructions (skills, memory) appear early.

        Args:
            agent: The agent instance
            agent_id: Agent identifier
            answers: Dict of current answers from agents
            planning_mode_enabled: Whether planning mode is active
            use_skills: Whether to include skills section
            enable_memory: Whether to include memory section
            enable_task_planning: Whether to include task planning guidance
            previous_turns: List of previous turn data for filesystem context
            human_qa_history: List of human Q&A pairs from broadcast channel (human mode only)
            vote_only: If True, agent has reached max answers and can only vote
            agent_mapping: Mapping from real agent ID to anonymous ID (e.g., agent_a -> agent1).
                          Pass from coordination_tracker.get_reverse_agent_mapping() for
                          global consistency with vote tool and injections.

        Returns:
            Complete system prompt string with XML structure
        """
        builder = SystemPromptBuilder()

        # PRIORITY 1 (CRITICAL): Agent Identity - WHO they are
        agent_system_message = agent.get_configurable_system_message()
        # Use empty string if None to avoid showing "None" in prompt
        if agent_system_message is None:
            agent_system_message = ""
        builder.add_section(AgentIdentitySection(agent_system_message))

        # PRIORITY 1 (CRITICAL): Core Behaviors - HOW to act
        builder.add_section(CoreBehaviorsSection())

        # PRIORITY 4: File Persistence Guidance (solution persistence + tool preambles)
        # Added for models that tend to output file contents in answers instead of using file tools
        # GPT-5.x: Based on OpenAI's prompting guides
        # Grok: Observed behavior of embedding HTML in answers instead of writing to files
        model_name = agent.backend.config.get("model", "").lower()
        if model_name.startswith("gpt-5") or model_name.startswith("grok"):
            builder.add_section(GPT5GuidanceSection())
            logger.info(f"[SystemMessageBuilder] Added GPT-5 guidance section for {agent_id} (model: {model_name})")
        # Grok-specific: Prevent HTML-escaping of file content (known Grok 4.1 issue with SVG/XML/HTML)
        if model_name.startswith("grok"):
            builder.add_section(GrokGuidanceSection())
            logger.info(f"[SystemMessageBuilder] Added Grok file encoding guidance for {agent_id} (model: {model_name})")

        # PRIORITY 1 (HIGH): Output-First Verification - verify outcomes, not implementations
        builder.add_section(OutputFirstVerificationSection())

        # PRIORITY 1 (CRITICAL): MassGen Coordination - vote/new_answer primitives
        voting_sensitivity = self.message_templates._voting_sensitivity
        answer_novelty_requirement = self.message_templates._answer_novelty_requirement
        builder.add_section(
            EvaluationSection(
                voting_sensitivity=voting_sensitivity,
                answer_novelty_requirement=answer_novelty_requirement,
                vote_only=vote_only,
            ),
        )

        # PRIORITY 5 (HIGH): Skills - Must be visible early
        if use_skills:
            from massgen.filesystem_manager.skills_manager import scan_skills

            # Scan all available skills
            skills_dir = Path(self.config.coordination_config.skills_directory)

            # Check if we should load previous session skills
            logs_dir = None
            load_prev = getattr(self.config.coordination_config, "load_previous_session_skills", False)
            logger.info(f"[SystemMessageBuilder] load_previous_session_skills = {load_prev}")
            if load_prev:
                logs_dir = Path(".massgen/massgen_logs")
                logger.info(f"[SystemMessageBuilder] Will scan logs_dir: {logs_dir}")

            all_skills = scan_skills(skills_dir, logs_dir=logs_dir)

            # Log what we found
            builtin_count = len([s for s in all_skills if s["location"] == "builtin"])
            project_count = len([s for s in all_skills if s["location"] == "project"])
            previous_count = len([s for s in all_skills if s["location"] == "previous_session"])
            logger.info(
                f"[SystemMessageBuilder] Scanned skills: {builtin_count} builtin, " f"{project_count} project, {previous_count} previous_session",
            )

            # Log details for each skill
            for skill in all_skills:
                name = skill.get("name", "unknown")
                location = skill.get("location", "unknown")
                source_path = skill.get("source_path", "")
                if source_path:
                    logger.info(f"[SystemMessageBuilder] Skill: {name} ({location}) - {source_path}")
                else:
                    logger.info(f"[SystemMessageBuilder] Skill: {name} ({location})")

            # Add skills section with all skills (both project and builtin)
            # Builtin skills are now treated the same as project skills - invoke with openskills read
            builder.add_section(SkillsSection(all_skills))

        # PRIORITY 5 (HIGH): Memory - Proactive usage
        if enable_memory:
            short_term_memories, long_term_memories = self._get_all_memories()
            temp_workspace_memories = self._load_temp_workspace_memories()
            archived_memories = self._load_archived_memories()

            # Always add memory section to show usage instructions, even if empty
            memory_config = {
                "short_term": {
                    "content": "\n".join([f"- {m}" for m in short_term_memories]) if short_term_memories else "",
                },
                "long_term": [{"id": f"mem_{i}", "summary": mem, "created_at": "N/A"} for i, mem in enumerate(long_term_memories)] if long_term_memories else [],
                "temp_workspace_memories": temp_workspace_memories,
                "archived_memories": archived_memories,
            }
            builder.add_section(MemorySection(memory_config))
            archived_count = len(archived_memories.get("short_term", {})) + len(archived_memories.get("long_term", {}))
            logger.info(
                f"[SystemMessageBuilder] Added memory section "
                f"({len(short_term_memories)} short-term, {len(long_term_memories)} long-term, "
                f"{len(temp_workspace_memories)} temp workspace, {archived_count} archived)",
            )

        # PRIORITY 5 (HIGH): Filesystem - Essential context
        if agent.backend.filesystem_manager:
            main_workspace = str(agent.backend.filesystem_manager.get_current_workspace())
            context_paths = agent.backend.filesystem_manager.path_permission_manager.get_context_paths() if agent.backend.filesystem_manager.path_permission_manager else []

            # Check if two-tier workspace is enabled
            use_two_tier_workspace = False
            if hasattr(agent.backend, "filesystem_manager") and agent.backend.filesystem_manager:
                use_two_tier_workspace = getattr(agent.backend.filesystem_manager, "use_two_tier_workspace", False)

            # Add project instructions section (CLAUDE.md / AGENTS.md discovery)
            # This comes BEFORE workspace structure so project context is established first
            if context_paths:
                logger.info(f"[SystemMessageBuilder] Checking for project instructions in {len(context_paths)} context paths")
                builder.add_section(ProjectInstructionsSection(context_paths, workspace_root=main_workspace))

            # Add workspace structure section (critical paths)
            builder.add_section(WorkspaceStructureSection(main_workspace, [p.get("path", "") for p in context_paths], use_two_tier_workspace=use_two_tier_workspace))

            # Check command execution settings
            enable_command_execution = False
            docker_mode = False
            enable_sudo = False
            concurrent_tool_execution = False
            if hasattr(agent, "config") and agent.config:
                enable_command_execution = agent.config.backend_params.get("enable_mcp_command_line", False)
                docker_mode = agent.config.backend_params.get("command_line_execution_mode", "local") == "docker"
                enable_sudo = agent.config.backend_params.get("command_line_docker_enable_sudo", False)
                concurrent_tool_execution = agent.config.backend_params.get("concurrent_tool_execution", False)
            elif hasattr(agent, "backend") and hasattr(agent.backend, "backend_params"):
                enable_command_execution = agent.backend.backend_params.get("enable_mcp_command_line", False)
                docker_mode = agent.backend.backend_params.get("command_line_execution_mode", "local") == "docker"
                enable_sudo = agent.backend.backend_params.get("command_line_docker_enable_sudo", False)
                concurrent_tool_execution = agent.backend.backend_params.get("concurrent_tool_execution", False)

            # Build and add filesystem sections using consolidated helper
            fs_ops, fs_best, cmd_exec = self._build_filesystem_sections(
                agent=agent,
                all_answers=answers,
                previous_turns=previous_turns,
                enable_command_execution=enable_command_execution,
                docker_mode=docker_mode,
                enable_sudo=enable_sudo,
                concurrent_tool_execution=concurrent_tool_execution,
                agent_mapping=agent_mapping,
            )

            builder.add_section(fs_ops)
            builder.add_section(fs_best)
            if cmd_exec:
                builder.add_section(cmd_exec)

            # Add lightweight file search guidance if command execution is available
            # (rg and sg are pre-installed in Docker and commonly available in local mode)
            builder.add_section(FileSearchSection())

            # Add multimodal tools section if enabled
            enable_multimodal = agent.backend.config.get("enable_multimodal_tools", False)
            if enable_multimodal:
                builder.add_section(MultimodalToolsSection())
                logger.info(f"[SystemMessageBuilder] Added multimodal tools section for {agent_id}")

            # Add code-based tools section if enabled (CodeAct paradigm)
            if agent.backend.filesystem_manager.enable_code_based_tools:
                workspace_path = str(agent.backend.filesystem_manager.get_current_workspace())
                shared_tools_path = None
                if agent.backend.filesystem_manager.shared_tools_directory:
                    shared_tools_path = str(agent.backend.filesystem_manager.shared_tools_directory)

                # Get MCP servers from backend for description lookup
                mcp_servers = getattr(agent.backend, "mcp_servers", []) or []

                builder.add_section(CodeBasedToolsSection(workspace_path, shared_tools_path, mcp_servers))
                logger.info(f"[SystemMessageBuilder] Added code-based tools section for {agent_id}")

        # PRIORITY 10 (MEDIUM): Subagent Delegation (conditional)
        enable_subagents = False
        if hasattr(self.config, "coordination_config") and hasattr(self.config.coordination_config, "enable_subagents"):
            enable_subagents = self.config.coordination_config.enable_subagents
            if enable_subagents:
                # Get workspace path for subagent section
                workspace_path = ""
                if agent.backend.filesystem_manager:
                    workspace_path = str(agent.backend.filesystem_manager.get_current_workspace())
                # Get max concurrent from config, default to 3
                max_concurrent = getattr(self.config.coordination_config, "subagent_max_concurrent", 3)
                builder.add_section(SubagentSection(workspace_path, max_concurrent))
                logger.info(f"[SystemMessageBuilder] Added subagent section for {agent_id} (max_concurrent: {max_concurrent})")

        # PRIORITY 10 (MEDIUM): Task Context (when multimodal tools OR subagents are enabled)
        # This instructs agents to create CONTEXT.md before using tools that make external API calls
        enable_multimodal = agent.backend.config.get("enable_multimodal_tools", False) if agent.backend else False
        if enable_multimodal or enable_subagents:
            builder.add_section(TaskContextSection())
            logger.info(f"[SystemMessageBuilder] Added task context section for {agent_id} (multimodal: {enable_multimodal}, subagents: {enable_subagents})")

        # PRIORITY 10 (MEDIUM): Task Planning
        if enable_task_planning:
            filesystem_mode = (
                hasattr(self.config.coordination_config, "task_planning_filesystem_mode")
                and self.config.coordination_config.task_planning_filesystem_mode
                and hasattr(agent, "backend")
                and hasattr(agent.backend, "filesystem_manager")
                and agent.backend.filesystem_manager
                and agent.backend.filesystem_manager.cwd
            )
            builder.add_section(TaskPlanningSection(filesystem_mode=filesystem_mode))

        # PRIORITY 10 (MEDIUM): Evolving Skills (when auto-discovery is enabled)
        auto_discover_enabled = False
        if hasattr(agent, "backend") and hasattr(agent.backend, "config"):
            auto_discover_enabled = agent.backend.config.get("auto_discover_custom_tools", False)
        if auto_discover_enabled:
            # Check for plan.json to provide plan-aware guidance
            plan_context = None
            if hasattr(agent, "backend") and hasattr(agent.backend, "filesystem_manager") and agent.backend.filesystem_manager:
                workspace_path = Path(agent.backend.filesystem_manager.get_current_workspace())
                plan_file = workspace_path / "tasks" / "plan.json"
                if plan_file.exists():
                    try:
                        import json

                        plan_context = json.loads(plan_file.read_text())
                        logger.info(f"[SystemMessageBuilder] Found plan.json with {len(plan_context.get('tasks', []))} tasks for evolving skills")
                    except Exception as e:
                        logger.warning(f"[SystemMessageBuilder] Failed to read plan.json: {e}")

            builder.add_section(EvolvingSkillsSection(plan_context=plan_context))
            logger.info(f"[SystemMessageBuilder] Added evolving skills section for {agent_id}")

        # PRIORITY 10 (MEDIUM): Broadcast Communication (conditional)
        if hasattr(self.config, "coordination_config") and hasattr(self.config.coordination_config, "broadcast"):
            broadcast_mode = self.config.coordination_config.broadcast
            if broadcast_mode and broadcast_mode is not False:
                builder.add_section(
                    BroadcastCommunicationSection(
                        broadcast_mode=broadcast_mode,
                        wait_by_default=getattr(self.config.coordination_config, "broadcast_wait_by_default", True),
                        sensitivity=getattr(self.config.coordination_config, "broadcast_sensitivity", "medium"),
                        human_qa_history=human_qa_history,
                    ),
                )
                sensitivity = getattr(self.config.coordination_config, "broadcast_sensitivity", "medium")
                qa_count = len(human_qa_history) if human_qa_history else 0
                logger.info(f"[SystemMessageBuilder] Added broadcast section (mode: {broadcast_mode}, sensitivity: {sensitivity}, human_qa: {qa_count})")

        # PRIORITY 10 (MEDIUM): Planning Mode (conditional)
        if planning_mode_enabled and self.config and hasattr(self.config, "coordination_config") and self.config.coordination_config and self.config.coordination_config.planning_mode_instruction:
            builder.add_section(PlanningModeSection(self.config.coordination_config.planning_mode_instruction))
            logger.info(f"[SystemMessageBuilder] Added planning mode instructions for {agent_id}")

        # Build and return the complete structured system prompt
        return builder.build()

    def build_presentation_message(
        self,
        agent,  # ChatAgent
        all_answers: Dict[str, str],
        previous_turns: List[Dict[str, Any]],
        enable_image_generation: bool = False,
        enable_audio_generation: bool = False,
        enable_file_generation: bool = False,
        enable_video_generation: bool = False,
        has_irreversible_actions: bool = False,
        enable_command_execution: bool = False,
        docker_mode: bool = False,
        enable_sudo: bool = False,
        concurrent_tool_execution: bool = False,
        agent_mapping: Optional[Dict[str, str]] = None,
    ) -> str:
        """Build system message for final presentation phase.

        This combines the agent's identity, presentation instructions, and filesystem
        operations using the structured section approach.

        Args:
            agent: The presenting agent
            all_answers: All answers from coordination phase
            previous_turns: List of previous turn data for filesystem context
            enable_image_generation: Whether image generation is enabled
            enable_audio_generation: Whether audio generation is enabled
            enable_file_generation: Whether file generation is enabled
            enable_video_generation: Whether video generation is enabled
            has_irreversible_actions: Whether agent has write access
            enable_command_execution: Whether command execution is enabled
            docker_mode: Whether commands run in Docker
            enable_sudo: Whether sudo is available
            concurrent_tool_execution: Whether tools execute in parallel
            agent_mapping: Mapping from real agent ID to anonymous ID (e.g., agent_a -> agent1).
                          Pass from coordination_tracker.get_reverse_agent_mapping() for
                          global consistency with vote tool and injections.

        Returns:
            Complete system message string
        """
        # Get agent's configurable system message
        agent_system_message = agent.get_configurable_system_message()
        if agent_system_message is None:
            agent_system_message = ""

        # Get presentation instructions from message_templates
        # (This contains special logic for image/audio/file/video generation)
        presentation_instructions = self.message_templates.final_presentation_system_message(
            original_system_message=agent_system_message,
            enable_image_generation=enable_image_generation,
            enable_audio_generation=enable_audio_generation,
            enable_file_generation=enable_file_generation,
            enable_video_generation=enable_video_generation,
            has_irreversible_actions=has_irreversible_actions,
            enable_command_execution=enable_command_execution,
        )

        # If filesystem is available, prepend filesystem sections
        if agent.backend.filesystem_manager:
            # Build filesystem sections using consolidated helper
            fs_ops, fs_best, cmd_exec = self._build_filesystem_sections(
                agent=agent,
                all_answers=all_answers,
                previous_turns=previous_turns,
                enable_command_execution=enable_command_execution,
                docker_mode=docker_mode,
                enable_sudo=enable_sudo,
                concurrent_tool_execution=concurrent_tool_execution,
                agent_mapping=agent_mapping,
            )

            # Build sections list
            sections_content = [fs_ops.build_content(), fs_best.build_content()]
            if cmd_exec:
                sections_content.append(cmd_exec.build_content())

            # Add code-based tools section if enabled (CodeAct paradigm)
            if agent.backend.filesystem_manager.enable_code_based_tools:
                workspace_path = str(agent.backend.filesystem_manager.get_current_workspace())
                shared_tools_path = None
                if agent.backend.filesystem_manager.shared_tools_directory:
                    shared_tools_path = str(agent.backend.filesystem_manager.shared_tools_directory)

                # Get MCP servers from backend for description lookup
                mcp_servers = getattr(agent.backend, "mcp_servers", []) or []

                code_based_tools_section = CodeBasedToolsSection(workspace_path, shared_tools_path, mcp_servers)
                sections_content.append(code_based_tools_section.build_content())
                logger.info("[SystemMessageBuilder] Added code-based tools section for presentation")

            # Add evolving skill consolidation instructions if auto-discovery enabled
            auto_discover_enabled = False
            if hasattr(agent, "backend") and hasattr(agent.backend, "config"):
                auto_discover_enabled = agent.backend.config.get("auto_discover_custom_tools", False)
            if auto_discover_enabled:
                evolving_skill_instructions = """## Evolving Skill Output

**REQUIRED**: Write a consolidated evolving skill to the final workspace.

Each agent has created their own evolving skill at `tasks/evolving_skill/SKILL.md` in their workspace.
Review these and consolidate into a single `SKILL.md` in the output directory:

- **name**: Descriptive name for this workflow
- **description**: What it does and when to reuse it
- **## Overview**: Problem solved
- **## Workflow**: The actual steps that worked (combined from all agents)
- **## Tools to Create**: Scripts written (with purpose, inputs, outputs)
- **## Tools to Use**: servers/ and custom_tools/ that were helpful
- **## Skills**: Other skills that were used
- **## Packages**: Dependencies installed
- **## Expected Outputs**: What this workflow produces
- **## Learnings**: What worked well, what didn't, tips for future use

This makes the work reusable for similar future tasks."""
                sections_content.append(evolving_skill_instructions)
                logger.info("[SystemMessageBuilder] Added evolving skill output instructions for presentation")

            # Combine: filesystem sections + presentation instructions
            filesystem_content = "\n\n".join(sections_content)
            return f"{filesystem_content}\n\n## Instructions\n{presentation_instructions}"
        else:
            # No filesystem - just return presentation instructions
            return presentation_instructions

    def build_post_evaluation_message(
        self,
        agent,  # ChatAgent
        all_answers: Dict[str, str],
        previous_turns: List[Dict[str, Any]],
        agent_mapping: Optional[Dict[str, str]] = None,
    ) -> str:
        """Build system message for post-evaluation phase.

        This combines the agent's identity, post-evaluation instructions, and filesystem
        operations using the structured section approach.

        Args:
            agent: The evaluating agent
            all_answers: All answers from coordination phase
            previous_turns: List of previous turn data for filesystem context
            agent_mapping: Mapping from real agent ID to anonymous ID (e.g., agent_a -> agent1).
                          Pass from coordination_tracker.get_reverse_agent_mapping() for
                          global consistency with vote tool and injections.

        Returns:
            Complete system message string
        """
        # Get agent's configurable system message
        agent_system_message = agent.get_configurable_system_message()
        if agent_system_message is None:
            agent_system_message = ""

        # Start with agent identity if provided
        parts = []
        if agent_system_message:
            parts.append(agent_system_message)

        # If filesystem is available, add filesystem sections
        if agent.backend.filesystem_manager:
            # Build filesystem sections using consolidated helper
            # (No command execution in post-evaluation)
            fs_ops, fs_best, _ = self._build_filesystem_sections(
                agent=agent,
                all_answers=all_answers,
                previous_turns=previous_turns,
                enable_command_execution=False,
                docker_mode=False,
                enable_sudo=False,
                agent_mapping=agent_mapping,
            )

            parts.append(fs_ops.build_content())
            parts.append(fs_best.build_content())

            # Add code-based tools section if enabled (CodeAct paradigm)
            if agent.backend.filesystem_manager.enable_code_based_tools:
                workspace_path = str(agent.backend.filesystem_manager.get_current_workspace())
                shared_tools_path = None
                if agent.backend.filesystem_manager.shared_tools_directory:
                    shared_tools_path = str(agent.backend.filesystem_manager.shared_tools_directory)

                # Get MCP servers from backend for description lookup
                mcp_servers = getattr(agent.backend, "mcp_servers", []) or []

                code_based_tools_section = CodeBasedToolsSection(workspace_path, shared_tools_path, mcp_servers)
                parts.append(code_based_tools_section.build_content())
                logger.info("[SystemMessageBuilder] Added code-based tools section for post-evaluation")

        # Add post-evaluation instructions
        post_eval = PostEvaluationSection()
        parts.append(post_eval.build_content())

        return "\n\n".join(parts)

    def _build_filesystem_sections(
        self,
        agent,  # ChatAgent
        all_answers: Dict[str, str],
        previous_turns: List[Dict[str, Any]],
        enable_command_execution: bool,
        docker_mode: bool = False,
        enable_sudo: bool = False,
        concurrent_tool_execution: bool = False,
        agent_mapping: Optional[Dict[str, str]] = None,
    ) -> Tuple[Any, Any, Optional[Any]]:  # Tuple[FilesystemOperationsSection, FilesystemBestPracticesSection, Optional[CommandExecutionSection]]
        """Build filesystem-related sections.

        This consolidates the duplicated logic across all three builder methods
        for creating filesystem operations, best practices, and command execution sections.

        Args:
            agent: The agent instance
            all_answers: Dict of current answers from agents
            previous_turns: List of previous turn data for filesystem context
            enable_command_execution: Whether to include command execution section
            docker_mode: Whether commands run in Docker
            enable_sudo: Whether sudo is available
            concurrent_tool_execution: Whether tools execute in parallel
            agent_mapping: Mapping from real agent ID to anonymous ID (e.g., agent_a -> agent1).
                          Pass from coordination_tracker.get_reverse_agent_mapping() for
                          global consistency with vote tool and injections.

        Returns:
            Tuple of (FilesystemOperationsSection, FilesystemBestPracticesSection, Optional[CommandExecutionSection])
        """
        # Extract filesystem paths from agent
        main_workspace = str(agent.backend.filesystem_manager.get_current_workspace())
        temp_workspace = str(agent.backend.filesystem_manager.agent_temporary_workspace) if agent.backend.filesystem_manager.agent_temporary_workspace else None
        context_paths = agent.backend.filesystem_manager.path_permission_manager.get_context_paths() if agent.backend.filesystem_manager.path_permission_manager else []

        # Calculate previous turns context
        current_turn_num = len(previous_turns) + 1 if previous_turns else 1
        turns_to_show = [t for t in previous_turns if t["turn"] < current_turn_num - 1]
        workspace_prepopulated = len(previous_turns) > 0

        # Get code-based tools flag from agent
        enable_code_based_tools = agent.backend.filesystem_manager.enable_code_based_tools

        # Build filesystem operations section
        fs_ops = FilesystemOperationsSection(
            main_workspace=main_workspace,
            temp_workspace=temp_workspace,
            context_paths=context_paths,
            previous_turns=turns_to_show,
            workspace_prepopulated=workspace_prepopulated,
            agent_answers=all_answers,
            enable_command_execution=enable_command_execution,
            agent_mapping=agent_mapping,
        )

        # Build filesystem best practices section
        fs_best = FilesystemBestPracticesSection(enable_code_based_tools=enable_code_based_tools)

        # Build command execution section if enabled
        cmd_exec = None
        if enable_command_execution:
            cmd_exec = CommandExecutionSection(
                docker_mode=docker_mode,
                enable_sudo=enable_sudo,
                concurrent_tool_execution=concurrent_tool_execution,
            )

        return fs_ops, fs_best, cmd_exec

    def _get_all_memories(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Read all memories from all agents' workspaces.

        Returns:
            Tuple of (short_term_memories, long_term_memories)
            Each is a list of memory dictionaries with keys:
            - name, description, content, tier, agent_id, created, updated
        """
        short_term_memories = []
        long_term_memories = []

        # Scan all agents' workspaces
        for agent_id, agent in self.agents.items():
            if not (hasattr(agent, "backend") and hasattr(agent.backend, "filesystem_manager") and agent.backend.filesystem_manager):
                continue

            workspace = agent.backend.filesystem_manager.cwd
            if not workspace:
                continue

            memory_dir = Path(workspace) / "memory"
            if not memory_dir.exists():
                continue

            # Read short-term memories
            short_term_dir = memory_dir / "short_term"
            if short_term_dir.exists():
                for mem_file in short_term_dir.glob("*.md"):
                    try:
                        memory_data = self._parse_memory_file(mem_file)
                        if memory_data:
                            short_term_memories.append(memory_data)
                    except Exception as e:
                        logger.warning(f"[SystemMessageBuilder] Failed to parse memory file {mem_file}: {e}")

            # Read long-term memories
            long_term_dir = memory_dir / "long_term"
            if long_term_dir.exists():
                for mem_file in long_term_dir.glob("*.md"):
                    try:
                        memory_data = self._parse_memory_file(mem_file)
                        if memory_data:
                            long_term_memories.append(memory_data)
                    except Exception as e:
                        logger.warning(f"[SystemMessageBuilder] Failed to parse memory file {mem_file}: {e}")

        return short_term_memories, long_term_memories

    def _load_archived_memories(self) -> Dict[str, Dict[str, Any]]:
        """Load all archived memories from sessions directory with deduplication.

        Deduplicate by filename - for memories with the same name across multiple archives,
        only keep the most recent version by file modification timestamp.

        Returns:
            Dictionary mapping tier ("short_term", "long_term") to memory dictionaries:
            - Each memory dict maps filename to {"content": str, "source": str, "timestamp": float}
        """
        if not self.session_id:
            return {"short_term": {}, "long_term": {}}

        # Load from sessions/ directory (persistent), not snapshots/ (gets cleared)
        archive_base = Path(".massgen/sessions") / self.session_id / "archived_memories"
        if not archive_base.exists():
            return {"short_term": {}, "long_term": {}}

        # Track all memories by filename with metadata for deduplication
        # Format: {tier: {filename: [{"content": str, "source": str, "timestamp": float, "path": Path}, ...]}}
        all_memories: Dict[str, Dict[str, list]] = {"short_term": {}, "long_term": {}}

        # Scan all archived answer directories
        for archive_dir in sorted(archive_base.iterdir()):
            if not archive_dir.is_dir():
                continue

            # Parse source label from directory name
            dir_name = archive_dir.name
            source_label = dir_name.replace("_", " ").title()  # "Agent A Answer 0"

            # Process both tiers
            for tier in ["short_term", "long_term"]:
                tier_dir = archive_dir / tier
                if not tier_dir.exists():
                    continue

                for mem_file in tier_dir.glob("*.md"):
                    try:
                        filename = mem_file.stem
                        content = mem_file.read_text()
                        timestamp = mem_file.stat().st_mtime

                        # Initialize list for this filename if needed
                        if filename not in all_memories[tier]:
                            all_memories[tier][filename] = []

                        # Add this version
                        all_memories[tier][filename].append(
                            {
                                "content": content,
                                "source": source_label,
                                "timestamp": timestamp,
                                "path": mem_file,
                            },
                        )
                    except Exception as e:
                        logger.warning(f"[SystemMessageBuilder] Failed to read archived memory {mem_file}: {e}")

        # Deduplicate: for each filename, keep only the most recent version
        deduplicated = {"short_term": {}, "long_term": {}}
        for tier in ["short_term", "long_term"]:
            for filename, versions in all_memories[tier].items():
                # Sort by timestamp descending and take the most recent
                latest = max(versions, key=lambda v: v["timestamp"])
                deduplicated[tier][filename] = {
                    "content": latest["content"],
                    "source": latest["source"],
                    "timestamp": latest["timestamp"],
                }

        return deduplicated

    def _load_temp_workspace_memories(self) -> List[Dict[str, Any]]:
        """Load all memories from temp workspace directories.

        Returns:
            List of temp workspace memory dictionaries with keys:
            - agent_label: Anonymous agent label (e.g., "agent1", "agent2")
            - memories: Dict with short_term and long_term subdicts
                Each subdict maps memory filename to full memory data (including metadata)
        """
        if not self.agent_temporary_workspace:
            return []

        temp_workspace_base = Path(self.agent_temporary_workspace)
        if not temp_workspace_base.exists():
            return []

        temp_memories = []

        # Scan all agent directories in temp workspace
        for agent_dir in sorted(temp_workspace_base.iterdir()):
            if not agent_dir.is_dir():
                continue

            agent_label = agent_dir.name  # e.g., "agent1", "agent2"
            memory_dir = agent_dir / "memory"

            if not memory_dir.exists():
                continue

            memories = {"short_term": {}, "long_term": {}}

            # Load short_term memories
            short_term_dir = memory_dir / "short_term"
            if short_term_dir.exists():
                for mem_file in short_term_dir.glob("*.md"):
                    try:
                        memory_data = self._parse_memory_file(mem_file)
                        if memory_data:
                            memories["short_term"][mem_file.stem] = memory_data
                        else:
                            # Fallback to raw content if parsing fails
                            memories["short_term"][mem_file.stem] = {
                                "name": mem_file.stem,
                                "content": mem_file.read_text(),
                            }
                    except Exception as e:
                        logger.warning(f"[SystemMessageBuilder] Failed to read temp workspace memory {mem_file}: {e}")

            # Load long_term memories
            long_term_dir = memory_dir / "long_term"
            if long_term_dir.exists():
                for mem_file in long_term_dir.glob("*.md"):
                    try:
                        memory_data = self._parse_memory_file(mem_file)
                        if memory_data:
                            memories["long_term"][mem_file.stem] = memory_data
                        else:
                            # Fallback to raw content if parsing fails
                            memories["long_term"][mem_file.stem] = {
                                "name": mem_file.stem,
                                "content": mem_file.read_text(),
                            }
                    except Exception as e:
                        logger.warning(f"[SystemMessageBuilder] Failed to read temp workspace memory {mem_file}: {e}")

            # Only add if there are actual memories
            if memories["short_term"] or memories["long_term"]:
                temp_memories.append(
                    {
                        "agent_label": agent_label,
                        "memories": memories,
                    },
                )

        return temp_memories

    @staticmethod
    def _parse_memory_file(file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse a memory markdown file with YAML frontmatter.

        Args:
            file_path: Path to the memory file

        Returns:
            Dictionary with memory data or None if parsing fails
        """
        try:
            content = file_path.read_text()

            # Split frontmatter from content
            if not content.startswith("---"):
                return None

            parts = content.split("---", 2)
            if len(parts) < 3:
                return None

            frontmatter_text = parts[1].strip()
            memory_content = parts[2].strip()

            # Parse frontmatter (simple key: value parser)
            metadata = {}
            for line in frontmatter_text.split("\n"):
                line = line.strip()
                if ":" in line:
                    key, value = line.split(":", 1)
                    metadata[key.strip()] = value.strip()

            # Return combined memory data
            return {
                "name": metadata.get("name", ""),
                "description": metadata.get("description", ""),
                "content": memory_content,
                "tier": metadata.get("tier", ""),
                "agent_id": metadata.get("agent_id", ""),
                "created": metadata.get("created", ""),
                "updated": metadata.get("updated", ""),
            }
        except Exception:
            return None
