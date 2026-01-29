# Subagents Module

## Overview

Subagents are child MassGen processes spawned by parent agents to handle delegated tasks. They run in isolated workspaces with their own logging sessions.

## Log Directory Structure

```
.massgen/massgen_logs/log_YYYYMMDD_HHMMSS/
└── turn_1/attempt_1/subagents/
    └── {subagent_id}/                    # e.g., "bio", "discog"
        ├── conversation.json             # User/assistant messages
        ├── subprocess_logs.json          # Reference to subprocess log location
        ├── live_logs/                    # SYMLINK during execution
        │   └── log_YYYYMMDD.../          # Subprocess's own log session
        │       └── turn_1/attempt_1/
        │           ├── events.jsonl
        │           ├── execution_metadata.yaml
        │           └── ...
        ├── full_logs/                    # COPIED after completion
        │   ├── events.jsonl
        │   ├── execution_metadata.yaml
        │   ├── massgen.log
        │   ├── status.json
        │   └── {agent_id}_N/             # Inner agent logs
        └── workspace/                    # Subagent's working directory
```

## Live vs Full Logs

| Type | When | Structure | Use Case |
|------|------|-----------|----------|
| `live_logs/` | During execution | Symlink → nested `log_XXX/turn_1/attempt_1/` | Real-time streaming |
| `full_logs/` | After completion | Flat directory with all files | Post-mortem, TUI display |

### Live Logs Nesting

`live_logs` symlinks to the subprocess's `.massgen/massgen_logs/` which contains another timestamped session:
```
live_logs -> workspace/.massgen/massgen_logs/
live_logs/log_20260126_HHMMSS/turn_1/attempt_1/events.jsonl  # Actual file
```

## Key Data Structures

### SubagentResult.log_path

Set to the **subagent base directory** (not events.jsonl):
```python
log_path = ".../subagents/{subagent_id}/"
```

To get events: `Path(log_path) / "full_logs" / "events.jsonl"`

### SubagentDisplayData.log_path

Same as SubagentResult - the base subagent directory.

### execution_metadata.yaml

Contains the subagent's config including inner agents:
```yaml
config:
  agents:                          # LIST, not dict
    - id: bio_agent_1              # Agent ID at root
      backend:
        type: grok
        model: grok-4-1-fast-reasoning
    - id: bio_agent_2
      backend:
        type: grok
        model: grok-4-1-fast-reasoning
```

## Code Locations

| Component | File | Key Functions |
|-----------|------|---------------|
| Manager | `massgen/subagent/manager.py` | `_get_subagent_log_dir()`, `_setup_subagent_live_logs()`, `_copy_subagent_logs()` |
| Models | `massgen/subagent/models.py` | `SubagentResult`, `SubagentDisplayData`, `SubagentConfig` |
| TUI Screen | `massgen/frontend/displays/textual_widgets/subagent_screen.py` | `_init_event_reader()`, `_detect_inner_agents()` |
| TUI Card | `massgen/frontend/displays/textual_widgets/subagent_card.py` | `SubagentCard`, status polling |

## TUI Integration

### Opening Subagent Screen

1. User clicks SubagentCard
2. `SubagentCard.OpenModal` message posted with `SubagentDisplayData`
3. `SubagentScreen` pushed with the subagent data
4. Screen calls `_init_event_reader()` to load events

The TUI screen should be **exactly** the same as the parent agent screen, as subagents are just subcalls to MassGen. The exception is the presence of an additional header, which shows the subagent name.