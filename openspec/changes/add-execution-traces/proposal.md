# Change: Add Execution Traces for Agent Context Recovery

## Why

When agents hit context limits and undergo compression, they lose detailed execution history. Similarly, when agents coordinate, they can only see other agents' final answers - not how they arrived at those answers.

Inspired by Cursor's "dynamic context discovery" pattern (using history as files), this change enables agents to access their complete execution trace as a searchable file.

**Linear Issue**: MAS-226

## What Changes

- **NEW**: `ExecutionTraceWriter` class that formats streaming buffer content as structured markdown
- **NEW**: `execution_trace.md` file saved alongside snapshots (answer.txt, vote.json)
- **MODIFY**: Compression recovery message references the trace file for detail recovery
- **MODIFY**: Context injection mentions trace files are available in temp workspaces

## Impact

- Affected code:
  - `massgen/execution_trace.py` (new)
  - `massgen/backend/_streaming_buffer_mixin.py`
  - `massgen/orchestrator.py`
  - `massgen/backend/_compression_utils.py`
- No breaking changes
- Traces are opt-in via existing buffer infrastructure
