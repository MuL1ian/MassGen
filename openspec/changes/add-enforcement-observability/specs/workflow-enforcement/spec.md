# Workflow Enforcement Observability

## ADDED Requirements

### Requirement: Enforcement Event Tracking
The system SHALL track all workflow enforcement events per agent in status.json with round-level granularity.

#### Scenario: Unknown tool triggers enforcement tracking
- **WHEN** an agent calls an unknown tool (e.g., `execute_command`)
- **AND** the system triggers a workflow enforcement restart
- **THEN** status.json SHALL contain a `reliability.enforcement_attempts` entry with:
  - `round`: the current round number
  - `attempt`: the attempt number within the round
  - `reason`: "unknown_tool"
  - `tool_calls`: ["execute_command"]
  - `buffer_preview`: first 500 chars of streaming buffer content
  - `timestamp`: Unix timestamp

#### Scenario: Invalid vote ID triggers enforcement tracking
- **WHEN** an agent votes for an invalid agent_id (e.g., "agent5" when only agent1/agent2 exist)
- **AND** the system triggers a workflow enforcement restart
- **THEN** status.json SHALL contain a `reliability.enforcement_attempts` entry with:
  - `reason`: "invalid_vote_id"
  - `error_message`: "Invalid agent_id 'agent5'. Valid agents: agent1, agent2"

#### Scenario: Multiple enforcement attempts tracked per round
- **WHEN** an agent triggers multiple enforcement restarts in a single round
- **THEN** status.json SHALL contain multiple entries in `reliability.enforcement_attempts`
- **AND** `reliability.by_round` SHALL aggregate counts per round

### Requirement: Enforcement Reason Categories
The system SHALL categorize enforcement events using these reason codes:
- `no_workflow_tool`: Called tools but none were workflow tools
- `no_tool_calls`: Text-only response, no tools called
- `invalid_vote_id`: Vote with invalid agent_id
- `vote_no_answers`: Vote when no answers exist
- `vote_and_answer`: Both vote and new_answer in same response
- `answer_limit`: Hit answer count limit
- `answer_novelty`: Answer too similar to existing
- `answer_duplicate`: Exact duplicate of existing answer
- `unknown_tool`: Called tool that doesn't exist

#### Scenario: Each enforcement point uses correct reason code
- **WHEN** workflow enforcement is triggered at any of the 8 enforcement points
- **THEN** the tracking event SHALL use the corresponding reason code from the category list

### Requirement: Buffer Preservation on Enforcement Restart
The system SHALL capture streaming buffer content before enforcement restart.

#### Scenario: Buffer content captured before restart
- **WHEN** workflow enforcement triggers a restart (new `agent.chat()` call)
- **THEN** the system SHALL first capture the current streaming buffer content
- **AND** store a truncated preview (first 500 chars) in `buffer_preview`
- **AND** store the full character count in tracking for `total_buffer_chars_lost` metric

### Requirement: Improved Enforcement Messages
The system SHALL provide clear retry counts and context in user-visible enforcement messages.

#### Scenario: Enforcement message includes retry count
- **WHEN** enforcement is triggered for an unknown tool on attempt 1 of 3
- **THEN** the user-visible message SHALL be formatted as: `Retry (1/3): Called execute_command (not workflow). Required: vote or new_answer`

#### Scenario: Invalid vote message includes valid options
- **WHEN** enforcement is triggered for an invalid vote ID
- **THEN** the user-visible message SHALL include the list of valid agent IDs

### Requirement: Status.json Reliability Structure
The system SHALL include a `reliability` field in each agent's status entry with the following structure:
- `enforcement_attempts`: List of enforcement event records
- `by_round`: Aggregated counts per round
- `unknown_tools`: List of unknown tool names encountered
- `workflow_errors`: List of workflow error types encountered
- `total_enforcement_retries`: Total count of retries
- `total_buffer_chars_lost`: Total characters lost from buffer clears
- `outcome`: Final outcome ("ok", "non_compliant", "dropped")

#### Scenario: Status.json includes reliability data after run
- **WHEN** a MassGen run completes
- **AND** at least one agent triggered enforcement
- **THEN** status.json SHALL contain the `reliability` field for that agent
- **AND** the field SHALL contain all enforcement events that occurred
