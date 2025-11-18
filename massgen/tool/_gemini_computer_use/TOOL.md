---
name: gemini-computer-use
description: Browser and desktop automation using Google's Gemini 2.5 Computer Use model
category: automation
requires_api_keys: [GEMINI_API_KEY]
tasks:
  - "Automate browser interactions using Gemini's native computer use capabilities"
  - "Control desktop applications with Gemini's action system"
  - "Perform multi-step workflows with Gemini 2.5"
  - "Execute browser automation with Gemini's computer use API"
keywords: [gemini, google, computer-use, browser, automation, playwright, desktop-control, genai]
---

# Gemini Computer Use

Browser and desktop automation tool using Google's Gemini 2.5 Computer Use model, which provides native computer control capabilities through the Google GenAI SDK.

## Purpose

Enable Gemini models to directly control computers through Google's Computer Use API:
- **Native Gemini integration**: Uses Gemini 2.5's built-in computer use
- **Action-based control**: Gemini decides and executes actions
- **Natural language tasks**: Describe what to do in plain English
- **Multi-step automation**: Gemini chains actions automatically
- **Google AI integration**: Seamless with Google's AI ecosystem

## When to Use This Tool

**Use Gemini Computer Use when:**
- Working with Google's Gemini 2.5 models
- Want native Gemini computer use capabilities
- Prefer Google's AI ecosystem
- Need Gemini-specific features or performance
- Task benefits from Gemini's reasoning + action loop

**Use Claude Computer Use instead when:**
- Working with Anthropic's Claude models
- Need Claude's specific safety features
- Prefer Anthropic's API

**Use generic Computer Use instead when:**
- Working with OpenAI models
- Need custom vision/action pipeline
- Want maximum control over implementation

**Use Browser Automation instead when:**
- Need simple, predefined actions
- Don't require AI-guided decision making
- Want lower cost/faster execution

## Available Functions

### `gemini_computer_use(task: str, environment: str, ...) -> ExecutionResult`

Main function for Gemini-powered computer automation.

**Example - Browser Automation:**
```python
result = await gemini_computer_use(
    task="Go to example.com and find the main heading",
    environment="browser",
    url="https://example.com"
)
# Gemini navigates, reads page, extracts heading
```

**Example - Multi-step Workflow:**
```python
result = await gemini_computer_use(
    task="""
    1. Navigate to wikipedia.org
    2. Search for 'Artificial Intelligence'
    3. Scroll down to the history section
    4. Summarize the first paragraph
    """,
    environment="browser"
)
# Gemini performs all steps and provides summary
```

**Parameters:**
- `task` (str): Natural language description of what to do
- `environment` (str): "browser" or "docker"
- `url` (str, optional): Starting URL for browser tasks
- `max_steps` (int): Maximum actions Gemini can take (default: 50)
- `headless` (bool): Run browser without GUI (default: False)
- `docker_image` (str, optional): Docker image for desktop automation
- `screenshot_dir` (str, optional): Where to save screenshots

**Returns:**
- Success/failure status
- Action log showing Gemini's steps
- Screenshots at each action
- Final result/answer

## How It Works

1. **Task submission**: You describe the task in natural language
2. **Screen capture**: Gemini sees current screen state
3. **Action planning**: Gemini decides next action
4. **Action execution**: Playwright/Docker executes the action
5. **Verification**: Gemini sees result on screen
6. **Repeat**: Loop until task complete or max steps reached

**Gemini's actions:**
- `click(x, y)`: Click at normalized coordinates (0-1000 scale)
- `type(text)`: Type text
- `scroll(x, y, direction)`: Scroll at position
- `key(key_name)`: Press keyboard key
- `done()`: Task complete

**Coordinate system:**
- Gemini uses normalized coordinates (0-1000)
- Tool converts to actual screen pixels (1440x900)
- More consistent across different resolutions

## Configuration

### Prerequisites

**Google AI API key:**
```bash
export GOOGLE_API_KEY="your-api-key"
```

**Install dependencies:**
```bash
pip install playwright google-genai
playwright install chromium
```

**For Docker automation (optional):**
```bash
pip install docker
```

### Supported Models

Gemini Computer Use works with:
- **Gemini 2.5 Flash** (recommended): Fast, efficient computer use
- **Gemini 2.5 Pro**: More capable, slower, higher cost
- Other Gemini models with computer use support

### YAML Config

Enable Gemini Computer Use in your config:

```yaml
tools:
  - name: gemini_computer_use

# Or use pre-configured example
config_file: "massgen/configs/tools/computer_use/gemini_browser.yaml"
```

## Environment Types

### Browser Environment
Uses Playwright to control Chromium browser.

**Features:**
- Full web browser control
- JavaScript execution
- Cookies/session management
- Headless mode support

