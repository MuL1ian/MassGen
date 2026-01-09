# MassGen v0.1.36 Release Announcement

<!--
This is the current release announcement. Copy this + feature-highlights.md to LinkedIn/X.
After posting, update the social links below.
-->

## Release Summary

We're excited to release MassGen v0.1.36, adding @path Context Handling & Hook Framework!

Reference files inline with `@path` syntax - just type `@` to trigger an autocomplete file picker (like Claude Code). Extend agent behavior with PreToolUse/PostToolUse hooks for permission validation, content injection, and custom processing. Plus: Claude Code native hooks integration and improved Docker resource management.

## Install

```bash
pip install massgen==0.1.36
```

## Links

- **Release notes:** https://github.com/massgen/MassGen/releases/tag/v0.1.36
- **X post:** [TO BE ADDED AFTER POSTING]
- **LinkedIn post:** [TO BE ADDED AFTER POSTING]

---

## Full Announcement (for LinkedIn)

Copy everything below this line, then append content from `feature-highlights.md`:

---

We're excited to release MassGen v0.1.36, adding @path Context Handling & Hook Framework!🚀 Reference files inline with `@path` syntax - just type `@` to trigger an autocomplete file picker (like Claude Code). Extend agent behavior with PreToolUse/PostToolUse hooks for permission validation, content injection, and custom processing. Plus: Claude Code native hooks integration and improved Docker resource management.

**Key Features:**

**@path Context Handling** - Inline context path references:
- Type `@` in CLI for autocomplete file picker popup
- `@path` (read), `@path:w` (write), `@dir/` (directory)
- Context accumulation across turns
- Deferred agent creation - Docker launches once with all paths

**Hook Framework** - General hook framework for agent lifecycle events:
- PreToolUse hooks for permission validation and argument modification
- PostToolUse hooks for content injection (tool_result or user_message strategies)
- Built-in MidStreamInjectionHook for cross-agent updates without losing work
- Custom Python callable hooks with glob-style pattern matching
- Configurable fail-open/fail-closed error handling

**Claude Code Integration** - Native hooks support for Claude Code workflows

Release notes: https://github.com/massgen/MassGen/releases/tag/v0.1.36

Feature highlights:

<!-- Paste feature-highlights.md content here -->
