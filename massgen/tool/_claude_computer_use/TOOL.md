---
name: claude-computer-use
description: Browser and desktop automation using Anthropic's Claude Computer Use API
category: automation
requires_api_keys: [ANTHROPIC_API_KEY]
tasks:
  - "Automate browser interactions using Claude's native computer use capabilities"
  - "Control desktop applications with Claude's vision-guided actions"
  - "Perform multi-step workflows with Claude's computer use model"
  - "Execute browser automation with natural language instructions"
keywords: [claude, anthropic, computer-use, browser, automation, playwright, vision, desktop-control]
---

# Claude Computer Use

Browser and desktop automation tool using Anthropic's Claude Computer Use beta API, which provides native computer control capabilities.

## Purpose

Enable Claude models to directly control computers through Anthropic's Computer Use API:
- **Native Claude integration**: Uses Claude's built-in computer use capabilities
- **Vision-guided actions**: Claude sees the screen and decides actions
- **Natural language control**: Describe tasks in plain English
- **Multi-step workflows**: Claude chains actions automatically
- **Safety built-in**: Anthropic's safety measures integrated

## When to Use This Tool

**Use Claude Computer Use when:**
- Working with Anthropic's Claude models (Claude 3.5 Sonnet, etc.)
- Want native computer use capabilities (no custom vision integration needed)
- Need Claude's safety guardrails for automation
- Prefer Anthropic's computer use API over custom implementations
- Task benefits from Claude's reasoning + vision + action loop

**Use generic Computer Use instead when:**
- Working with OpenAI or other models
- Need more control over automation implementation
- Want to customize vision/action pipeline
- Require specific Playwright features

**Use Browser Automation instead when:**
- Need simple, predefined browser actions
- Don't require vision-guided decision making
- Want lower cost/faster execution

## Available Functions

### `claude_computer_use(task: str, environment: str, ...) -> ExecutionResult`

Main function for Claude-powered computer automation.

**Example - Browser Automation:**
```python
result = await claude_computer_use(
    task="Go to example.com and find the contact email",
    environment="browser",
    url="https://example.com"
)
# Claude navigates, reads page, extracts email
```

**Example - Multi-step Workflow:**
```python
result = await claude_computer_use(
    task="""
    1. Navigate to github.com
    2. Search for 'anthropic claude'
    3. Click on the first repository
    4. Tell me the star count
    """,
    environment="browser"
)
# Claude performs all steps and reports results
```

**Parameters:**
- `task` (str): Natural language description of what to do
- `environment` (str): "browser" or "docker"
- `url` (str, optional): Starting URL for browser tasks
- `max_steps` (int): Maximum actions Claude can take (default: 50)
- `headless` (bool): Run browser without GUI (default: False)
- `docker_image` (str, optional): Docker image for desktop automation
- `screenshot_dir` (str, optional): Where to save action screenshots

**Returns:**
- Success/failure status
- Action log showing Claude's steps
- Screenshots at each action
- Final result/answer

## How It Works

1. **Task submission**: You describe the task in natural language
2. **Screen capture**: Claude sees current screen state
3. **Action planning**: Claude decides next action (click, type, scroll, etc.)
4. **Action execution**: Playwright/Docker executes the action
5. **Visual verification**: Claude sees result on screen
6. **Repeat**: Loop until task complete or max steps reached

**Claude's actions:**
- `click(x, y)`: Click at coordinates
- `type(text)`: Type text
- `scroll(direction)`: Scroll page
- `key(key_name)`: Press keyboard key
- `navigate(url)`: Go to URL
- `done()`: Task complete

## Configuration

### Prerequisites

**Anthropic API key:**
```bash
export ANTHROPIC_API_KEY="your-api-key"
```

**Install Playwright:**
```bash
pip install playwright anthropic
playwright install chromium
```

**For Docker automation (optional):**
```bash
pip install docker
```

### Supported Models

Claude Computer Use works with:
- **Claude 3.5 Sonnet** (recommended): `claude-3-5-sonnet-20241022`
- **Claude 3 Opus**: `claude-3-opus-20240229`
- Other Claude models with computer use support

### YAML Config

Enable Claude Computer Use in your config:

```yaml
tools:
  - name: claude_computer_use

# Or use pre-configured example
config_file: "massgen/configs/tools/computer_use/claude_browser.yaml"
```

## Environment Types

### Browser Environment
Uses Playwright to control Chromium browser.

**Features:**
- Full web browser control
- JavaScript execution
- Cookies/session management
- Headless mode support

