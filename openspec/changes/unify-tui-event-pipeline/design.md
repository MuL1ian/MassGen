## Context
The main Textual TUI currently renders from parsed stream output, while subagent views render from events.jsonl via ContentProcessor. This causes visual and behavioral drift between the main TUI and subagent TUI.

## Goals / Non-Goals
- Goals:
  - Single source of truth for TUI rendering based on MassGen events.
  - Identical timeline rendering for main and subagent views.
  - Inner agent tabs in subagent view show agent_id + model name and allow filtering.
- Non-Goals:
  - Redesigning the overall TUI layout or styles.
  - Replacing the existing event schema (only consumption path changes).

## Decisions
- Decision: Use MassGen events as the authoritative input for TimelineSection rendering in both main and subagent views.
  - Why: events.jsonl already exists, is structured, and is used by subagent views; aligning the main TUI removes drift.
- Decision: Introduce/standardize a shared adapter that takes MassGenEvent streams (live or file) and feeds ContentProcessor + TimelineSection.
  - Why: Avoid duplicating parsing logic across views.
- Decision: Inner agent tabs in subagent view are derived from execution_metadata.yaml (preferred) or event agent_id fields.
  - Why: Matches main TUI display and supports multi-agent subagent orchestrator mode.

## Risks / Trade-offs
- Risk: Some content currently only appears in stream parsing; missing event emission would drop content.
  - Mitigation: audit and add event emission for all timeline-relevant content before switching main TUI.
- Risk: Performance regressions if event emission volume increases.
  - Mitigation: keep event payloads compact; reuse existing event emission where possible.

## Migration Plan
1. Build shared adapter and run main TUI through it behind a flag.
2. Fill event emission gaps and verify parity between old and new pipelines.
3. Flip default to event-driven pipeline; keep raw parsing as fallback only if needed.

## Open Questions
- Do we need a short-lived compatibility window where both pipelines run for debugging?
- Should events include additional fields to avoid reconstructing missing UI context?