**Screen dimensions:** 1440x900 (Gemini's recommended resolution)

### Docker Environment
Runs automation in isolated Docker container.

**Features:**
- Desktop application control
- X11 GUI support
- Complete isolation
- Linux environment

**Requires:** Docker with X11 setup

## Gemini-Specific Features

**Normalized coordinates:**
- Actions use 0-1000 coordinate system
- More portable across resolutions
- Automatic conversion to actual pixels

**Efficient actions:**
- Gemini optimized for fewer steps
- Smart action planning
- Quick task completion

**Google AI integration:**
- Works with other Google AI services
- Consistent API across Google products
- Vertex AI compatibility

## Differences from Other Computer Use Tools

| Feature | Gemini Computer Use | Claude Computer Use | Generic Computer Use |
|---------|-------------------|-------------------|---------------------|
| **Model** | Gemini 2.5 | Claude 3.5 | OpenAI/various |
| **Coordinates** | Normalized (0-1000) | Pixel-based | Pixel-based |
| **Screen size** | 1440x900 | 1024x768 | Configurable |
| **API** | Google GenAI | Anthropic | OpenAI/custom |
| **Cost** | Google pricing | Anthropic pricing | OpenAI/other pricing |

## Cost Considerations

**Google AI Computer Use pricing:**
- Base model calls (Gemini 2.5)
- Vision processing (screenshots)
- Action execution

**Typical costs:**
- Simple task (5 steps): $0.05-0.20
- Complex task (20 steps): $0.30-1.00
- Per screenshot: ~$0.005-0.02

**Cost varies by:**
- Number of steps taken
- Screenshot frequency
- Model used (Flash vs Pro)
- Task complexity

**Generally cheaper than Claude, comparable to OpenAI.**

## Limitations

- **Gemini models only**: Requires Google AI API access
- **API-dependent**: Subject to Google's API availability
- **Screen resolution**: Fixed at 1440x900 (Gemini's optimized size)
- **Beta features**: Computer use may change as Google updates
- **Rate limits**: Subject to Google's rate limits
- **Browser focus**: Desktop automation less mature than browser
- **Regional availability**: May not be available in all regions

## Best Practices

**1. Clear, specific tasks:**
```python
# Good
task = "Navigate to news.ycombinator.com and extract the top 5 story titles"

# Bad
task = "Check Hacker News"
```

**2. Reasonable step limits:**
```python
# Most tasks complete in < 20 steps
max_steps=20

# Complex tasks
max_steps=50
```

**3. Use Flash model for speed:**
```python
# In your config
model: "gemini-2.5-flash"  # Faster, cheaper
# vs
model: "gemini-2.5-pro"    # More capable, slower
```

**4. Handle errors:**
```python
try:
    result = await gemini_computer_use(task=task, environment="browser")
except Exception as e:
    logger.error(f"Gemini computer use failed: {e}")
    # Fallback approach
```

**5. Monitor for efficiency:**
```python
result = await gemini_computer_use(...)
print(f"Completed in {result.steps_taken} steps")
# Optimize if consistently using many steps
```

## Common Use Cases

1. **Web scraping**: Extract data from dynamic websites
2. **Form automation**: Fill out web forms automatically
3. **Testing**: Automated UI testing with natural language
4. **Research**: Browse and synthesize information from multiple pages
5. **Monitoring**: Check website status or content changes
6. **Data entry**: Automate repetitive web data entry tasks

## Example Workflows

**Research task:**
```python
task = """
Go to scholar.google.com
Search for 'machine learning computer vision'
Find the most cited paper from 2024
Extract the title, authors, and citation count
"""
result = await gemini_computer_use(task=task, environment="browser")
```

**E-commerce interaction:**
```python
task = """
Navigate to example-shop.com
Search for 'wireless headphones'
Sort by price: low to high
Extract the name and price of the cheapest option
"""
result = await gemini_computer_use(task=task, environment="browser")
```

**Form submission:**
```python
task = """
Go to contact-form.example.com
Fill in:
  Name: Alice Smith
  Email: alice@example.com
  Subject: Product inquiry
  Message: What are your business hours?
Click Submit
Confirm success message appears
"""
result = await gemini_computer_use(task=task, environment="browser")
```

## Debugging

**Enable verbose logging:**
```python
import logging
logging.getLogger("google.genai").setLevel(logging.DEBUG)
```

**Check screenshots:**
Screenshots saved to workspace show Gemini's view at each step.

**Review action log:**
```python
result = await gemini_computer_use(...)
for i, action in enumerate(result.action_log):
    print(f"Step {i+1}: {action}")
```

**Common issues:**
- **Max steps exceeded**: Task too complex, break into smaller tasks
- **Action failed**: Page changed unexpectedly, try again
- **Coordinate mismatch**: Screen size different than expected
- **Rate limit**: Reduce automation frequency

## Migration Guide

**From generic Computer Use:**
```python
# Before
result = await computer_use_tool(
    task="...",
    environment="browser"
)

# After (Gemini)
result = await gemini_computer_use(
    task="...",
    environment="browser"
)
```

**From Claude Computer Use:**
Main differences:
- Different API (Google vs Anthropic)
- Different coordinate system (normalized vs pixel)
- Different screen resolution (1440x900 vs 1024x768)
- Generally faster and cheaper

**Task descriptions are compatible** - just switch the function.

## Performance Tips

**1. Use Flash model:**
Gemini 2.5 Flash is significantly faster and cheaper for most tasks.

**2. Headless mode:**
```python
headless=True  # Faster execution
```

**3. Minimize steps:**
Write clear, direct task descriptions to reduce unnecessary steps.

**4. Reuse browser sessions:**
For multiple related tasks, consider keeping browser open (advanced).

**5. Batch similar tasks:**
Process multiple similar tasks together to amortize startup costs.

## Comparison with Other Approaches

**When to use Gemini Computer Use:**
- ✅ Complex web interactions requiring AI reasoning
- ✅ Natural language task descriptions
- ✅ Tasks requiring visual understanding
- ✅ Multi-step workflows with decision points

**When to use alternatives:**
- ❌ Simple, predefined actions → Use Browser Automation
- ❌ API-accessible data → Use direct API calls
- ❌ Claude-specific features → Use Claude Computer Use
- ❌ Cost-sensitive high-volume → Use traditional web scraping
