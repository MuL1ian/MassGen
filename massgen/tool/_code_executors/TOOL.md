---
name: code-executors
description: Execute Python code and shell commands in isolated environments
category: code-execution
requires_api_keys: []
tasks:
  - "Run Python scripts in isolated temporary environments"
  - "Execute shell commands and capture output"
  - "Test code snippets and prototypes"
  - "Perform computational tasks with Python"
  - "Run system commands for file operations and utilities"
keywords: [python, shell, bash, execute, code-execution, scripting, subprocess, sandbox]
---

# Code Executors

Tools for executing Python code and shell commands in isolated, controlled environments with timeout management and output capture.

## Purpose

Enable agents to:
- Run Python code dynamically for computation and analysis
- Execute shell commands for system operations
- Test code snippets before committing
- Perform one-off computational tasks
- Automate system-level operations safely

## When to Use This Tool

**Use code executors when:**
- Need to run computational Python code
- Performing calculations or data analysis
- Testing code snippets before implementation
- Running system commands (file ops, process management)
- Prototyping algorithms or logic
- Need to execute external scripts

**Do NOT use for:**
- Long-running processes (use background jobs instead)
- Untrusted code (security risk)
- Production deployments
- Tasks requiring interactive input

## Available Functions

### `run_python_script(source_code: str, max_duration: float = 300) -> ExecutionResult`

Execute Python code in an isolated temporary environment.

**Example:**
```python
code = """
import math

def calculate_circle_area(radius):
    return math.pi * radius ** 2

area = calculate_circle_area(5)
print(f"Area: {area}")
"""

result = await run_python_script(code)
# Returns: "Area: 78.53981633974483"
```

**Features:**
- Runs in temporary directory (auto-cleanup)
- Captures stdout and stderr
- Timeout management (default 300 seconds)
- Exit code reporting
- Isolated from main process

**Parameters:**
- `source_code` (str): Python code to execute
- `max_duration` (float): Maximum execution time in seconds (default: 300)

**Returns:**
- `stdout`: Standard output from script
- `stderr`: Error output from script
- `exit_code`: Process exit code (0 = success)
- `timeout`: Whether execution timed out

**Example with error handling:**
```python
code = """
try:
    result = 10 / 0
except ZeroDivisionError as e:
    print(f"Error: {e}")
"""

result = await run_python_script(code)
# Returns: "Error: division by zero"
```

### `run_shell_command(command: str, max_duration: float = 300) -> ExecutionResult`

Execute shell commands and capture output.

**Example:**
```python
result = await run_shell_command("ls -la /tmp")
# Returns: Directory listing
```

**Example - File operations:**
```python
result = await run_shell_command("find . -name '*.py' | wc -l")
# Returns: Count of Python files
```

**Features:**
- Runs in system shell
- Captures stdout and stderr
- Timeout management
- Exit code reporting

**Parameters:**
- `command` (str): Shell command to execute
- `max_duration` (float): Maximum execution time in seconds (default: 300)

**Returns:**
- `stdout`: Command output
- `stderr`: Error messages
- `exit_code`: Command exit code
- `timeout`: Whether command timed out

**Warning:** Shell commands run with current user permissions. Use carefully.

## Configuration

### YAML Config

Enable code executors in your config:

```yaml
tools:
  - name: run_python_script
  - name: run_shell_command

# Or use custom_tools_path
custom_tools_path: "massgen/tool/_code_executors"
```

### Security Considerations

**Python execution:**
- Runs with current user permissions
- Can access filesystem (use workspace only)
- No network restrictions (be careful)
- Temporary files auto-cleanup
- Timeout prevents infinite loops

**Shell execution:**
- Full shell access (dangerous if misused)
- Run only trusted commands
- Validate inputs before execution
- Use absolute paths for safety
- Consider using Python instead for portability

## Timeout Management

Both executors enforce timeout limits to prevent hanging:

**Default timeout:** 300 seconds (5 minutes)

**Custom timeout:**
```python
# Short timeout for quick tasks
result = await run_python_script(code, max_duration=10)

# Long timeout for intensive tasks
result = await run_shell_command("./long_process.sh", max_duration=3600)
```

**On timeout:**
- Process is terminated
- Partial output is captured
- Exit code set to -1
- Timeout flag set to True

## Output Handling

**Python script output:**
```python
code = """
print("Line 1")
print("Line 2")
import sys
print("Error message", file=sys.stderr)
"""

result = await run_python_script(code)
# result.output_blocks[0].data contains:
# stdout: "Line 1\nLine 2\n"
# stderr: "Error message\n"
```

**Must use print() to capture output:**
```python
# This works
code = "print(5 + 5)"

# This doesn't (no output captured)
code = "5 + 5"
```

## Common Use Cases

### Python Execution

**1. Data analysis:**
```python
code = """
import json

data = [1, 2, 3, 4, 5]
mean = sum(data) / len(data)
print(f"Mean: {mean}")
"""
```

**2. File processing:**
```python
code = """
import csv

with open('data.csv', 'r') as f:
    reader = csv.reader(f)
    for row in reader:
        print(row)
"""
```

**3. Testing algorithms:**
```python
code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print(fibonacci(10))
"""
```

### Shell Execution

**1. File operations:**
```bash
find . -name '*.log' -mtime +7 -delete
```

**2. System information:**
```bash
df -h  # Disk usage
free -h  # Memory usage
uptime  # System uptime
```

**3. Text processing:**
```bash
grep -r "ERROR" /var/log | wc -l
```

**4. Archive operations:**
```bash
tar -czf backup.tar.gz /data
```

## Limitations

- **Security risk**: Code runs with full user permissions
- **No sandboxing**: No isolation from system resources
- **Timeout limit**: Max 300s by default (configurable)
- **No interactive input**: Cannot prompt for user input
- **No GUI**: Cannot run graphical applications
- **Python version**: Uses system Python interpreter
- **Shell dependency**: Shell commands not portable across OS
- **Resource limits**: No CPU/memory limits enforced
- **No state persistence**: Each execution is independent

## Best Practices

**1. Use Python over shell when possible:**
```python
# Prefer Python
code = "import os; print(os.listdir('.'))"

# Over shell
command = "ls"
```

**2. Handle errors explicitly:**
```python
code = """
try:
    # Your code here
    pass
except Exception as e:
    print(f"Error: {e}")
"""
```

**3. Validate inputs:**
```python
# Bad - unsafe
user_input = "some_file; rm -rf /"
command = f"cat {user_input}"

# Good - validated
import shlex
safe_input = shlex.quote(user_input)
command = f"cat {safe_input}"
```

**4. Use timeouts for safety:**
```python
# Prevent infinite loops
result = await run_python_script(code, max_duration=30)
```

**5. Clean up resources:**
```python
code = """
import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    # Work in tmpdir
    pass
# Auto-cleanup when done
"""
```

## Debugging

**Check exit codes:**
```python
result = await run_python_script(code)
if result.exit_code != 0:
    print(f"Script failed with code {result.exit_code}")
    print(f"Error: {result.stderr}")
```

**Verbose output:**
```python
code = """
print("Step 1: Starting")
# ... do work ...
print("Step 2: Processing")
# ... do work ...
print("Step 3: Complete")
"""
```

**Common issues:**
- **Import errors**: Module not installed in environment
- **Permission denied**: Insufficient file/directory permissions
- **Timeout**: Script taking too long
- **No output**: Forgot to print() results
