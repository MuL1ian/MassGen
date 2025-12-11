# Claude Programmatic Tool Calling & Tool Search

Concise reference for enabling Claude's advanced tool behaviors: programmatic tool calling (code execution invoking tools) and deferred tool discovery via tool search.

## Model & API Requirements
- Supported models: `claude-opus-4-5`, `claude-sonnet-4-5` (or variants containing those strings). Unsupported models auto-disable these flags and expose all tools normally (massgen/backend/claude.py).
- Enabling either feature adds Anthropic betas: `advanced-tool-use-2025-11-20`; `code-execution-2025-08-25` is added when code execution is on; Files API beta is added only when file uploads are present (_claude_api_params_handler.py).
- `enable_programmatic_flow` automatically flips `enable_code_execution` on so a code sandbox exists before tools can be called from code.

## Programmatic Tool Calling (code -> tools)
- Turn on via backend flag:

```yaml
backend:
  type: "claude"
  model: "claude-sonnet-4-5-20250929"
  enable_programmatic_flow: true
  # enable_code_execution is implied when missing
```

- The params handler attaches `allowed_callers: [code_execution_20250825]` to every custom + MCP tool so they can be invoked from within Claude's code_execution sandbox. Provider tools (web_search, code_execution) remain callable directly.
- Streaming cues from `massgen/backend/claude.py`: `?? [Programmatic Flow] Enabled...` on the first turn, and `?? [Programmatic] Tool '<name>' called from code execution` whenever a tool is triggered programmatically.
- Example config: `massgen/configs/providers/claude/programmatic_with_two_tools.yaml` (custom math tool + MCP weather server).

## Tool Search (deferred tool loading)
- Turn on via backend flags:

```yaml
backend:
  type: "claude"
  model: "claude-sonnet-4-5-20250929"
  enable_tool_search: true
  tool_search_variant: "bm25"  # default is "regex"
```

- The params handler adds the server-side search tool `tool_search_tool_<variant>_20251119` and marks all custom + MCP tools with `defer_loading: true` unless you override a tool/server with `defer_loading: false` (visible up front). Deferred/visible lists are logged for traceability.
- During streaming (`massgen/backend/claude.py`):
  - First turn emits `?? [Tool Search] Enabled (<variant>)...`.
  - Server tool blocks show `?? [Tool Search] Searching for tools (<variant>)...`, followed by `?? [Search Query] '<query>'` and `? [Tool Search] Completed - tools discovered` when discovery finishes.
- Example config: `massgen/configs/providers/claude/tool_search_example.yaml` (mix of visible/deferred custom tools and MCP servers, variant bm25).

## Using Both Together
- You can enable both flags; both are validated against the model list above and share the `advanced-tool-use-2025-11-20` beta. Programmatic flow still forces code execution on, and tool search still controls which tools start deferred vs visible.
- Good default starter:

```yaml
backend:
  type: "claude"
  model: "claude-sonnet-4-5-20250929"
  enable_programmatic_flow: true
  enable_tool_search: true
  tool_search_variant: "regex"  # or "bm25" for semantic matching
  custom_tools:
    - name: "two_num_tool"
      path: "massgen/tool/_basic/_two_num_tool.py"
      function: "two_num_tool"
      defer_loading: false  # keep visible
  mcp_servers:
    - name: "weather"
      type: "stdio"
      command: "npx"
      args: ["-y", "@fak111/weather-mcp"]
      defer_loading: false
```

## Where the behavior lives
- Validation + streaming markers: `massgen/backend/claude.py` (programmatic/tool search gating, log_stream_chunk output, event handling for server_tool_use/tool_search).
- API parameter wiring: `massgen/api_params_handler/_claude_api_params_handler.py` (beta injection, provider tool registration, allowed_callers/defer_loading handling).
