# Change: TUI Visual Redesign - Conversational AI Aesthetic

## Why
The current TUI feels utilitarian and developer-focused rather than polished and modern. The design lacks visual hierarchy, uses dated emoji-based indicators, has dense information display without breathing room, and the input area feels secondary rather than being the hero element. A visual refresh following the "Conversational AI" aesthetic will make MassGen more approachable, modern, and enjoyable to use while maintaining functionality.

## What Changes

### Phase 1: Input Bar + Mode Toggles (Highest Impact)
- **Unified Input Card**: Integrate mode toggles INTO the input area as a single cohesive card
- **Rounded Corners**: Use rounded box-drawing characters (╭╮╰╯) for softer, modern feel
- **Simplified Mode Indicators**: Replace emoji with radio-style indicators (◉ active, ○ inactive)
- **Hero Input Area**: Increase vertical padding, add placeholder text, integrate submit hint
- **Focus States**: Subtle border color change on focus

### Phase 2: Agent Tabs
- **Dot Indicators**: Replace emoji status icons with simple dots (◉ active, ○ waiting, ✓ done)
- **Two-Line Display**: Agent name prominent, model name as subtitle
- **Improved Spacing**: More horizontal space between tabs

### Phase 3: Tool Cards (Adaptive Density)
- **Collapsed Default**: Show only tool name + status + time when collapsed
- **Click to Expand**: Expand to show parameters/result on interaction
- **Softer Styling**: Rounded corners, less saturated category colors

### Phase 4: Welcome Screen
- **Keep ASCII Logo**: Per user preference
- **Centered Input Prompt**: Make input area the focal point
- **Soften Help Hints**: Smaller, more muted keyboard shortcuts

### Phase 5: Task Lists + Progress
- **Progress Bar**: Visual progress indicator with "X of Y" count
- **Better Indicators**: ● in-progress, ○ pending, ✓ done with "← current" marker
- **Cleaner Truncation**: Smart ellipsis for long task names

### Phase 6: Modals + Enhanced Previews
- **Rounded Modal Containers**: Use rounded borders for all modals
- **Consistent Headers**: Remove emoji from modal titles, use bullet separators
- **Softer Borders**: Less harsh border colors, subtle shadows/depth
- **Improved Spacing**: Better padding and margins inside modals
- **Unified Button Styling**: Consistent button appearance across all modals
- **Close Button Polish**: Softer close button styling with hover states

### Phase 6b: Diff Views for File Edits
- **Colored Diff Display**: Show file edits as colored diffs (green +additions, red -deletions)
- **Context Lines**: Show surrounding context for changes
- **Line Numbers**: Display line numbers in diff view
- **Summary Stats**: Show "+X -Y lines" summary for each file edit

### Phase 6c: Workspace Modal Improvements
- **Tree View**: Display directory structure as a tree (not flattened list)
- **File Statistics**: Show number of files, total lines changed (+X -Y)
- **Collapsible Directories**: Allow expanding/collapsing directory nodes
- **File Type Icons**: Simple text-based icons for file types (📄 files, 📁 folders)

### Phase 6d: Better Tool Result Previews
- **Formatted Previews**: Replace raw dict results with formatted, readable output
- **Truncated Content**: Smart truncation with "show more" for long results
- **Syntax Highlighting**: Basic highlighting for code in results

### Phase 7: Header + Final Polish
- **Simplified Header**: Remove emoji, use bullet separator (•)
- **Color Refinements**: Slightly desaturated accents, warmer tones
- **Consistent Hierarchy**: De-emphasize chrome, emphasize content

### Phase 9: Remove Outer Container Border
- **Borderless Container**: Remove the visible border/frame around the entire TUI
- **Edge-to-Edge Content**: Let content flow to terminal edges for cleaner appearance
- **CSS Updates**: Modify dark.tcss and light.tcss to remove Screen/container borders

