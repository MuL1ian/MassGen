# UI-TARS Computer Use Tool

## Overview

The UI-TARS Computer Use tool enables autonomous GUI automation using ByteDance's UI-TARS-1.5 model. This powerful vision-language model can analyze screenshots, reason about tasks, and generate actions to control browsers or Linux desktop environments.

## Key Features

- **Vision-Guided Automation**: Analyzes screenshots to understand GUI state
- **Reasoning Capabilities**: Provides thought process before each action
- **Multi-Environment Support**: Works with browsers (Playwright) or Docker containers
- **Rich Action Set**: Click, double-click, right-click, type, keyboard shortcuts, scroll, drag
- **State-of-the-Art Performance**: Achieves 42.5% on OSWorld, 84.8% on WebVoyager benchmarks

## Prerequisites

### Required

1. **UI-TARS API Access**:
   - Deploy UI-TARS-1.5-7B on HuggingFace Inference Endpoints
   - Get your HuggingFace API token
   - Set environment variables:
     ```bash
     export UI_TARS_API_KEY="hf_xxxxxxxxxxxxx"
     export UI_TARS_ENDPOINT="https://xxx.endpoints.huggingface.cloud"
     ```

2. **Python Dependencies**:
   ```bash
   pip install openai playwright docker
   playwright install
   ```

3. **Optional**:
   ```bash
   pip install ui-tars  # For advanced parsing features
   ```

### For Browser Automation

- Playwright installed: `playwright install`
- Works on any OS with browser support

### For Docker Automation

- Docker container with:
  - X11 virtual display (Xvfb)
  - xdotool for GUI control
  - scrot or imagemagick for screenshots
  - Desktop environment (e.g., Xfce)

## Quick Start

### Browser Automation

```python
from massgen.tool import ui_tars_computer_use
import asyncio

async def main():
    result = await ui_tars_computer_use(
        task="Search for 'Python asyncio' on Google and click the first result",
        environment="browser",
        initial_url="https://google.com",
        huggingface_endpoint="https://xxx.endpoints.huggingface.cloud"
    )
    print(result)

asyncio.run(main())
```

### Docker/Linux Automation

```python
from massgen.tool import ui_tars_computer_use
import asyncio

async def main():
    result = await ui_tars_computer_use(
        task="Open Firefox and browse to https://github.com",
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

### MassGen Configuration

Create `ui_tars_computer_use_example.yaml`:

```yaml
custom_tools:
  - name: custom_tool__ui_tars_computer_use
    implementation_file: massgen/tool/_ui_tars_computer_use/ui_tars_computer_use_tool.py
    function_name: ui_tars_computer_use
    description: >
      Automate browser or desktop GUI tasks using UI-TARS-1.5 vision model.
      Analyzes screenshots and generates actions with reasoning.
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
      environment_config:
        type: object
        description: Additional environment configuration
        required: false
```

Run with MassGen:

```bash
massgen --config ui_tars_computer_use_example.yaml "Open Google and search for AI news"
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `task` | str | Required | Detailed description of the task to perform |
| `environment` | str | "browser" | Environment type: "browser" or "linux" |
| `display_width` | int | 1440 | Display width in pixels |
| `display_height` | int | 900 | Display height in pixels |
| `max_iterations` | int | 25 | Maximum number of action iterations |
| `initial_url` | str | None | Initial URL to navigate to (browser only) |
| `huggingface_endpoint` | str | None | HuggingFace Inference Endpoint URL |
| `environment_config` | dict | {} | Additional configuration (see below) |
| `agent_cwd` | str | None | Agent's current working directory |
| `model` | str | "ui-tars-1.5" | Model name identifier |

### Environment Config Options

**For Browser (`environment="browser"`):**
- `headless` (bool): Run browser in headless mode (default: False)
- `browser_type` (str): Browser to use - "chromium", "firefox", "webkit" (default: "chromium")

**For Docker (`environment="linux"`):**
- `container_name` (str): Docker container name (default: "cua-container")
- `display` (str): X11 display number (default: ":99")

## UI-TARS Action Format

UI-TARS responds with:

1. **Thought**: Reasoning about current state and next action
2. **Action**: Specific action to execute

### Supported Actions

- `click(start_box='(x,y)')`: Click at coordinates
- `double_click(start_box='(x,y)')`: Double-click
- `right_click(start_box='(x,y)')`: Right-click (context menu)
- `type(text='<text>')`: Type text
- `key(text='<key>')`: Press keyboard key (e.g., 'Return', 'ctrl+c', 'Tab')
- `scroll(direction='<dir>')`: Scroll (up/down/left/right)
- `drag(start_box='(x1,y1)', end_box='(x2,y2)')`: Drag operation
- `WAIT`: Wait for page to load
- `DONE`: Task completed successfully
- `FAIL`: Task cannot be completed

## Output Format

The tool returns an `ExecutionResult` with JSON data:

```json
{
  "success": true,
  "operation": "ui_tars_computer_use",
  "task": "Search for Python documentation",
  "environment": "browser",
  "iterations": 5,
  "status": "done",
  "action_log": [
    {
      "iteration": 1,
      "thought": "I need to click on the search box to enter text",
      "action": "click(start_box='(500,300)')",
      "parsed_action": {"type": "click", "x": 500, "y": 300}
    },
    {
      "iteration": 2,
      "thought": "Now I'll type the search query",
      "action": "type(text='Python documentation')",
      "parsed_action": {"type": "type", "text": "Python documentation"}
    }
  ]
}
```

