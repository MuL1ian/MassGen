# Model Effort Calibration

## ADDED Requirements

### Requirement: Phase 0 Validation SHALL Precede Full Infrastructure
The system SHALL validate the calibration approach via a lightweight experiment before building registries, sweep workflows, or CI drift checks.

#### Scenario: Phase 0 experiment gates further work
- **WHEN** the Phase 0 experiment is run
- **THEN** it SHALL confirm that one-answer-collapse exists at measurable scale
- **AND** confirm that threshold tuning moves `effort_ratio` meaningfully
- **AND** confirm that results are stable across repeated trials
- **AND** produce a go/no-go recommendation for full infrastructure

### Requirement: Scenarios SHALL Be Non-Trivial Before Calibration
The scenario set used for calibration SHALL include tasks where iteration genuinely improves outcomes. Trivially simple tasks (e.g., "add two numbers") SHALL NOT be the sole basis for calibration targets.

#### Scenario: Scenario diversity prerequisite
- **WHEN** calibration targets are set for any effort level
- **THEN** the scenario set SHALL include at least 5 scenarios
- **AND** at least 2 SHALL be non-trivial (medium complexity or higher)
- **AND** the set SHALL cover creative, technical, and analytical task classes

### Requirement: Tunable Parameters SHALL Be a Shared Rubric Prompt Plus Per-Model Threshold
The calibration search space SHALL consist of a shared rubric-style voting prompt (improved globally) and a single per-model numeric threshold controlling voting propensity.

#### Scenario: Single-dimensional calibration search
- **WHEN** calibration is performed for a model and effort level
- **THEN** the system SHALL search over a single numeric threshold value
- **AND** use the shared rubric prompt for all models
- **AND** NOT perform multi-dimensional parameter searches

### Requirement: Effort Levels SHALL Be Defined by New-Answer Behavior
The system SHALL define user-facing effort levels (`low`, `medium`, `high`) using `new_answer` count behavior only in this phase.

#### Scenario: Effort metric computed from answer counts
- **WHEN** a calibration run completes for a model
- **THEN** the system SHALL compute `new_answer_count`
- **AND** compute `effort_ratio = new_answer_count / max_new_answers_per_agent`
- **AND** store these metrics in calibration outputs

### Requirement: Calibration SHALL Target a Dual-Metric Objective
The system SHALL calibrate each model and effort level against:
1. Target mean effort ratio
2. One-answer collapse risk (`P(new_answer_count == 1)`)

#### Scenario: Model-level calibration scoring
- **WHEN** repeated trials are run for `(model, scenario_set, effort_level)`
- **THEN** the system SHALL compute aggregate `mean_effort_ratio`
- **AND** compute aggregate `one_answer_rate`
- **AND** score candidate settings using both metrics

#### Scenario: One-answer-collapse is explicitly penalized
- **WHEN** two candidate settings have similar mean effort ratio
- **AND** one has higher one-answer rate
- **THEN** the system SHALL rank the lower one-answer-rate candidate higher

### Requirement: Calibration SHALL Be Model-Specific and Registry-Backed
The system SHALL maintain explicit registries for model candidates and calibrated settings.

#### Scenario: Candidate model registry
- **WHEN** calibration tests are configured
- **THEN** the model registry SHALL provide at least `backend`, `model`, `tier`, `enabled`, and `status` fields per model

#### Scenario: Calibrated setting registry
- **WHEN** calibration selection finishes for a model and effort level
- **THEN** the calibration registry SHALL persist the selected threshold value and calibration metadata

### Requirement: Calibration SHALL Use Repeated Trials
The system SHALL support repeated-run sampling for each test cell to reduce stochastic noise.

#### Scenario: Repeated trial execution
- **WHEN** a test cell `(model, scenario, effort_level)` is executed with trial count `N`
- **THEN** the harness SHALL run `N` independent executions
- **AND** report aggregated statistics across trials

### Requirement: Calibration SHALL Be Probabilistic by Default
The calibrated effort policy SHALL remain probabilistic and SHALL NOT require hard minimum iteration counts in this phase.

#### Scenario: No hard minimum required
- **WHEN** runtime effort policy is applied for a calibrated model
- **THEN** terminal actions SHALL remain allowed without enforcing deterministic minimum `new_answer` count
- **AND** expected effort SHALL be governed by calibrated propensity targets

### Requirement: First-Pass Policy SHALL Apply to Voting and Decomposition
The initial calibration mapping SHALL apply uniformly to both voting and decomposition coordination modes.

#### Scenario: Shared effort mapping across coordination modes
- **WHEN** user selects effort level `medium`
- **AND** run mode is either voting or decomposition
- **THEN** the resolved model-specific effort setting SHALL be the same first-pass mapping

### Requirement: Calibration Harness SHALL Surface the Exact Evaluation Problem
The harness documentation and outputs SHALL explicitly state that calibration targets the one-answer-collapse problem while preserving probabilistic control of effort.

#### Scenario: Evaluation-problem visibility
- **WHEN** a developer runs model-behavior calibration tests
- **THEN** generated summaries SHALL include the explicit problem statement
- **AND** include one-answer-rate metrics alongside effort ratio metrics
