# Observability

## ADDED Requirements

### Requirement: Round Context Logging

The system SHALL log comprehensive round context to enable workflow analysis, including the agent's intent and what answers were available for reference.

#### Scenario: Round intent logged
- **GIVEN** an agent starts a new round
- **WHEN** the round context is logged
- **THEN** the Logfire span SHALL include `massgen.round.intent` with up to 200 characters describing what the agent was asked to do

#### Scenario: Available answers logged
- **GIVEN** an agent starts a round with other agents' answers available
- **WHEN** the round context is logged
- **THEN** the Logfire span SHALL include:
  - `massgen.round.available_answers` with a JSON array of answer labels
  - `massgen.round.available_answer_count` with the number of answers
  - `massgen.round.answer_previews` with a JSON dict of truncated previews (100 chars each)

#### Scenario: No answers available
- **GIVEN** an agent starts a round with no other answers available
- **WHEN** the round context is logged
- **THEN** `massgen.round.available_answer_count` SHALL be 0

### Requirement: Vote Context Logging

The system SHALL log comprehensive vote context to enable analysis of voting behavior and answer selection.

#### Scenario: Full vote reason logged
- **GIVEN** an agent submits a vote with a reason
- **WHEN** the vote is logged
- **THEN** the Logfire span SHALL include `massgen.vote.reason` with up to 500 characters of the full voting reason

#### Scenario: Vote context details logged
- **GIVEN** an agent submits a vote
- **WHEN** the vote is logged
- **THEN** the Logfire span SHALL include:
  - `massgen.vote.agents_with_answers` with the count of agents who submitted answers
  - `massgen.vote.answer_label_mapping` with a JSON dict mapping labels to agent IDs

### Requirement: Agent Work Products Logging

The system SHALL log files created by agents to enable detection of repeated work and understanding of agent outputs.

#### Scenario: Files created logged
- **GIVEN** an agent has created files in its workspace
- **WHEN** the agent round completes
- **THEN** the Logfire event SHALL include:
  - `massgen.agent.files_created` with comma-separated filenames (max 50 files)
  - `massgen.agent.file_count` with the total number of files
  - `massgen.agent.workspace_path` with the path to the agent's workspace

#### Scenario: No files created
- **GIVEN** an agent has not created any files
- **WHEN** the agent round completes
- **THEN** `massgen.agent.file_count` SHALL be 0

### Requirement: Agent Restart Attribution

The system SHALL log restart events with the reason, trigger type, and triggering agent to Logfire.

#### Scenario: Restart logged with full context
- **GIVEN** an agent is restarted during coordination
- **WHEN** the restart is triggered
- **THEN** the Logfire event SHALL include:
  - `massgen.restart.reason` with up to 200 characters explaining why
  - `massgen.restart.trigger` with one of: "new_answer", "vote_change", "manual"
  - `massgen.restart.triggered_by_agent` with the agent ID that triggered the restart

#### Scenario: Restart trigger types
- **GIVEN** a restart is triggered by a new answer being submitted
- **WHEN** the restart event is logged
- **THEN** `massgen.restart.trigger` SHALL be "new_answer"

### Requirement: Subagent Task Logging

The system SHALL log the full subagent task description (up to 500 characters) as `massgen.subagent.task` when spawning subagents.

#### Scenario: Task logged on spawn
- **GIVEN** a parent agent spawns a subagent with a task description
- **WHEN** the subagent is spawned
- **THEN** the Logfire span SHALL include `massgen.subagent.task` with up to 500 characters of the task

#### Scenario: Long task truncated
- **GIVEN** a task description longer than 500 characters
- **WHEN** the subagent is spawned
- **THEN** the `massgen.subagent.task` attribute SHALL contain the first 500 characters

### Requirement: Subagent Files Tracking

The system SHALL log the files created by subagents when they complete, including a list of filenames and total count.

#### Scenario: Files logged on completion
- **GIVEN** a subagent has created files in its workspace
- **WHEN** the subagent completes (success or timeout with recovery)
- **THEN** the Logfire event SHALL include:
  - `massgen.subagent.files_created` with comma-separated filenames (max 50 files)
  - `massgen.subagent.file_count` with the total number of files

#### Scenario: No files created
- **GIVEN** a subagent has not created any files
- **WHEN** the subagent completes
- **THEN** the `massgen.subagent.file_count` SHALL be 0
- **AND** `massgen.subagent.files_created` SHALL be omitted or empty

### Requirement: Tool Error Context

The system SHALL log additional error context for failed tool executions when available.

#### Scenario: Error context logged
- **GIVEN** a tool execution fails with additional context
- **WHEN** the failure is logged
- **THEN** the Logfire event SHALL include `massgen.tool.error_context` with up to 500 characters of additional context

#### Scenario: No additional context
- **GIVEN** a tool execution fails without additional context
- **WHEN** the failure is logged
- **THEN** the `massgen.tool.error_context` attribute SHALL be omitted

### Requirement: Local File References

The system SHALL log paths to local files to enable seamless retrieval of full content when Logfire previews are insufficient.

#### Scenario: Run log path logged
- **GIVEN** a MassGen coordination session starts
- **WHEN** the session span is created
- **THEN** the Logfire span SHALL include `massgen.log_path` with the path to the run's log directory

#### Scenario: Agent log path logged
- **GIVEN** an agent starts a new round
- **WHEN** the round context is logged
- **THEN** the Logfire span SHALL include `massgen.agent.log_path` with the path to the agent's log directory

#### Scenario: Agent answer path logged
- **GIVEN** an agent submits an answer
- **WHEN** the answer is logged
- **THEN** the Logfire event SHALL include `massgen.agent.answer_path` with the path to the agent's answer file

#### Scenario: Subagent log path logged
- **GIVEN** a subagent is spawned
- **WHEN** the subagent spawn is logged
- **THEN** the Logfire span SHALL include `massgen.subagent.log_path` with the path to the subagent's log directory

#### Scenario: Subagent workspace path logged
- **GIVEN** a subagent completes execution
- **WHEN** the completion is logged
- **THEN** the Logfire event SHALL include `massgen.subagent.workspace_path` with the path to the subagent's workspace
