---
name: computer-use
description: Browser and desktop automation using OpenAI's Computer-Using Agent model
category: automation
requires_api_keys: [OPENAI_API_KEY]
tasks:
  - "Automate web browser interactions (click, type, scroll, navigate)"
  - "Control desktop applications in Docker/VM environments"
  - "Perform multi-step automated workflows with visual verification"
  - "Test web applications through automated user scenarios"
  - "Extract data through browser automation"
keywords: [automation, browser, computer-use, playwright, selenium, ui-automation, testing, workflow, cua]
---

# Computer Use Tool

Integration of OpenAI's Computer-Using Agent (CUA) model (`computer-use-preview`) for automated browser and desktop interactions.

## Purpose

Enable AI agents to interact with computers like humans do:
- **Browser automation**: Navigate websites, fill forms, click buttons
- **Desktop automation**: Control applications in sandboxed environments
- **Visual verification**: Use screenshots to verify actions
- **Multi-step workflows**: Chain complex automation sequences
- **Safety-first**: Built-in safety checks for secure operation

## When to Use This Tool

**Use computer use when:**
- Automating complex web interactions (multi-step forms, navigation)
- Testing web applications through realistic user scenarios
- Extracting data that requires interactive browsing
- Performing tasks that need visual verification
- Automating desktop apps in Docker/VM environments

**Do NOT use for:**
- Simple web scraping (use `_web_tools` instead)
- API-accessible data (use direct API calls)
- Local file operations (use file tools)
- Tasks on production systems (security risk)

## Available Functions

### `computer_use_tool(task: str, environment: str, ...) -> ExecutionResult`

Main computer use function that orchestrates browser/desktop automation.

**Example - Browser Automation:**
```python
result = await computer_use_tool(
    task="Go to example.com and click the 'Sign In' button",
    environment="browser",
    url="https://example.com"
)
# Returns: Action results with screenshot verification
```

**Example - Multi-step Workflow:**
```python
result = await computer_use_tool(
    task="""
    1. Navigate to github.com
    2. Search for 'massgen'
    3. Click on the first result
    4. Take a screenshot of the repository
    """,
    environment="browser"
)
```

**Parameters:**
- `task` (str): Description of what to do (natural language)
- `environment` (str): "browser" or "docker"
- `url` (str, optional): Starting URL for browser automation
- `max_steps` (int): Maximum automation steps (default: 50)
- `headless` (bool): Run browser without GUI (default: False)
- `docker_image` (str): Docker image for container automation
- `screenshot_dir` (str): Where to save screenshots

**Returns:**
- Success/failure status
- Action log with each step taken
- Screenshots at each step
- Final result description

## Architecture

The tool combines several components:

1. **Playwright**: Browser automation engine
2. **Computer Use Loop**: Orchestrates agent actions
3. **Screenshot Analysis**: Vision verification via `understand_image`
4. **Safety Checks**: Prevents dangerous operations
5. **Docker Integration** (optional): Sandboxed desktop automation

## Configuration

### Prerequisites

**Install Playwright:**
```bash
pip install playwright
playwright install chromium
```

**Set OpenAI API key:**
```bash
export OPENAI_API_KEY="your-api-key"
```

**For Docker automation (optional):**
```bash
pip install docker
docker pull ubuntu:22.04
```

**For image optimization (optional):**
```bash
pip install pillow
```

### YAML Config

Enable computer use in your config:

```yaml
tools:
  - name: computer_use_tool

# Or use pre-configured examples
config_file: "massgen/configs/tools/computer_use/browser_automation.yaml"
```

### Environment Types

**Browser environment:**
- Uses Playwright to control Chromium
- Best for web automation
- Supports headless mode for faster execution

**Docker environment:**
- Runs automation in isolated container
- Uses xdotool for desktop control
- Safer for untrusted automation
- Requires X11 forwarding setup

## Safety Features

The tool includes several safety mechanisms:

1. **Sandboxing**: Docker automation runs in isolated containers
2. **Safety checks**: Prevents dangerous operations (file deletion, system commands)
3. **Action logging**: All actions are recorded
4. **Screenshot verification**: Visual confirmation of each step
5. **Step limits**: Maximum automation steps to prevent infinite loops

**Safety check examples:**
- Blocks file system modifications outside workspace
- Prevents system command execution
- Validates URLs before navigation
- Restricts network access in Docker mode

## Integration with Vision

Computer use tool integrates with `understand_image` for visual feedback:

1. Agent takes action (click, type, etc.)
2. Screenshot captured
3. Vision model analyzes screenshot
4. Agent decides next action based on what it sees
5. Repeat until task complete

This visual feedback loop enables the agent to adapt to dynamic content and verify actions succeeded.

## Multi-Model Support

While designed for OpenAI's `computer-use-preview`, the tool can work with other models:
- **OpenAI GPT-4.1**: With vision for screenshot analysis
- **Gemini models**: With vision capabilities
- **Custom models**: If they support vision + function calling

## Limitations

- **Requires OpenAI CUA model**: `computer-use-preview` for best results
- **Browser-specific**: Playwright (Chromium) automation only
- **No mobile browsers**: Desktop browsers only
- **Docker complexity**: Desktop automation requires Docker setup
- **Safety restrictions**: Prevents many system-level operations
- **Speed**: Visual verification adds latency
- **Cost**: Vision API calls can be expensive
- **Captchas**: Cannot solve captchas or anti-bot measures

## Common Use Cases

1. **Web testing**: Automate test scenarios for web applications
2. **Form filling**: Complete multi-step forms automatically
3. **Data extraction**: Scrape data requiring authentication/interaction
4. **Visual regression**: Compare screenshots across changes
5. **Workflow automation**: Automate repetitive browser tasks
6. **Integration testing**: Test end-to-end user workflows
7. **Documentation**: Capture screenshots for tutorials

## Example Workflows

**Login and navigate:**
```python
task = """
1. Go to example.com/login
2. Enter username 'testuser' in the username field
3. Enter password 'testpass' in the password field
4. Click the 'Login' button
5. Wait for dashboard to load
6. Click on 'Settings' in the menu
"""
result = await computer_use_tool(task=task, environment="browser")
```

**Search and extract:**
```python
task = """
1. Navigate to search.example.com
2. Type 'climate change data' in the search box
3. Click search button
4. Take screenshot of results
5. Click on the first result
6. Extract the article title and summary
"""
result = await computer_use_tool(task=task, environment="browser")
```

## Debugging

**Enable verbose logging:**
```python
result = await computer_use_tool(
    task="...",
    environment="browser",
    verbose=True  # Detailed action logs
)
```

**Save screenshots:**
Screenshots are automatically saved to workspace. Check them to debug:
- What the agent saw at each step
- Where automation failed
- Visual state when errors occurred

**Common issues:**
- Selectors not found: Page loaded differently than expected
- Timeout errors: Page too slow or action didn't complete
- Safety blocks: Action prevented by safety checks
