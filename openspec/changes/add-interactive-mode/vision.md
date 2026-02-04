# Interactive Mode Vision

What MassGen looks like when interactive mode is fully realized — the workflows it enables and what a session feels like.

## The Core Experience

You open MassGen and talk to it like a collaborator. It knows your project, remembers what you've done, and decides when to bring in the full multi-agent team vs. handle something itself. You never have to think about "should this be a single-agent task or a multi-agent run?" — the interactive agent makes that call, and you can override it.

## Example Workflows

### 1. Building a Feature End-to-End

```
You:  "I need to add WebSocket support to the API server."

MassGen: I'll start by having the team plan the approach.
         [launches planning run → 3 agents discuss architecture]

         The team recommends:
         1. Add ws library dependency
         2. Create WebSocket handler module
         3. Update routing layer
         4. Add connection lifecycle management
         5. Write integration tests

         I've broken this into 3 scoped runs. Starting with the handler module.
         [launches execution run #1 → agents implement handler]

         Handler module is done. Let me verify it before moving on.
         [launches verification run → single agent reviews code]

         Looks good. Moving to routing integration.
         [launches execution run #2]

         ...

You:  "Actually, can we use Socket.IO instead of raw WebSockets?"

MassGen: Got it. I'll adjust the remaining work. Run #2 already touched routing
         but hasn't merged yet — I'll rerun that chunk with Socket.IO context.
         [relaunches run #2 with updated context]
```

**What's happening**: Plan decomposition, chained execution, result evaluation between runs, human feedback mid-workflow, context-aware reruns.

### 2. Quick Questions Mixed with Deep Work

```
You:  "What's the current test coverage for the auth module?"

MassGen: Based on the coverage report in workspace/coverage.json,
         the auth module has 78% line coverage. The gaps are in
         the OAuth refresh flow and the rate limiter.

You:  "Fix those coverage gaps."

MassGen: That's substantial work — I'll run the team on it.
         [launches multi-agent run with refinement]

         Done. Coverage is now at 94%. The team added 12 new tests.
         Here's a summary of what was added: ...

You:  "What's our deploy status?"

MassGen: The last deploy was 2 hours ago, commit abc123.
         CI is green on main.
```

**What's happening**: The agent answers simple questions directly (no run needed), delegates complex work to multi-agent coordination, and switches seamlessly between the two.

### 3. Run Debugging with Log Analysis

```
You:  "That last run seemed slow and the agents kept going in circles."

MassGen: Let me analyze the run logs.
         [launches log analysis on the previous run's logdir]

         Found the issue — agents 1 and 3 were producing nearly
         identical answers each round but voting each other down
         on minor style differences. This caused 4 extra refinement
         rounds with no meaningful progress.

         Recommendations:
         - Increase voting leniency for this type of task
         - Use 2 agents instead of 3 to reduce redundant perspectives

You:  "Rerun it with those settings."

MassGen: [launches run with 2 agents and lenient voting config]

         Done in 2 rounds instead of 6. Same quality output.
         Here's the result: ...
```

**What's happening**: The interactive agent uses MassGen's log analysis tooling to diagnose coordination problems in its own runs, then applies the learnings to a follow-up run with adjusted configuration.

### 4. Code Review and Iteration

```
You:  "Review PR #247."

MassGen: [launches multi-agent review run — agents independently review]

         Three agents reviewed the PR. Consensus issues:
         - SQL injection risk in the search endpoint (all 3 flagged)
         - Missing index on the new `status` column (2 of 3 flagged)
         - Test for edge case when input is empty array (2 of 3 flagged)

         One agent also suggested refactoring the query builder,
         but the others disagreed — it's fine as-is.

You:  "Fix the consensus issues but skip the refactor."

MassGen: [launches execution run with scoped context: just the 3 issues]

         All three fixed. Updated the PR. Want me to re-review?

You:  "Yes, quick single-agent check is fine."

MassGen: [launches single-agent run, no refinement]

         Looks clean. The SQL parameterization is correct, index migration
         is in place, and the edge case test passes.
```

**What's happening**: Multi-agent review for thoroughness, user selects which feedback to act on, scoped execution run, quick single-agent verification. The user naturally tells the agent what run mode to use ("quick single-agent check").

