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

## Phase 2: Content Display Redesign ✅ COMPLETE
**Goal**: Clean, organized content display with section widgets
**Estimated Effort**: Medium
**Dependencies**: Phase 1
**Status**: Completed 2026-01-10

### Design Decision Change

**Original approach**: Filter content aggressively, use styled bars in RichLog
**Revised approach**: Categorize content (not filter), use section widgets, hide RichLog

**Key insight**: Internal reasoning (voting, coordination) is valuable - it just needs organization, not filtering. Only filter true noise (empty JSON fragments, internal tool JSON that will become tool cards).

### What Was Implemented

- [x] **2.1** Create `content_normalizer.py`
  - `ContentNormalizer.normalize()` - Single entry point for all content preprocessing
  - `NormalizedContent` dataclass with `is_coordination` flag
  - Minimal JSON noise filtering (empty braces, fragments)
  - Workspace tool JSON filtering (`action_type`, `answer_data`, etc.)
  - Coordination content detection (voting patterns) for categorization

- [x] **2.2** Create `content_handlers.py`
  - `ToolContentHandler` - Parse tool events, track pending tools
  - `ThinkingContentHandler` - Clean streaming content
  - `ToolDisplayData` dataclass for tool card integration

- [x] **2.3** Create `content_sections.py` section widgets
  - `TimelineSection` - Chronological container replacing RichLog
  - `ReasoningSection` - Collapsible section for coordination content
  - `RestartBanner` - Prominent red banner for session restarts
  - `ToolCallCard` - Individual tool call with status styling
  - `ResponseSection` - Clean response display
  - `StatusBadge` - Compact inline indicator
  - `CompletionFooter` - Subtle completion indicator

- [x] **2.4** Integrate with AgentPanel
  - `compose()` yields TimelineSection
  - `add_content()` routes content to appropriate sections
  - `show_restart_separator()` uses TimelineSection.add_separator()
  - Coordination content routed to ReasoningSection

- [x] **2.5** Update CSS themes
  - ToolCallCard: Full borders, status-colored backgrounds
  - TimelineSection: `height: 1fr` to fill available space
  - ReasoningSection: Collapsible with dashed border
  - RestartBanner: Red background, centered text
  - Legacy RichLog hidden: `AgentPanel RichLog { display: none; }`

- [x] **2.6** Export widgets
  - All section widgets exported from `textual_widgets/__init__.py`

### Acceptance Criteria
- [x] Content appears in TimelineSection (not hidden RichLog)
- [x] Restart banners show prominently with red styling
- [x] Coordination content categorized to ReasoningSection
- [x] Workspace tool JSON filtered (will be tool cards)
- [x] Empty JSON noise filtered
- [x] TimelineSection fills available vertical space
- [x] Tool cards have status-based styling

### Files Created/Modified
- `content_normalizer.py` (new) - ContentNormalizer, NormalizedContent
- `content_handlers.py` (new) - ToolContentHandler, ThinkingContentHandler
- `textual_widgets/content_sections.py` (new) - All section widgets
- `textual_widgets/__init__.py` (modified) - Export new widgets
- `textual_terminal_display.py` (modified) - AgentPanel uses TimelineSection
- `textual_themes/dark.tcss` (modified) - Section widget CSS
- `textual_themes/light.tcss` (modified) - Section widget CSS

### Key Learnings

1. **Hide legacy widgets via CSS**: `AgentPanel RichLog { display: none; }` is cleaner than removing
2. **Route to new widgets, not old ones**: Restart banners weren't showing because `show_restart_separator()` wrote to hidden RichLog
3. **Filter vs Categorize**: Don't filter valuable content - categorize and display in collapsible sections
4. **Use `height: 1fr`**: Not `height: auto; max-height: 70%` for containers that should fill space

### Remaining Work (Phase 2.5)
- [ ] Parse workspace tool calls into nice tool cards (currently just filtered)
- [ ] Better tool card expansion/collapse UX
- [ ] Reasoning section expand/collapse click handling

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

## Phase 4: Feature Parity with Rich ✅ COMPLETE
**Goal**: Port all Rich terminal features
**Estimated Effort**: Large
**Dependencies**: Phase 1-3
**Status**: Completed 2026-01-10

### What Was Implemented

- [x] **4.1** Port `/context` command
  - Created `ContextModal` with interactive path addition UI
  - Shows current context paths
  - Add/remove path operations
  - Path validation (checks if path exists)

