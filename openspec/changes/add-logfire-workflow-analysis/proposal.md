# Change: Add Logfire Attributes for Workflow Analysis

## Why

When analyzing MassGen runs, we need to explain agent behavior in natural language: "What was the agent doing in round 1?", "Did agent_a see agent_b's answer when voting?", "Is agent_a repeating work?". Currently, Logfire lacks the context needed for this analysis - key data exists only in local log files.

**Hybrid approach**: Logfire should provide enough context to understand what happened (previews, counts, paths), while local logs provide full details (complete answers, full workspaces). Logfire attributes include paths that enable seamless local retrieval when full details are needed.

Gap analysis shows:
- Agent round intent (what agent was asked to do) - NOT in Logfire
- Available answers in context - Only labels, no previews
- Full vote reason - Truncated to ~100 chars
- Files created by agent - NOT logged
- Restart reason - NOT logged
- Answer label mappings (agent1.1 → agent_a) - NOT logged
- Local file paths - NOT logged (can't retrieve full content)

## What Changes

### 1. Round Context (for workflow explanation)
- `massgen.round.intent` - What the agent was asked to do (200 chars)
- `massgen.round.available_answers` - Answer labels available for reference (JSON array)
- `massgen.round.available_answer_count` - Number of answers agent could see
- `massgen.round.answer_previews` - Truncated previews of each answer (JSON dict, 100 chars each)

### 2. Vote Context (for analyzing voting behavior)
- `massgen.vote.reason` - Full voting reason (500 chars, up from ~100)
- `massgen.vote.agents_with_answers` - Count of agents who submitted answers
- `massgen.vote.answer_label_mapping` - Map of labels to agent IDs (JSON dict)

### 3. Agent Work Products (for detecting repeated work)
- `massgen.agent.files_created` - List of filenames created (50 files max)
- `massgen.agent.file_count` - Total files in workspace

### 4. Restart Context (for understanding interruptions)
- `massgen.restart.reason` - Why the agent was restarted (200 chars)
- `massgen.restart.trigger` - Trigger type: new_answer, vote_change, manual
- `massgen.restart.triggered_by_agent` - Which agent's action triggered restart

### 5. Subagent Enhancements
- `massgen.subagent.task` - Full task description (500 chars, up from 200)
- `massgen.subagent.files_created` - Files created by subagent
- `massgen.subagent.file_count` - Files in subagent workspace

### 6. Tool Error Context
- `massgen.tool.error_context` - Additional failure context (500 chars)

### 7. Local File References (for hybrid access)
- `massgen.log_path` - Path to the run's log directory
- `massgen.agent.log_path` - Path to agent's log directory (for full context.txt, vote.json)
- `massgen.agent.answer_path` - Path to agent's answer file (for full answer content)
- `massgen.subagent.log_path` - Path to subagent's log directory
- `massgen.subagent.workspace_path` - Path to subagent's workspace

**Usage pattern**: When Logfire shows a truncated preview, use the corresponding path attribute to read the full content locally.

## Impact

- **Affected code**:
  - `massgen/structured_logging.py` - Logging functions
  - `massgen/structured_logging_utils.py` - Constants
  - `massgen/orchestrator.py` - Restart logging, context passing, path tracking
  - `massgen/coordination_tracker.py` - Track answers_in_context
  - `massgen/subagent/manager.py` - Files tracking, path logging
  - `massgen/tool/_manager.py` - Error context
  - `massgen/skills/massgen-log-analyzer/SKILL.md` - New analysis queries
- **Affected specs**: New `observability` capability
- **Backward compatibility**: Additive only, no breaking changes
- **Risk**: Low - adds attributes without changing behavior

## References

- Linear: [MAS-199](https://linear.app/massgen-ai/issue/MAS-199)
