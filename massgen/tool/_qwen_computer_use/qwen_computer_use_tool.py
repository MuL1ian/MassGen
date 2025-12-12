# -*- coding: utf-8 -*-
"""
Qwen Computer Use tool for automating browser interactions using Qwen3-VL-235B-A22B-Thinking model.

This tool implements browser control using Qwen's vision-language model which allows the model to:
- Control a web browser (click, type, scroll, navigate)
- Analyze screenshots and decide actions
- Perform multi-step workflows
- Handle safety checks and confirmations
"""

import asyncio
import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from massgen.logger_config import logger
from massgen.tool._result import ExecutionResult, TextContent

# Optional dependencies with graceful fallback
try:
    from playwright.async_api import async_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

try:
    import docker

    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    docker = None


# Screen dimensions
SCREEN_WIDTH = 1440
SCREEN_HEIGHT = 900


def encode_image_base64(image_bytes: bytes) -> str:
    """Encode image bytes to base64 string for API calls."""
    return base64.b64encode(image_bytes).decode("utf-8")


def take_screenshot_docker(container, display: str = ":99") -> bytes:
    """Take a screenshot from Docker container using scrot.

    Args:
        container: Docker container instance
        display: X11 display number

    Returns:
        Screenshot as bytes
    """
    import time

    # Remove old screenshot if exists
    container.exec_run("rm -f /tmp/screenshot.png")

    # Take screenshot with scrot
    result = container.exec_run(
        "scrot /tmp/screenshot.png",
        environment={"DISPLAY": display},
    )

    if result.exit_code != 0:
        logger.error(f"Screenshot command failed: {result.output}")
        # Try alternative method with import
        result = container.exec_run(
            "import -window root /tmp/screenshot.png",
            environment={"DISPLAY": display},
        )
        if result.exit_code != 0:
            logger.error(f"Alternative screenshot also failed: {result.output}")
            return b""

    # Small delay to ensure file is written
    time.sleep(0.2)

    # Verify screenshot exists and has content
    check_result = container.exec_run("ls -lh /tmp/screenshot.png")
    logger.info(f"Screenshot file info: {check_result.output.decode()}")

    # Read the screenshot
    read_result = container.exec_run("cat /tmp/screenshot.png", stdout=True)
    if read_result.exit_code != 0:
        logger.error(f"Failed to read screenshot: {read_result.output}")
        return b""

    screenshot_bytes = read_result.output

    # Verify we got actual image data
    if len(screenshot_bytes) < 1000:  # PNG should be at least a few KB
        logger.error(f"Screenshot too small ({len(screenshot_bytes)} bytes), likely invalid")
        return b""

    # Verify PNG header
    if not screenshot_bytes.startswith(b"\x89PNG"):
        logger.error("Screenshot does not have valid PNG header")
        return b""

    logger.info(f"Successfully captured screenshot: {len(screenshot_bytes)} bytes")
    return screenshot_bytes


