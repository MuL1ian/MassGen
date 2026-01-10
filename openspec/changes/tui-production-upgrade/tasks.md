# TUI Production Upgrade - Task Breakdown

## Phase 1: Core Layout Refactor ✅ COMPLETE
**Goal**: Replace vertical boxes with horizontal tabs
**Estimated Effort**: Large
**Dependencies**: None
**Status**: Completed 2025-01-09

### Tasks

- [x] **1.1** Create `textual_widgets/` directory structure
  - Created `massgen/frontend/displays/textual_widgets/__init__.py`
  - Created `massgen/frontend/displays/textual_widgets/tab_bar.py`

- [x] **1.2** Implement `AgentTabBar` widget
  - Horizontal layout with agent tabs
  - Status badge display (⏳/⚙️/📝/✅/❌)
  - Active tab highlighting with status-based colors
  - Click handler for tab switching
  - `AgentTabChanged` message for event handling

- [x] **1.3** Reuse existing `AgentPanel` widget
  - Decision: Reuse existing AgentPanel (show/hide via CSS) instead of new widget
  - Each agent maintains own RichLog, scroll position, buffered content
  - Full width when visible, `display: none` when hidden

- [x] **1.4** Implement tab navigation
  - Tab/Shift+Tab cycling via `action_next_agent`/`action_prev_agent`
  - Number keys 1-9 for direct access
  - All agent streams continue in background
  - Scroll position automatically preserved (each panel maintains own state)

- [x] **1.5** Update `TextualApp` composition
  - Added `AgentTabBar` between header and main container
  - All `AgentPanel` instances created, only active one visible
  - `_switch_to_agent()` method for tab switching
  - `_active_agent_id` tracks currently visible agent

- [x] **1.6** Update TCSS themes
  - Added `AgentTabBar` and `AgentTab` styles (dark.tcss, light.tcss)
  - Added status-based tab border colors
  - Added active tab background colors
  - Updated `AgentPanel` for full-width display

- [x] **1.7** Additional features implemented
  - **Welcome screen**: ASCII logo with agent/model info on startup
  - **Compact header**: Single-line header (was multi-line with ASCII art)
  - **Easy quit**: q, Ctrl+Q, Escape bindings
  - **Agent models on welcome**: Shows "agent_id (model_name)" format

- [ ] **1.8** Write tests for tab navigation (TODO)
  - Created `scripts/test_tab_bar.py` for manual testing
  - Unit tests for `AgentTabBar` still needed
  - Integration tests for tab switching still needed

### Acceptance Criteria
- [x] Single agent visible at a time (full width)
- [x] Tab bar shows all agents with status
- [x] Tab/number key navigation works
- [x] Content streams continue in background
- [x] Scroll position preserved per agent
- [x] Welcome screen shows agent configuration
- [x] Easy way to quit the TUI

### Files Created/Modified
- `massgen/frontend/displays/textual_widgets/__init__.py` (new)
- `massgen/frontend/displays/textual_widgets/tab_bar.py` (new)
- `massgen/frontend/displays/textual_terminal_display.py` (modified)
- `massgen/frontend/displays/textual_themes/dark.tcss` (modified)
- `massgen/frontend/displays/textual_themes/light.tcss` (modified)
- `massgen/frontend/coordination_ui.py` (modified)
- `massgen/cli.py` (modified)
- `scripts/test_tab_bar.py` (new)

---

## Phase 2: Tool Call Cards ⚠️ PARTIAL (Styled Bars Approach)
**Goal**: Structured, collapsible tool call visualization
**Estimated Effort**: Medium
**Dependencies**: Phase 1
**Status**: Completed with styled bars approach; collapsible widgets deferred

### What Was Implemented

- [x] **2.3** Implement tool call detection
  - Parse tool calls from content stream via `_parse_tool_message()`
  - Detect tool start/result/error patterns
  - Track active tool calls per agent with `_pending_tool`

- [x] **2.5** Add tool type styling (via styled bars)
  - Category icons: Filesystem (📁), Web (🌐), Code (💻), Database (🗄️), Git (📦), API (🔌), AI (🤖), Memory (🧠)
  - Status colors: Green (success), Red (error), Alternating gray (in-progress)
  - Full-width bars with timing display

- [x] **2.6** Update TCSS themes
  - Tool card CSS added (for future use)
  - ToolCallCard styles in dark.tcss and light.tcss

- [x] **Additional features**
  - Reasoning display: "🤔 Reasoning" header with dimmed content below
  - Injection display: Purple bars for cross-agent context
  - Reminder display: Orange bars for high-priority tasks
  - Restart detection: Red banner on session restart
  - JSON filtering: Raw vote/action blocks hidden

### What Was Attempted But Deferred

