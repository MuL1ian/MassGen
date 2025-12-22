# UI-TARS Computer Use Tool

## Purpose

The UI-TARS Computer Use tool provides autonomous GUI automation capabilities using ByteDance's UI-TARS-1.5 vision-language model. The model analyzes screenshots, reasons about the task, and generates actions to control browsers or Linux desktop environments.

## Model

- **Name**: UI-TARS-1.5-7B
- **Provider**: ByteDance
- **Type**: Vision-Language Model with Reasoning
- **Base**: Qwen2.5-VL
- **Deployment**: HuggingFace Inference Endpoints
- **API**: OpenAI-compatible Chat Completions

## Key Capabilities

1. **Vision-Guided Control**: Analyzes screenshots to understand GUI state
2. **Chain-of-Thought Reasoning**: Provides thought process before actions
3. **Multi-Environment**: Supports browser and Linux desktop automation
4. **Rich Actions**: Click, type, scroll, drag, keyboard shortcuts, etc.
5. **State-of-the-Art**: Top performance on OSWorld, WebVoyager, AndroidWorld

## Usage

### Function Signature

```python
async def ui_tars_computer_use(
    task: str,
    environment: str = "browser",
    display_width: int = 1440,
    display_height: int = 900,
    max_iterations: int = 25,
    initial_url: Optional[str] = None,
    environment_config: Optional[Dict[str, Any]] = None,
    agent_cwd: Optional[str] = None,
    model: str = "ui-tars-1.5",
    huggingface_endpoint: Optional[str] = None,
) -> ExecutionResult
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `task` | str | Yes | - | Detailed task description |
| `environment` | str | No | "browser" | "browser" or "linux" (Docker) |
| `display_width` | int | No | 1440 | Display width in pixels |
| `display_height` | int | No | 900 | Display height in pixels |
| `max_iterations` | int | No | 25 | Maximum action iterations |
| `initial_url` | str | No | None | Starting URL (browser only) |
| `environment_config` | dict | No | {} | Environment-specific config |
| `agent_cwd` | str | No | None | Current working directory |
| `model` | str | No | "ui-tars-1.5" | Model identifier |
| `huggingface_endpoint` | str | No | None | HF Inference Endpoint URL |

### Environment Configuration

**Browser Mode (`environment="browser"`):**
```python
environment_config = {
    "headless": False,  # Run headless or with UI
    "browser_type": "chromium"  # chromium, firefox, webkit
}
```

**Linux/Docker Mode (`environment="linux"`):**
```python
environment_config = {
    "container_name": "cua-container",  # Docker container name
    "display": ":99"  # X11 display number
}
```

## Prerequisites

### Required Environment Variables

```bash
# HuggingFace API token
UI_TARS_API_KEY=hf_xxxxxxxxxxxxx

# HuggingFace Inference Endpoint URL
UI_TARS_ENDPOINT=https://xxx.endpoints.huggingface.cloud
```

### Python Dependencies

```bash
# Core dependencies
pip install openai playwright docker

# Install browsers
playwright install

# Optional: Advanced parsing
pip install ui-tars
```

### Docker Setup (for Linux environment)

```bash
# Run setup script
cd MassGen/scripts
./setup_docker_cua.sh

# Verify container is running
docker ps | grep cua-container
```

## Examples

### Example 1: Browser Search

```python
from massgen.tool import ui_tars_computer_use
import asyncio

async def main():
    result = await ui_tars_computer_use(
        task="Search for 'Python asyncio tutorial' on Google and click the first result",
        environment="browser",
        initial_url="https://www.google.com",
        display_width=1920,
        display_height=1080,
        huggingface_endpoint="https://xxx.endpoints.huggingface.cloud"
    )
    print(result)

asyncio.run(main())
```

### Example 2: Docker GUI Automation

```python
from massgen.tool import ui_tars_computer_use
import asyncio

async def main():
    result = await ui_tars_computer_use(
        task="Open Firefox, navigate to GitHub, and search for 'ui-tars'",
        environment="linux",
        environment_config={
            "container_name": "cua-container",
            "display": ":99"
        },
        huggingface_endpoint="https://xxx.endpoints.huggingface.cloud"
    )
    print(result)

