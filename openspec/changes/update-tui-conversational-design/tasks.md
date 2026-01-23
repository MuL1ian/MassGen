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

## 7. Phase 7: Header + Final Polish ✓ COMPLETED

### 7.1 Header Simplification
- [x] 7.1.1 Remove emoji from HeaderWidget (🤖, 💬, ⚠️ removed)
- [x] 7.1.2 Use bullet separator (•) instead of pipe

### 7.2 Color Refinements
- [x] 7.2.1 Desaturate accent colors in dark.tcss (15-20% softer)
- [x] 7.2.2 Update light.tcss to match new aesthetic
- [x] 7.2.3 Add softer border colors ($border-soft, $border-accent)

### 7.3 New CSS Classes
- [x] 7.3.1 Add `.rounded-card` class
- [x] 7.3.2 Add `.input-hero` class
- [x] 7.3.3 Add `.mode-pill` class
- [x] 7.3.4 Add `.progress-bar` and `.progress-bar-fill` classes
- [x] 7.3.5 Add `.diff-add` and `.diff-remove` classes
- [x] 7.3.6 Add `.tree-node`, `.tree-node-expanded`, `.tree-node-collapsed` classes
- [x] **7.3.7 CHECKPOINT: User approval for header + final polish ✓**

**Implementation Notes:**
- Files modified: `textual_terminal_display.py`, `dark.tcss`, `light.tcss`
- Header now displays: `MassGen • {num_agents} agents • Turn {turn} • {question}`
- Desaturated accent colors for softer appearance:
  - Primary: `#58a6ff` → `#5199d9`
  - Success: `#3fb950` → `#3a9d52`
  - Warning: `#d29922` → `#c4912a`
  - Error: `#f85149` → `#e04a42`
  - Info: `#39c5cf` → `#3ab0b5`
  - Special: `#a371f7` → `#9568d9`
- Light theme updated: `#0066cc` → `#1a6bb8`, `#0891b2` → `#0e7490`, `#1a7f37` → `#2e7d4a`
- New utility CSS classes added for Phase 8 preparation

## 8. Phase 8: Professional Visual Polish ✓ COMPLETED

### 8.1 Animation & Feedback System (Phase 8a) - SKIPPED
User requested no pulsing animations. Fade-in classes exist for future use.
- [x] 8.1.1-8.1.8 SKIPPED per user preference
- [x] **8.1.9 CHECKPOINT: User approved skipping animations**

### 8.2 Professional Color Palette (Phase 8b) ✓
- [x] 8.2.1 CSS variables for background layers ($bg-base, $bg-surface, $bg-card, $bg-elevated)
- [x] 8.2.2 CSS variables for borders ($border-subtle, $border-default, $border-focus)
- [x] 8.2.3-8.2.7 Applied to dark.tcss
- [x] **8.2.8 CHECKPOINT: User approved color palette**

### 8.3 Agent Status Ribbon (Phase 8c) ✓ SIMPLIFIED
Simplified version mounted - shows Round, Timeout, Tokens, Cost placeholders.
- [x] 8.3.1 Created `AgentStatusRibbon` widget
- [x] 8.3.9 Positioned below tab bar
- [x] 8.3.12 Round selector shows `Round N ▾`
- [~] 8.3.2-8.3.4 Activity indicator and tasks REMOVED (redundant)
- [~] 8.3.5-8.3.6 Token/cost display - placeholders only, backend wiring in Phase 13.1
- [x] **8.3.16 CHECKPOINT: User approved simplified ribbon**

### 8.4 Phase Indicator Bar (Phase 8d) - REMOVED
Removed as redundant - ExecutionStatusLine in Phase 13.2 will handle status display.
- [x] 8.4.1 Widget created but removed from layout
- [x] **8.4.8 CHECKPOINT: User approved removal**

### 8.5 Session Info Panel (Phase 8e) - REMOVED
Removed as redundant - session info moved to tab bar right side.
- [x] 8.5.1 Widget created but removed from layout
- [x] **8.5.8 CHECKPOINT: User approved removal**

