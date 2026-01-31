---
name: backend-integrator
description: Complete guide for integrating a new LLM backend into MassGen. Use when adding a new provider (e.g., Codex, Mistral, DeepSeek) or when auditing an existing backend for missing integration points. Covers all ~15 files that need touching.
---

# Backend Integrator

This skill provides the complete checklist and patterns for integrating a new LLM backend into MassGen. A full integration touches ~15 files across the codebase.

## When to Use This Skill

- Adding a new LLM provider/backend
- Auditing an existing backend for missing integration points
- Understanding what files to modify when extending backend capabilities

## Integration Architecture

```
Backend Type Decision:
  Stateless + OpenAI-compatible API   → subclass ChatCompletionsBackend
  Stateless + custom API              → subclass CustomToolAndMCPBackend
  Stateless + Response API format     → subclass ResponseBackend
  Stateful CLI wrapper (like Codex)   → subclass LLMBackend directly
  Stateful SDK wrapper (like Claude Code) → subclass LLMBackend directly
```

## Complete Checklist

### Phase 1: Core Implementation (3 files)

#### 1.1 Backend Class
**File**: `massgen/backend/<name>.py`

**Choose base class**:
- `LLMBackend` — bare minimum, you handle everything
- `CustomToolAndMCPBackend` — adds MCP + custom tool support (most common)
- `ChatCompletionsBackend` — for OpenAI-compatible APIs (inherits from above)
- `ResponseBackend` — for OpenAI Response API format

**Required methods**:
```python
async def stream_with_tools(self, messages, tools, **kwargs) -> AsyncGenerator[StreamChunk, None]:
    """Main streaming method. Yield StreamChunks."""

def get_provider_name(self) -> str:
    """Return provider name string (e.g., 'OpenAI', 'Codex')."""

def get_filesystem_support(self) -> FilesystemSupport:
    """Return NONE, NATIVE, or MCP."""
```

**StreamChunk types to yield**:
| Type | When | Key fields |
|------|------|------------|
| `"content"` | Text output | `content="..."` |
| `"tool_calls"` | Tool invocation | `tool_calls=[{id, name, arguments}]` |
| `"reasoning"` | Thinking/reasoning | `reasoning_delta="..."` |
| `"done"` | Stream complete | `usage={prompt_tokens, completion_tokens, total_tokens}` |
| `"error"` | Error occurred | `error="..."` |
| `"agent_status"` | Status update | `status="...", detail="..."` |

**Token tracking** — call one of:
```python
self._update_token_usage_from_api_response(usage_dict, model)  # If API returns usage
self._estimate_token_usage(messages, response_text, model)      # Fallback
```

**Timing** — call in stream_with_tools:
```python
self.start_api_call_timing(self.model)       # Before API call
self.record_first_token()                     # On first content chunk
self.end_api_call_timing(success=True/False)  # After completion
```

**For stateful backends** (CLI/SDK wrappers), also implement:
```python
def is_stateful(self) -> bool: return True
async def clear_history(self) -> None: ...
async def reset_state(self) -> None: ...
```

**Compression support** — inherit `StreamingBufferMixin` and call:
```python
self._clear_streaming_buffer(**kwargs)       # Start of stream
self._finalize_streaming_buffer(agent_id=id) # End of stream
```

#### 1.2 Formatter (if needed)
**File**: `massgen/formatter/<name>_formatter.py`

Only needed if the API uses a non-standard message/tool format (not OpenAI chat completions format). Subclass `FormatterBase` and implement `format_messages()`, `format_tools()`, `format_mcp_tools()`.

Existing formatters:
- `_claude_formatter.py` — Anthropic Messages API
- `_gemini_formatter.py` — Gemini API
- `_chat_completions_formatter.py` — OpenAI/generic (reuse for compatible APIs)

#### 1.3 API Params Handler (if needed)
**File**: `massgen/api_params_handler/<name>_api_params_handler.py`

Only needed if the backend calls an HTTP API and needs to filter/transform YAML config params before passing to the API. Subclass `APIParamsHandlerBase`.

