# TUI Production Upgrade - Technical Design

## Overview
This document details the technical architecture for upgrading the Textual TUI to production quality.

---

## 1. Layout Architecture

### Current Layout (Vertical Boxes)
```
┌────────────┬────────────┬────────────┐
│  Agent A   │  Agent B   │  Agent C   │
│  [scroll]  │  [scroll]  │  [scroll]  │
│            │            │            │
│            │            │            │
└────────────┴────────────┴────────────┘
```

**Problems:**
- Information overload with 3+ agents
- Small panels limit readable content
- Can't see full context of any single agent
- Hard to follow streaming in multiple panels

### New Layout (Horizontal Tabs)
```
┌─────────────────────────────────────────────────────────────────────────┐
│  MASSGEN  │ Session: abc123 │ Turn 2 │ Phase: Coordination              │
├─────────────────────────────────────────────────────────────────────────┤
│  [Agent A ⚙️] [Agent B ✅] [Agent C ⏳]                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Agent A (gpt-5)  ⚙️ Working                                           │
│  ────────────────────────────────────────────────────────────────────── │
│                                                                         │
│  [Full agent content with room to breathe]                              │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│ > Enter your question...                                                │
├─────────────────────────────────────────────────────────────────────────┤
│ 🗳️ Voting: A(2) B(1) │ Phase: enforcement │ 📊 Events: 5               │
└─────────────────────────────────────────────────────────────────────────┘
```

**Benefits:**
- Full-width content panel for focused reading
- Tab bar provides overview of all agents
- Status visible at a glance in tabs
- Room for structured tool call cards

### Widget Hierarchy
```
TextualApp (Screen)
├── HeaderWidget (dock: top)
│   ├── Logo/Title
│   ├── Session Info (ID, Turn, Phase)
│   └── Help Hints (collapsible)
│
├── AgentTabBar (dock: top, below header)
│   └── AgentTab × N (clickable, status badges)
│
├── MainContainer (fill remaining space)
│   └── AgentContentPanel (one visible at a time)
│       ├── AgentHeader (name, model, status)
│       └── ContentScroll (RichLog with tool cards)
│
├── InputWidget (dock: bottom)
│   └── TextArea or Input
│
├── StatusBar (dock: bottom)
│   ├── VoteDisplay
│   ├── PhaseIndicator
│   └── EventCounter
│
└── ToastContainer (overlay, bottom-right)
    └── ToastNotification × N (stacked)
```

---

## 2. Agent Tab Bar

### Visual Design
```
┌──────────────────────────────────────────────────────────────────┐
│  [Agent A ⚙️] [Agent B ✅] [Agent C ⏳] [Agent D ❌]              │
└──────────────────────────────────────────────────────────────────┘
     ↑ active      completed     working      error
     (highlighted)
```

### Tab States
| State | Icon | Background | Border |
|-------|------|------------|--------|
| Active + Working | ⚙️ | #007ACC | solid blue |
| Active + Complete | ✅ | #4ec9b0 | solid teal |
| Inactive + Working | ⚙️ | transparent | dashed |
| Inactive + Complete | ✅ | transparent | none |
| Error | ❌ | #f44747/10 | solid red |

### Navigation
| Key | Action |
|-----|--------|
| Tab | Next agent |
| Shift+Tab | Previous agent |
| 1-9 | Jump to agent N |
| Click on tab | Switch to agent |

### Implementation
```python
class AgentTabBar(Widget):
    """Horizontal tab bar for agent switching."""

    DEFAULT_CSS = """
    AgentTabBar {
        height: 3;
        dock: top;
        layout: horizontal;
    }
    """

    def __init__(self, agent_ids: List[str]):
        super().__init__()
        self.agent_ids = agent_ids
        self.active_agent: str = agent_ids[0] if agent_ids else ""
        self._agent_statuses: Dict[str, str] = {}

    def compose(self) -> ComposeResult:
        for agent_id in self.agent_ids:
            yield AgentTab(agent_id)

    def action_next_tab(self) -> None:
        """Switch to next agent."""
        ...

    def action_previous_tab(self) -> None:
        """Switch to previous agent."""
        ...

    def update_agent_status(self, agent_id: str, status: str) -> None:
        """Update status badge for an agent."""
        ...
```

---

## 3. Tool Call Cards

