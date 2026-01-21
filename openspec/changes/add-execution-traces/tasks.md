# Tasks: Add Execution Traces

## 1. Core Implementation

- [x] 1.1 Create `massgen/execution_trace.py` with `ExecutionTraceWriter` class
- [x] 1.2 Write unit tests for `ExecutionTraceWriter` (TDD - write tests first)
- [x] 1.3 Implement `ExecutionTraceWriter.to_markdown()` to pass tests

## 2. StreamingBuffer Integration

- [x] 2.1 Add `_execution_trace` attribute to `StreamingBufferMixin`
- [x] 2.2 Add `_init_execution_trace()` method
- [x] 2.3 Record tool calls in trace (via `_execute_tool_with_logging` in base class)
- [x] 2.4 Record tool results in trace (via `_append_tool_to_buffer`)
- [x] 2.5 Record reasoning in trace (via `_append_reasoning_to_buffer`)
- [x] 2.6 Add `_save_execution_trace()` method

## 3. Orchestrator Integration

- [x] 3.1 Call `_save_execution_trace()` in `_save_agent_snapshot()`
- [x] 3.2 Add trace file mention to `_build_tool_result_injection()`

## 4. Compression Recovery Integration

- [x] 4.1 Add execution trace file reference to compression recovery message

## 5. Testing

- [x] 5.1 Unit tests for ExecutionTraceWriter formatting
- [x] 5.2 Integration test: verify trace saved with snapshots (manual verification)
- [ ] 5.3 Integration test: verify trace copied to temp workspaces
- [ ] 5.4 Integration test: verify trace reference in compression recovery

## Notes

Tool call recording approach:
- Tool calls for MCP/custom tools: Recorded in `_execute_tool_with_logging` in `base_with_custom_tool_and_mcp.py` (checks for `_execution_trace` attribute via mixin)
- Tool calls for workflow tools (new_answer/vote): Recorded in `_append_tool_call_to_buffer` in `_streaming_buffer_mixin.py`
- Tool results: Recorded in `_append_tool_to_buffer` in `_streaming_buffer_mixin.py`
- Trace initialization: Auto-initializes when `_clear_streaming_buffer` is called, using `self.agent_id` as fallback

The integration tests (5.3-5.4) require running actual multi-agent coordination to verify end-to-end behavior.
