## MODIFIED Requirements

### Requirement: The system SHALL support a plan mode where queries create plans for approval before execution.
The system SHALL support a plan mode where queries create plans for approval before execution.

#### Scenario: Shift+Tab cycles through planning and analysis states
- **WHEN** the user presses `Shift+Tab`
- **THEN** the mode cycle SHALL be `normal -> plan -> execute -> analysis -> normal`
- **AND** the mode bar SHALL reflect the current state.

#### Scenario: Analysis state uses the existing mode settings surface
- **WHEN** the mode is `analysis`
- **THEN** pressing the mode settings button (`⋮`) SHALL open the existing popover surface
- **AND** the popover content SHALL switch to analysis controls (profile and log target) instead of plan-depth controls.


## ADDED Requirements

### Requirement: The Textual TUI SHALL support profile-based log analysis behavior.
The system SHALL provide `dev` and `user` analysis profiles in analysis mode.

#### Scenario: Dev profile focus
- **WHEN** analysis profile is `dev`
- **THEN** analysis prompt construction SHALL prioritize internal MassGen behavior debugging and improvement workflows.

#### Scenario: User profile focus
- **WHEN** analysis profile is `user`
- **THEN** analysis prompt construction SHALL prioritize reusable skill creation/refinement
- **AND** SHALL avoid default issue-tracking actions unless explicitly requested.


### Requirement: The Textual TUI SHALL provide skill discovery and session-level skill toggles.
The system SHALL display discovered skills grouped by source and allow session-only enable/disable control.

#### Scenario: Skill grouping
- **WHEN** the skills manager is opened
- **THEN** skills SHALL be grouped into `Default` (built-in) and `Created` (user/project/previous-session evolving).

#### Scenario: Session-only toggles
- **WHEN** a skill is toggled off in the skills manager
- **THEN** the change SHALL apply to subsequent turns in the current TUI session
- **AND** SHALL NOT persist to user settings or YAML files.


### Requirement: Analysis mode SHALL target log sessions and turns from the TUI.
The system SHALL expose analysis target selection for log session and turn.

#### Scenario: Default analysis target
- **WHEN** the user enters analysis mode
- **THEN** the default target SHALL be the current session latest available turn if present
- **AND** fallback to the latest global log session when current-session logs are unavailable.

#### Scenario: View report action
- **WHEN** the user chooses to view the analysis report from the analysis popover
- **THEN** the system SHALL open `ANALYSIS_REPORT.md` for the selected target turn when present
- **AND** show a non-fatal warning when the report does not exist.
