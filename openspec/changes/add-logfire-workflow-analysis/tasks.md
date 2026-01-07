# Tasks: Add Logfire Workflow Analysis Attributes

## 1. Constants and Utilities
- [x] 1.1 Add `PREVIEW_ROUND_INTENT = 200` to structured_logging_utils.py
- [x] 1.2 Add `PREVIEW_ANSWER_EACH = 100` to structured_logging_utils.py
- [x] 1.3 Add `PREVIEW_VOTE_REASON = 500` to structured_logging_utils.py
- [x] 1.4 Add `MAX_FILES_CREATED = 50` to structured_logging_utils.py
- [x] 1.5 Add `PREVIEW_RESTART_REASON = 200` to structured_logging_utils.py
- [x] 1.6 Add `PREVIEW_SUBAGENT_TASK = 500` to structured_logging_utils.py
- [x] 1.7 Add `PREVIEW_ERROR_CONTEXT = 500` to structured_logging_utils.py

## 2. Round Context Logging
- [x] 2.1 Update `log_agent_round_context()` - add `round_intent` param
- [x] 2.2 Add `available_answers` and `available_answer_count` params
- [x] 2.3 Add `answer_previews` param (dict with 100 char previews)
- [x] 2.4 Update orchestrator to pass round context data

## 3. Vote Context Logging
- [x] 3.1 Update `log_agent_vote()` - extend `reason` to 500 chars
- [x] 3.2 Add `agents_with_answers` count param
- [x] 3.3 Add `answer_label_mapping` dict param
- [x] 3.4 Update vote handling to pass full context

## 4. Agent Work Products Logging
- [x] 4.1 Add `log_agent_workspace_files()` function
- [x] 4.2 Call from orchestrator after agent round completes
- [x] 4.3 Include `workspace_path` attribute

## 5. Restart Logging
- [x] 5.1 Add `log_agent_restart()` function to structured_logging.py
- [x] 5.2 Add `triggered_by_agent` param
- [x] 5.3 Call from orchestrator restart handling (~line 2822)

## 6. Subagent Logging Enhancements
- [x] 6.1 Update `trace_subagent_execution()` - extend task to 500 chars
- [x] 6.2 Update `log_subagent_spawn()` - add `massgen.subagent.task`
- [x] 6.3 Update `log_subagent_complete()` - add files_created and file_count
- [x] 6.4 Update SubagentManager to scan workspace for files

## 7. Tool Error Context
- [x] 7.1 Add optional `error_context` param to `log_tool_execution()`
- [x] 7.2 Update tool manager to pass error context when available

## 8. Coordination Tracker Enhancements
- [x] 8.1 Track `answers_in_context` for each agent round
- [x] 8.2 Track `restart_triggered_by_agent`

## 9. Local File References
- [x] 9.1 Add `massgen.log_path` to coordination session span
- [x] 9.2 Add `massgen.agent.log_path` to agent round spans
- [x] 9.3 Add `massgen.agent.answer_path` to agent answer spans
- [x] 9.4 Add `massgen.subagent.log_path` to subagent spans
- [x] 9.5 Add `massgen.subagent.workspace_path` to subagent complete spans

## 10. Validation
- [x] 10.1 Run `openspec validate add-logfire-workflow-analysis --strict`
- [x] 10.2 Run existing tests to ensure no regression
- [ ] 10.3 Manual verification with Logfire

## 11. Documentation
- [x] 11.1 Update log analyzer skill with workflow analysis queries
- [x] 11.2 Add example queries for round intent analysis
- [x] 11.3 Add example queries for detecting repeated work
- [x] 11.4 Document hybrid approach (Logfire preview + local full content)