### Visual Design

**Collapsed State:**
```
┌─ 🔧 search_web ──────────────────────────────── ⏳ Running ─┐
└─────────────────────────────────────────────────────────────┘
```

**Expanded State:**
```
┌─ 🔧 search_web ──────────────────────────────── ✅ Done (1.2s) ─┐
│  Query: "python asyncio best practices"                          │
│  ────────────────────────────────────────────────────────────────│
│  Results: 5 pages found                                          │
│  [1] Real Python - Async IO in Python                            │
│  [2] Python Docs - asyncio — Asynchronous I/O                    │
│  [3] ...                                                         │
└──────────────────────────────────────────────────────────────────┘
```

### Card States
| State | Icon | Border Color |
|-------|------|--------------|
| Pending | ⏳ | gray |
| Running | ⏳ (animated) | blue |
| Success | ✅ | green |
| Error | ❌ | red |

### Tool Type Styling
| Type | Icon Prefix | Accent Color |
|------|-------------|--------------|
| MCP Tool | 🔌 | purple |
| Custom Tool | 🛠️ | orange |
| Filesystem | 📁 | cyan |
| Code Exec | 💻 | yellow |
| Web Search | 🌐 | blue |

### Data Model
```python
@dataclass
class ToolCallEvent:
    """Represents a tool call for display."""
    call_id: str
    tool_name: str
    tool_type: str  # "mcp", "custom", "filesystem", "code", "web"
    status: str  # "pending", "running", "success", "error"
    params: Dict[str, Any]
    result: Optional[str] = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    expanded: bool = False
```

### Implementation
```python
class ToolCallCard(Widget):
    """Collapsible card for displaying tool calls."""

    DEFAULT_CSS = """
    ToolCallCard {
        height: auto;
        margin: 0 1;
        border: round $secondary;
    }
    ToolCallCard.expanded {
        height: auto;
    }
    ToolCallCard.collapsed {
        height: 1;
    }
    """

    def __init__(self, event: ToolCallEvent):
        super().__init__()
        self.event = event

    def compose(self) -> ComposeResult:
        yield ToolCardHeader(self.event)
        if self.event.expanded:
            yield ToolCardBody(self.event)

    def on_click(self) -> None:
        """Toggle expansion."""
        self.event.expanded = not self.event.expanded
        self.refresh()
```

---

## 4. Status Bar

### Visual Design
```
┌─────────────────────────────────────────────────────────────────────────┐
│ 🗳️ Votes: A(2) B(1) C(0) │ Phase: enforcement │ 📊 Events: 12 │ ⏱️ 45s │
└─────────────────────────────────────────────────────────────────────────┘
```

### Sections
1. **Vote Display**: Real-time vote counts per agent
2. **Phase Indicator**: Current orchestration phase
3. **Event Counter**: Click to open events modal
4. **Timer**: Elapsed time for current turn

### Phase Indicators
| Phase | Display |
|-------|---------|
| initial_answer | `📝 Answering` |
| enforcement | `🗳️ Voting` |
| presentation | `🎤 Presenting` |
| completed | `✅ Complete` |

### Implementation
```python
class StatusBar(Widget):
    """Persistent status bar at bottom of screen."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        dock: bottom;
        background: $surface;
        border-top: solid $primary;
    }
    """

    def __init__(self):
        super().__init__()
        self.votes: Dict[str, int] = {}
        self.phase: str = "initial_answer"
        self.event_count: int = 0
        self.start_time: Optional[datetime] = None

    def compose(self) -> ComposeResult:
        yield VoteDisplay()
        yield PhaseIndicator()
        yield EventCounter()
        yield Timer()

    def update_votes(self, votes: Dict[str, int]) -> None:
        """Update vote counts."""
        ...

    def set_phase(self, phase: str) -> None:
        """Update current phase."""
        ...
```

---

## 5. Toast Notifications

### Visual Design
```
                                    ┌──────────────────────────────────┐
                                    │ 🗳️ Agent B voted for Agent A    │
                                    │ "Best analysis with examples"   │
                                    │                           [5s]  │
                                    └──────────────────────────────────┘
                                    ┌──────────────────────────────────┐
                                    │ ✅ Agent C completed answer      │
                                    │                           [3s]  │
                                    └──────────────────────────────────┘
```