- [x] **4.2** Port `/config` command
  - Already worked via SlashCommandDispatcher
  - Opens config in external editor (VS Code, vim, nano, or system default)
  - Proper editor detection and subprocess handling

- [x] **4.3** Implement `/metrics` command
  - Created `MetricsModal` with tool metrics summary table
  - Shows call counts, success/failure rates, avg/min/max duration
  - Sortable by different columns

- [x] **4.4** Implement cost breakdown
  - Created `CostBreakdownModal` with per-agent token usage table
  - Shows input/output/reasoning/cached tokens
  - Calculates costs from token_manager pricing
  - Shows peak context usage percentage

- [x] **4.5** Port full agent selector
  - Enhanced `AgentSelectorModal` with new options:
    - Agent inspection (1-9 keys)
    - Cost breakdown (c key)
    - Workspace files (w key)
    - Metrics (m key)
    - Open workspace (o key)
  - Navigate between agents with proper file viewing

- [x] **4.6** Port file inspection
  - Created `FileInspectionModal` with DirectoryTree widget
  - Tree view of workspace files (left panel)
  - File preview with syntax highlighting (right panel)
  - Open in editor functionality
  - File size limits for safe preview

- [x] **4.7** Implement broadcast prompt handling
  - Created `BroadcastPromptModal` for human input during coordination
  - Displays agent's question with formatting
  - Input field for user response
  - Timeout indicator (countdown)
  - Skip button for automation mode
  - Async integration with orchestrator via `prompt_for_broadcast_response()`

- [x] **4.8** Verify all slash commands
  - /help - Shows command list
  - /quit, /q - Exit TUI
  - /reset - Reset session
  - /status, /s - Show status
  - /inspect, /i - Agent inspection modal
  - /events [N] - Last N orchestrator events
  - /vote - Vote results modal
  - /cancel - Cancel current operation
  - /config - Open config in editor
  - /context - Context path modal
  - /cost, /c - Cost breakdown modal (NEW)
  - /workspace, /w - Workspace files modal (NEW)
  - /metrics, /m - Tool metrics modal (NEW)

- [ ] **4.9** Write comparison tests (deferred to testing phase)
  - Rich vs TUI output comparison
  - Command behavior parity

### New Slash Commands Added
| Command | Shortcut | Description |
|---------|----------|-------------|
| `/cost` | `/c` | Token usage and cost breakdown |
| `/workspace` | `/w` | List workspace files |
| `/metrics` | `/m` | Tool execution metrics |

### Files Created/Modified
- `massgen/frontend/displays/textual_terminal_display.py` - 6 new modals, helper methods
- `massgen/frontend/interactive_controller.py` - New command handlers
- `massgen/frontend/displays/textual_themes/dark.tcss` - Modal CSS styles
- `massgen/frontend/displays/textual_themes/light.tcss` - Modal CSS styles

### Acceptance Criteria
- [x] All Rich commands work in TUI
- [x] Command outputs are equivalent
- [x] File inspection works
- [x] Cost/metrics display works
- [x] Broadcast prompts work

---

## Phase 5: WebUI-Inspired Enhancements ⚠️ PARTIAL
**Goal**: Polish and production readiness
**Estimated Effort**: Medium
**Dependencies**: Phase 4
**Status**: In Progress

### What Was Implemented

- [x] **5.0.1** Vim Mode for Input (NEW)
  - `/vim` slash command toggles vim mode
  - Starts in INSERT mode (green indicator) for immediate typing
  - Press Escape to enter NORMAL mode (yellow indicator)
  - Visual indicator above input shows current mode (INSERT/NORMAL)
  - Hint text updates: "VIM: i/a insert • hjkl move • /vim off"
  - Full vim keybindings in normal mode:
    - Movement: h/j/k/l, w/b (word), 0/$ (line), gg/G (document)
    - Insert: i, a, A, o, O, s, S
    - Delete: x, X, dd, dw, d$, d0, D
    - Change: cc, cw, c$, c0, C
    - Character motions: f/t/F/T + char (e.g., `dt,` deletes to comma)
    - Combined: df/dt/cf/ct + char (e.g., `cf"` changes to quote)
    - Undo: u
  - Vim keys only active when vim mode enabled (no accidental triggers)
  - Input box border turns yellow in NORMAL mode

