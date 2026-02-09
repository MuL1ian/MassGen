# MassGen v0.1.49 Release Announcement

<!--
This is the current release announcement. Copy this + feature-highlights.md to LinkedIn/X.
After posting, update the social links below.
-->

## Release Summary

We're excited to release MassGen v0.1.49, focused on Coordination Quality! 🚀 Log analysis mode now built into the TUI for in-app run analysis. Fairness gate prevents fast agents from dominating, and checklist voting brings structured quality evaluation. Plus: automated testing infrastructure, persona generation now in TUI mode bar, skills modal, and bug fixes.

## Install

```bash
pip install massgen==0.1.49
```

## Links

- **Release notes:** https://github.com/massgen/MassGen/releases/tag/v0.1.49
- **X post:** [TO BE ADDED AFTER POSTING]
- **LinkedIn post:** [TO BE ADDED AFTER POSTING]

---

## Full Announcement (for LinkedIn)

Copy everything below this line, then append content from `feature-highlights.md`:

---

We're excited to release MassGen v0.1.49, focused on Coordination Quality! 🚀 Log analysis mode now built into the TUI for in-app run analysis. Fairness gate prevents fast agents from dominating, and checklist voting brings structured quality evaluation. Plus: automated testing infrastructure, persona generation now in TUI mode bar, and bug fixes.

**Key Features:**

**Log Analysis Mode in TUI** - Analyze runs without leaving the terminal:
- New "Analyzing" state in the TUI mode bar (Normal → Planning → Executing → Analyzing)
- Browse and select log directories and turns directly in the TUI
- Configurable analysis profiles for different analysis depths
- Empty submit in analysis mode runs default analysis on selected target

**Fairness Gate** - Balanced multi-agent coordination:
- Prevents fast agents from dominating rounds with configurable `fairness_lead_cap_answers`
- `max_midstream_injections_per_round` controls injection frequency
- Ensures all agents contribute meaningfully regardless of speed

**Checklist Voting** - Structured quality evaluation:
- New `checklist_tools_server.py` MCP server for objective quality assessment
- Binary pass/fail scoring replaces subjective voting
- Consistent, repeatable evaluation across coordination rounds

**Automated Testing Infrastructure** - CI/CD and snapshot testing:
- GitHub Actions workflow (`tests.yml`) for automated test execution
- SVG snapshot baselines for TUI visual regression testing
- 16+ new test files with comprehensive testing strategy

**Also in this release:**
- Persona generation now accessible from the TUI mode bar
- Skills modal for discovering and toggling skills in interactive mode

**Bug Fixes:**
- Fixed "[No response generated]" shadow agent errors (PR #861)
- Round banner timing, hook injection, final answer lock responsiveness

Release notes: https://github.com/massgen/MassGen/releases/tag/v0.1.49

Feature highlights:

<!-- Paste feature-highlights.md content here -->
