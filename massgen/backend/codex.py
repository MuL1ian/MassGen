# -*- coding: utf-8 -*-
"""
OpenAI Codex Backend - Integration with OpenAI Codex CLI for MassGen.

This backend provides integration with OpenAI's Codex CLI through subprocess
wrapping and JSON event stream parsing. Supports OAuth authentication via
ChatGPT subscription or API key authentication.

Key Features:
- OAuth authentication via ChatGPT subscription (browser or device flow)
- API key fallback (OPENAI_API_KEY)
- Session persistence and resumption
- JSON event stream parsing for real-time streaming
- MCP tool support via project-scoped .codex/config.toml in workspace
- System prompt injection via model_instructions_file in config.toml
- Full conversation context maintained across turns

Architecture:
- Wraps `codex exec --json` CLI command
- Parses JSONL event stream for streaming responses
- Tracks session_id for multi-turn conversation continuity
- Delegates tool execution to Codex CLI (MCP servers, file ops, etc.)

Tool & Sandbox Design Decisions:
- Codex has native tools: shell (command exec), apply_patch (file edit),
  web_search, image_view. These are NOT duplicated by MassGen MCP tools.
- MassGen's filesystem/command_line MCPs are SKIPPED for Codex since Codex
  handles file ops and shell natively via its own sandbox.
- MassGen-specific MCPs (planning, memory, workspace_tools for media gen,
  custom tools) ARE injected via .codex/config.toml [mcp_servers].
- Codex sandbox is OS-level (Seatbelt on macOS, Landlock on Linux), NOT
  Docker-based. It does not respect MassGen's docker execution mode.
- For docker execution mode: the Codex CLI runs inside a MassGen Docker
  container (via DockerManager exec_create/exec_start with streaming).
  Uses --sandbox danger-full-access since the container provides isolation.
  Host ~/.codex/ is mounted read-only for OAuth token access.

Requirements:
- Codex CLI installed: npm install -g @openai/codex
- Either: ChatGPT Plus/Pro subscription OR OPENAI_API_KEY

Authentication Flow:
1. Check OPENAI_API_KEY environment variable
2. If not found, check for cached OAuth tokens at ~/.codex/auth.json
3. If not found, initiate OAuth flow (browser or device code)
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

try:
    import tomli_w
except ImportError:
    tomli_w = None

from ..logger_config import logger
from .base import (
    FilesystemSupport,
    LLMBackend,
    StreamChunk,
    build_workflow_instructions,
    build_workflow_mcp_instructions,
    build_workflow_mcp_server_config,
    get_multimodal_tool_definitions,
    parse_workflow_tool_calls,
)
from .native_tool_mixin import NativeToolBackendMixin


class CodexBackend(NativeToolBackendMixin, LLMBackend):
    """OpenAI Codex backend using CLI subprocess with JSON event stream.

    Provides streaming interface to Codex with OAuth support and session
    persistence. Uses `codex exec --json` for programmatic control.
    """

    # Codex event types mapped to StreamChunk types (reference only;
    # actual parsing is in _parse_codex_event / _parse_item)
    EVENT_TYPE_MAP = {
        "thread.started": "agent_status",
        "turn.started": "agent_status",
        "turn.completed": "done",
        "turn.failed": "error",
        "item.started": "content",  # wrapper: check nested item.type
        "item.completed": "content",  # wrapper: check nested item.type
        "error": "error",
    }

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """Initialize CodexBackend.

        Args:
            api_key: OpenAI API key (falls back to OPENAI_API_KEY env var).
                    If None, will attempt OAuth authentication.
            **kwargs: Additional configuration options including:
                - model: Model name (default: gpt-5.2-codex)
                - cwd: Current working directory for Codex
                - system_prompt: System prompt to prepend
                - approval_mode: Codex approval mode (full-auto, full-access, suggest)
        """
        super().__init__(api_key, **kwargs)
        self.__init_native_tool_mixin__()

        # Authentication setup
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.use_oauth = not bool(self.api_key)
        self.auth_file = Path.home() / ".codex" / "auth.json"

        # Session management
        self.session_id: Optional[str] = None
        self._session_file: Optional[Path] = None

        # Configuration
        self.model = kwargs.get("model", "gpt-5.2-codex")
        self._config_cwd = kwargs.get("cwd")  # May be relative; resolved at execution time
        self.system_prompt = kwargs.get("system_prompt", "")
        self.approval_mode = kwargs.get("approval_mode", "full-auto")
        self.mcp_servers = kwargs.get("mcp_servers", [])
        self._workspace_config_written = False
        self._custom_tools_specs_path: Optional[Path] = None

        # Agent ID (needed for Docker container lookup)
        self.agent_id = kwargs.get("agent_id")

        # Docker execution mode
        self._docker_execution = kwargs.get("command_line_execution_mode") == "docker"
        self._docker_codex_verified = False

        # Custom tools: wrap as MCP server for Codex to connect to
        custom_tools = list(kwargs.get("custom_tools", []))

        # Register multimodal tools if enabled (Codex doesn't inherit from
        # BaseWithCustomToolAndMCP which normally handles this)
        enable_multimodal = self.config.get(
            "enable_multimodal_tools",
            False,
        ) or kwargs.get("enable_multimodal_tools", False)
        if enable_multimodal:
            custom_tools.extend(get_multimodal_tool_definitions())
            logger.info("Codex backend: multimodal tools enabled (read_media, generate_media)")

        if custom_tools:
            self._setup_custom_tools_mcp(custom_tools)

        # Verify Codex CLI is available (skip in docker mode — resolved inside container)
        if self._docker_execution:
            self._codex_path = "codex"
            # Auto-enable mounting ~/.codex/ for OAuth tokens
            if self.filesystem_manager and self.filesystem_manager.docker_manager:
                self.filesystem_manager.docker_manager.mount_codex_config = True
            logger.info("Codex backend: docker execution mode — CLI will be resolved inside container")
        else:
            self._codex_path = self._find_codex_cli()
            if not self._codex_path:
                raise RuntimeError(
                    "Codex CLI not found. Install with: npm install -g @openai/codex",
                )

        # Ensure authentication is available
        if self.use_oauth and not self._has_cached_credentials():
            logger.warning(
                "No API key or cached OAuth credentials found. " "Authentication will be required on first use.",
            )

    @property
    def cwd(self) -> str:
        """Resolve the working directory, preferring filesystem_manager's workspace."""
        if self.filesystem_manager:
            return str(Path(str(self.filesystem_manager.get_current_workspace())).resolve())
        return self._config_cwd or os.getcwd()

    def _find_codex_cli(self) -> Optional[str]:
        """Find the Codex CLI executable."""
        codex_path = shutil.which("codex")
        if codex_path:
            return codex_path

        # Check common npm global paths
        npm_paths = [
            Path.home() / ".npm-global" / "bin" / "codex",
            Path("/usr/local/bin/codex"),
            Path.home() / "node_modules" / ".bin" / "codex",
        ]
        for path in npm_paths:
            if path.exists():
                return str(path)

        return None

    def _has_cached_credentials(self) -> bool:
        """Check if OAuth tokens exist at ~/.codex/auth.json."""
        return self.auth_file.exists()

    async def _ensure_authenticated(self) -> None:
        """Ensure Codex is authenticated before making requests."""
        if self.api_key:
            # API key auth - set environment variable
            os.environ["OPENAI_API_KEY"] = self.api_key
            return

        if self._has_cached_credentials():
            # OAuth tokens exist
            return

        # Need to authenticate
        logger.info("Codex authentication required. Initiating OAuth flow...")
        await self._initiate_oauth_flow()

    async def _initiate_oauth_flow(self, use_device_flow: bool = False) -> None:
        """Trigger Codex OAuth authentication.

        Args:
            use_device_flow: If True, use device code flow (for headless environments).
                           If False, use browser-based OAuth.
        """
        if use_device_flow:
            # Device code flow for headless/SSH environments
            cmd = [self._codex_path, "login", "--device-auth"]
            logger.info(
                "Starting device code authentication. " "Follow the instructions to complete login.",
            )
        else:
            # Browser-based OAuth
            cmd = [self._codex_path, "login"]
            logger.info("Opening browser for Codex authentication...")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"Codex authentication failed: {error_msg}")

        # Device flow prints instructions to stdout
        if use_device_flow and stdout:
            print(stdout.decode())

        logger.info("Codex authentication successful.")

    def _setup_custom_tools_mcp(self, custom_tools: List[Dict[str, Any]]) -> None:
        """Wrap MassGen custom tools as an MCP server and add to mcp_servers.

        Writes a tool specs JSON file and creates an MCP server config entry
        that Codex can connect to via stdio transport.
        """
        try:
            from ..mcp_tools.custom_tools_server import (
                build_server_config,
                write_tool_specs,
            )
        except ImportError:
            logger.warning("custom_tools_server not available, skipping custom tools")
            return

        # Store raw config so specs can be re-written after workspace cleanup
        self._custom_tools_config = custom_tools

        # Write specs to workspace
        specs_path = Path(self.cwd) / ".codex" / "custom_tool_specs.json"
        write_tool_specs(custom_tools, specs_path)
        self._custom_tools_specs_path = specs_path

        # Build MCP server config and add to mcp_servers
        server_config = build_server_config(
            tool_specs_path=specs_path,
            allowed_paths=[self.cwd],
            agent_id="codex",
        )
        self.mcp_servers.append(server_config)
        logger.info(f"Custom tools MCP server configured with {len(custom_tools)} tool configs")

    def _write_workspace_config(self) -> None:
        """Write a project-scoped .codex/config.toml in the workspace directory.

        This configures MCP servers and other settings for this agent's session
        without touching the user's global ~/.codex/config.toml.
        """
        config: Dict[str, Any] = {}

        # Always write custom tool specs to current workspace (cwd may change between runs)
        if getattr(self, "_custom_tools_config", None):
            from ..mcp_tools.custom_tools_server import (
                build_server_config,
                write_tool_specs,
            )

            specs_path = Path(self.cwd) / ".codex" / "custom_tool_specs.json"
            write_tool_specs(self._custom_tools_config, specs_path)
            self._custom_tools_specs_path = specs_path
            # Update the MCP server config to point to current workspace
            for s in self.mcp_servers:
                if isinstance(s, dict) and s.get("name") == "massgen_custom_tools":
                    s.update(
                        build_server_config(
                            tool_specs_path=specs_path,
                            allowed_paths=[self.cwd],
                            agent_id="codex",
                        ),
                    )
                    break

        # Convert MassGen mcp_servers list to Codex config.toml format
        # Merge orchestrator-injected servers (self.config) with init-time servers (self.mcp_servers)
        # which may include custom_tools MCP added by _setup_custom_tools_mcp()
        config_mcp = self.config.get("mcp_servers") if self.config else None
        logger.info(f"Codex _write_workspace_config: self.config mcp_servers={config_mcp is not None}, self.mcp_servers={len(self.mcp_servers)} entries")

        # Start with orchestrator servers, then add any from init (custom tools)
        mcp_servers = []
        if config_mcp is not None:
            if isinstance(config_mcp, dict):
                for name, srv_config in config_mcp.items():
                    if isinstance(srv_config, dict):
                        srv_config["name"] = name
                        mcp_servers.append(srv_config)
            elif isinstance(config_mcp, list):
                mcp_servers.extend(config_mcp)
        # Merge in self.mcp_servers (custom tools etc.) avoiding duplicates by name
        existing_names = {s.get("name") for s in mcp_servers if isinstance(s, dict)}
        for s in self.mcp_servers:
            if isinstance(s, dict) and s.get("name") not in existing_names:
                mcp_servers.append(s)
        if mcp_servers:
            logger.info(f"Codex workspace config: writing {len(mcp_servers)} MCP server(s)")
        if mcp_servers:
            mcp_section: Dict[str, Any] = {}

            for server in mcp_servers:
                # Support both list-of-dicts and dict formats
                if isinstance(server, dict):
                    name = server.get("name", "")
                    if not name:
                        continue
                    entry: Dict[str, Any] = {}
                    server_type = server.get("type", "stdio")

                    if server_type == "stdio":
                        if server.get("command"):
                            entry["command"] = server["command"]
                        if server.get("args"):
                            entry["args"] = server["args"]
                        if server.get("env"):
                            entry["env"] = server["env"]
                        if server.get("cwd"):
                            entry["cwd"] = server["cwd"]
                    elif server_type == "http":
                        if server.get("url"):
                            entry["url"] = server["url"]
                        if server.get("bearer_token_env_var"):
                            entry["bearer_token_env_var"] = server["bearer_token_env_var"]

                    # Optional fields
                    if server.get("startup_timeout_sec"):
                        entry["startup_timeout_sec"] = server["startup_timeout_sec"]
                    if server.get("tool_timeout_sec"):
                        entry["tool_timeout_sec"] = server["tool_timeout_sec"]
                    if server.get("allowed_tools"):
                        entry["enabled_tools"] = server["allowed_tools"]
                    if server.get("exclude_tools"):
                        entry["disabled_tools"] = server["exclude_tools"]

                    mcp_section[name] = entry

            if mcp_section:
                config["mcp_servers"] = mcp_section

        # Inject system prompt + workflow instructions via AGENTS.md in workspace root.
        # Codex automatically reads AGENTS.md from the working directory.
        full_prompt = self.system_prompt or ""
        pending = getattr(self, "_pending_workflow_instructions", "")
        if pending:
            full_prompt = (full_prompt + "\n" + pending) if full_prompt else pending
        if full_prompt:
            agents_md_path = Path(self.cwd) / "AGENTS.md"
            agents_md_path.write_text(full_prompt)
            logger.info(f"Wrote Codex AGENTS.md: {agents_md_path} ({len(full_prompt)} chars)")

        # Configure sandbox writable_roots for local (non-Docker) workspace-write mode.
        # Codex workspace-write sandbox allows reads everywhere but only writes to:
        #   cwd (workspace) + /tmp + writable_roots
        # MassGen pattern: workspace=write, temp_workspaces=read, context_paths per permission.
        # We only need writable_roots for context paths with write permission.
        if not self._is_docker_mode and self.approval_mode in ("full-auto", "auto-edit"):
            writable_roots = []
            if self.filesystem_manager:
                ppm = getattr(self.filesystem_manager, "path_permission_manager", None)
                if ppm:
                    for mp in getattr(ppm, "managed_paths", []):
                        if mp.path_type == "context" and getattr(mp, "will_be_writable", False):
                            writable_roots.append(str(Path(mp.path).resolve()))
            if writable_roots:
                config["sandbox_workspace_write"] = {
                    "writable_roots": writable_roots,
                    "network_access": True,
                }
                logger.info(f"Codex sandbox writable_roots: {writable_roots}")

        if not config:
            return

        # Write config
        config_dir = Path(self.cwd) / ".codex"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.toml"

        if tomli_w:
            with open(config_path, "wb") as f:
                tomli_w.dump(config, f)
        else:
            # Fallback: manual TOML generation for simple structures
            self._write_toml_fallback(config, config_path)

        self._workspace_config_written = True
        logger.info(f"Wrote Codex workspace config: {config_path}")
        logger.info(f"Codex workspace config contents: {config}")

        # Mark workspace as trusted in ~/.codex/config.toml so Codex loads
        # the project-scoped config we just wrote (untrusted projects are skipped)
        self._ensure_workspace_trusted()

    def _remove_workspace_trust(self) -> None:
        """Remove the workspace trust entry from ~/.codex/config.toml."""
        global_config_path = Path.home() / ".codex" / "config.toml"
        workspace_path = self.cwd

        try:
            if not global_config_path.exists():
                return
            content = global_config_path.read_text()
            section_header = f'[projects."{workspace_path}"]'
            if section_header not in content:
                return

            # Remove the trust section (header + trust_level line + trailing newline)
            lines = content.split("\n")
            new_lines = []
            skip = False
            for line in lines:
                if line.strip() == section_header:
                    skip = True
                    continue
                if skip:
                    # Skip lines belonging to this section until next section or blank
                    stripped = line.strip()
                    if stripped.startswith("[") or stripped == "":
                        skip = False
                        if stripped == "":
                            continue  # skip the trailing blank line
                    else:
                        continue
                new_lines.append(line)

            global_config_path.write_text("\n".join(new_lines))
            logger.info(f"Removed workspace trust entry from {global_config_path}")
        except OSError as e:
            logger.warning(f"Failed to remove workspace trust entry: {e}")

    def _ensure_workspace_trusted(self) -> None:
        """Mark the workspace as trusted in ~/.codex/config.toml.

        Codex only loads project-scoped .codex/config.toml for trusted projects.
        We add a [projects."<workspace_path>"] trust_level = "trusted" entry
        to the user's global config so our MCP servers are picked up.
        """
        global_config_path = Path.home() / ".codex" / "config.toml"
        workspace_path = self.cwd

        try:
            # Read existing global config
            existing_content = ""
            if global_config_path.exists():
                existing_content = global_config_path.read_text()

            # Check if already trusted
            if f'[projects."{workspace_path}"]' in existing_content:
                logger.info(f"Workspace already trusted in global config: {workspace_path}")
                return

            # Append trust entry
            trust_entry = f'\n[projects."{workspace_path}"]\ntrust_level = "trusted"\n'
            global_config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(global_config_path, "a") as f:
                f.write(trust_entry)
            logger.info(f"Marked workspace as trusted in {global_config_path}: {workspace_path}")
        except OSError as e:
            logger.warning(f"Failed to mark workspace as trusted: {e}")

    @staticmethod
    def _toml_value(v: Any) -> str:
        """Convert a Python value to a TOML-compatible string."""
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, str):
            if "\n" in v:
                # Use TOML multiline basic string for content with newlines
                escaped = v.replace("\\", "\\\\").replace('"""', '\\"""')
                return f'"""\n{escaped}"""'
            return json.dumps(v)  # JSON string quoting works for TOML
        if isinstance(v, (int, float)):
            return str(v)
        if isinstance(v, list):
            return "[" + ", ".join(CodexBackend._toml_value(item) for item in v) + "]"
        if isinstance(v, dict):
            # TOML inline table: {key = "value", key2 = "value2"}
            pairs = [f"{k} = {CodexBackend._toml_value(val)}" for k, val in v.items()]
            return "{" + ", ".join(pairs) + "}"
        return json.dumps(v)

    @staticmethod
    def _write_toml_fallback(config: Dict[str, Any], path: Path) -> None:
        """Write a simple TOML file without tomli_w dependency.

        Follows the Codex config.toml format from the OpenAI docs:
        - MCP servers use [mcp_servers.<name>] table headers
        - Nested dicts (like env) use [mcp_servers.<name>.<key>] sub-tables
        - Arrays and strings use standard TOML syntax
        """
        lines: List[str] = []
        # Write top-level scalar keys FIRST (before any [table] sections),
        # otherwise TOML parsers assign them to the last open table.
        table_keys: List[str] = []
        for section_key, section_val in config.items():
            if isinstance(section_val, dict):
                table_keys.append(section_key)
            else:
                lines.append(f"{section_key} = {CodexBackend._toml_value(section_val)}")
        if lines:
            lines.append("")  # blank line before tables

        for section_key in table_keys:
            section_val = config[section_key]
            for name, entry in section_val.items():
                lines.append(f"[{section_key}.{name}]")
                # Separate simple values from sub-tables (dicts)
                sub_tables: List[tuple] = []
                for k, v in entry.items():
                    if isinstance(v, dict):
                        sub_tables.append((k, v))
                    else:
                        lines.append(f"{k} = {CodexBackend._toml_value(v)}")
                lines.append("")
                # Write sub-tables after simple values
                for sub_key, sub_val in sub_tables:
                    lines.append(f"[{section_key}.{name}.{sub_key}]")
                    for sk, sv in sub_val.items():
                        lines.append(f"{sk} = {CodexBackend._toml_value(sv)}")
                    lines.append("")
        path.write_text("\n".join(lines) + "\n")

    def _cleanup_workspace_config(self) -> None:
        """Remove the project-scoped .codex/ directory we created."""
        if not self._workspace_config_written and not self._custom_tools_specs_path:
            return
        config_dir = Path(self.cwd) / ".codex"
        try:
            # Remove individual files we created
            for filename in ("config.toml", "custom_tool_specs.json", "workflow_tool_specs.json"):
                filepath = config_dir / filename
                if filepath.exists():
                    filepath.unlink()
            # Remove dir if empty
            if config_dir.exists() and not any(config_dir.iterdir()):
                config_dir.rmdir()
            # Also remove AGENTS.md we wrote in workspace root
            agents_md = Path(self.cwd) / "AGENTS.md"
            if agents_md.exists():
                agents_md.unlink()
            logger.info("Cleaned up Codex workspace config.")
        except OSError as e:
            logger.warning(f"Failed to clean up Codex workspace config: {e}")

        # Remove trust entry from global config
        self._remove_workspace_trust()

        self._workspace_config_written = False
        self._custom_tools_specs_path = None

    @property
    def _is_docker_mode(self) -> bool:
        """Check if we should execute Codex inside a Docker container."""
        if not self._docker_execution:
            return False
        if not self.filesystem_manager:
            return False
        dm = getattr(self.filesystem_manager, "docker_manager", None)
        if dm is None:
            return False
        # Check if a container exists for this agent
        agent_id = self.agent_id or getattr(self.filesystem_manager, "agent_id", None)
        if agent_id and dm.get_container(agent_id):
            return True
        return False

    def _get_docker_container(self):
        """Get the Docker container for this agent.

        Returns:
            Container object

        Raises:
            RuntimeError: If no container is available
        """
        dm = self.filesystem_manager.docker_manager
        agent_id = self.agent_id or getattr(self.filesystem_manager, "agent_id", None)
        if not agent_id:
            raise RuntimeError("No agent_id set on Codex backend for Docker execution")
        container = dm.get_container(agent_id)
        if not container:
            raise RuntimeError(f"No Docker container found for agent {agent_id}")
        return container

    def _build_exec_command(
        self,
        prompt: str,
        resume_session: bool = False,
        for_docker: bool = False,
    ) -> List[str]:
        """Build the codex exec command with appropriate flags.

        Args:
            prompt: The user prompt to send
            resume_session: Whether to resume an existing session

        Returns:
            Command list for subprocess
        """
        codex_bin = "codex" if for_docker else self._codex_path
        cmd = [codex_bin, "exec"]

        # Resume existing session or start new
        # `codex exec resume` is a subcommand with its own limited flags
        # (--json, prompt only) — model/sandbox/cwd flags are NOT accepted.
        if resume_session and self.session_id:
            cmd.extend(["resume", self.session_id])
            cmd.append("--json")
            cmd.append(prompt)
            return cmd

        # --- New session path ---
        # JSON output for parsing
        cmd.append("--json")

        # Model selection
        if self.model:
            cmd.extend(["--model", self.model])

        # Sandbox + approval mode:
        # In Docker mode, the container IS the sandbox — bypass Codex's own sandbox
        # entirely. Using --dangerously-bypass-approvals-and-sandbox (--yolo) instead
        # of --full-auto -s danger-full-access because the latter still initializes
        # Landlock on Linux, which fails in containers without the required kernel
        # capabilities (error: "Sandbox(LandlockRestrict)").
        if for_docker:
            cmd.append("--dangerously-bypass-approvals-and-sandbox")
        elif self.approval_mode == "full-access":
            # Full filesystem access but still auto-approve via --full-auto
            cmd.extend(["--full-auto", "-s", "danger-full-access"])
        elif self.approval_mode == "dangerous-no-sandbox":
            cmd.append("--dangerously-bypass-approvals-and-sandbox")
        elif self.approval_mode in ("full-auto", "auto-edit"):
            # Sandboxed to workspace dir (default for MassGen)
            cmd.append("--full-auto")
        # "suggest" / default: no flag (but MassGen defaults to full-auto)

        # Working directory flag
        if self.cwd:
            cmd.extend(["-C", self.cwd])

        # Skip git repo requirement (MassGen workspaces may not be git repos)
        cmd.append("--skip-git-repo-check")

        # Add the prompt
        cmd.append(prompt)

        return cmd

    def _parse_codex_event(self, event: Dict[str, Any]) -> Optional[StreamChunk]:
        """Parse a Codex JSON event into a StreamChunk.

        Handles both the documented item.started/item.completed wrapper format
        (with nested item.type) and legacy direct event names as fallback.

        Args:
            event: Parsed JSON event from Codex

        Returns:
            StreamChunk or None if event should be skipped
        """
        event_type = event.get("type", "")

        # Extract session ID from thread.started
        if event_type == "thread.started":
            self.session_id = event.get("session_id") or event.get("thread_id")
            logger.info(f"Codex session started: {self.session_id}")
            return StreamChunk(
                type="agent_status",
                status="session_started",
                detail=f"Session: {self.session_id}",
            )

        # Handle item.started / item.completed wrapper format
        # These wrap a nested "item" dict with its own "type" field
        if event_type in ("item.started", "item.completed"):
            item = event.get("item", {})
            item_type = item.get("type", "")
            return self._parse_item(item_type, item)

        # Legacy direct event names (fallback)
        if event_type.startswith("item."):
            return self._parse_item(event_type, event)

        # Handle turn completion
        if event_type == "turn.completed":
            usage = event.get("usage", {})
            return StreamChunk(
                type="done",
                usage={
                    "prompt_tokens": usage.get("input_tokens", 0),
                    "completion_tokens": usage.get("output_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
            )

        if event_type == "turn.started":
            return StreamChunk(
                type="agent_status",
                status="turn_started",
            )

        # Handle errors - message is at top level, not nested
        if event_type in ("turn.failed", "error"):
            error_msg = event.get("message") or event.get("error", {}).get("message") or str(event)
            return StreamChunk(type="error", error=error_msg)

        # Skip unknown events
        logger.debug(f"Skipping unknown Codex event type: {event_type}")
        return None

    def _parse_item(self, item_type: str, item: Dict[str, Any]) -> Optional[StreamChunk]:
        """Parse an item by its type, used by both wrapper and legacy formats.

        Actual Codex v0.92 item types (from JSONL):
          - agent_message: {text: "..."} — main assistant output
          - reasoning: {text: "..."} — thinking/reasoning
          - command_execution: {command, aggregated_output, exit_code, status}
          - file_write: {path, content} — file creation/modification
          - tool_call / tool_result — MCP tool usage
        """

        # Agent message (main content output)
        if item_type in ("agent_message", "message", "item.message"):
            text = item.get("text") or item.get("content", "")
            if isinstance(text, list):
                text_parts = [c.get("text", "") for c in text if c.get("type") == "text"]
                text = "".join(text_parts)
            return StreamChunk(type="content", content=text)

        # Reasoning / thinking
        if item_type in ("reasoning", "item.reasoning"):
            return StreamChunk(
                type="reasoning",
                reasoning_delta=item.get("text") or item.get("content", ""),
            )

        # Command execution (shell commands)
        if item_type in ("command_execution", "command", "item.command"):
            command = item.get("command", "")
            output = item.get("aggregated_output") or item.get("output", "")
            status = item.get("status", "")
            exit_code = item.get("exit_code")
            suffix = ""
            if exit_code is not None and exit_code != 0:
                suffix = f" (exit {exit_code})"
            # Only emit for completed commands (skip in_progress)
            if status == "in_progress":
                return None
            return StreamChunk(
                type="content",
                content=f"$ {command}{suffix}\n{output}".rstrip(),
            )

        # File write / change (docs: fileChange has changes: [{path, kind, diff}])
        if item_type in ("file_write", "file_change", "fileChange", "item.file_change"):
            changes = item.get("changes", [])
            if changes:
                parts = []
                for change in changes:
                    path = change.get("path", "unknown")
                    kind = change.get("kind", "edit")
                    diff = change.get("diff", "")
                    parts.append(f"[File {kind}: {path}]")
                    if diff:
                        parts.append(diff)
                return StreamChunk(type="content", content="\n".join(parts))
            # Fallback for simpler format
            file_path = item.get("path", "unknown")
            return StreamChunk(type="content", content=f"[File written: {file_path}]")

        # MCP tool calls (docs: mcpToolCall {server, tool, status, arguments, result, error})
        if item_type in ("mcp_tool_call", "mcpToolCall", "tool_call", "item.tool_call"):
            tool_name = item.get("tool") or item.get("name", "")
            server = item.get("server", "")
            status = item.get("status", "")
            # For completed calls with results, emit as content
            if status == "completed" and item.get("result") is not None:
                result = item.get("result", "")
                # Check if this is a workflow MCP tool result — extract and emit as tool_calls
                if server == "massgen_workflow_tools":
                    workflow_call = self._try_extract_workflow_mcp_result_from_codex(result)
                    if workflow_call:
                        return StreamChunk(
                            type="tool_calls",
                            tool_calls=[workflow_call],
                            source="codex",
                        )
                return StreamChunk(
                    type="content",
                    content=f"[MCP {server}/{tool_name}]: {result}",
                )
            # For in-progress or started, emit as tool_call
            # Skip workflow MCP tools — only the completed result matters
            if status != "completed":
                if server == "massgen_workflow_tools":
                    return None
                tool_call = {
                    "id": item.get("id", ""),
                    "name": f"{server}/{tool_name}" if server else tool_name,
                    "arguments": item.get("arguments", {}),
                }
                return StreamChunk(type="tool_calls", tool_calls=[tool_call])
            # Completed with error
            if item.get("error"):
                return StreamChunk(
                    type="content",
                    content=f"[MCP {server}/{tool_name} error]: {item['error']}",
                )
            return None

        # Web search (docs: webSearch {query})
        if item_type in ("web_search", "webSearch"):
            query = item.get("query", "")
            return StreamChunk(type="content", content=f"[Web search: {query}]")

        # Image view (docs: imageView {path})
        if item_type in ("image_view", "imageView"):
            return StreamChunk(
                type="content",
                content=f"[Image: {item.get('path', '')}]",
            )

        logger.debug(f"Skipping unknown Codex item type: {item_type}")
        return None

    async def stream_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        **kwargs,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream a response from Codex with tool support.

        Codex handles tools internally via MCP servers configured in
        ~/.codex/config.toml. The tools parameter is used for MassGen's
        workflow tools (new_answer, vote, etc.) which are injected via
        system prompt.

        Args:
            messages: Conversation messages
            tools: Available tools schema (used for system prompt injection)
            **kwargs: Additional parameters

        Yields:
            StreamChunk: Standardized response chunks
        """
        await self._ensure_authenticated()

        # Extract system message from messages and merge into instructions file
        # The orchestrator injects the full system prompt (task context, coordination
        # instructions, etc.) as the first system message.  Codex only receives a
        # single user-prompt via CLI, so we must surface the system content through
        # the model_instructions_file.
        system_from_messages = ""
        for msg in messages:
            if msg.get("role") == "system":
                c = msg.get("content", "")
                if isinstance(c, str):
                    system_from_messages = c
                elif isinstance(c, list):
                    system_from_messages = "".join(p.get("text", "") for p in c if p.get("type") == "text")
                break  # Use first system message only

        if system_from_messages:
            # Override the backend's system_prompt so _write_workspace_config picks it up
            self.system_prompt = system_from_messages
            logger.info(f"Codex: injected system message from orchestrator ({len(system_from_messages)} chars)")

        # Setup workflow tools as MCP server (preferred) or text instructions (fallback)
        tool_names = [t.get("function", {}).get("name", "?") for t in (tools or [])]
        logger.info(f"Codex stream_with_tools: received {len(tools or [])} tools: {tool_names}")

        # Try to set up workflow tools as native MCP tools
        workflow_mcp_config = build_workflow_mcp_server_config(
            tools or [],
            str(Path(self.cwd) / ".codex"),
        )
        if workflow_mcp_config:
            # Add workflow MCP server to mcp_servers for this session
            # Remove any previous workflow server entry
            self.mcp_servers = [s for s in self.mcp_servers if not (isinstance(s, dict) and s.get("name") == "massgen_workflow_tools")]
            self.mcp_servers.append(workflow_mcp_config)
            # Still inject instructions so the agent knows it MUST call the tools
            self._pending_workflow_instructions = build_workflow_mcp_instructions(tools or [])
            logger.info("Codex: workflow tools configured as native MCP server")
        else:
            # Fallback: text-based workflow instructions
            self._pending_workflow_instructions = build_workflow_instructions(tools or [])
            logger.info(f"Codex workflow instructions (text fallback): {len(self._pending_workflow_instructions)} chars")

        has_workflow_mcp = workflow_mcp_config is not None

        # Write project-scoped config with MCP servers (+ workflow instructions if fallback)
        self._write_workspace_config()

        # Extract the latest user message as the prompt
        prompt = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    prompt = content
                elif isinstance(content, list):
                    # Handle content blocks
                    text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
                    prompt = "".join(text_parts)
                break

        if not prompt:
            yield StreamChunk(type="error", error="No user message found in messages")
            return

        # Resume session if we have one — Codex maintains server-side history,
        # so even single-message enforcement retries should resume the session
        resume_session = self.session_id is not None

        # Start API call timing
        self.start_api_call_timing(self.model)

        # Accumulate text content to parse workflow tool calls after streaming
        accumulated_content = ""
        held_done_chunk = None
        has_workflow = has_workflow_mcp or bool(self._pending_workflow_instructions)
        got_workflow_tool_calls = False

        stream = self._stream_docker(prompt, resume_session) if self._is_docker_mode else self._stream_local(prompt, resume_session)
        async for chunk in stream:
            if chunk.type == "content" and chunk.content:
                accumulated_content += chunk.content
            # Track if workflow tool_calls arrived from MCP (via _parse_item)
            if chunk.type == "tool_calls" and has_workflow_mcp:
                got_workflow_tool_calls = True
            # Hold the done chunk so we can attach workflow tool calls to it
            if chunk.type == "done" and has_workflow:
                held_done_chunk = chunk
                continue
            yield chunk

        # Text parsing fallback — only if MCP didn't produce workflow tool calls
        if not got_workflow_tool_calls and has_workflow and accumulated_content:
            workflow_tool_calls = parse_workflow_tool_calls(accumulated_content)
            if workflow_tool_calls:
                logger.info(f"Codex: parsed {len(workflow_tool_calls)} workflow tool call(s) from text")
                yield StreamChunk(type="tool_calls", tool_calls=workflow_tool_calls, source="codex")
        if held_done_chunk:
            yield held_done_chunk

    async def _stream_docker(
        self,
        prompt: str,
        resume_session: bool,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream Codex output by running inside a Docker container."""
        try:
            container = self._get_docker_container()

            # Verify codex exists in container (first call only)
            if not self._docker_codex_verified:
                exit_code, output = container.exec_run("which codex")
                if exit_code != 0:
                    yield StreamChunk(
                        type="error",
                        error=("codex CLI not found in Docker container. " "Add '@openai/codex' to command_line_docker_packages.preinstall.npm " "or use a Docker image with codex pre-installed."),
                    )
                    self.end_api_call_timing(success=False, error="codex not found in container")
                    return
                self._docker_codex_verified = True

            # Build command for docker execution
            cmd = self._build_exec_command(prompt, resume_session=resume_session, for_docker=True)

            # Auth: copy host ~/.codex/auth.json into workspace .codex/ dir,
            # then set HOME to workspace so Codex finds it at ~/. codex/auth.json.
            # The workspace is writable, so Codex can also write session files there.
            workspace = self.cwd
            codex_dir = Path(workspace) / ".codex"
            codex_dir.mkdir(parents=True, exist_ok=True)
            host_auth = Path.home() / ".codex" / "auth.json"
            if host_auth.exists():
                import shutil

                shutil.copy2(str(host_auth), str(codex_dir / "auth.json"))
                logger.info("Codex Docker auth: copied OAuth tokens to workspace .codex/")
            else:
                logger.warning("Codex Docker auth: no ~/.codex/auth.json found on host")

            exec_env = {"NO_COLOR": "1", "HOME": workspace}

            logger.info(f"Running Codex in Docker: {cmd}")

            # Create exec instance — pass cmd as list to avoid shell escaping issues
            exec_id = container.client.api.exec_create(
                container.id,
                cmd=cmd,
                stdout=True,
                stderr=True,
                workdir=self.cwd,
                environment=exec_env,
            )["Id"]

            # Stream output using a queue for async iteration
            output_gen = container.client.api.exec_start(exec_id, stream=True, detach=False)

            loop = asyncio.get_event_loop()
            queue: asyncio.Queue = asyncio.Queue()

            async def _read_output():
                """Read Docker output in executor and push lines to queue."""
                buffer = ""

                def _iterate():
                    nonlocal buffer
                    for raw_chunk in output_gen:
                        text = raw_chunk.decode("utf-8", errors="replace")
                        buffer += text
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            line = line.strip()
                            if line:
                                # Put line synchronously from executor thread
                                pass

                                # Use a thread-safe approach
                                loop.call_soon_threadsafe(queue.put_nowait, line)
                    # Flush remaining buffer
                    if buffer.strip():
                        loop.call_soon_threadsafe(queue.put_nowait, buffer.strip())
                    loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

                await loop.run_in_executor(None, _iterate)

            # Start reader task
            reader_task = asyncio.ensure_future(_read_output())

            first_content = True

            while True:
                line_str = await queue.get()
                if line_str is None:
                    break

                try:
                    event = json.loads(line_str)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse Codex event: {line_str}")
                    continue

                logger.info(f"Codex raw event (docker): {json.dumps(event, default=str)[:500]}")
                chunk = self._parse_codex_event(event)
                if chunk:
                    if first_content and chunk.type == "content":
                        self.record_first_token()
                        first_content = False

                    yield chunk

                    if chunk.type == "done" and chunk.usage:
                        self._update_token_usage_from_api_response(
                            chunk.usage,
                            self.model,
                        )

            await reader_task

            # Check exec exit code
            exec_inspect = container.client.api.exec_inspect(exec_id)
            exit_code = exec_inspect.get("ExitCode", -1)
            if exit_code != 0:
                yield StreamChunk(type="error", error=f"Codex exited with code {exit_code}")
                self.end_api_call_timing(success=False, error=f"Exit code {exit_code}")
            else:
                self.end_api_call_timing(success=True)

        except Exception as e:
            logger.error(f"Codex Docker backend error: {e}")
            self.end_api_call_timing(success=False, error=str(e))
            yield StreamChunk(type="error", error=str(e))

    async def _stream_local(
        self,
        prompt: str,
        resume_session: bool,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream Codex output via local subprocess."""
        # Build command
        cmd = self._build_exec_command(prompt, resume_session=resume_session)

        logger.info(f"Running Codex command: {' '.join(cmd)}")

        try:
            # Start subprocess
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd,
                env={**os.environ, "NO_COLOR": "1"},  # Disable ANSI colors
            )

            first_content = True

            # Stream and parse JSONL output
            async for line in proc.stdout:
                line_str = line.decode().strip()
                if not line_str:
                    continue

                try:
                    event = json.loads(line_str)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse Codex event: {line_str}")
                    continue

                logger.info(f"Codex raw event: {json.dumps(event, default=str)[:500]}")
                chunk = self._parse_codex_event(event)
                if chunk:
                    # Record first token timing
                    if first_content and chunk.type == "content":
                        self.record_first_token()
                        first_content = False

                    yield chunk

                    # Update token usage on completion
                    if chunk.type == "done" and chunk.usage:
                        self._update_token_usage_from_api_response(
                            chunk.usage,
                            self.model,
                        )

            # Wait for process to complete
            await proc.wait()

            if proc.returncode != 0:
                stderr = await proc.stderr.read()
                error_msg = stderr.decode() if stderr else f"Exit code {proc.returncode}"
                yield StreamChunk(type="error", error=f"Codex error: {error_msg}")
                self.end_api_call_timing(success=False, error=error_msg)
            else:
                self.end_api_call_timing(success=True)

        except Exception as e:
            logger.error(f"Codex backend error: {e}")
            self.end_api_call_timing(success=False, error=str(e))
            yield StreamChunk(type="error", error=str(e))

    @staticmethod
    def _try_extract_workflow_mcp_result_from_codex(result: Any) -> Optional[Dict[str, Any]]:
        """Extract a workflow tool call from a Codex MCP tool result.

        Codex MCP results come as dicts like:
            {'content': [{'text': '{"status":"ok","server":"massgen_workflow_tools",...}', 'type': 'text'}],
             'structured_content': None}

        Or sometimes as raw JSON strings.

        Returns:
            Tool call dict in orchestrator format, or None.
        """
        from ..mcp_tools.workflow_tools_server import extract_workflow_tool_call

        json_str = None

        if isinstance(result, dict):
            # Codex wraps MCP results in {'content': [{'text': '...', 'type': 'text'}], ...}
            content_list = result.get("content", [])
            if isinstance(content_list, list):
                for item in content_list:
                    if isinstance(item, dict) and item.get("type") == "text":
                        json_str = item.get("text", "")
                        break
            if not json_str:
                # Try the result dict itself
                return extract_workflow_tool_call(result)
        elif isinstance(result, str):
            json_str = result

        if not json_str:
            return None

        try:
            parsed = json.loads(json_str)
            return extract_workflow_tool_call(parsed)
        except (json.JSONDecodeError, TypeError):
            return None

    def get_disallowed_tools(self, config: Dict[str, Any]) -> List[str]:
        """Return Codex native tools to disable.

        Codex keeps all its native tools (shell, file_read, file_write,
        file_edit, web_search) since MassGen skips attaching MCP equivalents
        for categories the backend handles natively (see tool_category_overrides).

        Tool filtering for MCP servers is handled separately via
        enabled_tools/disabled_tools in .codex/config.toml per server.

        Codex also supports disabling built-in tools via config.toml:
        - [features].shell_tool = false
        - web_search = "disabled"

        Args:
            config: Backend config dict.

        Returns:
            Empty list — all native tools are kept.
        """
        return []

    def get_tool_category_overrides(self) -> Dict[str, str]:
        """Return tool category overrides for Codex.

        Codex has native tools for filesystem, command execution, file search,
        and web search. MassGen overrides native planning and subagent tools
        with its own implementations.
        """
        return {
            "filesystem": "skip",  # Native: file_read, file_write, file_edit
            "command_execution": "skip",  # Native: shell
            "file_search": "skip",  # Native: shell (rg/sg available)
            "web_search": "skip",  # Native: web_search
            "planning": "override",  # Override with MassGen planning MCP
            "subagents": "override",  # Override with MassGen spawn_subagents
        }

    def get_provider_name(self) -> str:
        """Get the name of this provider."""
        return "codex"

    def get_filesystem_support(self) -> FilesystemSupport:
        """Codex has native filesystem support via built-in tools."""
        return FilesystemSupport.NATIVE

    def is_stateful(self) -> bool:
        """Codex maintains session state via session files."""
        return True

    async def reset_state(self) -> None:
        """Reset session state for new conversation."""
        self.session_id = None
        self._session_file = None
        self._pending_workflow_instructions = ""
        self._cleanup_workspace_config()
        logger.info("Codex session state reset.")

    async def clear_history(self) -> None:
        """Clear conversation history while maintaining session.

        For Codex, this starts a fresh session.
        """
        self.session_id = None
        self._session_file = None
        self._cleanup_workspace_config()


# Register backend in the factory (add to cli.py create_backend function)
# "codex" -> CodexBackend
