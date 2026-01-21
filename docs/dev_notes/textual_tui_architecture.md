# Textual TUI Architecture Guide

This document provides a comprehensive overview of MassGen's Textual-based Terminal User Interface (TUI) for developers working on enhancements.

## Overview

The Textual TUI (`--display textual`) provides an interactive terminal interface for MassGen orchestration. It's built on the [Textual](https://textual.textualize.io/) framework and offers a richer experience than the Rich terminal display.

**Key File**: `massgen/frontend/displays/textual_terminal_display.py`

## Architecture

### Class Hierarchy

```
TextualTerminalDisplay (TerminalDisplay)
    │
    ├── TextualApp (textual.App)          # Main Textual application
    │   ├── WelcomeScreen (Container)     # Startup screen with logo
    │   ├── HeaderWidget (Static)         # Compact status header
    │   ├── AgentTabBar (Widget)          # Tab bar for agent switching
    │   ├── AgentPanel (ScrollableContainer)  # Per-agent content panel
    │   ├── PostEvaluationPanel           # Post-eval content
    │   └── FinalStreamPanel              # Final presentation stream
    │
    └── Nested Modal Classes
        ├── KeyboardShortcutsModal   # ? or h - shortcuts help
        ├── AgentOutputModal         # f - full agent output
        ├── CostBreakdownModal       # c - token usage/costs
        ├── MetricsModal             # m - tool metrics
        ├── VoteResultsModal         # v - vote results
        ├── OrchestratorEventsModal  # o - events
        ├── SystemStatusModal        # s - system status
        ├── MCPStatusModal           # p - MCP server status
        ├── AnswerBrowserModal       # b - browse all answers
        ├── TimelineModal            # t - coordination timeline
        ├── WorkspaceBrowserModal    # w - workspace file browser
        ├── AgentSelectorModal       # Post-answer inspection
        ├── ContextModal             # /context command
        ├── WorkspaceFilesModal      # /workspace command (list)
        ├── FileInspectionModal      # File tree + preview
        ├── BroadcastPromptModal     # Human input requests
        ├── PresentationModal
        ├── TableModal
        └── TextContentModal
```

### Key Components

#### TextualTerminalDisplay

The main display class that bridges MassGen's display interface with Textual.

```python
class TextualTerminalDisplay(TerminalDisplay):
    def __init__(self, agent_ids: List[str], **kwargs):
        # Key attributes:
        self.agent_ids          # List of agent IDs
        self.agent_models       # Dict[str, str] - agent_id -> model name
        self.theme              # "dark" or "light"
        self._app               # TextualApp instance
        self._buffers           # Dict[str, List] - per-agent content buffers
        self.agent_widgets      # Dict[str, AgentPanel] - panel widgets
```

**Important**: `TextualTerminalDisplay` runs in a separate thread. The Textual app runs in the main thread, while orchestration happens in a background thread.

#### TextualApp

The Textual `App` subclass that manages the UI.

```python
class TextualApp(App):
    def __init__(self, display, question, buffers, buffer_lock, buffer_flush_interval):
        self.coordination_display = display  # Reference to TextualTerminalDisplay
        self.question = question
        self._buffers = buffers
        self._buffer_lock = buffer_lock

        # UI state
        self._showing_welcome = True         # Welcome screen visible?
        self._active_agent_id = None         # Currently visible agent
        self._tab_bar = None                 # AgentTabBar widget
        self.agent_widgets = {}              # Dict[str, AgentPanel]
```

#### AgentTabBar & AgentTab

Custom widgets for agent switching (in `textual_widgets/tab_bar.py`).

```python
class AgentTab(Static):
    """Individual tab showing agent ID and status badge."""
    # Status badges: ⏳ waiting, ⚙️ working, 📝 streaming, ✅ completed, ❌ error

class AgentTabBar(Widget):
    """Horizontal bar containing all agent tabs."""
    # Methods: set_active(), update_agent_status(), get_next_agent(), get_previous_agent()
    # Emits: AgentTabChanged message on tab click
```

