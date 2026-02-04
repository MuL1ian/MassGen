# -*- coding: utf-8 -*-
"""Standalone MCP server that wraps MassGen custom tools.

This module creates a FastMCP server from a ToolManager's registered tools,
allowing any CLI-based backend (Codex, etc.) to access MassGen custom tools
via stdio MCP transport.

Usage (launched by backend):
    fastmcp run massgen/mcp_tools/custom_tools_server.py:create_server -- \
        --tool-specs /path/to/tool_specs.json \
        --allowed-paths /workspace

The tool_specs.json file is written by the backend before launch and contains
the serialized tool configurations needed to reconstruct the ToolManager.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import fastmcp

logger = logging.getLogger(__name__)


async def create_server() -> fastmcp.FastMCP:
    """Factory function to create MCP server from custom tool specs.

    Reads tool specifications from a JSON file (passed via --tool-specs)
    and registers each as an MCP tool backed by the actual Python function.
    """
    parser = argparse.ArgumentParser(description="MassGen Custom Tools MCP Server")
    parser.add_argument(
        "--tool-specs",
        type=str,
        required=True,
        help="Path to JSON file containing tool specifications",
    )
    parser.add_argument(
        "--allowed-paths",
        type=str,
        nargs="*",
        default=[],
        help="Allowed filesystem paths for tool execution",
    )
    parser.add_argument(
        "--agent-id",
        type=str,
        default="unknown",
        help="Agent ID for execution context",
    )
    args = parser.parse_args()

    mcp = fastmcp.FastMCP("massgen_custom_tools")

    # Load tool specs
    specs_path = Path(args.tool_specs)
    if not specs_path.exists():
        logger.error(f"Tool specs file not found: {specs_path}")
        return mcp

    with open(specs_path) as f:
        tool_specs = json.load(f)

    # Import ToolManager and reconstruct tools
    # Add project root to path so imports work
    project_root = str(Path(__file__).resolve().parent.parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from massgen.tool._manager import ToolManager

    tool_manager = ToolManager()

    # Register tools from specs using the same logic as _register_custom_tools
    custom_tools_config = tool_specs.get("custom_tools", [])
    for tool_config in custom_tools_config:
        try:
            if not isinstance(tool_config, dict):
                continue
            path = tool_config.get("path")
            category = tool_config.get("category", "default")

            # Setup category if needed
            if category != "default" and category not in tool_manager.tool_categories:
                tool_manager.setup_category(
                    category_name=category,
                    description=f"Custom {category} tools",
                    enabled=True,
                )

            # Normalize function field to list
            func_field = tool_config.get("function") or tool_config.get("func")
            if isinstance(func_field, str):
                functions = [func_field]
            elif isinstance(func_field, list):
                functions = func_field
            else:
                logger.error(f"Invalid function field: {func_field}")
                continue

            # Normalize name field
            name_field = tool_config.get("name")
            if name_field is None:
                names = [None] * len(functions)
            elif isinstance(name_field, str):
                names = [name_field] * len(functions)
            elif isinstance(name_field, list):
                names = name_field
            else:
                names = [None] * len(functions)

            # Normalize description field
            desc_field = tool_config.get("description")
            if desc_field is None:
                descs = [None] * len(functions)
            elif isinstance(desc_field, str):
                descs = [desc_field] * len(functions)
            elif isinstance(desc_field, list):
                descs = desc_field
            else:
                descs = [None] * len(functions)

            for i, func in enumerate(functions):
                name = names[i] if i < len(names) else None
                desc = descs[i] if i < len(descs) else None

                # If custom name, load and rename
                if name and name != func:
                    loaded = tool_manager._load_function_from_path(path, func) if path else tool_manager._load_builtin_function(func)
                    if loaded is None:
                        logger.error(f"Could not load function '{func}' from {path}")
                        continue
                    loaded.__name__ = name
                    tool_manager.add_tool_function(
                        path=None,
                        func=loaded,
                        category=category,
                        description=desc,
                    )
                else:
                    tool_manager.add_tool_function(
                        path=path,
                        func=func,
                        category=category,
                        description=desc,
                    )
        except Exception as e:
            logger.error(f"Failed to register tool from config: {e}")

    # Build execution context
    execution_context = {
        "agent_id": args.agent_id,
        "allowed_paths": [str(Path(p).resolve()) for p in args.allowed_paths],
    }
    if args.allowed_paths:
        execution_context["agent_cwd"] = args.allowed_paths[0]

    # Register each tool as an MCP tool
    schemas = tool_manager.fetch_tool_schemas()
    for schema in schemas:
        func_info = schema.get("function", {})
        tool_name = func_info.get("name", "")
        tool_desc = func_info.get("description", "")
        tool_params = func_info.get("parameters", {})

        if not tool_name:
            continue

        # Create the MCP tool handler
        _register_mcp_tool(
            mcp,
            tool_name,
            tool_desc,
            tool_params,
            tool_manager,
            execution_context,
        )
        logger.info(f"Registered MCP tool: {tool_name}")

    logger.info(f"Custom tools MCP server ready with {len(schemas)} tools")
    return mcp


def _register_mcp_tool(
    mcp: fastmcp.FastMCP,
    tool_name: str,
    tool_desc: str,
    tool_params: Dict[str, Any],
    tool_manager: Any,
    execution_context: Dict[str, Any],
) -> None:
    """Register a single custom tool as an MCP tool on the server.

    FastMCP doesn't support **kwargs handlers, so we build a concrete function
    with named parameters derived from the tool's JSON schema.
    """
    import inspect

    # Build parameter list from schema properties
    properties = tool_params.get("properties", {})
    required = set(tool_params.get("required", []))

    # Create parameters for the dynamic function
    params = []
    for param_name, param_info in properties.items():
        if param_name in required:
            params.append(
                inspect.Parameter(param_name, inspect.Parameter.POSITIONAL_OR_KEYWORD),
            )
        else:
            # Use None as default for optional params
            params.append(
                inspect.Parameter(
                    param_name,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=None,
                ),
            )

    # Create the handler with a proper signature
    async def _handler(**kwargs) -> str:
        tool_request = {"name": tool_name, "input": kwargs}
        results = []
        async for result in tool_manager.execute_tool(tool_request, execution_context):
            results.append(result)

        if not results:
            return json.dumps({"success": False, "error": "No result from tool"})

        final = results[-1]
        if hasattr(final, "model_dump"):
            return json.dumps(final.model_dump(), default=str)
        elif hasattr(final, "__dict__"):
            return json.dumps(final.__dict__, default=str)
        return json.dumps({"success": True, "result": str(final)})

    # Apply the correct signature so FastMCP sees named params, not **kwargs
    sig = inspect.Signature(params)
    _handler.__signature__ = sig
    _handler.__name__ = tool_name
    _handler.__doc__ = tool_desc

    mcp.tool(name=tool_name, description=tool_desc)(_handler)


def write_tool_specs(
    custom_tools: List[Dict[str, Any]],
    output_path: Path,
) -> Path:
    """Write tool specifications to a JSON file for the server to load.

    This is called by the backend before launching the MCP server process.

    Args:
        custom_tools: List of custom tool configurations from YAML config.
        output_path: Path to write the specs file.

    Returns:
        Path to the written specs file.
    """
    specs = {"custom_tools": custom_tools}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(specs, f, indent=2)
    return output_path


def build_server_config(
    tool_specs_path: Path,
    allowed_paths: Optional[List[str]] = None,
    agent_id: str = "unknown",
    env: Optional[Dict[str, str]] = None,
    tool_timeout_sec: int = 300,
) -> Dict[str, Any]:
    """Build an MCP server config dict for use in .codex/config.toml or mcp_servers list.

    Args:
        tool_specs_path: Path to the tool specs JSON file.
        allowed_paths: List of allowed filesystem paths.
        agent_id: Agent identifier.
        tool_timeout_sec: Timeout in seconds for tool execution (default 300 for media generation).

    Returns:
        MCP server configuration dict (stdio type).
    """
    # Use absolute file path - works in Docker because massgen is bind-mounted at same host path
    script_path = Path(__file__).resolve()

    cmd_args = [
        "run",
        f"{script_path}:create_server",
        "--",
        "--tool-specs",
        str(tool_specs_path),
        "--agent-id",
        agent_id,
    ]
    if allowed_paths:
        cmd_args.extend(["--allowed-paths"] + allowed_paths)

    env_vars = {"FASTMCP_SHOW_CLI_BANNER": "false"}
    if env:
        env_vars.update(env)
        # Always enforce banner suppression
        env_vars["FASTMCP_SHOW_CLI_BANNER"] = "false"

    return {
        "name": "massgen_custom_tools",
        "type": "stdio",
        "command": "fastmcp",
        "args": cmd_args,
        "env": env_vars,
        "tool_timeout_sec": tool_timeout_sec,
    }
