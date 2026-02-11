## ADDED Requirements

### Requirement: Planner SHALL Emit Chunk-Labeled Tasks

The planning artifact SHALL include a `chunk` field on every task in `project_plan.json`.

#### Scenario: Planning output includes chunk labels
- **WHEN** a planning run produces `project_plan.json`
- **THEN** every task SHALL include a non-empty `chunk` string
- **AND** chunk ordering SHALL be deterministic for execution

#### Scenario: Missing chunk metadata blocks execution
- **WHEN** any task in the plan is missing `chunk`
- **THEN** plan execution SHALL fail fast before execution begins
- **AND** the error SHALL identify the invalid task(s)

### Requirement: TUI SHALL Provide Structured Planning Review Modal

After a planning run, the system SHALL provide a rich plan review modal before execution.

#### Scenario: Planning modal supports chunk-first browsing
- **WHEN** a plan is produced in TUI planning mode
- **THEN** the modal SHALL display tasks grouped by chunk
- **AND** it SHALL expose enough detail to browse plan scope without leaving the modal

#### Scenario: Planning modal supports iterative action routing
- **WHEN** the modal is shown
- **THEN** it SHALL offer actions for `Continue Planning`, `Quick Edit`, and `Finalize Plan and Execute`

### Requirement: Planning Mode SHALL Support Iterative Refinement Before Execution

The system SHALL allow multiple planning turns before finalizing into execution.

#### Scenario: Continue Planning keeps user in planning loop
- **WHEN** user selects `Continue Planning`
- **THEN** the system SHALL run another planning turn
- **AND** return to plan review modal with updated plan revision

#### Scenario: Quick Edit uses single-agent planning turn
- **WHEN** user selects `Quick Edit`
- **THEN** the system SHALL run planning refinement in single-agent mode
- **AND** return to plan review modal with updated plan revision

#### Scenario: Finalize transitions from planning to execution
- **WHEN** user selects `Finalize Plan and Execute`
- **THEN** the latest reviewed plan SHALL be frozen for execution
- **AND** system mode SHALL transition to chunked execution

### Requirement: Plan Execution SHALL Run Chunk-by-Chunk

In plan execution modes, the system SHALL execute one chunk at a time using planner-defined chunk metadata.

#### Scenario: Active execution scope is chunk-only
- **WHEN** execution begins for an active chunk
- **THEN** the operational `tasks/plan.json` SHALL contain only tasks for that chunk
- **AND** the full frozen plan SHALL remain available as read-only context

#### Scenario: Chunk progression is sequential
- **WHEN** an active chunk is completed
- **THEN** execution SHALL advance to the next pending chunk in deterministic order
- **AND** it SHALL NOT execute future chunks before their turn

### Requirement: System SHALL Persist Chunk Progress and Checkpoints

The system SHALL persist chunk-level execution state and checkpoints for observability and recovery.

#### Scenario: Chunk completion writes checkpoint metadata
- **WHEN** a chunk finishes execution
- **THEN** chunk status, timing, and retry information SHALL be persisted
- **AND** completed chunk state SHALL be available for later resume/reporting

#### Scenario: Progress visibility includes current and next chunk
- **WHEN** execution is in progress
- **THEN** runtime state SHALL expose the current active chunk and next pending chunk
- **AND** chunk completion status SHALL be queryable for UI display

### Requirement: System SHALL Support Graceful Stop and Resume

Chunk execution SHALL support graceful interruption with resumable continuation.

#### Scenario: Graceful stop marks session resumable
- **WHEN** a stop/cancel is requested during chunk execution
- **THEN** execution SHALL stop at a safe boundary
- **AND** the session SHALL be marked resumable with the latest checkpoint

#### Scenario: Resume continues from correct boundary
- **WHEN** a resumable session is resumed
- **THEN** the system SHALL continue the current incomplete chunk
- **AND** if the current chunk is already complete, it SHALL continue from the next pending chunk

#### Scenario: Default resume target uses latest resumable session
- **WHEN** user enters execute/resume flow without explicitly choosing a session
- **THEN** the system SHALL default to the latest resumable plan session

### Requirement: TUI Execute Mode SHALL Provide Chunk Browser and Prefill Controls

The TUI execute popover SHALL provide chunk-level visibility and fast selection controls.

#### Scenario: Chunk browser displays execution position
- **WHEN** execute mode is opened in TUI
- **THEN** the popover SHALL display chunk list with status/progress
- **AND** it SHALL indicate current active chunk and next chunk

#### Scenario: Clicking chunk pre-fills execute input
- **WHEN** a user clicks a chunk entry in the execute popover
- **THEN** the execute input SHALL be pre-filled with that chunk selection

#### Scenario: Range selection prefill is supported
- **WHEN** a user selects a `bottom-top` range in execute popover controls
- **THEN** the execute input SHALL be pre-filled with the corresponding chunk range selection