asyncio.run(main())
```

### Example 3: Form Filling

```python
result = await ui_tars_computer_use(
    task="""
    1. Navigate to the contact form
    2. Fill in Name: John Doe
    3. Fill in Email: john@example.com
    4. Fill in Message: Hello, I'm interested in your product
    5. Click Submit button
    """,
    environment="browser",
    initial_url="https://example.com/contact",
    max_iterations=30,
    huggingface_endpoint="https://xxx.endpoints.huggingface.cloud"
)
```

### Example 4: MassGen YAML Configuration

```yaml
custom_tools:
  - name: custom_tool__ui_tars_computer_use
    implementation_file: massgen/tool/_ui_tars_computer_use/ui_tars_computer_use_tool.py
    function_name: ui_tars_computer_use
    description: |
      Automate browser or desktop tasks using UI-TARS-1.5 vision model.
      Provides reasoning and action generation for GUI automation.
    parameters:
      task:
        type: string
        description: Detailed task description
        required: true
      environment:
        type: string
        description: Environment type (browser or linux)
        default: browser
      display_width:
        type: integer
        description: Display width in pixels
        default: 1440
      display_height:
        type: integer
        description: Display height in pixels
        default: 900
      max_iterations:
        type: integer
        description: Maximum action iterations
        default: 25
      initial_url:
        type: string
        description: Initial URL for browser
        required: false
      huggingface_endpoint:
        type: string
        description: HuggingFace Inference Endpoint URL
        required: true
