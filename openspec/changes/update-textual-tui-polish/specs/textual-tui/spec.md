## ADDED Requirements

### Requirement: Tool Card Time Alignment
The tool card header SHALL display the elapsed time on the right side of the card, aligned with the card border.

#### Scenario: Tool card time position
- **WHEN** a tool card is displayed
- **THEN** the time (e.g., "(0.0s)") SHALL appear on the far right of the header row
- **AND** the tool name SHALL appear on the left

### Requirement: Clean Tool Card Labels
Tool cards SHALL NOT display redundant status indicators or type labels.

#### Scenario: Tool card without redundant labels
- **WHEN** a successful tool card is displayed
- **THEN** it SHALL NOT show a green check emoji before the time
- **AND** it SHALL NOT show "[MCP Tool]" text after the result

### Requirement: Current Workspace Option
The Workspace Browser modal SHALL provide access to the current active workspace.

#### Scenario: Current workspace in dropdown
- **WHEN** the Workspace Browser modal is opened during coordination
- **THEN** "Current Workspace" SHALL appear as the first option in the dropdown
- **AND** it SHALL be selected by default
- **AND** selecting it SHALL show files from the active workspace directory

### Requirement: Reverse Chronological Ordering
All lists of answers, events, and activities SHALL display items in reverse chronological order (most recent first).

#### Scenario: Answer list ordering
- **WHEN** answers are displayed in any modal (Answer Browser, Unified Browser)
- **THEN** the most recent answer SHALL appear first (at the top)
- **AND** older answers SHALL follow in descending order by timestamp

#### Scenario: Timeline event ordering
- **WHEN** timeline events are displayed
- **THEN** the most recent event SHALL appear first
- **AND** older events SHALL follow in descending order

### Requirement: Modal Width Optimization
Modal dialogs SHALL use sufficient width to display content clearly without excessive vertical scrolling.

#### Scenario: BrowserTabsModal width
- **WHEN** the Unified Browser modal is opened
- **THEN** it SHALL use at least 90% of screen width
- **AND** max-width SHALL be at least 140 characters

#### Scenario: Tool Detail Modal width
- **WHEN** the Tool Detail modal is opened
- **THEN** it SHALL use at least 80% of screen width
- **AND** max-width SHALL be at least 120 characters

### Requirement: Cancel Button Visibility
The Cancel button SHALL be visible and functional during coordination execution.

#### Scenario: Cancel button during execution
- **WHEN** coordination is running (agents are working)
- **THEN** a Cancel button SHALL be visible in the bottom status area
- **AND** pressing 'q' or clicking Cancel SHALL stop the current turn

### Requirement: Full Width Content
Scrollable content areas SHALL extend to the full width of their container.

#### Scenario: Timeline container width
- **WHEN** the agent panel is displayed
- **THEN** the timeline container SHALL extend to the right edge of the screen
- **AND** the scrollbar SHALL appear at the right edge

### Requirement: Clean Hook Result Display
Hook results displayed in tool modals SHALL be cleaned of injection markers.

#### Scenario: Hook result formatting
- **WHEN** a hook result is displayed in the Tool Detail modal
- **THEN** injection markers (e.g., "[INJECTION]", banner text) SHALL be stripped
- **AND** only the meaningful result content SHALL be shown

## MODIFIED Requirements

### Requirement: Help Modal Keybinding Accuracy
The help modal SHALL accurately reflect all available keybindings.

#### Scenario: Removed keybinding not shown
- **WHEN** the help modal is displayed
- **THEN** the 'f' keybinding SHALL NOT be listed
- **AND** all listed keybindings SHALL correspond to functional actions