### Phase 10: Content Area Cleanup
- **Remove Redundant Agent Header**: Remove "agent_a [1]" header from content area (redundant with tabs)
- **Direct Content Start**: Content area starts directly with agent output, no header
- **Round Info Relocated**: Round/timeout info moved to Agent Status Ribbon (Phase 8c)

### Phase 11: UX Polish

#### 11a: Collapsible Reasoning Blocks
Long `<thinking>` or reasoning sections should be collapsed by default for better readability.

**Current behavior:** Full reasoning text shown inline, can be overwhelming
**Proposed:** Show first 3-5 lines with "[+N more lines]" expander

```
╭─ Thinking ────────────────────────────────────────────────────╮
│  Let me analyze this problem step by step...                  │
│  First, I need to consider the constraints...                 │
│  The key insight here is that...                              │
│                                        [+47 more lines]       │
╰───────────────────────────────────────────────────────────────╯
```

**Implementation:** `content_sections.py` - reasoning block rendering

#### 11b: Scroll Indicators
Show visual cues when content is scrollable in the main content area.

**Proposed:** Subtle `▲` at top / `▼` at bottom when more content exists

```
                              ▲
╭───────────────────────────────────────────────────────────────╮
│  [visible content area]                                       │
│                                                               │
╰───────────────────────────────────────────────────────────────╯
                              ▼
```

**Implementation:** Check Textual's ScrollableContainer for scroll position events

## Impact
- **Affected specs**: tui (new capability spec)
- **Affected code**:
  - `massgen/frontend/displays/textual_widgets/mode_bar.py`
  - `massgen/frontend/displays/textual_widgets/multi_line_input.py`
  - `massgen/frontend/displays/textual_widgets/tab_bar.py`
  - `massgen/frontend/displays/textual_widgets/tool_card.py`
  - `massgen/frontend/displays/textual_widgets/content_sections.py`
  - `massgen/frontend/displays/textual_widgets/tool_detail_modal.py`
  - `massgen/frontend/displays/textual_widgets/task_plan_modal.py`
  - `massgen/frontend/displays/textual_widgets/subagent_modal.py`
  - `massgen/frontend/displays/textual_widgets/background_tasks_modal.py`
  - `massgen/frontend/displays/textual_widgets/plan_approval_modal.py`
  - `massgen/frontend/displays/textual_terminal_display.py`
  - `massgen/frontend/displays/textual/*.py` (all modal files)
  - `massgen/frontend/displays/textual_themes/dark.tcss`
  - `massgen/frontend/displays/textual_themes/light.tcss`

## Visual Preview

### Input Bar (New Design)
```
╭─────────────────────────────────────────────────────────────────────────────────╮
│  ◉ Normal    ○ Multi-Agent    ◉ Refine                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  What would you like to explore?                                                │
│                                                                                 │
╰───────────────────────────────────────────────────────────────────── ⌘⏎ Send ──╯
```

### Agent Tabs (New Design)
```
     ◉ agent_a                  ○ agent_b
     Gemini                     GPT-5.2
```

### Tool Card Collapsed (New Design)
```
┌ wrote file ─────────────────────────────────────────────── 0.0s ✓ ┐
│ tasks/evolving_skill/SKILL.md                                     │
└───────────────────────────────────────────────────────────────────┘
```

### Modal (New Design)
```
╭─ Tool Details ───────────────────────────────────────────────── ✕ ─╮
│                                                                    │
│  filesystem • write_file                              0.3s    ✓    │
│                                                                    │
│  ─────────────────────────────────────────────────────────────     │
│                                                                    │
│  Parameters                                                        │
│  path: /tasks/evolving_skill/SKILL.md                              │
│  content: # Skill Definition...                                    │
│                                                                    │
│  ─────────────────────────────────────────────────────────────     │
│                                                                    │
│  Result                                                            │
│  File written successfully (2.4 KB)                                │
│                                                                    │
╰────────────────────────────────────────────────────────── Close ───╯
```

