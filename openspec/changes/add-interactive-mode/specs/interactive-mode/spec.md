## ADDED Requirements

### Requirement: Interactive Session Lifecycle
The system SHALL provide a persistent `InteractiveSession` class that manages conversations across multiple runs.

#### Scenario: Session initialization
- **WHEN** the TUI starts with `interactive_mode.enabled: true`
- **THEN** an `InteractiveSession` is created and becomes the primary entry point for user interactions

#### Scenario: Session persistence across runs
- **WHEN** a run completes and returns results
- **THEN** the `InteractiveSession` retains context and can reference previous run results in subsequent conversations

### Requirement: Launch Run Tool
The system SHALL provide a `launch_run` MCP tool (in a new `massgen/mcp_tools/interactive/` server) that allows the interactive agent to spawn MassGen runs with configurable agent modes, refinement settings, and planning options. This is an MCP tool rather than a workflow tool so it can be exposed to external backends (Claude Code, Codex, etc.).

#### Scenario: Tool schema definition
- **WHEN** the interactive agent is initialized
- **THEN** it SHALL have access to a `launch_run` tool with parameters:
  - `task` (required): Description of what to accomplish
  - `context` (optional): Background information, constraints, or previous decisions
  - `agent_mode` (optional): "single" | "multi" - whether to use one agent or multiple (default: "multi")
  - `agents` (optional): List of specific agent IDs to use (defaults to all configured agents)
  - `refinement` (optional): true | false - whether to enable voting/refinement cycles (default: true for multi, false for single)
  - `planning_mode` (optional): true | false - if true, agents plan without executing actions (default: false)
  - `execute_after_planning` (optional): true | false - if planning_mode=true, whether to spawn a follow-up run to execute the plan (default: false)
  - `context_paths` (optional): Additional context paths for the run (list of `{path, permission}` objects). Merged with or replaces inherited context_paths
  - `agent_system_prompts` (optional): Map of agent ID to additional system prompt text to append for that agent in this run. Allows the interactive agent to inject per-agent guidance based on learnings from previous runs (e.g., corrections, style preferences, domain context)
  - `coordination_overrides` (optional): Additional config overrides for fine-grained control (excludes `context_paths` and `agent_system_prompts`, which have dedicated top-level parameters)

#### Scenario: Single agent run
- **WHEN** the interactive agent invokes `launch_run` with `agent_mode: "single"`
- **THEN** the system SHALL spawn an orchestrator with one agent and skip multi-agent coordination overhead

#### Scenario: Multi-agent run with refinement
- **WHEN** the interactive agent invokes `launch_run` with `agent_mode: "multi"` and `refinement: true`
- **THEN** the system SHALL spawn an orchestrator where agents coordinate, vote, and refine answers (default behavior)

#### Scenario: Multi-agent run without refinement
- **WHEN** the interactive agent invokes `launch_run` with `agent_mode: "multi"` and `refinement: false`
- **THEN** the system SHALL spawn an orchestrator where agents work independently and the best initial answer wins

#### Scenario: Per-agent system prompt customization
- **WHEN** the interactive agent invokes `launch_run` with `agent_system_prompts` mapping agent names (as defined in the YAML config `agents` list) to additional prompt text
- **THEN** the system SHALL append the specified text to each agent's system prompt for that run only
- **AND** agents not listed in the map SHALL use their default system prompts unchanged

#### Scenario: Planning mode run (plan returned to interactive)
- **WHEN** the interactive agent invokes `launch_run` with `planning_mode: true` and `execute_after_planning: false` (the default)
- **THEN** agents SHALL describe their approach without executing actions, and the resulting plan SHALL be returned to the interactive agent for review, decomposition, or modification before any execution

#### Scenario: Planning then automatic execution
- **WHEN** the interactive agent invokes `launch_run` with `planning_mode: true` and `execute_after_planning: true`
- **THEN** the system SHALL use the existing `enable_planning_mode` coordination flow where agents plan and the winner automatically executes in the final presentation phase

#### Scenario: Planning mode maps to existing infrastructure
- **WHEN** `planning_mode: true` is specified on `launch_run`
- **THEN** the system SHALL map this to the existing `CoordinationConfig.enable_planning_mode: true` setting on the spawned orchestrator

