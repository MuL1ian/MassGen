# Interactive Mode Design

## Context

MassGen is a multi-agent coordination system that currently operates in a task-oriented fashion: users submit a question, agents coordinate to solve it, and a final answer is produced. There's no persistent layer for ongoing orchestration or context management across runs. Also, it's important that sometimes multi-agent runs are not needed and the user just wants to ask a question to a single agent, e.g., for quick questions or for simple tasks. We want to add an interactive mode that allows the user to have a conversation with MassGen, where the interactive agent can decide when to delegate to a run or answer directly.

**Stakeholders:**
- End users who want a more conversational MassGen experience
- Developers building on MassGen who need programmatic run control
- Power users managing complex multi-run workflows

## Goals / Non-Goals

### Goals
- Create a persistent interactive layer that manages context across runs
- Enable the interactive agent to decide when to delegate vs. answer directly
- Provide clear data flow between interactive layer and spawned runs
- Maintain compatibility with existing single-task workflows
- Enable approval flows before spawning runs (configurable)

### Non-Goals
- Meta-level task planning (deferred)
- Parallel run orchestration (deferred)
- `ask_others` integration (pending broadcast refactoring)
- Bidirectional callbacks between interactive and runs (one-way only)

## Decisions

### Decision 1: Entry Point Strategy
**Choice:** Interactive Mode is the default when TUI launches with `interactive_mode.enabled: true` in config.

**Why:** This makes interactive mode the natural starting point without requiring new CLI flags. Users who want single-task behavior can disable it or use `--automation` mode.

**Alternatives considered:**
- Separate `--interactive` flag: Adds cognitive overhead
- Always interactive: Breaks existing workflows

### Decision 2: Run Triggering Mechanism
**Choice:** Use a `launch_run` tool that the interactive agent invokes.

**Why:** This follows the existing workflow toolkit pattern. The agent can reason about when to use it, and tool calls are naturally observable in the TUI.

**Alternatives considered:**
- Magic keywords in messages: Less flexible, harder to pass context
- Separate UI button: Removes agent autonomy

### Decision 3: Context Flow Architecture
**Choice:** One-way context flow (interactive → runs). The interactive agent packages context and passes it to runs. Results flow back but runs cannot request context mid-execution.

**Why:** Simplifies initial implementation. Bidirectional flow adds significant complexity and can be added later.

**Alternatives considered:**
- Bidirectional with callbacks: Too complex for v1
- No context passing: Limits usefulness

### Decision 4: Tool Set Differentiation
**Choice:** Interactive agent gets `launch_run` as an MCP tool (plus any other MCP/external tools). It does NOT get workflow tools like `new_answer`, `vote`, or `ask_others`.

**Why:** The interactive agent orchestrates but doesn't participate in coordination. Clear role separation.

**Alternatives considered:**
- Full tool access: Would confuse the agent's role
- Subset of coordination tools: Partial access is confusing

### Decision 4b: launch_run as MCP Tool (New Server)
**Choice:** `launch_run` is implemented as an MCP tool in a new `massgen/mcp_tools/interactive/` server, separate from the existing subagent MCP server.

**Why:**
- Portable across backends — any backend supporting MCP can use it
- Could be exposed to external tools (Claude Code, Codex) by adding this MCP server
- Follows the existing subagent MCP server pattern but with cleaner separation
- More extensible — other MCP clients can call it, enabling MassGen orchestration from outside MassGen
- When exposed externally, the `InteractiveOrchestratorSection` system prompt content can be included as context so external clients know when/how to call it

**Alternatives considered:**
- Workflow tool: Tighter MassGen integration but less portable
- Extend subagent MCP server: Same infrastructure but muddies the subagent server's responsibility

### Decision 5: System Prompt Section Reuse
**Choice:** Reuse existing MassGen system prompt sections (skills, memory, filesystem, etc.) but exclude coordination-specific sections.

**Why:** The interactive agent still needs capabilities like skills, memory, and filesystem access. Only the coordination workflow (vote/new_answer) doesn't apply.

**Included sections:**
- `AgentIdentitySection` (custom identity)
- `CoreBehaviorsSection` (action bias, parallel tools)
- `SkillsSection` (if enabled)
- `MemoryFilesystemSection` (if enabled)
- `FilesystemWorkspaceSection` (if workspace configured)
- `TaskPlanningSection` (if enabled)
- Model-specific guidance (GPT5, Grok)

**Excluded sections:**
- `MassGenCoordinationSection` (vote/new_answer workflow)
- `BroadcastCommunicationSection` (ask_others)
- `VotingGuidanceSection` (voting criteria)

**Added section:**
- `InteractiveOrchestratorSection` - explains launch_run usage and run configuration options. This is the core of the interactive mode and should be the most important section in the system prompt.

### Decision 6: Approval Flow
**Choice:** Optional approval modal controlled by `require_approval` config.

**Why:** Some users want oversight before runs start. Others prefer autonomous operation.

**Alternatives considered:**
- Always require approval: Too friction-heavy
- Never require approval: Some users want control

