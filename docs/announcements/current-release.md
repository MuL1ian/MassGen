# MassGen v0.1.49 Release Announcement

<!--
This is the current release announcement. Copy this + feature-highlights.md to LinkedIn/X.
After posting, update the social links below.
-->

## Release Summary

We're excited to release MassGen v0.1.49, focused on Coordination Quality! 🚀 Fairness gate prevents fast agents from dominating, persona easing softens agent approaches after seeing peers, and checklist voting brings structured quality evaluation. Plus: ROI-based iteration framework, automated testing infrastructure, skills modal, and bug fixes.

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

We're excited to release MassGen v0.1.49, focused on Coordination Quality! 🚀 Fairness gate prevents fast agents from dominating, persona easing softens agent approaches after seeing peers, and checklist voting brings structured quality evaluation. Plus: ROI-based iteration framework, automated testing infrastructure, and bug fixes.

**Key Features:**

**Fairness Gate** - Balanced multi-agent coordination:
- Prevents fast agents from dominating rounds with configurable `fairness_lead_cap_answers`
- `max_midstream_injections_per_round` controls injection frequency
- Ensures all agents contribute meaningfully regardless of speed

**Persona Easing** - Smarter agent adaptation:
- Auto-generated diverse agent personas via expanded `persona_generator.py`
- Personas soften after seeing peer solutions, reducing rigidity
- Agents converge on quality without losing creative diversity

**Checklist Voting** - Structured quality evaluation:
- New `checklist_tools_server.py` MCP server for objective quality assessment
- Binary pass/fail scoring replaces subjective voting
- Consistent, repeatable evaluation across coordination rounds

**ROI-Based Iteration Framework** - Budget-aware quality:
- 5-dimension rubric: correctness, depth, robustness, polish, testing
- Quality bars adapt to available budget and iteration count

**Automated Testing Infrastructure** - CI/CD and snapshot testing:
- GitHub Actions workflow (`tests.yml`) for automated test execution
- SVG snapshot baselines for TUI visual regression testing
- 16+ new test files with comprehensive testing strategy

**Bug Fixes:**
- Fixed "[No response generated]" shadow agent errors (PR #861)
- Round banner timing, hook injection, final answer lock responsiveness

Release notes: https://github.com/massgen/MassGen/releases/tag/v0.1.49

Feature highlights:

<!-- Paste feature-highlights.md content here -->
