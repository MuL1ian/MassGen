---
name: massgen-log-analyzer
description: Run MassGen experiments and analyze logs using automation mode, logfire tracing, and SQL queries. Use this skill for performance analysis, debugging agent behavior, evaluating coordination patterns, and improving the logging structure.
---

# MassGen Log Analyzer

This skill provides a structured workflow for running MassGen experiments and analyzing the resulting traces and logs using Logfire.

## Purpose

The log-analyzer skill helps you:
- Run MassGen experiments with proper instrumentation
- Query and analyze traces hierarchically
- Debug agent behavior and coordination patterns
- Measure performance and identify bottlenecks
- Improve the logging structure itself

## Prerequisites

**Required MCP Server:**
This skill requires the Logfire MCP server to be configured. The MCP server provides these tools:
- `mcp__logfire__arbitrary_query` - Run SQL queries against logfire data
- `mcp__logfire__schema_reference` - Get the database schema
- `mcp__logfire__find_exceptions_in_file` - Find exceptions in a file
- `mcp__logfire__logfire_link` - Create links to traces in the UI

**Required Flags:**
- `--automation` - Clean output for programmatic parsing
- `--logfire` - Enable Logfire tracing

## Part 1: Running MassGen Experiments

### Basic Command Format

```bash
uv run massgen --automation --logfire --config [config_file] "[question]"
```

### Running in Background (Recommended)

Use `run_in_background: true` (or however you run tasks in the background) to run experiments asynchronously so you can monitor progress and end early if needed.

**Expected Output (first lines):**
```
LOG_DIR: .massgen/massgen_logs/log_YYYYMMDD_HHMMSS_ffffff
STATUS: .massgen/massgen_logs/log_YYYYMMDD_HHMMSS_ffffff/turn_1/attempt_1/status.json
QUESTION: Your task here
[Coordination in progress - monitor status.json for real-time updates]
```

**Parse the LOG_DIR** - you'll need this for file-based analysis!

### Monitoring Progress

`status.json` updates every 2 seconds; use that to track progress.

```bash
cat [log_dir]/turn_1/attempt_1/status.json
```

**Key fields to monitor:**
- `coordination.completion_percentage` (0-100)
- `coordination.phase` - "initial_answer", "enforcement", "presentation"
- `results.winner` - null while running, agent_id when complete
- `agents[].status` - "waiting", "streaming", "answered", "voted", "error"
- `agents[].error` - null if ok, error details if failed

### Reading Final Results

After completion (exit code 0):

```bash
# Read the final answer
cat [log_dir]/turn_1/attempt_1/final/[winner]/answer.txt
```

**Other useful files:**
- `execution_metadata.yaml` - Full config and execution details
- `coordination_events.json` - Complete event log
- `coordination_table.txt` - Human-readable coordination summary

## Part 2: Querying Logfire

### Database Schema

The main table is `records` with these key columns:

| Column | Description |
|--------|-------------|
| `span_name` | Name of the span (e.g., "agent.agent_a.round_0") |
| `span_id` | Unique identifier for this span |
| `parent_span_id` | ID of the parent span (null for root) |
| `trace_id` | Groups all spans in a single trace |
| `duration` | Time in seconds |
| `start_timestamp` | When the span started |
| `end_timestamp` | When the span ended |
| `attributes` | JSON blob with custom attributes |
| `message` | Log message |
| `is_exception` | Boolean for errors |
| `exception_type` | Type of exception if any |
| `exception_message` | Exception message |

### MassGen Span Hierarchy

MassGen creates hierarchical spans:

```
coordination.session (root)
├── Coordination event: coordination_started
├── agent.agent_a.round_0
│   ├── llm.openrouter.stream
│   ├── mcp.filesystem.write_file
│   └── Tool execution: mcp__filesystem__write_file
├── agent.agent_b.round_0
├── Agent answer: agent1.1
├── agent.agent_a.round_1 (voting round)
├── Agent vote: agent_a -> agent1.1
├── Coordination event: winner_selected
└── agent.agent_a.presentation
    ├── Winner selected: agent1.1
    ├── llm.openrouter.stream
    └── Final answer from agent_a
```

### Custom Attributes