#### AgentPanel

Per-agent content panel with RichLog for streaming content.

```python
class AgentPanel(ScrollableContainer):
    def __init__(self, agent_id, display, index):
        self.agent_id = agent_id
        self.status = "waiting"
        self._content_log = None  # RichLog widget

    def add_content(self, content, content_type, style):
        """Add content to the RichLog."""

    def update_status(self, status):
        """Update agent status and styling."""
```

## Data Flow

### Content Streaming

```
Backend API Response
    │
    ▼
orchestrator.py (processes chunks)
    │
    ▼
TextualTerminalDisplay.update_agent_content()
    │
    ▼
_buffers[agent_id].append(content)  # Thread-safe buffering
    │
    ▼
_flush_buffers() (periodic, runs in app thread)
    │
    ▼
AgentPanel.add_content() → RichLog.write()
```

### Tab Switching

```
User presses Tab / clicks tab / presses number key
    │
    ▼
TextualApp.action_next_agent() / on_agent_tab_changed() / on_key()
    │
    ▼
_switch_to_agent(new_agent_id)
    │
    ├── Hide current AgentPanel (add_class("hidden"))
    ├── Show new AgentPanel (remove_class("hidden"))
    ├── Update AgentTabBar.set_active()
    └── Update _active_agent_id
```

### Welcome Screen → Main UI Transition

```
App starts with _showing_welcome = True
    │
    ▼
User types question in input box
    │
    ▼
on_input_submitted() → _dismiss_welcome()
    │
    ├── Hide WelcomeScreen (add_class("hidden"))
    ├── Show HeaderWidget (remove_class("hidden"))
    ├── Show AgentTabBar (remove_class("hidden"))
    └── Show main_container (remove_class("hidden"))
```

## Keyboard Shortcuts

The TUI supports keyboard shortcuts that work during coordination. Press `?` or `h` to see the shortcuts popup.

### Live Shortcuts (During Coordination)

| Key | Action | Method |
|-----|--------|--------|
| `?` or `h` | Show shortcuts help | `action_show_shortcuts()` |
| `f` | Full agent output | `action_open_agent_output()` |
| `c` | Cost breakdown | `action_open_cost_breakdown()` |
| `m` | Metrics | `action_open_metrics()` |
| `v` | Vote results | `action_open_vote_results()` |
| `o` | Orchestrator events | `action_open_orchestrator()` |
| `s` | System status | `action_open_system_status()` |
| `Tab` | Next agent | `action_next_agent()` |
| `Shift+Tab` | Previous agent | `action_prev_agent()` |
| `1-9` | Jump to agent N | `on_key()` handler |
| `q`/`Esc`/`Ctrl+Q` | Quit | `action_quit()` |

### Slash Commands (Type in Input)

| Command | Shortcut | Description |
|---------|----------|-------------|
| `/help` | `/h` | Full command list |
| `/output [agent]` | - | View agent output |
| `/cost` | `/c` | Cost breakdown |
| `/metrics` | `/m` | Tool metrics |
| `/events [N]` | - | Last N events |
| `/workspace` | `/w` | Workspace files |
| `/config` | - | Open config in editor |
| `/context` | - | Manage context paths |
| `/inspect` | `/i` | Agent inspection |
| `/vote` | `/v` | Vote results |
| `/vim` | - | Toggle vim editing mode |

### Adding New Shortcuts

1. Add binding to `BINDINGS` list in `TextualApp`:
   ```python
   Binding("x", "my_action", "Label")
   ```

2. Add action method with `@keyboard_action` decorator:
   ```python
   @keyboard_action
   def action_my_action(self):
       self._show_modal_async(MyModal())
   ```

3. Create modal class inheriting from `BaseModal`

## Styling (TCSS)

Themes are in `massgen/frontend/displays/textual_themes/`:
- `dark.tcss` - Dark theme (VS Code-inspired colors)
- `light.tcss` - Light theme

### Key Style Patterns

