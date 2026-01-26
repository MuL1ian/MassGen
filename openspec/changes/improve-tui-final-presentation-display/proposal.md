# Change: Fix TUI Final Presentation Display (CRITICAL)

## Why
The final presentation - the most important output for users - shows only partial reasoning text (e.g., `**Prioritizing Poetic Depth**`, `**Refining and Combining Concepts**`) but not the actual final answer/poem. Users cannot see the output they requested.

## What Changes
- Investigate and fix content filtering in `ContentNormalizer.should_display` logic
- Ensure actual answer content streams to `FinalPresentationCard`, not filtered out
- Potentially separate reasoning display from answer display in final presentation
- Add visual distinction between reasoning (collapsed/smaller) and answer (prominent)

**Root Cause Hypotheses:**
1. `ContentNormalizer.should_display` may filter answer content incorrectly
2. Reasoning chunks may push actual content out of view
3. Content may not be received at all from the orchestrator's `get_final_presentation()`

**Investigation Path:**
1. Check `content_normalizer.py` - `normalize()` and `should_display` logic
2. Check `PresentationContentHandler.process()` in `content_handlers.py`
3. Verify `FinalPresentationCard.append_chunk()` receives all content
4. Add debug logging to trace where content gets lost

## Impact
- Affected files:
  - `massgen/frontend/displays/content_normalizer.py` (primary investigation)
  - `massgen/frontend/displays/content_handlers.py` (PresentationContentHandler)
  - `massgen/frontend/displays/textual_widgets/content_sections.py` (FinalPresentationCard)
  - `massgen/frontend/displays/textual_terminal_display.py`
