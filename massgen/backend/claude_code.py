# -*- coding: utf-8 -*-
"""
Claude Code Stream Backend - Streaming interface using claude-code-sdk-python.

This backend provides integration with Claude Code through the
claude-code-sdk-python, leveraging Claude Code's server-side session
persistence and tool execution capabilities.

Key Features:
- ✅ Native Claude Code streaming integration
- ✅ Server-side session persistence (no client-side session
  management needed)
- ✅ Built-in tool execution (Read, Write, Bash, WebSearch, etc.)
- ✅ MassGen workflow tool integration (new_answer, vote via system prompts)
- ✅ Single persistent client with automatic session ID tracking
- ✅ Cost tracking from server-side usage data
- ✅ MCP command line mode: Bash tool disabled, execute_command MCP used instead (Docker or local)

Architecture:
- Uses ClaudeSDKClient with minimal functionality overlay
- Claude Code server maintains conversation history
- Extracts session IDs from ResultMessage responses
- Injects MassGen workflow tools via system prompts
- Converts claude-code-sdk Messages to MassGen StreamChunks

Requirements:
- claude-code-sdk-python installed: uv add claude-code-sdk
- Claude Code CLI available in PATH
- ANTHROPIC_API_KEY configured OR Claude subscription authentication

Test Results:
✅ TESTED 2025-08-10: Single agent coordination working correctly
- Command: uv run python -m massgen.cli --config claude_code_single.yaml "2+2=?"
- Auto-created working directory: claude_code_workspace/
- Session: 42593707-bca6-40ad-b154-7dc1c222d319
- Model: claude-sonnet-4-20250514 (Claude Code default)
- Tools available: Task, Bash, Glob, Grep, LS, Read, Write, WebSearch, etc.
- Answer provided: "2 + 2 = 4"
- Coordination: Agent voted for itself, selected as final answer
- Performance: 70 seconds total (includes coordination overhead)

TODO:
- Consider including cwd/session_id in new_answer results for context preservation
- Investigate whether next iterations need working directory context
"""

from __future__ import annotations