```css
/* Widget visibility */
.hidden {
    display: none;
}

/* Status-based styling */
AgentTab.status-working { border: solid #569cd6; }
AgentTab.status-streaming { border: solid #4ec9b0; }
AgentTab.status-completed { border: solid #4ec9b0; }
AgentTab.status-error { border: solid #f44747; }

/* Active state combines with status */
AgentTab.active.status-working { background: #569cd6; }
```

### Color Palette (Dark Theme)

| Purpose | Color | Usage |
|---------|-------|-------|
| Primary | `#007ACC` | Headers, active elements, buttons |
| Success | `#4ec9b0` | Completed, streaming |
| Working | `#569cd6` | In-progress states |
| Error | `#f44747` | Error states |
| Warning | `#ce9178` | Warnings, restart banner |
| Muted | `#858585` | Inactive, hints |
| Background | `#1e1e1e` | Main background |
| Surface | `#252526` | Panels, containers |

## Key Bindings

| Key | Action | Method |
|-----|--------|--------|
| `Tab` | Next agent | `action_next_agent()` |
| `Shift+Tab` | Previous agent | `action_prev_agent()` |
| `1-9` | Jump to agent N | `on_key()` |
| `q` / `Ctrl+Q` / `Escape` | Quit | `action_quit()` |
| `s` | System status modal | `action_open_system_status()` |
| `o` | Orchestrator events | `action_open_orchestrator()` |
| `v` | Vote results | `action_open_vote_results()` |

## Threading Model

```
Main Thread (Textual App)
├── UI rendering
├── Event handling
├── Buffer flushing (_flush_buffers)
└── Widget updates

Background Thread (Orchestration)
├── API calls to backends
├── Agent coordination
├── Content generation
└── Calls display.update_agent_content() → buffers
```

**Important**: All UI updates must happen on the main thread. Use `call_from_thread()` or buffer content for periodic flushing.

## Learnings from Phase 1

### What Worked Well

1. **Reusing AgentPanel**: Instead of creating a new `AgentContentPanel`, we reused the existing `AgentPanel` and just show/hide via CSS. This preserved:
   - Scroll position per agent
   - RichLog content history
   - Streaming state

2. **CSS-based visibility**: Using `.hidden { display: none; }` is simpler than managing widget lifecycle.

3. **Agent models at creation time**: Pass `agent_models` dict when creating the display, not relying on orchestrator being initialized.

4. **Container vs Static**: `WelcomeScreen` needed to be a `Container` (not `Static`) for `align: center middle` to work properly.

### Gotchas

1. **Config structure**: Model is nested in `backend.model`, not at top level of agent config.

2. **Compose timing**: `compose()` is called before orchestrator is set, so can't access `orchestrator.agents` there.

3. **Thread safety**: Always buffer content and flush periodically rather than updating widgets directly from background threads.

4. **TCSS specificity**: Status classes need to be combined properly (e.g., `AgentTab.active.status-working`).

5. **Height in Textual**: Use `height: 1fr` for flexible containers, `height: auto` for content-sized.

## Learnings from Phase 2

### Content Display Redesign

1. **Hide legacy widgets via CSS**: Using `AgentPanel RichLog { display: none; }` is cleaner than removing the widget entirely, preserving the option to re-enable.

2. **Route to new widgets, not old ones**: When `show_restart_separator()` was writing to the hidden RichLog, banners didn't show. Always verify that methods write to the active display widgets.

3. **Filter vs Categorize**: Don't filter valuable content (internal reasoning). Instead, categorize it and display in a collapsible section. Only filter true noise (empty JSON fragments, internal tool JSON that will be shown via proper tool cards).

4. **Content normalization as single entry point**: Having one `ContentNormalizer.normalize()` method that handles all preprocessing makes the system easier to maintain and debug.

5. **Workspace tool JSON filtering**: Internal coordination structures (`action_type`, `answer_data`) should be filtered from raw display because they'll be shown via proper tool cards - otherwise users see ugly JSON.

