## Context
The Textual TUI already has a mode bar and a plan settings popover. Backend log analysis exists via `massgen logs analyze` and the `massgen-log-analyzer` skill, but discovery and run-target selection are not integrated into the live TUI workflow.

## Goals / Non-Goals
- Goals:
  - Make log analysis a first-class TUI mode using existing UI surfaces.
  - Provide a clear dev-vs-user analysis intent switch.
  - Add in-TUI skill discovery and session-level enable/disable controls.
  - Keep existing plan/execute flows stable.
- Non-Goals:
  - Persist skill toggle preferences across sessions.
  - Replace existing backend log analysis implementation.
  - Add a new standalone analysis app.

## Decisions
- Decision: Reuse existing plan toggle and popover instead of adding separate mode widgets.
  - Why: Lower UI complexity and consistent interaction model.
- Decision: Represent analysis as a new `plan_mode` state (`analysis`) rather than a separate top-level mode type.
  - Why: Existing code paths and keyboard behavior are already centered on this state machine.
- Decision: Apply skill toggles by prompt filtering (system prompt skills section) rather than filesystem/container mutation.
  - Why: Session-local behavior with minimal risk and no mount lifecycle churn.
- Decision: User profile mode avoids default Linear issue creation, favoring skill synthesis with explicit confirmation before writes.
  - Why: Matches end-user workflow requirements.

## Risks / Trade-offs
- Risk: Overloading the plan popover could confuse users.
  - Mitigation: Mode-specific title/content and unchanged plan controls outside analysis.
- Risk: Prompt-only skill filtering does not hard-block tool execution.
  - Mitigation: Documented as session-level guidance behavior for v1.
- Risk: Skill draft extraction can fail if output is unstructured.
  - Mitigation: Add explicit tagged output instruction in analysis-user prompt and fallback behavior when missing.

## Migration Plan
1. Land mode/state and popover event changes.
2. Land skills modal + session filter wiring.
3. Land analysis prompt/target integration and skill-creation confirmation flow.
4. Add/extend tests and validate OpenSpec change.

## Open Questions
- None (implementation defaults selected during planning conversation).
