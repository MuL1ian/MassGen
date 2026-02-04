# Interactive Mode Implementation Tasks

## 1. Core Infrastructure

- [ ] 1.1 Create `massgen/interactive_session.py` with `InteractiveSession` class
  - [ ] 1.1.1 Implement session lifecycle management
  - [ ] 1.1.2 Implement `chat()` async generator for message processing
  - [ ] 1.1.3 Implement `_handle_launch_run()` for tool call handling
  - [ ] 1.1.4 Implement `_execute_run()` for orchestrator spawning
  - [ ] 1.1.5 Implement run history tracking
  - [ ] 1.1.6 Implement session persistence (serialize conversation history, run history, project ref to disk)
  - [ ] 1.1.7 Implement session resume (rehydrate message history for backend context)
  - [ ] 1.1.8 Implement session browser (list previous sessions with timestamp, project, last message preview)
  - [ ] 1.1.9 Implement context compaction for long sessions

- [ ] 1.2 Implement project workspace management
  - [ ] 1.2.1 Create project directory structure (CONTEXT.md, filepaths.json, runs/, deliverables/)
  - [ ] 1.2.2 Implement filepaths.json read/write (files and directories with descriptions)
  - [ ] 1.2.3 Implement run_description.json for run log tracking
  - [ ] 1.2.4 Implement deliverables/ management (source of truth for outputs)

- [ ] 1.3 Create `massgen/mcp_tools/interactive/` MCP server with `launch_run` tool
  - [ ] 1.3.1 Implement MCP server following subagent MCP server pattern
  - [ ] 1.3.2 Define `launch_run` tool schema with all run configuration parameters:
    - `task` (required): Description of what to accomplish
    - `context` (optional): Background information, constraints
    - `agent_mode` (optional): "single" | "multi" (default: "multi")
    - `agents` (optional): List of specific agent IDs
    - `refinement` (optional): Enable voting/refinement (default: mode-dependent)
    - `planning_mode` (optional): Plan without executing (default: false)
    - `execute_after_planning` (optional): Auto-execute after planning (default: false)
    - `context_paths` (optional): Additional context paths for the run (list of `{path, permission}` objects)
    - `agent_system_prompts` (optional): Map of agent ID to additional system prompt text for that run
    - `coordination_overrides` (optional): Fine-grained config overrides (excludes context_paths and agent_system_prompts)
  - [ ] 1.3.3 Implement MCP tool handler that wraps SubagentManager for run execution
  - [ ] 1.3.4 Register MCP server for auto-start when interactive mode enabled

- [ ] 1.4 Add `InteractiveOrchestratorSection` to `system_prompt_sections.py`
  - [ ] 1.4.1 Create section class that explains interactive orchestrator role
  - [ ] 1.4.2 Document available agents and their capabilities (from config)
  - [ ] 1.4.3 Explain when to use `launch_run` vs answer directly
  - [ ] 1.4.4 Document all run configuration options (agent_mode, refinement, planning_mode)
  - [ ] 1.4.5 Explain context flow to runs and result handling
  - [ ] 1.4.6 Document error/timeout/cancellation handling (inspect partial results, retry strategies)

- [ ] 1.5 Update `SystemMessageBuilder` for interactive mode
  - [ ] 1.5.1 Add method to build interactive agent system prompt
  - [ ] 1.5.2 Include standard sections: CoreBehaviors, Skills, Memory, Filesystem, TaskPlanning
  - [ ] 1.5.3 Exclude coordination sections: MassGenCoordination, Broadcast, VotingGuidance
  - [ ] 1.5.4 Add InteractiveOrchestratorSection

- [ ] 1.6 Add config validation for `interactive_mode` section
  - [ ] 1.6.1 Add `InteractiveModeConfig` dataclass in `agent_config.py`
  - [ ] 1.6.2 Add `_validate_interactive_mode()` to `config_validator.py`
  - [ ] 1.6.3 Update YAML schema documentation

## 2. TUI Integration

- [ ] 2.1 Extend `TuiModeState` in `tui_modes.py`
  - [ ] 2.1.1 Add `interactive_mode: bool` field
  - [ ] 2.1.2 Add `interactive_session: Optional[InteractiveSession]` field
  - [ ] 2.1.3 Add `current_run_id: Optional[str]` field
  - [ ] 2.1.4 Add `pending_run_approval: bool` field
  - [ ] 2.1.5 Update `get_orchestrator_overrides()` for interactive mode

