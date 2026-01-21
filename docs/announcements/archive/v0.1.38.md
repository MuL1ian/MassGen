# MassGen v0.1.38 Release Announcement

<!--
This is the current release announcement. Copy this + feature-highlights.md to LinkedIn/X.
After posting, update the social links below.
-->

## Release Summary

We're excited to release MassGen v0.1.38, adding Task Planning, Two-Tier Workspaces & Project Instructions! 🚀

MassGen can now create structured plans for future workflows with the new `--plan` flag (plan-only, no auto-execution). Two-tier git-backed workspaces separate work-in-progress from complete deliverables with automatic snapshot commits. CLAUDE.md and AGENTS.md files are auto-discovered following the agents.md standard. Plus: batch media analysis, timeout reliability fixes, and Docker health monitoring.

## Install

```bash
pip install massgen==0.1.38
```

## Links

- **Release notes:** https://github.com/massgen/MassGen/releases/tag/v0.1.38
- **X post:** [TO BE ADDED AFTER POSTING]
- **LinkedIn post:** [TO BE ADDED AFTER POSTING]

---

## Full Announcement (for LinkedIn)

Copy everything below this line, then append content from `feature-highlights.md`:

---

We're excited to release MassGen v0.1.38, adding Task Planning, Two-Tier Workspaces & Project Instructions! 🚀

MassGen can now create structured plans for future workflows with the new `--plan` flag (plan-only, no auto-execution). Two-tier git-backed workspaces separate work-in-progress from complete deliverables with automatic snapshot commits. CLAUDE.md and AGENTS.md files are auto-discovered following the agents.md standard. Plus: batch media analysis, timeout reliability fixes, and Docker health monitoring.

**Key Features:**

**Task Planning Mode** - Create plans for future workflows with `--plan`:
- `--plan` flag creates structured plans (no auto-execution)
- `--plan-depth` controls planning granularity (shallow/medium/deep)
- Outputs `feature_list.json` with task dependencies and priorities

**Two-Tier Workspaces** - Git-backed scratch/deliverable separation:
- `scratch/` for work-in-progress, `deliverable/` for complete outputs
- Automatic `[INIT]`, `[SNAPSHOT]`, `[TASK]` git commits
- Task completion triggers commits with completion notes
- Agents can review history with `git log`

**Project Instructions Auto-Discovery** - Following agents.md standard:
- CLAUDE.md and AGENTS.md auto-discovered from context paths (use `@./` to include current directory)
- Hierarchical "closest wins" for monorepo support
- Instructions prepended to agent system messages

**Batch Image Analysis** - Multi-image support:
- `understand_image` accepts dict for named multi-image comparison
- `read_media` accepts list for batch image processing
- Dict keys become reference names in prompts

**Timeout & Reliability Fixes:**
- Circuit breaker prevents infinite tool denial loops
- Soft->hard timeout race condition fixed
- MCP tools properly restored after restart
- Docker health monitoring with log capture on failures

Release notes: https://github.com/massgen/MassGen/releases/tag/v0.1.38

Feature highlights:

<!-- Paste feature-highlights.md content here -->
