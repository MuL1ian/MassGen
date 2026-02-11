## 1. Planning Contract and Validation

- [x] 1.1 Update planning prompt contract to require `chunk` on every task in `project_plan.json`
- [x] 1.2 Add plan validation that fails execution when any task is missing `chunk`
- [x] 1.3 Add validation for deterministic chunk ordering/dependency consistency
- [x] 1.4 Add/adjust tests for chunk metadata validation failures and success cases

## 2. Planning Review Loop (TUI)

- [x] 2.1 Redesign planning modal for chunk-grouped browsing and clearer task visibility
- [x] 2.2 Add `Continue Planning` action that runs another planning turn (multi-agent)
- [x] 2.3 Add `Quick Edit` action that runs planning refinement in single-agent mode
- [x] 2.4 Add `Finalize Plan and Execute` action that transitions to execution mode using latest revision
- [x] 2.5 Persist planning revision/iteration metadata and feedback history
- [x] 2.6 Add frontend tests for modal rendering, browsing, and action routing

## 3. Chunked Execution Engine

- [x] 3.1 Refactor plan execution loop to run one chunk per execution turn
- [x] 3.2 Generate chunk-only simplified `tasks/plan.json` for active chunk
- [x] 3.3 Preserve full frozen plan as read-only reference context during chunk runs
- [x] 3.4 Add chunk guardrails (completion/progress/retry budget)
- [x] 3.5 Persist chunk history and checkpoint metadata per chunk
- [x] 3.6 Add/adjust integration tests for chunk-by-chunk progression

## 4. Stop and Resume

- [x] 4.1 Implement graceful stop behavior at safe boundaries for chunk execution
- [x] 4.2 Persist resumable state when interrupted
- [x] 4.3 Implement resume selection defaulting to latest resumable session
- [x] 4.4 Implement resume behavior: continue incomplete current chunk; otherwise advance to next pending chunk
- [x] 4.5 Add tests for graceful stop, resumable marking, and resume correctness

## 5. TUI Execute Experience

- [x] 5.1 Add chunk browser UI to execute popover (current/next/status/progress)
- [x] 5.2 Add click-to-prefill chunk selection from chunk browser
- [x] 5.3 Add range selection prefill (`bottom-top`) in execute popover controls
- [x] 5.4 Surface chunk progress in execute mode state/UI updates
- [x] 5.5 Add frontend tests for chunk browser rendering and prefill behavior

## 6. Verification

- [x] 6.1 Run targeted unit tests for plan validation and chunk sequencing
- [x] 6.2 Run targeted integration tests for planning-review + execution flow parity
- [x] 6.3 Run OpenSpec strict validation for this change
