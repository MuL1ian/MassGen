## Context

The current plan execution path loads the full plan into `tasks/plan.json` and asks agents to execute everything in one run. This does not provide clear boundaries for execution scope, progress checkpoints, or deterministic resume behavior.

MAS-277 requires plan execution to support chunked progress with stop/resume. Product direction for this change is to keep runtime logic simple by shifting chunk definition responsibility to planning output.

Separately, current plan review UX is too shallow for iterative planning. Users need to browse chunk structure, provide quick feedback, run follow-up planning turns, and explicitly finalize into execution.

## Goals / Non-Goals

### Goals
- Always run plan execution chunk-by-chunk for plan execution modes.
- Make planning output declare chunk boundaries explicitly via task metadata.
- Provide deterministic execution order and progress tracking.
- Support graceful stop and resume with persisted checkpoints.
- Improve TUI execute-mode visibility and control of chunk progression.
- Provide a planning review loop in TUI so planning can continue for multiple turns before execution.

### Non-Goals
- Redesign interactive-mode `launch_run` orchestration.
- Introduce runtime AI-based chunk derivation fallback.
- Add fixed-size chunking configuration in this change.
- Implement full manual task JSON editing in modal UI.

## Decisions

### Decision: Chunk Source = Planner Metadata
Execution consumes `task.chunk` labels authored in `project_plan.json`.

Rationale:
- keeps execution deterministic
- avoids ambiguity in runtime partitioning
- allows planner to align chunk boundaries with dependency and verification intent

### Decision: Execution Scope = Chunk-Only Plan File
For each chunk run, operational `tasks/plan.json` includes only active chunk tasks.

Rationale:
- removes accidental execution of future chunks
- keeps MCP planning tools focused on current scope

Tradeoff:
- full-plan references remain needed for context. Mitigated by read-only frozen plan context mount.

### Decision: Full Plan Remains Read-Only Context
Frozen full plan is always available as reference context during chunk execution.

Rationale:
- preserves global intent and documentation continuity
- allows supporting docs to reference total roadmap without widening execution scope

### Decision: Stop/Resume at Safe Boundaries
Execution stops gracefully at tool/turn boundaries, then checkpoints. Resume restarts from current incomplete chunk, or next pending chunk if current is already complete.

Rationale:
- minimizes state ambiguity
- aligns with expected turn-based workflow

### Decision: Iterative Planning Happens Before Finalize
After initial plan generation in TUI, users stay in planning mode and choose between:
- continuing planning refinement (multi-agent)
- quick-edit refinement (single-agent)
- finalizing plan and entering execution

Rationale:
- planning quality usually benefits from 1+ review/refinement turns
- avoids forcing premature execution
- gives a lightweight path for small plan edits

### Decision: Small Plan Edits Use Single-Agent Refinement Turn
Quick edits are implemented as a single-agent planning turn, not manual JSON editing.

Rationale:
- keeps plan generation and consistency in LLM workflow
- avoids high-risk manual graph/chunk metadata corruption
- lower implementation complexity than full in-modal editor

## ASCII Diagrams

### End-to-End Flow

```text
User Task
   |
   v
[Plan Mode Turn #1]
   |
   v
[Planning Review Modal]
   |-------------------------------|-------------------------------|
   v                               v                               v
Continue Planning              Quick Edit                      Finalize + Execute
(multi-agent turn)             (single-agent turn)             (freeze latest plan)
   |                               |                               |
   v                               v                               v
[Plan Mode Turn #N]            [Plan Mode Turn #N]          [Chunked Execution Loop]
   |                               |                               |
   +-------------> [Planning Review Modal] <-----------------------+
```

### Planning State Machine (TUI)

```text
NORMAL
  |
  | toggle plan
  v
PLANNING_ACTIVE
  |
  | planning turn completes with plan artifact
  v
PLAN_REVIEW_READY
  |  continue planning  -> PLANNING_ACTIVE (multi-agent)
  |  quick edit         -> PLANNING_ACTIVE (single-agent)
  |  finalize           -> EXECUTION_ACTIVE
  |  cancel             -> NORMAL
  v
EXECUTION_ACTIVE
  | stop/cancel (graceful checkpoint)
  v
EXECUTION_RESUMABLE
  | resume
  v
EXECUTION_ACTIVE
```

### Chunk Execution Loop

```text
[Select Active Chunk] -> [Write chunk-only tasks/plan.json] -> [Run execution turn]
          |                                                  |
          |<--------------- guardrails + checkpoint ---------|
                              |
                              +--> complete chunk -> next chunk
                              +--> stop requested -> resumable checkpoint
                              +--> no-progress retry budget exhausted -> fail
```

## Data Model Additions

### Planning Task Schema
Each task must include:
- `chunk: string`

Recommended convention:
- ordered chunk labels (e.g., `C01_foundation`, `C02_backend`)

### Plan Session Metadata
Add planning review fields:
- `plan_revision: int`
- `planning_iteration_count: int`
- `planning_feedback_history: []`
- `last_planning_mode: "multi" | "single"`

Add resumable/chunk execution fields:
- `execution_mode: "chunked_by_planner_v1"`
- `current_chunk: string | null`
- `completed_chunks: string[]`
- `chunk_history: []` with per-chunk start/end/status/retries
- `resumable_state` checkpoint pointer

## Planning Review Flow

1. Planning turn generates/updates `project_plan.json`.
2. TUI opens planning review modal.
3. Modal presents chunk-grouped plan summary and task browse view.
4. User chooses:
   - Continue Planning (multi-agent planning turn)
   - Quick Edit (single-agent planning turn)
   - Finalize Plan and Execute
5. For planning actions, run planning turn and return to step 2 with incremented revision.
6. For finalize action, freeze latest plan and transition to execution mode.

## Execution Flow

1. Validate frozen plan has chunk labels for all tasks.
2. Build deterministic chunk order (first appearance order, with optional label-order checks).
3. Select active chunk.
4. Generate chunk-only `tasks/plan.json`.
5. Run one execution turn scoped to active chunk.
6. Evaluate chunk guardrails (completion/progress/retry limits).
7. Persist checkpoint and chunk history.
8. Continue to next chunk or mark resumable/failed/completed.

## TUI Flow

1. Execute popover reads chunk progression state.
2. Chunk browser shows current/next/completed/failed chunks.
3. Clicking a chunk prefills selection input.
4. Range (`bottom-top`) prefill supports multi-chunk intent preview.
5. Resume action defaults to latest resumable plan session.

## Risks / Trade-offs

- Risk: Planner omits or mislabels chunk metadata.
  - Mitigation: strict validation before execution.

- Risk: Supporting docs describe whole-plan behavior while runtime scope is chunk-only.
  - Mitigation: explicit prompt instructions that full plan is reference, chunk plan is execution scope.

- Risk: Resume ambiguity if interrupted mid-step.
  - Mitigation: graceful-stop boundary policy and checkpoint timestamps.

- Risk: Too many planning loops may increase cost/latency.
  - Mitigation: default action remains explicit and users can finalize at any review step.

## Migration Plan

1. Ship chunk-aware validation and execution metadata without removing existing fields.
2. Enable chunked execution in plan execution modes.
3. Add planning review loop UX in TUI.
4. Add TUI chunk browser and resume defaults.
5. Keep backward-compatible error messaging for legacy plans lacking `chunk`.

## Open Questions

- None for MAS-277 scope after alignment decisions in this spec.