### Diff View for File Edits (New Feature)
```
╭─ Edit: src/utils/parser.py ─────────────────────────── +12 -3 ─╮
│                                                                │
│   42 │   def parse_config(self, path: str):                    │
│   43 │       """Parse configuration file."""                   │
│   44 │-      config = {}                                       │  (red)
│   45 │+      config: Dict[str, Any] = {}                       │  (green)
│   46 │+      validator = ConfigValidator()                     │  (green)
│   47 │                                                         │
│   48 │       with open(path) as f:                             │
│   49 │-          data = f.read()                               │  (red)
│   50 │+          data = f.read()                               │  (green)
│   51 │+          if not validator.validate(data):              │  (green)
│   52 │+              raise ValueError("Invalid config")        │  (green)
│                                                                │
╰────────────────────────────────────────────────────────────────╯
```

### Workspace Modal - Tree View (New Design)
```
╭─ Workspace: session_abc123 ─────────────── 8 files • +156 -42 ─╮
│                                                                │
│  📁 session_abc123/                                            │
│  ├── 📄 execution_metadata.yaml                                │
│  ├── 📁 agent_a/                                               │
│  │   ├── 📄 turn_1_answer.md                      +45 -0       │
│  │   ├── 📄 turn_2_answer.md                      +38 -12      │
│  │   └── 📄 final_answer.md                       +22 -8       │
│  ├── 📁 agent_b/                                               │
│  │   ├── 📄 turn_1_answer.md                      +32 -0       │
│  │   └── 📄 turn_2_answer.md                      +19 -22      │
│  └── 📄 consensus_result.md                                    │
│                                                                │
│  ─────────────────────────────────────────────────────────     │
│  Summary: 2 agents • 3 turns • consensus reached               │
│                                                                │
╰────────────────────────────────────────────────────── Close ───╯
```

---

## Implementation Workflow

**IMPORTANT**: After completing each phase, stop and ask the user to run the TUI for visual approval before proceeding to the next phase. This ensures incremental validation and prevents compounding issues.

```
Phase N complete → User runs TUI → User approves → Proceed to Phase N+1
                                 → User requests changes → Iterate → Re-approve
```

---

## Phase 8: Professional Visual Polish (NEW)

### Phase 8a: Animation & Feedback Philosophy

**Core principle: "Calm presence with purposeful signals"**

The UI should feel like a professional assistant working quietly—attentive but not distracting. Animation serves information, not decoration.

```
DEFAULT STATE:  Everything is still, clean, readable
ACTIVE STATE:   One thing pulses/moves to show "I'm working"
TRANSITION:     Quick and smooth (150-200ms), never slow
COMPLETION:     Settles back to calm
```

**Key rule**: Only one element should be animated at a time. Motion draws the eye, so motion = "look here."

#### Animation Specifications

| Moment | Animation | Duration | Purpose |
|--------|-----------|----------|---------|
| **Waiting for response** | Pulsing `◉` in tab (opacity 0.5↔1.0) + "Thinking..." text | 800ms cycle | Confirms system received input |
| **Streaming text** | Blinking cursor `▌` at end of text | 530ms cycle | Shows "still generating" vs "done" |
| **Tool running** | Time ticking `0.1s → 0.2s → 0.3s` + spinner `⟳` | Real-time | Shows progress, not frozen |
| **Tool completes** | Result fades in | 150ms | Smooth appearance, not jarring |
| **Phase changes** | Brief highlight pulse on new phase indicator | 300ms | Marks milestone |
| **Round complete** | Separator fades in, summary appears below | 200ms | Moment to breathe |
| **Errors** | Red color change + toast notification | 3s auto-dismiss | Attention without blocking |
| **Token/cost updates** | No animation (silent in-place update) | — | Background info |
| **Modal open/close** | Opacity fade | 150ms | Professional, smooth |
| **Tab switch** | Ribbon updates immediately | Instant | Responsive feel |