async def execute_browser_action(page, action: Dict[str, Any], screen_width: int, screen_height: int) -> Dict[str, Any]:
    """Execute a browser action using Playwright.

    Args:
        page: Playwright page instance
        action: Action dictionary with type and parameters
        screen_width: Screen width in pixels
        screen_height: Screen height in pixels

    Returns:
        Result dictionary
    """
    try:
        action_type = action.get("type")
        logger.info(f"     Executing action: {action_type}")

        if action_type == "click":
            x_raw = action.get("x", 0)
            y_raw = action.get("y", 0)
            x = x_raw
            y = y_raw
            button = action.get("button", "left")  # Default to left click, can be "left", "right", "middle"

            logger.info(f"     Raw click coordinates from model: x={x_raw}, y={y_raw}")

            # Handle array format [x, y] from model
            if isinstance(x, list) and len(x) >= 2:
                y = x[1]
                x = x[0]
                logger.info(f"     Extracted from array: x={x}, y={y}")

            # Map button number to button name for Playwright
            if isinstance(button, int):
                button = {1: "left", 2: "middle", 3: "right"}.get(button, "left")

            logger.info(f"     Final click coordinates: x={x}, y={y} (screen: {screen_width}x{screen_height})")

            # Wait for page to be stable before clicking
            await asyncio.sleep(0.2)
            await page.mouse.click(x, y, button=button)
            # Wait after click for page to react
            await asyncio.sleep(0.5)
            logger.info(f"     Clicked at ({x}, {y}) with button={button}")

        elif action_type == "type":
            text = action.get("text", "")
            x_raw = action.get("x")
            y_raw = action.get("y")
            x = x_raw
            y = y_raw

            logger.info(f"     Raw type coordinates from model: x={x_raw}, y={y_raw}")

            # Handle array format [x, y] from model
            if isinstance(x, list) and len(x) >= 2:
                y = x[1]
                x = x[0]
                logger.info(f"     Extracted from array: x={x}, y={y}")
            # Extract from array if y is also an array (invalid format from model)
            if isinstance(y, list) and len(y) >= 1:
                y = y[0]
            # Ensure numeric types
            if x is not None:
                x = int(float(x)) if not isinstance(x, int) else x
            if y is not None:
                y = int(float(y)) if not isinstance(y, int) else y

            if x is not None and y is not None:
                logger.info(f"     Clicking at ({x}, {y}) before typing")
                await page.mouse.click(x, y)
                # Wait longer for element to focus
                await asyncio.sleep(0.5)

            await page.keyboard.type(text, delay=50)  # Add 50ms delay between keystrokes
            logger.info(f"     Typed: {text}")
            # Wait for text to appear in UI
            await asyncio.sleep(0.5)

        elif action_type == "scroll":
            direction = action.get("direction", "down")
            amount = action.get("amount", 300)
            if direction == "down":
                await page.evaluate(f"window.scrollBy(0, {amount})")
            elif direction == "up":
                await page.evaluate(f"window.scrollBy(0, -{amount})")
            elif direction == "left":
                await page.evaluate(f"window.scrollBy(-{amount}, 0)")
            elif direction == "right":
                await page.evaluate(f"window.scrollBy({amount}, 0)")
            logger.info(f"     Scrolled {direction} by {amount}px")

        elif action_type == "navigate":
            url = action.get("url", "")
            try:
                # Use domcontentloaded - networkidle is too strict for sites with continuous network activity
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                # Wait for initial render
                await asyncio.sleep(2)
                logger.info(f"     Navigated to: {url}")
            except Exception as e:
                logger.warning(f"     Navigation issue for {url}: {e}, proceeding anyway")

        elif action_type == "go_back":
            await page.go_back()
            logger.info("     Went back")

        elif action_type == "go_forward":
            await page.go_forward()
            logger.info("     Went forward")

        elif action_type == "wait":
            duration = action.get("duration", 1)
            await asyncio.sleep(duration)
            logger.info(f"     Waited {duration} seconds")

        elif action_type == "key":
            key = action.get("key", "")
            # Normalize common key names (Playwright expects capitalized keys)
            key_map = {
                "enter": "Enter",
                "return": "Enter",
                "escape": "Escape",
                "esc": "Escape",
                "tab": "Tab",
                "space": "Space",
                "backspace": "Backspace",
                "delete": "Delete",
                "arrowup": "ArrowUp",
                "arrowdown": "ArrowDown",
                "arrowleft": "ArrowLeft",
                "arrowright": "ArrowRight",
            }
            normalized_key = key_map.get(key.lower(), key)
            await page.keyboard.press(normalized_key)
            logger.info(f"     Pressed key: {normalized_key}")

        else:
            logger.warning(f"     Unknown action type: {action_type}")
            return {"error": f"Unknown action type: {action_type}"}

        # Wait for dynamic content and network activity to settle
        try:
            # Wait for network to be idle (no requests for 500ms)
            await page.wait_for_load_state("networkidle", timeout=3000)
            # Wait additional time for visual updates to render
            await asyncio.sleep(0.5)
        except Exception:
            # If timeout, wait longer for any pending updates
            await asyncio.sleep(1.5)

        return {"success": True}

    except Exception as e:
        logger.error(f"Error executing action {action.get('type')}: {e}")
        return {"error": str(e)}


