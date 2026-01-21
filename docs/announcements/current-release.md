# MassGen v0.1.41 Release Announcement

<!--
This is the current release announcement. Copy this + feature-highlights.md to LinkedIn/X.
After posting, update the social links below.
-->

## Release Summary

We're excited to release MassGen v0.1.41, adding Async Subagent Execution! 🚀 Parent agents can now spawn subagents in the background with `async_=True` and continue working while waiting for results. When subagents complete, their results are automatically injected into the parent's context. Plus, you can now resume any subagent (completed, timed-out, or failed) with `continue_subagent` to continue its work with preserved conversation context.

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

Spawn background subagents with `async_=True` - the parent keeps working while subagents run in parallel. Results automatically inject when complete. Resume any subagent (even timed-out ones) with `continue_subagent`.

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
- Automatic result injection via PostToolUse hooks
- Configurable injection strategies (tool_result/user_message)
- Subagent continuation for resuming work

Release notes: https://github.com/massgen/MassGen/releases/tag/v0.1.41

<!-- Paste feature-highlights.md content here -->
