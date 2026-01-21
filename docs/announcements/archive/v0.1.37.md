# MassGen v0.1.37 Release Announcement

<!--
This is the current release announcement. Copy this + feature-highlights.md to LinkedIn/X.
After posting, update the social links below.
-->

## Release Summary

We're excited to release MassGen v0.1.37, adding Execution Traces & Thinking Mode Improvements!🚀

Agents now preserve their full execution history as searchable markdown files, enabling compression recovery and cross-agent coordination. When context gets compressed, agents can read their trace files to recover details. Other agents can access execution traces to understand how solutions were reached. Plus: Claude Code and Gemini thinking mode improvements, standardized agent labeling, and OpenRouter documentation.

## Install

```bash
pip install massgen==0.1.37
```

## Links

- **Release notes:** https://github.com/massgen/MassGen/releases/tag/v0.1.37
- **X post:** [TO BE ADDED AFTER POSTING]
- **LinkedIn post:** [TO BE ADDED AFTER POSTING]

---

## Full Announcement (for LinkedIn)

Copy everything below this line, then append content from `feature-highlights.md`:

---

We're excited to release MassGen v0.1.37, adding Execution Traces & Thinking Mode Improvements!🚀

Agents now preserve their full execution history as searchable markdown files, enabling compression recovery and cross-agent coordination. When context gets compressed, agents can read their trace files to recover details. Other agents can access execution traces to understand how solutions were reached. Plus: Claude Code and Gemini thinking mode improvements, standardized agent labeling, and OpenRouter documentation.

**Key Features:**

**Execution Traces** - Full execution history preservation:
- Human-readable `execution_trace.md` saved alongside agent snapshots
- Compression recovery - agents read trace files to recover detailed history
- Cross-agent access - other agents can see how solutions were reached
- Full tool calls, results, and reasoning blocks without truncation
- Grep-friendly searchable format for debugging

**Thinking Mode Improvements** - Enhanced reasoning support:
- Claude Code thinking mode with streaming buffer integration
- Gemini thinking mode fixes for proper reasoning capture
- Voting execution traces with full vote context

**Standardized Agent Labeling** - Consistent identification:
- Unified labeling format across all backends
- Improved workspace anonymization for cross-agent sharing

Release notes: https://github.com/massgen/MassGen/releases/tag/v0.1.37

Feature highlights:

<!-- Paste feature-highlights.md content here -->
