# TUI Redesign Phase 9+11 Handoff: Edge-to-Edge Layout & UX Polish

## Overview

This phase combines Phase 9 (Remove Outer Container Border) and Phase 11 (UX Polish) for a cleaner, more polished interface.

---

## Phase 9: Remove Outer Container Border

### Goal
Remove the outer border/frame from the main app container so content flows edge-to-edge.

### Current State
The TUI may have a visible border around the entire app container, creating a "boxed" appearance.

### Implementation

#### 9.1.1-9.1.3 Remove Container Border
Location: `massgen/frontend/displays/textual_themes/dark.tcss`

Look for Screen or top-level container styles:
```tcss
/* Remove any border from main container */
Screen {
    border: none;
}

#main_container {
    border: none;
}
```

#### 9.1.4 Test Focus Rings and Modals
Ensure keyboard focus rings and modal overlays still work correctly without the outer border.

### Verification
```bash
uv run massgen --display textual --config massgen/configs/basic/multi/two_agents.yaml "Hello"
```
- Content should flow edge-to-edge
- No visible outer frame around the app
- Modals still appear correctly centered

---

## Phase 11: UX Polish

### 11.1 Collapsible Reasoning Blocks

#### Goal
Long `<thinking>` or reasoning sections should be collapsed by default to improve readability.

#### Design
```
▸ Thinking (47 lines)                           [click to expand]
│ First few lines of reasoning visible here...
│ More reasoning text...
│ [+44 more lines]
```

When expanded:
```
▾ Thinking (47 lines)                           [click to collapse]
│ Full reasoning content...
│ ...all lines visible...
```

#### Implementation

##### 11.1.1 Detect Reasoning Blocks
Location: `massgen/frontend/displays/textual_widgets/content_sections.py`

The `ThinkingSection` widget already exists. Modify to support collapse:

```python
class ThinkingSection(Widget):
    """Collapsible thinking/reasoning block."""

    DEFAULT_COLLAPSED_LINES = 5

    def __init__(self, content: str, ...):
        self._content = content
        self._collapsed = True  # Default collapsed
        self._lines = content.split('\n')

    def render(self) -> Text:
        if self._collapsed and len(self._lines) > self.DEFAULT_COLLAPSED_LINES:
            # Show first N lines + expander
            visible = '\n'.join(self._lines[:self.DEFAULT_COLLAPSED_LINES])
            remaining = len(self._lines) - self.DEFAULT_COLLAPSED_LINES
            return Text(f"▸ Thinking ({len(self._lines)} lines)\n{visible}\n[+{remaining} more lines]")
        else:
            return Text(f"▾ Thinking ({len(self._lines)} lines)\n{self._content}")

    async def on_click(self):
        self._collapsed = not self._collapsed
        self.refresh()
```

##### 11.1.2-11.1.4 Truncation and Expansion
- Show first 3-5 lines by default
- Add clickable "[+N more lines]" expander
- Toggle on click

##### 11.1.5 Remember State
Store expansion state in widget instance (resets on new session).

### 11.2 Scroll Indicators

#### Goal
Show visual cues (▲/▼) when content is scrollable.

#### Design
```
                                                              ▲
┌─────────────────────────────────────────────────────────────┐
│ Content here...                                             │
│ More content...                                             │
│ Even more content...                                        │
└─────────────────────────────────────────────────────────────┘
                                                              ▼
```

#### Implementation

##### 11.2.1 Track Scroll Position
Location: `massgen/frontend/displays/textual_terminal_display.py`

Hook into ScrollableContainer scroll events:

```python
def on_scroll(self, event: Scroll) -> None:
    """Update scroll indicators based on position."""
    container = event.sender

    # Check if content above viewport
    has_content_above = container.scroll_y > 0

    # Check if content below viewport
    has_content_below = container.scroll_y < container.max_scroll_y

    self._update_scroll_indicators(has_content_above, has_content_below)
```

##### 11.2.2-11.2.3 Show Indicators
Add subtle indicators at top/bottom edges:

```python
def _update_scroll_indicators(self, above: bool, below: bool):
    if self._scroll_up_indicator:
        self._scroll_up_indicator.display = above
    if self._scroll_down_indicator:
        self._scroll_down_indicator.display = below
```

##### 11.2.4 Subtle Styling
```tcss
.scroll-indicator {
    color: $fg-subtle;
    text-align: center;
    height: 1;
}

.scroll-indicator-up {
    dock: top;
}

.scroll-indicator-down {
    dock: bottom;
}
```

##### 11.2.5 Hide at Boundaries
Indicators auto-hide when at scroll boundaries (handled by display toggle).

---

## Files to Modify

