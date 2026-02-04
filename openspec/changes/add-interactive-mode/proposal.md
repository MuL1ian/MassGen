# Change: Add Interactive Mode for MassGen TUI

## Why

MassGen currently operates as a task-oriented system where users provide a question, agents coordinate, and a final answer is produced. There's no persistent orchestration layer that can help users plan tasks, manage context across multiple runs, or decide when to delegate to multi-agent coordination vs. handle simple tasks directly.

Interactive Mode transforms MassGen from a single-task system into a **persistent orchestration companion** that serves as the main entry point for all interactions.

## What Changes

- **New interactive session layer**: A persistent `InteractiveSession` class that manages conversations across multiple runs
- **New `launch_run` MCP tool**: New MCP server (`massgen/mcp_tools/interactive/`) allowing the interactive agent to spawn full multi-agent coordination. MCP-based for portability to external backends (Claude Code, Codex, etc.)
- **New system prompt section**: `InteractiveModeSection` provides orchestrator persona and MassGen knowledge
- **TUI mode integration**: Extends `TuiModeState` with interactive mode fields
- **Run approval modal**: Optional approval step before spawning runs
- **Config schema extension**: New `orchestrator.interactive_mode` section in YAML configs
- **Project-based workspace**: Directory structure for managing context across runs

## Impact

- **Affected specs**: interactive-mode (new)
- **Affected code**:
  - `massgen/interactive_session.py` (new)
  - `massgen/mcp_tools/interactive/` (new MCP server)
  - `massgen/frontend/displays/textual/run_approval_modal.py` (new)
  - `massgen/system_prompt_sections.py` (modify)
  - `massgen/frontend/displays/tui_modes.py` (modify)
  - `massgen/frontend/displays/textual_terminal_display.py` (modify)
  - `massgen/frontend/displays/textual_widgets/mode_bar.py` (modify)
  - `massgen/config_validator.py` (modify)
  - `massgen/cli.py` (modify)