def execute_docker_action(container, action: Dict[str, Any], screen_width: int, screen_height: int, display: str = ":99") -> Dict[str, Any]:
    """Execute an action in Docker using xdotool.

    Args:
        container: Docker container instance
        action: Action dictionary with type and parameters
        screen_width: Screen width in pixels
        screen_height: Screen height in pixels
        display: X11 display number

    Returns:
        Result dictionary
    """
    import time

    try:
        action_type = action.get("type")
        logger.info(f"     Docker executing action: {action_type}")

        if action_type == "click":
            x = action.get("x", 0)
            y = action.get("y", 0)
            button = action.get("button", 1)  # Default to left click (1), 3 is right click
            # Handle array format [x, y] from model
            if isinstance(x, list) and len(x) >= 2:
                y = x[1]
                x = x[0]
            # Move mouse first
            container.exec_run(
                f"xdotool mousemove --sync {x} {y}",
                environment={"DISPLAY": display},
            )
            time.sleep(0.1)  # Small delay to ensure mouse position updates
            # Then click
            container.exec_run(
                f"xdotool click {button}",
                environment={"DISPLAY": display},
            )
            logger.info(f"     Docker clicked at ({x}, {y}) with button {button}")

        elif action_type == "type":
            text = action.get("text", "")
            x = action.get("x")
            y = action.get("y")
            # Handle array format [x, y] from model
            if isinstance(x, list) and len(x) >= 2:
                y = x[1]
                x = x[0]
            if x is not None and y is not None:
                # Move mouse first
                container.exec_run(
                    f"xdotool mousemove --sync {x} {y}",
                    environment={"DISPLAY": display},
                )
                time.sleep(0.1)  # Small delay to ensure mouse position updates
                # Then click
                container.exec_run(
                    "xdotool click 1",
                    environment={"DISPLAY": display},
                )
                time.sleep(0.1)
            escaped_text = text.replace("'", "'\\''")
            container.exec_run(
                f"xdotool type '{escaped_text}'",
                environment={"DISPLAY": display},
            )
            logger.info(f"     Docker typed: {text}")

        elif action_type == "scroll":
            direction = action.get("direction", "down")
            if direction == "down":
                cmd = "xdotool key Page_Down"
            elif direction == "up":
                cmd = "xdotool key Page_Up"
            elif direction == "left":
                cmd = "xdotool key Left Left Left"
            elif direction == "right":
                cmd = "xdotool key Right Right Right"
            else:
                cmd = "xdotool key Page_Down"
            container.exec_run(cmd, environment={"DISPLAY": display})
            logger.info(f"     Docker scrolled {direction}")

        elif action_type == "navigate":
            url = action.get("url", "")
            container.exec_run("xdotool key ctrl+l", environment={"DISPLAY": display})
            time.sleep(0.5)
            escaped_url = url.replace("'", "'\\''")
            container.exec_run(
                f"xdotool type '{escaped_url}'",
                environment={"DISPLAY": display},
            )
            container.exec_run("xdotool key Return", environment={"DISPLAY": display})
            logger.info(f"     Docker navigated to: {url}")

        elif action_type == "go_back":
            container.exec_run("xdotool key alt+Left", environment={"DISPLAY": display})
            logger.info("     Docker went back")

        elif action_type == "go_forward":
            container.exec_run("xdotool key alt+Right", environment={"DISPLAY": display})
            logger.info("     Docker went forward")

        elif action_type == "wait":
            duration = action.get("duration", 1)
            time.sleep(duration)
            logger.info(f"     Docker waited {duration} seconds")

        elif action_type == "key":
            key = action.get("key", "")
            xdotool_key = key.replace("Control", "ctrl").replace("Shift", "shift").replace("Alt", "alt")
            container.exec_run(
                f"xdotool key {xdotool_key}",
                environment={"DISPLAY": display},
            )
            logger.info(f"     Docker pressed key: {key}")

        else:
            logger.warning(f"     Unknown action type: {action_type}")
            return {"error": f"Unknown action type: {action_type}"}

        time.sleep(0.5)
        return {"success": True}

    except Exception as e:
        logger.error(f"Error executing Docker action {action.get('type')}: {e}")
        return {"error": str(e)}