## Adding New Features

### Adding a New Widget

1. Create widget class (can be in `textual_terminal_display.py` or new file in `textual_widgets/`)
2. Add to `compose()` in `TextualApp`
3. Add styles to both `dark.tcss` and `light.tcss`
4. Wire up any event handlers

### Adding a New Modal

1. Inherit from `BaseModal` (handles ESC to close)
2. Implement `compose()` with content
3. Add action method in `TextualApp` to show it
4. Add key binding if needed

### Modifying Content Display

Content flows through `AgentPanel.add_content()`. To intercept/transform:
1. Modify `add_content()` method
2. Or modify `_flush_buffers()` in `TextualApp`
3. Or add preprocessing in `update_agent_content()` in `TextualTerminalDisplay`

## Content Display Architecture (Phase 2)

The content display system uses a layered architecture with content normalization, categorization, and specialized section widgets.

### Content Processing Flow

```
Content from Orchestrator
    │
    ▼
ContentNormalizer.normalize()
    │
    ├── Strip backend prefixes (emojis, [MCP], etc.)
    ├── Detect content type (tool_start, thinking, text, etc.)
    ├── Extract tool metadata
    ├── Flag coordination content (voting, answers)
    └── Filter noise (empty JSON fragments, workspace tool JSON)
    │
    ▼
AgentPanel.add_content()
    │
    ├── is_workspace_tool_json? → FILTER (hidden, will be tool cards)
    ├── is_json_noise? → FILTER (hidden)
    ├── is_coordination? → TimelineSection.add_reasoning()
    └── else → TimelineSection.add_text()
```

### Content Section Widgets

Located in `textual_widgets/content_sections.py`:

```
TimelineSection (Container)
├── ResponseSection (Static)      # Clean response/answer display
├── ReasoningSection (Static)     # Collapsible coordination content
├── ToolCallCard (Static)         # Individual tool call with status
└── RestartBanner (Static)        # Prominent restart separator
```

#### TimelineSection

Main content container that displays content chronologically:

```python
class TimelineSection(Container):
    """Chronological content display with tools interleaved."""

    def add_text(self, content: str) -> None
    def add_reasoning(self, content: str) -> None  # For coordination content
    def add_tool(self, tool_name: str, status: str, args: str = "") -> str
    def update_tool(self, tool_id: str, status: str, result: str = "") -> None
    def add_separator(self, label: str = "") -> None  # Uses RestartBanner for restarts
```

#### ReasoningSection

Collapsible section for internal reasoning and coordination content:

```python
class ReasoningSection(Static):
    """Collapsible reasoning/coordination section."""
    # Shows voting decisions, answer analysis, coordination messages
    # Styled with dashed border, can be expanded/collapsed
```

#### RestartBanner

Prominent visual separator when session restarts:

```python
class RestartBanner(Static):
    """Prominent restart separator banner."""
    # Red background, centered label
    # Format: "⚡ RESTART — ATTEMPT N — reason"
```

### Content Normalizer

Located in `content_normalizer.py`:

```python
class ContentNormalizer:
    @classmethod
    def normalize(cls, content: str, raw_type: str = "") -> NormalizedContent:
        """Single entry point for all content processing."""

    @staticmethod
    def strip_prefixes(content: str) -> str:
        """Remove backend emojis and prefixes."""

    @staticmethod
    def is_json_noise(content: str) -> bool:
        """Check for empty JSON fragments."""

    @staticmethod
    def is_workspace_tool_json(content: str) -> bool:
        """Check for internal action_type/answer_data JSON."""

    @staticmethod
    def is_coordination_content(content: str) -> bool:
        """Check for voting/coordination patterns."""
```

Key filtering patterns:
- **JSON noise**: `{}`, `[]`, `{`, `}`, etc.
- **Workspace tool JSON**: `action_type`, `answer_data`, `action: "new_answer"`, etc.
- **Coordination patterns**: "Voting for", "I will vote for", "existing answers", etc.

### CSS Styling