```

Run with:
```bash
massgen --config ui_tars_config.yaml "Search for AI news on Hacker News"
```

## UI-TARS Action Format

UI-TARS responds with two components:

1. **Thought**: Reasoning about the current state and next action
2. **Action**: Specific action command

### Action Syntax

```
Thought: <reasoning about what to do>
Action: <action_command>
```

### Available Actions

| Action | Syntax | Description |
|--------|--------|-------------|
| Click | `click(start_box='(x,y)')` | Click at coordinates |
| Double-click | `double_click(start_box='(x,y)')` | Double-click at coordinates |
| Right-click | `right_click(start_box='(x,y)')` | Right-click (context menu) |
| Type | `type(text='<text>')` | Type text input |
| Keyboard | `key(text='<key>')` | Press keyboard key |
| Scroll | `scroll(direction='<dir>')` | Scroll (up/down/left/right) |
| Drag | `drag(start_box='(x1,y1)', end_box='(x2,y2)')` | Drag operation |
| Wait | `WAIT` | Wait for page load |
| Done | `DONE` | Task completed successfully |
| Fail | `FAIL` | Task cannot be completed |

### Keyboard Keys

Examples: `Return`, `Tab`, `Escape`, `ctrl+c`, `ctrl+v`, `alt+Tab`, `shift+Tab`

### Example Response

```
Thought: I need to click on the search box at the top of the page to enter the search query.
Action: click(start_box='(500,120)')
```

## Output Format

### Success Response

```json
{
  "success": true,
  "operation": "ui_tars_computer_use",
  "task": "Search for Python documentation",
  "environment": "browser",
  "iterations": 8,
  "status": "done",
  "action_log": [
    {
      "iteration": 1,
      "thought": "I need to click on the search box",
      "action": "click(start_box='(500,300)')",
      "parsed_action": {
        "type": "click",
        "x": 500,
        "y": 300
      }
    },
    {
      "iteration": 2,
      "thought": "Now I'll type the search query",
      "action": "type(text='Python documentation')",
      "parsed_action": {
        "type": "type",
        "text": "Python documentation"
      }
    }
  ]
}
```

### Error Response

```json
{
  "success": false,
  "operation": "ui_tars_computer_use",
  "error": "Docker container 'cua-container' not found",
  "task": "Open Firefox",
  "environment": "linux"
}
```

## HuggingFace Deployment

### Step 1: Deploy Model

1. Go to [HuggingFace Inference Endpoints](https://endpoints.huggingface.co/catalog)
2. Search for "UI-TARS-1.5-7B" by ByteDance-Seed
3. Click "Import Model"
4. Configure deployment:

**Hardware:**
- GPU: L40S 1GPU 48G (recommended)
- Alternatives: Nvidia L4, A100

**Container Configuration:**
- Max Input Length: 65536
- Max Batch Prefill Tokens: 65536
- Max Number of Tokens: 65537

**Environment Variables:**
```
CUDA_GRAPHS=0
PAYLOAD_LIMIT=8000000
```

5. Create Endpoint
6. After deployment completes, go to Settings > Container
7. Update Container URI to: `ghcr.io/huggingface/text-generation-inference:3.2.1`
8. Click "Update Endpoint"

### Step 2: Get Endpoint URL

1. Go to your endpoint details page
2. Copy the endpoint URL (e.g., `https://xxx.endpoints.huggingface.cloud`)
3. Get your HuggingFace API token from [Settings > Access Tokens](https://huggingface.co/settings/tokens)

### Step 3: Configure MassGen

Add to `.env` file in MassGen root directory:

```bash
UI_TARS_API_KEY=hf_xxxxxxxxxxxxx
UI_TARS_ENDPOINT=https://xxx.endpoints.huggingface.cloud
```

## Performance Benchmarks

UI-TARS-1.5 achieves state-of-the-art results across multiple benchmarks:

### Computer Use

| Benchmark | UI-TARS-1.5 | Claude 3.7 | GPT-4V | Gemini 2.0 |
|-----------|-------------|------------|--------|------------|
| OSWorld (100 steps) | **42.5%** | 38.1% | 28.0% | 36.4% |
| Windows Agent Arena (50 steps) | **42.1%** | 29.8% | - | - |

### Browser Use

| Benchmark | UI-TARS-1.5 | Claude 3.7 | GPT-4V | Gemini 2.0 |
|-----------|-------------|------------|--------|------------|
| WebVoyager | **84.8%** | 87.0% | 84.1% | 87.0% |
| Online-Mind2web | **75.8%** | 71.0% | 62.9% | 71.0% |

### Phone Use

| Benchmark | UI-TARS-1.5 | Gemini 2.0 |
|-----------|-------------|------------|
| Android World | **64.2%** | 59.5% |

### GUI Grounding

| Benchmark | UI-TARS-1.5 | Claude 3.7 | GPT-4V | Gemini 2.0 |
|-----------|-------------|------------|--------|------------|
| ScreenSpot-V2 | **94.2%** | 91.6% | 87.6% | 87.9% |
| ScreenSpotPro | **61.6%** | 43.6% | 27.7% | 23.4% |

## Cost Estimation

### HuggingFace Infrastructure Costs

- **GPU L40S**: ~$1.30/hour
- **GPU A100**: ~$4.50/hour
- **GPU L4**: ~$0.60/hour

### Per-Task Costs (L40S)

- **Simple tasks** (5-10 iterations): $0.05-0.10
- **Medium tasks** (10-20 iterations): $0.10-0.15
- **Complex tasks** (20-30 iterations): $0.15-0.25

### Screenshot Processing

- Per screenshot: ~$0.01-0.02
- Depends on resolution and token count

*Note: Costs based on HuggingFace pricing as of January 2025.*

## Limitations

1. **Computational Requirements**: Requires GPU for inference
2. **Hallucination**: May occasionally misidentify GUI elements
3. **Dynamic Content**: May struggle with rapidly changing interfaces
4. **Model Scale**: 7B model is optimized for general computer use, not specifically for games
5. **CAPTCHA**: Can handle simple CAPTCHAs but complex ones may fail
6. **Coordinate Precision**: Uses absolute coordinates which may need adjustment for different resolutions

## Troubleshooting

### API Issues

**Problem**: `UI-TARS API key not found`

**Solution**: Set environment variable:
```bash
export UI_TARS_API_KEY="hf_xxxxxxxxxxxxx"
```

**Problem**: `UI-TARS endpoint not found`

**Solution**: Set endpoint or pass parameter:
```bash
export UI_TARS_ENDPOINT="https://xxx.endpoints.huggingface.cloud"
```

### Browser Issues

**Problem**: `Playwright not installed`

**Solution**:
```bash
pip install playwright
playwright install
```

**Problem**: Browser fails to start

**Solution**: Try different browser:
```python
environment_config={"browser_type": "firefox"}
```

### Docker Issues

**Problem**: `Docker container not found`

**Solution**: Create container:
```bash
cd MassGen/scripts
./setup_docker_cua.sh
```

**Problem**: `Failed to capture screenshot`

**Solution**: Verify X11 is running:
```bash
docker exec cua-container ps aux | grep Xvfb
docker exec cua-container bash -c "DISPLAY=:99 xdpyinfo"
```

**Problem**: Actions seem off-target

**Solution**: Verify container resolution:
```bash
docker exec cua-container bash -c "DISPLAY=:99 xdpyinfo | grep dimensions"
```

### Coordinate Issues

**Problem**: Clicks are off-target

**Solutions**:
1. Verify `display_width` and `display_height` match actual resolution
2. Check for browser zoom or scaling
3. For Docker, ensure container resolution matches parameters

## Best Practices

### Task Descriptions

1. **Be Specific**: Provide clear, detailed instructions
2. **Step-by-Step**: Break complex tasks into steps
3. **Context**: Include relevant context about the goal
4. **Constraints**: Mention any constraints or requirements

### Iteration Limits

- Simple tasks: 10-15 iterations
- Medium tasks: 20-25 iterations
- Complex tasks: 30-40 iterations

### Error Handling

```python
result = await ui_tars_computer_use(task=task, ...)
data = json.loads(result.output_blocks[0].data)

if data["success"]:
    print(f"Task completed in {data['iterations']} iterations")
    for step in data["action_log"]:
        print(f"{step['iteration']}: {step['thought']}")
else:
    print(f"Task failed: {data.get('error', data.get('status'))}")
```

### Resource Management

Always clean up resources:

```python
try:
    result = await ui_tars_computer_use(...)
finally:
    # Cleanup is automatic, but ensure Docker containers are stopped if needed
    pass
```

## Advanced Features

### Custom Action Parsing

With `ui-tars` package installed:

```python
from ui_tars.action_parser import parse_action_to_structure_output

response = "Thought: Click button\nAction: click(start_box='(100,200)')"
parsed = parse_action_to_structure_output(
    response,
    factor=1000,
    origin_resized_height=1080,
    origin_resized_width=1920,
    model_type="qwen25vl"
)
```

### Coordinate Visualization

For debugging coordinate issues, see: https://github.com/bytedance/UI-TARS/blob/main/README_coordinates.md

## Related Projects

- **UI-TARS Desktop**: https://github.com/bytedance/UI-TARS-desktop
- **Midscene.js** (Browser Automation): https://github.com/web-infra-dev/Midscene

## References

- **GitHub Repository**: https://github.com/bytedance/UI-TARS
- **Research Paper**: https://arxiv.org/abs/2501.12326
- **Official Website**: https://seed-tars.com/
- **HuggingFace Model**: https://huggingface.co/ByteDance-Seed/UI-TARS-1.5-7B
- **Deployment Guide**: https://github.com/bytedance/UI-TARS/blob/main/README_deploy.md
- **Discord Community**: https://discord.gg/pTXwYVjfcs

## Citation

```bibtex
@article{qin2025ui,
  title={UI-TARS: Pioneering Automated GUI Interaction with Native Agents},
  author={Qin, Yujia and Ye, Yining and Fang, Junjie and Wang, Haoming and Liang, Shihao
  and Tian, Shizuo and Zhang, Junda and Li, Jiahao and Li, Yunxin and Huang, Shijue
  and others},
  journal={arXiv preprint arXiv:2501.12326},
  year={2025}
}
```

## License

This tool integrates with UI-TARS-1.5 which is licensed under Apache-2.0 license.