**Screen dimensions:** 1024x768 (Claude's recommended resolution)

### Docker Environment
Runs automation in isolated Docker container.

**Features:**
- Desktop application control
- X11 GUI support
- Complete isolation
- Linux environment

**Requires:** Docker with X11 setup

## Safety Features

Anthropic's Computer Use API includes safety measures:

1. **Action validation**: Prevents dangerous operations
2. **Rate limiting**: Limits action frequency
3. **Scope restrictions**: Confines actions to safe domains
4. **User confirmation**: May prompt for approval on sensitive actions
5. **Logging**: All actions logged for audit

**Note:** Safety features are controlled by Anthropic's API, not local code.

## Differences from Generic Computer Use

| Feature | Claude Computer Use | Generic Computer Use |
|---------|-------------------|---------------------|
| **Model** | Claude models only | OpenAI, Gemini, etc. |
| **Vision integration** | Built-in (Anthropic API) | Custom (understand_image) |
| **Safety** | Anthropic's guardrails | Custom implementation |
| **Action set** | Claude's native actions | Playwright primitives |
| **API calls** | Anthropic API | OpenAI/other APIs |
| **Cost** | Anthropic pricing | OpenAI/other pricing |
| **Customization** | Limited (API-controlled) | Full control |

## Cost Considerations

**Anthropic Computer Use API pricing:**
- Base model calls (Claude 3.5 Sonnet)
- Vision processing (screenshots)
- Action execution overhead

**Typical costs:**
- Simple task (5 steps): $0.10-0.30
- Complex task (20 steps): $0.50-1.50
- Per screenshot: ~$0.01-0.05

**Cost varies by:**
- Number of steps taken
- Screenshot size/frequency
- Model used (Sonnet vs Opus)
- Task complexity

## Limitations

- **Claude models only**: Requires Anthropic API access
- **API-dependent**: Subject to Anthropic's API availability
- **Safety restrictions**: Cannot override Anthropic's safety measures
- **Screen resolution**: Fixed at 1024x768 (Claude's optimized size)
- **Beta API**: Computer Use is still in beta (may change)
- **Rate limits**: Subject to Anthropic's rate limits
- **Browser only**: Desktop automation requires Docker setup
- **Cost**: Can be expensive for many-step tasks

## Best Practices

**1. Clear task descriptions:**
```python
# Good - specific and clear
task = "Navigate to example.com, find the pricing page, and extract the cost of the Pro plan"

# Bad - vague
task = "Check the website"
```

**2. Set reasonable step limits:**
```python
# For simple tasks
max_steps=10

# For complex tasks
max_steps=50

# Avoid unlimited steps (cost/safety)
```

**3. Use headless mode in production:**
```python
# Faster, more reliable
result = await claude_computer_use(
    task="...",
    environment="browser",
    headless=True
)
```

**4. Handle errors gracefully:**
```python
try:
    result = await claude_computer_use(task=task, environment="browser")
except Exception as e:
    logger.error(f"Computer use failed: {e}")
    # Fallback to alternative approach
```

**5. Monitor action logs:**
```python
# Review what Claude did
print(result.action_log)
# Verify expected behavior
```

## Common Use Cases

1. **Web data extraction**: Navigate sites and extract specific information
2. **Form automation**: Fill out multi-step web forms
3. **Testing**: Automated UI testing with natural language scenarios
4. **Research**: Browse multiple pages and synthesize information
5. **Documentation**: Screenshot and document web workflows
6. **Validation**: Verify website content or functionality

## Example Workflows

**Extract data from website:**
```python
task = """
Navigate to news.ycombinator.com
Find the top 3 stories
For each story, extract the title and score
Return the results as a formatted list
"""
result = await claude_computer_use(task=task, environment="browser")
```

**Automated form filling:**
```python
task = """
Go to contact-form.example.com
Fill in:
  - Name: John Doe
  - Email: john@example.com
  - Message: Test message
Click Submit
Verify confirmation message appears
"""
result = await claude_computer_use(task=task, environment="browser")
```

## Debugging

**Enable verbose logging:**
Set environment variable: `ANTHROPIC_LOG=debug`

**Check screenshots:**
Screenshots saved to workspace show what Claude saw at each step.

**Review action log:**
```python
result = await claude_computer_use(...)
print(result.action_log)  # See all actions taken
```

**Common issues:**
- **Max steps reached**: Increase `max_steps` or simplify task
- **Action failed**: Page changed unexpectedly, add error handling
- **Safety block**: Task violates Anthropic's safety policies
- **Rate limit**: Reduce automation frequency

## Migration from Generic Computer Use

If moving from generic computer use to Claude:

```python
# Before (generic)
result = await computer_use_tool(
    task="...",
    environment="browser",
    url="..."
)

# After (Claude-specific)
result = await claude_computer_use(
    task="...",
    environment="browser",
    url="..."
)
```

Main differences:
- Uses Anthropic's API instead of OpenAI
- Built-in vision (no separate understand_image)
- Different safety model
- Claude-specific action set
