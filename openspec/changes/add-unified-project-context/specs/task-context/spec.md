## ADDED Requirements

### Requirement: Task Context File Creation

Main agents SHALL create a `CONTEXT.md` file in their workspace before spawning subagents or using multimodal tools (read_media, generate_media).

The CONTEXT.md file SHALL contain task context:
- What we're building or doing
- Key terminology specific to the task
- Visual/brand guidelines if relevant
- Any other details tools/subagents need to understand the task

#### Scenario: Agent creates CONTEXT.md before spawning subagent
- **WHEN** an agent needs to spawn a subagent
- **THEN** the agent creates CONTEXT.md with task context first
- **AND** the subagent receives the context in its workspace

#### Scenario: Agent creates CONTEXT.md before using multimodal tools
- **WHEN** an agent needs to use read_media or generate_media
- **THEN** the agent creates CONTEXT.md with task context first
- **AND** the tool injects the context into external API calls

### Requirement: Task Context Loading

The system SHALL provide a `load_task_context(workspace_path)` function that:
- Reads `CONTEXT.md` from the workspace root
- Returns the file content as a string (max 10000 characters)
- Raises an error if the file does not exist

#### Scenario: CONTEXT.md exists
- **WHEN** `load_task_context()` is called
- **AND** CONTEXT.md exists in the workspace
- **THEN** the function returns the file content

#### Scenario: CONTEXT.md missing
- **WHEN** `load_task_context()` is called
- **AND** CONTEXT.md does not exist
- **THEN** the function raises an error with message guiding agent to create the file

### Requirement: Multimodal Tool Context Injection

Multimodal tools (understand_image, understand_audio, understand_video, understand_file, generate_image, generate_video, generate_audio) SHALL inject task context into external API calls.

The context SHALL be prepended to prompts using the format:
```
[Task Context]
{context}

[Request]
{original_prompt}
```

#### Scenario: Tool receives task context
- **WHEN** a multimodal tool makes an external API call
- **AND** task_context is available
- **THEN** the context is prepended to the prompt

#### Scenario: Tool fails without CONTEXT.md
- **WHEN** a multimodal tool is called
- **AND** CONTEXT.md does not exist in workspace
- **THEN** the tool returns an error guiding the agent to create CONTEXT.md

### Requirement: Subagent Context Inheritance

When spawning subagents, the system SHALL automatically copy `CONTEXT.md` from the parent workspace to the subagent workspace.

Subagents SHALL NOT create or modify CONTEXT.md (read-only access).

#### Scenario: CONTEXT.md auto-copied to subagent
- **WHEN** a subagent is spawned
- **AND** CONTEXT.md exists in parent workspace
- **THEN** CONTEXT.md is copied to subagent workspace

#### Scenario: Subagent spawning fails without CONTEXT.md
- **WHEN** spawn_subagents is called
- **AND** CONTEXT.md does not exist in parent workspace
- **THEN** the spawn fails with an error guiding the agent to create CONTEXT.md

### Requirement: System Prompt Instructions

The system message builder SHALL include instructions for main agents about:
- When to create CONTEXT.md (before multimodal tools or subagents)
- What to include (task context: what we're building, key terms, relevant details)
- Example CONTEXT.md content

#### Scenario: Agent receives CONTEXT.md instructions
- **WHEN** an agent's system message is built
- **AND** multimodal tools or subagents are available
- **THEN** instructions for CONTEXT.md creation are included

### Requirement: Context Truncation Warning

When CONTEXT.md exceeds the maximum character limit (10000 chars), the system SHALL return a warning in tool and subagent responses so agents can see when context was truncated.

The warning SHALL be included in:
- Multimodal tool response objects (e.g., `{"success": true, "warning": "..."}`)
- SubagentResult objects (accessible via `result.warning` field)

#### Scenario: Tool returns truncation warning
- **WHEN** a multimodal tool loads CONTEXT.md
- **AND** the file exceeds 10000 characters
- **THEN** the tool response includes a warning field with truncation details

#### Scenario: Subagent result includes truncation warning
- **WHEN** a subagent is spawned
- **AND** CONTEXT.md in workspace exceeds 10000 characters
- **THEN** the SubagentResult includes the warning field
- **AND** the warning is visible to the parent agent (not just logged)
