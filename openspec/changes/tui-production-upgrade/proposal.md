# TUI Production Upgrade Proposal

## Summary
Migrate MassGen from Rich terminal to Textual TUI as the primary terminal interface, achieving full feature parity with Rich terminal and incorporating production-quality UX patterns from the WebUI.

## Motivation

### Current State
MassGen currently has three display modes:
1. **Rich Terminal** - Full-featured but aging, uses Rich library for formatting
2. **Textual TUI** - Newer, uses Textual for true terminal UI, but incomplete
3. **WebUI** - Most polished UX, but requires browser

The Textual TUI was introduced to provide a modern terminal experience but currently has:
- Feature gaps vs Rich terminal (missing /context, metrics, cost display, etc.)
- UX issues (vertical agent boxes cause information overload with multiple agents)
- No smart content filtering (shows ALL streaming content)
- Basic tool call display (just text prefixes, no structure)

### Goals
1. **Feature parity** with Rich terminal - all commands, displays, and capabilities
2. **Production-quality UX** - inspired by Claude Code, Codex, OpenCode
3. **Smart content display** - show selective info, expand on demand
4. **Unified terminal experience** - deprecate Rich terminal in favor of TUI

### Non-Goals
- Replacing WebUI (TUI is for terminal users)
- Supporting legacy terminals without Unicode/color support
- Mobile terminal support

## Proposed Solution

### Layout Architecture
Replace vertical agent boxes with **horizontal tabs** (one agent at a time):
- Clean, focused view like Claude Code/Codex
- Tab bar shows all agents with status badges
- Switch with Tab/Shift+Tab or number keys (1-9)
- All agent streams maintained in background

### Tool Call Display
Replace text prefixes with **collapsible cards**:
- Collapsed: `🔧 tool_name ── status`
- Expanded: params, result preview, timing
- Toggle with Enter/click
- Styled by tool type (MCP, custom, filesystem, code execution)

### Events & Notifications
Hybrid **status bar + toast notifications**:
- Persistent status bar: phase, vote counts, event counter
- Toast notifications for important events (votes, completions, errors)
- Auto-dismiss after 5 seconds, type-colored

## Implementation Phases

1. **Phase 1: Core Layout Refactor** - Horizontal tabs, single agent view
2. **Phase 2: Tool Call Cards** - Structured, collapsible tool visualization
3. **Phase 3: Status Bar & Toasts** - Event display system
4. **Phase 4: Feature Parity** - Port all Rich terminal features
5. **Phase 5: WebUI Enhancements** - Vote visualization, file browser, animations
6. **Phase 6: Migration** - Make TUI default, deprecate Rich

## Impact

### Files Modified
- `massgen/frontend/displays/textual_terminal_display.py` (major refactor)
- `massgen/frontend/interactive_controller.py`
- `massgen/frontend/displays/textual_themes/*.tcss`
- `massgen/cli.py`

### New Files
- `massgen/frontend/displays/textual_widgets/tab_bar.py`
- `massgen/frontend/displays/textual_widgets/tool_card.py`
- `massgen/frontend/displays/textual_widgets/toast.py`
- `massgen/frontend/displays/textual_widgets/status_bar.py`

### Breaking Changes
- Phase 6 will change default `--display` from `rich` to `textual`
- Rich terminal will show deprecation warning

## Success Criteria
1. All Rich terminal features work in TUI
2. All slash commands behave identically
3. Tool calls display with structured cards
4. Vote/coordination events show as toasts
5. Works in iTerm, VS Code terminal, Windows Terminal
6. Users prefer TUI over Rich in feedback

## Timeline
This is a multi-phase project. Each phase should be implemented as a separate PR with testing between phases.

## Related
- Linear Issue: [To be created]
- Design Document: `design.md`
- Task Breakdown: `tasks.md`