#### Streaming Cursor Behavior
```
While streaming:  "The answer is▌"        (cursor visible, blinking)
When complete:    "The answer is 42."     (cursor disappears)
```

#### Pulsing Dot States
```
◉ (bright)  →  ◉ (dim)  →  ◉ (bright)    Active/streaming (800ms cycle)
◉ (static bright)                         Idle but selected
○ (static dim)                            Inactive/waiting
```

#### Tool Card Lifecycle
```
1. Card appears:     ╭─ filesystem/write_file ─────── ⟳ 0.0s ─╮
2. Time ticks:       ╭─ filesystem/write_file ─────── ⟳ 0.3s ─╮
3. Completes:        ╭─ filesystem/write_file ─────── 0.3s ✓ ─╮  (fade in result)
```

---

### Phase 8b: Professional Color Palette
Current colors feel dated. Replace with a modern, harmonious palette inspired by Claude.ai, Linear, and Warp:

**Background Layers (Dark Theme):**
```
bg-base:      #0D1117  (deep blue-black, main background)
bg-surface:   #161B22  (elevated surfaces like agent panels)
bg-card:      #21262D  (cards, modals, tool results)
bg-elevated:  #30363D  (hover states, selected items)
```

**Border Colors:**
```
border-subtle:  #30363D  (most borders - softer than current)
border-default: #484F58  (emphasized borders)
border-focus:   #58A6FF  (focus rings, active states)
```

**Text Hierarchy:**
```
text-primary:   #E6EDF3  (main content, readable)
text-secondary: #8B949E  (labels, hints, subtitles)
text-muted:     #6E7681  (disabled, very subtle)
```

**Semantic Accents:**
```
accent-blue:    #58A6FF  (primary actions, links)
accent-green:   #3FB950  (success, completed)
accent-yellow:  #D29922  (warnings, in-progress)
accent-red:     #F85149  (errors, canceled)
accent-purple:  #A371F7  (AI/special indicators)
```

### Phase 8c: Agent Status Ribbon
A new component below the tab bar showing real-time status for the selected agent:
```
╭──────────────────────────────────────────────────────────────────────────╮
│ Round 2 ▾ │ ◉ Streaming... 12s │ ⏱ 5:30 │ Tasks: 3/7 ━━░░ │ 2.4k │ $0.003 │
╰──────────────────────────────────────────────────────────────────────────╯
         │
         ▼ (dropdown on click)
    ┌─────────────────────────┐
    │ ◉ Round 2 (current)     │
    │ ↻ Round 1 • ctx reset   │
    │   Round 0 • initial     │
    └─────────────────────────┘
```

Features:
- **Round navigation dropdown** (first element):
  - `◉ Round N (current)` - live streaming round
  - `↻ Round N • ctx reset` - rounds where context was reset
  - `Round 0 • initial` - first round (no reset indicator)
  - Clicking a round switches content view to that round's history
  - Shows "↻ Context was reset for this round" header when viewing historical reset rounds
- **Activity indicator**: ◉ Streaming, ○ Idle, ⏳ Thinking, ⏹ Canceled, ✗ Error
- **Elapsed time**: How long current activity has been running
- **Round timeout display**: Shows tiered timeouts from config:
  - Soft timeout countdown (from `initial_round_timeout_seconds` or `subsequent_round_timeout_seconds`)
  - Grace period when soft expires (from `round_timeout_grace_seconds`)
  - Color coding: normal (muted), warning (<30s, yellow), grace (orange), critical (<30s total, red)
- **Tasks progress**: Compact "X/Y" with mini progress bar (clickable → opens task modal)
- **Token count**: Running total for this agent
- **Cost estimate**: Running total for this agent

Interaction:
- Clicking the Round dropdown shows available rounds with context reset indicators
- Clicking the Tasks segment opens the full Task Plan Modal with detailed list
- Ribbon updates automatically when switching agent tabs
- Model name is shown in the tab itself (two-line display), not duplicated here

