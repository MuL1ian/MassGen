# Implementation Tasks

## Approval Workflow

**IMPORTANT**: After completing each phase, stop and ask the user to run the TUI for visual approval before proceeding to the next phase.

```
Phase N complete → User runs TUI → User approves → Proceed to Phase N+1
                                 → User requests changes → Iterate → Re-approve
```

Each phase section ends with a **CHECKPOINT** task to remind you to pause for approval.

---

## 1. Phase 1: Input Bar + Mode Toggles ✓ COMPLETED

### 1.1 Mode Toggle Redesign
- [x] 1.1.1 Update `ModeToggle.ICONS` to use radio indicators (◉/○) instead of emoji
- [x] 1.1.2 Update `ModeToggle.LABELS` - kept "Refine OFF" per user preference
- [x] 1.1.3 Update `ModeToggle.render()` to display cleaner format
- [x] 1.1.4 Update CSS for `.state-*` classes with softer colors

### 1.2 Unified Input Card
- [~] 1.2.1 SKIPPED: Keep existing ModeBar + Input structure (simpler)
- [x] 1.2.2 Update CSS to use `border: round` for rounded corners
- [~] 1.2.3 SKIPPED: Keep mode toggles as separate widget (cleaner separation)
- [~] 1.2.4 SKIPPED: Keep existing hint layout
- [~] 1.2.5 SKIPPED: Existing padding is adequate

### 1.3 Input Styling
- [x] 1.3.1 Update `#input_area` CSS - transparent background for clean look
- [x] 1.3.2 Update `#question_input` CSS - rounded border, transparent background
- [x] 1.3.3 Update `#mode_bar` CSS - transparent background
- [~] 1.3.4 Placeholder text unchanged (existing is fine)
- [x] **1.3.5 CHECKPOINT: User approval for input bar + mode toggles ✓**

**Implementation Notes:**
- Files modified: `mode_bar.py`, `dark.tcss`, `light.tcss`
- Key change: Transparent backgrounds for `#input_area`, `#mode_bar`, and `#question_input`
- Mode toggles use softer colors: #1a3a2a (green), #3d3520 (warning), #2d2d2d (off)
- User preferred keeping "Refine OFF" label over "Skip"

## 2. Phase 2: Agent Tabs ✓ COMPLETED

### 2.1 Tab Indicator Redesign
- [x] 2.1.1 Replace emoji status icons with dot indicators in `tab_bar.py`
- [x] 2.1.2 Add model name display to tabs (inline, shortened)
- [x] 2.1.3 Update CSS for new tab styling with underline indicator

### 2.2 Tab Spacing
- [x] 2.2.1 Updated tab spacing and removed borders for cleaner look
- [x] 2.2.2 Remove bracket notation `[1]` from tabs
- [x] **2.2.3 CHECKPOINT: User approval for agent tabs ✓**

**Implementation Notes:**
- Files modified: `tab_bar.py`, `textual_terminal_display.py`, `dark.tcss`, `light.tcss`
- STATUS_ICONS changed from emoji (⏳, ⚙️, 📝, ✅, ❌, 🏆) to dots (○, ◉, ✓, ✗)
- Model names shown inline with shortening (removes `-preview`, `-latest`, `-turbo` suffixes, truncates to 15 chars)
- Tab height reduced to 2 for compact display
- Active tabs use underline indicator (border-bottom: tall) instead of full border
- Agent color palette now applies to underline only on active tab

## 3. Phase 3: Tool Cards ✓ COMPLETED

### 3.1 Collapsible Implementation
- [x] 3.1.1 Add `collapsed` state to `ToolCallCard`
- [x] 3.1.2 Implement collapsed rendering (tool name + status + time + inline preview)
- [x] 3.1.3 Add click handler to expand/collapse (context-aware: left edge collapses, elsewhere opens modal)
- [x] 3.1.4 Default to collapsed state

### 3.2 Visual Styling
- [x] 3.2.1 Update CSS - thinner borders (`solid` instead of `wide`/`thick`), more padding
- [x] 3.2.2 Soften category colors (less saturated)
- [x] 3.2.3 Remove emoji icons, use text symbols (◉ for running, ○ for background)
- [x] **3.2.4 CHECKPOINT: User approval for tool cards ✓**

