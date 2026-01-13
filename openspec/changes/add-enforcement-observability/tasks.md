# Tasks: Add Enforcement Observability

## 1. Coordination Tracker Changes

- [x] 1.1 Add `enforcement_events: Dict[str, List[Dict]]` to `CoordinationTracker.__init__`
- [x] 1.2 Add `track_enforcement_event()` method with round tracking
- [x] 1.3 Update `save_status_file()` to include `reliability` field in agent_statuses
- [x] 1.4 Add tests for enforcement event tracking

## 2. Orchestrator Tracking Integration

- [x] 2.1 Add tracking call at line 4821 (vote_and_answer)
- [x] 2.2 Add tracking call at line 4855 (vote_no_answers)
- [x] 2.3 Add tracking call at line 4885 (invalid_vote_id)
- [x] 2.4 Add tracking call at line 4946 (answer_limit)
- [x] 2.5 Add tracking call at line 4964 (answer_novelty)
- [x] 2.6 Add tracking call at line 4988 (answer_duplicate)
- [x] 2.7 Add tracking call at line 5085 (no_workflow_tool / no_tool_calls)
- [x] 2.8 Add tracking call at line 4720 (unknown_tool) - Note: Unknown tools are tracked via no_workflow_tool enforcement when they fail to satisfy workflow requirements

## 3. Improved Enforcement Messages

- [x] 3.1 Update line 5072 to include retry count and tool list
- [x] 3.2 Update line 4817 to include retry count
- [x] 3.3 Update line 4852 to include retry count
- [x] 3.4 Update line 4882 to include retry count
- [x] 3.5 Update all other error messages with retry context

## 4. Buffer Preservation

- [x] 4.1 Add `_get_buffer_content()` method to capture buffer (in orchestrator.py)
- [x] 4.2 Capture buffer content before each `continue` in enforcement loop
- [x] 4.3 Include buffer summary in enforcement tracking (truncated to 500 chars)
- [x] 4.4 Add buffer_chars_lost metric to reliability tracking

## 5. Testing

- [x] 5.1 Test unknown tool tracked in reliability
- [x] 5.2 Test invalid vote ID tracked with error message
- [ ] 5.3 Test midstream injected answer can be voted for (requires integration test)
- [x] 5.4 Test multiple enforcement attempts tracked per round
- [x] 5.5 Test enforcement message format includes retry count
- [x] 5.6 Test buffer content captured before restart
