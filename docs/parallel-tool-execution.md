# Parallel Tool Execution Configuration

Quick guide for configuring model-level tool calling and local execution parallelism.

## Core Knobs

### 1. `parallel_tool_calls` (OpenAI Response API)
**What it controls:** How many tool calls the **model emits** in a single assistant turn.

- **Model behavior, not execution behavior** - controls whether the model can request multiple tools in one response
- Defaults to `true` for OpenAI Response API

```yaml
agents:
  - id: "openai_agent"
    backend:
      type: "openai"
      model: "gpt-5"
      parallel_tool_calls: true  # Model can emit multiple tool calls per turn
```

---

### 2. `concurrent_tool_execution` (All Backends)
**What it controls:** Whether MassGen **executes** multiple tool calls in parallel locally (after receiving them from the model).

- Toggles MassGen's local asyncio scheduler
- When enabled, backends push pending custom + MCP tool calls through `_execute_tool_calls` with optional `max_concurrent_tools` cap (default `10`) (`massgen/backend/base_with_custom_tool_and_mcp.py:1084`)
- Works with Response, ChatCompletions, Gemini, and Claude backends

```yaml
agents:
  - id: "my_agent"
    backend:
      type: "openai"  # Works with any backend
      model: "gpt-5-nano"
      concurrent_tool_execution: true  # Execute tools in parallel locally
      max_concurrent_tools: 10  # Optional: semaphore limit (default: 10)
```

**Key distinction:**
- Model's `parallel_tool_calls` controls how many calls **arrive** at once
- `concurrent_tool_execution` controls how many MassGen **runs** simultaneously

---

### 3. `max_concurrent_tools` (All Backends)
Controls the asyncio semaphore limit for local tool execution.

- Only affects execution speed, not the model's ability to request multiple tools
- Default: `10`
- Only relevant when `concurrent_tool_execution: true`

---

### 4. `disable_parallel_tool_use` (Claude)
**What it controls:** Inverse toggle for Claude's tool calling behavior (similar to OpenAI's `parallel_tool_calls`).

- Set `disable_parallel_tool_use: true` to force single tool calls per turn
- Default : Claude can request multiple tools per turn
- Injected into `tool_choice.disable_parallel_tool_use` (`massgen/api_params_handler/_claude_api_params_handler.py:124`)

```yaml
agents:
  - id: "claude_agent"
    backend:
      type: "claude"
      model: "claude-sonnet-4-20250514"
      disable_parallel_tool_use: false
      concurrent_tool_execution: true   # Execute them in parallel locally
```

---

### 5. `function_calling_mode` (Gemini)
**What it controls:** Gemini's function calling intent (not parallelism).

- Maps to Google's `FunctionCallingConfig` (`massgen/api_params_handler/_gemini_api_params_handler.py:78`)
- Gemini's automatic execution is always disabled (`massgen/backend/gemini.py:447-452`) - MassGen handles execution

**Options:**
- `AUTO`: Model decides whether to call functions (default)
- `ANY`: Model must call at least one function
- `NONE`: Model cannot call functions

```yaml
agents:
  - id: "gemini_agent"
    backend:
      type: "gemini"
      model: "gemini-2.5-pro"
      function_calling_mode: "AUTO"
      concurrent_tool_execution: true  # Execute tools in parallel locally
```

---

## Backend Specifics

### OpenAI Response API
- Set `parallel_tool_calls` and `concurrent_tool_execution` in agent config (see `massgen/configs/tools/custom_tools/gpt5_nano_custom_tool_with_mcp_parallel.yaml:5-20`)
- Response handler forwards `parallel_tool_calls` (default `true`), then streams resulting tool calls to `_execute_tool_calls` for local execution
- `massgen/backend/response.py:453` aggregates custom + MCP calls and hands them to the shared executor

```yaml
agents:
  - id: "openai_parallel"
    backend:
      type: "openai"
      model: "gpt-5"
      parallel_tool_calls: true          # Model emits multiple calls per turn
      concurrent_tool_execution: true    # Execute them in parallel locally
      max_concurrent_tools: 5
```

### OpenAI Chat Completions / Compatible Providers
- Uses the same base executor path because `ChatCompletionsBackend` inherits from `CustomToolAndMCPBackend` (`massgen/backend/chat_completions.py:42`)
- Any `parallel_tool_calls` flag is passed directly to the provider (Chat Completions params handler does not override it)
- Combine with `concurrent_tool_execution` to control local execution

```yaml
agents:
  - id: "groq_parallel"
    backend:
      type: "groq"
      model: "llama-3.3-70b"
      parallel_tool_calls: true          # Enable if provider supports it; verify using provider documentation
      concurrent_tool_execution: true
```

### Claude (Anthropic Messages API)
- Exposes inverse toggle: `disable_parallel_tool_use: true` forces single tool calls per turn
- API params handler injects into `tool_choice.disable_parallel_tool_use` (`massgen/api_params_handler/_claude_api_params_handler.py:124`)
- Default means Claude requests multiple tools when appropriate
- Local execution still honors `concurrent_tool_execution`/`max_concurrent_tools`

```yaml
agents:
  - id: "claude_parallel"
    backend:
      type: "claude"
      model: "claude-sonnet-4-20250514"
      disable_parallel_tool_use: false   # Allow multiple tool calls per turn
      concurrent_tool_execution: true    # Execute them in parallel locally
```

### Gemini
- Control tool-calling intent with `function_calling_mode` (`AUTO`, `ANY`, `NONE`) - maps to `FunctionCallingConfig` (`massgen/api_params_handler/_gemini_api_params_handler.py:78`)
- Gemini's model naturally supports emitting multiple `function_call` parts in a single response - the API has parallel tool calling capability built-in
- Backend registers custom/MCP tools as `types.Tool` but disables Gemini's automatic execution via `AutomaticFunctionCallingConfig(disable=True)` (`massgen/backend/gemini.py:447-452`)
- Gemini streams structured `function_call` parts; MassGen decides execution strategy via `concurrent_tool_execution`

```yaml
agents:
  - id: "gemini_parallel"
    backend:
      type: "gemini"
      model: "gemini-2.5-pro"
      function_calling_mode: "AUTO"
      concurrent_tool_execution: true
```

## Execution Flow

All backends that support custom/MCP tools route through the shared execution path:

1. **Model response** → Model emits tool calls
2. **Aggregation** → Backend aggregates custom + MCP calls (`massgen/backend/response.py:453` for Response/ChatCompletions/Claude/Gemini)
3. **Local execution** → `_execute_tool_calls` in `base_with_custom_tool_and_mcp.py:1084`
   - If `concurrent_tool_execution: false` or single tool → Sequential execution
   - If `concurrent_tool_execution: true` → Parallel execution with asyncio semaphore
4. **Results** → Streamed back to model for next turn


## Quick Tips

- **Default behavior:** OpenAI and Claude already default to allowing multiple tool calls per turn; only override if you need single-call semantics
- **Local vs. API:** `concurrent_tool_execution` is purely local - it doesn't affect what the model requests, only how MassGen executes
- **Reference config:** See `massgen/configs/tools/custom_tools/gpt5_nano_custom_tool_with_mcp_parallel.yaml` for a working example