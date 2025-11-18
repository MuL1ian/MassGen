# Code-Based Tools Example - Custom Tools

This directory contains example custom tools for demonstrating the code-based tools feature.

## What's Here

- `string_utils.py` - Simple string manipulation functions

## How It Works

When `custom_tools_path: "massgen/tool/_code_based_example"` is set in the config:

1. This entire directory gets **copied** to `shared_tools/custom_tools/` (or workspace)
2. Agents can read, import, and use these functions directly
3. These are **full Python implementations** (not MCP wrappers)

## Difference from MCP Tools

- **MCP tools** (in `servers/`) are auto-generated wrappers that call MCP protocol
- **Custom tools** (in `custom_tools/`) are complete Python code you provide

Both are visible to agents as normal Python modules they can import and use.

## Important: Return Type Requirement

**All custom tools MUST return `ExecutionResult`** (not plain str/int/dict):

```python
from massgen.tool._result import ExecutionResult, TextContent

def my_tool(input: str) -> ExecutionResult:
    """Custom tool that returns ExecutionResult."""
    result = do_something(input)

    return ExecutionResult(
        output_blocks=[TextContent(data=result)]
    )
```

See `string_utils.py` for examples of proper `ExecutionResult` usage.