### Phase 8d: Phase Indicator Bar
Show coordination flow progress (for multi-agent mode):
```
┌───────────────────────────────────────────────────────────────────────┐
│   ○ Initial Answer  →  ● Voting  →  ○ Consensus  →  ○ Presentation   │
└───────────────────────────────────────────────────────────────────────┘
```
- Current phase highlighted with ● and accent color
- Completed phases show ✓
- Helps users understand where they are in the flow

### Phase 8e: Session Info Panel (Header Area)
Utilize empty space in top-left with session summary:
```
┌─ Session ──────────────────────────────────────────────────────────────┐
│  Turn 2 of 5  •  1m 23s elapsed  •  ~$0.02 cost  •  12.4k tokens used │
└────────────────────────────────────────────────────────────────────────┘
```

### Phase 8f: Round Separators (SIMPLIFIED)
**Note:** Primary round navigation now handled by dropdown in Status Ribbon (Phase 8c).
Round separators are optional subtle visual breaks, not primary navigation.

Options:
1. **Remove entirely** - round switching via dropdown is sufficient
2. **Minimal visual break** - subtle dashed line without prominent text:
```
┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
```

The old banner-style separators ("Round 1 Complete") are no longer needed since users can navigate rounds via the dropdown.

### Phase 8g: Final Answer Card Redesign

**Current problems (to fix):**
- 🏆 Trophy emoji - inconsistent with emoji-free direction
- `#ffd700` gold header - harsh, dated
- "FINAL ANSWER" in ALL CAPS - shouty
- "Winner: A1.1 (2v) | Votes: A1.1(2)" - cryptic, hard to parse
- Thick gold border - too heavy
- "✓ Complete" progress bar at bottom - redundant

**Proposed redesign:**
```
╭─ Final Answer ───────────────────────────────────────────────╮
│                                                              │
│  The music of the heart is heard,                            │
│  A tapestry of joy and care...                               │
│                                                              │
│  ─────────────────────────────────────────────────────────── │
│  ✓ Consensus • 2 agents agreed • 1 round • $0.02             │
╰──────────────────────────────────────────────────────────────╯
```

