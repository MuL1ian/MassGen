# Tasks: Async Subagent Execution

## 1. Tests First (TDD)

- [ ] 1.1 Unit tests for SubagentManager callbacks
  - Test callback registration
  - Test callback invocation on completion
  - Test callback invocation on timeout
  - File: `massgen/tests/test_subagent_manager.py`

- [ ] 1.2 Unit tests for SubagentCompleteHook
  - Test queue checking
  - Test result formatting
  - Test injection strategies
  - File: `massgen/tests/test_hook_framework.py`

- [ ] 1.3 Unit tests for result formatter
  - Test XML format generation
  - Test single result formatting
  - Test batch formatting for multiple results
  - File: `massgen/tests/test_subagent_result_formatter.py` (new)

- [ ] 1.4 Unit tests for async parameter on spawn_subagents
  - Test async=false returns results (existing behavior)
  - Test async=true returns IDs immediately
  - Test async disabled in config falls back to blocking
  - File: `massgen/tests/test_subagent_mcp_server.py`

## 2. Core Infrastructure

- [ ] 2.1 Add completion callback mechanism to `SubagentManager`
  - Add `_completion_callbacks: List[Callable]`
  - Add `register_completion_callback()` method
  - Call callbacks in `_run_background()` when subagent finishes
  - File: `massgen/subagent/manager.py`

- [ ] 2.2 Enable `spawn_subagent_background()` (remove "not supported" guard)
  - Remove the warning/early return
  - Ensure proper semaphore handling
  - Verify timeout recovery still works
  - File: `massgen/subagent/manager.py`

- [ ] 2.3 Add pending results queue to Orchestrator
  - Add `_pending_subagent_results: Dict[str, List[SubagentResult]]`
  - Add `_on_subagent_complete()` callback method
  - Register callback with SubagentManager during init
  - File: `massgen/orchestrator.py`

## 3. Result Formatting

- [ ] 3.1 Implement result formatter
  - XML-structured format with metadata
  - Include full answer (no summarization needed)
  - Include execution stats (time, tokens, workspace)
  - File: `massgen/subagent/result_formatter.py` (new)

- [ ] 3.2 Handle multiple results
  - Batch format for multiple completions
  - Order by completion time
  - Include count in wrapper
  - File: `massgen/subagent/result_formatter.py`

## 4. Hook Integration

- [ ] 4.1 Create `SubagentCompleteHook` class
  - Inherit from appropriate hook base class
  - Match all tool names (`*` pattern)
  - Check pending results queue on each PostToolUse
  - Format results using result formatter
  - File: `massgen/mcp_tools/hooks.py`

- [ ] 4.2 Register `SubagentCompleteHook` as global hook
  - Add to orchestrator's hook setup
  - Pass reference to pending results queue
  - Configure injection strategy from config
  - File: `massgen/orchestrator.py`

- [ ] 4.3 Implement injection strategies
  - `tool_result`: Append to current tool response
  - `user_message`: Add as follow-up message
  - Respect `preserve_cache` flag
  - File: `massgen/mcp_tools/hooks.py`

## 5. MCP Tool Interface

- [ ] 5.1 Add `async` parameter to `spawn_subagents` tool
  - Add `async_: bool = False` parameter
  - When True, call `manager.spawn_subagent_background()` instead of blocking
  - Return subagent IDs and "running" status (no results yet)
  - When False (default), existing blocking behavior
  - File: `massgen/mcp_tools/subagent/_subagent_mcp_server.py`

- [ ] 5.2 Add `check_subagent_results` tool
  - Return list of completed subagent results
  - Include pending/running counts
  - Option to wait with timeout
  - File: `massgen/mcp_tools/subagent/_subagent_mcp_server.py`

- [ ] 5.3 Update tool descriptions
  - Document async parameter behavior in docstrings
  - Explain injection mechanism
  - Provide usage examples
  - File: `massgen/mcp_tools/subagent/_subagent_mcp_server.py`

## 6. Configuration

- [ ] 6.1 Add `async_subagents` config section
  - `enabled: bool` (default: true)
  - `injection_strategy: "tool_result" | "user_message"` (default: tool_result)
  - `inject_progress: bool` (default: false)
  - File: `massgen/orchestrator.py`, `massgen/config_validator.py`

- [ ] 6.2 Add config validation
  - Validate strategy values
  - File: `massgen/config_validator.py`

## 7. Integration Testing

- [ ] 7.1 Integration test for async flow
  - Spawn async subagent
  - Parent continues working
  - Result injected on next tool call
  - File: `massgen/tests/test_async_subagent.py` (new)

- [ ] 7.2 Test across backends
  - Claude, OpenAI, Gemini, OpenRouter, Grok
  - Verify injection works with each backend's message format
  - File: `scripts/test_async_subagent_backends.py` (new)

## 8. Edge Cases

- [ ] 8.1 Handle parent completion before subagent
  - Inject any pending results before final response
  - Log warning about orphaned subagents
  - File: `massgen/orchestrator.py`

- [ ] 8.2 Handle restart/recovery
  - Restore pending queue from disk (if feasible)
  - Or: accept loss and log warning
  - File: `massgen/orchestrator.py`

## 9. Documentation

- [ ] 9.1 Update subagent user guide
  - Document async spawning
  - Explain result injection
  - Provide examples
  - File: `docs/source/user_guide/advanced/subagents.rst`

- [ ] 9.2 Add example configs
  - Basic async subagent config
  - Multi-subagent parallel config
  - File: `massgen/configs/features/async_subagent_example.yaml`
