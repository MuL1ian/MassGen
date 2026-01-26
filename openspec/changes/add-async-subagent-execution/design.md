# Design: Async Subagent Execution with Result Injection

## Context

MassGen subagents currently block the parent agent until completion. The background spawn infrastructure exists but lacks the mechanism to notify the parent when results are ready. The hook framework (MAS-215) provides the injection point needed.

**Key constraint**: Subagents run as isolated subprocesses with no shared state. Results must flow through the file system (`answer.txt`, `status.json`) and then be injected via hooks.

## Goals / Non-Goals

### Goals
- Parent agent continues working while subagents run in background
- Results automatically injected when subagents complete
- Graceful handling of timeouts and partial results
- Cache-preserving injection (per MAS-192)
- Clear visibility into pending/completed subagents

### Non-Goals
- Real-time streaming of subagent progress (future enhancement)
- Shared memory between parent and subagent
- Subagent-to-subagent communication
- Complex dependency graphs between subagents

## Decisions

### 1. Injection Mechanism: PostToolUse Hook

**Decision**: Use a `SubagentCompleteHook` registered as a global PostToolUse hook.

**Why**:
- Hook framework already supports injection into tool results
- PostToolUse fires at natural boundaries (after any tool completes)
- Multiple injections can be combined if several subagents finish simultaneously

**Alternative considered**: Dedicated injection point
- Rejected: Would require changes to the core agent loop and break abstraction

### 2. Result Queue Architecture

**Decision**: Orchestrator maintains a per-agent `pending_subagent_results` queue.

```python
# In Orchestrator
self._pending_subagent_results: Dict[str, List[SubagentResult]] = defaultdict(list)

# When subagent completes (callback from SubagentManager)
def _on_subagent_complete(self, parent_agent_id: str, result: SubagentResult):
    self._pending_subagent_results[parent_agent_id].append(result)

# SubagentCompleteHook checks this queue during PostToolUse
```

**Why**:
- Orchestrator already coordinates agents and has access to all agent IDs
- Queue allows batching multiple completions
- Clear ownership and lifecycle management

### 3. Injection Strategies

**Decision**: Support two strategies via configuration:

| Strategy | Injection Point | Cache Impact | Best For |
|----------|-----------------|--------------|----------|
| `tool_result` | Appended to current tool response | Preserves cache | Quick results, minimal disruption |
| `user_message` | Added as follow-up user message | May break cache | Large results, needs agent attention |

**Default**: `tool_result` (cache-friendly)

### 4. Completion Callback Mechanism

**Decision**: Use `asyncio.Event` + callback registration in SubagentManager.

```python
class SubagentManager:
    def __init__(self, ...):
        self._completion_callbacks: List[Callable[[str, SubagentResult], None]] = []

    def register_completion_callback(self, callback: Callable):
        self._completion_callbacks.append(callback)

    async def _run_background(self, config, workspace):
        # ... existing logic ...
        result = await self._execute_subagent(config, workspace)
        # Notify all registered callbacks
        for callback in self._completion_callbacks:
            callback(config.parent_agent_id, result)
```

**Why**:
- Decouples SubagentManager from Orchestrator
- Multiple listeners can register (future: logging, metrics)
- Synchronous callback is fine - just adds to queue

### 5. MCP Tool Interface

**Decision**: Add `async: bool` parameter to existing `spawn_subagents` tool.

```python
@server.tool()
async def spawn_subagents(
    context: str,
    tasks: List[Dict],
    async_: bool = False,  # NEW: Run in background when True
) -> Dict:
    """
    Spawn one or more subagents to work on tasks.

    Args:
        context: Project context for subagents
        tasks: List of task configurations
        async_: If True, spawn in background and return immediately.
                Results will be automatically injected when complete.
                If False (default), wait for all subagents to complete.
    """
    if async_:
        # Non-blocking: return IDs, results injected later
        return {
            "subagent_ids": [...],
            "status": "running",
            "message": "Subagents spawned in background. Results will be injected when complete."
        }
    else:
        # Blocking: existing behavior
        return {"results": [...]}
```

**Why**:
- Single tool, simpler API surface
- Backwards compatible - default is blocking (existing behavior)
- Agent explicitly opts into async mode
- Consistent with common patterns (e.g., `subprocess.Popen` vs `subprocess.run`)

### 6. Result Format

**Decision**: Inject results in a structured XML-like format:

```xml
<subagent_result id="research_api_options" status="completed">
Background research task completed successfully.

## Summary
[Subagent's answer, potentially summarized if too long]

## Details
- Execution time: 45.2s
- Token usage: 12,345 input / 2,341 output
- Workspace: subagents/research_api_options/
</subagent_result>
```

**Why**:
- Clear boundaries for the agent to parse
- Metadata helps agent evaluate quality/completeness
- Workspace reference allows agent to read additional artifacts

### 7. Handling Multiple Completions

**Decision**: Batch inject all completed subagents in a single injection.

```xml
<subagent_results count="2">
<subagent_result id="research_task_1" status="completed">
...
</subagent_result>
<subagent_result id="analysis_task" status="completed_but_timeout">
...
</subagent_result>
</subagent_results>
```

**Why**:
- Single injection point minimizes cache disruption
- Agent sees complete picture of what finished
- Easier to process as a batch

### 8. Progress Updates (Optional)

**Decision**: Support optional progress injection via `inject_progress: true`.

When enabled, inject status updates every N seconds (configurable):

```xml
<subagent_progress>
- research_task_1: 60% complete (voting phase)
- analysis_task: running (initial_answer phase)
</subagent_progress>
```

**Why**:
- Visibility into long-running tasks
- Agent can decide to wait or continue
- Optional to avoid noise for short tasks

## Risks / Trade-offs

### Risk: Context Bloat
**Problem**: Many subagent results could balloon context size.
**Mitigation**:
- Subagent answers are already distilled/concise by design
- Agent can spawn fewer concurrent subagents if context is a concern
- Existing context compression handles large contexts

### Risk: Timing Edge Cases
**Problem**: Subagent completes just as parent finishes - result lost.
**Mitigation**:
- Always inject pending results before session ends
- Persist pending queue to disk for restart recovery (future)

### Risk: Injection Ordering
**Problem**: Results injected in arbitrary order vs spawn order.
**Mitigation**:
- Document that injection order = completion order
- Include spawn timestamp in result for agent to sort if needed

## Migration Plan

1. **Phase 1**: Enable `spawn_subagent_background()` with callback mechanism
2. **Phase 2**: Add `SubagentCompleteHook` and orchestrator queue
3. **Phase 3**: Add `spawn_subagent_async` MCP tool
4. **Phase 4**: Add progress injection (optional enhancement)

No breaking changes - existing `spawn_subagents` continues to work.

## Open Questions

1. **Cancellation semantics**: When parent completes, should background subagents be cancelled or allowed to finish?
2. **Cost attribution**: How to attribute subagent costs when results arrive asynchronously?
