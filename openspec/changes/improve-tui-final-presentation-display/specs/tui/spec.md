## ADDED Requirements

### Requirement: Complete Final Presentation Display
The TUI final presentation card SHALL display the complete final answer/output, not just reasoning fragments.

#### Scenario: Final answer fully visible
- **WHEN** a multi-agent session completes and produces a final presentation
- **THEN** the complete final answer (poem, solution, etc.) is displayed in the FinalPresentationCard
- **AND** the answer content is not truncated or filtered

#### Scenario: Reasoning does not obscure answer
- **WHEN** the final presentation includes both reasoning text and the actual answer
- **THEN** the actual answer is prominently displayed
- **AND** reasoning text does not push the answer out of view

### Requirement: Content Filtering Preserves Answers
The `ContentNormalizer` SHALL NOT filter out substantive answer content from final presentations.

#### Scenario: Answer content passes through normalizer
- **WHEN** final answer content is processed by ContentNormalizer
- **THEN** the `should_display` method returns true for answer content
- **AND** the content reaches the FinalPresentationCard unchanged
