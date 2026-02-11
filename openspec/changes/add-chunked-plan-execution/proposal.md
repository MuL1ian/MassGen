# Change: Add Planner-Defined Chunked Plan Execution and Iterative Planning Review (MAS-277)

## Why

Long plans are currently executed in a single run, which makes execution brittle, hard to monitor, and difficult to resume safely after interruption.

MAS-277 requires turn-based chunked execution with clear progress visibility, graceful stop behavior, and resumable checkpoints.

In addition, the current planning approval modal is too limited for real planning workflows: plans are hard to browse, iteration is awkward, and there is no clear “keep refining plan vs finalize and execute” loop. We need a planning-first review experience before execution starts.

## What Changes

### Planning Artifact Contract
- Require every task in `project_plan.json` to include a `chunk` field.
- Validate chunk metadata before execution starts.

### Planning Review and Iteration UX (TUI)
- Replace minimal plan approval experience with a richer planning review modal.
- Show plans grouped by chunk with clear status/progress context.
- Keep users in planning mode after initial plan generation with explicit actions:
  - `Continue Planning` (default multi-agent planning refinement turn)
  - `Quick Edit` (single-agent planning refinement turn for smaller changes)
  - `Finalize Plan and Execute`
- Re-open review modal after each planning refinement turn with updated plan revision.

### Execution Model
- Make chunked execution the default behavior for:
  - `--plan-and-execute`
  - `--execute-plan`
  - TUI execute mode
- Execute one chunk at a time.
- For each chunk run, write a chunk-only simplified `tasks/plan.json` for operational scope.
- Keep the full frozen plan mounted as read-only context for reference.

### Progress, Stop, and Resume
- Persist per-chunk checkpoint metadata and history.
- Support graceful stop at safe boundaries.
- Mark interrupted sessions as resumable.
- Resume defaults to latest resumable plan session.

### TUI Execute UX
- Add execute popover chunk browser showing:
  - current chunk
  - next chunk
  - per-chunk progress/state
- Allow click-to-prefill chunk selection and range selection (`bottom-top`) in input.

### Explicitly Out of Scope
- Interactive `launch_run` chained orchestration changes
- Dynamic chunk derivation fallback when `chunk` is missing
- Fixed-size chunk execution policy options
- Full manual JSON task editing in modal (this change uses planning refinement turns instead)

## Impact

- Affected specs: `plan-execution` (new capability)
- Affected code:
  - `massgen/cli.py`
  - `massgen/plan_execution.py`
  - `massgen/plan_storage.py`
  - `massgen/frontend/displays/textual_widgets/plan_approval_modal.py`
  - `massgen/frontend/displays/textual_widgets/plan_options.py`
  - `massgen/frontend/displays/textual_terminal_display.py`
  - related tests under `massgen/tests/` and `massgen/tests/frontend/`
