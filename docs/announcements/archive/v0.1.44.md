# MassGen v0.1.44 Release Announcement

<!--
This is the current release announcement. Copy this + feature-highlights.md to LinkedIn/X.
After posting, update the social links below.
-->

## Release Summary

We're excited to release MassGen v0.1.44, featuring Execute Mode for independent plan selection! 🔄 Cycle through Normal → Planning → Execute modes via Shift+Tab, browse and select from existing plans, and automatically preserve context paths between planning and execution phases. Enhanced case studies page with setup guides for first-time users.

## Install

```bash
pip install massgen==0.1.44
```

## Links

- **Release notes:** https://github.com/massgen/MassGen/releases/tag/v0.1.44
- **X post:** [TO BE ADDED AFTER POSTING]
- **LinkedIn post:** [TO BE ADDED AFTER POSTING]

---

## Full Announcement (for LinkedIn)

Copy everything below this line, then append content from `feature-highlights.md`:

---

We're excited to release MassGen v0.1.44, featuring Execute Mode for independent plan selection! 🔄

**Execute Mode**
- Cycle through Normal → Planning → Execute modes via Shift+Tab
- Plan selector popover shows up to 10 recent plans with timestamps
- "View Full Plan" button displays complete task breakdown
- Press Enter to execute selected plan without additional input
- Context paths automatically preserved from planning to execution

**Case Studies UX Enhancements**
- Interactive "Try it yourself" setup sections with quick start instructions
- Quick start command: `uv run massgen --web`
- Model selection guidance for best results
- Terminal config examples for CLI users
- Helper text for comparing MassGen with single-agent baselines

**TUI Performance Improvements**
- Optimized timeline rendering with viewport-based scrolling
- Fixed tool card spacing issues
- Enhanced tool tracking for better streaming visualization

**Bug Fixes**
- Fixed planning instruction injection during execute mode
- Improved plan mode separation logic

Try Execute Mode: `massgen --display textual` → Press Shift+Tab twice to enter Execute mode

Release notes: https://github.com/massgen/MassGen/releases/tag/v0.1.44

<!-- Paste feature-highlights.md content here -->

---
