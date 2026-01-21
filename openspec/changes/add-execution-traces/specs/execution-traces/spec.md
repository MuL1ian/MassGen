# Execution Traces Specification

## ADDED Requirements

### Requirement: Execution Trace File Format

The system SHALL persist agent execution history as a structured markdown file (`execution_trace.md`) that is human-readable and grep-friendly.

The trace file SHALL contain:
- Metadata header with agent ID, model, and start timestamp
- Round sections labeled by answer number (e.g., "Round 1 (Answer 1.1)")
- Tool calls with full arguments (no truncation)
- Tool results with full output (no truncation)
- Reasoning/thinking blocks when present
- Error entries with timestamps

#### Scenario: Basic trace file structure
- **GIVEN** an agent has executed tool calls during a round
- **WHEN** the execution trace is saved
- **THEN** the file contains a metadata header with agent_id, model, and timestamp
- **AND** the file contains round sections with tool call and result entries
- **AND** all content is preserved without truncation

#### Scenario: Tool call formatting
- **GIVEN** an agent calls a tool with arguments `{"file_path": "/workspace/main.py"}`
- **WHEN** the trace records the tool call
- **THEN** the entry shows the tool name and full JSON arguments
- **AND** the format is searchable (e.g., grep for tool name finds the entry)

#### Scenario: Error tracking
- **GIVEN** a tool execution fails with an error
- **WHEN** the trace records the result
- **THEN** the entry is marked as an error
- **AND** the error message is preserved in full

#### Scenario: Reasoning content
- **GIVEN** an agent produces reasoning/thinking content
- **WHEN** the trace records the reasoning
- **THEN** the content appears in a dedicated "Reasoning" section
- **AND** the full reasoning is preserved without truncation

---

### Requirement: Trace Persistence with Snapshots

The system SHALL save the execution trace file alongside other snapshot files when an agent submits an answer or vote.

#### Scenario: Trace saved on answer submission
- **GIVEN** an agent submits a new answer
- **WHEN** the orchestrator saves the agent snapshot
- **THEN** `execution_trace.md` is saved in the timestamped snapshot directory
- **AND** the trace contains all tool calls from the current round

#### Scenario: Trace available in temp workspace
- **GIVEN** agent snapshots are copied to temp workspaces for coordination
- **WHEN** another agent accesses the temp workspace
- **THEN** the `execution_trace.md` file is present
- **AND** the file can be read to understand the other agent's approach

---

### Requirement: Compression Recovery Reference

The system SHALL reference the execution trace file in compression recovery messages so agents can recover detailed history.

#### Scenario: Trace reference in compression recovery
- **GIVEN** an agent's context is compressed due to length limits
- **WHEN** the compression recovery message is generated
- **THEN** the message mentions `execution_trace.md` as a source of detailed history
- **AND** the message instructs the agent to read the file if details are needed

---

### Requirement: Cross-Agent Trace Access

The system SHALL make other agents' execution traces accessible during coordination by including trace file references in context injection.

#### Scenario: Trace mention in context injection
- **GIVEN** agent2 receives context about agent1's answer
- **WHEN** the context injection message is built
- **THEN** the message mentions that `execution_trace.md` is available
- **AND** the agent can read the file to understand how agent1 arrived at their answer
