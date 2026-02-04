# MassGen v0.1.47 Release Announcement

<!--
This is the current release announcement. Copy this + feature-highlights.md to LinkedIn/X.
After posting, update the social links below.
-->

## Release Summary

We're excited to release MassGen v0.1.47, adding Codex Backend Support! 🚀 OpenAI Codex CLI is now a fully supported backend with local and Docker execution, OAuth and API key authentication, and session persistence. A new NativeToolMixin provides shared native tool handling across CLI-based backends (Codex and Claude Code). Plus: TUI theme system refactored to palette-based architecture and per-agent voting sensitivity.

## Install

```bash
pip install massgen==0.1.47
```

## Links

- **Release notes:** https://github.com/massgen/MassGen/releases/tag/v0.1.47
- **X post:** [TO BE ADDED AFTER POSTING]
- **LinkedIn post:** [TO BE ADDED AFTER POSTING]

---

## Full Announcement (for LinkedIn)

Copy everything below this line, then append content from `feature-highlights.md`:

---

We're excited to release MassGen v0.1.47, adding Codex Backend Support! 🚀 OpenAI Codex CLI is now a fully supported backend with local and Docker execution, OAuth and API key authentication, and session persistence. A new NativeToolMixin provides shared native tool handling across CLI-based backends (Codex and Claude Code). Plus: TUI theme system refactored to palette-based architecture, per-agent voting sensitivity, and bug fixes.

**Key Features:**

**Codex Backend** - New `codex` backend type for OpenAI Codex CLI:
- Local and Docker execution modes with workspace mounting
- OAuth and API key authentication with session persistence
- Custom and workflow MCP servers for exposing MassGen tools to CLI-based backends
- NativeToolMixin abstract mixin shared between Codex and Claude Code

**TUI Theme Refactoring** - Palette-based architecture with unified base styles:
- Semantic CSS variables for consistent cross-component theming
- Theme palette files for dark, light, Catppuccin Latte, and Catppuccin Mocha variants

**Per-agent Voting Sensitivity** - Per-agent override for voting evaluation criteria (strict/balanced/lenient)

**Claude Code Backend Refactored** - Now uses NativeToolMixin with native filesystem support and OS-level sandbox

Release notes: https://github.com/massgen/MassGen/releases/tag/v0.1.47

Feature highlights:

<!-- Paste feature-highlights.md content here -->