**Implementation Notes:**
- Files modified: `tool_card.py`, `task_plan_card.py`, `textual_terminal_display.py`, `dark.tcss`, `light.tcss`
- Click behavior: collapsed→expand, expanded+left edge→collapse, expanded+elsewhere→modal
- Inline preview auto-resizes based on terminal width (`_get_available_preview_width`)
- Continuous vertical lines for reasoning blocks (removed gaps between thinking blocks)
- Task plan pinned at top with Ctrl+T toggle, resets on new round
- Help modal updated with all keyboard shortcuts

## 4. Phase 4: Welcome Screen ✓ COMPLETED

### 4.1 Layout Improvements
- [x] 4.1.1 Keep ASCII logo (user preference)
- [x] 4.1.2 Center input prompt area (already centered via CSS)
- [x] 4.1.3 Make tagline subtle (removed emoji, changed to muted color)

### 4.2 Help Hints
- [x] 4.2.1 Make keyboard hints smaller/muted (use [dim] markup)
- [x] 4.2.2 Clean up hint formatting (removed ○ prefix, consistent bullet separators)
- [x] **4.2.3 CHECKPOINT: User approval for welcome screen ✓**

**Implementation Notes:**
- Files modified: `textual_terminal_display.py`, `dark.tcss`, `light.tcss`
- Tagline changed from "🤖 Multi-Agent Collaboration System" to plain "Multi-Agent Collaboration System"
- Tagline color: `$accent-info` (cyan) in dark theme, `#0891b2` (teal) in light theme
- Agent list color: `$fg-primary` (bright) in dark theme, `#1f2937` (dark gray) in light theme
- CWD hint cleaned up: removed leading `○` and colon for consistency
- Visual hierarchy: logo (bold blue) → tagline (cyan) → agents (bright) → hint (blue accent) → shortcuts (muted)

## 5. Phase 5: Task Lists + Progress ✓ COMPLETED

### 5.1 Progress Bar
- [x] 5.1.1 Add visual progress bar to task section (inline mini bar: `━━━━━━───────`)
- [x] 5.1.2 Show "X of Y" count display (header: `▸ Tasks (3/5)`)

### 5.2 Task Indicators
- [x] 5.2.1 Update task indicators (● in-progress, ○ pending, ✓ done) - already existed
- [x] 5.2.2 Add "← current" marker for active task (changed from "← active")
- [x] 5.2.3 Implement smart truncation with ellipsis - already existed
- [x] **5.2.4 CHECKPOINT: User approval for task lists + progress ✓**

**Implementation Notes:**
- Files modified: `task_plan_card.py`, `task_plan_modal.py`, `textual_terminal_display.py`
- Mini progress bar added inline with header: `▸ Tasks (3/5)  ━━━━━━──────────`
- Progress bar uses `━` for completed, `─` (thin line) for remaining
- Changed `← active` to `← current` for consistency with spec
- Removed redundant "Tasks: X/Y" badge from top-right (info now in collapsible card)
- Click on task card opens full modal (same as Ctrl+T)
- Removed expand/collapse toggle - modal provides full view

## 6. Phase 6: Modals + Enhanced Previews ✓ COMPLETED