**New: Session Info in Tab Bar**
- [x] Turn number and question displayed on right side of tab bar
- [x] Blue icon (◈) and styling to distinguish from agent names
- [x] Clickable to show full prompt in modal
- [x] HeaderWidget removed entirely (info consolidated in tab bar)

### 8.6 Round Separators (Phase 8f) - **SUPERSEDED BY PHASE 12**
**Note:** This phase is superseded by Phase 12 (View-Based Navigation).
Round separators are removed entirely - navigation via view dropdown instead.

- [x] 8.6.1 ~~Remove banner-style separators~~ → Handled by Phase 12
- [x] 8.6.2 ~~Round switching via dropdown~~ → Handled by Phase 12
- [x] **8.6.3 SUPERSEDED: See Phase 12 for implementation**

### 8.7 Final Answer Card Redesign (Phase 8g) - **SUPERSEDED BY PHASE 12**
**Note:** This phase is superseded by Phase 12 (View-Based Navigation).
Final Answer becomes a dedicated view/screen, not an inline card.

- [x] 8.7.1-8.7.10 ~~Inline card redesign~~ → Replaced by Phase 12.3 (Final Answer View)
- [x] **8.7.11 SUPERSEDED: See Phase 12.3 for implementation**

### 8.8 Enhanced Tab Design (Phase 8h) ✓
- [x] 8.8.1 Two-line tab display (agent name + model name)
- [x] 8.8.3 Underline indicator for active tab (border-bottom: tall)
- [x] 8.8.4 Status indicators: ○ waiting, ◉ working, ✓ completed, ✗ error
- [x] 8.8.5 Tab spacing updated
- [x] **8.8.6 CHECKPOINT: User approved tab design**

### 8.9 Visual Depth Through Layering (Phase 8i) ✓
- [x] 8.9.1 Applied $bg-card to modal content areas
- [x] 8.9.4 Added focus rings ($border-focus) to AgentTab, ModeToggle, #session_info
- [x] 8.9.5 Consistent focus states across interactive elements
- [x] **8.9.6 CHECKPOINT: User approved visual depth**

### 8.10 Improved Task Modal (Phase 8j) ✓
Already complete from previous phases:
- [x] 8.10.1 Rounded corners (`border: round $accent-special`)
- [x] 8.10.2 Progress bar in header
- [x] 8.10.3 Fraction display (X/Y)
- [x] 8.10.4 Task indicators (✓ ● ○)
- [x] 8.10.5 "← current" marker for active task
- [x] 8.10.6 Full task names displayed
- [x] 8.10.7 Close button present
- [x] **8.10.9 CHECKPOINT: User approved task modal**

**Implementation Notes for Phase 8:**
- Files modified: `tab_bar.py`, `dark.tcss`, `_variables.tcss`, `textual_terminal_display.py`
- SessionInfoWidget added to tab_bar.py with click-to-expand prompt modal
- SessionInfoClicked message for modal handling
- HeaderWidget removed from compose (info consolidated in tab bar)
- Phase Indicator Bar and Session Info Panel widgets exist but removed from layout
- Status ribbon simplified: Round selector + timeout + token/cost placeholders

---

## 9. Phase 9: Remove Outer Container Border

### 9.1 Container Styling
- [ ] 9.1.1 Remove border from main app container (Screen or top-level widget)
- [ ] 9.1.2 Ensure content flows edge-to-edge without outer frame
- [ ] 9.1.3 Update dark.tcss and light.tcss to remove container borders
- [ ] 9.1.4 Test that keyboard focus rings and modals still work correctly
- [ ] **9.1.5 CHECKPOINT: User approval for borderless container**

---

## 10. Phase 10: Content Area Cleanup ✓ COMPLETED

### 10.1 Remove Redundant Agent Header
Completed as part of Phase 8 - header info consolidated into tab bar.
- [x] 10.1.1 Removed "agent_a [1]" style header (redundant with tabs)
- [x] 10.1.2 Round info in Agent Status Ribbon
- [x] 10.1.3 Content area starts directly with agent output
- [x] 10.1.4 HeaderWidget removed entirely
- [x] **10.1.5 CHECKPOINT: User approved (part of Phase 8)**

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

