# Change: Unify TUI Event Pipeline

## Why
The subagent TUI view renders a different timeline than the main TUI because they use different parsing pipelines (raw stream parsing vs. events.jsonl). This breaks parity and makes it hard to maintain a single source of truth for UI rendering.

## What Changes
- Establish a single, event-driven rendering pipeline (MassGen events → ContentProcessor → TimelineSection) for both main TUI and subagent views.
- Ensure subagent views mirror the main TUI timeline output for tools, thinking, status, and final answer content.
- Standardize subagent inner-agent tabs to show agent names + model names and allow cycling/filtering like the main TUI.

## Impact
- Affected specs: textual-tui
- Affected code: TUI rendering pipeline (Textual display), event streaming and consumption, subagent UI tabs