import atexit
import json
import os
import re
import sys
import uuid
import warnings
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from claude_agent_sdk import (  # type: ignore
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    PermissionResultAllow,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from ..logger_config import (
    log_backend_activity,
    log_backend_agent_message,
    log_stream_chunk,
    logger,
)
from ..structured_logging import get_current_round, get_tracer, log_token_usage
from ..tool import ToolManager
from ..tool.workflow_toolkits.base import WORKFLOW_TOOL_NAMES
from ._streaming_buffer_mixin import StreamingBufferMixin
from .base import FilesystemSupport, LLMBackend, StreamChunk


class ClaudeCodeBackend(StreamingBufferMixin, LLMBackend):
    """Claude Code backend using claude-code-sdk-python.

    Provides streaming interface to Claude Code with built-in tool execution
    capabilities and MassGen workflow tool integration. Uses ClaudeSDKClient
    for direct communication with Claude Code server.

    TODO (v0.0.14 Context Sharing Enhancement - See docs/dev_notes/v0.0.14-context.md):
    - Implement permission enforcement during file/workspace operations
    - Add execute_with_permissions() method to check permissions before operations
    - Integrate with PermissionManager for access control validation
    - Add audit logging for all file system access attempts
    - Enforce workspace boundaries based on agent permissions
    - Prevent unauthorized access to other agents' workspaces
    - Support permission-aware tool execution (Read, Write, Bash, etc.)
    """

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """Initialize ClaudeCodeBackend.

        Args:
            api_key: Anthropic API key (falls back to CLAUDE_CODE_API_KEY,
                    then ANTHROPIC_API_KEY env vars). If None, will attempt
                    to use Claude subscription authentication
            **kwargs: Additional configuration options including:
                - model: Claude model name
                - system_prompt: Base system prompt
                - allowed_tools: List of allowed tools
                - max_thinking_tokens: Maximum thinking tokens
                - cwd: Current working directory

        Note:
            Authentication is validated on first use. If neither API key nor
            subscription authentication is available, errors will surface when
            attempting to use the backend.
        """
        # Claude Code SDK doesn't support allowed_tools/disallowed_tools for MCP tools
        # See: https://github.com/anthropics/claude-code/issues/7328
        # Use mcpwrapped to filter tools at protocol level when exclude_file_operation_mcps is True
        if kwargs.get("exclude_file_operation_mcps", False):
            kwargs["use_mcpwrapped_for_tool_filtering"] = True
            logger.info("[ClaudeCodeBackend] Enabling mcpwrapped for MCP tool filtering (exclude_file_operation_mcps=True)")

        # Claude Code SDK uses MCP roots protocol which overrides our command-line paths
        # Use no-roots wrapper to prevent this and ensure both workspace and temp_workspaces are accessible
        # See: MAS-215 - Claude Code agents couldn't access temp_workspaces for voting/evaluation
        kwargs["use_no_roots_wrapper"] = True
        logger.debug("[ClaudeCodeBackend] Enabling no-roots wrapper for MCP filesystem")

        super().__init__(api_key, **kwargs)

        self.api_key = api_key or os.getenv("CLAUDE_CODE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        self.use_subscription_auth = not bool(self.api_key)

        # Set API key in environment for SDK if provided
        if self.api_key:
            os.environ["ANTHROPIC_API_KEY"] = self.api_key

        # Set git-bash path for Windows compatibility
        if sys.platform == "win32" and not os.environ.get("CLAUDE_CODE_GIT_BASH_PATH"):
            import shutil

            bash_path = shutil.which("bash")
            if bash_path:
                os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = bash_path
                logger.info(f"[ClaudeCodeBackend] Set CLAUDE_CODE_GIT_BASH_PATH={bash_path}")

        # Comprehensive Windows subprocess cleanup warning suppression
        if sys.platform == "win32":
            self._setup_windows_subprocess_cleanup_suppression()

        # Single ClaudeSDKClient for this backend instance
        self._client: Optional[Any] = None  # ClaudeSDKClient
        self._current_session_id: Optional[str] = None

        # Get workspace paths from filesystem manager (required for Claude Code)
        # The filesystem manager handles all workspace setup and management
        if not self.filesystem_manager:
            raise ValueError("Claude Code backend requires 'cwd' configuration for workspace management")

        self._cwd: str = str(Path(str(self.filesystem_manager.get_current_workspace())).resolve())

        self._pending_system_prompt: Optional[str] = None  # Windows-only workaround

        # Track tool_use_id -> tool_name for matching ToolResultBlock to its ToolUseBlock
        # (ToolResultBlock only has tool_use_id, not the tool name)
        self._tool_id_to_name: Dict[str, str] = {}

        # Custom tools support - initialize ToolManager if custom_tools are provided
        self._custom_tool_manager: Optional[ToolManager] = None
        custom_tools = kwargs.get("custom_tools", [])

        # Register multimodal tools if enabled
        enable_multimodal = self.config.get("enable_multimodal_tools", False) or kwargs.get("enable_multimodal_tools", False)

        # Build multimodal config - priority: explicit multimodal_config > individual config variables
        self._multimodal_config = self.config.get("multimodal_config", {}) or kwargs.get("multimodal_config", {})
        if not self._multimodal_config:
            # Build from individual generation config variables
            self._multimodal_config = {}
            for media_type in ["image", "video", "audio"]:
                backend = self.config.get(f"{media_type}_generation_backend")
                model = self.config.get(f"{media_type}_generation_model")
                if backend or model:
                    self._multimodal_config[media_type] = {}
                    if backend:
                        self._multimodal_config[media_type]["backend"] = backend
                    if model:
                        self._multimodal_config[media_type]["model"] = model

        if enable_multimodal:
            multimodal_tools = [
                {
                    "name": ["read_media"],
                    "category": "multimodal",
                    "path": "massgen/tool/_multimodal_tools/read_media.py",
                    "function": ["read_media"],
                },
                {
                    "name": ["generate_media"],
                    "category": "multimodal",
                    "path": "massgen/tool/_multimodal_tools/generation/generate_media.py",
                    "function": ["generate_media"],
                },
            ]
            custom_tools = list(custom_tools) + multimodal_tools
            logger.info("[ClaudeCode] Multimodal tools enabled: read_media, generate_media")

        if custom_tools:
            self._custom_tool_manager = ToolManager()
            self._register_custom_tools(custom_tools)

            # Create SDK MCP Server from custom tools and inject into mcp_servers
            sdk_mcp_server = self._create_sdk_mcp_server_from_custom_tools()
            if sdk_mcp_server:
                # Ensure mcp_servers exists in config
                if "mcp_servers" not in self.config:
                    self.config["mcp_servers"] = {}

                # Add SDK MCP server (convert to list format if dict format is used)
                if isinstance(self.config["mcp_servers"], dict):
                    # Already in dict format
                    self.config["mcp_servers"]["massgen_custom_tools"] = sdk_mcp_server
                elif isinstance(self.config["mcp_servers"], list):
                    # List format - add as special entry with SDK server marker
                    self.config["mcp_servers"].append(
                        {
                            "name": "massgen_custom_tools",
                            "__sdk_server__": sdk_mcp_server,
                        },
                    )
                else:
                    # Initialize as dict with SDK server
                    self.config["mcp_servers"] = {"massgen_custom_tools": sdk_mcp_server}

                logger.info(f"Registered SDK MCP server with {len(self._custom_tool_manager.registered_tools)} custom tools")

        # Initialize native hook adapter for MassGen hooks integration
        self._native_hook_adapter: Optional[Any] = None
        self._massgen_hooks_config: Optional[Dict[str, Any]] = None
        try:
            from ..mcp_tools.native_hook_adapters import ClaudeCodeNativeHookAdapter

            self._native_hook_adapter = ClaudeCodeNativeHookAdapter()
            logger.debug("[ClaudeCodeBackend] Native hook adapter initialized")
        except ImportError as e:
            logger.debug(f"[ClaudeCodeBackend] Native hook adapter not available: {e}")

        # Note: _execution_trace is initialized by StreamingBufferMixin
        # and configured with agent_id when _clear_streaming_buffer is called

    def _setup_windows_subprocess_cleanup_suppression(self):
        """Comprehensive Windows subprocess cleanup warning suppression."""
        # All warning filters
        warnings.filterwarnings("ignore", message="unclosed transport")
        warnings.filterwarnings("ignore", message="I/O operation on closed pipe")
        warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed transport")
        warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed event loop")
        warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed <socket.socket")
        warnings.filterwarnings("ignore", category=RuntimeWarning, message="coroutine")
        warnings.filterwarnings("ignore", message="Exception ignored in")
        warnings.filterwarnings("ignore", message="sys:1: ResourceWarning")
        warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*transport.*")
        warnings.filterwarnings("ignore", message=".*BaseSubprocessTransport.*")
        warnings.filterwarnings("ignore", message=".*_ProactorBasePipeTransport.*")
        warnings.filterwarnings("ignore", message=".*Event loop is closed.*")

        # Patch asyncio transport destructors to be silent
        try:
            import asyncio.base_subprocess
            import asyncio.proactor_events

            # Store originals
            original_subprocess_del = getattr(asyncio.base_subprocess.BaseSubprocessTransport, "__del__", None)
            original_pipe_del = getattr(asyncio.proactor_events._ProactorBasePipeTransport, "__del__", None)

            def silent_subprocess_del(self):
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        if original_subprocess_del:
                            original_subprocess_del(self)
                except Exception:
                    pass

            def silent_pipe_del(self):
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        if original_pipe_del:
                            original_pipe_del(self)
                except Exception:
                    pass

            # Apply patches
            if original_subprocess_del:
                asyncio.base_subprocess.BaseSubprocessTransport.__del__ = silent_subprocess_del
            if original_pipe_del:
                asyncio.proactor_events._ProactorBasePipeTransport.__del__ = silent_pipe_del
        except Exception:
            pass  # If patching fails, fall back to warning filters only

        # Setup exit handler for stderr suppression
        original_stderr = sys.stderr

        def suppress_exit_warnings():
            try:
                sys.stderr = open(os.devnull, "w")
                import time

                time.sleep(0.3)
            except Exception:
                pass
            finally:
                try:
                    if sys.stderr != original_stderr:
                        sys.stderr.close()
                    sys.stderr = original_stderr
                except Exception:
                    pass

        atexit.register(suppress_exit_warnings)

    def get_provider_name(self) -> str:
        """Get the name of this provider."""
        return "claude_code"

    def get_filesystem_support(self) -> FilesystemSupport:
        """Claude Code now uses MassGen's MCP-based filesystem tools (v0.1.26)

        Native Claude Code tools (Read, Write, Edit, Bash, etc.) are disabled
        via disallowed_tools to give MassGen full control. File operations
        are handled through the filesystem MCP server.
        """
        return FilesystemSupport.MCP

    def is_stateful(self) -> bool:
        """
        Claude Code backend is stateful - maintains conversation context.

        Returns:
            True - Claude Code maintains server-side session state
        """
        return True

    def supports_native_hooks(self) -> bool:
        """Check if this backend supports native hook integration.

        Claude Code backend supports native hooks via the Claude Agent SDK's
        HookMatcher API, allowing MassGen hooks to be executed natively by
        the Claude Code server.

        Returns:
            True if the native hook adapter is available
        """
        return self._native_hook_adapter is not None

    def get_native_hook_adapter(self) -> Optional[Any]:
        """Get the native hook adapter for this backend.

        Returns:
            ClaudeCodeNativeHookAdapter instance if available, None otherwise
        """
        return self._native_hook_adapter

    def set_native_hooks_config(self, config: Dict[str, Any]) -> None:
        """Set MassGen hooks converted to native format.

        Called by the orchestrator to set up MassGen hooks (MidStreamInjection,
        HighPriorityTaskReminder, user-configured hooks) in native format.
        These hooks will be merged with permission hooks when building
        ClaudeAgentOptions.

        Args:
            config: Native hooks configuration dict with PreToolUse and/or
                   PostToolUse keys containing HookMatcher lists
        """
        self._massgen_hooks_config = config
        logger.debug(
            f"[ClaudeCodeBackend] Set native hooks config: " f"PreToolUse={len(config.get('PreToolUse', []))} hooks, " f"PostToolUse={len(config.get('PostToolUse', []))} hooks",
        )

    def _get_execution_trace_hooks(self) -> Dict[str, List[Any]]:
        """Create SDK hooks that capture tool executions for the execution trace.

        Returns:
            Dictionary with PreToolUse and PostToolUse hook configurations
        """
        from claude_agent_sdk import HookMatcher

        # Store pending tool calls to correlate with results
        self._pending_tool_calls: Dict[str, Dict[str, Any]] = {}

        async def pre_tool_use_hook(input_data: Dict[str, Any], tool_use_id: Optional[str], context: Any) -> Dict[str, Any]:
            """Capture tool call before execution."""
            if self._execution_trace and input_data.get("hook_event_name") == "PreToolUse":
                tool_name = input_data.get("tool_name", "unknown")
                tool_input = input_data.get("tool_input", {})

                # Record the tool call
                self._execution_trace.add_tool_call(name=tool_name, args=tool_input)

                # Store for correlation with result
                if tool_use_id:
                    self._pending_tool_calls[tool_use_id] = {
                        "name": tool_name,
                        "input": tool_input,
                    }

                logger.debug(f"[ClaudeCodeBackend] Trace captured tool call: {tool_name}")

            # Return empty to allow the operation
            return {}

        async def post_tool_use_hook(input_data: Dict[str, Any], tool_use_id: Optional[str], context: Any) -> Dict[str, Any]:
            """Capture tool result after execution."""
            if self._execution_trace and input_data.get("hook_event_name") == "PostToolUse":
                tool_name = input_data.get("tool_name", "unknown")
                tool_response = input_data.get("tool_response", "")

                # Convert response to string if needed
                if isinstance(tool_response, dict):
                    result_str = json.dumps(tool_response)
                else:
                    result_str = str(tool_response) if tool_response else ""

                # Record the tool result
                self._execution_trace.add_tool_result(
                    name=tool_name,
                    result=result_str,
                    is_error=False,  # PostToolUse is only for successful calls
                )

                # Clean up pending call
                if tool_use_id and tool_use_id in self._pending_tool_calls:
                    del self._pending_tool_calls[tool_use_id]

                logger.debug(f"[ClaudeCodeBackend] Trace captured tool result: {tool_name}")

            return {}

        return {
            "PreToolUse": [HookMatcher(hooks=[pre_tool_use_hook])],
            "PostToolUse": [HookMatcher(hooks=[post_tool_use_hook])],
        }

    async def _setup_code_based_tools_symlinks(self) -> None:
        """Setup symlinks to shared code-based tools if they already exist.

        This is called for ClaudeCodeBackend after client connection since it doesn't
        directly manage MCP clients like OpenAI backend does. If another backend has
        already generated the shared tools, this creates the necessary symlinks.
        """
        if not self.filesystem_manager.shared_tools_base:
            # No shared tools configured - tools are per-agent
            return

        # Compute the hash of our MCP configuration to find the shared tools path
        # We need to extract tool schemas to compute the hash, but we don't have direct
        # MCP client access. Instead, check if shared tools directory already exists.
        from pathlib import Path

        shared_tools_base = Path(self.filesystem_manager.shared_tools_base)
        if not shared_tools_base.exists():
            # No shared tools generated yet
            return

        # Find hash subdirectories in shared_tools_base
        # In a multi-agent setup, agent_a will have generated tools, so we look for existing hash dirs
        hash_dirs = [d for d in shared_tools_base.iterdir() if d.is_dir()]

        if not hash_dirs:
            # No hash directories found
            return

        # Use the first (and typically only) hash directory
        # In multi-agent setups with same MCP config, there should be exactly one hash dir
        target_path = hash_dirs[0]

        # Check if tools exist in this directory
        if (target_path / "servers").exists() and (target_path / ".mcp").exists():
            # Set shared_tools_directory and create symlinks
            self.filesystem_manager.shared_tools_directory = target_path
            self.filesystem_manager._add_shared_tools_to_allowed_paths(target_path)
            logger.info(f"[ClaudeCodeBackend] Created symlinks to existing shared tools: {target_path}")

    async def clear_history(self) -> None:
        """
        Clear Claude Code conversation history while preserving session.

        Uses the /clear slash command to clear conversation history without
        destroying the session, working directory, or other session state.
        """
        if self._client is None:
            # No active session to clear
            return

        try:
            # Send /clear command to clear history while preserving session
            await self._client.query("/clear")

            # The /clear command should preserve:
            # - Session ID
            # - Working directory
            # - Tool availability
            # - Permission settings
            # While clearing only the conversation history

        except Exception as e:
            # Fallback to full reset if /clear command fails
            logger.warning(f"/clear command failed ({e}), falling back to full reset")
            await self.reset_state()

    async def reset_state(self) -> None:
        """
        Reset Claude Code backend state.

        Properly disconnects and clears the current session and client connection to start fresh.
        """
        if self._client is not None:
            try:
                await self._client.disconnect()
            except Exception:
                pass  # Ignore cleanup errors
        self._client = None
        self._current_session_id = None
        self._tool_id_to_name.clear()

    def update_token_usage_from_result_message(self, result_message) -> None:
        """Update token usage from Claude Code ResultMessage.

        Extracts actual token usage and cost data from Claude Code server
        response. This is more accurate than estimation-based methods.

        Args:
            result_message: ResultMessage from Claude Code with usage data
        """
        # Check if we have a valid ResultMessage
        if ResultMessage is not None and not isinstance(result_message, ResultMessage):
            return
        # Fallback: check if it has the expected attributes (for SDK compatibility)
        if not hasattr(result_message, "usage") or not hasattr(result_message, "total_cost_usd"):
            return

        # Extract usage information from ResultMessage
        if result_message.usage:
            usage_data = result_message.usage

            # Claude Code SDK returns:
            # - input_tokens: NEW uncached input tokens only
            # - cache_read_input_tokens: Tokens read from prompt cache (cache hits)
            # - cache_creation_input_tokens: Tokens written to prompt cache
            # Total input = input_tokens + cache_read + cache_creation

            if isinstance(usage_data, dict):
                # Base input tokens (uncached)
                base_input = usage_data.get("input_tokens", 0) or 0
                # Cache tokens
                cache_read = usage_data.get("cache_read_input_tokens", 0) or 0
                cache_creation = usage_data.get("cache_creation_input_tokens", 0) or 0
                # Total input is sum of all input-related tokens
                input_tokens = base_input + cache_read + cache_creation
                output_tokens = usage_data.get("output_tokens", 0) or 0
            else:
                # Object format - use getattr
                base_input = getattr(usage_data, "input_tokens", 0) or 0
                cache_read = getattr(usage_data, "cache_read_input_tokens", 0) or 0
                cache_creation = getattr(usage_data, "cache_creation_input_tokens", 0) or 0
                input_tokens = base_input + cache_read + cache_creation
                output_tokens = getattr(usage_data, "output_tokens", 0) or 0

            logger.info(
                f"[ClaudeCode] Token usage: input={input_tokens} " f"(base={base_input}, cache_read={cache_read}, cache_create={cache_creation}), " f"output={output_tokens}",
            )

            # Update cumulative tracking
            self.token_usage.input_tokens += input_tokens
            self.token_usage.output_tokens += output_tokens
            # Track cached tokens separately for detailed breakdown
            self.token_usage.cached_input_tokens += cache_read

        # Use actual cost from Claude Code (preferred over calculation)
        if result_message.total_cost_usd is not None:
            self.token_usage.estimated_cost += result_message.total_cost_usd
        else:
            # Fallback: calculate cost with litellm if not provided
            if result_message.usage:
                cost = self.token_calculator.calculate_cost_with_usage_object(
                    model=self.model,
                    usage=result_message.usage,
                    provider=self.get_provider_name(),
                )
                self.token_usage.estimated_cost += cost

    def update_token_usage(self, messages: List[Dict[str, Any]], response_content: str, model: str):
        """Update token usage tracking (fallback method).

        Only used when no ResultMessage available. Provides estimated token
        tracking for compatibility with base class interface. Should only be
        called when ResultMessage data is not available.

        Args:
            messages: List of conversation messages
            response_content: Generated response content
            model: Model name for cost calculation
        """
        # This method should only be called when we don't have a
        # ResultMessage. It provides estimated tracking for compatibility
        # with base class interface

        # Estimate input tokens from messages
        input_text = "\n".join([msg.get("content", "") for msg in messages])
        input_tokens = self.estimate_tokens(input_text)

        # Estimate output tokens from response
        output_tokens = self.estimate_tokens(response_content)

        # Update totals
        self.token_usage.input_tokens += input_tokens
        self.token_usage.output_tokens += output_tokens

        # Calculate estimated cost (no ResultMessage available)
        cost = self.calculate_cost(input_tokens, output_tokens, model, result_message=None)
        self.token_usage.estimated_cost += cost

    def get_supported_builtin_tools(self, enable_web_search: bool = False) -> List[str]:
        """Get list of builtin tools supported by Claude Code.

        Returns only tools that MassGen doesn't have native equivalents for.
        MassGen has native implementations for: read_file_content, save_file_content,
        append_file_content, run_shell_script, list_directory, and will add
        grep/glob tools (see issue 640).

        Args:
            enable_web_search: If True, include WebSearch and WebFetch tools.

        Returns:
            List of tool names that should be enabled for Claude Code.
        """
        tools = [
            "Task",  # Subagent spawning - unique to Claude Code
        ]

        if enable_web_search:
            tools.extend(["WebSearch", "WebFetch"])

        return tools

    # Known tools for well-known MCP servers (used for tool filtering)
    # NOTE: Claude Code SDK does NOT support filtering MCP tools via allowed_tools/disallowed_tools.
    # These only work for built-in tools (Read, Write, Bash, etc.), not MCP tools.
    # See: https://github.com/anthropics/claude-code/issues/7328
    # Workaround options:
    # 1. Use mcp-remote with --ignore-tool to proxy and filter tools
    # 2. Don't add MCP servers with unwanted tools
    # 3. Accept that tools are visible but use disallowed_tools to block execution
    KNOWN_SERVER_TOOLS = {
        "filesystem": [
            "read_file",
            "read_text_file",
            "read_multiple_files",
            "write_file",
            "edit_file",
            "create_directory",
            "list_directory",
            "directory_tree",
            "move_file",
            "copy_file",
            "delete_file",
            "search_files",
            "get_file_info",
            "list_allowed_directories",
        ],
        "workspace_tools": [
            "read_file_content",
            "save_file_content",
            "append_file_content",
            "list_directory",
            "create_directory",
            "copy_file",
            "move_file",
            "delete_file",
            "compare_files",
            "text_to_image_generation",
            "text_to_audio_generation",
        ],
        "command_line": [
            "execute_command",
        ],
    }

    def _get_all_tools_for_server(self, server_name: str) -> List[str]:
        """Get all known tools for a server, prefixed with mcp__{server}__.

        Used when we need to explicitly list all tools (fallback when wildcards not supported).
        Handles both exact server names and pattern-based names (e.g., planning_agent_a).

        Args:
            server_name: Name of the MCP server

        Returns:
            List of prefixed tool names, or empty list if server is unknown
        """
        # Check for exact match first
        tools = self.KNOWN_SERVER_TOOLS.get(server_name)
        if tools:
            return [f"mcp__{server_name}__{tool}" for tool in tools]

        # Check for pattern-based servers (e.g., planning_agent_a -> planning)
        # These are dynamically named servers with predictable tool sets
        DYNAMIC_SERVER_PATTERNS = {
            "planning_": [
                "create_task_plan",
                "update_task_status",
                "get_task_status",
                "get_all_tasks",
                "add_task",
                "remove_task",
                "clear_completed",
            ],
            "memory_": [
                "save_memory",
                "load_memory",
                "list_memories",
                "delete_memory",
            ],
        }

        for prefix, pattern_tools in DYNAMIC_SERVER_PATTERNS.items():
            if server_name.startswith(prefix):
                return [f"mcp__{server_name}__{tool}" for tool in pattern_tools]

        return []

    def get_current_session_id(self) -> Optional[str]:
        """Get current session ID from server-side session management.

        Returns:
            Current session ID if available, None otherwise
        """
        return self._current_session_id

    # TODO (v0.0.14 Context Sharing Enhancement - See docs/dev_notes/v0.0.14-context.md):
    # Add permission enforcement methods:
    # def execute_with_permissions(self, operation, path):
    #     """Execute operation only if permissions allow.
    #
    #     Args:
    #         operation: The operation to execute (e.g., tool call)
    #         path: The file/directory path being accessed
    #
    #     Raises:
    #         PermissionError: If agent lacks required access
    #     """
    #     if not self.check_permission(path, operation.type):
    #         raise PermissionError(f"Agent {self.agent_id} lacks {operation.type} access to {path}")
    #
    # def check_permission(self, path: str, access_type: str) -> bool:
    #     """Check if current agent has permission for path access."""
    #     # Will integrate with PermissionManager
    #     pass

    def _register_custom_tools(self, custom_tools: List[Dict[str, Any]]) -> None:
        """Register custom tools with the tool manager.

        Supports flexible configuration:
        - function: str | List[str]
        - description: str (shared) | List[str] (1-to-1 mapping)
        - preset_args: dict (shared) | List[dict] (1-to-1 mapping)

        Examples:
            # Single function
            function: "my_func"
            description: "My description"

            # Multiple functions with shared description
            function: ["func1", "func2"]
            description: "Shared description"

            # Multiple functions with individual descriptions
            function: ["func1", "func2"]
            description: ["Description 1", "Description 2"]

            # Multiple functions with mixed (shared desc, individual args)
            function: ["func1", "func2"]
            description: "Shared description"
            preset_args: [{"arg1": "val1"}, {"arg1": "val2"}]

        Args:
            custom_tools: List of custom tool configurations
        """
        if not self._custom_tool_manager:
            logger.warning("Custom tool manager not initialized, cannot register tools")
            return

        # Collect unique categories and create them if needed
        categories = set()
        for tool_config in custom_tools:
            if isinstance(tool_config, dict):
                category = tool_config.get("category", "default")
                if category != "default":
                    categories.add(category)

        # Create categories that don't exist
        for category in categories:
            if category not in self._custom_tool_manager.tool_categories:
                self._custom_tool_manager.setup_category(
                    category_name=category,
                    description=f"Custom {category} tools",
                    enabled=True,
                )

        # Register each custom tool
        for tool_config in custom_tools:
            try:
                if isinstance(tool_config, dict):
                    # Extract base configuration
                    path = tool_config.get("path")
                    category = tool_config.get("category", "default")

                    # Normalize function field to list
                    func_field = tool_config.get("function")
                    if isinstance(func_field, str):
                        functions = [func_field]
                    elif isinstance(func_field, list):
                        functions = func_field
                    else:
                        logger.error(
                            f"Invalid function field type: {type(func_field)}. " f"Must be str or List[str].",
                        )
                        continue

                    if not functions:
                        logger.error("Empty function list in tool config")
                        continue

                    num_functions = len(functions)

                    # Process name field (can be str or List[str])
                    name_field = tool_config.get("name")
                    names = self._process_field_for_functions(
                        name_field,
                        num_functions,
                        "name",
                    )
                    if names is None:
                        continue  # Validation error, skip this tool

                    # Process description field (can be str or List[str])
                    desc_field = tool_config.get("description")
                    descriptions = self._process_field_for_functions(
                        desc_field,
                        num_functions,
                        "description",
                    )
                    if descriptions is None:
                        continue  # Validation error, skip this tool

                    # Process preset_args field (can be dict or List[dict])
                    preset_field = tool_config.get("preset_args")
                    preset_args_list = self._process_field_for_functions(
                        preset_field,
                        num_functions,
                        "preset_args",
                    )
                    if preset_args_list is None:
                        continue  # Validation error, skip this tool

                    # Register each function with its corresponding values
                    for i, func in enumerate(functions):
                        # Load the function first if custom name is needed
                        if names[i] and names[i] != func:
                            # Need to load function and apply custom name
                            if path:
                                loaded_func = self._custom_tool_manager._load_function_from_path(path, func)
                            else:
                                loaded_func = self._custom_tool_manager._load_builtin_function(func)

                            if loaded_func is None:
                                logger.error(f"Could not load function '{func}' from path: {path}")
                                continue

                            # Apply custom name by modifying __name__ attribute
                            loaded_func.__name__ = names[i]

                            # Register with loaded function (no path needed)
                            self._custom_tool_manager.add_tool_function(
                                path=None,
                                func=loaded_func,
                                category=category,
                                preset_args=preset_args_list[i],
                                description=descriptions[i],
                            )
                        else:
                            # No custom name or same as function name, use normal registration
                            self._custom_tool_manager.add_tool_function(
                                path=path,
                                func=func,
                                category=category,
                                preset_args=preset_args_list[i],
                                description=descriptions[i],
                            )

                        # Use custom name for logging if provided
                        registered_name = names[i] if names[i] else func
                        logger.info(
                            f"Registered custom tool: {registered_name} from {path} " f"(category: {category}, " f"desc: '{descriptions[i][:50] if descriptions[i] else 'None'}...')",
                        )

            except Exception as e:
                func_name = tool_config.get("function", "unknown")
                logger.error(
                    f"Failed to register custom tool {func_name}: {e}",
                    exc_info=True,
                )

    def _process_field_for_functions(
        self,
        field_value: Any,
        num_functions: int,
        field_name: str,
    ) -> Optional[List[Any]]:
        """Process a config field that can be a single value or list.

        Conversion rules:
        - None → [None, None, ...] (repeated num_functions times)
        - Single value (not list) → [value, value, ...] (shared)
        - List with matching length → use as-is (1-to-1 mapping)
        - List with wrong length → ERROR (return None)

        Args:
            field_value: The field value from config
            num_functions: Number of functions being registered
            field_name: Name of the field (for error messages)

        Returns:
            List of values (one per function), or None if validation fails

        Examples:
            _process_field_for_functions(None, 3, "desc")
            → [None, None, None]

            _process_field_for_functions("shared", 3, "desc")
            → ["shared", "shared", "shared"]

            _process_field_for_functions(["a", "b", "c"], 3, "desc")
            → ["a", "b", "c"]

            _process_field_for_functions(["a", "b"], 3, "desc")
            → None (error logged)
        """
        # Case 1: None or missing field → use None for all functions
        if field_value is None:
            return [None] * num_functions

        # Case 2: Single value (not a list) → share across all functions
        if not isinstance(field_value, list):
            return [field_value] * num_functions

        # Case 3: List value → must match function count exactly
        if len(field_value) == num_functions:
            return field_value
        else:
            # Length mismatch → validation error
            logger.error(
                f"Configuration error: {field_name} is a list with "
                f"{len(field_value)} items, but there are {num_functions} functions. "
                f"Either use a single value (shared) or a list with exactly "
                f"{num_functions} items (1-to-1 mapping).",
            )
            return None

    async def _execute_massgen_custom_tool(self, tool_name: str, args: dict) -> dict:
        """Execute a MassGen custom tool and convert result to MCP format.

        Args:
            tool_name: Name of the custom tool to execute
            args: Arguments for the tool

        Returns:
            MCP-formatted response with content blocks
        """
        if not self._custom_tool_manager:
            return {
                "content": [
                    {"type": "text", "text": "Error: Custom tool manager not initialized"},
                ],
            }

        # Build execution context for context param injection
        # The tool manager will only inject params that match @context_params decorator
        execution_context = {}
        if hasattr(self, "_execution_context") and self._execution_context:
            try:
                execution_context = self._execution_context.model_dump()
            except Exception:
                pass

        # Ensure agent_cwd is always available for custom tools
        # Use filesystem_manager's cwd which is set to the agent's workspace
        if self.filesystem_manager:
            execution_context["agent_cwd"] = str(self.filesystem_manager.cwd)
            # Also add allowed_paths for path validation
            if hasattr(self.filesystem_manager, "path_permission_manager") and self.filesystem_manager.path_permission_manager:
                paths = self.filesystem_manager.path_permission_manager.get_mcp_filesystem_paths()
                if paths:
                    execution_context["allowed_paths"] = paths

        # Add multimodal_config for read_media/generate_media tools
        if hasattr(self, "_multimodal_config") and self._multimodal_config:
            execution_context["multimodal_config"] = self._multimodal_config

        tool_request = {
            "name": tool_name,
            "input": args,
        }

        # Add observability context (agent_id, round tracking)
        execution_context["agent_id"] = getattr(self, "_current_agent_id", None) or "unknown"
        # Add round tracking from context variable (set by orchestrator via set_current_round)
        round_number, round_type = get_current_round()
        if round_number is not None:
            execution_context["round_number"] = round_number
        if round_type:
            execution_context["round_type"] = round_type

        result_text = ""
        try:
            async for result in self._custom_tool_manager.execute_tool(
                tool_request,
                execution_context=execution_context,
            ):
                # Accumulate ExecutionResult blocks
                if hasattr(result, "output_blocks"):
                    for block in result.output_blocks:
                        if hasattr(block, "data"):
                            result_text += str(block.data)
                        elif hasattr(block, "content"):
                            result_text += str(block.content)
                elif hasattr(result, "content"):
                    result_text += str(result.content)
                else:
                    result_text += str(result)
        except Exception as e:
            logger.error(f"Error executing custom tool {tool_name}: {e}")
            result_text = f"Error: {str(e)}"

        # Return MCP format response
        return {
            "content": [
                {"type": "text", "text": result_text or "Tool executed successfully"},
            ],
        }

    def _create_sdk_mcp_server_from_custom_tools(self):
        """Convert MassGen custom tools to SDK MCP Server.

        Returns:
            SDK MCP Server instance or None if no tools or SDK unavailable
        """
        if not self._custom_tool_manager:
            return None

        try:
            from claude_agent_sdk import create_sdk_mcp_server, tool
        except ImportError:
            logger.warning("claude-agent-sdk not available, custom tools will not be registered")
            return None

        # Get all registered custom tools
        tool_schemas = self._custom_tool_manager.fetch_tool_schemas()
        if not tool_schemas:
            logger.info("No custom tools to register")
            return None

        # Convert each tool to MCP tool format
        mcp_tools = []
        for tool_schema in tool_schemas:
            try:
                tool_name = tool_schema["function"]["name"]
                tool_desc = tool_schema["function"].get("description", "")
                tool_params = tool_schema["function"]["parameters"]

                # Create async wrapper for MassGen tool
                # Use default argument to capture tool_name in closure
                async def tool_wrapper(args, tool_name=tool_name):
                    return await self._execute_massgen_custom_tool(tool_name, args)

                # Register using SDK tool decorator
                mcp_tool = tool(
                    name=tool_name,
                    description=tool_desc,
                    input_schema=tool_params,
                )(tool_wrapper)

                mcp_tools.append(mcp_tool)
                logger.info(f"Converted custom tool to MCP: {tool_name}")

            except Exception as e:
                logger.error(f"Failed to convert tool {tool_schema.get('function', {}).get('name', 'unknown')} to MCP: {e}")

        if not mcp_tools:
            logger.warning("No custom tools successfully converted to MCP")
            return None

        # Create SDK MCP server
        try:
            sdk_mcp_server = create_sdk_mcp_server(
                name="massgen_custom_tools",
                version="1.0.0",
                tools=mcp_tools,
            )
            logger.info(f"Created SDK MCP server with {len(mcp_tools)} custom tools")
            return sdk_mcp_server
        except Exception as e:
            logger.error(f"Failed to create SDK MCP server: {e}")
            return None

    def _build_system_prompt_with_workflow_tools(self, tools: List[Dict[str, Any]], base_system: Optional[str] = None) -> str:
        """Build system prompt that includes workflow tools information.

        Creates comprehensive system prompt that instructs Claude on tool
        usage, particularly for MassGen workflow coordination tools.

        Args:
            tools: List of available tools
            base_system: Base system prompt to extend (optional)

        Returns:
            Complete system prompt with tool instructions
        """
        system_parts = []

        # Start with base system prompt
        if base_system:
            system_parts.append(base_system)

        # Add MCP command line execution instruction if enabled
        enable_mcp_command_line = self.config.get("enable_mcp_command_line", False)
        command_line_execution_mode = self.config.get("command_line_execution_mode", "local")
        if enable_mcp_command_line:
            system_parts.append("\n--- Code Execution Environment ---")
            system_parts.append("- Use the execute_command MCP tool for all command execution")
            system_parts.append("- The Bash tool is disabled - use execute_command instead")
            if command_line_execution_mode == "docker":
                system_parts.append("- Commands run in isolated Docker container")
            # Below is necessary bc Claude Code is automatically loaded with knowledge of the current git repo;
            # this prompt is a temporary workaround before running fully within docker
            system_parts.append(
                "- Do NOT use any git repository information you may see as part of a broader directory. "
                "All git information must come from the execute_command tool and be focused solely on the "
                "directories you were told to work in, not any parent directories.",
            )

        # Add workflow tools information if present
        if tools:
            workflow_tools = [t for t in tools if t.get("function", {}).get("name") in WORKFLOW_TOOL_NAMES]
            if workflow_tools:
                system_parts.append("\n--- Coordination Actions ---")
                for tool in workflow_tools:
                    name = tool.get("function", {}).get("name", "unknown")
                    description = tool.get("function", {}).get("description", "No description")
                    system_parts.append(f"- {name}: {description}")

                    # Add usage examples for workflow tools
                    if name == "new_answer":
                        system_parts.append(
                            '    Usage: {"tool_name": "new_answer", ' '"arguments": {"content": "your improved answer. If any builtin tools were used, mention how they are used here."}}',
                        )
                    elif name == "vote":
                        # Extract valid agent IDs from enum if available
                        agent_id_enum = None
                        for t in tools:
                            if t.get("function", {}).get("name") == "vote":
                                agent_id_param = t.get("function", {}).get("parameters", {}).get("properties", {}).get("agent_id", {})
                                if "enum" in agent_id_param:
                                    agent_id_enum = agent_id_param["enum"]
                                break

                        if agent_id_enum:
                            agent_list = ", ".join(agent_id_enum)
                            system_parts.append(f'    Usage: {{"tool_name": "vote", ' f'"arguments": {{"agent_id": "agent1", ' f'"reason": "explanation"}}}} // Choose agent_id from: {agent_list}')
                        else:
                            system_parts.append('    Usage: {"tool_name": "vote", ' '"arguments": {"agent_id": "agent1", ' '"reason": "explanation"}}')
                    elif name == "submit":
                        system_parts.append(
                            '    Usage: {"tool_name": "submit", ' '"arguments": {"confirmed": true}}',
                        )
                    elif name == "restart_orchestration":
                        system_parts.append(
                            '    Usage: {"tool_name": "restart_orchestration", ' '"arguments": {"reason": "The answer is incomplete because...", ' '"instructions": "In the next attempt, please..."}}',
                        )
                    elif name == "ask_others":
                        system_parts.append(
                            '    Usage: {"tool_name": "ask_others", ' '"arguments": {"question": "Which framework should we use: Next.js or React?"}}',
                        )
                        system_parts.append(
                            '    IMPORTANT: When user says "call ask_others" or "ask others", you MUST execute this tool call.',
                        )

                system_parts.append("\n--- MassGen Coordination Instructions ---")
                system_parts.append("IMPORTANT: You must respond with a structured JSON decision at the end of your response.")
                # system_parts.append(
                #     "You must use the coordination tools (new_answer, vote) "
                #     "to participate in multi-agent workflows."
                # )
                # system_parts.append(
                #     "Make sure to include the JSON in the exact format shown in the usage examples above.")
                system_parts.append("The JSON MUST be formatted as a strict JSON code block:")
                system_parts.append("1. Start with ```json on one line")
                system_parts.append("2. Include your JSON content (properly formatted)")
                system_parts.append("3. End with ``` on one line")
                system_parts.append('Example format:\n```json\n{"tool_name": "vote", "arguments": {"agent_id": "agent1", "reason": "explanation"}}\n```')
                system_parts.append("The JSON block should be placed at the very end of your response, after your analysis.")

        return "\n".join(system_parts)

    async def _log_backend_input(self, messages, system_prompt, tools, kwargs):
        """Log backend inputs using StreamChunk for visibility (enabled by default)."""
        # Enable by default, but allow disabling via environment variable
        if os.getenv("MASSGEN_LOG_BACKENDS", "1") == "0":
            return

        try:
            # Create debug info using the logging approach that works in MassGen
            reset_mode = "🔄 RESET" if kwargs.get("reset_chat") else "💬 CONTINUE"
            tools_info = f"🔧 {len(tools)} tools" if tools else "🚫 No tools"

            debug_info = f"[BACKEND] {reset_mode} | {tools_info} | Session: {self._current_session_id}"

            if system_prompt and len(system_prompt) > 0:
                # Show full system prompt in debug logging
                debug_info += f"\n[SYSTEM_FULL] {system_prompt}"

            # Yield a debug chunk that will be captured by the logging system
            yield StreamChunk(type="debug", content=debug_info, source="claude_code_backend")

        except Exception as e:
            # Log the error but don't break backend execution
            yield StreamChunk(
                type="debug",
                content=f"[BACKEND_LOG_ERROR] {str(e)}",
                source="claude_code_backend",
            )

    def extract_structured_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Extract structured JSON response for Claude Code format.

        Looks for JSON in the format:
        {"tool_name": "vote/new_answer", "arguments": {...}}

        Args:
            response_text: The full response text to search

        Returns:
            Extracted JSON dict if found, None otherwise
        """
        try:
            import re

            # Strategy 0: Look for JSON inside markdown code blocks first
            markdown_json_pattern = r"```json\s*(\{.*?\})\s*```"
            markdown_matches = re.findall(markdown_json_pattern, response_text, re.DOTALL)

            for match in reversed(markdown_matches):
                try:
                    parsed = json.loads(match.strip())
                    if isinstance(parsed, dict) and "tool_name" in parsed:
                        return parsed
                except json.JSONDecodeError:
                    continue

            # Strategy 1: Look for complete JSON blocks with proper braces
            json_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
            json_matches = re.findall(json_pattern, response_text, re.DOTALL)

            # Try parsing each match (in reverse order - last one first)
            for match in reversed(json_matches):
                try:
                    cleaned_match = match.strip()
                    parsed = json.loads(cleaned_match)
                    if isinstance(parsed, dict) and "tool_name" in parsed:
                        return parsed
                except json.JSONDecodeError:
                    continue

            # Strategy 2: Look for JSON blocks with nested braces (more complex)
            brace_count = 0
            json_start = -1

            for i, char in enumerate(response_text):
                if char == "{":
                    if brace_count == 0:
                        json_start = i
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0 and json_start >= 0:
                        # Found a complete JSON block
                        json_block = response_text[json_start : i + 1]
                        try:
                            parsed = json.loads(json_block)
                            if isinstance(parsed, dict) and "tool_name" in parsed:
                                return parsed
                        except json.JSONDecodeError:
                            pass
                        json_start = -1

            # Strategy 3: Line-by-line approach (fallback)
            lines = response_text.strip().split("\n")
            json_candidates = []

            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("{") and stripped.endswith("}"):
                    json_candidates.append(stripped)
                elif stripped.startswith("{"):
                    # Multi-line JSON - collect until closing brace
                    json_text = stripped
                    for j in range(i + 1, len(lines)):
                        json_text += "\n" + lines[j].strip()
                        if lines[j].strip().endswith("}"):
                            json_candidates.append(json_text)
                            break

            # Try to parse each candidate
            for candidate in reversed(json_candidates):
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict) and "tool_name" in parsed:
                        return parsed
                except json.JSONDecodeError:
                    continue

            return None

        except Exception:
            return None

    def _parse_workflow_tool_calls(self, text_content: str) -> List[Dict[str, Any]]:
        """Parse workflow tool calls from text content.

        Searches for JSON-formatted tool calls in the response text and
        converts them to the standard tool call format used by MassGen.
        Uses the extract_structured_response method for robust JSON extraction.

        Args:
            text_content: Response text to search for tool calls

        Returns:
            List of unique tool call dictionaries in standard format
        """
        tool_calls = []

        # First try to extract structured JSON response
        structured_response = self.extract_structured_response(text_content)

        if structured_response and isinstance(structured_response, dict):
            tool_name = structured_response.get("tool_name")
            arguments = structured_response.get("arguments", {})

            if tool_name and isinstance(arguments, dict):
                tool_calls.append(
                    {
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                        "type": "function",
                        "function": {"name": tool_name, "arguments": arguments},
                    },
                )
                return tool_calls

        # Fallback: Look for multiple JSON tool calls using regex patterns
        seen_calls = set()  # Track unique tool calls to prevent duplicates

        # Look for JSON tool call patterns
        json_patterns = [
            r'\{"tool_name":\s*"([^"]+)",\s*"arguments":\s*' r"(\{[^}]*\})\}",
            r'\{\s*"tool_name"\s*:\s*"([^"]+)"\s*,\s*"arguments"' r"\s*:\s*(\{[^}]*\})\s*\}",
        ]

        for pattern in json_patterns:
            matches = re.finditer(pattern, text_content, re.IGNORECASE)
            for match in matches:
                tool_name = match.group(1)
                try:
                    arguments = json.loads(match.group(2))

                    # Create a unique identifier for this tool call
                    # Based on tool name and arguments content
                    call_signature = (tool_name, json.dumps(arguments, sort_keys=True))

                    # Only add if we haven't seen this exact call before
                    if call_signature not in seen_calls:
                        seen_calls.add(call_signature)
                        tool_calls.append(
                            {
                                "id": f"call_{uuid.uuid4().hex[:8]}",
                                "type": "function",
                                "function": {"name": tool_name, "arguments": arguments},
                            },
                        )
                except json.JSONDecodeError:
                    continue

        return tool_calls

    def _build_claude_options(self, **options_kwargs) -> ClaudeAgentOptions:
        """Build ClaudeAgentOptions with provided parameters.

        Creates a secure configuration with only essential Claude Code tools enabled.
        MassGen has native implementations for most file/shell operations, so we only
        enable unique tools like Task (subagent spawning) and optionally web tools.

        Config options:
        - use_default_prompt (bool, default False): When True, uses Claude Code's
          default system prompt with MassGen instructions appended. When False,
          uses only MassGen's workflow system prompt for full control.
        - enable_web_search (bool, default False): When True, enables WebSearch
          and WebFetch tools. When False, these are disabled (use MassGen's crawl4ai).

        Returns:
            ClaudeAgentOptions configured with provided parameters and
            security restrictions
        """
        options_kwargs.get("cwd", os.getcwd())
        permission_mode = options_kwargs.get("permission_mode", "acceptEdits")
        enable_web_search = options_kwargs.get("enable_web_search", False)
        allowed_tools = options_kwargs.get("allowed_tools", self.get_supported_builtin_tools(enable_web_search))

        # Filter out parameters handled separately or not for ClaudeAgentOptions
        excluded_params = self.get_base_excluded_config_params() | {
            # Claude Code specific exclusions
            "api_key",
            "allowed_tools",
            "permission_mode",
            "custom_tools",  # Handled separately via SDK MCP server conversion
            "instance_id",  # Used for Docker container naming, not for ClaudeAgentOptions
            "enable_rate_limit",  # Rate limiting parameter (handled at orchestrator level, not backend)
            # MassGen-specific config options (not ClaudeAgentOptions parameters)
            "enable_web_search",  # Handled above - controls WebSearch/WebFetch tool availability
            "use_default_prompt",  # Handled in stream_with_tools - controls system prompt mode
            "max_thinking_tokens",  # Handled below - converted to env.MAX_THINKING_TOKENS
            # Note: use_mcpwrapped_for_tool_filtering and use_no_roots_wrapper are in base excluded params
            # Note: system_prompt is NOT excluded - it's needed for internal workflow prompt injection
            # Validation prevents it from being set in YAML backend config
        }

        # Handle max_thinking_tokens -> env.MAX_THINKING_TOKENS conversion
        # This enables extended thinking in Claude Agent SDK, providing ThinkingBlock
        # outputs with the model's internal reasoning process.
        # See: https://platform.claude.com/docs/en/build-with-claude/extended-thinking
        max_thinking_tokens = options_kwargs.get("max_thinking_tokens")
        if max_thinking_tokens is not None:
            # Merge with existing env dict if present
            env_dict = options_kwargs.get("env", {})
            if env_dict is None:
                env_dict = {}
            env_dict["MAX_THINKING_TOKENS"] = str(max_thinking_tokens)
            options_kwargs["env"] = env_dict
            logger.info(f"[ClaudeCodeBackend] Extended thinking enabled with budget: {max_thinking_tokens} tokens")

        # Get cwd from filesystem manager (always available since we require it in __init__)
        cwd_option = Path(str(self.filesystem_manager.get_current_workspace())).resolve()
        self._cwd = str(cwd_option)

        # Get hooks configuration from filesystem manager (permission hooks)
        permission_hooks = self.filesystem_manager.get_claude_code_hooks_config()

        # Merge permission hooks with MassGen hooks (MidStreamInjection, user hooks, etc.)
        if self._massgen_hooks_config and self._native_hook_adapter:
            hooks_config = self._native_hook_adapter.merge_native_configs(
                permission_hooks,
                self._massgen_hooks_config,
            )
            logger.debug(
                f"[ClaudeCodeBackend] Merged hooks: " f"PreToolUse={len(hooks_config.get('PreToolUse', []))} total, " f"PostToolUse={len(hooks_config.get('PostToolUse', []))} total",
            )
        else:
            hooks_config = permission_hooks

        # Convert mcp_servers from list format to dict format for ClaudeAgentOptions
        # List format: [{"name": "server1", "type": "stdio", ...}, ...]
        # Dict format: {"server1": {"type": "stdio", ...}, ...}
        mcp_servers_dict = {}
        if "mcp_servers" in options_kwargs:
            mcp_servers = options_kwargs["mcp_servers"]
            if isinstance(mcp_servers, list):
                for server in mcp_servers:
                    if isinstance(server, dict):
                        if "__sdk_server__" in server:
                            # SDK MCP Server object (created via create_sdk_mcp_server)
                            server_name = server["name"]
                            mcp_servers_dict[server_name] = server["__sdk_server__"]
                        elif "name" in server:
                            # Regular dictionary configuration
                            server_config = {k: v for k, v in server.items() if k != "name"}
                            mcp_servers_dict[server["name"]] = server_config
                            # Log filesystem server args for debugging
                            if server["name"] == "filesystem":
                                logger.info(f"[ClaudeCodeBackend] Configuring filesystem MCP server with args: {server_config.get('args', [])}")
            elif isinstance(mcp_servers, dict):
                # Already in dict format
                mcp_servers_dict = mcp_servers

        # Get additional directories from filesystem manager for Claude Code access
        # This is required because Claude Code's built-in permission system restricts
        # filesystem access to cwd by default. MCP server args alone aren't sufficient.
        add_dirs = []
        if self.filesystem_manager:
            fs_paths = self.filesystem_manager.path_permission_manager.get_mcp_filesystem_paths()
            # Add all paths except cwd (which is already accessible)
            cwd_str = str(cwd_option)
            for path in fs_paths:
                if path != cwd_str:
                    add_dirs.append(path)
            if add_dirs:
                logger.info(f"[ClaudeCodeBackend._build_claude_options] Adding extra dirs for Claude Code access: {add_dirs}")

        options = {
            "cwd": cwd_option,
            "resume": self.get_current_session_id(),
            "permission_mode": permission_mode,
            "allowed_tools": allowed_tools,
            "add_dirs": add_dirs if add_dirs else [],
            # Disable loading filesystem-based settings to ensure our programmatic config takes precedence
            "setting_sources": [],
            **{k: v for k, v in options_kwargs.items() if k not in excluded_params},
        }

        # Add converted mcp_servers if present
        if mcp_servers_dict:
            options["mcp_servers"] = mcp_servers_dict
            # Debug log the full filesystem server config
            if "filesystem" in mcp_servers_dict:
                fs_config = mcp_servers_dict["filesystem"]
                logger.info(f"[ClaudeCodeBackend] Full filesystem MCP config being passed to SDK: {fs_config}")

        # System prompt handling based on use_default_prompt config
        # - use_default_prompt=True: Use Claude Code preset (for coding style guidelines)
        # - use_default_prompt=False (default): Use only MassGen's workflow prompt
        use_default_prompt = options_kwargs.get("use_default_prompt", False)
        if use_default_prompt and "system_prompt" not in options:
            # Use Claude Code preset as base (will be appended to in stream_with_tools)
            options["system_prompt"] = {"type": "preset", "preset": "claude_code"}
        # else: system_prompt will be set as plain string in stream_with_tools

        # Add hooks if available
        if hooks_config:
            options["hooks"] = hooks_config

        # Add can_use_tool hook to auto-grant MCP tools
        async def can_use_tool(tool_name: str, tool_args: dict, context):
            """Auto-grant permissions for MCP tools."""
            # Auto-approve all MCP tools (they start with mcp__)
            if tool_name.startswith("mcp__"):
                return PermissionResultAllow(updated_input=tool_args)
            # For non-MCP tools, use default permission behavior
            # Return None to use default permission mode
            return None

        options["can_use_tool"] = can_use_tool

        # Debug: Log the full mcp_servers config being passed to SDK
        if "mcp_servers" in options and "filesystem" in options["mcp_servers"]:
            logger.info(f"[ClaudeCodeBackend] FINAL filesystem config to SDK: {options['mcp_servers']['filesystem']}")

        # Debug: Log add_dirs to verify they're being passed
        if options.get("add_dirs"):
            logger.info(f"[ClaudeCodeBackend] FINAL add_dirs to SDK: {options['add_dirs']}")

        return ClaudeAgentOptions(**options)

    def create_client(self, **options_kwargs) -> ClaudeSDKClient:
        """Create ClaudeSDKClient with configurable parameters.

        Args:
            **options_kwargs: ClaudeAgentOptions parameters

        Returns:
            ClaudeSDKClient instance
        """

        # Build options with all parameters
        options = self._build_claude_options(**options_kwargs)

        # Create ClaudeSDKClient with configured options
        self._client = ClaudeSDKClient(options)
        return self._client

    async def stream_with_tools(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], **kwargs) -> AsyncGenerator[StreamChunk, None]:
        """
        Stream a response with tool calling support using claude-code-sdk.

        Properly handle messages and tools context for Claude Code.

        Args:
            messages: List of conversation messages
            tools: List of available tools (includes workflow tools)
            **kwargs: Additional options for client configuration

        Yields:
            StreamChunk objects with response content and metadata
        """
        # Extract agent_id from kwargs if provided and store for tool execution context
        agent_id = kwargs.get("agent_id", None)
        self._current_agent_id = agent_id  # Store for custom tool execution

        # Clear streaming buffer at start (respects _compression_retry flag)
        # This also initializes execution trace via the mixin
        self._clear_streaming_buffer(**kwargs)

        # Initialize span tracking variables for proper cleanup in all code paths
        llm_span = None
        llm_span_cm = None  # Context manager for the span
        llm_span_open = False

        log_backend_activity(
            self.get_provider_name(),
            "Starting stream_with_tools",
            {"num_messages": len(messages), "num_tools": len(tools) if tools else 0},
            agent_id=agent_id,
        )
        # Merge constructor config with stream kwargs (stream kwargs take priority)
        all_params = {**self.config, **kwargs}

        # Extract system message from messages for append mode (always do this)
        # This must be done BEFORE checking if we have a client to ensure workflow_system_prompt is always defined
        system_msg = next((msg for msg in messages if msg.get("role") == "system"), None)
        if system_msg:
            system_content = system_msg.get("content", "")  # noqa: E128
        else:
            system_content = ""

        # Build system prompt with tools information
        # This must be done before any conditional paths to ensure it's always defined
        workflow_system_prompt = self._build_system_prompt_with_workflow_tools(tools or [], system_content)

        # Check if we already have a client
        if self._client is not None:
            client = self._client
        else:
            # Set default disallowed_tools if not provided
            # Disable tools that MassGen has native implementations for
            enable_web_search = all_params.get("enable_web_search", False)

            if "disallowed_tools" not in all_params:
                disallowed_tools = [
                    # Security restrictions (dangerous bash patterns)
                    "Bash(rm*)",
                    "Bash(sudo*)",
                    "Bash(su*)",
                    "Bash(chmod*)",
                    "Bash(chown*)",
                    # Redundant tools - MassGen has native implementations
                    "Read",  # Use MassGen's read_file_content
                    "Write",  # Use MassGen's save_file_content
                    "Edit",  # Use MassGen's append_file_content
                    "MultiEdit",  # Use MassGen's append_file_content
                    "Bash",  # Use MassGen's run_shell_script
                    "BashOutput",
                    "KillShell",
                    "LS",  # MassGen has list_directory
                    "Grep",  # Use execute_command or future MassGen grep (issue 640)
                    "Glob",  # Use execute_command or future MassGen glob (issue 640)
                    "TodoWrite",  # MassGen has its own task tracking
                    "NotebookEdit",
                    "NotebookRead",
                    "mcp__ide__getDiagnostics",
                    "mcp__ide__executeCode",
                    "ExitPlanMode",
                ]

                # Only disable web tools if not enabled
                if not enable_web_search:
                    disallowed_tools.extend(["WebSearch", "WebFetch"])

                all_params["disallowed_tools"] = disallowed_tools
                logger.info(
                    f"[ClaudeCodeBackend] Using minimal tool set: Task" f"{', WebSearch, WebFetch' if enable_web_search else ''}",
                )

            # Additional disabling when MCP command_line is enabled
            # (redundant now since Bash is always disabled, but kept for explicit clarity)
            enable_mcp_command_line = all_params.get("enable_mcp_command_line", False)
            if enable_mcp_command_line:
                logger.info("[ClaudeCodeBackend] MCP command_line enabled, using execute_command for all commands")

            # Convert allowed_tools from MCP server configs to agent-level allowed_tools
            # Claude Agent SDK expects tool filtering at agent level, not server config level
            # Using allowed_tools (allowlist) hides tools entirely so Claude won't try to use them
            mcp_servers = all_params.get("mcp_servers", [])
            if isinstance(mcp_servers, list):
                # Check if any server has allowed_tools specified
                has_allowed_tools = any(isinstance(s, dict) and s.get("allowed_tools") for s in mcp_servers)

                if has_allowed_tools:
                    # Build complete allowed_tools list
                    # Start with current allowed_tools (builtin tools like Task)
                    current_allowed = all_params.get("allowed_tools", self.get_supported_builtin_tools(enable_web_search))
                    if isinstance(current_allowed, list):
                        merged_allowed = list(current_allowed)
                    else:
                        merged_allowed = [current_allowed] if current_allowed else []

                    # Add MCP tools from servers
                    for server in mcp_servers:
                        if not isinstance(server, dict):
                            continue

                        server_name = server.get("name")
                        if not server_name:
                            continue

                        server_allowed = server.get("allowed_tools")
                        if server_allowed:
                            # Server has explicit allowed_tools - add only those
                            for tool in server_allowed:
                                merged_allowed.append(f"mcp__{server_name}__{tool}")
                            logger.info(
                                f"[ClaudeCodeBackend] Server '{server_name}': allowing specific tools -> {server_allowed}",
                            )
                        else:
                            # Server has no allowed_tools - allow all its tools
                            # Use explicit tool list for known servers, wildcard for unknown
                            all_tools = self._get_all_tools_for_server(server_name)
                            if all_tools:
                                merged_allowed.extend(all_tools)
                                logger.info(
                                    f"[ClaudeCodeBackend] Server '{server_name}': allowing all {len(all_tools)} known tools",
                                )
                            else:
                                # Unknown server - use wildcard and hope it works
                                merged_allowed.append(f"mcp__{server_name}__*")
                                logger.warning(
                                    f"[ClaudeCodeBackend] Server '{server_name}': unknown server, using wildcard pattern",
                                )

                    all_params["allowed_tools"] = merged_allowed
                    logger.info(
                        f"[ClaudeCodeBackend] Set allowed_tools with {len(merged_allowed)} entries to hide filtered tools",
                    )

            # Windows-specific handling: detect long prompts that exceed CreateProcess limit
            # Windows CreateProcess has ~8,191 char limit for entire command line
            # Use conservative threshold of 4000 chars to account for other CLI arguments
            WINDOWS_PROMPT_THRESHOLD = 4000
            if sys.platform == "win32" and len(workflow_system_prompt) > WINDOWS_PROMPT_THRESHOLD:
                # Windows with long prompt: delay system prompt delivery
                # The prompt will be injected into the first user message (via stdin pipe) instead
                logger.info(
                    f"[ClaudeCodeBackend] Windows detected long system prompt " f"({len(workflow_system_prompt)} chars > {WINDOWS_PROMPT_THRESHOLD}), " "deferring delivery to first user message",
                )
                clean_params = {k: v for k, v in all_params.items() if k not in ["system_prompt"]}
                client = self.create_client(**clean_params)
                self._pending_system_prompt = workflow_system_prompt

            else:
                # Original approach for Mac/Linux and Windows with simple prompts
                try:
                    # System prompt handling based on use_default_prompt config
                    use_default_prompt = all_params.get("use_default_prompt", False)

                    if use_default_prompt:
                        # Use Claude Code preset with MassGen instructions appended
                        # This gives Claude Code's coding style guidelines + MassGen workflow tools
                        system_prompt_config = {
                            "type": "preset",
                            "preset": "claude_code",
                            "append": workflow_system_prompt,
                        }
                    else:
                        # Use only MassGen's workflow system prompt (no preset)
                        # This gives full control over agent behavior
                        system_prompt_config = workflow_system_prompt

                    client = self.create_client(**{**all_params, "system_prompt": system_prompt_config})
                    self._pending_system_prompt = None

                except Exception as create_error:
                    # Fallback for unexpected failures
                    if sys.platform == "win32":
                        clean_params = {k: v for k, v in all_params.items() if k not in ["system_prompt"]}
                        client = self.create_client(**clean_params)
                        self._pending_system_prompt = workflow_system_prompt
                    else:
                        # On Mac/Linux, re-raise the error since this shouldn't happen
                        raise create_error

        # Connect client if not already connected
        if not client._transport:
            try:
                await client.connect()

                # Setup code-based tools after connection (creates symlinks to shared tools if they exist)
                if self.filesystem_manager and self.filesystem_manager.enable_code_based_tools:
                    await self._setup_code_based_tools_symlinks()

            except Exception as e:
                yield StreamChunk(
                    type="error",
                    error=f"Failed to connect to Claude Code: {str(e)}",
                    source="claude_code",
                )
                return

        # Log backend inputs when we have workflow_system_prompt available
        if "workflow_system_prompt" in locals():
            async for debug_chunk in self._log_backend_input(messages, workflow_system_prompt, tools, kwargs):
                yield debug_chunk

        # Format the messages for Claude Code
        if not messages:
            log_stream_chunk(
                "backend.claude_code",
                "error",
                "No messages provided to stream_with_tools",
                agent_id,
            )
            # No messages to process - yield error
            yield StreamChunk(
                type="error",
                error="No messages provided to stream_with_tools",
                source="claude_code",
            )
            return

        # Validate messages - should only contain user messages for Claude Code
        user_messages = [msg for msg in messages if msg.get("role") == "user"]
        assistant_messages = [msg for msg in messages if msg.get("role") == "assistant"]

        if assistant_messages:
            log_stream_chunk(
                "backend.claude_code",
                "error",
                "Claude Code backend cannot accept assistant messages - it maintains its own conversation history",
                agent_id,
            )
            yield StreamChunk(
                type="error",
                error="Claude Code backend cannot accept assistant messages - it maintains its own conversation history",
                source="claude_code",
            )
            return

        if not user_messages:
            log_stream_chunk(
                "backend.claude_code",
                "error",
                "No user messages found to send to Claude Code",
                agent_id,
            )
            yield StreamChunk(
                type="error",
                error="No user messages found to send to Claude Code",
                source="claude_code",
            )
            return

        # Combine all user messages into a single query
        user_contents = []
        for user_msg in user_messages:
            content = user_msg.get("content", "").strip()
            if content:
                user_contents.append(content)

        if user_contents:
            # Join multiple user messages with newlines
            combined_query = "\n\n".join(user_contents)

            # Windows workaround: Inject pending system prompt into first user message
            # This avoids Windows CreateProcess command-line length limits
            if hasattr(self, "_pending_system_prompt") and self._pending_system_prompt:
                logger.info("[ClaudeCodeBackend] Injecting pending system prompt into first user message")
                combined_query = f"""<system_instructions>

                {self._pending_system_prompt}

                </system_instructions>
                ---
                {combined_query}"""

                # Clear the pending prompt after injection
                self._pending_system_prompt = None

            log_backend_agent_message(
                agent_id or "default",
                "SEND",
                {"system": workflow_system_prompt, "user": combined_query},
                backend_name=self.get_provider_name(),
            )

            # Create span for LLM interaction tracing
            tracer = get_tracer()
            model_name = self.config.get("model") or "claude-code-default"
            llm_span_attributes = {
                "llm.provider": "claude_code",
                "llm.model": model_name,
                "llm.operation": "stream",
                "gen_ai.system": "anthropic",
                "gen_ai.request.model": model_name,
            }
            if agent_id:
                llm_span_attributes["massgen.agent_id"] = agent_id
            # Get round tracking from context variable (set by orchestrator via set_current_round)
            llm_round_number, llm_round_type = get_current_round()
            if llm_round_number is not None:
                llm_span_attributes["massgen.round"] = llm_round_number
            if llm_round_type:
                llm_span_attributes["massgen.round_type"] = llm_round_type

            # Enter span context - will be closed when ResultMessage is received or on error
            # Note: tracer.span() returns a context manager, so we need to store it
            # and capture the actual span object from __enter__()
            llm_span_cm = tracer.span("llm.claude_code.stream", attributes=llm_span_attributes)
            llm_span = llm_span_cm.__enter__()
            llm_span_open = True

            await client.query(combined_query)
        else:
            log_stream_chunk("backend.claude_code", "error", "All user messages were empty", agent_id)
            yield StreamChunk(type="error", error="All user messages were empty", source="claude_code")
            return

        # Stream response and convert to MassGen StreamChunks
        accumulated_content = ""
        try:
            async for message in client.receive_response():
                if isinstance(message, (AssistantMessage, UserMessage)):
                    # Process assistant message content
                    for block in message.content:
                        if isinstance(block, ThinkingBlock):
                            # Extended thinking content (summarized for Claude 4 models)
                            thinking_text = block.thinking
                            if thinking_text:
                                log_stream_chunk("backend.claude_code", "reasoning", thinking_text, agent_id)
                                yield StreamChunk(
                                    type="reasoning",
                                    content=thinking_text,
                                    reasoning_delta=thinking_text,
                                    source="claude_code",
                                )
                                # Add to streaming buffer for compression recovery
                                self._append_reasoning_to_buffer(thinking_text)

                        elif isinstance(block, TextBlock):
                            accumulated_content += block.text

                            # Yield content chunk
                            log_backend_agent_message(
                                agent_id or "default",
                                "RECV",
                                {"content": block.text},
                                backend_name=self.get_provider_name(),
                            )
                            log_stream_chunk("backend.claude_code", "content", block.text, agent_id)
                            yield StreamChunk(type="content", content=block.text, source="claude_code")
                            # Add to streaming buffer for compression recovery
                            self._append_to_streaming_buffer(block.text)
                            # Also add to execution trace as content (model's text output)
                            # This is distinct from ThinkingBlock which would be reasoning
                            if self._execution_trace:
                                self._execution_trace.add_content(block.text)

                        elif isinstance(block, ToolUseBlock):
                            # Claude Code's builtin tool usage
                            log_backend_activity(
                                self.get_provider_name(),
                                f"Builtin tool called: {block.name}",
                                {"tool_id": block.id},
                                agent_id=agent_id,
                            )
                            log_stream_chunk(
                                "backend.claude_code",
                                "tool_use",
                                {"name": block.name, "input": block.input},
                                agent_id,
                            )

                            # Track tool_id -> tool_name for ToolResultBlock matching
                            self._tool_id_to_name[block.id] = block.name

                            # Emit tool start event in standard format (matches ContentNormalizer patterns)
                            yield StreamChunk(
                                type="content",
                                content=f"🔧 Calling {block.name}...",
                                source="claude_code",
                                tool_call_id=block.id,
                            )

                            # Emit tool arguments in standard format
                            args_str = json.dumps(block.input) if isinstance(block.input, dict) else str(block.input)
                            yield StreamChunk(
                                type="content",
                                content=f"Arguments for Calling {block.name}: {args_str}",
                                source="claude_code",
                                tool_call_id=block.id,
                            )

                            # Add to streaming buffer for compression recovery
                            tool_args = block.input if isinstance(block.input, dict) else {"input": block.input}
                            self._append_tool_call_to_buffer([{"name": block.name, "arguments": tool_args}])

                        elif isinstance(block, ToolResultBlock):
                            # Tool result from Claude Code
                            # Look up tool name from our tracking map
                            tool_name = self._tool_id_to_name.pop(block.tool_use_id, "unknown")

                            is_error = block.is_error
                            result_str = str(block.content) if block.content else ""

                            log_stream_chunk(
                                "backend.claude_code",
                                "tool_result",
                                {"tool_name": tool_name, "is_error": is_error, "content": result_str[:200]},
                                agent_id,
                            )

                            # Emit tool result in standard format (matches ContentNormalizer patterns)
                            yield StreamChunk(
                                type="content",
                                content=f"Results for Calling {tool_name}: {result_str}",
                                source="claude_code",
                                tool_call_id=block.tool_use_id,
                            )

                            # Emit tool completion in standard format
                            completion_emoji = "❌" if is_error else "✅"
                            completion_status = "failed" if is_error else "completed"
                            yield StreamChunk(
                                type="content",
                                content=f"{completion_emoji} {tool_name} {completion_status}",
                                source="claude_code",
                                tool_call_id=block.tool_use_id,
                            )

                            # Add to streaming buffer for compression recovery
                            self._append_tool_to_buffer(
                                tool_name=tool_name,
                                result_text=result_str,
                                is_error=is_error,
                            )

                    # Parse workflow tool calls from accumulated content
                    workflow_tool_calls = self._parse_workflow_tool_calls(accumulated_content)
                    if workflow_tool_calls:
                        log_stream_chunk(
                            "backend.claude_code",
                            "tool_calls",
                            workflow_tool_calls,
                            agent_id,
                        )
                        yield StreamChunk(
                            type="tool_calls",
                            tool_calls=workflow_tool_calls,
                            source="claude_code",
                        )

                    # Yield complete message
                    log_stream_chunk(
                        "backend.claude_code",
                        "complete_message",
                        accumulated_content[:200] if len(accumulated_content) > 200 else accumulated_content,
                        agent_id,
                    )
                    yield StreamChunk(
                        type="complete_message",
                        complete_message={
                            "role": "assistant",
                            "content": accumulated_content,
                        },
                        source="claude_code",
                    )

                elif isinstance(message, SystemMessage):
                    # System status updates
                    self._track_session_info(message=message)
                    log_stream_chunk(
                        "backend.claude_code",
                        "backend_status",
                        {"subtype": message.subtype, "data": message.data},
                        agent_id,
                    )
                    yield StreamChunk(
                        type="backend_status",
                        status=message.subtype,
                        content=json.dumps(message.data),
                        source="claude_code",
                    )

                elif isinstance(message, ResultMessage):
                    # Track session ID from server response
                    self._track_session_info(message)

                    # Update token usage using ResultMessage data
                    self.update_token_usage_from_result_message(message)

                    # Log structured token usage for observability
                    if message.usage:
                        usage_data = message.usage
                        if isinstance(usage_data, dict):
                            input_tokens = (usage_data.get("input_tokens", 0) or 0) + (usage_data.get("cache_read_input_tokens", 0) or 0) + (usage_data.get("cache_creation_input_tokens", 0) or 0)
                            output_tokens = usage_data.get("output_tokens", 0) or 0
                            cached_tokens = usage_data.get("cache_read_input_tokens", 0) or 0
                        else:
                            input_tokens = (
                                (getattr(usage_data, "input_tokens", 0) or 0) + (getattr(usage_data, "cache_read_input_tokens", 0) or 0) + (getattr(usage_data, "cache_creation_input_tokens", 0) or 0)
                            )
                            output_tokens = getattr(usage_data, "output_tokens", 0) or 0
                            cached_tokens = getattr(usage_data, "cache_read_input_tokens", 0) or 0

                        log_token_usage(
                            agent_id=agent_id or "unknown",
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            reasoning_tokens=0,  # Claude Code doesn't expose this separately
                            cached_tokens=cached_tokens,
                            estimated_cost=message.total_cost_usd or 0.0,
                            model=self.config.get("model") or "claude-code-default",
                        )

                    # Close LLM span on successful completion
                    if llm_span_open and llm_span_cm:
                        if message.duration_ms:
                            llm_span.set_attribute("llm.duration_ms", message.duration_ms)
                        if message.total_cost_usd:
                            llm_span.set_attribute("llm.cost_usd", message.total_cost_usd)
                        llm_span_cm.__exit__(None, None, None)
                        llm_span_open = False

                    # Yield completion
                    log_stream_chunk(
                        "backend.claude_code",
                        "complete_response",
                        {
                            "session_id": message.session_id,
                            "cost_usd": message.total_cost_usd,
                        },
                        agent_id,
                    )
                    yield StreamChunk(
                        type="complete_response",
                        complete_message={
                            "session_id": message.session_id,
                            "duration_ms": message.duration_ms,
                            "cost_usd": message.total_cost_usd,
                            "usage": message.usage,
                            "is_error": message.is_error,
                        },
                        source="claude_code",
                    )

                    # Finalize streaming buffer
                    self._finalize_streaming_buffer(agent_id=agent_id)

                    # Final done signal
                    log_stream_chunk("backend.claude_code", "done", None, agent_id)
                    yield StreamChunk(type="done", source="claude_code")
                    break

        except Exception as e:
            error_msg = str(e)

            # Finalize streaming buffer even on error
            self._finalize_streaming_buffer(agent_id=agent_id)

            # Close LLM span on error
            if llm_span_open and llm_span_cm:
                llm_span.set_attribute("error", True)
                llm_span.set_attribute("error.message", error_msg[:500])
                llm_span_cm.__exit__(type(e), e, e.__traceback__)
                llm_span_open = False

            # Provide helpful Windows-specific guidance
            if "git-bash" in error_msg.lower() or "bash.exe" in error_msg.lower():
                error_msg += (
                    "\n\nWindows Setup Required:\n"
                    "1. Install Git Bash: https://git-scm.com/downloads/win\n"
                    "2. Ensure git-bash is in PATH, or set: "
                    "CLAUDE_CODE_GIT_BASH_PATH=C:\\Program Files\\Git\\bin\\bash.exe"
                )
            elif "exit code 1" in error_msg and "win32" in str(sys.platform):
                error_msg += "\n\nThis may indicate missing git-bash on Windows. Please install Git Bash from https://git-scm.com/downloads/win"

            log_stream_chunk("backend.claude_code", "error", error_msg, agent_id)
            yield StreamChunk(
                type="error",
                error=f"Claude Code streaming error: {str(error_msg)}",
                source="claude_code",
            )

    def _track_session_info(self, message) -> None:
        """Track session information from Claude Code server responses.

        Extracts and stores session ID, working directory, and other session
        metadata from ResultMessage and SystemMessage responses to enable
        session continuation and state management across multiple interactions.

        Args:
            message: Message from Claude Code (ResultMessage or SystemMessage)
                    potentially containing session information
        """
        if ResultMessage is not None and isinstance(message, ResultMessage):
            # ResultMessage contains definitive session information
            if hasattr(message, "session_id") and message.session_id:
                self._current_session_id = message.session_id

        elif SystemMessage is not None and isinstance(message, SystemMessage):
            # SystemMessage may contain session state updates
            if hasattr(message, "data") and isinstance(message.data, dict):
                # Extract session ID from system message data
                if "session_id" in message.data and message.data["session_id"]:
                    self._current_session_id = message.data["session_id"]

                # Extract working directory from system message data
                if "cwd" in message.data and message.data["cwd"]:
                    self._cwd = message.data["cwd"]

    async def interrupt(self):
        """Send interrupt signal to gracefully stop the current operation.

        This tells the Claude Code CLI to stop its current work cleanly,
        avoiding noisy stream-closed errors that occur when the process
        is killed abruptly.
        """
        if self._client is not None:
            try:
                await self._client.interrupt()
            except Exception:
                pass  # Ignore errors during interrupt

    async def disconnect(self):
        """Disconnect the ClaudeSDKClient and clean up resources.

        Properly closes the connection and resets internal state.
        Should be called when the backend is no longer needed.
        """
        if self._client is not None:
            try:
                await self._client.disconnect()
            except Exception:
                pass  # Ignore cleanup errors
            finally:
                self._client = None
                self._current_session_id = None

    def __del__(self):
        """Cleanup on destruction.

        Note: This won't work for async cleanup in practice.
        Use explicit disconnect() calls for proper resource cleanup.
        """
        # Note: This won't work for async cleanup, but serves as documentation
        # Real cleanup should be done via explicit disconnect() calls
