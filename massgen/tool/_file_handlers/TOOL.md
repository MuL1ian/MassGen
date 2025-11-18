---
name: file-handlers
description: Read and write files with line range support and validation
category: file-operations
requires_api_keys: []
tasks:
  - "Read file contents with optional line ranges"
  - "Write or update files safely"
  - "Read specific sections of large files"
  - "Access files with path validation"
  - "Handle text file operations"
keywords: [file, read, write, filesystem, io, text-files, line-range, file-operations]
---

# File Handlers

Tools for reading and writing files with line range support, path validation, and error handling.

## Purpose

Provide safe, controlled file access for agents:
- Read entire files or specific line ranges
- Write new files or update existing ones
- Validate paths for security
- Handle large files efficiently
- Manage file operations with clear error messages

## When to Use This Tool

**Use file handlers when:**
- Reading configuration files or data
- Writing results to files
- Processing log files or large text files
- Reading specific sections of files (line ranges)
- Need validated file access

**Do NOT use for:**
- Binary file operations (use specialized tools)
- Database operations (use database tools)
- Complex file transformations (use code executors)
- Archive operations (use shell commands)

## Available Functions

### `read_file_content(target_path: str, line_range: Optional[List[int]] = None) -> ExecutionResult`

Read file contents with optional line range specification.

**Example - Read entire file:**
```python
result = await read_file_content("config.yaml")
# Returns: Full file content
```

**Example - Read specific lines:**
```python
# Read lines 10-20
result = await read_file_content("large_file.log", line_range=[10, 20])
# Returns: Lines 10-20 with line numbers
```

**Example - Read last 100 lines:**
```python
# Negative indices from end
result = await read_file_content("log.txt", line_range=[-100, -1])
# Returns: Last 100 lines
```

**Parameters:**
- `target_path` (str): Path to file (absolute or relative to workspace)
- `line_range` (List[int], optional): [start, end] line numbers (1-based, inclusive)
  - Positive numbers: Count from start
  - Negative numbers: Count from end (e.g., [-100, -1] = last 100 lines)

**Returns:**
- File content as text
- Line numbers included when using line ranges
- Error message if file not found or invalid range

**Format with line numbers:**
```
   1│ First line
   2│ Second line
   3│ Third line
```

### `write_file_content(target_path: str, content: str, mode: str = 'w') -> ExecutionResult`

Write content to a file (create or update).

**Example - Create new file:**
```python
content = "Hello, World!\nThis is a test."
result = await write_file_content("output.txt", content)
# Creates: output.txt with content
```

**Example - Append to file:**
```python
result = await write_file_content(
    "log.txt",
    "New log entry\n",
    mode='a'  # Append mode
)
# Appends: to existing file
```

**Parameters:**
- `target_path` (str): Path where to write file
- `content` (str): Content to write
- `mode` (str): Write mode ('w' = overwrite, 'a' = append)

**Returns:**
- Success confirmation with path
- Error message if write failed

## Configuration

### YAML Config

Enable file handlers in your config:

```yaml
tools:
  - name: read_file_content
  - name: write_file_content

# Or use custom_tools_path
custom_tools_path: "massgen/tool/_file_handlers"
```

## Line Range Specifications

Line ranges use 1-based indexing (like text editors):

**Positive indices (from start):**
```python
# Read lines 1-10
line_range=[1, 10]

# Read first 50 lines
line_range=[1, 50]

# Read single line
line_range=[42, 42]
```

**Negative indices (from end):**
```python
# Last 100 lines
line_range=[-100, -1]

# Last 10 lines
line_range=[-10, -1]

# 100 lines before last line
line_range=[-101, -2]
```

**Mixed indices:**
```python
# From line 100 to end
line_range=[100, -1]
```

## Path Handling

**Relative paths:**
- Resolved relative to agent workspace
- Example: `"data/config.yaml"` → `{workspace}/data/config.yaml`

**Absolute paths:**
- Must be within allowed directories (if validation enabled)
- Example: `"/tmp/output.txt"`

**Path validation:**
- Checks file exists before reading
- Validates path is within allowed directories
- Prevents directory traversal attacks

## Use Cases

### 1. Read Configuration Files

```python
result = await read_file_content("config.yaml")
# Parse YAML content
```

### 2. Process Log Files

```python
# Get last 1000 lines of log
result = await read_file_content("app.log", line_range=[-1000, -1])
# Analyze recent logs
```

### 3. Read Large Files Efficiently

```python
# Read 100 lines at a time
for i in range(0, 10000, 100):
    result = await read_file_content(
        "huge_file.txt",
        line_range=[i+1, i+100]
    )
    # Process chunk
```

### 4. Write Results

```python
results = "Analysis complete\nFound 42 items\n"
await write_file_content("results.txt", results)
```

### 5. Append to Log

```python
import datetime
log_entry = f"[{datetime.now()}] Task completed\n"
await write_file_content("activity.log", log_entry, mode='a')
```

### 6. Extract File Sections

```python
# Read function definition (lines 50-75)
result = await read_file_content("code.py", line_range=[50, 75])
```

## Error Handling

**File not found:**
```python
result = await read_file_content("missing.txt")
# Returns: "Error: File 'missing.txt' does not exist."
```

**Invalid line range:**
```python
result = await read_file_content("file.txt", line_range=[100, 50])
# Returns: "Error: Invalid line range [100, 50] for file with N lines."
```

**Path is directory:**
```python
result = await read_file_content("/some/directory")
# Returns: "Error: Path '/some/directory' is not a file."
```

**Write permission denied:**
```python
result = await write_file_content("/root/file.txt", "content")
# Returns: Error message with details
```

## Limitations

- **Text files only**: No binary file support
- **Encoding**: UTF-8 encoding assumed
- **Memory limits**: Reading huge files into memory can be slow
- **No atomic operations**: Writes not atomic (use temp files for safety)
- **No file locking**: Concurrent access not managed
- **No compression**: Cannot read compressed files directly
- **Line-based only**: Cannot specify byte ranges

## Best Practices

**1. Use line ranges for large files:**
```python
# Bad - reads entire 10GB file
result = await read_file_content("huge.log")

# Good - reads only needed lines
result = await read_file_content("huge.log", line_range=[-1000, -1])
```

**2. Handle errors gracefully:**
```python
result = await read_file_content("data.txt")
if "Error:" in result.output_blocks[0].data:
    print("File read failed")
else:
    # Process content
    pass
```

**3. Use relative paths in workspace:**
```python
# Good - portable
await read_file_content("data/input.txt")

# Avoid - hardcoded absolute paths
await read_file_content("/Users/john/data/input.txt")
```

**4. Append mode for logs:**
```python
# Append to log (preserves existing content)
await write_file_content("log.txt", "new entry\n", mode='a')
```

**5. Create parent directories first:**
```python
import os
os.makedirs("output/reports", exist_ok=True)
await write_file_content("output/reports/summary.txt", content)
```

## Common Issues

**Issue: Line numbers off by one**
- Remember: Line ranges are 1-based (first line is 1, not 0)

**Issue: Reading binary files**
- Solution: Use specialized tools or code executors

**Issue: File encoding errors**
- Solution: Ensure files are UTF-8 encoded

**Issue: Large file memory usage**
- Solution: Use line ranges to read chunks

**Issue: Concurrent write conflicts**
- Solution: Use unique filenames or file locking externally
