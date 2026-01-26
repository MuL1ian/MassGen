## ADDED Requirements

### Requirement: Async Subagent Spawning

The system SHALL provide non-blocking subagent execution via an `async` parameter on the existing `spawn_subagents` tool.

#### Scenario: Parent spawns async subagent and continues working
- **GIVEN** a parent agent with subagent tools enabled
- **WHEN** the parent calls `spawn_subagents` with `async=true`
- **THEN** the tool returns immediately with subagent IDs and "running" status
- **AND** the parent agent can continue executing other tools
- **AND** the subagent runs concurrently in the background

#### Scenario: Multiple async subagents spawned
- **GIVEN** a parent agent
- **WHEN** the parent spawns 3 subagents with `async=true`
- **THEN** all 3 subagents run concurrently (subject to `max_concurrent_subagents`)
- **AND** the parent receives IDs for all spawned subagents

#### Scenario: Default blocking behavior preserved
- **GIVEN** a parent agent with subagent tools enabled
- **WHEN** the parent calls `spawn_subagents` without the `async` parameter
- **THEN** the tool blocks until all subagents complete
- **AND** returns results directly (existing behavior)

### Requirement: Automatic Result Injection

The system SHALL automatically inject completed subagent results into the parent agent's conversation at the next tool boundary.

#### Scenario: Result injected after subagent completes
- **GIVEN** a parent agent with a running async subagent
- **WHEN** the subagent completes successfully
- **AND** the parent executes any tool
- **THEN** the subagent result is injected into the tool response
- **AND** the injection includes the subagent ID, status, answer, and execution metadata

#### Scenario: Multiple results batched
- **GIVEN** a parent agent with 3 running async subagents
- **WHEN** 2 subagents complete before the parent's next tool call
- **THEN** both results are injected together in a single batch
- **AND** results are ordered by completion time

#### Scenario: Timeout result injected
- **GIVEN** a parent agent with a running async subagent
- **WHEN** the subagent times out but has partial work
- **THEN** the partial result is injected with status "completed_but_timeout" or "partial"
- **AND** the injection includes whatever answer was recovered

### Requirement: Injection Strategy Configuration

The system SHALL support configurable injection strategies to control how results are delivered to the parent agent.

#### Scenario: Tool result injection strategy (default)
- **GIVEN** `async_subagents.injection_strategy: "tool_result"` in config
- **WHEN** a subagent result is injected
- **THEN** the result is appended to the current tool's response
- **AND** prompt cache is preserved where possible

#### Scenario: User message injection strategy
- **GIVEN** `async_subagents.injection_strategy: "user_message"` in config
- **WHEN** a subagent result is injected
- **THEN** the result is added as a follow-up user message
- **AND** the agent explicitly processes the result as new input

### Requirement: Result Format

The system SHALL format injected results in a structured, parseable format with relevant metadata.

#### Scenario: Successful result format
- **WHEN** a completed subagent result is injected
- **THEN** the format includes:
  - Subagent ID and status in XML-like tags
  - The subagent's full answer
  - Execution time and token usage
  - Workspace path for accessing additional artifacts

### Requirement: Explicit Result Polling

The system SHALL provide a tool for agents to explicitly check subagent status and retrieve results.

#### Scenario: Check all subagent results
- **WHEN** the parent calls `check_subagent_results()`
- **THEN** the tool returns:
  - List of completed results (not yet injected)
  - Count of still-running subagents
  - Count of pending (queued) subagents

#### Scenario: Check specific subagent status
- **WHEN** the parent calls `check_subagent_status(subagent_id)`
- **THEN** the tool returns the subagent's current status
- **AND** if completed, includes the result
- **AND** if running, includes progress information if available

### Requirement: Graceful Session Completion

The system SHALL handle pending subagent results when the parent session completes.

#### Scenario: Pending results injected before session ends
- **GIVEN** a parent agent with pending (completed but not injected) subagent results
- **WHEN** the parent is about to produce its final response
- **THEN** all pending results are injected before the final response
- **AND** the parent has opportunity to incorporate them

#### Scenario: Running subagents when parent completes
- **GIVEN** a parent agent with still-running async subagents
- **WHEN** the parent session completes
- **THEN** running subagents are allowed to complete (not forcibly cancelled)
- **AND** a warning is logged about orphaned subagent results

### Requirement: Async Subagent Configuration

The system SHALL support YAML configuration for async subagent behavior.

#### Scenario: Enable async subagents
- **GIVEN** the following config:
  ```yaml
  orchestrator:
    coordination:
      async_subagents:
        enabled: true
        injection_strategy: "tool_result"
  ```
- **WHEN** an agent spawns a subagent with `async=true`
- **THEN** the subagent runs in background mode
- **AND** results are injected per the configured strategy

#### Scenario: Disable async subagents
- **GIVEN** `async_subagents.enabled: false` in config
- **WHEN** an agent calls `spawn_subagents` with `async=true`
- **THEN** the tool falls back to blocking behavior
- **AND** a warning is logged about async being disabled