#### Scenario: Run execution via tool
- **WHEN** the interactive agent invokes `launch_run` with a task
- **THEN** the system SHALL spawn an orchestrator with the provided configuration and inject the task + context as the initial user message

#### Scenario: Successful results returned to agent
- **WHEN** a spawned run completes successfully
- **THEN** the `RunResult` SHALL be returned with `status: success`, `final_answer`, `workspace_path`, and `coordination_summary`

#### Scenario: Run error
- **WHEN** a spawned run fails due to a backend error, crash, or other failure
- **THEN** the `RunResult` SHALL be returned with `status: error`, an `error` message describing the failure, and any partial results (per-agent answers, workspace files) produced before the failure

#### Scenario: Run timeout
- **WHEN** a spawned run exceeds the orchestrator's configured timeout
- **THEN** the `RunResult` SHALL be returned with `status: timeout` and any partial results (per-agent answers, workspace files) produced before the timeout

#### Scenario: Interactive agent handles failed/timed-out runs
- **WHEN** the interactive agent receives a `RunResult` with `status: error` or `status: timeout`
- **THEN** it SHALL inspect partial results (read workspace files or per-agent answers) and either use what's available, launch a follow-up run with partial results as context to finish the work, or inform the user and ask how to proceed

### Requirement: Interactive Agent System Prompt
The system SHALL reuse existing MassGen system prompt sections but exclude coordination-specific sections and add interactive orchestrator guidance.

#### Scenario: Reused system prompt sections
- **WHEN** the interactive agent's system prompt is built
- **THEN** it SHALL include standard MassGen sections that apply:
  - `AgentIdentitySection` (if custom identity configured)
  - `CoreBehaviorsSection` (default to action, parallel tools)
  - `SkillsSection` (if skills enabled)
  - `ProjectInstructionsSection` (CLAUDE.md/AGENTS.md discovery, if context paths exist)
  - `WorkspaceStructureSection` (critical paths, workspace layout)
  - `FilesystemOperationsSection` + `FilesystemBestPracticesSection` (read/write/list tools)
  - `CommandExecutionSection` (if command execution enabled)
  - `FileSearchSection` (rg/sg search guidance)
  - `MultimodalToolsSection` (if multimodal enabled)
  - `CodeBasedToolsSection` (if CodeAct enabled)
  - `TaskContextSection` (CONTEXT.md creation guidance — critical for project workspace)
  - `TaskPlanningSection` (meta-planning variant — see below)
  - Model-specific guidance sections (GPT5, Grok, etc.)

#### Scenario: Excluded system prompt sections
- **WHEN** the interactive agent's system prompt is built
- **THEN** it SHALL NOT include coordination-specific sections:
  - `EvaluationSection` (vote/new_answer primitives, voting sensitivity)
  - `BroadcastCommunicationSection` (ask_others)
  - `PlanningModeSection` (coordination planning mode instructions)
  - `SubagentSection` (interactive agent uses launch_run, not spawn_subagents)
  - `EvolvingSkillsSection` (unnecessary overhead for interactive agent)
  - Any section that references `new_answer`, `vote`, or coordination primitives

#### Scenario: Meta-planning via TaskPlanningSection
- **WHEN** the interactive agent's system prompt includes TaskPlanningSection
- **THEN** the guidance SHALL be reframed for meta-planning: planning what `launch_run` calls to make (modes, scoping, sequencing), NOT planning how to do the task itself. The interactive agent plans the orchestration strategy, not the implementation.

#### Scenario: Added interactive orchestrator section
- **WHEN** the interactive agent's system prompt is built
- **THEN** it SHALL include an `InteractiveOrchestratorSection` explaining:
  - Its role as the entry point for MassGen
  - Available agents and their capabilities (from config)
  - When to use `launch_run` vs answer directly
  - How to configure runs (agent_mode, refinement, planning_mode)
  - How context flows to runs and results flow back

#### Scenario: No coordination tools
- **WHEN** the interactive agent's tool set is assembled
- **THEN** it SHALL NOT include `new_answer`, `vote`, or `ask_others` tools (those are for coordination agents only)

### Requirement: Run Approval Flow
The system SHALL optionally display an approval modal before executing a run when `require_approval: true`.

