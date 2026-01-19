# Change: Textual TUI Polish and UX Improvements

## Why
The Textual TUI has multiple visual and functional issues that degrade user experience: tool cards have misaligned elements, workspace browser lacks "current" option, timeline is hard to understand, modals are too narrow, and various UI elements are incomplete or incorrect.

## What Changes

### Tool Card Display
- Move time display from middle to right side of card header
- Remove redundant check emoji and "[MCP Tool]" label from tool cards
- Remove verbose "Results for Calling mcp__..." prefixes from tool results

### Workspace Browser
- Add "Current Workspace" as first option in dropdown (currently missing despite code changes)
- Order answers with most recent first (currently oldest first)

### Timeline/Browser Modal
- Make modal wider (currently too vertically constrained)
- Improve timeline readability with clearer event formatting
- Order events with most recent first

### Answer Browser Modal
- Order answers with most recent first (currently oldest first)
- Make modal wider for better readability

### Tool Detail Modal (Hook Display)
- Fix hook result display formatting (currently shows raw injection markers)
- Make modal wider

### Bottom Status Bar
- Add visible Cancel button during execution (currently missing)
- Fix content not extending to right edge of screen

### Help Modal
- Remove 'f' from help since it's no longer bound
- Update descriptions for changed keybindings

### General
- Fix scrollable content not extending to right edge (width: 100% issue)
- Ensure all modals have proper Close button styling

## Impact
- Affected files:
  - `massgen/frontend/displays/textual_terminal_display.py`
  - `massgen/frontend/displays/textual_widgets/tool_card.py`
  - `massgen/frontend/displays/textual_themes/dark.tcss`
  - `massgen/frontend/displays/textual_themes/light.tcss`
  - `massgen/frontend/displays/content_normalizer.py`
  - `massgen/frontend/displays/content_handlers.py`
