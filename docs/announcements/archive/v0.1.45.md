# MassGen v0.1.45 Release Announcement

<!--
This is the current release announcement. Copy this + feature-highlights.md to LinkedIn/X.
After posting, update the social links below.
-->

## Release Summary

We're excited to release MassGen v0.1.45, featuring TUI (Textual Terminal) as the default display mode! 🚀 All users now get the superior interactive terminal UI by default, with automatic migration for existing configs. Setup wizards generate TUI configs out of the box, and documentation has been enhanced to highlight the TUI experience.

## Install

```bash
pip install massgen==0.1.45
```

## Links

- **Release notes:** https://github.com/massgen/MassGen/releases/tag/v0.1.45
- **X post:** [TO BE ADDED AFTER POSTING]
- **LinkedIn post:** [TO BE ADDED AFTER POSTING]

---

## Full Announcement (for LinkedIn)

Copy everything below this line, then append content from `feature-highlights.md`:

---

We're excited to release MassGen v0.1.45, featuring TUI (Textual Terminal) as the default display mode! 🚀

**TUI as Default Display**
- All new MassGen installations use the superior TUI experience by default
- Existing configs with `rich_terminal` automatically migrate with deprecation warning
- 160+ example configs updated to use `textual_terminal`
- Use `--display rich` flag to explicitly request legacy Rich display

**Enhanced Setup & First-Run Experience**
- Setup wizard (`--setup`, `--quickstart`) generates TUI configs by default
- Clear documentation highlighting TUI benefits for new users
- Prominent TUI feature descriptions throughout docs
- Smooth migration path for existing users

**Bug Fixes & Packaging**
- Fixed case study page paths for proper documentation rendering
- Added missing files to MANIFEST.in for complete PyPI package distribution
- Updated ReadTheDocs configuration with Python 3.12

**What is the TUI?**
The Textual Terminal UI provides:
- Interactive mode cycling (Normal → Planning → Execute) via Shift+Tab
- Real-time agent progress with collapsible tool calls
- Plan browsing and execution from a visual selector
- Human input queue for mid-stream message injection
- Organized timeline with tool batching and rounded cards
- Professional "Conversational AI" aesthetic with desaturated colors

Try the TUI: `massgen --display textual` (now the default!)

Release notes: https://github.com/massgen/MassGen/releases/tag/v0.1.45

<!-- Paste feature-highlights.md content here -->

---
