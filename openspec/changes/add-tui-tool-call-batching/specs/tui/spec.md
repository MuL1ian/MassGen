## ADDED Requirements

### Requirement: Tool Call Batching Display
The TUI SHALL group consecutive tool calls from the same MCP server into a batched display.

#### Scenario: Consecutive filesystem calls are batched
- **WHEN** 5 consecutive `filesystem/write_file` tool calls execute
- **THEN** they are displayed as a single `ToolBatchCard`
- **AND** the header shows the server name and total call count (e.g., "filesystem (5 calls)")
- **AND** individual calls are shown in a tree structure below

#### Scenario: Mixed server calls are not batched together
- **WHEN** tool calls alternate between different MCP servers
- **THEN** each server's calls are batched separately
- **AND** the display shows separate batch cards for each server

### Requirement: Tree View Auto-Collapse
The batched tool card tree view SHALL auto-collapse when showing more than 3 items.

#### Scenario: Large batch shows collapsed view
- **WHEN** a batch contains more than 3 tool calls
- **THEN** the first 3 calls are shown
- **AND** a "+N more" indicator shows remaining count
- **AND** clicking the indicator expands to show all calls

#### Scenario: Small batch shows all items
- **WHEN** a batch contains 3 or fewer tool calls
- **THEN** all calls are displayed without collapse indicator

### Requirement: Batch Tool Results
Tool results within a batch SHALL display correctly mapped to their source call.

#### Scenario: Tool result displays within batch
- **WHEN** a tool call in a batch completes with a result
- **THEN** the result is displayed inline with the corresponding tree item
- **AND** the batch header shows overall completion status
