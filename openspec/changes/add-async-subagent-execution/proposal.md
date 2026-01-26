# Change: Add Async Subagent Execution with Result Injection

## Why

Currently, all subagent calls are **blocking** - the parent agent must wait for the subagent to complete before continuing. This causes:

1. **Wasted time** - Parent sits idle during long-running subagent tasks (research, code generation, analysis)
2. **Sequential bottlenecks** - Can't parallelize parent work with subagent research
3. **Poor UX** - Users see the parent "stuck" waiting for minutes

The infrastructure for background execution exists (`spawn_subagent_background()` in `manager.py`) but is marked "Not supported yet" and lacks the critical **result injection** mechanism. With the hook framework (MAS-215) now merged, we can implement proper result injection via `PostToolUse` hooks.

## What Changes

### New Capabilities
- **`async` parameter on `spawn_subagents`** - When `async=true`, returns immediately while subagents run in background
- **Automatic result injection** - Via `SubagentCompleteHook` (PostToolUse) that injects completed results
- **Polling tool** - `check_subagent_results()` for explicit result retrieval
- **Progress visibility** - Status updates injected periodically (optional)

### Implementation Approach
- Use existing `spawn_subagent_background()` implementation (mostly complete)
- Add `async` parameter to existing `spawn_subagents` tool (backwards compatible)
- Add `SubagentCompleteHook` as a built-in PostToolUse hook
- Inject results at next tool boundary when subagent completes
- Support configurable injection strategies: `tool_result`, `user_message`

### YAML Configuration
```yaml
orchestrator:
  async_subagents:
    enabled: true
    injection_strategy: "tool_result"  # or "user_message"
    inject_progress: false  # Periodic progress updates
    max_background: 3  # Concurrent background subagents
```

## Impact

- **Affected specs**: New `subagent` capability (or extend existing if present)
- **Affected code**:
  - `massgen/subagent/manager.py` - Enable `spawn_subagent_background()`, add completion callbacks
  - `massgen/mcp_tools/subagent/_subagent_mcp_server.py` - Add `spawn_subagent_async` tool
  - `massgen/mcp_tools/hooks.py` - Add `SubagentCompleteHook`
  - `massgen/orchestrator.py` - Register hook, track pending results
  - `massgen/config_validator.py` - Validate new config options

## Related Issues

- **MAS-214**: Async subagent execution with result injection on completion (this spec)
- **MAS-215**: General hook framework (dependency - MERGED)
- **MAS-192**: Fix injections based on backend logic (cache preservation)
- **MAS-197**: Subagent work discarded on timeout
