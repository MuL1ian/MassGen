---
name: browser-automation
description: Simple browser automation for any LLM model using Playwright
category: automation
requires_api_keys: []
tasks:
  - "Navigate to web pages and capture content"
  - "Click elements and fill forms"
  - "Take screenshots of web pages"
  - "Extract text and data from web pages"
  - "Automate simple browser workflows"
keywords: [browser, automation, playwright, selenium, web, screenshot, click, navigation, testing]
---

# Browser Automation Tool

Simple browser automation tool that works with any LLM model (GPT-4.1, GPT-4o, Gemini, etc.) without requiring OpenAI's specialized computer-use-preview model.

## Purpose

Provide basic browser automation capabilities for agents that don't have access to advanced computer use models. This is a lightweight alternative to the full Computer Use tool.

## When to Use This Tool

**Use browser automation when:**
- You need simple browser interactions (navigate, click, type)
- Working with models that don't support computer use (Gemini, GPT-4o, etc.)
- Task doesn't require complex multi-step automation
- You want faster, cheaper browser automation
- Taking screenshots for documentation

**Use Computer Use instead when:**
- Need complex multi-step workflows with visual verification
- Require adaptive behavior based on page state
- Working with OpenAI's `computer-use-preview` model
- Need desktop automation beyond browsers

## Available Functions

### `browser_automation(task: str, action: str, ...) -> ExecutionResult`

Main browser automation function with specific action types.

**Actions:**
- `navigate`: Go to a URL
- `click`: Click an element
- `type`: Type text into an element
- `screenshot`: Capture page screenshot
- `extract`: Extract text from elements

**Example - Navigate:**
```python
result = await browser_automation(
    task="Open Wikipedia",
    url="https://en.wikipedia.org",
    action="navigate"
)
```

**Example - Click:**
```python
result = await browser_automation(
    task="Click search button",
    action="click",
    selector="button[type='submit']"
)
```

**Example - Type:**
```python
result = await browser_automation(
    task="Search for Jimmy Carter",
    action="type",
    selector="input[name='search']",
    text="Jimmy Carter"
)
```

**Example - Screenshot:**
```python
result = await browser_automation(
    task="Capture homepage",
    action="screenshot",
    output_filename="homepage.png"
)
```

**Example - Extract:**
```python
result = await browser_automation(
    task="Get article title",
    action="extract",
    selector="h1.article-title"
)
```

**Parameters:**
- `task` (str): Description of what to do
- `action` (str): Action type (navigate/click/type/screenshot/extract)
- `url` (str, optional): URL to navigate to
- `selector` (str, optional): CSS selector for element
- `text` (str, optional): Text to type
- `headless` (bool): Run without GUI (default: False)
- `screenshot` (bool): Take screenshot after action (default: True)
- `output_filename` (str, optional): Where to save screenshot
- `agent_cwd` (str): Workspace directory (auto-injected)

## Configuration

### Prerequisites

**Install Playwright:**
```bash
pip install playwright
playwright install chromium
```

### YAML Config

Enable browser automation in your config:

```yaml
custom_tools_path: "massgen/tool/_browser_automation"

# Or add to tools list
tools:
  - name: browser_automation
```

## Action Types

### Navigate
Load a webpage.

```python
await browser_automation(
    task="Load example.com",
    action="navigate",
    url="https://example.com"
)
```

### Click
Click an element using CSS selector.

```python
await browser_automation(
    task="Click login button",
    action="click",
    selector="#login-btn"
)
```

**Common selectors:**
- By ID: `#element-id`
- By class: `.class-name`
- By type: `button[type='submit']`
- By text: `text="Click me"`

### Type
Type text into an input field.

```python
await browser_automation(
    task="Enter username",
    action="type",
    selector="input[name='username']",
    text="myusername"
)
```

### Screenshot
Capture current page state.

```python
await browser_automation(
    task="Screenshot results",
    action="screenshot",
    output_filename="results.png"
)
```

Screenshots saved to agent workspace by default.

### Extract
Extract text content from elements.

```python
await browser_automation(
    task="Get article text",
    action="extract",
    selector=".article-content"
)
```

Returns the text content of matched elements.

## Headless Mode

Run browser without GUI for faster execution:

```python
result = await browser_automation(
    task="...",
    action="...",
    headless=True  # No visible browser window
)
```

**Headless benefits:**
- Faster execution
- Lower resource usage
- Suitable for server environments

**When not to use headless:**
- Debugging (want to see what's happening)
- Pages that detect headless browsers
- Visual verification needed

## Multi-Step Workflows

Chain multiple actions by calling the function multiple times:

```python
# Step 1: Navigate
await browser_automation(
    task="Load search page",
    action="navigate",
    url="https://example.com/search"
)

# Step 2: Type search query
await browser_automation(
    task="Enter search term",
    action="type",
    selector="input[name='q']",
    text="climate change"
)

# Step 3: Submit
await browser_automation(
    task="Click search",
    action="click",
    selector="button[type='submit']"
)

# Step 4: Screenshot results
await browser_automation(
    task="Capture results",
    action="screenshot",
    output_filename="search_results.png"
)
```

## Limitations

- **No visual AI**: Actions must be pre-specified (no adaptive behavior)
- **Manual selectors**: You must provide CSS selectors
- **No state awareness**: Doesn't verify if actions succeeded
- **Single browser instance**: Each call is independent
- **No session persistence**: Cookies/state not maintained across calls
- **Basic actions only**: No drag-drop, file upload, etc.
- **No iframe support**: Cannot interact with iframe content directly
- **Chromium only**: Uses Playwright's Chromium browser

## Common Use Cases

1. **Simple scraping**: Navigate and extract data
2. **Screenshots**: Capture pages for documentation
3. **Form testing**: Fill and submit simple forms
4. **Navigation flows**: Click through multi-page flows
5. **Content extraction**: Get text from specific elements
6. **Visual verification**: Screenshot before/after states

## Comparison with Computer Use

| Feature | Browser Automation | Computer Use |
|---------|-------------------|--------------|
| Model requirement | Any LLM | OpenAI CUA preferred |
| Visual AI | No | Yes |
| Complexity | Simple actions | Complex workflows |
| Cost | Lower | Higher (vision calls) |
| Speed | Faster | Slower (verification) |
| Adaptability | Fixed actions | Adaptive behavior |
| Best for | Predetermined steps | Dynamic tasks |

## Debugging

**Check screenshots:**
- Screenshots saved after each action (if enabled)
- Review to see what page looked like
- Verify selectors matched correct elements

**Common issues:**
- **Element not found**: Selector incorrect or page not loaded
- **Click failed**: Element not clickable or hidden
- **Type failed**: Element not an input or disabled
- **Timeout**: Page loading too slow

**Solutions:**
- Add wait time for page loads
- Verify selectors using browser DevTools
- Check if JavaScript is modifying page
- Use more specific selectors
