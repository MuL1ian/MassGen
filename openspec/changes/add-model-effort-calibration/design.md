## Context

MassGen users need effort controls that feel similar to direct model usage, but multi-agent orchestration introduces additional dynamics (tool enforcement, voting/stop transitions, fairness gating). A single global prompt strategy does not produce uniform iteration behavior across providers/models.

Current test harness already measures `new_answer` and `vote` counts, but it is not yet structured as a calibration system with objective functions, repeated trials, registries, and explicit acceptance criteria.

## Goals / Non-Goals

- Goals:
  - Validate the calibration approach via a Phase 0 experiment before building full infrastructure.
  - Define `low|medium|high` effort levels with measurable targets.
  - Calibrate per-model behavior so effort levels map to predictable iteration propensity.
  - Keep effort policy probabilistic (avoid forced extra work by default).
  - Persist calibration outputs in a model registry so runtime behavior is stable and auditable.
- Non-Goals:
  - Cost or latency optimization in this change (may be added later).
  - Hard minimum iteration constraints in production behavior.
  - Full multi-agent exhaustive calibration in first pass.
  - Multi-dimensional parameter search (single threshold per model is sufficient).

## Decisions

- Decision: Use normalized effort metric.
  - `effort_ratio = new_answer_count / max_new_answers_per_agent`
  - Rationale: ratios scale across different cap values.

- Decision: Optimize two signals.
  - Primary: `mean_effort_ratio` toward target.
  - Secondary: `one_answer_rate` guardrail to detect collapse-to-one behavior.
  - Rationale: mean alone can hide pathological one-answer behavior.

- Decision: Calibrate probabilistically via repeated runs.
  - Use repeated trials per `(model, scenario, effort_level)`.
  - Rationale: reduces noise from stochastic model behavior.

- Decision: Single-agent first pass, plus light multi-agent validation.
  - Single-agent is the main calibration proxy.
  - Add a smaller follow-up validation matrix for multi-agent mode stability.
  - Rationale: balance speed and realism.

- Decision: Store two registries.
  - `models_registry`: candidate/verified models and metadata.
  - `calibration_registry`: selected per-model settings by effort level.
  - Rationale: explicit provenance and easy extension.

- Decision: Single-dimensional search space.
  - Use a shared rubric-style voting prompt across all models.
  - The only per-model tunable is a numeric threshold (controls voting propensity).
  - Rationale: keeps calibration tractable, avoids combinatorial explosion, and allows sharing prompt improvements across models.

- Decision: Phase 0 validation before infrastructure.
  - Run a lightweight experiment (repeated trials, realistic scenarios, a few models) to confirm:
    1. One-answer-collapse exists at measurable scale
    2. Threshold tuning actually moves the `effort_ratio` needle
    3. Results are stable enough to warrant registries and CI checks
  - Rationale: avoid building sophisticated infrastructure on unvalidated assumptions.

## Tunable Parameters

The calibration search space is intentionally narrow:

| Parameter | Scope | Type | Description |
|-----------|-------|------|-------------|
| Voting rubric prompt | Shared (all models) | string | A rubric-style prompt that defines when to vote vs. provide a new answer. Improved globally. |
| Voting threshold | Per-model | numeric | A single numeric value controlling voting propensity. Higher = more reluctant to vote (more iteration). |

The threshold maps to the existing `sensitivity_offset` in `model_adjustments.py`. The rubric prompt replaces ad-hoc `voting_prompt_boost` strings with a structured, shared prompt template.

## Exact Evaluation Problem Definition

Given model `m`, effort level `e`, scenario set `S`, cap `k`:

Find settings `theta(m,e)` such that:
- `E[new_answer_count / k]` is close to target ratio for `e`, and
- `P(new_answer_count == 1)` remains below effort-level threshold,
- while preserving successful task completion.

This directly targets the one-answer-collapse failure mode without imposing deterministic minimum iteration counts.

## Starter Targets

Assuming calibration cap `k = 4` for resolution:
- `low`: target ratio `0.40`
- `medium`: target ratio `0.65`
- `high`: target ratio `0.85`

Starter one-answer-rate caps:
- `low <= 0.70`
- `medium <= 0.40`
- `high <= 0.20`

## Candidate Models (Initial + Planned)

- `claude_code / claude-opus-4-5` (tier 1)
- `claude_code / claude-sonnet-4-5` (tier 1)
- `openai / gpt-5.2` (tier 1)
- `openai / gpt-5-mini` (tier 2)
- `codex / gpt-5.3-codex` (tier 1)
- `gemini / gemini-3-flash-preview` (tier 1)
- `gemini / gemini-3-pro-preview` (tier 1)
- `grok / grok-4-1-fast-reasoning` (tier 2)
- `groq / openai/gpt-oss-120b` (tier 2)
- `openrouter / moonshotai/kimi-k2.5` (tier 1)
- `openrouter / z-ai/glm-4.7` (tier 1)
- `openrouter / minimax/minimax-m2.1` (tier 1)
- `openrouter / z-ai/glm-4.7-flash` (tier 2)
- `openrouter / stepfun/step-3.5-flash:free` (tier 2)

## Risks / Trade-offs

- Provider drift: model behavior may change over time; requires periodic recalibration.
- Proxy mismatch: single-agent calibration can diverge from multi-agent runtime behavior.
- Overfitting: prompt tuning may overfit to narrow scenarios if scenario set is too trivial.

## Mitigations

- Add drift checks in CI/cron for selected models.
- Require scenario diversity (creative, analytical, technical, and at least one medium-complexity scenario).
- Add a small multi-agent spot-check suite after calibration selection.

## Migration Plan

1. **Phase 0: Validation experiment** (blocking prerequisite for all subsequent phases)
   a. Expand scenario set with non-trivial tasks (creative, technical, analytical with real complexity).
   b. Resolve open questions: tolerance bands, trial count, CI policy.
   c. Run ~10 trials x 5+ scenarios x 2-3 models (Claude, Gemini, one OpenAI).
   d. Confirm: one-answer-collapse exists, threshold tuning moves the needle, results are stable.
   e. Go/no-go decision on full infrastructure.
2. Add registries and repeated-trial test harness.
3. Run baseline calibration for initial models (sweep over threshold values).
4. Populate calibration registry for `low|medium|high`.
5. Integrate runtime mapping from user effort level to calibrated threshold.
6. Add periodic drift re-validation.

## Blocking Prerequisites (Must Be Resolved Before Calibration)

- **Acceptance tolerance bands**: Define how close `mean_effort_ratio` must be to target for each effort level (e.g., +/- 0.10).
- **Trial count N**: Define default trial count per cell and cost budget envelope.
- **CI failure policy**: Define whether drift detection fails CI or is warn-only.
- **Scenario upgrade**: Non-trivial scenarios must exist before any calibration numbers are meaningful.
