# Change: Add TUI Log Analysis Mode with Dev/User Profiles and Skill Management

## Why
MassGen already has backend log analysis, but the Textual TUI does not expose it as a first-class mode. Users also need an in-TUI way to discover, classify, and toggle skills, with a user-focused flow that turns run analysis into reusable skills.

## What Changes
- Add an `analysis` state to the existing mode-bar plan cycle (`normal -> plan -> execute -> analysis -> normal`).
- Reuse the existing plan settings popover surface for analysis controls:
  - profile (`dev` vs `user`)
  - log session / turn target
  - view analysis report action
  - open skills manager action
- Add a TUI skills manager modal that:
  - shows `Default` (built-in) vs `Created` (user/project/previous-session evolving) groups
  - supports session-only on/off toggles for all discovered skills
- In analysis mode:
  - default analysis target to current session latest turn, with selectable override
  - apply profile-specific prompt behavior
  - ensure skills are available and filtered by session toggles
- In user analysis profile, support confirm-before-write skill creation from analyzed run output.

## Impact
- Affected specs: `textual-tui`, `tui`
- Affected code:
  - `massgen/frontend/displays/tui_modes.py`
  - `massgen/frontend/displays/textual_widgets/mode_bar.py`
  - `massgen/frontend/displays/textual_widgets/plan_options.py`
  - `massgen/frontend/displays/textual_terminal_display.py`
  - `massgen/frontend/displays/textual/widgets/modals/*`
  - `massgen/frontend/interactive_controller.py`
  - `massgen/cli.py`
  - `massgen/system_message_builder.py`