| File | Changes |
|------|---------|
| `dark.tcss` | Remove container border, add scroll indicator styles |
| `light.tcss` | Same as dark.tcss |
| `content_sections.py` | Make ThinkingSection collapsible |
| `textual_terminal_display.py` | Add scroll indicators to agent panels |

---

## Testing Commands

```bash
# Test edge-to-edge layout
uv run massgen --display textual --config massgen/configs/basic/multi/two_agents.yaml "Hello"

# Test with long thinking content (for collapsible blocks)
uv run massgen --display textual --config massgen/configs/basic/single/sonnet.yaml "Explain quantum computing in detail"

# Test scroll indicators (generate lots of content)
uv run massgen --display textual --config massgen/configs/tools/mcp/filesystem_demo.yaml "List all files recursively"
```

---

## Estimated Complexity

| Task | Complexity | Notes |
|------|------------|-------|
| 9.1 Remove container border | Low | CSS only |
| 11.1 Collapsible reasoning | Medium | Widget modification, click handling |
| 11.2 Scroll indicators | Medium | Scroll event handling, indicator widgets |

---

# TUI Redesign Phase 13 Handoff: Backend Integration for Status Ribbon

## Overview

Phase 13 focuses on wiring backend data to the TUI status elements and adding a multi-agent aware execution status line.

## Current State (Post Phase 8)

### Layout (top to bottom)
1. **Tab Bar** - Agent tabs (left) + Session info (right: `◈ Turn 1` + truncated question)
2. **Status Ribbon** - `Round 1 ▾ │ ⏱ --:-- │ - │ $--.---` (placeholders)
3. **Content Area** - Agent panels with timeline
4. **Execution Bar** - Shows during coordination (cancel button)
5. **Mode Bar + Input** - Plan/Agent/Refine toggles + input field
6. **Status Bar** - Bottom status (elapsed time, phase)

### Key Files
- `massgen/frontend/displays/textual_terminal_display.py` - Main TUI app
- `massgen/frontend/displays/textual_widgets/agent_status_ribbon.py` - Status ribbon widget
- `massgen/frontend/displays/textual_widgets/tab_bar.py` - Tab bar with session info

### What's Working
- Tab bar shows Turn and Question (clickable for full prompt modal)
- Status ribbon displays with Round selector
- Timeout placeholder shows `⏱ --:--`
- Token placeholder shows `-`
- Cost placeholder shows `$--.---`

### What's NOT Wired
- Token count not updating during streaming
- Cost not calculating from token usage
- Timeout not counting down
- No multi-agent status visibility when focused on one agent

---

## Phase 13.1: Token/Cost Backend Wiring

### Goal
Wire real token counts and cost estimates from the backend to the status ribbon.

### Implementation Steps

#### 13.1.1 Token Tracking in ChatAgent
Location: `massgen/chat_agent.py`

The agent already receives token usage from backends. Need to:
1. Accumulate `input_tokens` and `output_tokens` per turn
2. Expose via callback or property for TUI consumption

```python
# In ChatAgent, track cumulative tokens
self._total_input_tokens = 0
self._total_output_tokens = 0

# After each API call, accumulate
self._total_input_tokens += response.usage.input_tokens
self._total_output_tokens += response.usage.output_tokens
```

#### 13.1.2 Cost Calculation
Location: `massgen/token_manager/token_manager.py`

Use existing `TokenManager.get_cost()` method:
```python
from massgen.token_manager import TokenManager
cost = TokenManager.get_cost(model_name, input_tokens, output_tokens)
```

#### 13.1.3 Pass to TUI Display
Location: `massgen/frontend/displays/textual_terminal_display.py`

Add callback or update method:
```python
def update_agent_tokens(self, agent_id: str, input_tokens: int, output_tokens: int, cost: float):
    """Update token/cost display for an agent."""
    if self._app:
        self._call_app_method("_update_ribbon_tokens", agent_id, input_tokens + output_tokens, cost)
```

#### 13.1.4 Wire to AgentStatusRibbon
Location: `massgen/frontend/displays/textual_widgets/agent_status_ribbon.py`

Methods already exist:
- `set_tokens(tokens: int)` - Updates token display
- `set_cost(cost: float)` - Updates cost display

Just need to call them from the app when data arrives.

#### 13.1.5 Real-time Updates
Update during streaming, not just at end of response:
- Hook into `notify_agent_content()` or streaming callbacks
- Debounce updates to avoid excessive refreshes (every 500ms or on token threshold)

### Verification
```bash
uv run massgen --display textual --config massgen/configs/basic/multi/two_agents.yaml "What is 2+2?"
```
- Token count should increase during streaming
- Cost should update in real-time
- Switching agents should show their respective token/cost

---

## Phase 13.2: Execution Status Line

### Goal
Add a status line above the mode bar showing activity across ALL agents, not just the focused one.