### Decision 7: Launch Run Tool Parameters
**Choice:** The `launch_run` tool supports flexible run configurations:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `task` | string | required | What to accomplish |
| `context` | string | null | Background info, constraints |
| `agent_mode` | "single" \| "multi" | "multi" | One or multiple agents |
| `agents` | string[] | all | Specific agents to use |
| `refinement` | bool | true (multi), false (single) | Enable voting/refinement |
| `planning_mode` | bool | false | Plan without executing |
| `execute_after_planning` | bool | false | Auto-execute after planning |
| `context_paths` | list | inherited | Additional context paths for the run |
| `agent_system_prompts` | map | null | Per-agent additional system prompt text |
| `coordination_overrides` | object | null | Fine-grained config |

**Run Mode Matrix:**

| Mode | agent_mode | refinement | planning_mode | Behavior |
|------|------------|------------|---------------|----------|
| Quick single | single | false | false | One agent, direct execution |
| Single + refine | single | true | false | One agent with self-refinement |
| Multi no-refine | multi | false | false | Multiple agents, best initial wins |
| Multi + refine | multi | true | false | Full coordination with voting |
| Plan only | any | any | true | Agents describe approach, no actions |
| Plan → Execute | any | any | true + execute | Plan first, then auto-execute winner |

**Why this flexibility:** Different tasks have different optimal configurations. Simple tasks don't need multi-agent overhead. Complex tasks benefit from coordination. Planning mode enables "think first" workflows. Using an LLM itself to decide what to launch is effective for routing and can take human feedback for easy toggling instead of needing to manually ask for a specific mode every time.

## Architecture

### Class Hierarchy

```
InteractiveSession
├── _interactive_agent: ChatAgent (single agent, special system prompt)
├── run_history: List[RunResult]
├── _orchestrator_factory: Callable (creates orchestrators for runs)
└── workspace: ProjectWorkspace (context/file management)

LaunchRunMCPServer (massgen/mcp_tools/interactive/)
├── Exposes `launch_run` MCP tool
├── Wraps SubagentManager for run execution
└── Auto-starts when interactive mode enabled
```

### Interactive Conversation UI

```
┌─────────────────────────────────────────────────────┐
│  Context Bar: [Project: my-app] [Status: Idle] [Coordinate] │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────────────────┐                │
│  │ 🤖 MassGen                       │                │
│  │ That's a significant refactor.   │                │
│  │ Let me plan this out first and   │                │
│  │ then delegate to a multi-agent   │                │
│  │ run.                             │                │
│  └─────────────────────────────────┘                │
│                                                     │
│  ┌─────────────────────────────────┐                │
│  │ ▶ Run: Plan JWT auth refactor    │                │
│  │   Status: Complete ✓             │                │
│  │   3 agents · 2 rounds · 4m12s   │                │
│  │   [Click to expand]              │                │
│  └─────────────────────────────────┘                │
│                                                     │
│  ┌─────────────────────────────────┐                │
│  │ 🤖 MassGen                       │                │
│  │ The agents produced a plan with  │                │
│  │ 3 phases. I'll now execute       │                │
│  │ phase 1...                       │                │
│  └─────────────────────────────────┘                │
│                                                     │
│  ┌─────────────────────────────────┐                │
│  │ ▶ Run: Execute phase 1 - JWT     │                │
│  │   Status: Running...             │                │
│  │   3 agents · round 1             │                │
│  │   [Cancel]                       │                │
│  └─────────────────────────────────┘                │
│                                                     │
│                ┌─────────────────────────────────┐  │
│                │ 🧑 User                         │  │
│                │ Actually, use Paseto instead    │  │
│                │ of JWT                          │  │
│                └─────────────────────────────────┘  │
│                                                     │
├─────────────────────────────────────────────────────┤
│  [Type a message...]                        [Send]  │
└─────────────────────────────────────────────────────┘
```

- Agent messages and run cards: left-aligned
- User messages: right-aligned
- Input box always visible at bottom
- User can send messages while a run is active (queued for interactive agent)

### Data Flow

```
User Input
    │
    ▼
InteractiveSession.chat()
    │
    ├─── Simple query ──────────► Interactive Agent responds directly
    │
    └─── Complex task ──────────► Interactive Agent calls launch_run
                                        │
                                        ▼
                                  Approval Modal (if required)
                                        │
                                        ▼
                                  InteractiveSession._execute_run()
                                        │
                                        ▼
                                  Orchestrator spawned with context
                                        │
                                        ▼
                                  Multi-agent coordination
                                        │
                                        ▼
                                  RunResult returned to Interactive Agent
                                        │
                                        ▼
                                  Agent summarizes/suggests next steps
```

### State Machine

