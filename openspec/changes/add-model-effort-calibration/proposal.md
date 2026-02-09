# Change: Add Model Effort Calibration

## Why

MassGen currently has inconsistent iteration behavior across models. In some runs, models terminate after a single `new_answer` and move to `vote`/`stop` too early, while others iterate much more. This makes perceived effort unpredictable and hard to align with user expectations.

### Exact Evaluation Problem

We need a reproducible way to measure and tune **model propensity to iterate** so that user-facing effort levels (`low`, `medium`, `high`) map to predictable amounts of refinement work.

Concretely, we are targeting this failure mode:
- **One-answer collapse**: model emits only 1 `new_answer` and terminates too readily.

And this product requirement:
- **Effort alignment**: effort levels should control approximate work amount, measured by `new_answer` count behavior, with model-specific calibration.

## What Changes

- **ADDED**: A Phase 0 validation experiment to confirm the calibration approach works before building full infrastructure.
- **ADDED**: Non-trivial scenario set as a hard prerequisite for any calibration (existing trivial scenarios are insufficient).
- **ADDED**: A model behavior calibration framework based on repeated single-agent runs.
- **ADDED**: Effort-level definitions (`low`, `medium`, `high`) based on normalized ratio:
  - `effort_ratio = new_answer_count / max_new_answers_per_agent`
- **ADDED**: Calibration objective using:
  - primary metric: mean `effort_ratio`
  - secondary metric: one-answer rate (`P(new_answer_count == 1)`)
- **ADDED**: Simplified tunable parameter: a shared rubric-style voting prompt with a per-model numeric threshold (single-dimensional search).
- **ADDED**: Registry of candidate/verified models for calibration (backend, model, tier, enabled/status).
- **ADDED**: Registry of calibrated per-model effort settings (per-model threshold values).
- **MODIFIED**: `massgen/tests/model_behavior` harness to support repeated trials and effort-level reporting.

## Scope Decisions (Locked)

- Effort levels are defined by `new_answer` count behavior only (for now).
- Initial calibration is shared across both voting and decomposition modes.
- Behavior remains probabilistic (no hard minimum iteration rule in this change).
- Tunable parameter is a single numeric threshold per model (not a multi-dimensional search).
- Scenario set MUST include non-trivial tasks before calibration targets are set.
- Phase 0 experiment MUST validate the approach before full infrastructure is built.

## Impact

- Affected specs: `model-effort-calibration` (new capability spec)
- Affected code:
  - `massgen/tests/model_behavior/conftest.py`
  - `massgen/tests/model_behavior/test_model_behavior.py`
  - `massgen/tests/model_behavior/model_adjustments.py`
  - `massgen/tests/model_behavior/scenarios/*` (must be expanded with non-trivial scenarios)
  - new registry/config files under `massgen/tests/model_behavior/`
  - runtime mapping surfaces in orchestrator/prompt configuration layers (gated on Phase 0 validation)