async def qwen_computer_use(
    task: str,
    environment: str = "browser",
    display_width: int = 1440,
    display_height: int = 900,
    max_iterations: int = 25,
    initial_url: Optional[str] = None,
    environment_config: Optional[Dict[str, Any]] = None,
    agent_cwd: Optional[str] = None,
    model: str = "qwen3-vl-235b-a22b-thinking",
) -> ExecutionResult:
    """
    Execute a browser or Docker automation task using Qwen's vision-language model.

    This tool implements control using Qwen's VL model which analyzes screenshots
    and generates actions to autonomously control a browser or Linux desktop to complete tasks.

    Args:
        task: Description of the task to perform
        environment: Environment type - "browser" or "linux" (Docker)
        display_width: Display width in pixels (default: 1440)
        display_height: Display height in pixels (default: 900)
        max_iterations: Maximum number of action iterations (default: 25)
        initial_url: Initial URL to navigate to (browser only, default: None)
        environment_config: Additional configuration (browser: headless/browser_type, docker: container_name/display)
        agent_cwd: Agent's current working directory
        model: Qwen model to use (default: qwen3-vl-235b-a22b-thinking)

    Returns:
        ExecutionResult containing success status, action log, and results

    Examples:
        # Browser task
        qwen_computer_use("Search for Python documentation on Google", environment="browser")

        # Docker task
        qwen_computer_use(
            "Open Firefox and browse to GitHub",
            environment="linux",
            environment_config={"container_name": "cua-container", "display": ":99"}
        )

    Prerequisites:
        - QWEN_API_KEY environment variable must be set
        - For browser: pip install playwright && playwright install
        - For Docker: Docker container with X11 and xdotool installed
    """
    # Check environment-specific dependencies
    if environment == "linux":
        if not DOCKER_AVAILABLE:
            result = {
                "success": False,
                "operation": "qwen_computer_use",
                "error": "Docker not installed. Install with: pip install docker",
            }
            return ExecutionResult(output_blocks=[TextContent(data=json.dumps(result, indent=2))])
    else:  # browser
        if not PLAYWRIGHT_AVAILABLE:
            result = {
                "success": False,
                "operation": "qwen_computer_use",
                "error": "Playwright not installed. Install with: pip install playwright && playwright install",
            }
            return ExecutionResult(output_blocks=[TextContent(data=json.dumps(result, indent=2))])

    if not OPENAI_AVAILABLE:
        result = {
            "success": False,
            "operation": "qwen_computer_use",
            "error": "OpenAI SDK not installed. Install with: pip install openai",
        }
        return ExecutionResult(output_blocks=[TextContent(data=json.dumps(result, indent=2))])

    environment_config = environment_config or {}

    try:
        # Load environment variables
        script_dir = Path(__file__).parent.parent.parent.parent
        env_path = script_dir / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        else:
            load_dotenv()

        qwen_api_key = os.getenv("QWEN_API_KEY")
        if not qwen_api_key:
            result = {
                "success": False,
                "operation": "qwen_computer_use",
                "error": "Qwen API key not found. Please set QWEN_API_KEY in .env file or environment variable.",
            }
            return ExecutionResult(output_blocks=[TextContent(data=json.dumps(result, indent=2))])

        # Check for custom endpoint (e.g., HuggingFace Inference Endpoint)
        qwen_endpoint = os.getenv("QWEN_HF_ENDPOINT") or os.getenv("QWEN_ENDPOINT")

        # Initialize Qwen client (using OpenAI-compatible API)
        if qwen_endpoint:
            # Custom endpoint (e.g., HuggingFace) - ensure it ends with /v1
            if not qwen_endpoint.endswith("/v1"):
                qwen_endpoint = qwen_endpoint.rstrip("/") + "/v1"
            logger.info(f"Using custom Qwen endpoint: {qwen_endpoint}")
            client = OpenAI(
                api_key=qwen_api_key,
                base_url=qwen_endpoint,
            )
        else:
            # Default to DashScope API
            logger.info("Using DashScope Qwen API")
            client = OpenAI(
                api_key=qwen_api_key,
                base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            )

        # Initialize environment (browser or Docker)
        container = None
        display = None
        page = None
        playwright = None
        browser = None

        if environment == "linux":
            # Docker environment
            logger.info("Initializing Docker environment...")
            container_name = environment_config.get("container_name", "cua-container")
            display = environment_config.get("display", ":99")

            docker_client = docker.from_env()
            try:
                container = docker_client.containers.get(container_name)
                if container.status != "running":
                    logger.info(f"Starting container {container_name}...")
                    container.start()
                logger.info(f"Using Docker container: {container_name} (display {display})")
            except docker.errors.NotFound:
                result = {
                    "success": False,
                    "operation": "qwen_computer_use",
                    "error": f"Docker container '{container_name}' not found. Please create it first.",
                }
                return ExecutionResult(output_blocks=[TextContent(data=json.dumps(result, indent=2))])

            # Take initial screenshot from Docker
            initial_screenshot = take_screenshot_docker(container, display)

            # Verify screenshot was captured
            if not initial_screenshot or len(initial_screenshot) < 1000:
                result = {
                    "success": False,
                    "operation": "qwen_computer_use",
                    "error": f"Failed to capture screenshot from Docker container. Check if X11 display {display} is running and scrot is installed.",
                }
                return ExecutionResult(output_blocks=[TextContent(data=json.dumps(result, indent=2))])

            # Start Firefox and navigate to initial URL if provided (for Docker environment)
            if initial_url:
                logger.info(f"Starting Firefox and navigating to: {initial_url}")
                try:
                    import time

                    # Start Firefox if not running
                    container.exec_run("firefox &", environment={"DISPLAY": display}, detach=True)
                    time.sleep(6)  # Wait longer for Firefox to fully start and render

                    # Navigate to URL: Ctrl+L to focus address bar, type URL, press Enter
                    container.exec_run("xdotool key ctrl+l", environment={"DISPLAY": display})
                    time.sleep(0.8)
                    escaped_url = initial_url.replace("'", "'\\''")
                    container.exec_run(f"xdotool type '{escaped_url}'", environment={"DISPLAY": display})
                    time.sleep(0.8)
                    container.exec_run("xdotool key Return", environment={"DISPLAY": display})
                    time.sleep(5)  # Wait longer for page to fully load and render
                    logger.info("Initial URL navigation complete")
                except Exception as e:
                    logger.warning(f"Failed to navigate to initial URL: {e}")

        else:
            # Browser environment
            logger.info("Initializing browser...")
            playwright = await async_playwright().start()
            browser_type = environment_config.get("browser_type", "chromium")
            headless = environment_config.get("headless", True)

            # Prepare launch options
            launch_options = {"headless": headless}

            # If not headless and DISPLAY is set, log it
            if not headless:
                display_env = os.environ.get("DISPLAY")
                if display_env:
                    logger.info(f"Running browser with DISPLAY={display_env} (environment variable)")
                else:
                    logger.warning("headless=false but DISPLAY not set. Browser window may not be visible.")

            if browser_type == "chromium":
                browser = await playwright.chromium.launch(**launch_options)
            elif browser_type == "firefox":
                browser = await playwright.firefox.launch(**launch_options)
            elif browser_type == "webkit":
                browser = await playwright.webkit.launch(**launch_options)
            else:
                browser = await playwright.chromium.launch(**launch_options)

            context = await browser.new_context(viewport={"width": display_width, "height": display_height})
            page = await context.new_page()

            # Navigate to initial URL or blank page
            if initial_url:
                logger.info(f"Navigating to initial URL: {initial_url}")
                try:
                    # Use domcontentloaded instead of networkidle - many sites have continuous network activity
                    # Increase timeout to 30s for slow-loading sites like Yahoo Finance
                    await page.goto(initial_url, wait_until="domcontentloaded", timeout=30000)
                    # Wait for initial render
                    await asyncio.sleep(2)
                    logger.info(f"Successfully loaded {initial_url}")
                except Exception as e:
                    logger.warning(f"Navigation to {initial_url} encountered issue: {e}")
                    logger.info("Proceeding anyway - page may have partially loaded")
                    # Don't fail entirely - the page might have loaded enough to work with
            else:
                await page.goto("about:blank")

            logger.info(f"Initialized {browser_type} browser ({display_width}x{display_height})")

            # Take initial screenshot from browser
            initial_screenshot = await page.screenshot(type="png")

            # Verify screenshot dimensions match viewport
            import io

            from PIL import Image

            img = Image.open(io.BytesIO(initial_screenshot))
            logger.info(f"Screenshot dimensions: {img.width}x{img.height} (viewport: {display_width}x{display_height})")
            if img.width != display_width or img.height != display_height:
                logger.warning(f"Screenshot size mismatch! Expected {display_width}x{display_height}, got {img.width}x{img.height}")

        # Initialize conversation
        logger.info(f"Task: {task} (environment: {environment}, model: {model})")

        # Encode initial screenshot
        screenshot_base64 = encode_image_base64(initial_screenshot)

        # System prompt for computer use
        system_prompt = f"""You are a computer automation assistant. You can see screenshots and generate actions to control the computer.

IMPORTANT: The screen resolution is {display_width}x{display_height} pixels.
- Valid X coordinates: 0 to {display_width-1}
- Valid Y coordinates: 0 to {display_height-1}

Your task is to analyze the screenshot and the user's request, then generate appropriate actions to complete the task.

Available actions:
- click: Click at coordinates {{"type": "click", "x": <int>, "y": <int>, "button": 1|3}} (button 1=left, 3=right, default=1)
- type: Type text {{"type": "type", "text": "<string>", "x": <int>, "y": <int>}} (x,y optional for focus)
- scroll: Scroll in direction {{"type": "scroll", "direction": "down|up|left|right", "amount": <int>}}
- navigate: Navigate to URL {{"type": "navigate", "url": "<string>"}}
- go_back: Go back {{"type": "go_back"}}
- go_forward: Go forward {{"type": "go_forward"}}
- wait: Wait {{"type": "wait", "duration": <seconds>}}
- key: Press key {{"type": "key", "key": "<key_name>"}}
- done: Task complete {{"type": "done", "result": "<string>"}}

Respond with a JSON object containing:
{{
  "thought": "Your reasoning about what you see and what to do next",
  "actions": [<action_objects>]
}}

IMPORTANT STRATEGIES:
1. Be VERY precise with coordinates - examine the screenshot pixel-by-pixel to identify exact click targets
2. For search boxes and text inputs: USE THE TYPE ACTION DIRECTLY - most modern inputs accept keyboard input without requiring a click first
3. If you see you're repeating the same action (like clicking the same coordinates), try a different approach immediately
4. ALWAYS SCROLL FIRST if you need information below the current view - don't waste time closing banners/overlays
5. If clicking fails after 2 attempts, try: typing directly, pressing Enter, scrolling, or using navigation
6. Close buttons are in the TOP-RIGHT corner of overlays - but only as a last resort

Be precise with coordinates. All coordinates MUST be within the valid range. Analyze the screenshot carefully before deciding actions."""

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Task: {task}\n\nAnalyze this screenshot and generate the next actions."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{screenshot_base64}"},
                    },
                ],
            },
        ]

        # Agent loop
        action_log = []
        iteration_count = 0

        try:
            for i in range(max_iterations):
                iteration_count = i + 1
                logger.info(f"\n--- Qwen Computer Use Turn {iteration_count}/{max_iterations} ---")
                logger.info("Requesting action from Qwen...")

                # Call Qwen API
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.0,  # Deterministic behavior
                    max_tokens=2000,
                )

                assistant_message = response.choices[0].message.content
                logger.info(f"Qwen response: {assistant_message[:200]}...")

                # Parse response
                try:
                    # Try to extract JSON from response
                    response_json = json.loads(assistant_message)
                    thought = response_json.get("thought", "")
                    actions = response_json.get("actions", [])
                except json.JSONDecodeError:
                    # If not valid JSON, try to extract from markdown code block
                    if "```json" in assistant_message:
                        json_str = assistant_message.split("```json")[1].split("```")[0].strip()
                        response_json = json.loads(json_str)
                        thought = response_json.get("thought", "")
                        actions = response_json.get("actions", [])
                    elif "```" in assistant_message:
                        json_str = assistant_message.split("```")[1].split("```")[0].strip()
                        response_json = json.loads(json_str)
                        thought = response_json.get("thought", "")
                        actions = response_json.get("actions", [])
                    else:
                        logger.warning(f"Could not parse JSON from response: {assistant_message}")
                        actions = []
                        thought = assistant_message

                logger.info(f"Thought: {thought}")
                logger.info(f"Actions: {actions}")

                # Check if task is complete
                if any(action.get("type") == "done" for action in actions):
                    final_result = next((action.get("result", "") for action in actions if action.get("type") == "done"), "Task completed")
                    logger.info(f"Task completed: {final_result}")
                    action_log.append(
                        {
                            "iteration": iteration_count,
                            "thought": thought,
                            "status": "completed",
                            "final_output": final_result,
                        },
                    )
                    break

                if not actions:
                    logger.warning("No actions generated, treating as completion")
                    action_log.append(
                        {
                            "iteration": iteration_count,
                            "thought": thought,
                            "status": "completed",
                            "final_output": thought,
                        },
                    )
                    break

                # Execute actions
                logger.info("Executing actions...")
                action_results = []
                for action in actions:
                    if environment == "linux":
                        result = execute_docker_action(container, action, display_width, display_height, display)
                    else:
                        result = await execute_browser_action(page, action, display_width, display_height)
                    action_results.append({"action": action, "result": result})

                # Log actions
                action_log.append(
                    {
                        "iteration": iteration_count,
                        "thought": thought,
                        "actions": action_results,
                    },
                )

                # Capture new screenshot
                logger.info("Capturing new screenshot...")
                if environment == "linux":
                    new_screenshot = take_screenshot_docker(container, display)
                else:
                    new_screenshot = await page.screenshot(type="png")

                screenshot_base64 = encode_image_base64(new_screenshot)

                # Add to conversation - but remove old screenshot to prevent payload bloat
                # Keep only the most recent screenshot in the conversation
                messages.append({"role": "assistant", "content": assistant_message})

                # Remove the previous user message that contained an old screenshot
                # Keep system message (index 0) and remove old user messages with images
                messages = (
                    [messages[0]]
                    + [msg for msg in messages[1:] if msg.get("role") != "user"]
                    + [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Here is the new screenshot after executing the actions. Generate the next actions or indicate if the task is complete."},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/png;base64,{screenshot_base64}"},
                                },
                            ],
                        },
                    ]
                )

                # Truncate conversation history to prevent context overflow
                # Keep system message + last 10 turns (20 messages: 10 user + 10 assistant)
                if len(messages) > 21:  # 1 system + 20 conversation messages
                    messages = [messages[0]] + messages[-20:]  # Keep system + recent 20
                    logger.info("Truncated conversation history to recent 10 turns to manage context size")

        finally:
            # Cleanup
            if environment == "linux":
                logger.info("\nDocker environment cleanup complete")
            else:
                logger.info("\nClosing browser...")
                if browser:
                    await browser.close()
                if playwright:
                    await playwright.stop()

        # Prepare result
        if iteration_count >= max_iterations:
            result = {
                "success": False,
                "operation": "qwen_computer_use",
                "error": f"Reached maximum iterations ({max_iterations})",
                "task": task,
                "environment": environment,
                "model": model,
                "iterations": iteration_count,
                "action_log": action_log,
            }
        else:
            result = {
                "success": True,
                "operation": "qwen_computer_use",
                "task": task,
                "environment": environment,
                "model": model,
                "iterations": iteration_count,
                "action_log": action_log,
            }

        return ExecutionResult(output_blocks=[TextContent(data=json.dumps(result, indent=2))])

    except Exception as e:
        logger.error(f"Qwen computer use failed: {str(e)}")
        import traceback

        traceback.print_exc()
        result = {
            "success": False,
            "operation": "qwen_computer_use",
            "error": f"Qwen computer use failed: {str(e)}",
            "task": task,
            "environment": environment,
        }
        return ExecutionResult(output_blocks=[TextContent(data=json.dumps(result, indent=2))])