CLI/SDK wrappers (Codex, Claude Code) typically don't need this — they build commands directly.

### Phase 2: Registration (4 files)

#### 2.1 Backend __init__.py
**File**: `massgen/backend/__init__.py`

```python
from .your_backend import YourBackend
# Add to __all__
```

#### 2.2 CLI Backend Mapping
**File**: `massgen/cli.py`

Add to `create_backend()` function:
```python
elif backend_type == "your_backend":
    api_key = kwargs.get("api_key") or os.getenv("YOUR_API_KEY")
    if not api_key:
        raise ConfigurationError(
            _api_key_error_message("YourBackend", "YOUR_API_KEY", config_path)
        )
    return YourBackend(api_key=api_key, **kwargs)
```

For CLI-based backends that don't need API keys, skip the key check.

#### 2.3 Capabilities Registry
**File**: `massgen/backend/capabilities.py`

Add entry to `BACKEND_CAPABILITIES`:
```python
"your_backend": BackendCapabilities(
    backend_type="your_backend",
    provider_name="YourProvider",
    supported_capabilities={"mcp", "web_search", ...},
    builtin_tools=["web_search"],  # Provider-native tools
    filesystem_support="mcp",      # "none", "mcp", or "native"
    models=["model-a", "model-b"], # Newest first
    default_model="model-a",
    env_var="YOUR_API_KEY",        # Or None
    notes="...",
    model_release_dates={"model-a": "2025-06"},
    base_url="https://api.example.com/v1",  # If applicable
)
```

#### 2.4 Config Validator (if needed)
**File**: `massgen/config_validator.py`

Add backend-specific validation to `_validate_backend()` if there are special rules (e.g., required params, incompatible combinations).

### Phase 3: Token Management (1 file)

#### 3.1 Pricing
**File**: `massgen/token_manager/token_manager.py`

**Check LiteLLM first** — only add to `PROVIDER_PRICING` if the model is NOT in the LiteLLM database. Provider name must match `get_provider_name()` exactly (case-sensitive).

### Phase 4: Excluded Params (2 files, if adding new YAML params)

#### 4.1 Base Class Exclusions
**File**: `massgen/backend/base.py` -> `get_base_excluded_config_params()`

#### 4.2 API Params Handler Exclusions
**File**: `massgen/api_params_handler/_api_params_handler_base.py` -> `get_base_excluded_params()`

Both must stay in sync. Add any new framework-level YAML params that should NOT be passed to the provider API.

### Phase 5: Authentication

#### 5.1 API Key Backends (standard)
Most backends use API keys. Set `env_var` in `capabilities.py` and add the key check in `cli.py`:
```python
# cli.py
api_key = kwargs.get("api_key") or os.getenv("YOUR_API_KEY")
if not api_key:
    raise ConfigurationError(...)
return YourBackend(api_key=api_key, **kwargs)
```

#### 5.2 OAuth / Subscription Auth (CLI/SDK wrappers)
For backends that support OAuth (like Codex, Claude Code), implement a multi-tier auth cascade:

```python
def __init__(self, api_key=None, **kwargs):
    # Tier 1: Explicit API key
    self.api_key = api_key or os.getenv("YOUR_API_KEY")
    # Tier 2: Check cached OAuth tokens
    self.use_oauth = not bool(self.api_key)
    self.auth_file = Path.home() / ".your_cli" / "auth.json"

async def _ensure_authenticated(self):
    if self.api_key:
        os.environ["YOUR_API_KEY"] = self.api_key
        return
    if self._has_cached_credentials():
        return
    # Tier 3: Initiate OAuth flow
    await self._initiate_oauth_flow()

async def _initiate_oauth_flow(self, use_device_flow=False):
    """Wrap the CLI's login command."""
    cmd = [self._cli_path, "login"]
    if use_device_flow:
        cmd.append("--device-auth")  # For headless/SSH
    proc = await asyncio.create_subprocess_exec(*cmd, ...)
```

**In `cli.py`**: Skip API key check — delegate auth to the backend:
```python
elif backend_type == "your_backend":
    # Auth handled by backend (API key or OAuth)
    return YourBackend(**kwargs)
```