#### Scenario: Approval required
- **WHEN** the interactive agent calls `launch_run` and `require_approval: true`
- **THEN** the TUI SHALL display a modal showing the task, context, and selected agents, with Approve/Edit/Cancel buttons

#### Scenario: Approval granted
- **WHEN** the user clicks Approve in the modal
- **THEN** the run SHALL proceed with the displayed configuration

#### Scenario: Approval cancelled
- **WHEN** the user clicks Cancel in the modal
- **THEN** the system SHALL return a cancellation result to the interactive agent without executing the run

#### Scenario: Approval not required
- **WHEN** `require_approval: false`
- **THEN** runs SHALL execute immediately without showing the approval modal

### Requirement: Run Cancellation
The system SHALL allow users to cancel a running run from the TUI.

#### Scenario: Cancel button on active run
- **WHEN** a run is in progress via `launch_run`
- **THEN** the SubagentCard SHALL display a Cancel button

#### Scenario: Cancellation result
- **WHEN** the user cancels a running run
- **THEN** the system SHALL stop the run and return a `RunResult` with `status: cancelled` and any partial results (per-agent answers, workspace files) that were produced before cancellation

#### Scenario: Interactive agent handles cancellation
- **WHEN** the interactive agent receives a cancelled `RunResult`
- **THEN** it SHALL inspect partial results and inform the user what was completed, offering to retry or continue with what's available

### Requirement: Session Persistence and Resumability
The system SHALL persist interactive session state to disk so sessions can be resumed after TUI restarts.

#### Scenario: Session state serialization
- **WHEN** the interactive agent sends or receives a message, or a run completes
- **THEN** the session state SHALL be persisted to disk under the project workspace (or a default location if no project is active)

#### Scenario: Session state contents
- **WHEN** session state is serialized
- **THEN** it SHALL include: conversation history (human and agent messages), run history (RunResults with summaries), active project reference, and any pending context

#### Scenario: Default resume on startup
- **WHEN** the TUI starts with `interactive_mode.enabled: true` and previous sessions exist
- **THEN** the system SHALL default to continuing the most recent session, restoring conversation history and run context

#### Scenario: Session browser
- **WHEN** the user wants to switch sessions
- **THEN** the TUI SHALL provide a session browser listing previous sessions with: timestamp, project name (if any), and a preview of the last message
- **AND** the user SHALL be able to select any previous session to resume

#### Scenario: Conversation history rehydration
- **WHEN** a session is resumed
- **THEN** the interactive agent's message history SHALL be restored so the backend has full conversational context (not just a summary)

#### Scenario: Fresh session option
- **WHEN** the user is in the session browser
- **THEN** the user SHALL have the option to start a fresh session instead of resuming an existing one

### Requirement: Interactive Mode Configuration
The system SHALL support `orchestrator.interactive_mode` configuration section in YAML configs.

#### Scenario: Config structure
- **WHEN** a config file includes `orchestrator.interactive_mode`
- **THEN** the validator SHALL accept fields: `enabled` (bool), `require_approval` (bool), `backend` (optional backend config)

