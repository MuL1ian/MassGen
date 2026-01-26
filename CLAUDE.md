# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

## Planning
When planning or creating specs, use AskUserQuestions to ensure you align with the user before creating full planning files.

## Debugging Assumptions

**IMPORTANT**: When the user asks you to check logs from a MassGen run, assume they ran with the current uncommitted changes unless they explicitly say otherwise. Do NOT assume "the run used an older commit" just because the execution_metadata.yaml shows a different git commit - the user likely ran with local modifications after you suggested changes. Always debug the actual code behavior first.

## Project Overview

MassGen is a multi-agent system that coordinates multiple AI agents to solve complex tasks through parallel processing, intelligence sharing, and consensus building. Agents work simultaneously, observe each other's progress, and vote to converge on the best solution.

## Essential Commands

All commands use `uv run` prefix:

```bash
# Run tests
uv run pytest massgen/tests/                           # All tests
uv run pytest massgen/tests/test_specific.py -v        # Single test file
uv run pytest massgen/tests/test_file.py::test_name -v # Single test

# Run MassGen (ALWAYS use --automation for programmatic execution)
uv run massgen --automation --config [config.yaml] "question"

# Build documentation
cd docs && make html                    # Build docs
cd docs && make livehtml                # Auto-reload dev server at localhost:8000

# Pre-commit checks
uv run pre-commit run --all-files

# Validate all configs
uv run python scripts/validate_all_configs.py

# Build Web UI (required after modifying webui/src/*)
cd webui && npm run build
```

## Architecture Overview

### Core Flow
```text
cli.py → orchestrator.py → chat_agent.py → backend/*.py
                ↓
        coordination_tracker.py (voting, consensus)
                ↓
        mcp_tools/ (tool execution)
```

### Key Components

**Orchestrator** (`orchestrator.py`): Central coordinator managing parallel agent execution, voting, and consensus detection. Handles coordination phases: initial_answer → enforcement (voting) → presentation.

**Backends** (`backend/`): Provider-specific implementations. All inherit from `base.py`. Add new backends by:
1. Create `backend/new_provider.py` inheriting from base
2. Register in `backend/__init__.py`
3. Add model mappings to `massgen/utils.py`
4. Add capabilities to `backend/capabilities.py`
5. Update `config_validator.py`

**MCP Integration** (`mcp_tools/`): Model Context Protocol for external tools. `client.py` handles multi-server connections, `security.py` validates operations.

**Streaming Buffer** (`backend/_streaming_buffer_mixin.py`): Tracks partial responses during streaming for compression recovery.

### Backend Hierarchy
```text
base.py (abstract interface)
    └── base_with_custom_tool_and_mcp.py (tool + MCP support)
            ├── response.py (OpenAI Response API)
            ├── chat_completions.py (generic OpenAI-compatible)
            ├── claude.py (Anthropic)
            ├── claude_code.py (Claude Code SDK)
            ├── gemini.py (Google)
            └── grok.py (xAI)
```

### TUI Design Principles

**Timeline Chronology Rule**: Tool batching MUST respect chronological order. Tools should ONLY be batched when they arrive consecutively with no intervening content (thinking, text, status). When non-tool content arrives, any pending batch must be finalized before the content is added, and the next tool starts a fresh batch.

This is enforced via `ToolBatchTracker.mark_content_arrived()` in `content_handlers.py`, which is called whenever non-tool content is added to the timeline.

## Configuration

YAML configs in `massgen/configs/` define agent setups. Structure:
- `basic/` - Simple single/multi-agent configs
- `tools/` - MCP, filesystem, code execution configs
- `providers/` - Provider-specific examples
- `teams/` - Pre-configured specialized teams

When adding new YAML parameters, update **both**:
- `massgen/backend/base.py` → `get_base_excluded_config_params()`
- `massgen/api_params_handler/_api_params_handler_base.py` → `get_base_excluded_config_params()`

## Workflow Guidelines

1. **Prioritize specs and TDD** - Write tests before implementation for complex features
2. **Keep PR_DRAFT.md updated** - Create a PR_DRAFT.md that references each new feature with corresponding Linear (e.g., `Closes MAS-XXX`) and GitHub issue numbers. Keep this updated as new features are added. You may need to ask the user whether to overwrite or append to this file. Ensure you include test cases here as well as configs used to test them.
3. **Review PRs** with `pr-checks` skill.
4. **Git staging**: Use `git add -u .` for modified tracked files

## Documentation Requirements

Documentation must be **consistent with implementation**, **concise**, and **usable**.

### What to Update (per PR)

