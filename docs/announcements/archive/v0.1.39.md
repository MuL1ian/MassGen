# MassGen v0.1.39 Release Announcement

<!--
This is the current release announcement. Copy this + feature-highlights.md to LinkedIn/X.
After posting, update the social links below.
-->

## Release Summary

We're excited to release MassGen v0.1.39, adding Plan and Execute Workflow! 🚀

MassGen now supports a complete plan-then-execute workflow that separates "what to build" from "how to build it". Use `--plan-and-execute` to create a plan then immediately execute it, or `--execute-plan` to run existing plans. Task verification workflow distinguishes completed from verified work with batch verification groups. Plans are stored in `.massgen/plans/` with frozen snapshots and execution tracking.

## Install

```bash
pip install massgen==0.1.39
```

## Links

- **Release notes:** https://github.com/massgen/MassGen/releases/tag/v0.1.39
- **X post:** [TO BE ADDED AFTER POSTING]
- **LinkedIn post:** [TO BE ADDED AFTER POSTING]

---

## Full Announcement (for LinkedIn)

Copy everything below this line, then append content from `feature-highlights.md`:

---

We're excited to release MassGen v0.1.39, adding Plan and Execute Workflow! 🚀

MassGen now supports a complete plan-then-execute workflow that separates "what to build" from "how to build it". Use `--plan-and-execute` to create a plan then immediately execute it, or `--execute-plan` to run existing plans. Task verification workflow distinguishes completed from verified work with batch verification groups. Plans are stored in `.massgen/plans/` with frozen snapshots and execution tracking.

**Key Features:**

**Plan and Execute Workflow** - Flexible planning and execution modes:
- `--plan-and-execute`: Create plan then immediately execute it
- `--execute-plan <id|path|latest>`: Execute existing plans without re-planning
- `--broadcast <human|agents|false>`: Control planning collaboration

**Task Verification Workflow** - Distinguish implementation from validation:
- Status flow: `pending` → `in_progress` → `completed` → `verified`
- Verification groups (e.g., "foundation", "frontend_ui") for batch validation
- Agents verify entire groups at logical checkpoints

**Plan Storage System** - Persistent plan management in `.massgen/plans/`:
- Plan structure with metadata, execution logs, and diffs
- `frozen/` directory for immutable planning-phase snapshots
- `workspace/` directory for modified plan after execution

**Bug Fixes:**
- Response API function call message sanitization for OpenAI compatibility
- Plan execution edge cases (single-agent configs, subprocess deadlocks)

Release notes: https://github.com/massgen/MassGen/releases/tag/v0.1.39

Feature highlights:

<!-- Paste feature-highlights.md content here -->
