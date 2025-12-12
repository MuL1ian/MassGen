# Qwen Computer Use Tool for MassGen

## Overview

The Qwen Computer Use tool integrates Alibaba Cloud's Qwen3-VL-235B-A22B-Thinking vision-language model into MassGen, enabling automated browser and computer interactions through vision-guided action generation with reasoning capabilities.

## Key Features

- **Vision-Language Control**: Uses Qwen VL model to analyze screenshots and generate actions
- **OpenAI-Compatible API**: Leverages Qwen's OpenAI-compatible endpoint
- **Multi-Environment Support**: Works with both browser (Playwright) and Docker/Linux environments
- **Natural Language Tasks**: Describe complex tasks in plain English
- **Cost-Effective**: Efficient VL model with competitive pricing
- **Comprehensive Action Set**: Click, type, scroll, navigate, and more

## Prerequisites

### API Key
```bash
export QWEN_API_KEY="your-qwen-api-key"
```

Get your API key from [Alibaba Cloud DashScope](https://dashscope.aliyuncs.com/)

### Dependencies
```bash
# Core dependencies
pip install openai playwright

# Install browser
playwright install chromium

# Optional: For Docker automation
pip install docker
```

## Quick Start

### Browser Automation

```bash
# Using configuration file
massgen --config massgen/configs/tools/custom_tools/qwen_computer_use_example.yaml \
    "Search Google for Python 3.12 new features"

# With visible browser (requires DISPLAY)
DISPLAY=:20 massgen --config massgen/configs/tools/custom_tools/qwen_computer_use_example.yaml \
    "Navigate to Wikipedia and find information about quantum computing"
```

### Docker/Linux Automation

```bash
# First, set up Docker container (one-time)
./scripts/setup_docker_cua.sh

# Run automation
massgen --config massgen/configs/tools/custom_tools/qwen_computer_use_docker_example.yaml \
    "Open Firefox and search for AI news"
```

## Python API

```python
from massgen.tool import qwen_computer_use
import asyncio

# Browser task
result = asyncio.run(qwen_computer_use(
    task="Go to github.com and find popular Python projects",
    environment="browser",
    model="qwen3-vl-235b-a22b-thinking"
))

# Docker task
result = asyncio.run(qwen_computer_use(
    task="Open calculator and compute 123 * 456",
    environment="linux",
    environment_config={
        "container_name": "cua-container",
        "display": ":99"
    }
))

# Parse result
import json
output = json.loads(result.output_blocks[0].data)
print(f"Success: {output['success']}")
print(f"Iterations: {output['iterations']}")
print(f"Action log: {output['action_log']}")
```

## Configuration Examples

### Minimal Browser Config

```yaml
agents:
  - id: "qwen_agent"
    backend:
      type: "openai"
      model: "gpt-4.1"
      custom_tools:
        - name: ["qwen_computer_use"]
          path: "massgen/tool/_qwen_computer_use/qwen_computer_use_tool.py"
          function: ["qwen_computer_use"]
          preset_args:
            environment: "browser"
            model: "qwen3-vl-235b-a22b-thinking"
```

### Advanced Config with Options

```yaml
agents:
  - id: "qwen_agent"
    backend:
      type: "openai"
      model: "gpt-4.1"
      custom_tools:
        - name: ["qwen_computer_use"]
          path: "massgen/tool/_qwen_computer_use/qwen_computer_use_tool.py"
          function: ["qwen_computer_use"]
          preset_args:
            environment: "browser"
            display_width: 1920
            display_height: 1080
            max_iterations: 30
            model: "qwen3-vl-235b-a22b-thinking"
            environment_config:
              headless: true
              browser_type: "chromium"
```

## How It Works

1. **Task Submission**: You provide a natural language task description
2. **Screenshot Capture**: Initial screenshot is captured (browser or Docker)
3. **Vision Analysis**: Qwen VL model analyzes the screenshot
4. **Action Generation**: Model generates JSON actions based on visual understanding
5. **Action Execution**: Playwright or xdotool executes the actions
6. **Iteration**: Process repeats with new screenshots until task complete

### Action Format

Qwen generates actions in JSON format:

```json
{
  "thought": "I can see a search box in the center. I'll click it and type the query.",
  "actions": [
    {
      "type": "click",
      "x": 720,
      "y": 450
    },
    {
      "type": "type",
      "text": "machine learning"
    },
    {
      "type": "key",
      "key": "Return"
    }
  ]
}
```

### Available Actions

- **click**: Click at pixel coordinates
- **type**: Type text (with optional click position)
- **scroll**: Scroll in direction (up/down/left/right)
- **navigate**: Navigate to URL
- **go_back**: Browser back button
- **go_forward**: Browser forward button
- **wait**: Wait for duration
- **key**: Press keyboard key
- **done**: Mark task as complete

## Environment Types

### Browser Environment

Uses Playwright to control Chromium browser:
- Full JavaScript execution
- Cookies and session management
- Headless or visible mode
- Network interception capabilities

**Default resolution**: 1440x900

### Docker/Linux Environment

Uses xdotool for desktop control:
- X11 GUI support
- Complete isolation
- Ubuntu 22.04 with Xfce
- Firefox and standard tools

**Requires**: Docker container with X11 setup

## Comparison with Other Tools

| Feature | Qwen Computer Use | Gemini Computer Use | Claude Computer Use |
|---------|------------------|---------------------|---------------------|
| **Model** | Qwen3-VL-235B | Gemini 2.5 | Claude 3.5+ |
| **API Type** | OpenAI-compatible | Google GenAI | Anthropic |
| **Coordinates** | Pixel-based | Normalized (0-1000) | Pixel-based |
| **Implementation** | Vision → JSON actions | Native computer use | Native computer use |
| **Cost** | Low | Medium | Medium-High |
| **Speed** | Fast | Fast | Medium |

## Use Cases

### Web Scraping
```python
task = """
Navigate to news.ycombinator.com
Extract the top 10 story titles and URLs
Return as a formatted list
"""
```

### Form Automation
```python
task = """
Go to contact-form.example.com
Fill in:
  Name: John Doe
  Email: john@example.com
  Message: Hello, I have a question
Click Submit
"""
```

### Research & Information Gathering
```python
task = """
Search Google Scholar for 'quantum computing 2024'
Find the most cited paper
Extract title, authors, and citation count
"""
```

### UI Testing
```python
task = """
Navigate to myapp.com/login
Enter username: testuser
Enter password: testpass123
Click login button
Verify dashboard loads successfully
"""
```

## Cost Considerations

**Qwen API Pricing** (approximate):
- VL model call (235B): ~$0.005-0.02 per call
- Per screenshot analysis: ~$0.005-0.02
- Typical task (10 iterations): $0.05-0.20

**Cost varies by**:
- Number of iterations
- Task complexity
- Screenshot frequency
- Model used

**Cost optimization tips**:
1. Write clear, specific tasks to minimize iterations
2. Set reasonable `max_iterations` limits
3. Use headless mode when visual monitoring not needed
4. Batch similar tasks together

## Performance Tips

1. **Clear Task Descriptions**: Be specific to reduce unnecessary iterations
   ```python
   # Good
   task = "Extract the top 5 story titles from Hacker News homepage"

   # Less good
   task = "Check what's on Hacker News"
   ```

2. **Appropriate Iteration Limits**:
   - Simple tasks: 10-15 iterations
   - Complex tasks: 20-30 iterations

3. **Headless Mode**: Faster execution when visual monitoring not needed
   ```yaml
   environment_config:
     headless: true
   ```

4. **Optimize Display Size**: Match your target content
   ```yaml
   display_width: 1920
   display_height: 1080
   ```

## Troubleshooting

### Common Issues

**API Key Not Found**
```bash
export QWEN_API_KEY="your-key"
# Or add to .env file
```

**Playwright Not Installed**
```bash
pip install playwright
playwright install chromium
```

**Docker Container Not Found**
```bash
./scripts/setup_docker_cua.sh
docker ps  # Verify container is running
```

**JSON Parsing Errors**
The implementation handles various JSON formats including markdown code blocks. If issues persist, check model response format.

**Max Iterations Exceeded**
- Task too complex: break into smaller subtasks
- Increase limit: `max_iterations=40`
- Simplify task description

### Debugging

**Enable verbose logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Check action log**:
```python
result = await qwen_computer_use(...)
output = json.loads(result.output_blocks[0].data)
for iteration in output['action_log']:
    print(f"Iteration {iteration['iteration']}:")
    print(f"  Thought: {iteration.get('thought')}")
    print(f"  Actions: {iteration.get('actions')}")
```

## Limitations

- **Vision model dependency**: Requires Qwen VL model access
- **API rate limits**: Subject to Alibaba Cloud rate limits
- **JSON format**: Actions must be in valid JSON format
- **Coordinate precision**: Requires accurate display size configuration
- **Browser focus**: Desktop automation less mature than browser
- **Regional availability**: May vary by region

## Best Practices

1. **Test with simple tasks first** before complex automation
2. **Monitor iterations** to optimize task descriptions
3. **Handle errors gracefully** with try-except blocks
4. **Use appropriate timeouts** for network-dependent tasks
5. **Clean up resources** (browser/Docker) after use
6. **Secure API keys** using environment variables
7. **Validate results** after automation completes

## Migration Guide

### From Gemini Computer Use

```python
# Before (Gemini)
result = await gemini_computer_use(
    task="...",
    environment="browser"
)

# After (Qwen)
result = await qwen_computer_use(
    task="...",
    environment="browser",
    model="qwen3-vl-235b-a22b-thinking"
)
```

Main differences:
- Different API (OpenAI-compatible vs Google GenAI)
- Pixel coordinates instead of normalized
- JSON-based action format
- Different response structure

### From Claude Computer Use

Similar migration pattern. Main differences:
- Different provider (Alibaba vs Anthropic)
- Vision-guided actions vs native computer use
- OpenAI-compatible API vs Anthropic API

## Examples

See the `massgen/configs/tools/custom_tools/` directory for complete examples:

- `qwen_computer_use_example.yaml` - Browser automation
- `qwen_computer_use_docker_example.yaml` - Docker/Linux automation

## Support & Contributing

For issues, questions, or contributions:
- Check the main MassGen documentation
- Review TOOL.md for detailed tool information
- See examples in the configs directory

## License

Part of the MassGen framework. See main LICENSE file.
