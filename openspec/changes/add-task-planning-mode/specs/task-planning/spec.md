## ADDED Requirements

### Requirement: Task Planning CLI Mode

The system SHALL provide a `--plan` CLI flag that enables task planning mode, where agents interactively create structured feature lists.

#### Scenario: Basic task planning invocation
- **WHEN** user runs `massgen --plan "Build a REST API"`
- **THEN** agents receive task planning instructions prepended to the question
- **AND** agents can explore the codebase (cwd auto-added to context_paths)
- **AND** agents can ask user clarifying questions via `ask_others`
- **AND** winning agent writes `feature_list.json` and supporting docs

#### Scenario: Plan depth control
- **WHEN** user runs `massgen --plan --plan-depth deep "Build a REST API"`
- **THEN** agents receive depth-specific instructions targeting 100-200+ tasks
- **AND** feature list contains granular step-by-step tasks

### Requirement: Plan Depth Configuration

The system SHALL support a `--plan-depth` CLI flag with values `shallow`, `medium`, or `deep` to control task granularity.

#### Scenario: Shallow depth
- **WHEN** `--plan-depth shallow` is specified
- **THEN** agents target 5-10 high-level phases/milestones
- **AND** instructions specify "high-level phases only"

#### Scenario: Medium depth (default)
- **WHEN** `--plan-depth medium` is specified or `--plan` without depth
- **THEN** agents target 20-50 tasks organized in sections
- **AND** instructions specify "sections with tasks"

#### Scenario: Deep depth
- **WHEN** `--plan-depth deep` is specified
- **THEN** agents target 100-200+ granular tasks
- **AND** instructions specify "granular step-by-step"

### Requirement: Interactive Planning Process

The system SHALL enable interactive planning where agents ask users clarifying questions throughout the planning process.

#### Scenario: User questions enabled
- **WHEN** `--plan` is specified
- **THEN** `broadcast` is set to `"user"` automatically
- **AND** `ask_others` tool routes questions to the user
- **AND** user responses influence the plan

#### Scenario: Codebase exploration enabled
- **WHEN** `--plan` is specified
- **THEN** current working directory is added to `context_paths`
- **AND** agents can explore files in the codebase

### Requirement: Structured Feature List Output

The system SHALL output a structured `feature_list.json` file with features containing id, name, description, status, dependencies, and priority.

#### Scenario: Feature list format
- **WHEN** planning completes successfully
- **THEN** `feature_list.json` contains an array of feature objects
- **AND** each feature has: id (e.g., "F001"), name, description, status ("pending"), dependencies (array of ids), priority ("high"|"medium"|"low")
- **AND** dependencies form a valid DAG (no cycles)