## 12. Phase 12: View-Based Round & Final Answer Navigation

**This phase supersedes Phase 8f (Round Separators) and Phase 8g (Final Answer Card).**

### 12.1 View Dropdown in Status Ribbon (Phase 12a)
- [ ] 12.1.1 Update `AgentStatusRibbon` round selector to become a full view selector
- [ ] 12.1.2 Add "Final Answer" option at top of dropdown (only shown after consensus)
- [ ] 12.1.3 Show separator line between Final Answer and rounds
- [ ] 12.1.4 Display round indicators: `◉ Round N (current)`, `Round N`, `↻ Round N` (context reset)
- [ ] 12.1.5 Implement dropdown click handler to switch views
- [ ] 12.1.6 Update ribbon label to show current view ("Round 2 ▾" or "✓ Final Answer ▾")
- [ ] **12.1.7 CHECKPOINT: User approval for view dropdown**

### 12.2 Round View Content (Phase 12b)
- [ ] 12.2.1 Create per-round content storage: `agent_views[agent_id]["rounds"][round_num]`
- [ ] 12.2.2 Modify content append methods to store content by round number
- [ ] 12.2.3 Implement `switch_to_round(agent_id, round_num)` method
- [ ] 12.2.4 Clear and repopulate agent panel when switching rounds
- [ ] 12.2.5 Remove `RestartBanner` widget (no longer needed)
- [ ] 12.2.6 Remove inline separators from content flow
- [ ] 12.2.7 Track current view per agent: `agent_views[agent_id]["current_view"]`
- [ ] **12.2.8 CHECKPOINT: User approval for round view switching**

### 12.3 Final Answer View - Dedicated Screen (Phase 12c)
- [ ] 12.3.1 Create new `FinalAnswerView` widget (dedicated screen, not inline card)
- [ ] 12.3.2 Design centered layout with generous whitespace
- [ ] 12.3.3 Add "Final Answer" title (centered, clean typography)
- [ ] 12.3.4 Add horizontal separators above/below content
- [ ] 12.3.5 Display final answer content with proper markdown rendering
- [ ] 12.3.6 Add metadata footer: consensus status, presenting agent, rounds, agents agreed
- [ ] 12.3.7 Add action buttons: [Copy] [Workspace] [Voting Details]
- [ ] 12.3.8 Add "Type below to continue" hint
- [ ] 12.3.9 Store final answer data: `agent_views[agent_id]["final_answer"]`
- [ ] 12.3.10 Remove inline `FinalPresentationCard` (replaced by this view)
- [ ] **12.3.11 CHECKPOINT: User approval for Final Answer view**

### 12.4 Auto-Navigation (Phase 12d)
- [ ] 12.4.1 When consensus is reached, add "Final Answer" to view dropdown
- [ ] 12.4.2 Auto-switch presenting agent's tab to Final Answer view
- [ ] 12.4.3 Keep other agent tabs on their current round view
- [ ] 12.4.4 Allow user to navigate back to any round via dropdown
- [ ] **12.4.5 CHECKPOINT: User approval for auto-navigation**

### 12.5 Deprecations & Cleanup (Phase 12e)
- [ ] 12.5.1 Remove `RestartBanner` class from `content_sections.py`
- [ ] 12.5.2 Remove `FinalPresentationCard` class from `content_sections.py`
- [ ] 12.5.3 Remove round separator CSS from `dark.tcss` and `light.tcss`
- [ ] 12.5.4 Remove inline final answer card CSS
- [ ] 12.5.5 Update `__init__.py` exports (remove deprecated, add new)
- [ ] 12.5.6 Clean up any references to removed widgets
- [ ] **12.5.7 CHECKPOINT: User approval for cleanup**

---

## 13. Phase 13: Backend Integration for Status Ribbon

