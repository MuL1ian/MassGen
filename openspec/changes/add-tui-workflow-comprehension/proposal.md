# Change: Add TUI Workflow Comprehension

## Why
Users don't understand what "rounds", "answers", "votes", or "final presentation" mean. The UI assumes familiarity with multi-agent collaboration concepts. New users see technical jargon instead of understanding what's happening.

## What Changes
- Add conversational status messages that explain the workflow in plain language
- Replace jargon ("Round 2") with human descriptions ("They can see each other's ideas now...")
- Show the organic, self-directed nature of the workflow
- Make multi-agent collaboration feel like a conversation, not a pipeline

**Chosen Design: Option B - Conversational Narrator**

Examples of status messages:
- `"3 agents are thinking about this..."`
- `"They can see each other's ideas now. Claude is refining..."`
- `"Gemini thinks Claude's approach is best. Waiting for GPT..."`
- `"They agreed! Here's the final answer."`

**Key Mental Model to Communicate**:
1. Multiple agents work on your question
2. They can see each other's progress
3. They decide when to improve vs. vote for a solution
4. Process continues until they agree → final answer

## Impact
- Affected files:
  - `massgen/frontend/displays/textual_widgets/` (new status banner widget or mode_bar enhancement)
  - `massgen/frontend/displays/textual_terminal_display.py` (state tracking for status messages)
  - `massgen/frontend/displays/textual_themes/dark.tcss` (banner styling)
  - `massgen/frontend/displays/textual_themes/light.tcss` (banner styling)
