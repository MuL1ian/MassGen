---
name: code-based-example
description: Example custom tools demonstrating string manipulation utilities
category: text-processing
requires_api_keys: []
tasks:
  - "Reverse strings for text manipulation"
  - "Count words in text documents"
  - "Convert text to uppercase"
  - "Demonstrate custom tool implementation patterns"
keywords: [string, text, reverse, uppercase, word-count, example, custom-tools]
---

# Code-Based Example Tools

Simple string manipulation utilities that demonstrate how to create custom tools in MassGen's code-based paradigm.

## Purpose

This is a reference implementation showing:
- How to structure custom tools
- Proper use of `ExecutionResult` return types
- Simple, testable tool functions
- Integration with MassGen's tool system

## When to Use This Tool

- **Text manipulation tasks**: Reverse strings, count words, change case
- **Learning reference**: Study this when creating your own custom tools
- **Testing**: Validate that custom tools are working correctly

These are intentionally simple examples. For production use cases, consider more sophisticated text processing libraries.

## Available Functions

### `reverse_string(text: str) -> ExecutionResult`
Reverses the characters in a string.

**Example:**
```python
result = reverse_string("hello")
# Returns: "olleh"
```

### `count_words(text: str) -> ExecutionResult`
Counts the number of words in text (splits on whitespace).

**Example:**
```python
result = count_words("hello world")
# Returns: "2"
```

### `uppercase(text: str) -> ExecutionResult`
Converts text to uppercase.

**Example:**
```python
result = uppercase("hello")
# Returns: "HELLO"
```

## Configuration

To use these tools, set in your YAML config:

```yaml
custom_tools_path: "massgen/tool/_code_based_example"
```

This copies the entire directory to `shared_tools/custom_tools/` where agents can import and use them.

## Implementation Pattern

**All custom tools MUST return `ExecutionResult`:**

```python
from massgen.tool._result import ExecutionResult, TextContent

def my_tool(input: str) -> ExecutionResult:
    result = do_something(input)
    return ExecutionResult(
        output_blocks=[TextContent(data=result)]
    )
```

## Limitations

- These are basic string utilities for demonstration purposes
- No advanced text processing (regex, NLP, etc.)
- Not suitable for large-scale text analysis
- For production text processing, use specialized libraries
