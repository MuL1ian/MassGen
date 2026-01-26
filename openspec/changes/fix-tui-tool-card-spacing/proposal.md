# Change: Fix TUI Tool Card Spacing

## Why
Excessive empty space between consecutive tool cards wastes vertical real estate and disrupts visual flow. When multiple tool calls execute in rapid succession, the gaps between cards make them appear disconnected rather than part of a cohesive sequence.

## What Changes
- Reduce `ToolCallCard` vertical margin from `1 0 1 1` to `0 0 0 1`
- Remove top/bottom margins that create 2-row gaps between consecutive cards
- Maintain left border styling for visual separation

**Root Cause Analysis:**
- `ToolCallCard` CSS: `margin: 1 0 1 1` creates 1 row top and 1 row bottom margins
- Between consecutive cards, this creates consistent 2-row gaps
- This is excessive for a rapid tool call sequence

## Impact
- Affected files:
  - `massgen/frontend/displays/textual_themes/dark.tcss` (lines 2305-2315)
  - `massgen/frontend/displays/textual_themes/light.tcss` (corresponding lines)
