# Change: Fix TUI Mode Bar Alignment

## Why
The mode bar extends further left than the input box below it, creating a visual misalignment that disrupts the polished appearance of the TUI input area.

## What Changes
- Adjust CSS padding/margins to align the left edges of the mode bar and input box
- Centralize horizontal spacing at the container level for consistency

**Root Cause Analysis:**
- Mode bar: `padding: 0 1` (1 unit left padding)
- Input box: `margin: 0 1` + `padding: 0 1` (2 units total left offset)
- Creates 1-unit horizontal misalignment

## Impact
- Affected files:
  - `massgen/frontend/displays/textual_themes/dark.tcss`
  - `massgen/frontend/displays/textual_widgets/mode_bar.py` (inline CSS)
