# Interactive Mode Module

## Overview

Interactive Mode is a persistent orchestration layer that sits above MassGen's coordination system. The interactive agent is the main entry point for users — it understands MassGen's capabilities, helps plan and configure runs, handles simple tasks directly, and delegates complex work to multi-agent coordination via `launch_run`.

## Architecture

```
User Input
    │
    ▼
InteractiveSession
├── InteractiveAgent (persistent conversation)
│   ├── launch_run MCP tool → spawns Orchestrator (reuses subagent infra)
│   ├── Filesystem/MCP tools (for simple direct tasks)
│   └── Task planning tools (meta-planning: what runs to make)
├── Run history tracking
└── Project workspace management

Spawned Run (via launch_run)
├── Full Orchestrator with configured agents
├── Coordination → voting → presentation
├── Displayed via SubagentCard/SubagentScreen (reused)
└── Results returned to InteractiveAgent
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `InteractiveSession` | `massgen/interactive_session.py` | Session lifecycle, run history, project workspace |
| `launch_run` MCP server | `massgen/mcp_tools/interactive/` | MCP tool for spawning runs (portable across backends) |
| `InteractiveOrchestratorSection` | `massgen/system_prompt_sections.py` | System prompt explaining orchestrator role and launch_run usage |
| Context bar | `massgen/frontend/displays/textual_widgets/` | Replaces mode bar; shows project name, run status, "Coordinate" button |

## Configuration

```yaml
orchestrator:
  interactive_mode:
    enabled: true              # Default when TUI launches
    require_approval: true     # Approval modal before runs
    backend:                   # Optional: defaults to first agent's backend
      type: "claude_code"
      model: "claude-opus-4-5"
    append_system_prompt: |    # Optional custom guidance
      You specialize in code review tasks.

  context_paths:
    - path: "src/"
      permission: "write"

agents:
  - id: "agent_a"
    backend: { type: "claude", model: "claude-sonnet-4-20250514" }
  - id: "agent_b"
    backend: { type: "openai", model: "gpt-5" }
```

## launch_run MCP Tool

The interactive agent spawns runs via the `launch_run` MCP tool. This is an MCP server (not a workflow tool) so it can be exposed to external backends (Claude Code, Codex, etc.).

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `task` | string | required | What to accomplish |
| `context` | string | null | Background info, constraints, previous decisions |
| `agent_mode` | "single" \| "multi" | "multi" | One or multiple agents |
| `agents` | string[] | all | Specific agents to use |
| `refinement` | bool | true (multi), false (single) | Enable voting/refinement |
| `planning_mode` | bool | false | Plan without executing |
| `execute_after_planning` | bool | false | Auto-execute after planning (uses existing planning mode) |
| `context_paths` | list | inherited | Additional/override context paths for the run |
| `coordination_overrides` | object | null | Fine-grained config overrides |

### Run Mode Matrix

| Mode | agent_mode | refinement | planning_mode | Behavior |
|------|------------|------------|---------------|----------|
| Quick single | single | false | false | One agent, direct execution |
| Multi no-refine | multi | false | false | Multiple agents, best initial wins |
| Multi + refine | multi | true | false | Full coordination with voting |
| Plan only | any | any | true | Plan returned to interactive agent for review |
| Plan → Execute | any | any | true + execute | Existing planning mode auto-execute flow |

## System Prompt Sections

### Included
- `AgentIdentitySection` — custom identity
- `CoreBehaviorsSection` — action bias, parallel tools
- `SkillsSection` — available skills
- `ProjectInstructionsSection` — CLAUDE.md/AGENTS.md discovery
- `WorkspaceStructureSection` — critical paths
- `FilesystemOperationsSection` + `FilesystemBestPracticesSection`
- `CommandExecutionSection` (if enabled)
- `FileSearchSection`
- `MultimodalToolsSection` (if enabled)
- `CodeBasedToolsSection` (if enabled)
- `TaskContextSection` — CONTEXT.md creation guidance
- `TaskPlanningSection` — **reframed for meta-planning** (planning what launch_run calls to make, not how to do the task)
- Model-specific guidance (GPT5, Grok)
- **`InteractiveOrchestratorSection`** — core new section

### Excluded
- `EvaluationSection` — vote/new_answer primitives
- `BroadcastCommunicationSection` — ask_others (deferred)
- `PlanningModeSection` — coordination planning mode
- `SubagentSection` — interactive uses launch_run, not spawn_subagents
- `EvolvingSkillsSection` — unnecessary overhead

## Plan Decomposition and Chained Execution

The interactive agent's key capability is breaking large tasks into scoped runs:

```
1. User: "Build a full-stack todo app"
2. Interactive agent calls launch_run(planning_mode=true)
3. Plan returned (e.g., 30 tasks)
4. Interactive agent groups into chunks:
   - Chunk 1: DB schema + API endpoints (tasks 1-8)
   - Chunk 2: Frontend components (tasks 9-18)
   - Chunk 3: Auth + deployment (tasks 19-30)
5. launch_run(task=chunk_1, context=plan_summary)
6. Evaluate result (self or via delegated evaluation run)
7. If good → launch_run(task=chunk_2, context=chunk_1_result)
8. If bad → rerun chunk_1 with corrections
```

The interactive agent can delegate evaluation to other agents via `launch_run` with the previous output as context, rather than spending its own context window on evaluation.

## TUI Integration

### Context Bar (replaces Mode Bar)
- Shows: current project name, run status (idle/running/complete), "Coordinate" button
- No plan/agent/refinement phase indicators (those are for coordination mode)
- In coordination mode (outside interactive context bar), skills management now lives on a dedicated `Skills` mode-bar button rather than analysis-only settings.

### Run Display (reuses Subagent infrastructure)
- `SubagentCard` appears inline in interactive timeline during runs
- Click to expand into `SubagentScreen` with full coordination view
- Labeled "Run: <task>" instead of "Subagent: <task>"

### Switch to Normal Mode
- "Coordinate" button in context bar transitions to standard coordination TUI
- After coordination completes, user can return to interactive mode

## Project Workspace Structure

```
workspace/
├── projects/
│   ├── todo_api/
│   │   ├── CONTEXT.md              # Goals, decisions, constraints
│   │   ├── filepaths.json          # Key files/dirs with descriptions
│   │   ├── runs/
│   │   │   └── run_description.json # Description + log paths
│   │   └── deliverables/           # Source of truth for outputs
│   └── data_pipeline/
│       └── ...
└── scratch/                        # Ephemeral working area
```

- `filepaths.json` tracks files AND directories (context paths, not exhaustive)
- `deliverables/` is the source of truth — interactive agent may update files post-run
- `run_description.json` tracks run logs by topic/deliverable

## Context Paths

- Interactive agent inherits `context_paths` from orchestrator config
- Spawned runs inherit those paths automatically
- `launch_run` can specify additional/override `context_paths` per run
- Useful for pointing runs to specific project workspace directories

## Deferred Capabilities

- Session persistence for interactive conversations
- Context compaction for long sessions
- Runtime config switching
- `ask_others` integration (pending broadcast refactoring)
- Parallel run orchestration
- Subagent reuse for quick single-agent tasks
- Native project workspace support in MassGen core