**In `capabilities.py`**: Set `env_var` to the API key name (optional, not required for OAuth):
```python
env_var="YOUR_API_KEY",  # Optional - can use OAuth instead
notes="Works with subscription auth (via `your-cli login`) or YOUR_API_KEY."
```

*NOTE: We only offer oauth through supported SDKs or programmatic command line usage as suggested by the provider. We must find the accepted way of using oauth for each backend to ensure we are supporting it correctly (e.g., use the Claude Agent SDK, NOT Claude Code with API spoofing).*

#### 5.3 No Auth (local inference)
For local servers (LM Studio, vLLM, SGLang), set `env_var=None` in capabilities. No key check in `cli.py`.

**Reference implementations**:
- `codex.py` — Full OAuth with browser + device code flows
- `claude_code.py` — 3-tier: `CLAUDE_CODE_API_KEY` -> `ANTHROPIC_API_KEY` -> subscription login
- `lmstudio` / `vllm` / `sglang` — No auth (`env_var=None`)

### Phase 6: Custom Tools & MCP

#### 6.1 Standard Path (API backends)
If inheriting from `CustomToolAndMCPBackend`, MCP and custom tools work automatically:
- MCP servers from YAML `mcp_servers` config
- Custom tools from `custom_tools` / `custom_tools_path` config
- Filesystem MCP injected by `FilesystemManager` when `cwd` is set
- Tool execution handled by `ToolManager`

#### 6.2 Multimodal Tools (all backend types)
When `enable_multimodal_tools: true` is set, the backend must register `read_media` and `generate_media` custom tools. Use the shared helper in `massgen/backend/base.py`:

```python
from .base import get_multimodal_tool_definitions

# In __init__:
enable_multimodal = self.config.get("enable_multimodal_tools", False) or kwargs.get("enable_multimodal_tools", False)
if enable_multimodal:
    custom_tools.extend(get_multimodal_tool_definitions())
```

- **API backends** (`CustomToolAndMCPBackend` subclasses): handled automatically — base class calls `get_multimodal_tool_definitions()` and registers via `_register_custom_tools()`
- **CLI/SDK backends** (`LLMBackend` subclasses like Codex, Claude Code): must do this explicitly in `__init__`, then wrap as MCP server (see §6.4)

**Important**: Always use `get_multimodal_tool_definitions()` — never inline the tool dicts. This keeps the definitions in one place.

#### 6.3 CLI/SDK Wrappers — MCP Servers
These backends must configure the CLI/SDK's own MCP system:

**Codex**: Write project-scoped `.codex/config.toml` in the workspace (`-C` dir). Codex reads this automatically. Convert MassGen's `mcp_servers` list to TOML format:
```toml
[mcp_servers.filesystem]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
```

**Claude Code**: Pass `mcp_servers` dict directly to SDK options. The SDK handles server lifecycle:
```python
options = {"mcp_servers": {"filesystem": {"command": "npx", "args": [...]}}}
```

#### 6.4 CLI/SDK Wrappers — Custom Tools
Custom tools need special handling since the LLM runs inside an external process:

**Preferred: Wrap as MCP server** (what `claude_code.py` does):
1. Load custom tools via `ToolManager` (schemas + executors)
2. Create an MCP server that exposes each tool
3. Register the MCP server with the CLI/SDK
4. When the LLM calls the MCP tool, the wrapper executes via `ToolManager`

```python
# claude_code.py pattern (simplified)
def _create_sdk_mcp_server_from_custom_tools(self):
    tool_schemas = self._custom_tool_manager.fetch_tool_schemas()
    mcp_tools = []
    for schema in tool_schemas:
        name = schema["function"]["name"]
        async def wrapper(args, tool_name=name):
            return await self._execute_massgen_custom_tool(tool_name, args)
        mcp_tools.append(tool(name=name, ...)(wrapper))
    return create_sdk_mcp_server(name="massgen_custom_tools", tools=mcp_tools)
```