| Change Type | Required Documentation |
|-------------|----------------------|
| New features | `docs/source/user_guide/` RST with runnable commands and expected output |
| New YAML params | `docs/source/reference/yaml_schema.rst` |
| New models | `massgen/backend/capabilities.py` + `massgen/token_manager/token_manager.py` |
| Complex/architectural | Design doc in `docs/dev_notes/` with architecture diagrams |
| New config options | Example YAML in `massgen/configs/` |
| Breaking changes | Migration guide |

### What to Update (release PRs only)

For release PRs on `dev/v0.1.X` branches (e.g., `dev/v0.1.33`):
- `README.md` - Recent Achievements section
- `CHANGELOG.md` - Full release notes

### Documentation Quality Standards

**Consistency**: Parameter names, file paths, and behavior descriptions must match actual code. Flag any discrepancies.

**Usability**:
- Include runnable commands users can try immediately
- Provide architecture diagrams for complex features
- Show expected output so users know what to expect

**Conciseness**:
- Avoid bloated prose and over-documentation
- One clear explanation beats multiple redundant ones
- Remove filler text and unnecessary verbosity

### File Locations

- **Internal** (not published): `docs/dev_notes/[feature-name]_design.md`
- **User guides**: `docs/source/user_guide/`
- **Reference**: `docs/source/reference/`
- **API docs**: Auto-generate from Google-style docstrings

## Registry Updates

### When Adding New Models

1. **Always update** `massgen/backend/capabilities.py`:
   - Add to `models` list (newest first)
   - Add to `model_release_dates`
   - Update `supported_capabilities` if new features

2. **Check LiteLLM first** before adding to `token_manager.py`:
   - If model is in LiteLLM database, no pricing update needed
   - Only add to `PROVIDER_PRICING` if missing from LiteLLM
   - Use correct provider casing: `"OpenAI"`, `"Anthropic"`, `"Google"`, `"xAI"`

3. **Regenerate docs**: `uv run python docs/scripts/generate_backend_tables.py`

### When Adding New YAML Parameters

Update **both** files to exclude from API passthrough:
- `massgen/backend/base.py` → `get_base_excluded_config_params()`
- `massgen/api_params_handler/_api_params_handler_base.py` → `get_base_excluded_config_params()`

## CodeRabbit Integration

This project uses CodeRabbit for automated PR reviews. Configuration: `.coderabbit.yaml`

### Claude Code CLI Integration

CodeRabbit integrates directly with Claude Code via CLI. After implementing a feature, run:

```bash
coderabbit --prompt-only
```

This provides token-efficient review output. Claude Code will create a task list from detected issues and can apply fixes systematically.

**Options**:
- `--type uncommitted` - Review only uncommitted changes
- `--type committed` - Review only committed changes
- `--base develop` - Specify comparison branch

**Workflow example**: Ask Claude to implement and review together:
> "Implement the new config option and then run coderabbit --prompt-only"

### PR Commands (GitHub/GitLab)

In PR comments:
- `@coderabbitai review` - Trigger incremental review
- `@coderabbitai resolve` - Mark all comments as resolved
- `@coderabbitai summary` - Regenerate PR summary

### Applying Suggestions

- **Committable suggestions**: Click "Commit suggestion" button on GitHub
- **Complex fixes**: Hand off to Claude Code or address manually

## Custom Tools

Tools in `massgen/tool/` require `TOOL.md` with YAML frontmatter:
```yaml
---
name: tool-name
description: One-line description
category: primary-category
requires_api_keys: [OPENAI_API_KEY]  # or []
tasks:
  - "Task this tool can perform"
keywords: [keyword1, keyword2]
---
```

Docker execution mode auto-excludes tools missing required API keys.

## Testing Notes

- Mark expensive API tests with `@pytest.mark.expensive`
- Use `@pytest.mark.docker` for Docker-dependent tests
- Async tests use `@pytest.mark.asyncio`
- **API Keys**: Use `python-dotenv` to load API keys from `.env` file in test scripts:
  ```python
  from dotenv import load_dotenv
  load_dotenv()  # Load before importing os.getenv()
  ```

### Integration Testing Across Backends

When creating integration tests that involve backend functionality (hooks, tool execution, streaming, compression, etc.), **test across all 5 standard backends**:

| Backend | Type | Model | API Style |
|---------|------|-------|-----------|
| Claude | `claude` | `claude-haiku-4-5-20251001` | anthropic |
| OpenAI | `openai` | `gpt-4o-mini` | openai |
| Gemini | `gemini` | `gemini-3-flash-preview` | gemini |
| OpenRouter | `chatcompletion` | `openai/gpt-4o-mini` | openai |
| Grok | `grok` | `grok-3-mini` | openai |