MassGen spans include these custom attributes (access via `attributes->'key'`):

| Attribute | Description |
|-----------|-------------|
| `massgen.agent_id` | Agent identifier (agent_a, agent_b) |
| `massgen.iteration` | Current iteration number |
| `massgen.round` | Round number for this agent |
| `massgen.round_type` | "initial_answer", "voting", or "presentation" |
| `massgen.backend` | Backend provider name |
| `massgen.num_context_answers` | Number of answers in context |
| `massgen.is_winner` | True for presentation spans |
| `massgen.outcome` | "vote", "answer", or "error" (set after round completes) |
| `massgen.voted_for` | Agent ID voted for (only set for votes) |
| `massgen.voted_for_label` | Answer label voted for (e.g., "agent1.1", only set for votes) |
| `massgen.answer_label` | Answer label assigned (e.g., "agent1.1", only set for answers) |
| `massgen.error_message` | Error message (only set when outcome is "error") |
| `massgen.usage.input` | Input token count |
| `massgen.usage.output` | Output token count |
| `massgen.usage.reasoning` | Reasoning token count |
| `massgen.usage.cached_input` | Cached input token count |
| `massgen.usage.cost` | Estimated cost in USD |

## Part 3: Common Analysis Queries

### 1. View Trace Hierarchy

```sql
SELECT span_name, span_id, parent_span_id, duration, start_timestamp
FROM records
WHERE trace_id = '[YOUR_TRACE_ID]'
ORDER BY start_timestamp
LIMIT 50
```

### 2. Find Recent Sessions

```sql
SELECT span_name, trace_id, duration, start_timestamp
FROM records
WHERE span_name = 'coordination.session'
ORDER BY start_timestamp DESC
LIMIT 10
```

### 3. Agent Round Performance

```sql
SELECT
  span_name,
  duration,
  attributes->>'massgen.agent_id' as agent_id,
  attributes->>'massgen.round' as round,
  attributes->>'massgen.round_type' as round_type
FROM records
WHERE span_name LIKE 'agent.%'
ORDER BY start_timestamp DESC
LIMIT 20
```

### 4. Tool Call Analysis

```sql
SELECT
  span_name,
  duration,
  parent_span_id,
  start_timestamp
FROM records
WHERE span_name LIKE 'mcp.%' OR span_name LIKE 'Tool execution:%'
ORDER BY start_timestamp DESC
LIMIT 30
```

### 5. Find Errors

```sql
SELECT
  span_name,
  exception_type,
  exception_message,
  trace_id,
  start_timestamp
FROM records
WHERE is_exception = true
ORDER BY start_timestamp DESC
LIMIT 20
```

### 6. LLM Call Performance

```sql
SELECT
  span_name,
  duration,
  attributes->>'gen_ai.request.model' as model,
  start_timestamp
FROM records
WHERE span_name LIKE 'llm.%'
ORDER BY start_timestamp DESC
LIMIT 30
```

### 7. Full Trace with Hierarchy (Nested View)

```sql
SELECT
  CASE
    WHEN parent_span_id IS NULL THEN span_name
    ELSE '  └─ ' || span_name
  END as hierarchy,
  duration,
  span_id,
  parent_span_id
FROM records
WHERE trace_id = '[YOUR_TRACE_ID]'
ORDER BY start_timestamp
```

### 8. Coordination Events Timeline

```sql
SELECT span_name, message, duration, start_timestamp
FROM records
WHERE span_name LIKE 'Coordination event:%'
   OR span_name LIKE 'Agent answer:%'
   OR span_name LIKE 'Agent vote:%'
   OR span_name LIKE 'Winner selected:%'
ORDER BY start_timestamp DESC
LIMIT 30
```

## Part 4: Analysis Workflow

### Step 1: Run Experiment

```bash
uv run massgen --automation --logfire --config [config] "[prompt]" 2>&1
```

### Step 2: Find the Trace

Query for recent sessions:
```sql
SELECT trace_id, duration, start_timestamp
FROM records
WHERE span_name = 'coordination.session'
ORDER BY start_timestamp DESC
LIMIT 5
```

### Step 3: Analyze Hierarchy