**For CLI wrappers without SDK MCP** (like Codex):
Use the shared `massgen/mcp_tools/custom_tools_server.py` utility. It creates a standalone fastmcp server that wraps ToolManager tools via stdio transport.

```python
from ..mcp_tools.custom_tools_server import build_server_config, write_tool_specs

def _setup_custom_tools_mcp(self, custom_tools):
    # 1. Write tool specs JSON to workspace
    specs_path = Path(self.cwd) / ".codex" / "custom_tool_specs.json"
    write_tool_specs(custom_tools, specs_path)

    # 2. Get MCP server config (fastmcp run ... --tool-specs ...)
    server_config = build_server_config(
        tool_specs_path=specs_path,
        allowed_paths=[self.cwd],
        agent_id="my_backend",
    )

    # 3. Add to mcp_servers list (written to workspace config before launch)
    self.mcp_servers.append(server_config)
```

The server is launched by the CLI as a subprocess and connects via stdio. Cleanup the specs file on `reset_state()`.

**Reference**: `codex.py` uses this pattern. `custom_tools_server.py` also provides `build_server_config()` which returns a ready-to-use MCP server dict.

**Fallback: System prompt injection**
- Describe tools as JSON schema in the system prompt
- Parse structured output (JSON blocks) for tool calls
- Only use when MCP wrapping isn't feasible

#### 6.5 Custom Tool YAML Config
```yaml
backend:
  type: your_backend
  custom_tools:
    - path: "massgen/tool/_basic"          # Directory with TOOL.md
      function: "two_num_tool"
    - path: "path/to/tool.py"             # Single file
      function: ["func_a", "func_b"]
      preset_args: [{"timeout": 30}, {}]
  custom_tools_path: "massgen/tool/"      # Auto-discover from directory
  auto_discover_custom_tools: true        # Discover from registry
```

**MassGen workflow tools** (new_answer, vote, etc.): Always injected via system prompt — these are coordination-level, not executable tools. See §6.7 for full details.

#### 6.7 Workflow Tool Integration (vote, new_answer, etc.)

Workflow tools are NOT native function-calling tools — they're injected into the system prompt and parsed from the model's text output. This pattern is shared between Claude Code and Codex backends.

**Shared helpers** in `massgen/backend/base.py`:
```python
from .base import build_workflow_instructions, parse_workflow_tool_calls, extract_structured_response

# build_workflow_instructions(tools) → str
#   Filters tools to workflow tools, returns instruction text with usage examples.
#   Returns "" if no workflow tools present.

# parse_workflow_tool_calls(text) → List[Dict]
#   Extracts JSON tool calls from text output.
#   Returns standard format: {id, type, function: {name, arguments}}

# extract_structured_response(text) → Optional[Dict]
#   Low-level: extracts {"tool_name": "...", "arguments": {...}} from text.
#   Tries: ```json blocks → regex → brace-matching → line-by-line.
```

**For API backends**: Workflow tools are passed as normal function tools — no injection needed.

**For CLI/SDK backends** (Codex, Claude Code): The model can't receive native function tool definitions, so:

1. **Build instructions**: Call `build_workflow_instructions(tools)` to get the instruction text
2. **Inject into system prompt**: Append to whatever mechanism the backend uses for system prompts
3. **Accumulate text output**: Track all `content` chunks during streaming
4. **Parse after streaming**: Call `parse_workflow_tool_calls(accumulated_text)` to extract tool calls
5. **Yield as done chunk**: `yield StreamChunk(type="done", tool_calls=workflow_tool_calls)`

**Codex-specific**: Instructions go into `AGENTS.md` at the workspace root (Codex auto-reads this). The orchestrator's system message is also extracted from messages and included, since Codex only receives a single user prompt via CLI — the system message from the orchestrator would otherwise be lost. This approach was utilized as the developer instructions approach wasn't working.

**Claude Code-specific**: Instructions are built by `_build_system_prompt_with_workflow_tools()` which also adds MCP command-line sections, then passed as `system_prompt` to the SDK.


#### 6.6 Provider-Native Tools: Keep vs. Override

CLI/SDK-based agents (Codex, Claude Code) come with their own built-in tools (file editing, shell execution, web search, sub-agents, etc.). When integrating, decide which to keep and which to override with MassGen equivalents.

**General rule**: Prefer the provider's native tools unless MassGen has a specific reason to override. Native tools are optimized for the provider's model and avoid extra MCP overhead.

**Override when MassGen adds value**:
- **Sub-agents/Task tools**: Override with MassGen's sub-agents — theirs can't participate in MassGen coordination (voting, consensus, intelligence sharing)
- **Filesystem tools**: May override if MassGen needs path permission enforcement or workspace isolation beyond what the provider offers

**Keep provider-native**:
- **File read/write/edit**: Provider tools are model-optimized
- **Shell/command execution**: Provider sandboxing is already configured
- **Web search**: Provider integration is usually seamless

**Implementation**: Use the provider's tool filtering mechanism to disable specific tools:

```python
# Codex: via .codex/config.toml
[mcp_servers.some_server]
disabled_tools = ["task", "sub_agent"]

