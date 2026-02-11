# MassGen v0.1.50 Release Announcement

<!--
This is the current release announcement. Copy this + feature-highlights.md to LinkedIn/X.
After posting, update the social links below.
-->

## Release Summary

We're excited to release MassGen v0.1.50, focused on Chunked Plan Execution & Skill Lifecycle Management! 🚀 Chunked plan execution for safer long-form task completion with progress checkpoints. Skill lifecycle management with consolidation, organizer, and previous-session skill loading. Iterative planning review modal. Responsive TUI mode bar. Worktree improvements with branch accumulation and cross-agent diff visibility.

## Install

```bash
pip install massgen==0.1.50
```

## Links

- **Release notes:** https://github.com/massgen/MassGen/releases/tag/v0.1.50
- **X post:** [TO BE ADDED AFTER POSTING]
- **LinkedIn post:** [TO BE ADDED AFTER POSTING]

---

## Full Announcement (for LinkedIn)

Copy everything below this line, then append content from `feature-highlights.md`:

---

We're excited to release MassGen v0.1.50, focused on Chunked Plan Execution & Skill Lifecycle Management! 🚀 Chunked plan execution for safer long-form task completion with progress checkpoints. Skill lifecycle management with consolidation, organizer, and previous-session skill loading. Iterative planning review modal. Responsive TUI mode bar.

**Key Features:**

**Chunked Plan Execution** - Safer long-form task completion:
- Plans divided into chunks (e.g., `C01_foundation`) and executed one chunk at a time
- Progress checkpoints with chunk browsing in TUI
- Frozen plan snapshots preserve original plan state during execution
- `target_steps` and `target_chunks` parameters for plan sizing with dynamic mode

**Iterative Planning Review Modal** - Plan iteration before execution:
- New modal with Continue Planning / Quick Edit / Finalize Plan options
- Allows plan refinement before committing to execution

**Skill Lifecycle Management** - Reusable skill workflows:
- New lifecycle modes: `create_or_update`, `create_new`, `consolidate`
- Skill organizer for merging overlapping skills into consolidated workflows
- `SKILL_REGISTRY.md` routing guide for skill discovery and selection
- Previous-session skill loading with `load_previous_session_skills` config
- Local Skills MCP for skill access in Docker/local execution contexts

**Worktree Improvements** - Better cross-agent collaboration:
- Branch accumulation across coordination rounds
- Cross-agent diff visibility via `generate_branch_summaries()`
- Orphan worktree cleanup

**Also in this release:**
- Responsive TUI mode bar with vertical/horizontal adaptive layout
- TUI homescreen and theming improvements with CSS refinements
- Skills modal with source grouping and quick actions (Enable All/Disable All)
- Plan depth controls with dynamic mode

**Bug Fixes:**
- Test fixes across hooks, Docker mounts, and snapshots

Release notes: https://github.com/massgen/MassGen/releases/tag/v0.1.50

Feature highlights:

<!-- Paste feature-highlights.md content here -->
