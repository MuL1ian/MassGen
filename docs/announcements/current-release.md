# MassGen v0.1.41 Release Announcement

<!--
This is the current release announcement. Copy this + feature-highlights.md to LinkedIn/X.
After posting, update the social links below.
-->

## Release Summary

We're excited to release MassGen v0.1.41, adding Async Subagent Execution! 🚀 Parent agents can now spawn subagents in the background with `async_=True` and continue working while waiting for results. The parent can poll for subagent completion and retrieve results when ready.

## Install

```bash
pip install massgen==0.1.41
```

## Links

- **Release notes:** https://github.com/massgen/MassGen/releases/tag/v0.1.41
- **X post:** [TO BE ADDED AFTER POSTING]
- **LinkedIn post:** [TO BE ADDED AFTER POSTING]

---

## Full Announcement (for LinkedIn)

Copy everything below this line, then append content from `feature-highlights.md`:

---

We're excited to release MassGen v0.1.41, adding Async Subagent Execution! 🚀

Spawn background subagents with `async_=True` - the parent keeps working while subagents run in parallel. Poll for completion when ready.

Example:
```json
{
  "tool": "spawn_subagents",
  "arguments": {
    "tasks": [{"task": "Research OAuth 2.0", "subagent_id": "oauth"}],
    "async_": true
  }
}
```

Key features:
- Non-blocking subagent execution
- Poll for subagent completion and retrieve results
- Configurable injection strategies (tool_result/user_message)

Release notes: https://github.com/massgen/MassGen/releases/tag/v0.1.41

<!-- Paste feature-highlights.md content here -->