Get full trace structure:
```sql
SELECT span_name, span_id, parent_span_id, duration
FROM records
WHERE trace_id = '[trace_id_from_step_2]'
ORDER BY start_timestamp
```

### Step 4: Investigate Specific Issues

**Slow tool calls:**
```sql
SELECT span_name, duration, parent_span_id
FROM records
WHERE trace_id = '[trace_id]' AND span_name LIKE 'mcp.%'
ORDER BY duration DESC
```

**Agent comparison:**
```sql
SELECT
  attributes->>'massgen.agent_id' as agent,
  COUNT(*) as rounds,
  SUM(duration) as total_time,
  AVG(duration) as avg_round_time
FROM records
WHERE trace_id = '[trace_id]' AND span_name LIKE 'agent.%'
GROUP BY attributes->>'massgen.agent_id'
```

### Step 5: Create Trace Link

Use the MCP tool to create a viewable link:
```
mcp__logfire__logfire_link(trace_id="[your_trace_id]")
```

## Part 5: Improving the Logging Structure

### Current Span Types

| Span Pattern | Source | Description |
|--------------|--------|-------------|
| `coordination.session` | coordination_tracker.py | Root session span |
| `agent.{id}.round_{n}` | orchestrator.py | Agent execution round |
| `agent.{id}.presentation` | orchestrator.py | Winner's final presentation |
| `mcp.{server}.{tool}` | mcp_tools/client.py | MCP tool execution |
| `llm.{provider}.stream` | backends | LLM streaming call |
| `Tool execution: {name}` | base_with_custom_tool.py | Tool wrapper |
| `Coordination event: *` | coordination_tracker.py | Coordination events |
| `Agent answer: {label}` | coordination_tracker.py | Answer submission |
| `Agent vote: {from} -> {to}` | coordination_tracker.py | Vote cast |

### Adding New Spans

Use the tracer from structured_logging:

```python
from massgen.structured_logging import get_tracer

tracer = get_tracer()
with tracer.span("my_operation", attributes={
    "massgen.custom_key": "value",
}):
    do_work()
```

### Context Propagation Notes

**Known limitation:** When multiple agents run concurrently via `asyncio.create_task`, child spans may not nest correctly under agent round spans. This is an OpenTelemetry context propagation issue with concurrent async code. The presentation phase works correctly because only one agent runs.

**Workaround:** For accurate nesting in concurrent scenarios, explicit context passing with `contextvars.copy_context()` would be needed.

## Logfire Documentation Reference

**Main Documentation:** https://logfire.pydantic.dev/docs/

### Key Pages to Know

| Topic | URL | Description |
|-------|-----|-------------|
| **Getting Started** | `/docs/` | Overview, setup, and core concepts |
| **Manual Tracing** | `/docs/guides/onboarding-checklist/add-manual-tracing/` | Creating spans, adding attributes |
| **SQL Explorer** | `/docs/guides/web-ui/explore/` | Writing SQL queries in the UI |
| **Live View** | `/docs/guides/web-ui/live/` | Real-time trace monitoring |
| **Query API** | `/docs/how-to-guides/query-api/` | Programmatic access to data |
| **OpenAI Integration** | `/docs/integrations/llms/openai/` | LLM call instrumentation |

### Logfire Concepts

**Spans vs Logs:**
- **Spans** represent operations with measurable duration (use `with logfire.span():`)
- **Logs** capture point-in-time events (use `logfire.info()`, `logfire.error()`, etc.)
- Spans and logs inside a span block become children of that span

**Span Names vs Messages:**
- `span_name` = the first argument (used for filtering, keep low-cardinality)
- `message` = formatted result with attribute values interpolated
- Example: `logfire.info('Hello {name}', name='Alice')` → span_name="Hello {name}", message="Hello Alice"

**Attributes:**
- Keyword arguments become structured JSON attributes
- Access in SQL via `attributes->>'key'` or `attributes->'key'`
- Cast when needed: `(attributes->'cost')::float`

### Live View Features

