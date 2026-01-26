# MassGen v0.1.43 Release Announcement

<!--
This is the current release announcement. Copy this + feature-highlights.md to LinkedIn/X.
After posting, update the social links below.
-->

## Release Summary

We're excited to release MassGen v0.1.43, featuring Tool Call Batching in the TUI! 🚀 Consecutive MCP tool calls are now grouped into collapsible tree views—see filesystem operations batched with timing info, expand to view details, and enjoy cleaner final answer presentation with reasoning separated from results. Experience it: massgen --display textual

## Install

```bash
pip install massgen==0.1.43
```

## Links

- **Release notes:** https://github.com/massgen/MassGen/releases/tag/v0.1.43
- **X post:** [TO BE ADDED AFTER POSTING]
- **LinkedIn post:** [TO BE ADDED AFTER POSTING]

---

## Full Announcement (for LinkedIn)

Copy everything below this line, then append content from `feature-highlights.md`:

---

We're excited to release MassGen v0.1.43, featuring Tool Call Batching in the TUI! 🚀

**Tool Call Batching (TUI)**
- Consecutive MCP tool calls grouped into collapsible tree views
- Shows 3 items by default with "+N more" indicator
- Click to expand full list of operations
- Tree structure: server → operation → file path → status

**Clean Final Answers**
- Reasoning text now separated from actual answer content
- Visual distinction: reasoning collapsed/smaller, answer prominent
- Clear "FINAL ANSWER" display with winner and vote count

**Plan Mode Enhancements**
- New PlanOptionsPopover for browsing recent plans
- Plan depth selector (thorough/balanced/quick)
- Broadcast mode toggle for collaboration control

**Bug Fixes**
- Fixed bottom status bar not showing
- Fixed scrolling bar display issues
- Fixed mode button interactions

Try the new TUI: `massgen --display textual "your question"`

Release notes: https://github.com/massgen/MassGen/releases/tag/v0.1.43

<!-- Paste feature-highlights.md content here -->

---
