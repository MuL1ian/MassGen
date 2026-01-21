# Design: Add Enforcement Observability

## Context

The orchestrator's workflow enforcement mechanism triggers restarts when agents don't use valid workflow tools (vote/new_answer). Currently:
1. Enforcement events aren't tracked in status.json
2. Error messages don't include retry counts or context
3. Streaming buffer content is lost on restart with no record
4. Unknown tool calls trigger restarts but aren't tracked

Key architectural constraint: **Workflow tools are terminal** - they end the agent's turn, so we cannot use MCP-style inline error handling. We MUST call `agent.chat()` again.

## Goals / Non-Goals

### Goals
- Track all enforcement events in status.json with round-level granularity
- Provide clear retry counts and context in user-visible messages
- Capture buffer content before it's lost on restart
- Enable post-run analysis of enforcement patterns
- If there are any workflow-style restarts that can be accomplished using the MCP restart pattern, we should shift them to that pattern, as it's much more optimal (as we just continue streaming).

### Non-Goals
- Changing workflow enforcement to be non-terminal (fundamental architecture)
- Real-time dashboards (status.json is sufficient)
- Automatic recovery from enforcement failures

## Decisions

### Decision 1: Round-Level Tracking

Track enforcement events per round, not just per turn/attempt:

```python
enforcement_events[agent_id].append({
    "round": current_round,      # NEW: Which round
    "attempt": attempt,          # Attempt within round
    "reason": "invalid_vote_id",
    "tool_calls": ["vote"],
    "error_message": "Invalid agent_id 'agent5'",
    "buffer_preview": "First 500 chars...",  # NEW: Captured buffer
    "timestamp": time.time(),
})
```

**Rationale**: Round-level tracking helps identify if certain rounds consistently trigger enforcement (e.g., round 2 always has issues with novelty checks).

### Decision 2: Buffer Capture Before Clear

Modify buffer clearing to capture content first:

```python
# In orchestrator, before continue:
buffer_content = agent.backend._get_streaming_buffer()
self.coordination_tracker.track_enforcement_event(
    ...,
    buffer_preview=buffer_content,
)
# Then continue (which triggers new chat() and clears buffer)
```

*Note*: Truncate to first 500 chars for `buffer_preview` in status.json logging. Track full `buffer_chars` count for metrics.

**Rationale**: Buffer contains reasoning tokens and partial work that may be valuable for debugging. Truncated preview is sufficient for status.json logging while full char count enables metrics analysis.

### Decision 3: Enforcement Reason Categories

| Reason | Code Location | Description |
|--------|---------------|-------------|
| `no_workflow_tool` | 5072 | Called tools but none were workflow |
| `no_tool_calls` | 5072 | Text-only response |
| `invalid_vote_id` | 4880 | Vote with invalid agent_id |
| `vote_no_answers` | 4851 | Vote when no answers exist |
| `vote_and_answer` | 4816 | Both tools in same response |
| `answer_limit` | 4943 | Hit answer count limit |
| `answer_novelty` | 4961 | Answer too similar |
| `answer_duplicate` | 4984 | Exact duplicate |
| `unknown_tool` | 4720 | Tool doesn't exist |

### Decision 4: Status.json Structure

```json
{
  "agents": {
    "agent_c": {
      "reliability": {
        "enforcement_attempts": [
          {
            "round": 1,
            "attempt": 1,
            "reason": "unknown_tool",
            "tool_calls": ["execute_command"],
            "error_message": null,
            "buffer_preview": "[Reasoning]\nI should read...",
            "timestamp": 1736683468.123
          }
        ],
        "by_round": {
          "1": {"count": 2, "reasons": ["unknown_tool", "no_workflow_tool"]},
          "2": {"count": 0, "reasons": []}
        },
        "unknown_tools": ["execute_command"],
        "workflow_errors": [],
        "total_enforcement_retries": 2,
        "total_buffer_chars_lost": 15000,
        "outcome": "ok"
      }
    }
  }
}
```

## Risks / Trade-offs

### Risk: Buffer Preview Size
- **Risk**: Large buffers could bloat status.json
- **Mitigation**: Truncate buffer to first 500 chars for `buffer_preview` field. Track full `buffer_chars` count separately for metrics. This keeps status.json manageable while preserving enough context for debugging.

### Risk: Performance of Tracking
- **Risk**: Tracking calls add overhead
- **Mitigation**: Minimal overhead (dict append), only on enforcement (error path)

### Trade-off: Terminal vs Inline Handling
- We confirmed workflow tools are terminal (stream ends after vote/new_answer)
- Cannot adopt MCP-style inline error handling
- Must accept the restart cost but can track and measure it

## Migration Plan

1. Add tracking infrastructure (no behavior change)
2. Add tracking calls at enforcement points
3. Update messages with retry counts
4. Add buffer capture

Rollback: Remove tracking calls (data loss only, no behavior change)

## Open Questions

1. **Midstream injection vote validity**: Need to verify votes for midstream-injected answers work correctly. Test case: Agent B votes for Agent C's answer that arrived via midstream injection. We can use injection_delay_test.yaml here to force an injection and test, documenting the results

2. **Unknown tool terminal behavior**: Logs show unknown tools cause terminal restart. Need to verify this is the current behavior and decide if it should change (out of scope for this change).