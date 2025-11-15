# -*- coding: utf-8 -*-
"""
Tool Code Writer

Writes generated MCP tool wrapper code and custom tools to workspace filesystem.
Creates the directory structure that agents discover via filesystem operations.

Directory Structure Created:
    workspace/
    ├── servers/              # MCP tool wrappers (auto-generated)
    │   ├── __init__.py      # Tool registry
    │   ├── weather/
    │   └── github/
    ├── custom_tools/         # Full Python implementations (user-provided)
    ├── utils/               # Agent-created helper scripts
    └── .mcp/                # Hidden MCP runtime
        ├── client.py
        └── servers.json
"""

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..logger_config import logger
from ..mcp_tools.code_generator import MCPToolCodeGenerator


class ToolCodeWriter:
    """Writes MCP tool code and custom tools to workspace filesystem.

    This class handles:
    - Creating servers/ directory with MCP tool wrappers
    - Copying custom_tools/ if provided
    - Creating empty utils/ for agent scripts
    - Setting up hidden .mcp/ directory for MCP client
    """

    def __init__(self):
        """Initialize the tool code writer."""
        self.generator = MCPToolCodeGenerator()

    def setup_code_based_tools(
        self,
        workspace_path: Path,
        mcp_servers: List[Dict[str, Any]],
        custom_tools_path: Optional[Path] = None,
    ) -> None:
        """Set up complete code-based tools directory structure.

        Args:
            workspace_path: Path to agent workspace
            mcp_servers: List of MCP server configurations
            custom_tools_path: Optional path to custom tools directory to copy

        Example:
            >>> writer = ToolCodeWriter()
            >>> writer.setup_code_based_tools(
            ...     Path("workspace"),
            ...     [{"name": "weather", "tools": [...]}],
            ...     Path("my_custom_tools")
            ... )
        """
        workspace_path = Path(workspace_path)

        logger.info(f"[ToolCodeWriter] Setting up code-based tools in {workspace_path}")

        # Create servers/ directory with MCP wrappers
        self.write_mcp_tools(workspace_path, mcp_servers)

        # Copy custom_tools/ if provided
        if custom_tools_path:
            self.copy_custom_tools(workspace_path, custom_tools_path)
        else:
            # Create empty custom_tools/ with __init__.py
            self.create_empty_custom_tools(workspace_path)

        # Create empty utils/ for agent scripts
        self.create_utils_directory(workspace_path)

        # Create hidden .mcp/ directory with client
        self.create_mcp_client(workspace_path, mcp_servers)

        logger.info("[ToolCodeWriter] Code-based tools setup complete")

    def write_mcp_tools(
        self,
        workspace_path: Path,
        mcp_servers: List[Dict[str, Any]],
    ) -> None:
        """Write MCP tool wrappers to servers/ directory.

        Args:
            workspace_path: Path to agent workspace
            mcp_servers: List of MCP server configurations with tool schemas
        """
        servers_path = workspace_path / "servers"
        servers_path.mkdir(parents=True, exist_ok=True)

        server_names = []

        for server_config in mcp_servers:
            server_name = server_config.get("name")
            if not server_name:
                logger.warning("[ToolCodeWriter] Skipping MCP server without name")
                continue

            tools = server_config.get("tools", [])
            if not tools:
                logger.warning(f"[ToolCodeWriter] No tools found for server '{server_name}'")
                continue

            # Create server directory
            server_dir = servers_path / server_name
            server_dir.mkdir(exist_ok=True)

            # Generate wrapper for each tool
            tool_names = []
            for tool in tools:
                tool_name = tool.get("name")
                if not tool_name:
                    continue

                # Generate wrapper code
                wrapper_code = self.generator.generate_tool_wrapper(
                    server_name,
                    tool_name,
                    tool,
                )

                # Write to file
                tool_file = server_dir / f"{tool_name}.py"
                tool_file.write_text(wrapper_code)

                tool_names.append(tool_name)

            # Generate __init__.py for server
            if tool_names:
                init_code = self.generator.generate_server_init(server_name, tool_names)
                (server_dir / "__init__.py").write_text(init_code)
                server_names.append(server_name)

                logger.info(f"[ToolCodeWriter] Generated {len(tool_names)} tools for '{server_name}' server")

        # Generate servers/__init__.py
        if server_names:
            servers_init_code = self.generator.generate_tools_init(server_names)
            (servers_path / "__init__.py").write_text(servers_init_code)

        logger.info(f"[ToolCodeWriter] Created {len(server_names)} MCP server modules in servers/")

    def copy_custom_tools(
        self,
        workspace_path: Path,
        custom_tools_path: Path,
    ) -> None:
        """Copy custom tools directory to workspace.

        Args:
            workspace_path: Path to agent workspace
            custom_tools_path: Path to source custom tools directory
        """
        if not custom_tools_path.exists():
            logger.warning(f"[ToolCodeWriter] Custom tools path does not exist: {custom_tools_path}")
            return

        dest_path = workspace_path / "custom_tools"

        # Remove existing if present
        if dest_path.exists():
            shutil.rmtree(dest_path)

        # Copy directory
        shutil.copytree(custom_tools_path, dest_path)

        # Ensure __init__.py exists
        init_file = dest_path / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""Custom tools provided by user."""\n')

        logger.info(f"[ToolCodeWriter] Copied custom tools from {custom_tools_path}")

    def create_empty_custom_tools(self, workspace_path: Path) -> None:
        """Create empty custom_tools/ directory with __init__.py.

        Args:
            workspace_path: Path to agent workspace
        """
        custom_tools_path = workspace_path / "custom_tools"
        custom_tools_path.mkdir(exist_ok=True)

        init_file = custom_tools_path / "__init__.py"
        if not init_file.exists():
            init_content = '''"""
