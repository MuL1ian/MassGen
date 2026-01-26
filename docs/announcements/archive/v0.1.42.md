# MassGen v0.1.42 Release Announcement

<!--
This is the current release announcement. Copy this + feature-highlights.md to LinkedIn/X.
After posting, update the social links below.
-->

## Release Summary

We're excited to release MassGen v0.1.42, featuring Human Input Queue! 🚀 Guide your agents in real-time—inject feedback mid-stream while they work, keeping them on track without interrupting their flow. Plus, a comprehensive TUI Visual Redesign brings a modern "Conversational AI" aesthetic to the terminal. Experience it: massgen --display textual

## Install

```bash
pip install massgen==0.1.42
```

## Links

- **Release notes:** https://github.com/massgen/MassGen/releases/tag/v0.1.42
- **X post:** [TO BE ADDED AFTER POSTING]
- **LinkedIn post:** [TO BE ADDED AFTER POSTING]

---

## Full Announcement (for LinkedIn)

Copy everything below this line, then append content from `feature-highlights.md`:

---

We're excited to release MassGen v0.1.42, featuring Human Input Queue!

**Human Input Queue**
- Inject messages to agents mid-stream while they work
- Thread-safe queue with per-agent tracking
- Visual indicators in TUI when input is pending

**TUI Visual Redesign**
The Textual terminal UI has been completely refreshed with a modern "Conversational AI" aesthetic:
- Rounded corners and softer borders throughout
- Professional desaturated color palette
- Edge-to-edge layouts with proper spacing
- Redesigned agent tabs, tool cards, and modals
- Scroll indicators and progress bars

**AG2 Single-Agent Fix**
- Fixed coordination issues for single-agent AG2 setups
- Proper vote handling when only one agent present

Try the new TUI: `massgen --display textual "your question"`

Release notes: https://github.com/massgen/MassGen/releases/tag/v0.1.42

<!-- Paste feature-highlights.md content here -->

---
