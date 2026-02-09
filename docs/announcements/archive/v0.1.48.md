# MassGen v0.1.48 Release Announcement

<!--
This is the current release announcement. Copy this + feature-highlights.md to LinkedIn/X.
After posting, update the social links below.
-->

## Release Summary

We're excited to release MassGen v0.1.48, adding Decomposition Mode! 🚀 A new coordination mode that decomposes tasks into subtasks assigned to individual agents, with a presenter agent synthesizing the final result. Plus: Worktree isolation for safe file writes with review modal, quickstart wizard Docker setup, and bug fixes.

## Install

```bash
pip install massgen==0.1.48
```

## Links

- **Release notes:** https://github.com/massgen/MassGen/releases/tag/v0.1.48
- **X post:** [TO BE ADDED AFTER POSTING]
- **LinkedIn post:** [TO BE ADDED AFTER POSTING]

---

## Full Announcement (for LinkedIn)

Copy everything below this line, then append content from `feature-highlights.md`:

---

We're excited to release MassGen v0.1.48, adding Decomposition Mode! 🚀 A new coordination mode that decomposes tasks into subtasks assigned to individual agents, with a presenter agent synthesizing the final result. Plus: Worktree isolation for safe file writes with review modal, quickstart wizard Docker setup, and bug fixes.

**Key Features:**

**Decomposition Mode** - New `decomposition` coordination mode:
- Automatically decomposes complex tasks into subtasks assigned to individual agents
- Presenter agent role for synthesizing subtask results into a final answer
- TUI mode bar toggle, subtask assignment display, and generation modals
- Quickstart wizard integration for easy decomposition mode selection

**Worktree Isolation** - Safe file writes with review workflow:
- New `write_mode` config for git worktree-based isolation of agent writes
- Review modal for approving/rejecting changes before applying to original paths
- Shadow repo support for non-git directories

**Quickstart Wizard Docker Setup** - Docker setup step with animated pull progress and real-time stdout streaming

Release notes: https://github.com/massgen/MassGen/releases/tag/v0.1.48

Feature highlights:

<!-- Paste feature-highlights.md content here -->