Custom Tools Directory

Add your custom Python tools here. Each tool should be a .py file with functions
that agents can import and use.

Example:
    # custom_tools/analyze_data.py
    def analyze_sales(csv_path: str) -> dict:
        """Analyze sales data from CSV file."""
        import pandas as pd
        df = pd.read_csv(csv_path)
        return {
            "total": df["amount"].sum(),
            "average": df["amount"].mean()
        }

Usage:
    from custom_tools.analyze_data import analyze_sales
    result = analyze_sales("sales.csv")
"""
'''
            init_file.write_text(init_content)

        logger.info("[ToolCodeWriter] Created empty custom_tools/ directory")

    def create_utils_directory(self, workspace_path: Path) -> None:
        """Create empty utils/ directory for agent-written scripts.

        Args:
            workspace_path: Path to agent workspace
        """
        utils_path = workspace_path / "utils"
        utils_path.mkdir(exist_ok=True)

        readme_file = utils_path / "README.md"
        if not readme_file.exists():
            readme_content = """# Utils Directory

This directory is for **your scripts** - helper functions and workflows you create.

## Purpose

Use utils/ to:
- Combine multiple tools into workflows
- Write async operations for parallel tool calls
- Filter large datasets before returning results
- Create reusable helper functions

## Examples

### Simple Tool Composition
```python
# utils/weather_report.py
from servers.weather import get_forecast, get_current

def daily_report(city: str) -> str:
    current = get_current(city)
    forecast = get_forecast(city, days=3)

    report = f"Current: {current['temp']}°F\\n"
    report += f"3-day forecast: {forecast['summary']}"
    return report
```

### Async Operations
```python
# utils/multi_city_weather.py
import asyncio
from servers.weather import get_forecast

async def get_forecasts(cities: list) -> dict:
    tasks = [get_forecast(city) for city in cities]
    results = await asyncio.gather(*tasks)
    return dict(zip(cities, results))
```

### Data Filtering
```python
# utils/qualified_leads.py
from servers.salesforce import get_records

def get_top_leads(limit: int = 50) -> list:
    # Fetch 10k records
    all_records = get_records(object="Lead", limit=10000)

    # Filter in execution environment (not sent to LLM)
    qualified = [r for r in all_records if r["score"] > 80]

    # Return only top results
    return sorted(qualified, key=lambda x: x["score"], reverse=True)[:limit]
```

## Running Utils

Call from Python:
```python
from utils.weather_report import daily_report
report = daily_report("San Francisco")
print(report)
```

Or execute via command line:
```bash
python utils/weather_report.py "San Francisco"
```
"""
            readme_file.write_text(readme_content)

        logger.info("[ToolCodeWriter] Created utils/ directory for agent scripts")

    def create_mcp_client(
        self,
        workspace_path: Path,
        mcp_servers: List[Dict[str, Any]],
    ) -> None:
        """Create hidden .mcp/ directory with client code and server configs.

        Args:
            workspace_path: Path to agent workspace
            mcp_servers: List of MCP server configurations
        """
        mcp_path = workspace_path / ".mcp"
        mcp_path.mkdir(exist_ok=True)

        # Generate MCP client code
        client_code = self.generator.generate_mcp_client()
        (mcp_path / "client.py").write_text(client_code)

        # Write server configurations (filtered to only include necessary info)
        server_configs = {}
        for server in mcp_servers:
            server_name = server.get("name")
            if server_name:
                # Only include connection info, not tool schemas
                server_configs[server_name] = {
                    "type": server.get("type"),
                    "command": server.get("command"),
                    "args": server.get("args"),
                    "env": server.get("env", {}),
                    "url": server.get("url"),
                }

        with open(mcp_path / "servers.json", "w") as f:
            json.dump(server_configs, f, indent=2)

        logger.info(f"[ToolCodeWriter] Created .mcp/ directory with client and {len(server_configs)} server configs")
