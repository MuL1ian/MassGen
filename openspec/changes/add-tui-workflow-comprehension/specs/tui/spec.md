## ADDED Requirements

### Requirement: Conversational Workflow Status
The TUI SHALL display conversational status messages that explain the multi-agent workflow in plain language.

#### Scenario: Initial working phase
- **WHEN** multiple agents begin working on a question
- **THEN** the status displays a message like "3 agents are thinking about this..."
- **AND** the message uses casual, human language (not technical jargon)

#### Scenario: Agents sharing progress
- **WHEN** agents can see each other's work and are iterating
- **THEN** the status displays a message like "They can see each other's ideas now. Claude is refining..."
- **AND** the message identifies which agent(s) are actively working

#### Scenario: Votes being cast
- **WHEN** one or more agents vote for another's solution
- **THEN** the status displays a message like "Gemini thinks Claude's approach is best. Waiting for GPT..."
- **AND** the message shows who voted for whom and who is still deciding

#### Scenario: Consensus reached
- **WHEN** agents reach consensus on the best solution
- **THEN** the status displays a message like "They agreed! Here's the final answer."
- **AND** the transition to final presentation is clear to the user

### Requirement: Jargon-Free Language
The workflow status messages SHALL NOT use technical terms that assume familiarity with multi-agent systems.

#### Scenario: No technical jargon displayed
- **WHEN** any workflow status message is displayed
- **THEN** it does NOT use terms like "round", "enforcement phase", "convergence", or "coordination"
- **AND** it uses simple descriptions like "thinking", "refining", "agreed"