### 13.1 Token/Cost Wiring
The status ribbon has placeholders for tokens and cost that need backend integration.

- [ ] 13.1.1 Add token tracking to `ChatAgent` - accumulate input/output tokens per turn
- [ ] 13.1.2 Add cost calculation using `token_manager` pricing data
- [ ] 13.1.3 Pass token/cost data through `TextualTerminalDisplay` callbacks
- [ ] 13.1.4 Wire `AgentStatusRibbon.set_tokens()` and `set_cost()` methods
- [ ] 13.1.5 Update ribbon display in real-time during streaming
- [ ] **13.1.6 CHECKPOINT: User approval for token/cost display**

### 13.2 Execution Status Line (Multi-Agent Aware)
Add a status line above the mode bar showing activity across ALL agents, not just the focused one.

**Design Options (implement 1c as default, test others):**

**Option 1c - Two-Line Status (DEFAULT):**
```
  ◉ agent_a thinking...                                     R2 • 45s • $0.02
  B: ✓ done  C: ◉ write_file
```

**Option 1b - All Agents Inline:**
```
  A: ◉ thinking    B: ✓ done    C: ◉ write_file (0.3s)
```

**Option 1a - Current Focus + Agent Pills:**
```
  ◉ agent_a is thinking...                    [B ✓] [C ◉]
```

**Tasks:**
- [ ] 13.2.1 Create `ExecutionStatusLine` widget with multi-agent awareness
- [ ] 13.2.2 Position above mode bar / below agent panels
- [ ] 13.2.3 Implement Option 1c (two-line) as default layout:
  - Top line: focused agent's detailed status + round/time/cost
  - Bottom line: other agents' compact status (letter: indicator action)
- [ ] 13.2.4 Track status for ALL agents, not just focused one:
  - `◉` streaming/thinking (with optional elapsed time)
  - `✓` done/ready
  - `○` waiting/idle
  - Tool name when executing tool (e.g., `write_file`)
  - Vote target when voted (e.g., `voted A1.2`)
- [ ] 13.2.5 Wire to orchestrator events for real-time updates across all agents
- [ ] 13.2.6 Update bottom line when switching agent tabs (swap focused vs other agents)
- [ ] 13.2.7 Use subtle styling (dim/muted) - bottom line even more muted than top
- [ ] 13.2.8 (Optional) Implement 1a and 1b as alternative layouts for A/B testing
- [ ] **13.2.9 CHECKPOINT: User approval for execution status line**

---

## 14. Phase 14: Testing & Verification

- [ ] 13.1 Run MassGen with multi-agent config, verify welcome screen
- [ ] 13.2 Test mode toggle interactions
- [ ] 13.3 Verify tool cards collapse/expand behavior
- [ ] 13.4 Test task list progress display
- [ ] 13.5 Verify all keyboard shortcuts still work
- [ ] 13.6 Test both dark and light themes
- [ ] 13.7 Verify modal styling consistency
- [ ] 13.8 Test diff view with file edit operations
- [ ] 13.9 Test workspace modal tree view navigation
- [ ] 13.10 Verify tool result preview formatting
- [ ] 13.11 Test agent status ribbon updates during execution
- [ ] 13.12 Verify phase indicator bar shows correct coordination state
- [ ] 13.13 Test session info panel updates
- [ ] 13.14 Verify activity pulse animation works
- [ ] 13.15 Test view dropdown in status ribbon
- [ ] 13.16 Test round view switching (select different round, verify content changes)
- [ ] 13.17 Test Final Answer view (clean layout, metadata, buttons)
- [ ] 13.18 Test auto-navigation to Final Answer on consensus
- [ ] 13.19 Verify navigation back from Final Answer to rounds
- [ ] 13.20 Test round timeout display with soft/grace/hard timeouts
- [ ] 13.21 Test collapsible reasoning blocks (expand/collapse)
- [ ] 13.22 Test scroll indicators in content area
- [ ] 13.23 Verify "ctx reset" indicator shows on appropriate rounds in dropdown