- [ ] **2.1** Define `ToolCallEvent` data model - Not needed for styled bars
- [ ] **2.2** Implement `ToolCallCard` widget - Created but reverted
  - Widget exists at `textual_widgets/tool_card.py` but not used
  - **Issue**: Mounting widgets with `.mount()` doesn't integrate with RichLog scroll
  - Cards ended up stuck at bottom, click events didn't work
  - Would require replacing RichLog entirely (major refactor)
- [ ] **2.4** Integrate with content panel - Using styled bars in RichLog instead
- [ ] **2.7** Write tests for tool cards - Deferred

### Acceptance Criteria (Revised for Styled Bars)
- [x] Tool calls display as styled full-width bars
- [x] Bars show tool name, category icon, and status
- [x] Status (running/success/error) visually indicated with colors
- [x] Timing shown on completion
- [x] Different tool types have distinct category icons
- [ ] ~~Toggle works via click and Enter key~~ (Deferred - requires RichLog replacement)

### Files Modified
- `massgen/frontend/displays/textual_terminal_display.py` - `_format_tool_line()`, `_handle_tool_content()`, `_make_full_width_bar()`
- `massgen/frontend/displays/textual_widgets/tool_card.py` - Created (unused)
- `massgen/frontend/displays/textual_themes/dark.tcss` - Tool card CSS
- `massgen/frontend/displays/textual_themes/light.tcss` - Tool card CSS

### Future Work (If Collapsible Cards Still Desired)
1. Replace RichLog with custom ScrollableContainer holding individual widgets
2. Or implement virtual collapsibility (re-render RichLog on keyboard shortcut)
3. Or add separate tool panel sidebar

---

## Phase 3: Status Bar & Toasts ⚠️ PARTIAL
**Goal**: Persistent status + ephemeral notifications
**Estimated Effort**: Medium
**Dependencies**: Phase 1
**Status**: Core features implemented; using built-in notify() for toasts

### What Was Implemented

- [x] **3.1** Implement `StatusBar` widget
  - Dock at bottom
  - Vote count display per agent (compact format: "A:2 B:1")
  - Current phase indicator (idle/coordinating/voting/presenting)
  - Event counter (clickable → opens OrchestratorEventsModal)
  - Elapsed timer (starts when welcome screen dismisses)

- [x] **3.2-3.3** Toast Notifications (via built-in `notify()`)
  - Decision: Use Textual's built-in `notify()` method instead of custom widgets
  - Auto-dismiss with configurable timeout (3-5 seconds)
  - Type-based severity (information, warning, error)
  - Vote notifications: "🗳️ Agent → VotedFor"
  - Completion notifications: "✅ Agent completed"
  - Error notifications with 5-second timeout

- [x] **3.4** Integrate with orchestrator events
  - Vote events → toast + status bar update
  - Phase changes → status bar update
  - Events counter increments with orchestrator events

- [x] **3.5** Update TCSS themes
  - StatusBar styles for dark.tcss and light.tcss
  - Phase-specific border colors
  - Clickable events counter with hover effect

### What Was Deferred

- [ ] **3.6** Write tests
  - Status bar update tests
  - Toast lifecycle tests
  - Event integration tests

- [ ] **3.7** Improve mouse handling (moved to future phase)
  - Add mouse mode toggle (Ctrl+M to disable mouse capture)
  - Visual feedback for clickable elements
  - Graceful fallback when mouse events conflict with terminal

### Acceptance Criteria (Revised)
- [x] Status bar always visible at bottom
- [x] Vote counts update in real-time
- [x] Phase indicator shows current phase
- [x] Toasts appear for important events (via notify())
- [x] Toasts auto-dismiss after timeout
- [ ] ~~Toasts stack properly (max 3)~~ - Using built-in notify() stacking
- [ ] Mouse mode toggle - Deferred
- [ ] Clickable element indicators - Partial (events counter only)

### Files Modified
- `massgen/frontend/displays/textual_terminal_display.py` - StatusBar widget, notification methods
- `massgen/frontend/coordination_ui.py` - Vote parsing, phase tracking
- `massgen/frontend/displays/textual_themes/dark.tcss` - StatusBar styles
- `massgen/frontend/displays/textual_themes/light.tcss` - StatusBar styles

---

## Phase 4: Feature Parity with Rich
**Goal**: Port all Rich terminal features
**Estimated Effort**: Large
**Dependencies**: Phase 1-3

### Tasks

- [ ] **4.1** Port `/context` command
  - Interactive path addition UI
  - Path validation
  - Config update

- [ ] **4.2** Port `/config` command
  - Open config in external editor
  - Detect editor (VS Code, vim, nano)
  - Handle editor exit

- [ ] **4.3** Implement `/metrics` command
  - Tool metrics summary table
  - Call counts, timing, success rates
  - Modal or inline display