#### Scenario: Default values
- **WHEN** `interactive_mode` is specified but fields are omitted
- **THEN** defaults SHALL be: `enabled: true`, `require_approval: true`, `backend: null` (use first agent's backend)

#### Scenario: Validation errors
- **WHEN** invalid values are provided (e.g., negative timeout)
- **THEN** the config validator SHALL report a clear error with location and suggestion

### Requirement: TUI Mode State Extension
The system SHALL extend `TuiModeState` to track interactive mode state.

#### Scenario: State fields
- **WHEN** `TuiModeState` is instantiated
- **THEN** it SHALL include: `interactive_mode` (bool), `interactive_session` (Optional[InteractiveSession]), `current_run_id` (Optional[str]), `pending_run_approval` (bool)

#### Scenario: Mode indicator
- **WHEN** interactive mode is active
- **THEN** the TUI SHALL NOT display the standard mode bar (plan/agent/refinement phases)
- **AND** SHALL instead display a context bar showing: current project name (if any), active run status, and a button to switch to normal MassGen coordination mode

### Requirement: Context Bar
The system SHALL display a context bar in place of the standard mode bar when interactive mode is active.

#### Scenario: Context bar content
- **WHEN** interactive mode is active
- **THEN** the context bar SHALL show: current project name (or "No project"), run status (idle/running/complete), and a "Coordinate" button to switch to normal mode

#### Scenario: No active run
- **WHEN** no run is in progress
- **THEN** the context bar SHALL show idle status and the switch-to-normal button

#### Scenario: Active run
- **WHEN** a run is in progress via `launch_run`
- **THEN** the context bar SHALL show the run status (e.g., "Running: task summary...")

### Requirement: Switch to Normal Coordination Mode
The system SHALL allow users to switch from interactive mode to the normal MassGen coordination TUI view via a button in the UI.

#### Scenario: Switch button
- **WHEN** the user clicks the "Coordinate" button in the context bar
- **THEN** the TUI SHALL transition to the standard coordination view with the mode bar, agent tabs, and full coordination workflow using the same agents from the config
- **AND** the user SHALL be prompted for a question to coordinate on (standard MassGen input flow)
- **AND** the coordination run SHALL be independent of the interactive session (not managed by the interactive agent)

#### Scenario: Interactive session during coordination
- **WHEN** a coordination run is active via the "Coordinate" button
- **THEN** the interactive session SHALL be paused but preserved in memory
- **AND** the user SHALL NOT be able to switch back to interactive mode until the coordination run completes or is cancelled

#### Scenario: Return to interactive
- **WHEN** a coordination run completes or is cancelled
- **THEN** the TUI SHALL return to interactive mode with the interactive session resumed
- **AND** the coordination run results SHALL NOT be automatically injected into the interactive agent's context (the runs are independent)

### Requirement: Context Flow Between Interactive and Runs
The system SHALL support one-way context flow from interactive session to spawned runs.

#### Scenario: Context injection
- **WHEN** a run is spawned via `launch_run`
- **THEN** the `context` parameter (if provided) SHALL be injected into the run's initial user message along with the `task`

#### Scenario: Context paths inheritance
- **WHEN** a run is spawned via `launch_run`
- **THEN** the spawned orchestrator SHALL inherit the interactive session's `context_paths` from the orchestrator config

#### Scenario: Context paths override per run
- **WHEN** the interactive agent specifies `context_paths` in `launch_run`
- **THEN** the specified paths SHALL be merged with the inherited context_paths from the orchestrator config

#### Scenario: Results consumption
- **WHEN** a run completes
- **THEN** the interactive agent SHALL receive: `final_answer`, `workspace_path`, and `coordination_summary` (including votes, winner, rounds)

### Requirement: Project-Based Workspace
The system SHALL support a project-based workspace structure for managing context across runs.

#### Scenario: Workspace directory structure
- **WHEN** the interactive agent creates a project
- **THEN** it SHALL create a directory under `workspace/projects/<project-name>/` containing:
  - `CONTEXT.md`: Project goals, decisions, constraints, and ongoing context
  - `filepaths.json`: Key files and directories with descriptions (context paths, not exhaustive)
  - `runs/`: Directory for associated run references
  - `deliverables/`: Most up-to-date outputs from runs (may be updated by interactive agent post-run)

#### Scenario: filepaths.json format
- **WHEN** `filepaths.json` is created or updated
- **THEN** it SHALL contain a JSON object mapping logical names to `{path, desc}` entries, where path can be a file OR directory

#### Scenario: Run log tracking
- **WHEN** a run completes for a project
- **THEN** the runs/ directory SHALL contain a `run_description.json` with description and paths for logs about that topic/deliverable

#### Scenario: Deliverables as source of truth
- **WHEN** the interactive agent or a run produces output
- **THEN** the `deliverables/` directory SHALL contain the most current version (since the interactive agent may update files post-run, deliverables/ is the source of truth, not the most recent run's workspace)

#### Scenario: Scratch workspace
- **WHEN** the interactive agent needs temporary working space
- **THEN** it SHALL use `workspace/scratch/` for ephemeral files not associated with any project

### Requirement: Launch Run TUI Display
The system SHALL reuse the existing SubagentCard/SubagentScreen infrastructure to display `launch_run` runs, since subagents already are full MassGen orchestrator runs with multi-agent coordination and voting.

#### Scenario: Inline run card
- **WHEN** the interactive agent calls `launch_run`
- **THEN** a SubagentCard SHALL appear inline in the interactive conversation timeline showing run status, progress, and task summary

#### Scenario: Expanded run view
- **WHEN** the user clicks on the run card
- **THEN** a SubagentScreen SHALL open showing the full coordination view (agent tabs, timelines, tool cards, voting) for the spawned run

#### Scenario: Run framing
- **WHEN** a SubagentScreen displays a `launch_run` coordination
- **THEN** it SHALL be labeled as "Run: <task summary>" rather than "Subagent: <task>"

### Requirement: Interactive Conversation UI
The system SHALL display the interactive agent's conversation in a chat-like layout within a single agent tab.

#### Scenario: Chat layout
- **WHEN** interactive mode is active
- **THEN** the TUI SHALL display the conversation in a single agent tab with agent messages left-aligned and human messages right-aligned

#### Scenario: Human message persistence
- **WHEN** the user sends a message to the interactive agent
- **THEN** the message SHALL appear in the conversation timeline and persist across the session (not disappear after the agent responds)

#### Scenario: User input disabled during active run
- **WHEN** a `launch_run` is in progress
- **THEN** the TUI SHALL disable user input to the interactive agent (the user cannot send messages to the interactive agent while a run is active)
- **AND** the user MAY still interact with the run via the SubagentScreen (e.g., cancel button) but cannot send freeform messages to the interactive agent until the run completes or is cancelled

#### Scenario: Run cards inline
- **WHEN** the interactive agent calls `launch_run`
- **THEN** the SubagentCard SHALL appear inline within the same conversation timeline, between the agent's messages

### Requirement: Interactive Agent Delegation Behavior
The interactive agent SHALL delegate complex work to multi-agent runs while handling simple tasks directly.

#### Scenario: Simple task handling
- **WHEN** a user asks a simple question that the interactive agent can answer directly
- **THEN** the agent SHALL respond without spawning a run

#### Scenario: Complex task delegation
- **WHEN** a user requests complex work requiring multi-agent coordination
- **THEN** the interactive agent SHALL use `launch_run` to delegate the work

#### Scenario: Context-efficient operation
- **WHEN** large outputs or files need to be passed between runs
- **THEN** the interactive agent SHALL summarize and filter context rather than passing everything verbatim

### Requirement: Plan Decomposition and Chained Execution
The interactive agent SHALL be capable of chaining `launch_run` calls to decompose large plans into scoped execution chunks, evaluate results between runs, and rerun if needed.

#### Scenario: Plan-then-execute chain
- **WHEN** a complex task requires planning before execution
- **THEN** the interactive agent SHALL first call `launch_run` with `planning_mode: true`, receive the plan, then decompose the plan into scoped execution runs

#### Scenario: Plan decomposition into scoped runs
- **WHEN** a planning run returns a large plan (e.g., 20-50 tasks)
- **THEN** the interactive agent SHALL group related tasks into manageable chunks and call `launch_run` for each chunk with scoped context, rather than passing the entire plan to a single run

#### Scenario: Result evaluation between runs
- **WHEN** a scoped execution run completes
- **THEN** the interactive agent SHALL evaluate whether the result is good enough or needs a rerun with additional context/corrections before proceeding to the next chunk

#### Scenario: Rerun on insufficient results
- **WHEN** the interactive agent determines a run's output is incomplete or incorrect
- **THEN** it SHALL call `launch_run` again for that chunk with updated context explaining what was missing or wrong

#### Scenario: Delegated evaluation
- **WHEN** the interactive agent does not want to evaluate results itself (e.g., to save context or for objectivity)
- **THEN** it SHALL call `launch_run` with the previous output as context to have other agents evaluate, verify, or refine the results (typically with `refinement: false` but configurable)

#### Scenario: Natural language run configuration
- **WHEN** a user provides natural language preferences (e.g., "big plan, no feedback needed", "quick single agent", "thorough multi-agent review")
- **THEN** the interactive agent SHALL translate these into appropriate `launch_run` parameters (planning_mode, agent_mode, refinement, require_approval overrides)