Tool cards use status-based styling:

```css
ToolCallCard {
    border: solid #3d4550;
    background: #1e2530;
}

ToolCallCard.status-running {
    border: solid #569cd6;
    background: #1a2535;
}

ToolCallCard.status-success {
    border: solid #4ec9b0;
    background: #1a2d28;
}
```

TimelineSection fills available space:

```css
TimelineSection {
    height: 1fr;  /* Fills available vertical space */
}
```

Legacy RichLog is hidden (replaced by TimelineSection):

```css
AgentPanel RichLog {
    display: none;
}
```

## Multi-Line Input

The TUI supports multi-line input using the `MultiLineInput` widget, which extends Textual's `TextArea`.

### Usage

- **Submit**: Press Enter to submit your question (matches standard convention)
- **New line**: Press Shift+Enter or Ctrl+J to insert a new line
- **Vim mode**: Type `/vim` to enable vim-style editing
- **Visual hint**: A hint above the input shows current mode and available commands

### Implementation

```python
class MultiLineInput(TextArea):
    """Multi-line input with Enter submission and optional vim mode."""

    BINDINGS = [
        Binding("enter", "submit", "Submit", priority=True),
        Binding("shift+enter", "newline", "New Line", priority=True),
        Binding("ctrl+j", "newline", "New Line", show=False),
    ]

    class Submitted(Message, bubble=True):
        """Sent when Enter is pressed."""

    class VimModeChanged(Message, bubble=True):
        """Sent when vim mode changes between normal/insert."""
```

### Vim Mode

The input supports optional vim-style editing, toggled via `/vim` command.

#### Enabling Vim Mode

Type `/vim` in the input and press Enter. The input enters INSERT mode (green indicator), ready for typing.

#### Mode Indicators

- **INSERT** (green): Normal typing, Escape switches to NORMAL
- **NORMAL** (yellow): Vim commands active, input border turns yellow

#### Vim Commands (Normal Mode)

| Category | Keys | Action |
|----------|------|--------|
| **Insert** | `i` | Insert at cursor |
| | `a` | Insert after cursor |
| | `A` | Insert at end of line |
| | `o` | Open line below |
| | `O` | Open line above |
| | `s` | Substitute character |
| | `S` | Substitute line |
| **Movement** | `h/j/k/l` | Left/down/up/right |
| | `w/b` | Word forward/backward |
| | `0/$` | Line start/end |
| | `gg/G` | Document start/end |
| **Delete** | `x/X` | Delete char at/before cursor |
| | `dd` | Delete line |
| | `dw` | Delete word |
| | `d$/D` | Delete to end of line |
| | `d0` | Delete to start of line |
| **Change** | `cc` | Change line |
| | `cw` | Change word |
| | `c$/C` | Change to end of line |
| | `c0` | Change to start of line |
| **Char Motion** | `f<char>` | Move to next char |
| | `t<char>` | Move to before char |
| | `F<char>` | Move to prev char |
| | `T<char>` | Move to after prev char |
| **Combined** | `dt<char>` | Delete to before char |
| | `df<char>` | Delete through char |
| | `ct<char>` | Change to before char |
| | `cf<char>` | Change through char |
| **Other** | `u` | Undo |
| | `Escape` | Enter normal mode (from insert) |

#### Disabling Vim Mode

Type `/vim` again to toggle off. The indicator disappears and normal editing resumes.

### CSS Styling

```css
#question_input {
    height: auto;
    min-height: 1;
    max-height: 10;
}

/* Vim normal mode border */
#question_input.vim-normal {
    border: solid #d29922;
}

/* Vim mode indicators */
#vim_indicator.vim-normal-indicator {
    background: #d29922;
    color: #0d1117;
}

#vim_indicator.vim-insert-indicator {
    background: #238636;
    color: #ffffff;
}
```

## File Reference