### 5. Research and Analysis

```
You:  "I need to decide between Kafka and RabbitMQ for our event bus.
       We have ~10k events/sec, need exactly-once delivery, and
       the team knows Python best."

MassGen: I'll have the team research this independently so we get
         diverse perspectives.
         [launches multi-agent run, no refinement — want independent opinions]

         Three perspectives:
         - Agent 1 recommends Kafka (throughput, partitioning)
         - Agent 2 recommends RabbitMQ (simpler ops, good Python libs)
         - Agent 3 recommends Kafka but flags operational complexity

         Key tradeoff: Kafka handles your throughput with room to grow,
         but RabbitMQ is operationally simpler for a Python-first team.

         Want me to have them debate and converge on a recommendation?

You:  "Yes."

MassGen: [launches multi-agent run with refinement on the same question,
          with the initial research as context]

         After deliberation, the team recommends Kafka with a managed
         service (Confluent/MSK) to reduce ops burden. The Python
         ecosystem concern is addressed by confluent-kafka-python which
         is mature. Here's the full analysis: ...
```

**What's happening**: First run gathers independent perspectives (no refinement), second run drives consensus (with refinement). The interactive agent sequences these strategically.

### 6. Project Continuity Across Sessions

```
[Session 1 - Monday]
You:  "Start a new project: migrate the user service to gRPC."

MassGen: Created project workspace at workspace/projects/grpc-migration/.
         I've initialized CONTEXT.md with the project goals.
         Let me plan the migration.
         [launches planning run]

         Here's the migration plan (14 tasks across 4 phases)...
         [saves plan to deliverables/migration_plan.md]

[Session 2 - Tuesday]
You:  "Continue the gRPC migration."

MassGen: [reads CONTEXT.md and deliverables/]

         Last session we completed Phase 1 (proto definitions) and
         started Phase 2 (server implementation). The health check
         and user CRUD endpoints are done. Remaining in Phase 2:
         - Authentication interceptor
         - Rate limiting interceptor

         Want me to continue with the auth interceptor?
```

**What's happening**: Project workspace persists on disk. The interactive agent reads CONTEXT.md and deliverables to reconstruct where things left off, even across separate CLI invocations.

### 7. Human-in-the-Loop with Approval

```
You:  "Refactor the entire database layer to use SQLAlchemy 2.0 style."

MassGen: That's a large change. I'll plan it first.
         [launches planning run]

         Plan ready — 23 files affected, 4 phases. I'd like to
         execute Phase 1 (model definitions) first.

         ┌─────────────────────────────────────────┐
         │ Run Approval                            │
         │                                         │
         │ Task: Migrate model definitions to      │
         │       SQLAlchemy 2.0 mapped_column()    │
         │                                         │
         │ Agents: claude-opus, gpt-4o, gemini-2   │
         │ Mode: Multi-agent with refinement       │
         │ Files: models/*.py (8 files)            │
         │                                         │
         │ [Approve]  [Edit]  [Cancel]             │
         └─────────────────────────────────────────┘

You:  [clicks Edit, removes gemini-2 from agents]
      [clicks Approve]

MassGen: [runs with 2 agents]
```

**What's happening**: Approval modal gives the user visibility and control before expensive runs. They can adjust agents, scope, or cancel entirely.

## What Makes This Different

**vs. Single-agent coding assistants** (Copilot, Cursor, Claude Code): MassGen brings multiple agents with different perspectives. The interactive agent knows when one brain is enough and when you need three.

**vs. Current MassGen**: No more one-shot task execution. The interactive layer maintains context, chains runs, evaluates results, and adapts. It's the difference between a single function call and a REPL.

**vs. Agentic frameworks** (AutoGPT, CrewAI): MassGen's multi-agent coordination (voting, refinement, broadcast) is the execution engine. The interactive layer is the orchestration and context management on top — not a replacement for human judgment, but an amplifier.

## The Feel

The interactive agent should feel like a **senior technical lead** who:
- Answers quick questions without ceremony
- Delegates complex work to specialist teams
- Breaks big problems into manageable chunks
- Checks work before moving on
- Remembers what you've been working on
- Asks when it's unsure, acts when it's confident