**Reference scripts**:
- `scripts/test_hook_backends.py` - Hook framework integration tests
- `scripts/test_compression_backends.py` - Context compression tests

**Integration test pattern**:
```python
BACKEND_CONFIGS = {
    "claude": {"type": "claude", "model": "claude-haiku-4-5-20251001"},
    "openai": {"type": "openai", "model": "gpt-4o-mini"},
    "gemini": {"type": "gemini", "model": "gemini-3-flash-preview"},
    "openrouter": {"type": "chatcompletion", "model": "openai/gpt-4o-mini", "base_url": "..."},
    "grok": {"type": "grok", "model": "grok-3-mini"},
}
```

Use `--verbose` flag to show detailed output (injection content, message formats, etc.).

## Key Files for New Contributors

- Entry point: `massgen/cli.py`
- Coordination logic: `massgen/orchestrator.py`
- Agent implementation: `massgen/chat_agent.py`
- Backend interface: `massgen/backend/base.py`
- Config validation: `massgen/config_validator.py`
- Model registry: `massgen/utils.py`

## MassGen Skills

MassGen includes specialized skills in `massgen/skills/` for common workflows (log analysis, running experiments, creating configs, etc.).

### Enabling Skill Discovery

If MassGen skills aren't being discovered, symlink them to `.claude/skills/`:

```bash
mkdir -p .claude/skills
for skill in massgen/skills/*/; do
  ln -sf "../../$skill" ".claude/skills/$(basename "$skill")"
done

# Also symlink the skill-creator for creating new skills
ln -sf "../.agent/skills/skill-creator" ".claude/skills/skill-creator"
```

Once symlinked, Claude Code will automatically discover and use these skills when relevant.

### Creating New Skills

When you notice a repeatable workflow emerging (e.g., same sequence of steps done multiple times), suggest creating a new skill for it. Use the `skill-creator` skill to help structure and create new skills in `massgen/skills/`.

### Improving Existing Skills
After you finish a workflow using a skill, it is a good idea to improve it, especially if a human has guided you through new workflows or you found other errors or inefficiencies. You should edit the file in `massgen/skills/` to improve it and have the human approve it.

## Linear Integration

This project uses Linear for issue tracking.

### Setup (if Linear tools unavailable)

If `mcp__linear-server__*` tools aren't available:

```bash
claude mcp add --transport http linear-server https://mcp.linear.app/mcp
```

### Feature Workflow

1. **Create Linear issue first** → `mcp__linear-server__create_issue`
2. **For significant changes** → Create OpenSpec proposal referencing the issue
3. **Implement** → Reference issue ID in commits
4. **Update status** → `mcp__linear-server__update_issue`

This ensures features are tracked in Linear and spec'd via OpenSpec before implementation.

*Note*: When using Linear, ensure you use the MassGen project and prepend '[FEATURE]', '[DOCS]', '[BUG]', or '[ROADMAP]' to the issue name. By default, set issues as 'Todo'.

## Release Workflow

### Automated (GitHub Actions)

| Trigger | Action | Workflow |
|---------|--------|----------|
| Git tag push | GitHub Release created | `auto-release.yml` |
| GitHub Release published | PyPI publish | `pypi-publish.yml` |
| Git tag push | Docker images built | `docker-publish.yml` |
| Git tag push | Docs validated | `release-docs-automation.yml` |

### Release Preparation

Use the `release-prep` skill to automate release documentation:

```bash
release-prep v0.1.34
```

This will:
1. Archive previous announcement → `docs/announcements/archive/`
2. Generate CHANGELOG.md entry draft
3. Create `docs/announcements/current-release.md`
4. Validate documentation is updated
5. Check LinkedIn character count (~3000 limit)

### Announcement Files

```text
docs/announcements/
├── feature-highlights.md    # Long-lived feature list (update for major features)
├── current-release.md       # Active announcement (copy to LinkedIn/X)
└── archive/                 # Past announcements
```

### Full Release Process

1. **Merge release PR** to main
2. **Run `release-prep v0.1.34`** - generates CHANGELOG, announcement
3. **Review and commit** announcement files
4. **Create git tag**: `git tag v0.1.34 && git push origin v0.1.34`
5. **Publish GitHub Release** - triggers PyPI publish automatically
6. **Post to LinkedIn/X** - copy from `docs/announcements/current-release.md` + `feature-highlights.md`
7. **Update links** in `current-release.md` after posting