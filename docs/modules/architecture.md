# Architecture

## Core Flow

```text
cli.py -> orchestrator.py -> chat_agent.py -> backend/*.py
                |
        coordination_tracker.py (voting, consensus)
                |
        mcp_tools/ (tool execution)
```

## Key Components

**Orchestrator** (`orchestrator.py`): Central coordinator managing parallel agent execution, voting, and consensus detection. Handles coordination phases: initial_answer -> enforcement (voting) -> presentation.

**Backends** (`backend/`): Provider-specific implementations. All inherit from `base.py`. Add new backends by:
1. Create `backend/new_provider.py` inheriting from base
2. Register in `backend/__init__.py`
3. Add model mappings to `massgen/utils.py`
4. Add capabilities to `backend/capabilities.py`
5. Update `config_validator.py`

See also: [Backend Registration Checklist in CLAUDE.md Memory](../../CLAUDE.md)

**MCP Integration** (`mcp_tools/`): Model Context Protocol for external tools. `client.py` handles multi-server connections, `security.py` validates operations. Some tools have dual paths: SDK (in-process, for ClaudeCode) and stdio (config.toml-based, for Codex). **Stdio MCP servers run inside Docker where `massgen` is NOT installed** — never import from `massgen` in stdio servers. Pre-compute any needed values in the orchestrator and pass via JSON specs files. Also note Codex sometimes sends tool args as JSON strings instead of dicts — always add a `json.loads()` fallback.

**Streaming Buffer** (`backend/_streaming_buffer_mixin.py`): Tracks partial responses during streaming for compression recovery.

## Backend Hierarchy

```text
base.py (abstract interface)
    +-- base_with_custom_tool_and_mcp.py (tool + MCP support)
            |-- response.py (OpenAI Response API)
            |-- chat_completions.py (generic OpenAI-compatible)
            |-- claude.py (Anthropic)
            |-- claude_code.py (Claude Code SDK)
            |-- gemini.py (Google)
            +-- grok.py (xAI)
```

## Agent Statelessness and Anonymity

Agents are STATELESS and ANONYMOUS across coordination rounds. Each round:
- Agent gets a fresh LLM invocation with no memory of previous rounds
- Agent does not know which agent it is (all identities are anonymous)
- Cross-agent information (answers, workspaces) is presented anonymously
- System prompts and branch names must NOT reveal agent identity or round history

## TUI Design Principles

**Timeline Chronology Rule**: Tool batching MUST respect chronological order. Tools should ONLY be batched when they arrive consecutively with no intervening content (thinking, text, status). When non-tool content arrives, any pending batch must be finalized before the content is added, and the next tool starts a fresh batch.

This is enforced via `ToolBatchTracker.mark_content_arrived()` in `content_handlers.py`, which is called whenever non-tool content is added to the timeline.