## Use Cases

### Web Automation
- Form filling and submission
- Data extraction from websites
- E-commerce automation
- Web testing and validation

### Desktop Automation
- Application installation and configuration
- File management operations
- System settings configuration
- Cross-application workflows

### Complex Workflows
- Multi-step research tasks
- Documentation gathering
- Competitive analysis
- Content aggregation

## HuggingFace Deployment Guide

### 1. Deploy UI-TARS-1.5 Model

1. Go to [HuggingFace Inference Endpoints](https://endpoints.huggingface.co/catalog)
2. Search for "UI-TARS-1.5-7B" and click Import Model
3. Configure:
   - **Hardware**: GPU L40S 1GPU 48G (or L4/A100)
   - **Max Input Length**: 65536
   - **Max Batch Prefill Tokens**: 65536
   - **Max Number of Tokens**: 65537
   - **Environment Variables**:
     - `CUDA_GRAPHS=0`
     - `PAYLOAD_LIMIT=8000000`
4. Create Endpoint
5. After deployment, update Container URI to: `ghcr.io/huggingface/text-generation-inference:3.2.1`
6. Copy your endpoint URL

### 2. Configure Environment

Add to `.env` file in MassGen root:

```bash
UI_TARS_API_KEY=hf_xxxxxxxxxxxxx
UI_TARS_ENDPOINT=https://xxx.endpoints.huggingface.cloud
```

## Performance Benchmarks

UI-TARS-1.5 achieves state-of-the-art results:

| Benchmark | Score |
|-----------|-------|
| OSWorld (100 steps) | 42.5% |
| Windows Agent Arena (50 steps) | 42.1% |
| WebVoyager | 84.8% |
| Online-Mind2web | 75.8% |
| Android World | 64.2% |
| ScreenSpot-V2 | 94.2% |
| ScreenSpotPro | 61.6% |

## Cost Estimates

UI-TARS-1.5-7B running on HuggingFace Inference Endpoints:

- **Infrastructure**: ~$1.30/hour (L40S GPU)
- **Per Task**: $0.05-0.20 (depending on complexity)
- **Per Screenshot**: ~$0.01-0.02

*Note: Costs vary based on HuggingFace pricing and task complexity.*

## Troubleshooting

### API Connection Issues

```
Error: UI-TARS API key not found
```
**Solution**: Set `UI_TARS_API_KEY` environment variable with your HuggingFace token.

```
Error: UI-TARS endpoint not found
```
**Solution**: Set `UI_TARS_ENDPOINT` or pass `huggingface_endpoint` parameter.

### Playwright Issues

```
Error: Playwright not installed
```
**Solution**:
```bash
pip install playwright
playwright install
```

### Docker Issues

```
Error: Docker container 'cua-container' not found
```
**Solution**: Create container with:
```bash
cd MassGen/scripts
./setup_docker_cua.sh
```

```
Error: Failed to capture screenshot
```
**Solution**: Ensure X11 is running in container:
```bash
docker exec cua-container ps aux | grep Xvfb
```

### Coordinate Issues

UI-TARS uses absolute coordinates based on screen resolution. If actions seem off-target:

1. Verify display resolution matches: `display_width` and `display_height`
2. For Docker, check container resolution: `xdpyinfo -display :99 | grep dimensions`
3. Ensure no scaling is applied in browser viewport

## Limitations

1. **Computation**: Requires GPU for inference (7B model)
2. **Hallucination**: May occasionally misidentify GUI elements
3. **CAPTCHA**: Can handle simple CAPTCHAs but complex ones may fail
4. **Dynamic Content**: May struggle with rapidly changing interfaces
5. **Model Scale**: 7B model may not perform optimally on very complex game scenarios

## Best Practices

1. **Clear Task Descriptions**: Provide detailed, step-by-step task descriptions
2. **Appropriate Iterations**: Set `max_iterations` based on task complexity
3. **Initial State**: For browser tasks, provide `initial_url` to start from known state
4. **Error Handling**: Monitor action_log for failures and retry if needed
5. **Resource Management**: Clean up browser/container instances after use

## Advanced Features

### Custom Parsing

If you install `ui-tars` package, advanced coordinate processing is available:

```python
from ui_tars.action_parser import parse_action_to_structure_output

parsed = parse_action_to_structure_output(
    response="Action: click(start_box='(100,200)')",
    factor=1000,
    origin_resized_height=1080,
    origin_resized_width=1920,
    model_type="qwen25vl"
)
```

### Coordinate Visualization

For debugging, refer to [UI-TARS coordinates guide](https://github.com/bytedance/UI-TARS/blob/main/README_coordinates.md).

## References

- **GitHub**: https://github.com/bytedance/UI-TARS
- **Paper**: https://arxiv.org/abs/2501.12326
- **Website**: https://seed-tars.com/
- **HuggingFace Model**: https://huggingface.co/ByteDance-Seed/UI-TARS-1.5-7B
- **Deployment Guide**: https://github.com/bytedance/UI-TARS/blob/main/README_deploy.md

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

This tool integrates with UI-TARS-1.5 which is licensed under Apache-2.0.

## Support

For issues related to:
- **This tool**: Open issue in MassGen repository
- **UI-TARS model**: Visit https://github.com/bytedance/UI-TARS
- **HuggingFace deployment**: Contact HuggingFace support
- **Community**: Join Discord at https://discord.gg/pTXwYVjfcs
