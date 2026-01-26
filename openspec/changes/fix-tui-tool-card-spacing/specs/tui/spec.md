## ADDED Requirements

### Requirement: Compact Tool Card Spacing
Consecutive tool call cards in the TUI SHALL have minimal vertical spacing to maintain visual cohesion.

#### Scenario: Multiple tool calls display compactly
- **WHEN** multiple tool calls execute in sequence
- **THEN** the tool cards appear with minimal gap between them (no more than 1 row)
- **AND** visual separation is maintained via left border styling only