### Toast Types
| Type | Icon | Border Color | Use Case |
|------|------|--------------|----------|
| vote | 🗳️ | amber | Vote cast events |
| answer | 📝 | blue | Answer submitted |
| complete | ✅ | green | Agent completed |
| error | ❌ | red | Errors |
| info | ℹ️ | gray | General info |

### Behavior
- Auto-dismiss after 5 seconds
- Click to dismiss immediately
- Stack from bottom (newest at bottom)
- Max 3 visible at once (older ones queue)
- Fade-out animation on dismiss

### Implementation
```python
class ToastNotification(Widget):
    """Auto-dismissing notification toast."""

    DEFAULT_CSS = """
    ToastNotification {
        width: 40;
        height: auto;
        margin: 1;
        padding: 1;
        border: round $secondary;
        layer: overlay;
    }
    """

    def __init__(self, title: str, message: str, toast_type: str = "info"):
        super().__init__()
        self.title = title
        self.message = message
        self.toast_type = toast_type
        self.dismiss_timer: Optional[Timer] = None

    def on_mount(self) -> None:
        """Start auto-dismiss timer."""
        self.dismiss_timer = self.set_timer(5.0, self.dismiss)

    def dismiss(self) -> None:
        """Remove this toast."""
        self.remove()


class ToastContainer(Widget):
    """Container for stacking toast notifications."""

    DEFAULT_CSS = """
    ToastContainer {
        dock: bottom;
        align: right bottom;
        layer: overlay;
        width: auto;
        height: auto;
    }
    """

    def add_toast(self, title: str, message: str, toast_type: str = "info") -> None:
        """Add a new toast notification."""
        toast = ToastNotification(title, message, toast_type)
        self.mount(toast)

        # Limit visible toasts
        if len(self.children) > 3:
            self.children[0].remove()
```

---

## 6. Event System Design

### Event Types
```python
class TUIEvent:
    """Base class for TUI events."""
    timestamp: datetime


class AgentContentEvent(TUIEvent):
    """Agent streaming content."""
    agent_id: str
    content: str
    content_type: str  # "thinking", "tool", "status", "presentation"


class AgentStatusEvent(TUIEvent):
    """Agent status change."""
    agent_id: str
    status: str  # "waiting", "working", "streaming", "completed", "error"


class ToolCallEvent(TUIEvent):
    """Tool call start/update/complete."""
    agent_id: str
    call_id: str
    tool_name: str
    status: str
    params: Optional[Dict] = None
    result: Optional[str] = None


class VoteEvent(TUIEvent):
    """Vote cast."""
    voter_id: str
    target_id: str
    reason: str


class PhaseEvent(TUIEvent):
    """Coordination phase change."""
    phase: str
    details: Optional[str] = None
```

### Event Flow
```
Orchestrator
    │
    ▼
CoordinationUI (adapter)
    │
    ▼
TextualTerminalDisplay
    │
    ├──► AgentTabBar.update_status()
    ├──► AgentContentPanel.append_content()
    ├──► StatusBar.update()
    └──► ToastContainer.add_toast()
```

### Event Dispatch
```python
class TextualTerminalDisplay:
    def dispatch_event(self, event: TUIEvent) -> None:
        """Route event to appropriate widgets."""
        if isinstance(event, AgentContentEvent):
            self._handle_content(event)
        elif isinstance(event, AgentStatusEvent):
            self._handle_status(event)
        elif isinstance(event, ToolCallEvent):
            self._handle_tool_call(event)
        elif isinstance(event, VoteEvent):
            self._handle_vote(event)
        elif isinstance(event, PhaseEvent):
            self._handle_phase(event)

    def _handle_vote(self, event: VoteEvent) -> None:
        """Handle vote event."""
        # Update status bar
        self._status_bar.increment_vote(event.target_id)

        # Show toast
        self._toast_container.add_toast(
            title=f"🗳️ {event.voter_id} voted for {event.target_id}",
            message=event.reason[:50] + "..." if len(event.reason) > 50 else event.reason,
            toast_type="vote"
        )
```

---

## 7. Keyboard Navigation Map