- [x] **5.0** Keyboard shortcuts help system (NEW)
  - `?` or `h` key opens shortcuts modal during coordination
  - Rich-formatted display with color-coded sections
  - Welcome screen shows "Press ? for shortcuts" hint
  - All keyboard shortcuts documented in popup

- [x] **5.1** Agent output modal (NEW)
  - `f` key opens full output for current agent
  - Copy to clipboard functionality
  - Save to file functionality
  - Scrollable text view with line count

- [x] **5.2** Live keyboard shortcuts during coordination
  - `f` - Full agent output
  - `c` - Cost breakdown modal
  - `m` - Metrics modal
  - `p` - MCP server status
  - `v` - Vote results
  - `o` - Orchestrator events
  - `s` - System status
  - `?`/`h` - Help/shortcuts
  - `Tab`/`Shift+Tab` - Switch agents

### Keyboard Shortcuts Reference

| Key | Action | Description |
|-----|--------|-------------|
| `?` or `h` | Show Help | Keyboard shortcuts popup |
| `f` | Full Output | Current agent's full output |
| `c` | Cost | Token usage breakdown |
| `m` | Metrics | Tool execution stats |
| `p` | MCP Status | MCP server connections & tools |
| `v` | Votes | Vote results |
| `o` | Events | Orchestrator events |
| `s` | Status | System status |
| `Tab` | Next Agent | Switch to next agent |
| `Shift+Tab` | Prev Agent | Switch to previous agent |
| `1-9` | Agent N | Jump to specific agent |
| `q`/`Esc` | Quit | Exit TUI |

- [x] **5.3** Real-time vote visualization
  - Crown emoji (👑) highlights vote leader in StatusBar
  - CSS animation on vote updates (flash/pulse effect)
  - Vote history tracking with timestamps
  - Standings shown in toast notifications
  - `consensus-reached` CSS animation for winner

- [x] **5.4** MCP server status
  - `MCPStatusModal` shows connected servers and tools
  - `p` key binding opens MCP status
  - `/mcp` or `/p` slash command
  - StatusBar MCP indicator (`🔌 Ns/Nt` format)
  - Per-server tool count and preview

### Completed WebUI Parity Features

- [x] **5.5** Enhanced Toast Notifications ✅ COMPLETE
  - New answer toast with agent ID and model name
  - Vote cast toast with voter → target info and current standings
  - Auto-dismiss after configurable timeout (5s for answers, 3s for votes)
  - Color-coded by type (answer=green, vote=amber, error=red)
  - Tracks all answers and votes for browser/timeline modals

- [x] **5.6** Answer Browser Modal ✅ COMPLETE
  - `b` key or `/answers` command opens browser
  - Lists all answers with timestamps, model names
  - Filter by agent via dropdown selector
  - Visual indicators: Winner (gold + 🏆), Final (green ✓)
  - Vote count per agent displayed
  - Content preview (80 char truncated)

- [x] **5.7** Timeline Visualization ✅ COMPLETE
  - `t` key or `/timeline` command opens timeline
  - Chronological event list (not swimlane - simpler/clearer)
  - Event types: ○ answer, ◇ vote, ★ winner
  - Shows agent, answer label, voter → target
  - Timestamps for all events
  - Summary: total answers, total votes

- [x] **5.8** Workspace Browser ✅ COMPLETE
  - `w` key or `/files` command opens workspace browser
  - Per-answer workspace selection via dropdown
  - Split pane: file list (left) + preview (right)
  - Filters hidden files (.files starting with .)
  - File size display
  - Text file preview with syntax-aware extensions
  - Binary file detection

### Completed WebUI Parity Features (Continued)

- [x] **5.9** Vote Browser with Distribution ✅ COMPLETE
  - Vote distribution summary (ASCII bar chart) with `████░░░░` visualization
  - Winner highlighted with trophy emoji
  - Individual votes list with voter → target
  - Integrated into existing VoteResultsModal (`v` key)

- [x] **5.10** Progress Summary in StatusBar ✅ COMPLETE
  - Compact status line: "3 agents | 2 answers | 4/6 votes"
  - Updates on new answers and votes
  - Winner announcement displayed when consensus reached

- [x] **5.11** Winner Celebration Effects ✅ COMPLETE (partial)
  - Winner tab highlighted with gold styling
  - StatusBar shows winner announcement
  - Enhanced toast notification with winner details
  - `_celebrate_winner()` method triggers visual effects