| File | Purpose |
|------|---------|
| `textual_terminal_display.py` | Main display class, TextualApp, AgentPanel |
| `textual_widgets/__init__.py` | Widget exports |
| `textual_widgets/tab_bar.py` | AgentTabBar, AgentTab, AgentTabChanged |
| `textual_widgets/multi_line_input.py` | MultiLineInput for multi-line text entry |
| `textual_widgets/content_sections.py` | TimelineSection, ReasoningSection, RestartBanner, etc. |
| `content_normalizer.py` | ContentNormalizer, NormalizedContent |
| `content_handlers.py` | ToolContentHandler, ThinkingContentHandler |
| `textual_themes/dark.tcss` | Dark theme styles |
| `textual_themes/light.tcss` | Light theme styles |
| `coordination_ui.py` | Creates display, manages coordination |
| `cli.py` | Entry point, passes agent_models to display |

## Testing

### Manual Testing Script

```bash
# Test with different agent counts
uv run massgen --display textual --config massgen/configs/basic/multi/three_agents_default.yaml "test"

# Test tab bar widget standalone
uv run python scripts/test_tab_bar.py
```

### Key Test Scenarios

1. Single agent - tab bar still shows, no navigation needed
2. Multiple agents - tab switching, background streaming
3. Welcome screen - shows on startup, dismisses on input
4. Status updates - tabs and panels update colors
5. Terminal resize - layout adapts
6. Theme switching - both dark and light work

## WebUI Parity Roadmap

The Textual TUI aims to provide feature parity with the MassGen WebUI. This section tracks the mapping between WebUI features and TUI implementations.

### Feature Comparison

| WebUI Feature | TUI Status | Key Binding | Notes |
|---------------|------------|-------------|-------|
| Toast Notifications | ✅ Basic | - | Using `self.notify()`, needs enhanced answer/vote toasts |
| Agent Cards | ✅ Done | Tab/1-9 | AgentPanel with status, streaming |
| Agent Status | ✅ Done | - | StatusBar + tab status badges |
| Vote Results | ✅ Done | `v` | VoteResultsModal |
| Vote Distribution | ⚠️ Partial | `v` | Leader highlighting done, bar chart TODO |
| Cost Breakdown | ✅ Done | `c` | CostBreakdownModal |
| Tool Metrics | ✅ Done | `m` | MetricsModal |
| MCP Status | ✅ Done | `p` | MCPStatusModal |
| Keyboard Shortcuts | ✅ Done | `?`/`h` | KeyboardShortcutsModal |
| Full Agent Output | ✅ Done | `f` | AgentOutputModal with copy/save |
| Workspace Browser | ✅ Done | `w` | WorkspaceBrowserModal - browse answer snapshots |
| File Preview | ✅ Done | - | Split pane with text file preview |
| Answer Browser | ✅ Done | `b` | AnswerBrowserModal - filter by agent, winner badges |
| Timeline View | ✅ Done | `t` | TimelineModal - chronological event list |
| Enhanced Toasts | ✅ Done | - | Model names, standings in vote/answer toasts |
| Progress Summary | ⚠️ Partial | - | StatusBar shows phase, needs counts |
| Follow-up Input | ⚠️ Basic | - | Input field exists, needs polish |
| Winner Celebration | ⚠️ Partial | - | Vote leader highlight, needs final winner |

### WebUI-Inspired Enhancements (Phase 5.5+)

#### ✅ Enhanced Toast Notifications (COMPLETE)
- Shows agent model name in answer toasts
- Shows voter → target with current standings in vote toasts
- Auto-dismiss after configurable timeout (5s answers, 3s votes)
- Tracks all answers/votes for browser and timeline modals

#### ✅ Answer Browser Modal (COMPLETE)
- `b` key or `/answers` command opens browser
- Lists all answers with timestamps and model names
- Filter by agent via dropdown selector
- Winner badges (🏆 gold), Final badges (✓ green)
- Vote count per agent, content preview