- [ ] 2.2 Create `massgen/frontend/displays/textual/run_approval_modal.py`
  - [ ] 2.2.1 Implement modal UI with task/context display
  - [ ] 2.2.2 Add agent list display
  - [ ] 2.2.3 Add Approve/Edit/Cancel buttons
  - [ ] 2.2.4 Handle button press events
  - [ ] 2.2.5 Return approval result to parent

- [ ] 2.3 Update `textual_terminal_display.py`
  - [ ] 2.3.1 Initialize `InteractiveSession` on mount when enabled
  - [ ] 2.3.2 Handle run approval callbacks
  - [ ] 2.3.3 Show run progress during execution
  - [ ] 2.3.4 Transition UI between interactive and running states
  - [ ] 2.3.5 Handle `InteractiveModeChanged` messages

- [ ] 2.4 Replace mode bar with context bar in interactive mode
  - [ ] 2.4.1 Hide standard mode bar (plan/agent/refinement) when interactive mode active
  - [ ] 2.4.2 Create context bar widget showing: project name, run status (idle/running/complete)
  - [ ] 2.4.3 Add "Coordinate" button to switch to normal MassGen coordination view
  - [ ] 2.4.4 Handle return to interactive mode after coordination completes

## 3. CLI & Polish

- [ ] 3.1 Update `cli.py`
  - [ ] 3.1.1 Add `--interactive` flag (default behavior when TUI enabled)
  - [ ] 3.1.2 Create `InteractiveSession` when flag enabled
  - [ ] 3.1.3 Pass session to TUI initialization

- [ ] 3.2 Write tests
  - [ ] 3.2.1 Unit test: `test_launch_run_tool_schema()` - all parameters present
  - [ ] 3.2.2 Unit test: `test_interactive_session_initialization()`
  - [ ] 3.2.3 Unit test: `test_run_config_single_agent()` - agent_mode="single"
  - [ ] 3.2.4 Unit test: `test_run_config_multi_no_refine()` - refinement=false
  - [ ] 3.2.5 Unit test: `test_run_config_planning_mode()` - planning_mode=true
  - [ ] 3.2.6 Integration test: `test_interactive_launches_run()`
  - [ ] 3.2.7 Integration test: `test_context_passed_correctly()`
  - [ ] 3.2.8 Integration test: `test_results_returned()`
  - [ ] 3.2.9 Integration test: `test_planning_then_execute()`

## 4. Documentation

- [ ] 4.1 Add example configs
  - [ ] 4.1.1 Create `massgen/configs/interactive/basic_interactive.yaml`
  - [ ] 4.1.2 Create `massgen/configs/interactive/code_review_interactive.yaml`

- [ ] 4.2 Create `docs/modules/interactive_mode.md` module documentation
  - [ ] 4.2.1 Architecture overview (InteractiveSession, launch_run MCP, system prompt sections)
  - [ ] 4.2.2 Data flow (context paths, run spawning, results return)
  - [ ] 4.2.3 TUI integration (context bar, SubagentScreen reuse, mode switching)
  - [ ] 4.2.4 Project workspace structure (CONTEXT.md, filepaths.json, runs/, deliverables/)

- [ ] 4.3 Update user guide
  - [ ] 4.3.1 Add interactive mode section to docs

## 5. Future Enhancements (Deferred)

These are tracked but out of scope for initial implementation:

- [ ] 5.1 Meta-level task planning with high-level task lists
- [ ] 5.2 Parallel run orchestration
- [ ] 5.3 `ask_others` integration (pending broadcast refactoring)
- [ ] 5.4 Native MassGen project-based workspace support
- [ ] 5.5 Run session continuity — allow `launch_run` to resume a previous run's coordination session (same agents, context, and state) rather than starting fresh each time
- [ ] 5.6 Runtime config switching (allow interactive agent to modify its own config or create new agent definitions dynamically, beyond launch_run overrides)
- [ ] 5.7 Subagent reuse for single-agent tasks (interactive agent could use existing subagent infrastructure for quick tasks instead of full launch_run orchestration)
- [ ] 5.8 Context compaction for long interactive sessions (auto-summarize earlier context, preserve recent exchanges)
- [ ] 5.9 Human prompt injection into active runs — allow queuing user messages into a running `launch_run` (similar to main orchestrator human input support, not yet supported in subagent infrastructure)
- [ ] 5.10 Log analysis integration — allow the interactive agent to launch log analysis (via existing `massgen-log-analyzer` skill/tooling) on completed or failed runs for debugging and performance insights
- [ ] 5.11 Cost tracking and budget management — track token usage and costs for the interactive conversation and each `launch_run` call separately, surface costs to the interactive agent so it can make cost-aware decisions (e.g., prefer single-agent for cheap tasks, warn user before expensive runs)