- [x] **5.13** Multi-Tab Browser Modal ✅ COMPLETE
  - `BrowserTabsModal` with 4 tabs: Answers | Votes | Workspace | Timeline
  - Number keys (1-4) switch between tabs
  - `u` key binding and `/browser` slash command
  - Summarized views of all data

### Completed Tasks - WebUI Parity Features (2026-01-11)

#### Medium Priority (Enhanced Features)

- [x] **5.12** Final Answer View ✅ COMPLETE
  - Prominent display of winning answer with model name in header
  - Copy to clipboard button (platform-aware: pbcopy/clip/xclip)
  - Save to file button (saves to `final_answers/` directory)
  - Workspace browser button for winner
  - Follow-up question input field (appears after completion)
  - Content buffering for copy/save operations

#### Lower Priority (Nice-to-Haves)

- [x] **5.14** File Preview Enhancements ✅ COMPLETE
  - `render_file_preview()` helper function
  - Syntax highlighting for 32 file extensions (Python, JS, JSON, YAML, etc.)
  - Markdown rendering with Rich Markdown
  - Binary file detection (35 extension types)
  - File size limits and error handling
  - Updated WorkspaceBrowserModal to use new helper

- [x] **5.15** Animated Progress Indicators ✅ COMPLETE
  - `ProgressIndicator` widget with animated spinner
  - Unicode/ASCII/dots spinner styles
  - Optional progress percentage display
  - Timer-based animation with cleanup
  - AgentPanel loading state uses spinner (replaces static text)

- [x] **5.16** Polish and Refinement ✅ COMPLETE
  - Unified state classes (`.state-success`, `.state-warning`, `.state-error`, `.state-loading`)
  - Pulse animation classes (`.pulse-vote`, `.pulse-leader`, `.pulse-winner`)
  - Action button types (`Button.action-primary`, `Button.action-danger`)
  - Progress indicator styling
  - Final stream panel button and follow-up container styles

- [x] **5.17** Enhanced Keyboard Shortcuts ✅ COMPLETE (NEW)
  - Single-key shortcuts when not in input: q, s, o, v, w, f, c, m, a, t, h/?
  - `q` key cancels/stops current execution
  - Escape unfocuses input to enable shortcuts
  - `i` or `/` refocuses input (vim-like)
  - Full docstring in `_handle_agent_shortcuts()`

### Future Tasks - Session Management (WebUI Parity)

#### Not Started (For Later)

- [ ] **5.18** Session Management
  - View previous sessions
  - End session gracefully
  - Continue session after end
  - Session history browser
  - Session persistence/resume

### Files Modified
- `textual_terminal_display.py` - New modals: AnswerBrowserModal, TimelineModal, WorkspaceBrowserModal, MCPStatusModal, BrowserTabsModal; enhanced toasts with `notify_new_answer()` and `notify_vote()`; answer/vote tracking; new key bindings (b, t, w, p, u); VoteResultsModal enhanced with distribution chart; StatusBar progress summary; winner celebration effects via `_celebrate_winner()`
- `interactive_controller.py` - New commands: `/answers`, `/timeline`, `/files`, `/mcp`, `/browser`; HELP_TEXT updated
- `textual_themes/dark.tcss` - Modal styling for all modals; vote animations; winner tab styling; consensus-reached StatusBar styling; unified browser modal CSS
- `textual_themes/light.tcss` - Modal styling for all modals; vote animations; winner tab styling; consensus-reached StatusBar styling; unified browser modal CSS

### Acceptance Criteria
- [x] Keyboard shortcuts accessible via ? key
- [x] Agent output viewable during coordination
- [x] Welcome screen shows help hint
- [x] Vote visualization feels responsive (leader highlight, animations)
- [x] MCP status viewable via p key or /mcp command
- [x] Answer browser with filtering and details (`b` key)
- [x] Timeline visualization (`t` key)
- [x] Workspace browser with file preview (`w` key)
- [x] Enhanced toasts with model names and standings
- [x] Vote distribution bar chart (in vote modal `v` key)
- [x] Progress summary indicators (in StatusBar)
- [x] Winner celebration effects (tab highlight, toast, StatusBar update)
- [x] Multi-tab browser modal (`u` key, `/browser` command)
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
