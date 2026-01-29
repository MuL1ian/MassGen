## ADDED Requirements

### Requirement: Unified Event Rendering Pipeline
The TUI SHALL render timeline content exclusively from MassGen events using a shared event-to-timeline adapter (ContentProcessor + TimelineSection) for both main and subagent views.

#### Scenario: Main and subagent views render identical output
- **WHEN** the main TUI and a subagent view are given the same ordered event sequence
- **THEN** both views render the same timeline cards and text content in the same order

#### Scenario: Live event streaming updates the timeline
- **WHEN** new events are emitted during an active run
- **THEN** the TUI updates the timeline without relying on raw stream parsing

### Requirement: Subagent View Parity
The subagent view SHALL use the same timeline rendering behavior and formatting as the main TUI for tools, thinking, status, and final answer content.

#### Scenario: Tool and thinking content match main TUI
- **WHEN** a subagent emits tool_start/tool_complete and thinking/text events
- **THEN** the subagent view displays the same tool cards and thinking/text styles as the main TUI

### Requirement: Subagent Inner-Agent Tabs
The subagent view SHALL display inner-agent tabs with agent_id and model name and allow cycling/filtering the timeline by inner agent.

#### Scenario: Inner-agent tabs render with model names
- **WHEN** execution metadata includes multiple inner agents with model names
- **THEN** the subagent view shows a tab for each inner agent with its name and model

#### Scenario: Selecting an inner agent filters timeline
- **WHEN** a user selects an inner-agent tab
- **THEN** the timeline updates to show only events for that agent