- [ ] **4.4** Implement cost breakdown
  - Per-agent token usage
  - Cost calculation
  - Display in modal or status

- [ ] **4.5** Port full agent selector
  - View agent output files
  - Open in external editor
  - View workspace files
  - Navigate between agents

- [ ] **4.6** Port file inspection
  - Tree view of workspace
  - File preview
  - Open files externally

- [ ] **4.7** Implement broadcast prompt handling
  - Human input requests from agents
  - Timeout handling
  - Skip in automation mode

- [ ] **4.8** Verify all slash commands
  - /help, /quit, /reset, /status
  - /inspect, /events, /vote
  - /cancel, /config, /context

- [ ] **4.9** Write comparison tests
  - Rich vs TUI output comparison
  - Command behavior parity

### Acceptance Criteria
- [ ] All Rich commands work in TUI
- [ ] Command outputs are equivalent
- [ ] File inspection works
- [ ] Cost/metrics display works
- [ ] Broadcast prompts work

---

## Phase 5: WebUI-Inspired Enhancements
**Goal**: Polish and production readiness
**Estimated Effort**: Medium
**Dependencies**: Phase 4

### Tasks

- [ ] **5.1** Real-time vote visualization
  - Animated vote count updates
  - Winner highlight animation
  - Vote history in status bar

- [ ] **5.2** File browser modal
  - Tree view with folders
  - File type icons
  - Preview panel
  - Navigate and select

- [ ] **5.3** Animated progress indicators
  - Initialization progress bar
  - Agent setup spinner
  - Turn completion animation

- [ ] **5.4** MCP server status
  - Show connected servers
  - Tool availability indicator
  - Error states

- [ ] **5.5** Workspace quick-view
  - See files created by agent
  - Quick preview without leaving panel
  - Open full view

- [ ] **5.6** Polish and refinement
  - Consistent animations
  - Smooth transitions
  - Error state styling
  - Loading states

### Acceptance Criteria
- [ ] Vote visualization feels responsive
- [ ] File browser is navigable
- [ ] Progress indicators give feedback
- [ ] Overall UX feels polished

---

## Phase 6: Migration & Default Switch
**Goal**: Make TUI the default, deprecate Rich
**Estimated Effort**: Small
**Dependencies**: Phase 5

### Tasks

- [ ] **6.1** Update CLI defaults
  - Change `--display` default to "textual"
  - Keep "rich" as option

- [ ] **6.2** Add deprecation warning
  - Show warning when using `--display rich`
  - Include migration guidance
  - Link to documentation

- [ ] **6.3** Update documentation
  - Update README examples
  - Update user guide
  - Update quickstart

- [ ] **6.4** Update example configs
  - Remove rich-specific configs
  - Ensure TUI works with all examples

- [ ] **6.5** Create migration guide
  - Document differences
  - New keyboard shortcuts
  - New features

- [ ] **6.6** Final testing
  - End-to-end testing
  - Cross-terminal testing
  - Performance testing

### Acceptance Criteria
- [ ] `uv run massgen` uses TUI by default
- [ ] Rich shows deprecation warning
- [ ] Documentation is updated
- [ ] Migration guide exists

---

## Testing Requirements

### Unit Tests (per widget)
- [ ] `test_agent_tab_bar.py`
- [ ] `test_tool_call_card.py`
- [ ] `test_toast_notification.py`
- [ ] `test_status_bar.py`
- [ ] `test_agent_content_panel.py`

### Integration Tests
- [ ] `test_tui_session_flow.py`
- [ ] `test_tui_multi_agent.py`
- [ ] `test_tui_tool_calls.py`
- [ ] `test_tui_events.py`

### Manual Testing Checklist
- [ ] iTerm2 on macOS
- [ ] VS Code integrated terminal
- [ ] Windows Terminal
- [ ] SSH remote session
- [ ] 1-agent config
- [ ] 2-agent config
- [ ] 3-agent config
- [ ] 5+ agent config
- [ ] Dark theme
- [ ] Light theme
- [ ] Terminal resize handling
- [ ] Mouse support
- [ ] Keyboard-only navigation

---

## Risk Mitigation

### Risk: Textual library limitations
**Mitigation**: Research Textual capabilities upfront, have fallback designs

### Risk: Performance with many agents
**Mitigation**: Virtual scrolling, content truncation, lazy rendering

### Risk: Terminal compatibility issues
**Mitigation**: Test early and often on target terminals, have emoji fallbacks

### Risk: Breaking existing workflows
**Mitigation**: Keep Rich available during migration, document changes

---

## Success Metrics

1. **Feature completeness**: 100% of Rich features in TUI
2. **User preference**: >80% prefer TUI in feedback
3. **Performance**: <100ms response to user input
4. **Stability**: Zero crashes in normal operation
5. **Compatibility**: Works in all target terminals
