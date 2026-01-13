# Change: Add Enforcement Observability

## Why

Current enforcement logging is confusing and doesn't provide enough context for debugging:
- Users see `🔄 needs to use workflow tools...` with no explanation of WHY
- Unknown tool calls trigger terminal restarts but aren't tracked
- No way to analyze enforcement patterns across rounds/turns in status.json
- Streaming buffer content is lost on enforcement restart with no record

## What Changes

- **ADDED**: `reliability` field in status.json per agent tracking enforcement events
- **ADDED**: Round-level enforcement tracking (not just turn/attempt)
- **ADDED**: Buffer content capture before enforcement restart
- **MODIFIED**: Enforcement messages include retry count and context
- **MODIFIED**: Unknown tool handling tracks the event (currently causes restart but not tracked)

## Impact

- Affected specs: workflow-enforcement (new capability spec)
- Affected code:
  - `massgen/coordination_tracker.py` - Add enforcement tracking data structures
  - `massgen/orchestrator.py` - Track events at enforcement trigger points, improve messages
  - `massgen/backend/_streaming_buffer_mixin.py` - Capture buffer before clear
