# MassGen v0.1.38 Release Announcement

<!--
This is the current release announcement. Copy this + feature-highlights.md to LinkedIn/X.
After posting, update the social links below.
-->

## Release Summary

We're excited to release MassGen v0.1.38, adding Task Planning, Two-Tier Workspaces & Project Instructions!🚀

Agents can now plan before they execute with the new `--plan` flag. Two-tier git-backed workspaces separate work-in-progress from complete deliverables with automatic snapshot commits. CLAUDE.md and AGENTS.md files are auto-discovered following the agents.md standard. Plus: batch media analysis, timeout reliability fixes, and Docker health monitoring.

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

We're excited to release MassGen v0.1.38, adding Task Planning, Two-Tier Workspaces & Project Instructions!🚀

Agents can now plan before they execute with the new `--plan` flag. Two-tier git-backed workspaces separate work-in-progress from complete deliverables with automatic snapshot commits. CLAUDE.md and AGENTS.md files are auto-discovered following the agents.md standard. Plus: batch media analysis, timeout reliability fixes, and Docker health monitoring.

**Key Features:**

**Task Planning Mode** - Structured execution with `--plan`:
- `--plan` flag enables planning before execution
- `--plan-depth` controls planning depth (1-3 levels)
- Agents create task lists before executing work

**Two-Tier Workspaces** - Git-backed scratch/deliverable separation:
- `scratch/` for work-in-progress, `deliverable/` for complete outputs
- Automatic `[INIT]`, `[SNAPSHOT]`, `[TASK]` git commits
- Task completion triggers commits with completion notes
- Agents can review history with `git log`

**Project Instructions Auto-Discovery** - Following agents.md standard:
- CLAUDE.md and AGENTS.md auto-discovered from context paths
- Hierarchical "closest wins" for monorepo support
- Seamless integration with `@path` syntax

**Batch Media Analysis** - Multi-image support:
- `understand_image` accepts dict for named multi-image comparison
- `read_media` accepts list for batch parallel processing
- Dict keys become reference names in prompts

**Timeout & Reliability Fixes:**
- Circuit breaker prevents infinite tool denial loops
- Soft->hard timeout race condition fixed
- MCP tools properly restored after restart
- Docker health monitoring with log capture on failures

Release notes: https://github.com/massgen/MassGen/releases/tag/v0.1.38

Feature highlights:

<!-- Paste feature-highlights.md content here -->