### Global Shortcuts
| Key | Action | Context |
|-----|--------|---------|
| Tab | Next agent tab | Always |
| Shift+Tab | Previous agent tab | Always |
| 1-9 | Jump to agent N | Always |
| Ctrl+K | Toggle safe keyboard mode | Always |
| Ctrl+C | Cancel current turn | During processing |
| Escape | Close modal/cancel input | Modal open / Input focused |

### Agent Panel Shortcuts
| Key | Action |
|-----|--------|
| j / Down | Scroll down |
| k / Up | Scroll up |
| g | Jump to top |
| G | Jump to bottom |
| Enter | Expand/collapse focused tool card |
| Space | Toggle auto-scroll |

### Input Shortcuts
| Key | Action |
|-----|--------|
| Enter | Submit (single line mode) |
| Ctrl+Enter | Submit (multi-line mode) |
| Up | Previous history |
| Down | Next history |
| Tab | Autocomplete (if available) |

### Modal Shortcuts
| Key | Action |
|-----|--------|
| Escape | Close modal |
| j/k | Navigate items |
| Enter | Select item |
| q | Close modal |

---

## 8. Theme System

### CSS Variables (dark.tcss)
```css
$background: #1e1e1e;
$surface: #252526;
$surface-light: #2d2d2d;
$text: #d4d4d4;
$text-muted: #808080;
$primary: #007ACC;
$secondary: #569cd6;
$success: #4ec9b0;
$warning: #ce9178;
$error: #f44747;
$info: #9cdcfe;

/* Status colors */
$status-working: #569cd6;
$status-streaming: #4ec9b0;
$status-completed: #4ec9b0;
$status-error: #f44747;
$status-waiting: #808080;

/* Toast colors */
$toast-vote: #d7ba7d;
$toast-answer: #569cd6;
$toast-complete: #4ec9b0;
$toast-error: #f44747;
$toast-info: #808080;

/* Tool type colors */
$tool-mcp: #c586c0;
$tool-custom: #ce9178;
$tool-filesystem: #4ec9b0;
$tool-code: #dcdcaa;
$tool-web: #569cd6;
```

### Component Styles
```css
/* Tab bar */
AgentTabBar {
    height: 3;
    dock: top;
    background: $surface;
    border-bottom: solid $primary;
}

AgentTab {
    width: auto;
    padding: 0 2;
    margin: 0 1;
}

AgentTab.active {
    background: $primary;
    color: white;
}

AgentTab.inactive {
    background: transparent;
    border: dashed $text-muted;
}

/* Tool cards */
ToolCallCard {
    margin: 1 0;
    padding: 0 1;
    border: round $secondary;
}

ToolCallCard.collapsed {
    height: 1;
}

ToolCallCard.expanded {
    height: auto;
}

ToolCallCard.status-running {
    border: round $status-working;
}

ToolCallCard.status-success {
    border: round $success;
}

ToolCallCard.status-error {
    border: round $error;
}

/* Status bar */
StatusBar {
    height: 1;
    dock: bottom;
    background: $surface;
    border-top: solid $primary;
    padding: 0 1;
}

/* Toasts */
ToastNotification {
    width: 40;
    padding: 1;
    margin: 0 1 1 0;
    border: round $secondary;
    background: $surface;
}

ToastNotification.type-vote {
    border: round $toast-vote;
}

ToastNotification.type-complete {
    border: round $toast-complete;
}

ToastNotification.type-error {
    border: round $toast-error;
}
```

---

## 9. Content Display Architecture (Revised)

### Problem
Current TUI shows ALL streaming content, causing information overload. Original plan was to filter content, but internal reasoning is valuable - it just needs organization.

### Solution: Content Normalization & Section Widgets

**Key Decision**: Don't filter valuable content (internal reasoning, voting). Instead, categorize it and display in organized sections. Only filter true noise.

### Content Normalization (Single Entry Point)
```python
class ContentNormalizer:
    """Single entry point for all content preprocessing."""

    @classmethod
    def normalize(cls, content: str, raw_type: str = "") -> NormalizedContent:
        """Process content for display.

        Steps:
        1. Strip backend prefixes (emojis, [MCP], etc.)
        2. Detect content type (tool_start, thinking, text, etc.)
        3. Extract tool metadata
        4. Flag coordination content (for grouping, not filtering)
        5. Filter noise (empty JSON, workspace tool JSON)
        """

    @staticmethod
    def is_workspace_tool_json(content: str) -> bool:
        """Check for internal coordination JSON.

        Filters: action_type, answer_data, action: "new_answer", etc.
        These are hidden because they'll be shown via proper tool cards.
        """

    @staticmethod
    def is_coordination_content(content: str) -> bool:
        """Check for voting/coordination patterns (for categorization).

        Patterns: "Voting for", "I will vote for", "existing answers", etc.
        This content is displayed in ReasoningSection, not filtered.
        """
```