### 6.1 Modal Visual Redesign
- [x] 6.1.1 Update all modal containers to use solid borders (softer than thick)
- [x] 6.1.2 Remove emoji from modal titles
- [x] 6.1.3 Use bullet separators in modal headers
- [x] 6.1.4 Soften border colors across all modals (hardcoded hex colors - theme vars don't work in DEFAULT_CSS)
- [x] 6.1.5 Improve internal padding and margins
- [x] 6.1.6 Unify button styling across modals
- [x] 6.1.7 Polish close button with softer hover states

**Implementation Notes:**
- Files modified: `task_plan_modal.py`, `tool_detail_modal.py`, `background_tasks_modal.py`, `plan_approval_modal.py`, `subagent_modal.py`
- All modals now use `border: solid` instead of `border: thick`
- **Important**: Theme variables (`$accent-*`) don't work in modal `DEFAULT_CSS` blocks - used hardcoded hex colors instead:
  - `#a371f7` (purple), `#d29922` (warning/yellow), `#39c5cf` (info/cyan), `#58a6ff` (primary/blue)
  - `#3fb950` (success/green), `#f85149` (error/red), `#8b949e` (muted), `#e6edf3` (primary text)
  - `#0d1117` (bg-base), `#1c2128` (surface), `#161b22` (surface-2), `#21262d` (surface-3), `#30363d` (border)
- Title changes: TaskPlanModal (📋 → "Task Plan"), ToolDetailModal (emoji removed), BackgroundTasksModal (⚙️ → "Background Operations"), PlanApprovalModal ("Plan Ready for Execution" → "Plan Approval"), SubagentModal (🚀 → "Subagent . ")
- Close buttons have softer colors (#8b949e) with hover states (#e6edf3)

### 6.2 Diff View for File Edits (DEFERRED)
- [ ] 6.2.1 Create `DiffView` widget for displaying file changes
- [ ] 6.2.2 Implement colored diff rendering (green +, red -)
- [ ] 6.2.3 Add line numbers to diff display
- [ ] 6.2.4 Show context lines around changes
- [ ] 6.2.5 Add "+X -Y lines" summary header
- [ ] 6.2.6 Integrate diff view into tool result display for write_file/edit operations
**Note: Deferred to a future phase.**

### 6.3 Workspace Browser Improvements
- [x] 6.3.1 Implemented proper tree view with ASCII connectors (├──, └──, │)
- [x] 6.3.2 Collapsible directories - dirs with >3 files collapsed by default
- [x] 6.3.3 Click directory header (▶/▼) to expand/collapse
- [x] 6.3.4 Filter out subagent directories (UUID patterns, agent_*, subagent_*, gitignored dirs)
- [x] 6.3.5 Removed redundant WorkspaceFilesModal - consolidated into WorkspaceBrowserModal
- [x] 6.3.6 Removed emoji from UI (📁 → text, 📂 → text)

**Implementation Notes:**
- Files modified: `browser_modals.py`, `workspace_modals.py` (removed WorkspaceFilesModal), `textual/__init__.py`, `textual/widgets/__init__.py`, `textual/widgets/modals/__init__.py`, `textual_terminal_display.py`
- Tree display shows: `▶ dirname/ (count)` for collapsed, `▼ dirname/` for expanded
- Added `_expanded_dirs` set and `_dir_file_counts` dict for state tracking
- `_toggle_directory()` and `_refresh_file_list()` methods handle expansion
- Directory filtering uses `SKIP_DIRS_FOR_LOGGING` constant + custom patterns for UUIDs, timestamps, agent dirs
- `/workspace` command now calls `_show_workspace_browser()` instead of removed modal

### 6.4 Better Tool Result Previews
- [x] 6.4.1 Create formatted preview renderer for common result types (ResultRenderer class)
- [x] 6.4.2 Replace raw dict display with readable formatting
- [x] 6.4.3 Implement smart truncation with line/char limits
- [x] 6.4.4 Add basic syntax highlighting for code in results (JSON, Python, etc.)
- [x] **6.4.5 CHECKPOINT: User approval for modals + enhanced previews ✓**

**Implementation Notes:**
- New file created: `result_renderer.py`
- Content type detection: JSON, Python, JavaScript, TypeScript, Markdown, YAML, XML, Shell
- Uses `rich.syntax.Syntax` for syntax highlighting
- Smart truncation with configurable limits (50 lines, 5000 chars default)
- JSON is pretty-printed before highlighting
- Integrated into ToolDetailModal for arguments and output display

## 7. Phase 7: Header + Final Polish

### 7.1 Header Simplification
- [ ] 7.1.1 Remove emoji from HeaderWidget
- [ ] 7.1.2 Use bullet separator (•) instead of pipe

### 7.2 Color Refinements
- [ ] 7.2.1 Slightly desaturate accent colors in dark.tcss
- [ ] 7.2.2 Update light.tcss to match new aesthetic
- [ ] 7.2.3 Add softer border colors

### 7.3 New CSS Classes
- [ ] 7.3.1 Add `.rounded-card` class
- [ ] 7.3.2 Add `.input-hero` class
- [ ] 7.3.3 Add `.mode-pill` class
- [ ] 7.3.4 Add `.progress-bar` class
- [ ] 7.3.5 Add `.diff-add` and `.diff-remove` classes
- [ ] 7.3.6 Add `.tree-node` class for workspace tree
- [ ] **7.3.7 CHECKPOINT: User approval for header + final polish**

## 8. Phase 8: Professional Visual Polish

### 8.1 Animation & Feedback System (Phase 8a)
- [ ] 8.1.1 Implement pulsing dot animation for active agent tabs (800ms cycle, opacity 0.5↔1.0)
- [ ] 8.1.2 Add blinking cursor `▌` at end of streaming text (530ms cycle)
- [ ] 8.1.3 Implement tool card time ticking during execution (`⟳ 0.1s → 0.2s...`)
- [ ] 8.1.4 Add fade-in transitions for tool results (150ms)
- [ ] 8.1.5 Add fade-in/out for modal open/close (150ms)
- [ ] 8.1.6 Implement phase indicator highlight pulse on change (300ms)
- [ ] 8.1.7 Add round separator fade-in (200ms)
- [ ] 8.1.8 Implement error toast with auto-dismiss (3s)
- [ ] **8.1.9 CHECKPOINT: User approval for animations**

### 8.2 Professional Color Palette (Phase 8b)
- [ ] 8.2.1 Define CSS variables for background layers ($bg-base, $bg-surface, $bg-card, $bg-elevated)
- [ ] 8.2.2 Define CSS variables for borders ($border-subtle, $border-default, $border-focus)
- [ ] 8.2.3 Define CSS variables for text hierarchy ($text-primary, $text-secondary, $text-muted)
- [ ] 8.2.4 Define CSS variables for semantic accents ($accent-blue, $accent-green, $accent-yellow, $accent-red, $accent-purple)
- [ ] 8.2.5 Update dark.tcss with new color palette
- [ ] 8.2.6 Update light.tcss with corresponding light theme colors
- [ ] 8.2.7 Apply new colors to all existing widgets
- [ ] **8.2.8 CHECKPOINT: User approval for color palette**

### 8.3 Agent Status Ribbon (Phase 8c)
- [ ] 8.3.1 Create new `AgentStatusRibbon` widget
- [ ] 8.3.2 Implement activity indicator display (◉ Streaming, ○ Idle, ⏳ Thinking, ⏹ Canceled, ✗ Error)
- [ ] 8.3.3 Add elapsed time display with real-time ticking updates
- [ ] 8.3.4 Add compact tasks progress display (X/Y with mini progress bar `━━░░`)
- [ ] 8.3.5 Add token count display
- [ ] 8.3.6 Add cost estimate display
- [ ] 8.3.7 Make Tasks segment clickable → opens Task Plan Modal
- [ ] 8.3.8 Wire ribbon to update when switching agent tabs
- [ ] 8.3.9 Position ribbon below tab bar in layout
- [ ] 8.3.10 Add round timeout display with tiered timeouts:
  - Show soft timeout countdown (from `initial_round_timeout_seconds` or `subsequent_round_timeout_seconds`)
  - Show grace period when soft expires (from `round_timeout_grace_seconds`)
  - Show hard timeout as soft + grace total
  - Format: `⏱ 5:30 soft │ 2:00 grace` or `⏱ 7:30 remaining`
- [ ] 8.3.11 Update timeout display colors: normal (muted), warning (<30s soft, yellow), grace period (orange), critical (<30s total, red)
- [ ] **8.3.12 CHECKPOINT: User approval for status ribbon**

### 8.4 Phase Indicator Bar (Phase 8d)
- [ ] 8.4.1 Create new `PhaseIndicatorBar` widget
- [ ] 8.4.2 Implement phase states: Initial Answer → Voting → Consensus → Presentation
- [ ] 8.4.3 Add visual indicators: ○ pending, ● current (with pulse), ✓ completed
- [ ] 8.4.4 Add arrow separators (→) between phases
- [ ] 8.4.5 Wire to orchestrator phase changes
- [ ] 8.4.6 Add highlight pulse animation on phase change (300ms)
- [ ] 8.4.7 Only show in multi-agent mode
- [ ] **8.4.8 CHECKPOINT: User approval for phase indicator**

### 8.5 Session Info Panel (Phase 8e)
- [ ] 8.5.1 Create new `SessionInfoPanel` widget
- [ ] 8.5.2 Add turn counter display (Turn X of Y)
- [ ] 8.5.3 Add elapsed time with real-time updates
- [ ] 8.5.4 Add total cost estimate (aggregated across agents)
- [ ] 8.5.5 Add total token count (aggregated across agents)
- [ ] 8.5.6 Position in header area (top of screen)
- [ ] 8.5.7 Style with rounded borders, subtle background
- [ ] **8.5.8 CHECKPOINT: User approval for session info panel**

### 8.6 Improved Round Separators (Phase 8f)
- [ ] 8.6.1 Replace box-style round indicators with dashed line separators (┄┄┄)
- [ ] 8.6.2 Center "Round X Complete" text in separator
- [ ] 8.6.3 Add summary line below (vote count, consensus status)
- [ ] 8.6.4 Add fade-in animation when separator appears (200ms)
- [ ] 8.6.5 Add breathing room (padding) around separators
- [ ] **8.6.6 CHECKPOINT: User approval for round separators**

### 8.7 Final Answer Card Redesign (Phase 8g)
- [ ] 8.7.1 Remove trophy emoji from title, use "Final Answer" (title case, not ALL CAPS)
- [ ] 8.7.2 Replace gold colors (#ffd700) with muted green ($accent-green, desaturated)
- [ ] 8.7.3 Simplify vote summary: "2 agents agreed • 1 round" instead of cryptic "Winner: A1.1 (2v) | Votes: A1.1(2)"
- [ ] 8.7.4 Use rounded corners (border: round) for softer appearance
- [ ] 8.7.5 Remove external "✓ Complete" progress bar (redundant)
- [ ] 8.7.6 Add summary footer inside card (consensus status, rounds, agents, cost)
- [ ] 8.7.7 Use softer border weight (solid instead of double/thick)
- [ ] 8.7.8 Post-eval status cleanup:
  - Change completed title from "✅ FINAL ANSWER" to "✓ Final Answer"
  - Change "🔍 Evaluating..." to "◉ Evaluating..."
  - Change "🔄 Restart Requested" to "↻ Restart Requested"
  - Keep "✓ Verified" as-is (already clean)
- [ ] 8.7.9 Improve internal padding and whitespace
- [ ] 8.7.10 Apply proper markdown rendering
- [ ] **8.7.11 CHECKPOINT: User approval for final answer card**

### 8.8 Enhanced Tab Design (Phase 8h)
- [ ] 8.8.1 Implement two-line tab display (agent name bold + model name muted)
- [ ] 8.8.2 Add rounded corners for selected tab (╭╮╰╯), square for unselected
- [ ] 8.8.3 Add underline indicator (════) below selected tab
- [ ] 8.8.4 Implement status-specific indicator colors:
  - `◉` Streaming/Active (accent-blue, pulsing)
  - `○` Idle/Waiting (text-muted)
  - `✓` Done (accent-green)
  - `⏹` Canceled (accent-yellow)
  - `✗` Error (accent-red)
- [ ] 8.8.5 Update tab spacing for breathing room
- [ ] **8.8.6 CHECKPOINT: User approval for tab design**

### 8.9 Visual Depth Through Layering (Phase 8i)
- [ ] 8.9.1 Apply $bg-card to main card elements
- [ ] 8.9.2 Apply $bg-elevated to nested/inset content
- [ ] 8.9.3 Add left accent borders where appropriate
- [ ] 8.9.4 Add focus ring ($border-focus) to interactive elements
- [ ] 8.9.5 Ensure consistent layering across all widgets
- [ ] **8.9.6 CHECKPOINT: User approval for visual depth**

### 8.10 Improved Task Modal (Phase 8j)
- [ ] 8.10.1 Update task modal with rounded corners
- [ ] 8.10.2 Add progress bar in modal header (━━━━░░░░)
- [ ] 8.10.3 Add fraction display (X/Y) with visual bar
- [ ] 8.10.4 Implement task indicators (✓ done, ● current, ○ pending)
- [ ] 8.10.5 Add "← current" marker for active task
- [ ] 8.10.6 Ensure full task names displayed (not truncated)
- [ ] 8.10.7 Add close button and click-outside-to-dismiss
- [ ] 8.10.8 Modal fade-in animation (150ms)
- [ ] **8.10.9 CHECKPOINT: User approval for task modal**

---

## 9. Phase 9: Remove Outer Container Border

### 9.1 Container Styling
- [ ] 9.1.1 Remove border from main app container (Screen or top-level widget)
- [ ] 9.1.2 Ensure content flows edge-to-edge without outer frame
- [ ] 9.1.3 Update dark.tcss and light.tcss to remove container borders
- [ ] 9.1.4 Test that keyboard focus rings and modals still work correctly
- [ ] **9.1.5 CHECKPOINT: User approval for borderless container**

---

## 10. Phase 10: Content Area Cleanup

### 10.1 Remove Redundant Agent Header
- [ ] 10.1.1 Remove "agent_a [1]" style header from content area (redundant with tabs)
- [ ] 10.1.2 Move round info to Agent Status Ribbon (handled in 8.3.10)
- [ ] 10.1.3 Ensure content area starts directly with agent output
- [ ] 10.1.4 Update all themes to remove content header styling
- [ ] **10.1.5 CHECKPOINT: User approval for content area cleanup**

---

## 11. Phase 11: UX Polish

### 11.1 Collapsible Reasoning Blocks
Long `<thinking>` or reasoning sections should be collapsed by default to improve readability.
- [ ] 11.1.1 Detect reasoning/thinking blocks in content (look for `<thinking>` tags or "Thinking:" prefixes)
- [ ] 11.1.2 Show first 3-5 lines of reasoning by default
- [ ] 11.1.3 Add "[+N more lines]" expander link below truncated content
- [ ] 11.1.4 Implement click to expand/collapse reasoning blocks
- [ ] 11.1.5 Remember expansion state within session
- [ ] **11.1.6 CHECKPOINT: User approval for collapsible reasoning blocks**

### 11.2 Scroll Indicators
Show visual cues when content is scrollable in containers.
- [ ] 11.2.1 Add scroll position tracking to main content area (ScrollableContainer)
- [ ] 11.2.2 Show ▲ indicator at top when content exists above viewport
- [ ] 11.2.3 Show ▼ indicator at bottom when content exists below viewport
- [ ] 11.2.4 Use subtle styling (muted color, small size) to avoid distraction
- [ ] 11.2.5 Hide indicators when at scroll boundaries
- [ ] **11.2.6 CHECKPOINT: User approval for scroll indicators**

---

## 12. Phase 12: Testing & Verification

- [ ] 12.1 Run MassGen with multi-agent config, verify welcome screen
- [ ] 12.2 Test mode toggle interactions
- [ ] 12.3 Verify tool cards collapse/expand behavior
- [ ] 12.4 Test task list progress display
- [ ] 12.5 Verify all keyboard shortcuts still work
- [ ] 12.6 Test both dark and light themes
- [ ] 12.7 Verify modal styling consistency
- [ ] 12.8 Test diff view with file edit operations
- [ ] 12.9 Test workspace modal tree view navigation
- [ ] 12.10 Verify tool result preview formatting
- [ ] 12.11 Test agent status ribbon updates during execution
- [ ] 12.12 Verify phase indicator bar shows correct coordination state
- [ ] 12.13 Test session info panel updates
- [ ] 12.14 Verify activity pulse animation works
- [ ] 12.15 Test final answer card with consensus results
- [ ] 12.16 Test round timeout display with soft/grace/hard timeouts
- [ ] 12.17 Test collapsible reasoning blocks (expand/collapse)
- [ ] 12.18 Test scroll indicators in content area
