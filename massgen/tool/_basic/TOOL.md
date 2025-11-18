---
name: basic-tools
description: Basic utility tools for testing and demonstration
category: utilities
requires_api_keys: []
tasks:
  - "Add two numbers together"
  - "Perform simple arithmetic operations"
  - "Test tool functionality"
  - "Validate tool registration and execution"
keywords: [math, arithmetic, testing, utilities, example, demo, validation]
---

# Basic Tools

Simple utility tools primarily used for testing and validating MassGen's tool system.

## Purpose

Provide minimal, testable tools for:
- Validating tool registration works correctly
- Testing tool execution pipeline
- Demonstrating simplest possible tool implementation
- Quick sanity checks during development

## When to Use This Tool

**Use basic tools when:**
- Testing that tools are working at all
- Need simple arithmetic for debugging
- Validating tool configuration
- Learning how tools work

**Do NOT use for:**
- Production calculations (use code executors or Python directly)
- Complex math (use specialized libraries)
- Real-world tasks (use appropriate tools)

## Available Functions

### `two_num_tool(x: int, y: int) -> ExecutionResult`

Add two numbers together.

**Example:**
```python
result = await two_num_tool(5, 3)
# Returns: "The sum of 5 and 3 is 8"
```

**Parameters:**
- `x` (int): First number
- `y` (int): Second number

**Returns:**
- ExecutionResult containing the sum as a formatted string

## Configuration

### YAML Config

```yaml
tools:
  - name: two_num_tool

# Or use custom_tools_path
custom_tools_path: "massgen/tool/_basic"
```

## Implementation

This is the simplest possible tool implementation:

```python
from massgen.tool._result import ExecutionResult, TextContent

async def two_num_tool(x: int, y: int) -> ExecutionResult:
    """Add two numbers together."""
    result = x + y
    return ExecutionResult(
        output_blocks=[
            TextContent(data=f"The sum of {x} and {y} is {result}"),
        ],
    )
```

**Key points:**
- Async function (required for all tools)
- Returns `ExecutionResult` (not plain int/str)
- Wraps output in `TextContent`
- Simple, testable logic

## Use Cases

### 1. Validate Tool System

```python
# If this works, tool system is functioning
result = await two_num_tool(1, 1)
assert "2" in result.output_blocks[0].data
```

### 2. Test Configuration

```yaml
# Test that YAML config loads tools correctly
tools:
  - name: two_num_tool
```

### 3. Debug Tool Execution

```python
# Minimal tool to isolate execution issues
result = await two_num_tool(10, 20)
print(result.output_blocks[0].data)
```

### 4. Learning Example

Study `_two_num_tool.py` to understand:
- Tool function signature
- ExecutionResult usage
- Async/await pattern
- Type hints

## Limitations

- **Only addition**: Doesn't support other operations
- **Integers only**: No float support
- **No error handling**: Assumes valid inputs
- **Not practical**: Use for testing, not production

## Extending Basic Tools

To add more basic utilities, follow this pattern:

```python
from massgen.tool._result import ExecutionResult, TextContent

async def my_basic_tool(param: str) -> ExecutionResult:
    """Tool description."""
    result = do_something(param)
    return ExecutionResult(
        output_blocks=[TextContent(data=result)]
    )
```

Then add to `__init__.py` to export it.

## Comparison with Code Executors

**Basic tools:**
- Pre-defined functions
- Fast execution
- Type-safe
- Limited flexibility

**Code executors:**
- Dynamic code
- Slower execution
- More powerful
- Full Python capabilities

For simple arithmetic, code executors are better:

```python
# Instead of basic tools
result = await run_python_script("print(5 + 3)")

# More flexible, no need for dedicated tool
```

## Best Practices

**Don't rely on basic tools for real work:**
```python
# Bad - using basic tool for calculation
result = await two_num_tool(142, 857)

# Good - use Python directly
result = 142 + 857

# Or if agent needs to calculate
result = await run_python_script("print(142 + 857)")
```

**Use for testing only:**
```python
# Good - validating tool system works
def test_tool_execution():
    result = await two_num_tool(1, 2)
    assert result.output_blocks[0].data == "The sum of 1 and 2 is 3"
```

## Summary

Basic tools are **intentionally minimal** for testing purposes. For real tasks, use:
- **Code executors** for calculations
- **Specialized tools** for specific domains
- **Custom tools** for your use cases

The basic tools directory serves as:
- A template for creating tools
- A test suite for tool functionality
- A learning resource for tool patterns