# Claude Code: via SDK options
options = {
    "permissions": {
        "disallowed_tools": ["Task"],  # Disable Claude Code's Task tool
    }
}
```

**Document in capabilities.py** which native tools the backend provides:
```python
builtin_tools=["file_edit", "shell", "web_search", "sub_agent"],
notes="Native tools: file ops, shell, web search, sub-agents. Override sub-agents with MassGen's."
```

### Phase 7: Testing (2+ files)

#### 7.1 Capabilities Test
Automatically tested by `massgen/tests/test_backend_capabilities.py` once you add to capabilities.py.

```bash
uv run pytest massgen/tests/test_backend_capabilities.py -v
```

#### 7.2 Integration Test
**Create**: `massgen/tests/test_<name>_integration.py` or add to cross-backend test scripts.

Cross-backend test pattern:
```python
BACKEND_CONFIGS = {
    "claude": {"type": "claude", "model": "claude-haiku-4-5-20251001"},
    "openai": {"type": "openai", "model": "gpt-4o-mini"},
    "your_backend": {"type": "your_backend", "model": "model-a"},
}
```

#### 7.3 Config Validation
```bash
uv run python scripts/validate_all_configs.py
```

### Phase 8: Config Examples (2+ files)

#### 8.1 Single Agent
**Create**: `massgen/configs/providers/<name>/single_<name>.yaml`

#### 8.2 Multi-Agent / Tools
**Create**: `massgen/configs/providers/<name>/<name>_with_tools.yaml`

### Phase 9: Documentation (3+ files)

#### 9.1 YAML Schema
**File**: `docs/source/reference/yaml_schema.rst` — document backend-specific params

#### 9.2 Backend Tables
```bash
uv run python docs/scripts/generate_backend_tables.py
```

#### 9.3 User Guide
**File**: `docs/source/user_guide/backends.rst` — add section for new backend

## Common Patterns

### CLI Wrapper Backend (like Codex)
```
__init__: find CLI binary, set config defaults
stream_with_tools: build command -> spawn subprocess -> parse JSONL stdout -> yield StreamChunks
MCP: write project-scoped config file in workspace before launch
Custom tools: wrap as MCP server or inject via system prompt
Cleanup: remove workspace config on reset_state/clear_history
```

#### Docker Execution for CLI Backends
If a CLI-based backend doesn't support Docker natively, run the CLI inside the MassGen container:

1. Install the CLI in the Docker image (add to `npm install -g` in Dockerfile) or via `command_line_docker_packages.preinstall.npm`
2. In `__init__`, detect `command_line_execution_mode: "docker"` and skip host CLI lookup
3. In `stream_with_tools`, use `container.client.api.exec_create()` + `exec_start(stream=True)` to run the CLI inside the container
4. If the CLI has its own sandbox, disable it — the container provides isolation
5. If the CLI needs host credentials, mount them read-only via `_build_credential_mounts()`

**Reference**: `codex.py` implements this pattern with `_stream_docker()` / `_stream_local()` branching.

#### Docker MCP Path Resolution
MCP server configs are built by the orchestrator on the host with absolute host file paths (e.g., `fastmcp run /host/path/massgen/mcp_tools/planning/_server.py:create_server`). Inside Docker, these paths don't exist unless explicitly mounted.

**Solution**: `_docker_manager.py` bind-mounts the `massgen/` package directory into the container at the same host path (read-only). This makes host-path-based MCP configs work as-is inside the container, using the latest source from the host rather than stale pip-installed modules.

#### Shell Sandboxing for Backends with Native Tools
**This section applies only to backends that bring their own shell/file tools** (e.g., CLI wrappers with built-in command execution). If a backend delegates all tool execution to MassGen's MCP servers, MassGen's `PathPermissionManager` handles sandboxing automatically.

When the backend has its own tools that can access the filesystem or run commands, you must map MassGen's permission model to the backend's sandbox mechanism:

| MassGen concept | Expected access |
|---|---|
| Workspace | Write |
| Temp workspaces | Read-only |
| Read context paths | Read-only |
| Write context paths | Write — must be explicitly granted in backend sandbox config |

The workspace is typically writable by default. Read access to the full filesystem is usually allowed. The key task is ensuring write context paths are added to the backend's writable allowlist (e.g., `sandbox_workspace_write.writable_roots` for Codex, `allowed_directories` for Claude Code).

**Docker mode**: Skip backend sandbox config — the container IS the sandbox. Grant full access inside the container.

### SDK Wrapper Backend (like Claude Code)
```
__init__: import SDK, configure options
stream_with_tools: call SDK with messages -> iterate events -> yield StreamChunks
MCP: pass mcp_servers dict to SDK options
Custom tools: create SDK MCP server from tool definitions
State: SDK manages conversation state internally
```

### API Backend (like Claude, Gemini)
```
Subclass CustomToolAndMCPBackend or ChatCompletionsBackend
Implement formatter if non-standard API format
Implement API params handler to filter/transform config -> API params
MCP + custom tools handled automatically by base class
```

## Reference Backends by Complexity

| Backend | Lines | Type | Good reference for |
|---------|-------|------|--------------------|
| `grok.py` | ~80 | Subclass of ChatCompletions | Minimal API backend |
| `chat_completions.py` | ~500 | OpenAI-compatible | Standard API backend |
| `codex.py` | ~500 | CLI wrapper | CLI-based backend |
| `response.py` | ~600 | Response API | Reasoning models |
| `gemini.py` | ~800 | Custom API | Non-OpenAI API |
| `claude_code.py` | ~1700 | SDK wrapper | Full-featured stateful |
| `claude.py` | ~1700 | Custom API | Full-featured API |

## File Summary

| # | File | Required? | Purpose |
|---|------|-----------|---------|
| 1 | `massgen/backend/<name>.py` | Yes | Core backend |
| 2 | `massgen/formatter/<name>_formatter.py` | If non-standard API | Message/tool formatting |
| 3 | `massgen/api_params_handler/<name>_handler.py` | If HTTP API | Param filtering |
| 4 | `massgen/backend/__init__.py` | Yes | Export |
| 5 | `massgen/cli.py` | Yes | Backend creation |
| 6 | `massgen/backend/capabilities.py` | Yes | Model registry |
| 7 | `massgen/config_validator.py` | If special rules | Validation |
| 8 | `massgen/token_manager/token_manager.py` | If not in LiteLLM | Pricing |
| 9 | `massgen/backend/base.py` | If new YAML params | Excluded params |
| 10 | `massgen/api_params_handler/_base.py` | If new YAML params | Excluded params |
| 11 | `massgen/tests/test_*` | Yes | Tests |
| 12 | `massgen/configs/providers/<name>/` | Yes | Example configs |
| 13 | `docs/source/reference/yaml_schema.rst` | Yes | Schema docs |
| 14 | `docs/source/user_guide/backends.rst` | Yes | User guide |
| 15 | `docs/scripts/generate_backend_tables.py` | Run it | Regenerate tables |
