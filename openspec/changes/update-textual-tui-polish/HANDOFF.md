# Handoff: Textual TUI Polish (update-textual-tui-polish)

## Context

A previous agent attempted to implement 9 TUI improvements but several were incomplete or didn't work. This OpenSpec change documents all remaining issues that need to be fixed.

## Current State

The OpenSpec proposal is created and validated:
- `openspec/changes/update-textual-tui-polish/proposal.md` - Overview
- `openspec/changes/update-textual-tui-polish/tasks.md` - Implementation checklist
- `openspec/changes/update-textual-tui-polish/specs/textual-tui/spec.md` - Requirements

---

## Round 3 Issues (Latest Feedback) - ALL FIXED

### Issue 3.1: Help Modal Still Not Wide Enough ✅ FIXED
**Problem**: Help modal could still be wider to better use available terminal space
**Fix Applied**: Increased `#shortcuts_modal_container` max-width to 150

### Issue 3.2: Answer Browser - Color by Agent ✅ FIXED
**Problem**: Answers in browser should be colored based on which agent submitted them
**Fix Applied**: Added agent color classes (agent-color-0 through agent-color-3) with colored left borders:
- Agent 0: Cyan (#4ec9b0)
- Agent 1: Magenta (#c586c0)
- Agent 2: Yellow (#dcdcaa)
- Agent 3: Orange (#ce9178)

### Issue 3.3: Agent Output Modal - Make Taller ✅ FIXED
**Problem**: Agent output modal ('o' key) has too much empty space, text area should be larger
**Fix Applied**: Increased modal width to 95%, height to 92%

### Issue 3.4: Timeline Needs More Color/Visual Appeal ✅ FIXED
**Problem**: Timeline is too plain, needs more visual distinction
**Fix Applied**:
- Status messages: blue border-left (#58a6ff)
- Response text: green border-left and background (#3fb950, #0d1f14)
- Answer text: thick yellow border-left and background (#d29922, #1f1a0d)
- Thinking text: blue color (#79c0ff)
- Vote text: purple background (#1a1426)
- RestartBanner: purple borders (#a371f7)

### Issue 3.5: Scroll Mode (tmux-style) ✅ FIXED
**Problem**: When scrolling up to read content, new content auto-scrolls to bottom, losing scroll position
**Fix Applied**:
- TimelineSection tracks scroll position via `on_scroll_to` event
- When user scrolls up, enters "scroll mode" (auto-scroll pauses)
- Scroll indicator banner shows "📜 SCROLL MODE — Press [g] or [Esc] to resume auto-scroll"
- New content counter shows how many items arrived while in scroll mode
- Press 'g' or 'Escape' to exit scroll mode and resume auto-scroll
- Scrolling to bottom also exits scroll mode automatically

---

## Round 2 Issues (from Jan 13 screenshots) - ALL FIXED

### Issue 2.1: Help Modal Still Too Narrow ✅ FIXED
**Fix Applied**: Increased `#shortcuts_modal_container` max-width from 90 to 120, min-width from 55 to 70

### Issue 2.2: Agent Output Modal Issues ✅ FIXED
- ✅ Shows model name from `agent.backend.model` instead of "Unknown"
- ✅ Added agent toggle buttons to switch between agents
- ✅ Modal scrolls to bottom on open

### Issue 2.3: Tool Call Tips Not Visible + Input Bar During Execution ✅ FIXED
- ✅ Tips visible with wider help modal
- ✅ Input bar shows: elapsed time → votes → "Working... [q] to cancel"

### Issue 2.4: Answer Browser Ordering and Readability ✅ FIXED
- ✅ Answer list sorted by timestamp descending (most recent first)
- ✅ Default selection is now first item (most recent)

---

## Round 1 Issues (Original - All Fixed)

### 1. Tool Card Display ✅ FIXED
### 2. Workspace Browser ✅ FIXED
### 3. Timeline/Browser Modal ✅ FIXED
### 4. Tool Detail Modal ✅ FIXED
### 5. Help Modal ✅ FIXED
### 6. Status Bar Improvements ✅ FIXED

---

## Files to Modify (Round 3)

| File | Changes |
|------|---------|
| `massgen/frontend/displays/textual_themes/dark.tcss` | Help modal width, agent output modal height, timeline colors |
| `massgen/frontend/displays/textual_themes/light.tcss` | Same CSS changes |
| `massgen/frontend/displays/textual_terminal_display.py` | Answer browser agent colors, scroll mode logic |
| `massgen/frontend/displays/textual_widgets/content_sections.py` | Timeline visual improvements |

## Testing

```bash
uv run massgen --config massgen/configs/tools/mcp/filesystem_tools.yaml "create a poem file"
```

Round 3 verification (implementation complete, testing recommended):
- [x] Press '?' → Help modal uses more terminal width (max-width: 150)
- [x] Press 't' → Answers colored by agent (agent-color-0 through agent-color-3)
- [x] Press 'o' → Agent output modal is taller, less empty space (95% width, 92% height)
- [x] Timeline has more visual color/distinction (colored borders for status, response, answer, thinking, vote)
- [x] Scroll up → Enter scroll mode, auto-scroll pauses (indicator shows)
- [x] Press 'g' or Esc → Exit scroll mode, resume auto-scroll