### Section Widget Architecture
```
TimelineSection (Container) - Chronological content display
├── ResponseSection (Static)      # Clean response/answer display
├── ReasoningSection (Static)     # Collapsible coordination content
├── ToolCallCard (Static)         # Individual tool call with status
└── RestartBanner (Static)        # Prominent restart separator
```

### TimelineSection
```python
class TimelineSection(Container):
    """Chronological content with tools interleaved."""

    def add_text(self, content: str) -> None
    def add_reasoning(self, content: str) -> None  # Coordination content
    def add_tool(self, tool_name: str, status: str, args: str = "") -> str
    def update_tool(self, tool_id: str, status: str, result: str = "") -> None
    def add_separator(self, label: str = "") -> None  # RestartBanner for restarts
```

### RestartBanner
```python
class RestartBanner(Static):
    """Prominent visual separator for session restarts."""
    # Red background, centered label
    # Format: "⚡ RESTART — ATTEMPT N — reason"
```

### Content Routing Flow
```
Content → ContentNormalizer.normalize()
              │
              ├── is_workspace_tool_json? → FILTER (hidden)
              ├── is_json_noise? → FILTER (hidden)
              ├── is_coordination? → TimelineSection.add_reasoning()
              └── else → TimelineSection.add_text()

Tool events → ToolContentHandler.process()
              │
              └── TimelineSection.add_tool() / update_tool()

Restart → show_restart_separator()
              │
              └── TimelineSection.add_separator() → RestartBanner
```

### What Gets Filtered vs Categorized

| Content Type | Action | Reason |
|--------------|--------|--------|
| Empty JSON `{}`, `[]` | FILTER | Pure noise |
| Workspace tool JSON | FILTER | Will be tool cards |
| Voting/coordination | CATEGORIZE → ReasoningSection | Valuable but needs organization |
| Tool calls | PARSE → ToolCallCard | Structured display |
| Regular text | DISPLAY → TimelineSection | Normal content |

### CSS: Legacy RichLog Hidden
```css
/* Hide legacy RichLog, TimelineSection is primary display */
AgentPanel RichLog {
    display: none;
}

TimelineSection {
    height: 1fr;  /* Fill available space */
}
```

---

## 10. Migration Strategy

### Phase 1: Parallel Operation
- Both Rich and Textual available via `--display` flag
- Textual becomes feature-complete
- No deprecation warnings yet

### Phase 2: Soft Migration
- `--display textual` becomes default
- `--display rich` still available
- Deprecation warning shown when using Rich

### Phase 3: Hard Migration
- Rich terminal removed or moved to legacy
- `--display rich` shows error with migration guide
- TUI is the only terminal option

### CLI Changes
```python
# Current
parser.add_argument("--display", choices=["rich", "textual"], default=None)

# Phase 2
parser.add_argument("--display", choices=["rich", "textual"], default="textual")

# When using Rich
if args.display == "rich":
    print("⚠️ Rich terminal is deprecated. Use --display textual instead.")
    print("   Rich will be removed in v0.2.0")
```

---

## Appendix: File Structure

```
massgen/frontend/displays/
├── base_display.py
├── terminal_display.py
├── rich_terminal_display.py
├── textual_terminal_display.py  # Main display, AgentPanel
├── content_normalizer.py        # ContentNormalizer, NormalizedContent
├── content_handlers.py          # ToolContentHandler, ThinkingContentHandler
├── textual_widgets/
│   ├── __init__.py              # Widget exports
│   ├── tab_bar.py               # AgentTabBar, AgentTab
│   ├── tool_card.py             # ToolCallCard (for tool display)
│   └── content_sections.py      # TimelineSection, ReasoningSection, RestartBanner
└── textual_themes/
    ├── dark.tcss                # Dark theme (VS Code-inspired)
    └── light.tcss               # Light theme
```
