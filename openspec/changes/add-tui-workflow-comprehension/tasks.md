## 1. Design

- [ ] 1.1 Identify where status messages should be displayed (mode bar area, header, or dedicated widget)
- [ ] 1.2 Define all workflow states and their corresponding conversational messages
- [ ] 1.3 Determine how to track agent states (working, voted, refining) for message generation

## 2. Implementation

- [ ] 2.1 Create status message generator that produces conversational text based on workflow state
- [ ] 2.2 Add/modify widget to display the conversational status messages
- [ ] 2.3 Wire up state changes from orchestrator to update status messages
- [ ] 2.4 Add CSS styling for status message display

## 3. Message Catalog

Status messages to implement:
- [ ] 3.1 Initial: "N agents are thinking about this..."
- [ ] 3.2 Sharing: "They can see each other's ideas now. [Agent] is refining..."
- [ ] 3.3 Voting: "[Agent] thinks [OtherAgent]'s approach is best. Waiting for [remaining]..."
- [ ] 3.4 Consensus: "They agreed! Here's the final answer."
- [ ] 3.5 Edge cases: single agent, no votes yet, mixed states

## 4. Testing

- [ ] 4.1 Test with multi-agent config to verify messages update correctly
- [ ] 4.2 Test message transitions through full workflow
- [ ] 4.3 Verify messages are readable and not truncated