#### ✅ Timeline Visualization (COMPLETE)
- `t` key or `/timeline` command opens timeline
- Chronological event list format:
```
Event Timeline
──────────────────────────────────────────────────
  12:34:56  ○ agent_a submitted answer agent1.1
  12:34:58  ○ agent_b submitted answer agent2.1
  12:35:02  ◇ agent_a voted for agent_b
  12:35:10  ★ agent_b submitted answer agent2.2 (WINNER)
──────────────────────────────────────────────────
Total: 3 answers, 2 votes
```

#### ✅ Workspace Browser (COMPLETE)
- `w` key or `/files` command opens workspace browser
- Per-answer workspace selection via dropdown
- Split pane: file list (left) + preview (right)
- Filters hidden files, shows file sizes
- Text file preview with syntax-aware extensions

#### ⚠️ Vote Distribution Visualization (TODO)
WebUI shows bar chart. TUI should:
- ASCII bar chart (`████░░░░ 3/5`)
- Winner highlighted with trophy
- Sorted by vote count
- Total votes summary

## Hook Visualization (Phase 6)

The TUI displays hook executions attached to tool cards, providing visibility into
the hook framework that controls tool execution flow.

### Hook Display Architecture

```
Hook Execution Event
    │
    ▼
GeneralHookManager.execute_hooks()
    │
    ├── Tracks executed hooks on HookResult
    │
    ▼
AgentPanel receives tool content
    │
    ├── Pre-hook → ToolCallCard.add_pre_hook()
    │       └── Renders above tool card
    │
    └── Post-hook → ToolCallCard.add_post_hook()
            └── Renders below tool result
```

### Hook Types Displayed

| Hook | Type | Visual | When Shown |
|------|------|--------|------------|
| `round_timeout_hard` | Pre | 🪝 or 🚫 | Before tool, when timeout active |
| `round_timeout_soft` | Post | ⏰ | After tool, when soft timeout exceeded |
| `mid_stream_injection` | Post | 🪝 📥 | After tool, when context injected |

### Visual Rendering

Hooks render as decorations around the ToolCallCard:

```
  🪝 timeout_hard: allowed              ← Pre-hook (compact)
  📁 filesystem/write_file    ✓ (0.3s)  ← Tool card
    {"path": "..."}
    → Success
  🪝 mid_stream: +context               ← Post-hook (compact)
```

Blocked hooks appear more prominently:

```
  🚫 timeout_hard: BLOCKED - Hard timeout exceeded
  📁 filesystem/write_file    ✗ blocked
    {"path": "..."}
```

### Per-Agent Timeout Display in Header

The AgentPanel header shows per-agent timeout countdown:

- **Normal**: `⏱ 0:45 | ⏰ 0:15` (elapsed | remaining)
- **Warning** (<60s): `⏱ 0:45 | ⏰ 0:15` in yellow
- **Grace period**: `⏱ 1:05 | ⚠️ Grace: 0:55` in bold yellow
- **Hard blocked**: `⏱ 2:05 | 🚫 BLOCKED` in bold red

### Key Files

| File | Purpose |
|------|---------|
| `textual_widgets/tool_card.py` | ToolCallCard with hook display methods |
| `textual_terminal_display.py` | AgentPanel with timeout display |
| `mcp_tools/hooks.py` | HookResult with executed_hooks tracking |
| `orchestrator.py` | get_agent_timeout_state() method |

### CSS Styling (dark.tcss / light.tcss)

```css
/* Hook indicators */
.hook-indicator.blocked { color: #f44747; }
.hook-indicator.allowed { color: #c586c0; }

/* Timeout countdown in header */
.timeout-normal { color: #858585; }
.timeout-warning { color: #d29922; }
.timeout-critical { color: #f44747; font-weight: bold; }
```

---

### Remaining Implementation Priority

1. **Medium Priority** (Enhanced UX)
   - Vote distribution bar chart
   - Progress summary in StatusBar
   - Winner celebration effects
   - Multi-tab browser modal

2. **Lower Priority** (Polish)
   - Animated progress indicators
   - Compare workspaces view
   - File operation badges ([+] create, [~] modify)