**Changes needed in `content_sections.py`:**
- `_build_title()`: Change from "🏆 FINAL ANSWER" to "Final Answer"
- `_build_vote_summary()`: Change from "Winner: A1.1 (2v) | Votes: A1.1(2)" to "2 agents agreed • 1 round"
- `complete()`: Change "✅ FINAL ANSWER" to "✓ Final Answer"
- `set_post_eval_status()`: Remove emojis from status messages
- CSS: Replace gold (#ffd700) with muted green
- CSS: Use rounded corners (border: round)
- Remove redundant "✓ Complete" progress indicator
- Add summary footer inside card instead of external progress bar

**Post-eval states (cleaned up):**
```
◉ Evaluating...           (pulsing indicator)
✓ Verified                [▸ Show Details]
↻ Restart Requested       [▸ Show Details]
```

Features:
- Title case "Final Answer" (not ALL CAPS)
- Clean summary footer with session stats
- Rounded corners, softer muted green borders
- Human-readable vote summary
- Proper whitespace

### Phase 8h: Enhanced Tab Design with Model Names
```
   ╭────────────────╮    ┌────────────────┐
   │  ◉ agent_a     │    │  ○ agent_b     │
   │  claude-haiku  │    │  gpt-5.2       │
   ╰────────────────╯    └────────────────┘
   ════════════════
```

- Two-line display: agent name (bold) + model name (muted)
- Rounded corners for selected tab
- Underline indicator below selected
- Status indicators with state-specific colors:
  - `◉` Streaming/Active (blue pulse)
  - `○` Idle/Waiting (muted)
  - `✓` Done (green)
  - `⏹` Canceled (yellow)
  - `✗` Error (red)

### Phase 8i: Visual Depth Through Layering
Establish visual hierarchy through background layering:
```
╭─────────────────────────────────────────╮  ← bg-card
│  ▌ Main content with left accent        │  ← left border accent
│                                         │
│  ┌─ Nested section ──────────────────┐  │  ← bg-elevated (inset)
│  │  Secondary content area           │  │
│  └───────────────────────────────────┘  │
╰─────────────────────────────────────────╯
```

- Cards sit on surfaces
- Nested content uses slightly different background
- Focus states add subtle glow/ring

### Phase 8j: Improved Task Modal (click from ribbon)
When user clicks "Tasks: 3/7" in the status ribbon, show enhanced modal:
```
╭─ Tasks ──────────────────────────────────────── 3/7 ━━━━━━━░░░░ ─╮
│                                                                  │
│  ✓ Create SKILL.md with workflow plan                           │
│  ✓ Check long-term memories for relevant context                │
│  ● Brainstorm and draft a poem about love  ← current            │
│  ○ Refine the poem for better flow and imagery                  │
│  ○ Finalize and save to deliverable/ directory                  │
│  ○ Update SKILL.md with learnings from this session             │
│  ○ Document decisions to optimize future work                   │
│                                                                  │
╰──────────────────────────────────────────────────────── Close ───╯
```

Features:
- Progress bar integrated into modal header
- Fraction display (3/7) with visual progress bar
- Clear current task marker with `← current`
- Full task names (not truncated like ribbon)
- Rounded corners, consistent modal styling
- Close button or click-outside to dismiss

### Visual Preview: Full Session View (New Design)
```
╭─ Session ────────────────────────────────────────────────────────────────╮
│  Turn 2 of 5  •  1m 23s  •  ~$0.02  •  12.4k tokens                     │
╰──────────────────────────────────────────────────────────────────────────╯

┌───────────────────────────────────────────────────────────────────────────┐
│   ✓ Initial  →  ● Voting  →  ○ Consensus  →  ○ Presentation              │
└───────────────────────────────────────────────────────────────────────────┘

   ╭────────────────╮    ┌────────────────┐
   │  ◉ agent_a     │    │  ○ agent_b     │
   │  claude-haiku  │    │  gpt-5.2       │
   ╰────────────────╯    └────────────────┘
   ════════════════

╭──────────────────────────────────────────────────────────────────────────╮
│ ◉ Streaming... 12s │ Tasks: 3/7 ━━░░ │ 2.4k tokens │ $0.003            │
╰──────────────────────────────────────────────────────────────────────────╯

╭─ agent_a ────────────────────────────────────────────────────────────────╮
│                                                                          │
│  **Analyzing the problem...**                                            │
│                                                                          │
│  ╭─ filesystem/write_file ─────────────────────────────── 0.3s ✓ ─╮     │
│  │  tasks/evolving_skill/SKILL.md                                 │     │
│  ╰────────────────────────────────────────────────────────────────╯     │
│                                                                          │
╰──────────────────────────────────────────────────────────────────────────╯

╭──────────────────────────────────────────────────────────────────────────╮
│  ◉ Normal    ○ Multi-Agent    ◉ Refine                                  │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  What would you like to explore?                                         │
│                                                                          │
╰──────────────────────────────────────────────────────────────── ⏎ Send ──╯
```

---

## Phase 12: View-Based Round & Final Answer Navigation

**This phase supersedes Phase 8f (Round Separators) and Phase 8g (Final Answer Card).**

### Problem with Current Approach

The current TUI shows all rounds inline with separators, and embeds the Final Answer as a card within the content flow. This creates:
- Cluttered, long-scrolling content areas
- No easy way to jump between rounds
- Final Answer gets lost in the content stream
- Poor UX when sessions have many rounds

### New Paradigm: Views Instead of Inline Content

The agent panel becomes a **view container** that shows ONE view at a time:
- **Round views**: Show content for a specific round only
- **Final Answer view**: Dedicated clean presentation screen

Navigation happens via a dropdown in the Status Ribbon.

### 12a: View Dropdown in Status Ribbon

Update the Status Ribbon's round selector to become a full view selector:

```
┌─ Status Ribbon ───────────────────────────────────────────────┐
│ [Round 2 ▾] │ ◉ Streaming... 12s │ Tasks: 3/7 │ 2.4k │ $0.003 │
└───────────────────────────────────────────────────────────────┘
        │
        ▼ (dropdown on click)
   ┌─────────────────────────────┐
   │ ✓ Final Answer              │  ← Only shown when consensus reached
   │ ─────────────────────────── │
   │ ◉ Round 2 (current)         │  ← Currently streaming/active
   │   Round 1                   │  ← Historical round
   │   Round 0 • initial         │  ← First round
   └─────────────────────────────┘
```

**Dropdown items:**
- `✓ Final Answer` - Only appears after consensus, at top with separator
- `◉ Round N (current)` - The live/active round (pulsing indicator)
- `Round N` - Historical rounds (plain text)
- `↻` prefix for rounds that had context reset

### 12b: Round View Content

When a round is selected, the agent panel shows ONLY that round's content:

```
┌─ Agent Panel (Round 2 selected) ──────────────────────────────┐
│                                                               │
│  [Thinking block for round 2...]                              │
│                                                               │
│  ╭─ filesystem/write_file ──────────────────── 0.3s ✓ ─╮     │
│  │  tasks/poem.md                                      │     │
│  ╰─────────────────────────────────────────────────────╯     │
│                                                               │
│  Here's the poem I created...                                 │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

**Key changes:**
- No RestartBanner separators (removed entirely)
- No FinalPresentationCard inline
- Clean, focused view of single round
- Content stored per-round: `agent_content[agent_id][round_num]`

### 12c: Final Answer View (Dedicated Screen)

When "Final Answer" is selected from dropdown, show a dedicated presentation:

```
┌─ Status Ribbon ───────────────────────────────────────────────┐
│ [✓ Final Answer ▾] │ Complete │ 2 agents • 1 round │ $0.02   │
└───────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                                                                 │
│                        Final Answer                             │
│                                                                 │
│   ─────────────────────────────────────────────────────────     │
│                                                                 │
│   The music of the heart is heard,                              │
│   A tapestry of joy and care,                                   │
│   Where love's sweet melody is stirred,                         │
│   And hope floats gently through the air.                       │
│                                                                 │
│   A garden tended, soft and slow,                               │
│   Where seeds of trust begin to grow,                           │
│   Love is the bridge, the open door,                            │
│   The peace we find, and so much more.                          │
│                                                                 │
│   ─────────────────────────────────────────────────────────     │
│                                                                 │
│   ✓ Consensus reached                                           │
│   Presented by agent_a (claude-haiku)                           │
│   2 agents agreed • 1 round • verified by post-evaluation       │
│                                                                 │
│                                                                 │
│   ┌──────────┐  ┌────────────────┐  ┌──────────────────────┐   │
│   │  📋 Copy │  │  📂 Workspace  │  │  📊 Voting Details   │   │
│   └──────────┘  └────────────────┘  └──────────────────────┘   │
│                                                                 │
│   💬 Type below to continue the conversation                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Design principles:**
- Generous whitespace - let the answer breathe
- Centered title, clean typography
- Metadata footer with key stats
- Action buttons at bottom
- No cramped inline card styling

### 12d: Auto-Navigation

When consensus is reached:
1. Final Answer view is added to dropdown
2. **Auto-switch to Final Answer view** for the presenting agent's tab
3. User can navigate back to any round via dropdown
4. Other agent tabs stay on their current round view

### 12e: Implementation Changes

**Files to modify:**

| File | Changes |
|------|---------|
| `textual_terminal_display.py` | Add view state management, round content storage |
| `agent_status_ribbon.py` | Convert round selector to view dropdown with Final Answer option |
| `content_sections.py` | Remove `RestartBanner`, remove inline `FinalPresentationCard` |
| `tab_bar.py` | No changes (tabs switch agents, not views) |
| **NEW** `final_answer_view.py` | Dedicated Final Answer screen component |

**Data structures:**
```python
# Per-agent content storage
self._agent_views = {
    "agent_a": {
        "rounds": {
            0: [content_widgets...],  # Round 0 content
            1: [content_widgets...],  # Round 1 content
            2: [content_widgets...],  # Round 2 content (current)
        },
        "final_answer": FinalAnswerData | None,
        "current_view": "round:2" | "final_answer",
    }
}
```

**View switching logic:**
```python
def switch_view(self, agent_id: str, view: str):
    """Switch agent panel to show specific view.

    Args:
        agent_id: The agent
        view: "round:N" or "final_answer"
    """
    # Clear current content
    # Load content for selected view
    # Update ribbon to show selected view
```

### 12f: Deprecations

The following are **removed** by this phase:
- `RestartBanner` widget - no longer needed
- Inline `FinalPresentationCard` - replaced by dedicated view
- Round separator styling in CSS

### Visual Summary

**Before (Inline):**
```
┌─────────────────────────────────┐
│ Round 1 content                 │
│ ┄┄┄ Round 1 Complete ┄┄┄        │
│ Round 2 content                 │
│ ╭─ Final Answer ────────────╮   │
│ │ [crammed inline]          │   │
│ ╰───────────────────────────╯   │
└─────────────────────────────────┘
```

**After (View-Based):**
```
┌─ [Round 2 ▾] ───────────────────┐
│                                 │
│ [Only Round 2 content]          │
│ [Clean, focused]                │
│                                 │
└─────────────────────────────────┘

   OR (when Final Answer selected)

┌─ [✓ Final Answer ▾] ────────────┐
│                                 │
│        Final Answer             │
│                                 │
│   [Beautiful, spacious]         │
│                                 │
│   [Copy] [Workspace] [Details]  │
└─────────────────────────────────┘
```

---

## Phase 13: Backend Integration

### 13.2 Execution Status Line (Multi-Agent Aware)

A status line above the mode bar showing activity across ALL agents - so you can see what B and C are doing even when focused on agent A's tab.

**Option 1c - Two-Line Status (DEFAULT):**
```
┌─────────────────────────────────────────────────────────────────────┐
│  [Agent content area]                                               │
└─────────────────────────────────────────────────────────────────────┘

  ◉ agent_a thinking...                                     R2 • 45s • $0.02
  B: ✓ done  C: ◉ write_file

╭─────────────────────────────────────────────────────────────────────╮
│  ◉ Normal    ○ Multi-Agent    ◉ Refine                              │
```

- Top line: focused agent's detailed status + session stats (round, time, cost)
- Bottom line: other agents' compact status
- When switching tabs, the lines swap appropriately

**Option 1b - All Agents Inline (Alternative):**
```
  A: ◉ thinking    B: ✓ done    C: ◉ write_file (0.3s)
```

All agents equal weight, scan left-to-right. More compact, single line.

**Option 1a - Current Focus + Agent Pills (Alternative):**
```
  ◉ agent_a is thinking...                    [B ✓] [C ◉]
```

Primary action prominent, others as minimal pills on the right.

**Status Indicators:**
| Indicator | Meaning |
|-----------|---------|
| `◉` | Streaming/thinking (pulsing animation) |
| `✓` | Done/ready |
| `○` | Waiting/idle |
| `tool_name` | Executing tool (e.g., `write_file`, `read_file`) |
| `voted X` | Voted for answer X (e.g., `voted A1.2`) |

**Implementation:** Start with 1c, test in real sessions, adjust based on feedback.