The Logfire Live View UI (https://logfire.pydantic.dev/) provides:
- **Real-time streaming** of traces as they arrive
- **SQL search pane** (press `/` to open) with auto-complete
- **Natural language to SQL** - describe what you want and get a query
- **Timeline histogram** showing span counts over time
- **Trace details panel** with attributes, exceptions, and OpenTelemetry data
- **Cross-linking** between SQL results and trace view via trace_id/span_id

### SQL Explorer Tips

The Explore page uses Apache DataFusion SQL syntax (similar to Postgres):

```sql
-- Subqueries and CTEs work
WITH recent AS (
  SELECT * FROM records
  WHERE start_timestamp > now() - interval '1 hour'
)
SELECT * FROM recent WHERE is_exception;

-- Access nested JSON
SELECT attributes->>'massgen.agent_id' as agent FROM records;

-- Cast JSON values
SELECT (attributes->'token_count')::int as tokens FROM records;

-- Time filtering is efficient
WHERE start_timestamp > now() - interval '30 minutes'
```

### LLM Instrumentation

Logfire auto-instruments OpenAI calls when configured:
- Captures conversation display, token usage, response metadata
- Creates separate spans for streaming requests vs responses
- Works with both sync and async clients

MassGen's backends use this for `llm.{provider}.stream` spans.

## Reference Documentation

**Logfire:**
- Main docs: https://logfire.pydantic.dev/docs/
- Live View: https://logfire.pydantic.dev/docs/guides/web-ui/live/
- SQL Explorer: https://logfire.pydantic.dev/docs/guides/web-ui/explore/
- Query API: https://logfire.pydantic.dev/docs/how-to-guides/query-api/
- Manual tracing: https://logfire.pydantic.dev/docs/guides/onboarding-checklist/add-manual-tracing/
- OpenAI integration: https://logfire.pydantic.dev/docs/integrations/llms/openai/
- Schema reference: Use `mcp__logfire__schema_reference` tool

**MassGen:**
- Automation mode: `AI_USAGE.md`
- Status file reference: `docs/source/reference/status_file.rst`
- Structured logging: `massgen/structured_logging.py`

## Tips for Effective Analysis

1. **Always use both flags:** `--automation --logfire` together
2. **Run in background** for long tasks to monitor progress
3. **Query by trace_id** to isolate specific sessions
4. **Check parent_span_id** to understand hierarchy
5. **Use duration** to identify bottlenecks
6. **Look at attributes** for MassGen-specific context
7. **Create trace links** to share findings with team

## Part 6: Comprehensive Log Analysis Pattern

When asked to analyze a MassGen log run, follow this structured checklist covering **correctness**, **efficiency**, **errors**, and **agent behavior**.

### Step 1: Get Session Overview

First, identify the session and get high-level metrics:

```sql
-- Find recent sessions with basic stats
SELECT
  trace_id,
  duration as session_duration_sec,
  start_timestamp,
  end_timestamp
FROM records
WHERE span_name = 'coordination.session'
ORDER BY start_timestamp DESC
LIMIT 5
```

### Step 2: Correctness Analysis

**Goal:** Verify the coordination worked correctly and produced a valid answer.

#### 2a. Check Coordination Flow
```sql
-- Verify all expected phases occurred
SELECT span_name, start_timestamp, duration
FROM records
WHERE trace_id = '[TRACE_ID]'
  AND (span_name LIKE 'Coordination event:%'
       OR span_name LIKE 'Agent answer:%'
       OR span_name LIKE 'Agent vote:%'
       OR span_name LIKE 'Winner selected:%'
       OR span_name LIKE 'Final answer%')
ORDER BY start_timestamp
```

**Expected flow:**
1. `Coordination event: coordination_started`
2. `Agent answer: agent1.1`, `Agent answer: agent2.1` (initial answers)
3. `Agent vote: agent_a -> ...`, `Agent vote: agent_b -> ...`
4. `Coordination event: winner_selected`
5. `Winner selected: ...`
6. `Final answer from ...`

#### 2b. Check for Incomplete Rounds
```sql
-- Find agents that started but didn't complete
SELECT
  span_name,
  attributes->>'massgen.outcome' as outcome,
  attributes->>'massgen.error_message' as error
FROM records
WHERE trace_id = '[TRACE_ID]'
  AND span_name LIKE 'agent.%'
ORDER BY start_timestamp
```

**Red flags:**
- `outcome = null` (round didn't complete)
- `outcome = "error"` (agent failed)
- Missing expected agent rounds

#### 2c. Verify Voting Consistency
```sql
-- Check all votes were cast and valid
SELECT
  span_name,
  attributes->>'massgen.agent_id' as voter,
  attributes->>'massgen.voted_for' as voted_for,
  attributes->>'massgen.voted_for_label' as voted_for_label
FROM records
WHERE trace_id = '[TRACE_ID]'
  AND span_name LIKE 'Agent vote:%'
```

### Step 3: Efficiency Analysis

**Goal:** Identify bottlenecks and optimization opportunities.

#### 3a. Phase Duration Breakdown
```sql
-- Time spent in each phase
SELECT
  CASE
    WHEN span_name LIKE 'agent.%.round_0' THEN 'initial_answer'
    WHEN span_name LIKE 'agent.%.round_%' THEN 'voting'
    WHEN span_name LIKE 'agent.%.presentation' THEN 'presentation'
    ELSE 'other'
  END as phase,
  COUNT(*) as count,
  ROUND(AVG(duration), 2) as avg_duration_sec,
  ROUND(MAX(duration), 2) as max_duration_sec,
  ROUND(SUM(duration), 2) as total_duration_sec
FROM records
WHERE trace_id = '[TRACE_ID]'
  AND span_name LIKE 'agent.%'
GROUP BY 1
ORDER BY total_duration_sec DESC
```

#### 3b. Slowest Operations (Top Bottlenecks)
```sql
-- Find the 10 slowest spans
SELECT span_name, duration, start_timestamp
FROM records
WHERE trace_id = '[TRACE_ID]'
ORDER BY duration DESC
LIMIT 10
```

#### 3c. Tool Call Performance
```sql
-- Analyze tool call efficiency
SELECT
  span_name,
  COUNT(*) as call_count,
  ROUND(AVG(duration), 3) as avg_duration_sec,
  ROUND(MAX(duration), 3) as max_duration_sec,
  ROUND(SUM(duration), 3) as total_duration_sec
FROM records
WHERE trace_id = '[TRACE_ID]'
  AND span_name LIKE 'mcp.%'
GROUP BY span_name
ORDER BY total_duration_sec DESC
```

#### 3d. Slow Tool Calls (>1 second)
```sql
-- Find specific slow tool calls with their arguments
SELECT
  span_name,
  duration,
  attributes->>'massgen.agent_id' as agent,
  attributes->>'massgen.round' as round,
  attributes->>'massgen.round_type' as round_type,
  start_timestamp
FROM records
WHERE trace_id = '[TRACE_ID]'
  AND span_name LIKE 'mcp.%'
  AND duration > 1.0
ORDER BY duration DESC
```

#### 3e. Repeated/Redundant Tool Calls
```sql
-- Check for duplicate tool calls (same tool called multiple times)
SELECT
  span_name,
  attributes->>'massgen.agent_id' as agent,
  attributes->>'massgen.round' as round,
  COUNT(*) as call_count
FROM records
WHERE trace_id = '[TRACE_ID]'
  AND span_name LIKE 'mcp.%'
GROUP BY span_name, attributes->>'massgen.agent_id', attributes->>'massgen.round'
HAVING COUNT(*) > 1
ORDER BY call_count DESC
```

#### 3f. LLM Call Latency
```sql
-- Analyze LLM response times
SELECT
  span_name,
  duration,
  attributes->>'gen_ai.request.model' as model,
  attributes->>'massgen.agent_id' as agent,
  start_timestamp
FROM records
WHERE trace_id = '[TRACE_ID]'
  AND span_name LIKE 'llm.%'
ORDER BY duration DESC
```

### Step 4: Error Analysis

**Goal:** Identify failures, exceptions, and error patterns.

#### 4a. Find All Exceptions
```sql
-- All exceptions in the trace
SELECT
  span_name,
  exception_type,
  exception_message,
  start_timestamp
FROM records
WHERE trace_id = '[TRACE_ID]'
  AND is_exception = true
ORDER BY start_timestamp
```

#### 4b. Failed Tool Calls
```sql
-- Tool calls that failed
SELECT
  span_name,
  attributes->>'error_message' as error,
  attributes->>'massgen.agent_id' as agent,
  attributes->>'arguments_preview' as arguments,
  duration,
  start_timestamp
FROM records
WHERE trace_id = '[TRACE_ID]'
  AND span_name LIKE 'Tool execution:%'
  AND attributes->>'success' = 'false'
ORDER BY start_timestamp
```

#### 4c. Agent Errors
```sql
-- Agents that encountered errors
SELECT
  span_name,
  attributes->>'massgen.outcome' as outcome,
  attributes->>'massgen.error_message' as error,
  duration
FROM records
WHERE trace_id = '[TRACE_ID]'
  AND span_name LIKE 'agent.%'
  AND attributes->>'massgen.outcome' = 'error'
```

#### 4d. Timeout Analysis
```sql
-- Check for timeout-related errors
SELECT
  span_name,
  exception_type,
  exception_message,
  duration
FROM records
WHERE trace_id = '[TRACE_ID]'
  AND (exception_message LIKE '%timeout%'
       OR exception_message LIKE '%Timeout%'
       OR exception_type LIKE '%Timeout%')
```

### Step 5: Cost & Token Analysis

**Goal:** Understand resource consumption.

#### 5a. Token Usage by Agent
```sql
-- Token usage per agent
SELECT
  attributes->>'massgen.agent_id' as agent,
  SUM((attributes->'massgen.usage.input')::int) as total_input_tokens,
  SUM((attributes->'massgen.usage.output')::int) as total_output_tokens,
  SUM((attributes->'massgen.usage.reasoning')::int) as total_reasoning_tokens,
  SUM((attributes->'massgen.usage.cost')::float) as total_cost_usd
FROM records
WHERE trace_id = '[TRACE_ID]'
  AND span_name LIKE 'agent.%'
  AND attributes->>'massgen.usage.input' IS NOT NULL
GROUP BY attributes->>'massgen.agent_id'
```

#### 5b. Token Usage by Phase
```sql
-- Token usage by round type
SELECT
  attributes->>'massgen.round_type' as phase,
  SUM((attributes->'massgen.usage.input')::int) as total_input_tokens,
  SUM((attributes->'massgen.usage.output')::int) as total_output_tokens,
  COUNT(*) as round_count
FROM records
WHERE trace_id = '[TRACE_ID]'
  AND span_name LIKE 'agent.%'
  AND attributes->>'massgen.usage.input' IS NOT NULL
GROUP BY attributes->>'massgen.round_type'
```

### Step 6: Agent Behavior Analysis

**Goal:** Understand how agents collaborated and made decisions.

#### 6a. Voting Patterns
```sql
-- Who voted for whom
SELECT
  attributes->>'massgen.agent_id' as voter,
  attributes->>'massgen.voted_for_label' as voted_for,
  span_name
FROM records
WHERE trace_id = '[TRACE_ID]'
  AND span_name LIKE 'Agent vote:%'
ORDER BY start_timestamp
```

#### 6b. Answer Diversity
```sql
-- How many unique answers were generated
SELECT
  span_name,
  attributes->>'massgen.answer_label' as answer_label,
  start_timestamp
FROM records
WHERE trace_id = '[TRACE_ID]'
  AND span_name LIKE 'Agent answer:%'
ORDER BY start_timestamp
```

#### 6c. Tool Usage by Agent & Round
```sql
-- Which tools each agent used in each round
SELECT
  attributes->>'massgen.agent_id' as agent,
  attributes->>'massgen.round' as round,
  attributes->>'massgen.round_type' as round_type,
  span_name as tool,
  COUNT(*) as call_count
FROM records
WHERE trace_id = '[TRACE_ID]'
  AND span_name LIKE 'mcp.%'
GROUP BY 1, 2, 3, 4
ORDER BY agent, round::int, call_count DESC
```

#### 6d. Tool Arguments Analysis (for debugging)
```sql
-- See what arguments were passed to tools
SELECT
  span_name,
  attributes->>'arguments_preview' as arguments,
  attributes->>'output_preview' as output,
  attributes->>'massgen.agent_id' as agent,
  attributes->>'massgen.round_type' as round_type
FROM records
WHERE trace_id = '[TRACE_ID]'
  AND span_name LIKE 'Tool execution:%'
ORDER BY start_timestamp
LIMIT 20
```

#### 6e. Slowest Tool Call Details
```sql
-- Get the slowest tool call with full context
SELECT
  span_name,
  duration,
  attributes->>'arguments_preview' as arguments,
  attributes->>'output_preview' as output,
  attributes->>'massgen.agent_id' as agent,
  attributes->>'massgen.round' as round,
  attributes->>'massgen.round_type' as round_type
FROM records
WHERE trace_id = '[TRACE_ID]'
  AND span_name LIKE 'mcp.%'
ORDER BY duration DESC
LIMIT 1
```

### Step 7: LLM Performance Analysis

**Goal:** Understand LLM call timing and costs.

#### 7a. All LLM Calls with Timing
```sql
-- Get all LLM calls with duration and model
SELECT
  span_name,
  duration as duration_sec,
  attributes->>'gen_ai.request.model' as model,
  attributes->>'massgen.agent_id' as agent,
  start_timestamp
FROM records
WHERE trace_id = '[TRACE_ID]'
  AND span_name LIKE 'llm.%'
ORDER BY start_timestamp
```

#### 7b. LLM Timing Summary
```sql
-- Aggregate LLM timing stats
SELECT
  attributes->>'gen_ai.request.model' as model,
  COUNT(*) as call_count,
  ROUND(AVG(duration), 2) as avg_duration_sec,
  ROUND(MIN(duration), 2) as min_duration_sec,
  ROUND(MAX(duration), 2) as max_duration_sec,
  ROUND(SUM(duration), 2) as total_duration_sec
FROM records
WHERE trace_id = '[TRACE_ID]'
  AND span_name LIKE 'llm.%'
GROUP BY attributes->>'gen_ai.request.model'
```

#### 7c. Slowest LLM Call
```sql
-- Get the slowest LLM call with context
SELECT
  span_name,
  duration,
  attributes->>'gen_ai.request.model' as model,
  attributes->>'massgen.agent_id' as agent,
  start_timestamp
FROM records
WHERE trace_id = '[TRACE_ID]'
  AND span_name LIKE 'llm.%'
ORDER BY duration DESC
LIMIT 1
```

### Analysis Summary Template

After running the above queries, summarize findings in this format:

```
## Log Analysis Summary

**Session:** [trace_id]
**Duration:** X seconds
**Agents:** [agent_a, agent_b]
**Winner:** [agent_id]

### Correctness
- ✅/❌ All phases completed
- ✅/❌ All agents submitted answers
- ✅/❌ All agents voted
- ✅/❌ Winner selected correctly

### Efficiency

**Phase Duration Breakdown:**
| Phase | Count | Avg (s) | Max (s) | Total (s) |
|-------|-------|---------|---------|-----------|
| initial_answer | X | X.XX | X.XX | X.XX |
| voting | X | X.XX | X.XX | X.XX |
| presentation | X | X.XX | X.XX | X.XX |

**Bottleneck:** [phase/operation] took X seconds

### LLM Performance

**LLM Calls Summary:**
| Model | Calls | Avg (s) | Min (s) | Max (s) | Total (s) |
|-------|-------|---------|---------|---------|-----------|
| [model] | X | X.XX | X.XX | X.XX | X.XX |

**Slowest LLM Call:** [model] in [agent] took X.XX seconds

### Tool Performance

**Tool Calls Summary:**
| Tool | Calls | Avg (ms) | Max (ms) | Total (ms) |
|------|-------|----------|----------|------------|
| [tool] | X | X | X | X |

**Slowest Tool Call:**
- **Tool:** [mcp.server.tool_name]
- **Duration:** X.XXms
- **Agent:** [agent_id] in round [N] ([round_type])
- **Command:** [Human-readable description of what the tool did based on arguments]
- **Arguments:** `{"path": "...", ...}`

### Errors
- **Exceptions:** [count] total
- **Failed tools:** [list]
- **Agent errors:** [list]

### Cost
- **Total tokens:** X input, Y output
- **Estimated cost:** $X.XX

### Recommendations
1. [Specific optimization suggestion]
2. [Error fix needed]
3. [Pattern to investigate]
```
