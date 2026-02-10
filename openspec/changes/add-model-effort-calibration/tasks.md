# Tasks: Add Model Effort Calibration

## 0. Blocking Prerequisites

These MUST be completed before any calibration work (sections 4-6) begins.

### 0a. Resolve Open Questions

- [ ] 0a.1 Define acceptance tolerance bands for `mean_effort_ratio` per effort level (e.g., target +/- 0.10)
- [ ] 0a.2 Define default trial count `N` per cell and cost budget envelope
- [ ] 0a.3 Define CI failure policy: fail on drift vs. warn-only

### 0b. Scenario Upgrade (prerequisite for all calibration)

- [ ] 0b.1 Audit current scenarios — all 3 are trivially simple and will not produce meaningful calibration data
- [ ] 0b.2 Add at least 2 non-trivial scenarios where iteration genuinely improves outcomes (e.g., "design a REST API", "refactor code to handle edge cases")
- [ ] 0b.3 Ensure scenario set covers creative, technical, and analytical task classes at non-trivial difficulty
- [ ] 0b.4 Add scenario metadata (difficulty/category) for reporting slices
- [ ] 0b.5 Aim for 5+ total scenarios with a mix of simple and medium complexity

## 1. Phase 0: Validation Experiment

Gated on: section 0 complete. Go/no-go decision for sections 4-8.

- [ ] 1.1 Run ~10 trials x 5+ scenarios x 2-3 models (Claude, Gemini, one OpenAI/Codex)
- [ ] 1.2 Confirm one-answer-collapse exists at measurable scale (not just anecdotal)
- [ ] 1.3 Confirm threshold tuning actually moves `effort_ratio` (vary threshold, measure effect)
- [ ] 1.4 Confirm results are stable enough across trials to warrant per-model calibration
- [ ] 1.5 Write up Phase 0 findings and go/no-go recommendation

## 2. Registry and Data Model

Gated on: Phase 0 go decision.

- [ ] 2.1 Add `models_registry` file under `massgen/tests/model_behavior/` with fields: `backend`, `model`, `tier`, `enabled`, `status`, `notes`
- [ ] 2.2 Seed registry with current initial models (Claude + Gemini + Codex)
- [ ] 2.3 Add planned-model entries from the agreed candidate list (disabled by default until verified), including `codex / gpt-5.3-codex`
- [ ] 2.4 Add `calibration_registry` file keyed by model and effort level with selected threshold and calibration metadata

## 3. Metrics and Objective

Gated on: Phase 0 go decision.

- [ ] 3.1 Add metric extraction for `new_answer_count` and `max_new_answers_per_agent`
- [ ] 3.2 Compute `effort_ratio = new_answer_count / max_new_answers_per_agent`
- [ ] 3.3 Compute `one_answer_rate` across repeated trials
- [ ] 3.4 Implement calibration objective scoring (`target_ratio` distance + one-answer penalty)

## 4. Test Harness Extensions

Gated on: Phase 0 go decision.

- [ ] 4.1 Extend `test_model_behavior.py` to run repeated trials per `(model, scenario, effort_level)`
- [ ] 4.2 Add effort level abstraction (`low`, `medium`, `high`) mapping to per-model threshold values
- [ ] 4.3 Add CLI options for trial count and effort-level filtering
- [ ] 4.4 Persist per-run and aggregated metrics into structured outputs in `debug_output/`
- [ ] 4.5 Emit summary tables including mean ratio, variance, and one-answer rate

## 5. Calibration Selection Workflow

Gated on: sections 2-4 complete.

- [ ] 5.1 Implement threshold sweep for each model/effort level (single-dimensional search over voting threshold)
- [ ] 5.2 Select best threshold by objective and write to `calibration_registry`
- [ ] 5.3 Add deterministic output format for storing calibration runs (timestamp, sample size, scenario set, selected threshold)
- [ ] 5.4 Add validation command/test that replays selected thresholds and checks acceptance bands

## 6. Runtime Integration

Gated on: section 5 complete.

- [ ] 6.1 Add user-facing effort-level config (`low|medium|high`) wiring to resolved per-model threshold
- [ ] 6.2 Apply mapping uniformly for voting and decomposition modes (first-pass shared policy)
- [ ] 6.3 Add fallback behavior for unknown/unverified models

## 7. Documentation

- [ ] 7.1 Document the exact evaluation problem and calibration objective in user/developer docs
- [ ] 7.2 Document effort-level semantics as probabilistic targets (not hard minimum iterations)
- [ ] 7.3 Document the tunable parameter model (shared rubric prompt + per-model threshold)
- [ ] 7.4 Document registry schema and how to onboard new models

## 8. Verification

Gated on: section 5 complete.

- [ ] 8.1 Run expensive model-behavior suite for initial models with repeated trials
- [ ] 8.2 Run a small multi-agent spot-check to confirm single-agent calibration transfers
- [ ] 8.3 Record calibration artifacts and acceptance outcomes in PR_DRAFT.md