```
                    ┌──────────────────────────────────────────┐
                    │                                          │
                    ▼                                          │
             ┌──────────┐                                      │
             │   IDLE   │◄──────────────────────────┐          │
             └────┬─────┘                           │          │
                  │                                 │          │
                  │ User sends message              │          │
                  ▼                                 │          │
             ┌──────────┐                           │          │
             │ CHATTING │                           │          │
             └────┬─────┘                           │          │
                  │                                 │          │
          ┌───────┴───────┐                         │          │
          │               │                         │          │
          ▼               ▼                         │          │
    Direct reply    launch_run called               │          │
          │               │                         │          │
          │               ▼                         │          │
          │        ┌──────────────┐                 │          │
          │        │ AWAITING     │─────────────────┤          │
          │        │ APPROVAL     │  Cancel         │          │
          │        └──────┬───────┘                 │          │
          │               │ Approve                 │          │
          │               ▼                         │          │
          │        ┌──────────────┐                 │          │
          │        │   RUNNING    │                 │          │
          │        └──┬───┬───┬──┘                  │          │
          │           │   │   │                     │          │
          │  Complete │   │   │ Error/Timeout       │          │
          │           │   │   │                     │          │
          │           │   │   ▼                     │          │
          │           │   │ ┌──────────────┐        │          │
          │           │   │ │ PROCESSING   │────────┘          │
          │           │   │ │ PARTIAL      │ (has partial      │
          │           │   │ └──────────────┘  results)         │
          │           │   │                                    │
          │           │   │ Cancel                             │
          │           │   ▼                                    │
          │           │ ┌──────────────┐                       │
          │           │ │ PROCESSING   │───────────────────────┘
          │           │ │ CANCELLED    │ (has partial results)
          │           │ └──────────────┘
          │           ▼
          │    ┌──────────────┐
          │    │ PROCESSING   │────────────────────────────────┘
          │    │ RESULTS      │
          │    └──────────────┘
          │
          └────────────────────────────────────────────────────┘
```

## Config Schema

```yaml
orchestrator:
  interactive_mode:
    enabled: true                    # Enable interactive mode
    require_approval: true           # Show approval modal before runs
    backend:                         # Optional: defaults to first agent's backend
      type: "claude_code"
      model: "claude-opus-4-5"
    # context_compaction: deferred to later

  coordination:
    # ... existing coordination config
```

## Risks / Trade-offs

### Risk: Context Loss During Compaction
**Mitigation:** Preserve critical context markers, allow users to pin important messages.

### Risk: Approval Modal Friction
**Mitigation:** Make it optional via config, provide keyboard shortcut to approve quickly.

### Risk: Agent Confusion About Role
**Mitigation:** Clear system prompt differentiating interactive agent from coordination agents.

### Trade-off: One-Way Context Flow
**Accepted:** Simplifies v1, can add bidirectional callbacks later if needed.

### Risk: Token Cost Accumulation
**Mitigation (deferred):** Track costs separately for the interactive conversation and each `launch_run` call. Surface per-run costs in RunResult so the interactive agent can make cost-aware routing decisions. Add optional budget config later.

### Trade-off: No Parallel Runs
**Accepted:** Sequential runs are simpler, parallel orchestration is a v2 feature.

## Migration Plan

1. Interactive mode is opt-in via config (default: disabled initially)
2. Existing configs continue to work unchanged
3. Add example configs showing interactive mode usage
4. Document migration path for users wanting interactive mode

### Decision 8: Launch Run Reuses Subagent Infrastructure
**Choice:** `launch_run` reuses the existing subagent infrastructure (SubagentManager, SubagentScreen/SubagentCard TUI). A subagent already IS a full MassGen orchestrator run (multi-agent coordination with voting), so `launch_run` is conceptually identical.

**Why:** The subagent system already:
- Spawns full orchestrators (not single-agent workers)
- Provides inline SubagentCard + expandable SubagentScreen with full TUI parity
- Handles workspace isolation, event streaming, and result collection
- Supports async and blocking execution modes

**What differs for interactive mode:**
- Called from the interactive conversation layer instead of a coordination agent
- Different tool name/schema (`launch_run` vs `spawn_subagents`) with interactive-specific parameters (agent_mode, refinement, planning_mode)
- Label framing: "Run: <task>" instead of "Subagent: <task>"
- Results flow back to interactive agent's conversation context

**Implementation:** `launch_run` wraps SubagentManager with interactive-mode-specific parameter mapping.

### Decision 9: Project Workspace Structure
**Choice:** Per-project directories with CONTEXT.md, filepaths.json, runs/, and deliverables/

**Why:** Provides structured context management across multiple runs. The interactive agent can reference project context when launching runs, and deliverables/ serves as the source of truth for outputs (since interactive agent may update files post-run).

**Key design choices:**
- `filepaths.json` tracks files AND directories (context paths, not exhaustive file lists)
- `run_description.json` in runs/ rather than symlinked logdirs (more portable, explicit)
- `deliverables/` is the source of truth, not the most recent run workspace
- For long projects, starting a new run with fresh context may be better than continuing a stale session

**Alternatives considered:**
- Flat workspace: Too unstructured for multi-project use
- Symlinked logdirs: Less portable, harder to describe

## Open Questions

1. **Should interactive mode be default in future versions?** - Deferred, gather user feedback first
2. **How should workspace directories be structured?** - Proposed structure in implementation plan, may evolve
3. **What level of context should be passed to runs?** - Start with full context, add filtering if needed
4. **Should we switch subagent calling to be more like launch_run?** - Deferred, gather user feedback first after this spec is implemented
