 # MassGen v0.1.46 Release Announcement

<!--
This is the current release announcement. Copy this + feature-highlights.md to LinkedIn/X.
After posting, update the social links below.
-->

## Release Summary

We're excited to release MassGen v0.1.46, featuring real-time subagent TUI streaming! 🚀 Subagents now display in interactive preview cards that expand to full timeline views, with a major TUI event architecture refactor for better maintainability and consistency.

## Install

```bash
pip install massgen==0.1.46
```

## Links

- **Release notes:** https://github.com/massgen/MassGen/releases/tag/v0.1.46
- **X post:** [TO BE ADDED AFTER POSTING]
- **LinkedIn post:** [TO BE ADDED AFTER POSTING]

---

## Full Announcement (for LinkedIn)

Copy everything below this line, then append content from `feature-highlights.md`:

---

We're excited to release MassGen v0.1.46, featuring real-time subagent TUI streaming! 🚀

**Subagent TUI Streaming**
- Clickable preview cards show subagent status and progress in the main TUI
- Click any card to expand to full timeline view with real-time event streaming
- Unified display components ensure identical tool displays between main and subagents
- Subagent rounds tracking with visual status indicators

**Enhanced Final Presentation**
- Final answer display now includes workspace visualization
- Winning agent clearly highlighted with visual indicator
- Improved formatting with better reasoning/answer separation

**TUI Architecture Refactor**
- Major refactor to structured event emission pipeline
- Single source of truth for display creation shared across agent types
- Improved maintainability and consistency
- Better debugging support with enhanced logging

**Bug Fixes**
- Fixed banner display issues for first coordination round
- Fixed tool call ID handling for models like kimi2.5
- Improved round tracking logic for accurate status display

**Documentation Updates**
- New tutorial video GIF previews for better visual guidance
- Comprehensive subagent architecture documentation
- Updated video tutorial links opening in new tabs

Try subagent streaming: `uv run massgen --config @examples/configs/features/test_subagent_orchestrator_code_mode.yaml "Use subagents to research bob dylan"`

Release notes: https://github.com/massgen/MassGen/releases/tag/v0.1.46

<!-- Paste feature-highlights.md content here -->

---