### Design (Option 1c - Two-Line Status)
```
  ◉ agent_a thinking...                                     R2 • 45s • $0.02
  B: ✓ done  C: ◉ write_file
```

- **Top line**: Focused agent's detailed status + round/time/cost
- **Bottom line**: Other agents' compact status (letter: indicator action)

### Implementation Steps

#### 13.2.1 Create ExecutionStatusLine Widget
Location: `massgen/frontend/displays/textual_widgets/execution_status_line.py` (new)

```python
class ExecutionStatusLine(Widget):
    """Multi-agent aware status line showing activity across all agents."""

    DEFAULT_CSS = """
    ExecutionStatusLine {
        width: 100%;
        height: 2;
        background: $bg-surface;
        padding: 0 1;
    }
    """

    def __init__(self, agent_ids: List[str]):
        self._agent_ids = agent_ids
        self._agent_status: Dict[str, AgentStatus] = {}
        self._focused_agent: str = agent_ids[0] if agent_ids else ""

    def set_agent_status(self, agent_id: str, status: str, detail: str = ""):
        """Update status for an agent."""
        self._agent_status[agent_id] = AgentStatus(status, detail)
        self._update_display()

    def set_focused_agent(self, agent_id: str):
        """Change which agent is on the top line."""
        self._focused_agent = agent_id
        self._update_display()
```

#### 13.2.2 Position in Layout
In `textual_terminal_display.py` compose():
```python
# Position above mode bar, below agent panels
self._execution_status = ExecutionStatusLine(agent_ids, id="execution_status_line")
yield self._execution_status
```

#### 13.2.3 Status Types
```python
STATUS_INDICATORS = {
    "streaming": "◉",      # Blue, with elapsed time
    "thinking": "◉",       # Blue
    "tool": "◉",           # Blue, show tool name
    "done": "✓",           # Green
    "waiting": "○",        # Muted
    "voted": "✓",          # Green, show vote target
    "error": "✗",          # Red
}
```

#### 13.2.4 Wire to Orchestrator Events
Hook into existing callbacks:
- `update_agent_status()` - Agent state changes
- `notify_tool_start()` / `notify_tool_end()` - Tool execution
- `notify_vote()` - Voting
- `notify_phase()` - Phase changes

#### 13.2.5 Tab Switch Handling
When user switches tabs via `on_agent_tab_changed`:
```python
def on_agent_tab_changed(self, event: AgentTabChanged):
    # ... existing code ...
    if self._execution_status:
        self._execution_status.set_focused_agent(event.agent_id)
```

### CSS Styling
```tcss
ExecutionStatusLine {
    width: 100%;
    height: 2;
    background: $bg-surface;
    border-top: solid $border-default;
    padding: 0 1;
}

ExecutionStatusLine .top-line {
    color: $fg-primary;
}

ExecutionStatusLine .bottom-line {
    color: $fg-muted;
}
```

### Verification
```bash
uv run massgen --display textual --config massgen/configs/basic/multi/three_agents.yaml "Write a haiku"
```
- Top line shows focused agent's detailed status
- Bottom line shows other agents' compact status
- Switching tabs updates which agent is on top vs bottom
- Tool executions show tool name
- Votes show vote target

---

## Files to Modify

| File | Changes |
|------|---------|
| `chat_agent.py` | Add token accumulation |
| `textual_terminal_display.py` | Wire token/cost callbacks, add ExecutionStatusLine |
| `agent_status_ribbon.py` | Already has set_tokens/set_cost methods |
| `execution_status_line.py` | NEW - Create widget |
| `textual_widgets/__init__.py` | Export new widget |
| `dark.tcss` | Add ExecutionStatusLine styling |

---

## Testing Commands

```bash
# Basic multi-agent test
uv run massgen --display textual --config massgen/configs/basic/multi/two_agents.yaml "Hello"

# Three agents for status line visibility
uv run massgen --display textual --config massgen/configs/basic/multi/three_agents.yaml "Write a story"

# With tools to test tool status display
uv run massgen --display textual --config massgen/configs/tools/mcp/filesystem_demo.yaml "List files"
```

---

## Dependencies

- Phase 8 complete (status ribbon mounted with placeholders)
- Token tracking data available from backends
- TokenManager pricing data for cost calculation

---

## Estimated Complexity

| Task | Complexity | Notes |
|------|------------|-------|
| 13.1 Token/Cost Wiring | Medium | Backend integration, callback plumbing |
| 13.2 ExecutionStatusLine | Medium | New widget, multi-agent state tracking |

---

## Notes

- The status ribbon already has `set_tokens()` and `set_cost()` methods - just need to call them
- ExecutionStatusLine should be hidden in single-agent mode (or show simplified version)
- Consider debouncing token updates to avoid UI thrashing during fast streaming
- The bottom line of ExecutionStatusLine uses agent letter prefixes (A, B, C) for compactness
