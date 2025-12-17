# -*- coding: utf-8 -*-
"""
FastAPI Web Server for MassGen Web UI

Provides WebSocket endpoints for real-time coordination updates
and serves the React frontend.
"""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Set

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from massgen.frontend.displays.web_display import WebDisplay


class ConnectionManager:
    """Manages WebSocket connections per session."""

    def __init__(self):
        # session_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # session_id -> WebDisplay instance
        self.displays: Dict[str, WebDisplay] = {}
        # session_id -> orchestration task
        self.tasks: Dict[str, asyncio.Task] = {}
        # session_id -> log session directory (for multi-turn continuation)
        self.session_log_dirs: Dict[str, Path] = {}
        # session_id -> current turn number
        self.session_turns: Dict[str, int] = {}
        # session_id -> config path used
        self.session_configs: Dict[str, str] = {}
        # Completed sessions: session_id -> metadata (persists after disconnect)
        self.completed_sessions: Dict[str, Dict[str, Any]] = {}

    def mark_session_completed(self, session_id: str, question: str = None, config: str = None) -> None:
        """Mark a session as completed so it persists in the session list."""
        import time

        self.completed_sessions[session_id] = {
            "question": question,
            "config": config,
            "completed_at": time.time(),
        }

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(websocket)

    def disconnect(self, websocket: WebSocket, session_id: str) -> None:
        """Remove a WebSocket connection."""
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            # Clean up empty sessions
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast(self, session_id: str, message: Dict[str, Any]) -> None:
        """Broadcast message to all clients in a session."""
        if session_id not in self.active_connections:
            return

        disconnected = set()
        for websocket in self.active_connections[session_id]:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.add(websocket)

        # Clean up disconnected clients
        self.active_connections[session_id] -= disconnected

    def get_display(self, session_id: str) -> Optional[WebDisplay]:
        """Get the WebDisplay for a session."""
        return self.displays.get(session_id)

    def create_display(self, session_id: str, agent_ids: list, agent_models: Optional[Dict[str, str]] = None) -> WebDisplay:
        """Create a new WebDisplay for a session."""

        async def broadcast_fn(message: Dict[str, Any]) -> None:
            await self.broadcast(session_id, message)

        display = WebDisplay(
            agent_ids=agent_ids,
            broadcast=broadcast_fn,
            session_id=session_id,
            agent_models=agent_models,
        )
        self.displays[session_id] = display
        return display


# Global connection manager
manager = ConnectionManager()

# Default config path (set from CLI)
_default_config_path: Optional[str] = None


def set_default_config(config_path: Optional[str]) -> None:
    """Set the default config path for new sessions."""
    global _default_config_path
    _default_config_path = config_path


def get_default_config() -> Optional[str]:
    """Get the default config path."""
    return _default_config_path


def create_app(config_path: Optional[str] = None, automation_mode: bool = False) -> "FastAPI":
    """Create and configure the FastAPI application.

    Args:
        config_path: Default config path for coordination sessions
        automation_mode: If True, UI shows automation-friendly timeline view
    """
    if not FASTAPI_AVAILABLE:
        raise ImportError(
            "FastAPI is not installed. Install with: pip install massgen",
        )

    # Store default config
    if config_path:
        set_default_config(config_path)

    app = FastAPI(
        title="MassGen Web UI",
        description="Real-time multi-agent coordination visualization",
        version="0.1.0",
    )

    # Store automation_mode in app state for WebSocket access
    app.state.automation_mode = automation_mode

    # CORS for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, restrict this
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # =========================================================================
    # API Routes
    # =========================================================================

    @app.get("/api/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok", "service": "massgen-web"}

    @app.get("/api/config")
    async def get_config():
        """Get current default config path."""
        return {"config_path": get_default_config()}

    @app.get("/api/config/content")
    async def get_config_content(path: str):
        """Get the content of a config file."""
        try:
            config_path = Path(path)
            if not config_path.exists():
                return JSONResponse(
                    status_code=404,
                    content={"error": "Config file not found"},
                )
            if not config_path.is_file():
                return JSONResponse(
                    status_code=400,
                    content={"error": "Path is not a file"},
                )
            # Security: ensure path is within allowed locations
            config_path = config_path.resolve()
            allowed_paths = [
                Path.home() / ".config" / "massgen",
            ]
            try:
                import massgen

                package_dir = Path(massgen.__file__).parent
                allowed_paths.append(package_dir / "configs")
            except Exception:
                pass

            is_allowed = any(str(config_path).startswith(str(allowed.resolve())) for allowed in allowed_paths)
            if not is_allowed:
                return JSONResponse(
                    status_code=403,
                    content={"error": "Access denied"},
                )

            content = config_path.read_text(encoding="utf-8")
            return {"content": content, "path": str(config_path)}
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": str(e)},
            )

    @app.get("/api/configs")
    async def list_configs():
        """List all available config files."""
        configs = []
        quickstart_config = None

        # Check for user's default config at ~/.config/massgen/config.yaml
        user_config_path = Path.home() / ".config" / "massgen" / "config.yaml"
        if user_config_path.exists():
            quickstart_config = {
                "name": "Default Config",
                "path": str(user_config_path),
                "category": "user",
                "relative": "config.yaml",
            }
            configs.append(quickstart_config)

        # Get configs from massgen package
        try:
            import massgen

            package_dir = Path(massgen.__file__).parent
            configs_dir = package_dir / "configs"

            if configs_dir.exists():
                for yaml_file in configs_dir.rglob("*.yaml"):
                    # Get relative path from configs dir
                    rel_path = yaml_file.relative_to(configs_dir)
                    configs.append(
                        {
                            "name": yaml_file.stem,
                            "path": str(yaml_file),
                            "category": str(rel_path.parent) if rel_path.parent != Path(".") else "root",
                            "relative": str(rel_path),
                        },
                    )
        except Exception:
            pass

        # Sort by category then name (user configs first)
        def sort_key(x):
            # Put 'user' category first, then sort alphabetically
            if x["category"] == "user":
                return ("0", x["name"])
            return (x["category"], x["name"])

        configs.sort(key=sort_key)

        # Use quickstart config as default if it exists, otherwise CLI default
        default = str(user_config_path) if user_config_path.exists() else get_default_config()

        return {
            "configs": configs,
            "default": default,
            "quickstart_config": str(user_config_path) if user_config_path.exists() else None,
        }

    # =========================================================================
    # Quickstart Wizard API Routes
    # =========================================================================

    @app.get("/api/setup/status")
    async def get_setup_status():
        """Check if setup is needed (no config exists) and Docker availability."""
        from pathlib import Path

        from massgen.utils.docker_diagnostics import diagnose_docker

        # Check if default config exists
        config_path = Path.home() / ".config" / "massgen" / "config.yaml"
        has_config = config_path.exists()

        # Check Docker using diagnostics
        diagnostics = diagnose_docker()

        return {
            "needs_setup": not has_config,
            "has_config": has_config,
            "config_path": str(config_path),
            "docker_available": diagnostics.is_available,
            "docker_status": diagnostics.status.value,
            "docker_error": diagnostics.error_message if not diagnostics.is_available else None,
            "docker_resolution": diagnostics.resolution_steps if not diagnostics.is_available else None,
        }

    @app.get("/api/docker/diagnostics")
    async def get_docker_diagnostics():
        """Get comprehensive Docker diagnostics.

        Returns detailed information about Docker installation status,
        daemon availability, permissions, and installed images.
        """
        from massgen.utils.docker_diagnostics import diagnose_docker

        diagnostics = diagnose_docker()
        return diagnostics.to_dict()

    @app.get("/api/setup/env-status")
    async def get_env_status():
        """Check which .env files exist and their locations."""
        from pathlib import Path

        home_env = Path.home() / ".massgen" / ".env"
        local_env = Path.cwd() / ".env"

        return {
            "global_env": {
                "path": str(home_env),
                "exists": home_env.exists(),
            },
            "local_env": {
                "path": str(local_env),
                "exists": local_env.exists(),
            },
            "recommended": "global",
        }

    @app.post("/api/setup/api-keys")
    async def save_api_keys(request_data: dict):
        """Save API keys to .env file.

        Request body:
        {
            "keys": {
                "OPENAI_API_KEY": "sk-...",
                "ANTHROPIC_API_KEY": "sk-ant-..."
            },
            "save_location": "global" | "local"
        }

        Returns:
            {"success": true, "saved_to": "...", "saved_keys": ["OPENAI_API_KEY", ...]}
        """
        import os
        from pathlib import Path

        keys = request_data.get("keys", {})
        save_location = request_data.get("save_location", "global")

        if not keys:
            return JSONResponse(
                {"error": "No API keys provided"},
                status_code=400,
            )

        # Validate keys format (basic sanity checks)
        for key_name, key_value in keys.items():
            if not key_name or not isinstance(key_name, str):
                return JSONResponse(
                    {"error": f"Invalid key name: {key_name}"},
                    status_code=400,
                )
            if not key_value or not isinstance(key_value, str):
                return JSONResponse(
                    {"error": f"Invalid value for {key_name}"},
                    status_code=400,
                )

        # Determine save path
        if save_location == "global":
            env_dir = Path.home() / ".massgen"
            env_path = env_dir / ".env"
        else:
            env_dir = Path.cwd()
            env_path = env_dir / ".env"

        try:
            # Create directory if needed
            env_dir.mkdir(parents=True, exist_ok=True)

            # Load existing env vars if file exists
            existing_vars = {}
            if env_path.exists():
                with open(env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            name, _, value = line.partition("=")
                            existing_vars[name.strip()] = value.strip().strip('"').strip("'")

            # Merge new keys (overwrite existing)
            existing_vars.update(keys)

            # Write back
            with open(env_path, "w") as f:
                f.write("# MassGen API Keys\n")
                f.write("# Generated by MassGen WebUI Setup\n\n")
                for name, value in sorted(existing_vars.items()):
                    f.write(f'{name}="{value}"\n')

            # Set file permissions (600 - owner read/write only)
            os.chmod(env_path, 0o600)

            # Reload into current environment
            for name, value in keys.items():
                os.environ[name] = value

            return {
                "success": True,
                "saved_to": str(env_path),
                "saved_keys": list(keys.keys()),
                "message": f"Saved {len(keys)} API key(s) to {env_path}",
            }

        except Exception as e:
            return JSONResponse(
                {"error": f"Failed to save API keys: {str(e)}"},
                status_code=500,
            )

    @app.post("/api/docker/pull")
    async def start_docker_pull(request_data: dict):
        """Start pulling Docker images.

        Request body:
        {
            "images": ["ghcr.io/massgen/mcp-runtime-sudo:latest"]
        }

        Returns:
            {"job_id": "uuid", "status": "started"}
        """
        images = request_data.get("images", [])

        if not images:
            return JSONResponse(
                {"error": "No images specified"},
                status_code=400,
            )

        job_id = str(uuid.uuid4())

        # Store job info for tracking
        if not hasattr(app, "_docker_pull_jobs"):
            app._docker_pull_jobs = {}

        app._docker_pull_jobs[job_id] = {
            "images": images,
            "status": "started",
            "progress": {},
            "completed": False,
            "error": None,
        }

        return {
            "job_id": job_id,
            "status": "started",
            "images": images,
        }

    @app.get("/api/docker/pull/{job_id}/stream")
    async def stream_docker_pull(job_id: str):
        """Stream Docker pull progress via Server-Sent Events.

        Returns SSE stream with progress updates.
        """
        from starlette.responses import StreamingResponse

        if not hasattr(app, "_docker_pull_jobs"):
            app._docker_pull_jobs = {}

        job = app._docker_pull_jobs.get(job_id)
        if not job:
            return JSONResponse(
                {"error": "Job not found"},
                status_code=404,
            )

        async def generate():
            import json

            try:
                import docker

                client = docker.from_env()
            except Exception as e:
                yield f"data: {json.dumps({'event': 'error', 'error': str(e)})}\n\n"
                return

            images = job["images"]

            for image in images:
                yield f"data: {json.dumps({'event': 'start', 'image': image})}\n\n"

                try:
                    # Pull with streaming progress
                    for line in client.api.pull(image, stream=True, decode=True):
                        status = line.get("status", "")
                        progress = line.get("progress", "")
                        layer_id = line.get("id", "")

                        yield f"data: {json.dumps({'event': 'progress', 'image': image, 'status': status, 'progress': progress, 'layer_id': layer_id})}\n\n"

                    yield f"data: {json.dumps({'event': 'complete', 'image': image, 'success': True})}\n\n"

                except Exception as e:
                    yield f"data: {json.dumps({'event': 'error', 'image': image, 'error': str(e)})}\n\n"

            yield f"data: {json.dumps({'event': 'done', 'all_complete': True})}\n\n"

            # Clean up job
            if job_id in app._docker_pull_jobs:
                del app._docker_pull_jobs[job_id]

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/api/skills")
    async def list_skills():
        """List all available skills (built-in, user-installed, and project).

        Returns skills from:
        - Built-in: massgen/skills/
        - User: ~/.agent/skills/ (home directory - where openskills installs)
        - Project: .agent/skills/ (current working directory)
        """
        from pathlib import Path

        import massgen

        skills = []
        seen_names = set()  # Track seen skill names to avoid duplicates

        def add_skills_from_dir(skills_dir: Path, location: str) -> None:
            """Helper to add skills from a directory."""
            if not skills_dir.exists():
                return

            for skill_dir in skills_dir.iterdir():
                if skill_dir.is_dir() and skill_dir.name not in seen_names:
                    skill_md = skill_dir / "SKILL.md"
                    if skill_md.exists():
                        description = ""
                        try:
                            content = skill_md.read_text()
                            lines = content.strip().split("\n")
                            for line in lines:
                                if line.strip() and not line.startswith("#") and not line.startswith("---"):
                                    description = line.strip()[:200]
                                    break
                        except Exception:
                            pass

                        skills.append(
                            {
                                "name": skill_dir.name,
                                "description": description,
                                "location": location,
                                "path": str(skill_dir),
                                "installed": True,
                            },
                        )
                        seen_names.add(skill_dir.name)

        # Find built-in skills
        massgen_path = Path(massgen.__file__).parent
        add_skills_from_dir(massgen_path / "skills", "builtin")

        # Find user-installed skills (~/.agent/skills/ - where openskills/crawl4ai install)
        add_skills_from_dir(Path.home() / ".agent" / "skills", "user")

        # Find project skills (.agent/skills/ in current directory)
        add_skills_from_dir(Path.cwd() / ".agent" / "skills", "project")

        return {
            "skills": skills,
            "builtin_count": len([s for s in skills if s["location"] == "builtin"]),
            "user_count": len([s for s in skills if s["location"] == "user"]),
            "project_count": len([s for s in skills if s["location"] == "project"]),
        }

    @app.get("/api/skills/{skill_name}")
    async def get_skill_detail(skill_name: str):
        """Get detailed information about a skill including SKILL.md content."""
        from pathlib import Path

        import massgen

        # Search in built-in skills first
        massgen_path = Path(massgen.__file__).parent
        builtin_skill = massgen_path / "skills" / skill_name

        if builtin_skill.exists():
            skill_md = builtin_skill / "SKILL.md"
            content = skill_md.read_text() if skill_md.exists() else ""
            return {
                "name": skill_name,
                "location": "builtin",
                "path": str(builtin_skill),
                "content": content,
            }

        # Search in project skills
        project_skill = Path.cwd() / ".agent" / "skills" / skill_name
        if project_skill.exists():
            skill_md = project_skill / "SKILL.md"
            content = skill_md.read_text() if skill_md.exists() else ""
            return {
                "name": skill_name,
                "location": "project",
                "path": str(project_skill),
                "content": content,
            }

        return JSONResponse(
            {"error": f"Skill '{skill_name}' not found"},
            status_code=404,
        )

    @app.post("/api/skills/install")
    async def install_skill_package(request_data: dict):
        """Install a skill package (anthropic or crawl4ai).

        Request body:
        {
            "package": "anthropic" | "crawl4ai"
        }

        Returns:
            {"success": true, "message": "..."} or {"error": "..."}
        """
        from massgen.utils.skills_installer import (
            install_anthropic_skills,
            install_crawl4ai_skill,
            install_openskills_cli,
        )

        package_id = request_data.get("package")

        if package_id == "anthropic":
            # First ensure openskills CLI is installed
            if not install_openskills_cli():
                return JSONResponse(
                    {"error": "Failed to install openskills CLI. Ensure npm/Node.js is installed."},
                    status_code=500,
                )
            # Then install Anthropic skills
            if install_anthropic_skills():
                return {"success": True, "message": "Anthropic skills installed successfully"}
            else:
                return JSONResponse(
                    {"error": "Failed to install Anthropic skills"},
                    status_code=500,
                )

        elif package_id == "crawl4ai":
            if install_crawl4ai_skill():
                return {"success": True, "message": "Crawl4AI skill installed successfully"}
            else:
                return JSONResponse(
                    {"error": "Failed to install Crawl4AI skill"},
                    status_code=500,
                )

        else:
            return JSONResponse(
                {"error": f"Unknown package: {package_id}"},
                status_code=400,
            )

    @app.get("/api/providers")
    async def get_providers():
        """Get available providers with their models and API key status."""
        import os

        from massgen.backend.capabilities import BACKEND_CAPABILITIES

        providers = []
        for backend_type, caps in BACKEND_CAPABILITIES.items():
            # Skip generic/advanced backends for quickstart
            # Also skip ag2 as it's not a realistic standalone backend
            if backend_type in ["chatcompletion", "inference", "lmstudio", "vllm", "sglang", "ag2"]:
                continue

            # Check if API key is available (and not a placeholder)
            has_api_key = False
            if backend_type == "claude_code":
                # Claude Code always shows - works with CLI login, CLAUDE_CODE_API_KEY, or ANTHROPIC_API_KEY
                # Mark as available but the notes will explain auth requirements
                has_api_key = True
            elif caps.env_var:
                api_key = os.getenv(caps.env_var, "")
                # Check it's not empty and not a placeholder from .env.example
                # All placeholders follow pattern: your-*-key-here
                is_placeholder = api_key.lower().startswith("your-") and api_key.lower().endswith("-key-here")
                has_api_key = bool(api_key) and not is_placeholder
            else:
                # Local backends don't need keys
                has_api_key = True

            providers.append(
                {
                    "id": backend_type,
                    "name": caps.provider_name,
                    "models": caps.models,
                    "default_model": caps.default_model,
                    "env_var": caps.env_var,
                    "has_api_key": has_api_key,
                    "capabilities": list(caps.supported_capabilities),
                    "notes": caps.notes,
                },
            )

        # Sort by has_api_key (available first), then by name
        providers.sort(key=lambda p: (not p["has_api_key"], p["name"]))

        return {"providers": providers}

    @app.get("/api/providers/{provider_id}/models")
    async def get_provider_models(provider_id: str):
        """Get dynamic model list for a provider.

        For providers like OpenRouter that have many models, this fetches
        the full list from their API with caching.
        """
        from massgen.backend.capabilities import BACKEND_CAPABILITIES
        from massgen.utils.model_catalog import get_models_for_provider

        # Get static models from capabilities
        caps = BACKEND_CAPABILITIES.get(provider_id)
        static_models = caps.models if caps else []

        # For providers with dynamic model lists, fetch from API
        dynamic_providers = ["openrouter", "groq", "together", "fireworks", "cerebras", "nebius", "moonshot", "qwen", "poe"]

        if provider_id in dynamic_providers:
            try:
                dynamic_models = await get_models_for_provider(provider_id, use_cache=True)
                if dynamic_models:
                    return {
                        "provider_id": provider_id,
                        "models": dynamic_models,
                        "source": "dynamic",
                    }
            except Exception:
                pass  # Fall back to static models

        return {
            "provider_id": provider_id,
            "models": static_models,
            "source": "static",
        }

    @app.get("/api/providers/{provider_id}/capabilities")
    async def get_provider_capabilities(provider_id: str):
        """Get capabilities for a specific provider.

        Returns information about what features the provider supports,
        such as web search, code execution, etc.
        """
        from massgen.backend.capabilities import BACKEND_CAPABILITIES

        caps = BACKEND_CAPABILITIES.get(provider_id)
        if not caps:
            return JSONResponse(
                {"error": f"Unknown provider: {provider_id}"},
                status_code=404,
            )

        return {
            "provider_id": provider_id,
            "supports_web_search": "web_search" in caps.supported_capabilities,
            "supports_code_execution": "code_execution" in caps.supported_capabilities,
            "supports_mcp": "mcp" in caps.supported_capabilities,
            "builtin_tools": caps.builtin_tools,
            "filesystem_support": caps.filesystem_support,
            "all_capabilities": list(caps.supported_capabilities),
        }

    @app.post("/api/config/generate")
    async def generate_config(request_data: dict):
        """Generate a config YAML from wizard selections.

        Request body:
        {
            "agents": [
                {"id": "agent_a", "provider": "openai", "model": "gpt-4o", "enable_web_search": true},
                {"id": "agent_b", "provider": "claude", "model": "claude-sonnet-4-5-20250929", "enable_web_search": false}
            ],
            "use_docker": true,
            "context_path": "/path/to/project",  // optional
            "coordination": {  // optional
                "voting_sensitivity": "balanced",  // lenient, balanced, strict
                "answer_novelty_requirement": "lenient"  // lenient, balanced, strict
            }
        }

        Returns:
            {"config": {...}, "yaml": "..."}
        """
        import yaml

        from massgen.config_builder import ConfigBuilder

        agents_config = request_data.get("agents", [])
        use_docker = request_data.get("use_docker", True)
        context_path = request_data.get("context_path")
        coordination = request_data.get("coordination", {})

        if not agents_config:
            return JSONResponse(
                {"error": "At least one agent is required"},
                status_code=400,
            )

        # Convert to format expected by _generate_quickstart_config
        formatted_agents = []
        agent_tools = {}  # Per-agent tool settings
        agent_system_messages = {}  # Per-agent system messages
        for agent in agents_config:
            agent_id = agent.get("id", f"agent_{chr(ord('a') + len(formatted_agents))}")
            formatted_agents.append(
                {
                    "id": agent_id,
                    "type": agent.get("provider", "openai"),
                    "model": agent.get("model", "gpt-4o"),
                },
            )
            # Collect per-agent tool settings
            tool_settings = {}
            if agent.get("enable_web_search") is not None:
                tool_settings["enable_web_search"] = agent.get("enable_web_search")
            if agent.get("enable_code_execution") is not None:
                tool_settings["enable_code_execution"] = agent.get("enable_code_execution")
            if tool_settings:
                agent_tools[agent_id] = tool_settings
            # Collect per-agent system messages
            if agent.get("system_message"):
                agent_system_messages[agent_id] = agent.get("system_message")

        # Use ConfigBuilder to generate config
        builder = ConfigBuilder()
        config = builder._generate_quickstart_config(
            formatted_agents,
            context_path=context_path,
            use_docker=use_docker,
            agent_tools=agent_tools,
            agent_system_messages=agent_system_messages,
            coordination_settings=coordination,
        )

        # Convert to YAML string for preview
        yaml_str = yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True)

        return {"config": config, "yaml": yaml_str}

    @app.post("/api/config/save")
    async def save_config(request_data: dict):
        """Save the generated config to a file.

        Request body:
        {
            "config": {...},  // The config object from generate_config (optional if yaml_content provided)
            "yaml_content": "...",  // Raw YAML string (optional, takes priority if provided)
            "filename": "my_config.yaml"  // Optional custom filename (defaults to config.yaml)
        }

        Returns:
            {"success": true, "path": "..."}
        """
        import re
        from pathlib import Path

        import yaml

        config = request_data.get("config")
        yaml_content = request_data.get("yaml_content")

        if not config and not yaml_content:
            return JSONResponse(
                {"error": "No config or yaml_content provided"},
                status_code=400,
            )

        # Get custom filename or use default
        filename = request_data.get("filename", "config.yaml")
        # Sanitize filename - only allow alphanumeric, underscore, dash, and .yaml extension
        if not re.match(r"^[\w\-]+\.ya?ml$", filename):
            # If invalid, sanitize it
            base_name = re.sub(r"[^\w\-]", "_", filename.replace(".yaml", "").replace(".yml", ""))
            filename = f"{base_name}.yaml"

        # Save to user config location
        config_dir = Path.home() / ".config" / "massgen"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / filename

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                if yaml_content:
                    # Write raw YAML content (user edited)
                    f.write(yaml_content)
                else:
                    # Serialize config object to YAML
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

            return {
                "success": True,
                "path": str(config_path),
                "filename": filename,
                "message": f"Config saved to {config_path}",
            }
        except Exception as e:
            return JSONResponse(
                {"error": f"Failed to save config: {str(e)}"},
                status_code=500,
            )

    @app.get("/api/config/user-configs")
    async def list_user_configs():
        """List all user config files in ~/.config/massgen/.

        Returns:
            {"configs": [{"name": "config.yaml", "path": "...", "modified": timestamp}, ...]}
        """
        from pathlib import Path

        config_dir = Path.home() / ".config" / "massgen"
        configs = []

        if config_dir.exists():
            for yaml_file in config_dir.glob("*.yaml"):
                stat = yaml_file.stat()
                configs.append(
                    {
                        "name": yaml_file.name,
                        "path": str(yaml_file),
                        "modified": stat.st_mtime,
                        "size": stat.st_size,
                    },
                )
            for yml_file in config_dir.glob("*.yml"):
                stat = yml_file.stat()
                configs.append(
                    {
                        "name": yml_file.name,
                        "path": str(yml_file),
                        "modified": stat.st_mtime,
                        "size": stat.st_size,
                    },
                )

        # Sort by modification time (newest first)
        configs.sort(key=lambda x: x["modified"], reverse=True)

        return {"configs": configs, "config_dir": str(config_dir)}

    @app.put("/api/config/update")
    async def update_config(request_data: dict):
        """Update an existing config file with new content.

        Request body:
        {
            "path": "/path/to/config.yaml",  // Full path to the config file
            "content": "yaml content string"  // New YAML content
        }

        Returns:
            {"success": true, "path": "..."}
        """
        from pathlib import Path

        import yaml

        config_path = request_data.get("path")
        content = request_data.get("content")

        if not config_path:
            return JSONResponse(
                {"error": "No path provided"},
                status_code=400,
            )

        if content is None:
            return JSONResponse(
                {"error": "No content provided"},
                status_code=400,
            )

        config_path = Path(config_path).resolve()

        # Security: ensure path is within allowed locations
        allowed_paths = [
            Path.home() / ".config" / "massgen",
        ]
        is_allowed = any(str(config_path).startswith(str(allowed.resolve())) for allowed in allowed_paths)
        if not is_allowed:
            return JSONResponse(
                {"error": "Access denied: can only edit configs in ~/.config/massgen/"},
                status_code=403,
            )

        # Validate YAML syntax before saving
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            return JSONResponse(
                {"error": f"Invalid YAML syntax: {str(e)}"},
                status_code=400,
            )

        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(content)

            return {
                "success": True,
                "path": str(config_path),
                "message": f"Config updated: {config_path}",
            }
        except Exception as e:
            return JSONResponse(
                {"error": f"Failed to save config: {str(e)}"},
                status_code=500,
            )

    @app.post("/api/config/rename")
    async def rename_config(request_data: dict):
        """Rename a config file.

        Request body:
        {
            "path": "/path/to/old_config.yaml",
            "new_name": "new_config.yaml"
        }

        Returns:
            {"success": true, "old_path": "...", "new_path": "..."}
        """
        import re
        from pathlib import Path

        old_path = request_data.get("path")
        new_name = request_data.get("new_name")

        if not old_path:
            return JSONResponse(
                {"error": "No path provided"},
                status_code=400,
            )

        if not new_name:
            return JSONResponse(
                {"error": "No new name provided"},
                status_code=400,
            )

        old_path = Path(old_path).resolve()

        # Security: ensure path is within allowed locations
        allowed_paths = [
            Path.home() / ".config" / "massgen",
        ]
        is_allowed = any(str(old_path).startswith(str(allowed.resolve())) for allowed in allowed_paths)
        if not is_allowed:
            return JSONResponse(
                {"error": "Access denied: can only rename configs in ~/.config/massgen/"},
                status_code=403,
            )

        if not old_path.exists():
            return JSONResponse(
                {"error": "Config file not found"},
                status_code=404,
            )

        # Sanitize new filename
        if not re.match(r"^[\w\-]+\.ya?ml$", new_name):
            base_name = re.sub(r"[^\w\-]", "_", new_name.replace(".yaml", "").replace(".yml", ""))
            new_name = f"{base_name}.yaml"

        new_path = old_path.parent / new_name

        if new_path.exists():
            return JSONResponse(
                {"error": f"A config with name '{new_name}' already exists"},
                status_code=409,
            )

        try:
            old_path.rename(new_path)
            return {
                "success": True,
                "old_path": str(old_path),
                "new_path": str(new_path),
                "new_name": new_name,
                "message": f"Config renamed to {new_name}",
            }
        except Exception as e:
            return JSONResponse(
                {"error": f"Failed to rename config: {str(e)}"},
                status_code=500,
            )

    @app.delete("/api/config/delete")
    async def delete_config(path: str):
        """Delete a config file.

        Query params:
            path: Full path to the config file to delete

        Returns:
            {"success": true, "path": "..."}
        """
        from pathlib import Path

        if not path:
            return JSONResponse(
                {"error": "No path provided"},
                status_code=400,
            )

        config_path = Path(path).resolve()

        # Security: ensure path is within allowed locations
        allowed_paths = [
            Path.home() / ".config" / "massgen",
        ]
        is_allowed = any(str(config_path).startswith(str(allowed.resolve())) for allowed in allowed_paths)
        if not is_allowed:
            return JSONResponse(
                {"error": "Access denied: can only delete configs in ~/.config/massgen/"},
                status_code=403,
            )

        if not config_path.exists():
            return JSONResponse(
                {"error": "Config file not found"},
                status_code=404,
            )

        # Don't allow deleting the last config
        config_dir = Path.home() / ".config" / "massgen"
        yaml_files = list(config_dir.glob("*.yaml")) + list(config_dir.glob("*.yml"))
        if len(yaml_files) <= 1:
            return JSONResponse(
                {"error": "Cannot delete the last config file"},
                status_code=400,
            )

        try:
            config_path.unlink()
            return {
                "success": True,
                "path": str(config_path),
                "message": f"Config deleted: {config_path.name}",
            }
        except Exception as e:
            return JSONResponse(
                {"error": f"Failed to delete config: {str(e)}"},
                status_code=500,
            )

    @app.get("/api/sessions")
    async def list_sessions():
        """List all active and completed sessions."""
        sessions = []
        # Active sessions (with WebSocket connections)
        for session_id in manager.active_connections.keys():
            display = manager.get_display(session_id)
            task = manager.tasks.get(session_id)

            sessions.append(
                {
                    "session_id": session_id,
                    "connections": len(manager.active_connections.get(session_id, set())),
                    "has_display": display is not None,
                    "is_running": task is not None and not task.done() if task else False,
                    "question": display.question if display and hasattr(display, "question") else None,
                    "status": "active",
                },
            )

        # Completed sessions (no longer connected but preserved)
        for session_id, metadata in manager.completed_sessions.items():
            # Skip if already in active list
            if session_id in manager.active_connections:
                continue
            sessions.append(
                {
                    "session_id": session_id,
                    "connections": 0,
                    "has_display": False,
                    "is_running": False,
                    "question": metadata.get("question"),
                    "status": "completed",
                    "completed_at": metadata.get("completed_at"),
                },
            )

        return {"sessions": sessions}

    @app.post("/api/sessions")
    async def create_session():
        """Create a new coordination session."""
        session_id = str(uuid.uuid4())
        return JSONResponse({"session_id": session_id})

    @app.get("/api/workspace/{session_id}/{agent_id}")
    async def get_workspace_files(session_id: str, agent_id: str):
        """Get workspace files for an agent.

        Returns files from the agent's current workspace directory.
        """
        display = manager.get_display(session_id)
        if display is None:
            return JSONResponse(
                {"error": "Session not found", "files": []},
                status_code=404,
            )

        # Get workspace path from display if available
        workspace_path = getattr(display, "_workspace_path", None)
        if workspace_path:
            agent_workspace = Path(workspace_path) / agent_id
        else:
            # Fall back to default workspace pattern
            agent_workspace = Path.cwd() / f"workspace_{agent_id}"

        files = []
        if agent_workspace.exists():
            try:
                for file_path in agent_workspace.rglob("*"):
                    if file_path.is_file():
                        rel_path = file_path.relative_to(agent_workspace)
                        stat = file_path.stat()
                        files.append(
                            {
                                "path": str(rel_path),
                                "size": stat.st_size,
                                "modified": stat.st_mtime,
                                "operation": "create",  # For compatibility
                            },
                        )
            except Exception as e:
                return JSONResponse(
                    {"error": str(e), "files": []},
                    status_code=500,
                )

        return {"files": files, "workspace_path": str(agent_workspace)}

    @app.get("/api/workspaces")
    async def list_workspaces():
        """List all available workspaces including current and historical.

        Returns:
        - current: Workspaces in cwd (workspace1, workspace2, etc.)
        - historical: Dated workspaces from logs directory
        """
        workspaces = {
            "current": [],
            "historical": [],
        }

        # Find current workspaces in cwd
        cwd = Path.cwd()
        for path in cwd.iterdir():
            if path.is_dir() and path.name.startswith("workspace"):
                workspaces["current"].append(
                    {
                        "name": path.name,
                        "path": str(path),
                        "type": "current",
                    },
                )

        # Find historical workspaces in logs directory
        logs_dir = cwd / "logs"
        if logs_dir.exists():
            for date_dir in sorted(logs_dir.iterdir(), reverse=True):
                if date_dir.is_dir():
                    # Look for workspace directories within dated logs
                    for ws_dir in date_dir.iterdir():
                        if ws_dir.is_dir() and "workspace" in ws_dir.name.lower():
                            workspaces["historical"].append(
                                {
                                    "name": f"{date_dir.name}/{ws_dir.name}",
                                    "path": str(ws_dir),
                                    "type": "historical",
                                    "date": date_dir.name,
                                },
                            )

        return workspaces

    @app.get("/api/workspace/browse")
    async def browse_workspace(path: str):
        """Browse files in a specific workspace path.

        Args:
            path: Absolute path to workspace directory
        """
        workspace_path = Path(path)

        if not workspace_path.exists():
            return JSONResponse(
                {"error": "Workspace not found", "files": []},
                status_code=404,
            )

        if not workspace_path.is_dir():
            return JSONResponse(
                {"error": "Path is not a directory", "files": []},
                status_code=400,
            )

        files = []
        try:
            for file_path in workspace_path.rglob("*"):
                if file_path.is_file():
                    rel_path = file_path.relative_to(workspace_path)
                    stat = file_path.stat()
                    files.append(
                        {
                            "path": str(rel_path),
                            "size": stat.st_size,
                            "modified": stat.st_mtime,
                            "operation": "create",
                        },
                    )
        except Exception as e:
            return JSONResponse(
                {"error": str(e), "files": []},
                status_code=500,
            )

        return {"files": files, "workspace_path": str(workspace_path)}

    @app.get("/api/sessions/{session_id}/answer-workspaces")
    async def get_answer_workspaces(session_id: str):
        """Get workspaces linked to specific answer versions.

        Uses snapshot_mappings.json from log directory if available,
        otherwise scans the log directory structure.
        """
        import json

        from massgen.logger_config import get_log_session_dir

        display = manager.get_display(session_id)
        agent_ids = display.agent_ids if display else []

        workspaces = []
        log_session_dir = get_log_session_dir()

        if not log_session_dir or not log_session_dir.exists():
            return {"workspaces": [], "current": []}

        # Try to use snapshot_mappings.json for accurate workspace info
        snapshot_mappings_file = log_session_dir / "snapshot_mappings.json"
        if snapshot_mappings_file.exists():
            try:
                with open(snapshot_mappings_file) as f:
                    snapshot_mappings = json.load(f)

                for label, mapping in snapshot_mappings.items():
                    # Only include answers (not votes or final)
                    if mapping.get("type") != "answer":
                        continue

                    agent_id = mapping.get("agent_id", "")
                    timestamp = mapping.get("timestamp", "")

                    # Build workspace path from mapping
                    workspace_path = log_session_dir / agent_id / timestamp / "workspace"
                    if workspace_path.exists():
                        workspaces.append(
                            {
                                "answerId": f"{agent_id}-{timestamp}",
                                "agentId": agent_id,
                                "answerNumber": mapping.get("round", 1),
                                "answerLabel": label,  # Use the canonical label from mappings
                                "timestamp": timestamp,
                                "workspacePath": str(workspace_path),
                            },
                        )
            except Exception as e:
                print(f"[WARNING] Failed to load snapshot_mappings.json: {e}")
                # Fall through to directory scanning

        # Fallback: Scan log directory structure if no mappings found
        if not workspaces:
            for entry in log_session_dir.iterdir():
                if not entry.is_dir():
                    continue

                # Check for turn directories (turn_1, turn_2, etc.)
                if entry.name.startswith("turn_"):
                    for agent_dir in entry.iterdir():
                        if not agent_dir.is_dir():
                            continue
                        agent_id = agent_dir.name
                        agent_index = (agent_ids.index(agent_id) + 1) if agent_id in agent_ids else 0

                        # Find timestamp directories with workspaces
                        answer_count = 0
                        for ts_dir in sorted(agent_dir.iterdir(), key=lambda x: x.name):
                            if ts_dir.is_dir() and (ts_dir / "workspace").exists():
                                answer_count += 1
                                workspaces.append(
                                    {
                                        "answerId": f"{agent_id}-{ts_dir.name}",
                                        "agentId": agent_id,
                                        "answerNumber": answer_count,
                                        "answerLabel": f"agent{agent_index}.{answer_count}",
                                        "timestamp": ts_dir.name,
                                        "workspacePath": str(ts_dir / "workspace"),
                                    },
                                )

        # Also include current workspaces from cwd
        cwd = Path.cwd()
        current = []
        for path in cwd.iterdir():
            if path.is_dir() and path.name.startswith("workspace"):
                current.append(
                    {
                        "name": path.name,
                        "path": str(path),
                        "type": "current",
                    },
                )

        return {"workspaces": workspaces, "current": current}

    @app.get("/api/workspace/file")
    async def get_file_content(path: str, workspace: str):
        """Get the content of a specific file from a workspace.

        Args:
            path: Relative path to file within workspace
            workspace: Absolute path to workspace directory

        Returns:
            {
                "content": str,           # File content (text files)
                "binary": bool,           # True if binary file
                "size": int,              # File size in bytes
                "mimeType": str,          # Detected MIME type
                "language": str,          # Programming language for syntax highlighting
            }
        """
        import mimetypes

        workspace_path = Path(workspace).resolve()
        file_path = (workspace_path / path).resolve()

        # Security: Ensure file is within workspace (prevent directory traversal)
        try:
            file_path.relative_to(workspace_path)
        except ValueError:
            return JSONResponse(
                {"error": "Access denied: path outside workspace"},
                status_code=403,
            )

        if not file_path.exists():
            return JSONResponse(
                {"error": "File not found"},
                status_code=404,
            )

        if not file_path.is_file():
            return JSONResponse(
                {"error": "Path is not a file"},
                status_code=400,
            )

        # Get file stats
        stat = file_path.stat()
        size = stat.st_size

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        mime_type = mime_type or "application/octet-stream"

        # Map extensions to syntax highlighting languages
        extension_to_language = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".html": "html",
            ".htm": "html",
            ".css": "css",
            ".scss": "scss",
            ".less": "less",
            ".sh": "bash",
            ".bash": "bash",
            ".zsh": "bash",
            ".sql": "sql",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".hpp": "cpp",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".r": "r",
            ".R": "r",
            ".lua": "lua",
            ".pl": "perl",
            ".xml": "xml",
            ".toml": "toml",
            ".ini": "ini",
            ".cfg": "ini",
            ".conf": "ini",
            ".dockerfile": "dockerfile",
            ".gitignore": "gitignore",
            ".env": "dotenv",
            ".txt": "plaintext",
            ".log": "plaintext",
        }

        suffix = file_path.suffix.lower()
        language = extension_to_language.get(suffix, "plaintext")

        # Special case for Dockerfile without extension
        if file_path.name.lower() == "dockerfile":
            language = "dockerfile"

        # Check if binary by reading first chunk
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(8192)

            # Check for null bytes (binary indicator)
            is_binary = b"\x00" in chunk

            if is_binary:
                return {
                    "content": "",
                    "binary": True,
                    "size": size,
                    "mimeType": mime_type,
                    "language": language,
                }

            # Read full content for text files (limit to 1MB)
            max_size = 1024 * 1024  # 1MB
            if size > max_size:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read(max_size)
                content += f"\n\n... (truncated, file is {size} bytes)"
            else:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()

            return {
                "content": content,
                "binary": False,
                "size": size,
                "mimeType": mime_type,
                "language": language,
            }

        except Exception as e:
            return JSONResponse(
                {"error": f"Failed to read file: {str(e)}"},
                status_code=500,
            )

    @app.get("/api/sessions/{session_id}/timeline")
    async def get_session_timeline(session_id: str):
        """Get coordination timeline data for visualization.

        Returns timeline nodes representing answers, votes, and final answer
        with their context sources (which answers they saw).
        """
        display = manager.get_display(session_id)
        if display is None:
            return JSONResponse(
                {"error": "Session not found"},
                status_code=404,
            )

        # Get agents from display
        agent_ids = display.agent_ids if display else []

        # Build timeline from display's tracked events
        nodes = []

        # Get timeline data from display if available
        timeline_events = getattr(display, "_timeline_events", [])

        for event in timeline_events:
            node = {
                "id": event.get("id", ""),
                "type": event.get("type", "answer"),
                "agentId": event.get("agent_id", ""),
                "label": event.get("label", ""),
                "timestamp": event.get("timestamp", 0),
                "round": event.get("round", 1),
                "contextSources": event.get("context_sources", []),
                "votedFor": event.get("voted_for"),
            }
            nodes.append(node)

        # Timeline nodes are only populated from explicitly recorded events
        # (record_answer_with_context, record_vote_with_context, record_final_with_context)
        # No fallback reconstruction - prevents phantom nodes from appearing before
        # agents have actually submitted answers

        # Sort by timestamp
        nodes.sort(key=lambda x: x.get("timestamp", 0))

        # Calculate start/end times
        timestamps = [n.get("timestamp", 0) for n in nodes if n.get("timestamp")]
        start_time = min(timestamps) if timestamps else 0
        end_time = max(timestamps) if timestamps else None

        return {
            "nodes": nodes,
            "agents": agent_ids,
            "startTime": start_time,
            "endTime": end_time,
        }

    @app.get("/api/sessions/{session_id}")
    async def get_session(session_id: str):
        """Get current state of a session."""
        display = manager.get_display(session_id)
        if display is None:
            return JSONResponse(
                {"error": "Session not found"},
                status_code=404,
            )
        return JSONResponse(display.get_state_snapshot())

    @app.get("/api/sessions/{session_id}/final-answer")
    async def get_final_answer(session_id: str):
        """Get the clean final answer from the saved log file.

        The final answer is saved to:
        .massgen/massgen_logs/log_<timestamp>/turn_<N>/final/<agent_id>/answer.txt

        This returns the clean answer without any tool call noise.
        """
        # Get the log session dir from the display (stored after coordination completes)
        display = manager.get_display(session_id)
        log_session_dir = getattr(display, "log_session_dir", None) if display else None

        print(f"[DEBUG] get_final_answer: session_id={session_id}")
        print(f"[DEBUG] get_final_answer: display={display}")
        print(f"[DEBUG] get_final_answer: log_session_dir from display={log_session_dir}")

        # Fallback to global log session dir if display doesn't have it
        if not log_session_dir:
            from massgen.logger_config import get_log_session_dir

            log_session_dir = get_log_session_dir()
            print(f"[DEBUG] get_final_answer: log_session_dir from global={log_session_dir}")

        if not log_session_dir or not log_session_dir.exists():
            print("[DEBUG] get_final_answer: log_session_dir not found or doesn't exist")
            return JSONResponse(
                {"error": "Log directory not found", "answer": None},
                status_code=404,
            )

        # log_session_dir could be:
        # - .massgen/massgen_logs/log_xxx/turn_1 (old structure)
        # - .massgen/massgen_logs/log_xxx/turn_1/attempt_N (new structure with attempts)
        # We need to search for final/<agent>/answer.txt in multiple possible locations

        # Helper to find answer in a final directory
        def find_answer_in_final_dir(final_dir):
            if not final_dir.exists():
                return None
            for agent_dir in final_dir.iterdir():
                if not agent_dir.is_dir():
                    continue
                answer_file = agent_dir / "answer.txt"
                print(f"[DEBUG] get_final_answer: Checking answer_file={answer_file}")
                if answer_file.exists():
                    try:
                        answer_content = answer_file.read_text(encoding="utf-8")
                        print(f"[DEBUG] get_final_answer: Found answer! Length={len(answer_content)}")
                        return {
                            "answer": answer_content,
                            "agent_id": agent_dir.name,
                            "path": str(answer_file),
                        }
                    except Exception as e:
                        return {"error": f"Failed to read answer: {str(e)}"}
            return None

        # Try 1: Direct final/ directory (log_session_dir/final)
        final_dir = log_session_dir / "final"
        print(f"[DEBUG] get_final_answer: Looking for final_dir={final_dir}")
        result = find_answer_in_final_dir(final_dir)
        if result:
            if "error" in result:
                return JSONResponse({"error": result["error"], "answer": None}, status_code=500)
            return result

        # Try 2: Check for attempt_N subdirectories (log_session_dir/attempt_N/final)
        print("[DEBUG] get_final_answer: Checking attempt subdirectories")
        for attempt_dir in sorted(log_session_dir.iterdir(), reverse=True):
            if not attempt_dir.is_dir() or not attempt_dir.name.startswith("attempt_"):
                continue
            print(f"[DEBUG] get_final_answer: Checking attempt dir: {attempt_dir}")
            final_dir = attempt_dir / "final"
            result = find_answer_in_final_dir(final_dir)
            if result:
                if "error" in result:
                    return JSONResponse({"error": result["error"], "answer": None}, status_code=500)
                return result

        # Fallback: search in turn subdirectories (for older log structure or if log_session_dir is base)
        print("[DEBUG] get_final_answer: No final dir, searching turn subdirs")
        for turn_dir in sorted(log_session_dir.iterdir(), reverse=True):
            if not turn_dir.is_dir() or not turn_dir.name.startswith("turn_"):
                continue

            # Check direct final/ in turn dir
            result = find_answer_in_final_dir(turn_dir / "final")
            if result:
                if "error" in result:
                    return JSONResponse({"error": result["error"], "answer": None}, status_code=500)
                return result

            # Check attempt_N subdirectories within turn dir
            for attempt_dir in sorted(turn_dir.iterdir(), reverse=True):
                if not attempt_dir.is_dir() or not attempt_dir.name.startswith("attempt_"):
                    continue
                result = find_answer_in_final_dir(attempt_dir / "final")
                if result:
                    if "error" in result:
                        return JSONResponse({"error": result["error"], "answer": None}, status_code=500)
                    return result

        return JSONResponse(
            {"error": "Final answer not found", "answer": None},
            status_code=404,
        )

    @app.post("/api/sessions/{session_id}/start")
    async def start_coordination(session_id: str, request: dict):
        """Start coordination for a session."""
        question = request.get("question", "")
        # Use provided config or fall back to default
        cfg_path = request.get("config") or get_default_config()

        if not question:
            return JSONResponse(
                {"error": "Question is required"},
                status_code=400,
            )

        if not cfg_path:
            return JSONResponse(
                {"error": "No config specified. Use --config flag or provide in request."},
                status_code=400,
            )

        # Start orchestration in background
        task = asyncio.create_task(
            run_coordination(session_id, question, cfg_path),
        )
        manager.tasks[session_id] = task

        return JSONResponse(
            {
                "status": "started",
                "session_id": session_id,
                "config": cfg_path,
            },
        )

    # =========================================================================
    # WebSocket Endpoint
    # =========================================================================

    @app.websocket("/ws/{session_id}")
    async def websocket_endpoint(websocket: WebSocket, session_id: str):
        """WebSocket endpoint for real-time coordination updates."""
        await manager.connect(websocket, session_id)

        try:
            # Send current state if session exists
            display = manager.get_display(session_id)
            if display:
                await websocket.send_json(
                    {
                        "type": "state_snapshot",
                        "automation_mode": app.state.automation_mode,
                        **display.get_state_snapshot(),
                    },
                )
            else:
                # Send init message with automation_mode even without display
                await websocket.send_json(
                    {
                        "type": "init",
                        "automation_mode": app.state.automation_mode,
                        "session_id": session_id,
                    },
                )

            # Handle incoming messages
            while True:
                data = await websocket.receive_json()
                action = data.get("action")

                if action == "start":
                    # Start new coordination
                    question = data.get("question", "")
                    # Use provided config or fall back to default
                    cfg_path = data.get("config") or get_default_config()

                    if not cfg_path:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "message": "No config specified. Start server with --config flag.",
                            },
                        )
                        continue

                    if question:
                        # Send immediate acknowledgment that we received the prompt
                        await websocket.send_json(
                            {
                                "type": "preparation_status",
                                "status": "Received prompt...",
                                "detail": "Preparing to start coordination",
                                "session_id": session_id,
                            },
                        )

                        task = asyncio.create_task(
                            run_coordination(session_id, question, cfg_path),
                        )
                        manager.tasks[session_id] = task
                        await websocket.send_json(
                            {
                                "type": "coordination_started",
                                "session_id": session_id,
                                "config": cfg_path,
                            },
                        )

                elif action == "get_state":
                    # Request current state
                    display = manager.get_display(session_id)
                    if display:
                        await websocket.send_json(
                            {
                                "type": "state_snapshot",
                                **display.get_state_snapshot(),
                            },
                        )

                elif action == "broadcast_response":
                    # Human response to a broadcast question
                    # TODO: Integrate with BroadcastChannel
                    pass

                elif action == "continue":
                    # Continue conversation with follow-up question
                    followup_question = data.get("question", "")
                    if not followup_question:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "message": "Question is required for continuation",
                            },
                        )
                        continue

                    # Get session info from previous turn
                    session_log_dir = manager.session_log_dirs.get(session_id)
                    current_turn = manager.session_turns.get(session_id, 0)
                    cfg_path = manager.session_configs.get(session_id) or get_default_config()

                    if not session_log_dir:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "message": "No active session to continue. Start a new coordination first.",
                            },
                        )
                        continue

                    if not cfg_path:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "message": "No config available for continuation.",
                            },
                        )
                        continue

                    # Start continuation coordination
                    next_turn = current_turn + 1
                    task = asyncio.create_task(
                        run_coordination_with_history(
                            session_id=session_id,
                            question=followup_question,
                            config_path=cfg_path,
                            session_log_dir=session_log_dir,
                            turn_number=next_turn,
                        ),
                    )
                    manager.tasks[session_id] = task
                    await websocket.send_json(
                        {
                            "type": "coordination_started",
                            "session_id": session_id,
                            "config": cfg_path,
                            "turn": next_turn,
                            "is_continuation": True,
                        },
                    )

        except WebSocketDisconnect:
            manager.disconnect(websocket, session_id)
        except Exception as e:
            # Send error and disconnect
            try:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": str(e),
                    },
                )
            except Exception:
                pass
            manager.disconnect(websocket, session_id)

    # =========================================================================
    # Static File Serving (React build)
    # =========================================================================

    # Path to React build directory (packaged with massgen)
    static_dir = Path(__file__).parent / "static"

    if static_dir.exists():
        # Serve static files from React build
        app.mount(
            "/assets",
            StaticFiles(directory=static_dir / "assets"),
            name="assets",
        )

        @app.get("/")
        async def serve_index():
            """Serve React app index.html."""
            return FileResponse(static_dir / "index.html")

        @app.get("/{path:path}")
        async def serve_spa(path: str):
            """Serve React SPA - route all paths to index.html.

            Note: API routes (/api/*) are handled by the routes defined above.
            This catch-all only handles frontend routes.
            """
            # Don't serve SPA for API routes - they should 404 if not found
            if path.startswith("api/"):
                return JSONResponse(
                    {"error": "API endpoint not found", "path": path},
                    status_code=404,
                )

            file_path = static_dir / path
            if file_path.exists() and file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(static_dir / "index.html")

    return app


async def _save_session_metadata(
    session_id: str,
    question: str,
    orchestrator: Any,
    config_path: str,
    log_session_dir: Optional[Path],
    turn_number: int = 1,
) -> None:
    """Save CLI-compatible metadata for multi-turn session continuation.

    This creates the same metadata structure as the CLI's save_final_state(),
    enabling sessions started in WebUI to be continued with `--continue`.

    Args:
        session_id: WebSocket session identifier
        question: The question/task that was asked
        orchestrator: The orchestrator instance (to get winning agent info)
        config_path: Path to the config file used
        log_session_dir: The log session directory (may include attempt subdirectory)
        turn_number: Current turn number (default 1 for first turn)
    """
    import json
    from datetime import datetime

    from massgen.logger_config import get_log_session_dir_base, get_log_session_root

    if not log_session_dir or not log_session_dir.exists():
        print("[WebUI] Warning: log_session_dir not available, skipping metadata save")
        return

    try:
        # Get orchestrator status for winning agent info
        status = orchestrator.get_status()
        winning_agent = status.get("selected_agent", "unknown")

        # Get the final answer
        final_answer = ""
        if hasattr(orchestrator, "_final_presentation_content") and orchestrator._final_presentation_content:
            final_answer = orchestrator._final_presentation_content.strip()
        elif winning_agent and hasattr(orchestrator, "agent_states") and winning_agent in orchestrator.agent_states:
            stored_answer = orchestrator.agent_states[winning_agent].answer
            if stored_answer:
                final_answer = stored_answer.strip()

        # Get the turn directory (without attempt subdirectory)
        # log_session_dir may be log_xxx/turn_Y/attempt_1/ but we need log_xxx/turn_Y/
        turn_dir = get_log_session_dir_base()
        session_dir = get_log_session_root()

        print(f"[WebUI] Saving metadata: turn_dir={turn_dir}, session_dir={session_dir}")

        # Save metadata.json at turn level (CLI-compatible format)
        metadata = {
            "turn": turn_number,
            "timestamp": datetime.now().isoformat(),
            "winning_agent": winning_agent,
            "task": question,
            "session_id": session_dir.name,  # Use log dir name as session ID (e.g., log_xxx)
        }
        metadata_file = turn_dir / "metadata.json"
        metadata_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        # Save answer.txt at turn level (CLI-compatible format)
        # Note: final/{agent}/answer.txt already exists, but CLI expects answer.txt at turn level too
        answer_file = turn_dir / "answer.txt"
        answer_file.write_text(final_answer, encoding="utf-8")

        # Save winning_agents_history.json at session level (for multi-turn memory sharing)
        winning_agents_history = []

        # Load existing history if present
        history_file = session_dir / "winning_agents_history.json"
        if history_file.exists():
            try:
                winning_agents_history = json.loads(history_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                pass

        # Add current turn's winner
        winning_agents_history.append(
            {
                "agent_id": winning_agent,
                "turn": turn_number,
                "timestamp": datetime.now().isoformat(),
            },
        )
        history_file.write_text(json.dumps(winning_agents_history, indent=2), encoding="utf-8")

        # Register session with SessionRegistry for `massgen --list-sessions` compatibility
        try:
            from massgen.session import SessionRegistry

            registry = SessionRegistry()
            # Use the log directory name as session_id (e.g., "log_20251130_211636_581944")
            massgen_session_id = session_dir.name
            registry.register_session(
                session_id=massgen_session_id,
                log_directory=str(session_dir),
                config_path=config_path,
            )
            print(f"[WebUI] Registered session: {massgen_session_id}")
        except Exception as e:
            print(f"[WebUI] Warning: Could not register session: {e}")

        # Store session info in ConnectionManager for continuation
        manager.session_log_dirs[session_id] = session_dir
        manager.session_turns[session_id] = turn_number
        manager.session_configs[session_id] = config_path

        print(f"[WebUI] Saved session metadata: turn={turn_number}, winner={winning_agent}")

    except Exception as e:
        print(f"[WebUI] Error saving session metadata: {e}")
        import traceback

        traceback.print_exc()


async def run_coordination_with_history(
    session_id: str,
    question: str,
    config_path: str,
    session_log_dir: Path,
    turn_number: int,
) -> None:
    """Run coordination with conversation history from previous turns.

    This is similar to `run_coordination()` but:
    1. Restores previous turn data using `restore_session()`
    2. Passes `previous_turns` and `winning_agents_history` to Orchestrator
    3. Sets the correct turn number in logger

    Args:
        session_id: WebSocket session identifier
        question: The follow-up question
        config_path: Path to the config file
        session_log_dir: Path to the session log directory (e.g., .massgen/massgen_logs/log_xxx)
        turn_number: The turn number for this coordination (2, 3, etc.)
    """
    import traceback

    try:
        # Import here to avoid circular imports
        from massgen.agent_config import AgentConfig, CoordinationConfig
        from massgen.cli import (
            create_agents_from_config,
            load_config_file,
            resolve_config_path,
        )
        from massgen.frontend.coordination_ui import CoordinationUI
        from massgen.logger_config import (
            get_log_session_dir,
            set_log_base_session_dir,
            set_log_turn,
        )
        from massgen.orchestrator import Orchestrator

        # IMPORTANT: Set the base session dir to reuse the existing session log directory
        # This must happen before set_log_turn() or get_log_session_dir() is called
        set_log_base_session_dir(session_log_dir.name)  # e.g., "log_20251202_235530_074788"

        # Restore session state from previous turns
        previous_turns = []
        winning_agents_history = []
        conversation_history = []  # For multi-turn context passing to agents

        try:
            from massgen.session import restore_session

            # The session_log_dir is the base log dir (e.g., .massgen/massgen_logs/log_xxx)
            # We need to tell restore_session to look in the massgen_logs directory
            print(f"[WebUI] Attempting to restore session: session_log_dir={session_log_dir}")
            print(f"[WebUI] session_log_dir.name={session_log_dir.name}, parent={session_log_dir.parent}")
            session_state = restore_session(
                session_log_dir.name,  # e.g., "log_20251130_211636_581944"
                session_storage=str(session_log_dir.parent),  # e.g., ".massgen/massgen_logs"
            )
            if session_state:
                previous_turns = session_state.previous_turns
                winning_agents_history = session_state.winning_agents_history
                conversation_history = session_state.conversation_history or []
                print(f"[WebUI] Restored {len(previous_turns)} previous turns, {len(winning_agents_history)} winners, {len(conversation_history)} history messages")
                if conversation_history:
                    print(f"[WebUI] Conversation history preview: {conversation_history[0] if conversation_history else 'empty'}")
            else:
                print(f"[WebUI] restore_session returned None for {session_log_dir.name}")
        except Exception as e:
            print(f"[WebUI] ERROR restoring session state: {e}")
            traceback.print_exc()
            # Continue anyway - first follow-up might work without full history

        # Set the turn number for logging
        set_log_turn(turn_number)

        # Resolve config path
        resolved_path = resolve_config_path(config_path)
        if resolved_path is None:
            raise ValueError(f"Could not resolve config path: {config_path}")

        config = load_config_file(str(resolved_path))

        # Extract orchestrator config dict from YAML
        orchestrator_cfg = config.get("orchestrator", {})

        # Create agents from config with progress updates
        # Note: Multi-turn reuses existing session, so progress is less critical but nice to have
        num_agents = len(config.get("agents", []))

        # Create progress callback that sends WebSocket updates
        loop = asyncio.get_running_loop()

        async def emit_preparation_status(status: str, detail: str = "") -> None:
            """Emit preparation status update to web clients."""
            await manager.broadcast(
                session_id,
                {
                    "type": "preparation_status",
                    "status": status,
                    "detail": detail,
                    "session_id": session_id,
                },
            )

        await emit_preparation_status("Initializing agents...", f"{num_agents} agent{'s' if num_agents != 1 else ''}")

        def progress_callback(status: str, detail: str) -> None:
            """Thread-safe callback to queue progress updates."""
            asyncio.run_coroutine_threadsafe(
                emit_preparation_status(status, detail),
                loop,
            )

        # Run agent creation in thread pool so progress updates can be sent
        agents = await loop.run_in_executor(
            None,
            lambda: create_agents_from_config(
                config,
                orchestrator_config=orchestrator_cfg,
                config_path=str(resolved_path),
                memory_session_id=session_id,
                progress_callback=progress_callback,
            ),
        )

        # Get agent IDs and model names
        agent_ids = list(agents.keys())
        agent_models = {}
        for agent_id, agent in agents.items():
            # Try to get model name from agent - check multiple sources
            model_name = getattr(agent, "model", None)
            # For ConfigurableAgent, model is in config.backend_params["model"]
            if not model_name and hasattr(agent, "config") and agent.config:
                backend_params = getattr(agent.config, "backend_params", None)
                if backend_params:
                    model_name = backend_params.get("model")
            if model_name:
                agent_models[agent_id] = model_name

        # Create web display with agent_models
        display = manager.create_display(session_id, agent_ids, agent_models)

        # Build AgentConfig object for orchestrator
        orchestrator_config = AgentConfig()

        # Apply voting sensitivity if specified
        if "voting_sensitivity" in orchestrator_cfg:
            orchestrator_config.voting_sensitivity = orchestrator_cfg["voting_sensitivity"]

        # Apply answer count limit if specified
        if "max_new_answers_per_agent" in orchestrator_cfg:
            orchestrator_config.max_new_answers_per_agent = orchestrator_cfg["max_new_answers_per_agent"]

        # Apply answer novelty requirement if specified
        if "answer_novelty_requirement" in orchestrator_cfg:
            orchestrator_config.answer_novelty_requirement = orchestrator_cfg["answer_novelty_requirement"]

        # Apply coordination config from YAML (includes enable_agent_task_planning, etc.)
        coord_cfg = orchestrator_cfg.get("coordination", {})
        if coord_cfg:
            orchestrator_config.coordination_config = CoordinationConfig(
                enable_planning_mode=coord_cfg.get("enable_planning_mode", False),
                planning_mode_instruction=coord_cfg.get(
                    "planning_mode_instruction",
                    "During coordination, describe what you would do without actually executing actions.",
                ),
                max_orchestration_restarts=coord_cfg.get("max_orchestration_restarts", 0),
                enable_agent_task_planning=coord_cfg.get("enable_agent_task_planning", False),
                max_tasks_per_plan=coord_cfg.get("max_tasks_per_plan", 10),
                broadcast=coord_cfg.get("broadcast", False),
                broadcast_sensitivity=coord_cfg.get("broadcast_sensitivity", "medium"),
                response_depth=coord_cfg.get("response_depth", "medium"),
                broadcast_timeout=coord_cfg.get("broadcast_timeout", 300),
                broadcast_wait_by_default=coord_cfg.get("broadcast_wait_by_default", True),
                max_broadcasts_per_agent=coord_cfg.get("max_broadcasts_per_agent", 10),
                task_planning_filesystem_mode=coord_cfg.get("task_planning_filesystem_mode", False),
                enable_memory_filesystem_mode=coord_cfg.get("enable_memory_filesystem_mode", False),
                use_skills=coord_cfg.get("use_skills", False),
                massgen_skills=coord_cfg.get("massgen_skills", []),
                skills_directory=coord_cfg.get("skills_directory", ".agent/skills"),
                load_previous_session_skills=coord_cfg.get("load_previous_session_skills", False),
            )

        # Get context sharing parameters
        snapshot_storage = orchestrator_cfg.get("snapshot_storage")
        agent_temporary_workspace = orchestrator_cfg.get("agent_temporary_workspace")

        # Create orchestrator with history from previous turns
        orchestrator = Orchestrator(
            agents=agents,
            config=orchestrator_config,
            session_id=session_id,
            snapshot_storage=snapshot_storage,
            agent_temporary_workspace=agent_temporary_workspace,
            previous_turns=previous_turns,
            winning_agents_history=winning_agents_history,
        )

        # Store the log session directory in the display
        display.log_session_dir = get_log_session_dir()
        print(f"[WebUI] run_coordination_with_history: turn={turn_number}, log_dir={display.log_session_dir}")

        # Create coordination UI with web display
        ui = CoordinationUI(
            display=display,
            display_type="web",
        )

        # Run coordination with conversation history (like CLI does)
        # Build messages list: previous Q&A pairs + current question
        messages = conversation_history.copy() if conversation_history else []
        messages.append({"role": "user", "content": question})

        if len(messages) > 1:
            # Multi-turn: use coordinate_with_context so agents see previous conversation
            print(f"[WebUI] Running coordination with {len(conversation_history)} history messages")
            await ui.coordinate_with_context(orchestrator, question, messages)
        else:
            # First turn: standard coordination
            await ui.coordinate(orchestrator, question)

        # Save CLI-compatible metadata for this turn
        await _save_session_metadata(
            session_id=session_id,
            question=question,
            orchestrator=orchestrator,
            config_path=str(resolved_path),
            log_session_dir=display.log_session_dir,
            turn_number=turn_number,
        )

        # Broadcast completion
        await manager.broadcast(
            session_id,
            {
                "type": "coordination_complete",
                "session_id": session_id,
                "turn": turn_number,
            },
        )

        # Mark session as completed so it persists in session list
        manager.mark_session_completed(
            session_id,
            question=question,
            config=str(resolved_path) if resolved_path else None,
        )

    except Exception as e:
        # Log the full traceback for debugging
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"[WebUI Error] {error_msg}")
        traceback.print_exc()

        # Broadcast error
        await manager.broadcast(
            session_id,
            {
                "type": "error",
                "message": error_msg,
                "session_id": session_id,
            },
        )


async def run_coordination(
    session_id: str,
    question: str,
    config_path: Optional[str] = None,
) -> None:
    """Run coordination with web display.

    Args:
        session_id: Session identifier
        question: Question for coordination
        config_path: Optional path to config YAML
    """
    import traceback

    async def send_init_status(message: str, step: str, progress: int = 0) -> None:
        """Send initialization status to WebSocket clients."""
        await manager.broadcast(
            session_id,
            {
                "type": "init_status",
                "message": message,
                "step": step,
                "progress": progress,
                "session_id": session_id,
            },
        )

    async def emit_preparation_status(status: str, detail: str = "") -> None:
        """Emit preparation status update to web clients."""
        await manager.broadcast(
            session_id,
            {
                "type": "preparation_status",
                "status": status,
                "detail": detail,
                "session_id": session_id,
            },
        )

    try:
        # Emit initial preparation status
        await emit_preparation_status("Loading configuration...", config_path or "")

        # Import here to avoid circular imports
        from massgen.agent_config import AgentConfig, CoordinationConfig
        from massgen.cli import (
            create_agents_from_config,
            load_config_file,
            resolve_config_path,
        )
        from massgen.frontend.coordination_ui import CoordinationUI
        from massgen.orchestrator import Orchestrator

        # Send initial status
        await send_init_status("Loading configuration...", "config", 10)

        # Load config from YAML file
        if not config_path:
            raise ValueError("Config path is required")

        # Resolve config path (handles @examples/, paths, etc.)
        resolved_path = resolve_config_path(config_path)
        if resolved_path is None:
            raise ValueError(f"Could not resolve config path: {config_path}")

        config = load_config_file(str(resolved_path))

        # Extract orchestrator config dict from YAML
        orchestrator_cfg = config.get("orchestrator", {})

        # Send agent setup status (this is the slow part - Docker containers, etc.)
        agent_configs = config.get("agents", [])
        num_agents = len(agent_configs)
        await send_init_status(f"Setting up {num_agents} agents...", "agents", 30)

        # Check if Docker is being used
        uses_docker = config.get("execution", {}).get("use_docker", False)
        if uses_docker:
            await emit_preparation_status("Preparing Docker environment...", "Setting up isolated containers")

        # Create agents from config with progress updates
        await emit_preparation_status("Initializing agents...", f"{num_agents} agent{'s' if num_agents != 1 else ''}")

        # Create progress callback that sends WebSocket updates
        # We run agent creation in a thread so progress updates can be sent in real-time
        loop = asyncio.get_running_loop()

        def progress_callback(status: str, detail: str) -> None:
            """Thread-safe callback to queue progress updates."""
            # Schedule the async emit on the main event loop
            asyncio.run_coroutine_threadsafe(
                emit_preparation_status(status, detail),
                loop,
            )

        # Run agent creation in thread pool so progress updates can be sent
        agents = await loop.run_in_executor(
            None,
            lambda: create_agents_from_config(
                config,
                orchestrator_config=orchestrator_cfg,
                config_path=str(resolved_path),
                memory_session_id=session_id,
                progress_callback=progress_callback,
            ),
        )

        # Get agent IDs and model names
        agent_ids = list(agents.keys())
        agent_models = {}
        for agent_id, agent in agents.items():
            # Try to get model name from agent - check multiple sources
            model_name = getattr(agent, "model", None)
            # For ConfigurableAgent, model is in config.backend_params["model"]
            if not model_name and hasattr(agent, "config") and agent.config:
                backend_params = getattr(agent.config, "backend_params", None)
                if backend_params:
                    model_name = backend_params.get("model")
            if model_name:
                agent_models[agent_id] = model_name

        await send_init_status(f"Agents ready: {', '.join(agent_ids)}", "agents_ready", 60)

        # Emit status about loaded agents
        await emit_preparation_status("Configuring orchestrator...", ", ".join(agent_ids))

        # Create web display with agent_models
        display = manager.create_display(session_id, agent_ids, agent_models)

        await send_init_status("Initializing orchestrator...", "orchestrator", 80)

        # Build AgentConfig object for orchestrator (required by Orchestrator)
        orchestrator_config = AgentConfig()

        # Apply voting sensitivity if specified
        if "voting_sensitivity" in orchestrator_cfg:
            orchestrator_config.voting_sensitivity = orchestrator_cfg["voting_sensitivity"]

        # Apply answer count limit if specified
        if "max_new_answers_per_agent" in orchestrator_cfg:
            orchestrator_config.max_new_answers_per_agent = orchestrator_cfg["max_new_answers_per_agent"]

        # Apply answer novelty requirement if specified
        if "answer_novelty_requirement" in orchestrator_cfg:
            orchestrator_config.answer_novelty_requirement = orchestrator_cfg["answer_novelty_requirement"]

        # Apply coordination config from YAML (includes enable_agent_task_planning, etc.)
        coord_cfg = orchestrator_cfg.get("coordination", {})
        if coord_cfg:
            orchestrator_config.coordination_config = CoordinationConfig(
                enable_planning_mode=coord_cfg.get("enable_planning_mode", False),
                planning_mode_instruction=coord_cfg.get(
                    "planning_mode_instruction",
                    "During coordination, describe what you would do without actually executing actions.",
                ),
                max_orchestration_restarts=coord_cfg.get("max_orchestration_restarts", 0),
                enable_agent_task_planning=coord_cfg.get("enable_agent_task_planning", False),
                max_tasks_per_plan=coord_cfg.get("max_tasks_per_plan", 10),
                broadcast=coord_cfg.get("broadcast", False),
                broadcast_sensitivity=coord_cfg.get("broadcast_sensitivity", "medium"),
                response_depth=coord_cfg.get("response_depth", "medium"),
                broadcast_timeout=coord_cfg.get("broadcast_timeout", 300),
                broadcast_wait_by_default=coord_cfg.get("broadcast_wait_by_default", True),
                max_broadcasts_per_agent=coord_cfg.get("max_broadcasts_per_agent", 10),
                task_planning_filesystem_mode=coord_cfg.get("task_planning_filesystem_mode", False),
                enable_memory_filesystem_mode=coord_cfg.get("enable_memory_filesystem_mode", False),
                use_skills=coord_cfg.get("use_skills", False),
                massgen_skills=coord_cfg.get("massgen_skills", []),
                skills_directory=coord_cfg.get("skills_directory", ".agent/skills"),
                load_previous_session_skills=coord_cfg.get("load_previous_session_skills", False),
            )

        # Get context sharing parameters
        snapshot_storage = orchestrator_cfg.get("snapshot_storage")
        agent_temporary_workspace = orchestrator_cfg.get("agent_temporary_workspace")

        # Create orchestrator with AgentConfig object
        orchestrator = Orchestrator(
            agents=agents,
            config=orchestrator_config,
            session_id=session_id,
            snapshot_storage=snapshot_storage,
            agent_temporary_workspace=agent_temporary_workspace,
        )

        # Store the log session directory in the display BEFORE coordination
        # This ensures the API can find it when coordination_complete is sent
        from massgen.logger_config import get_log_session_dir

        display.log_session_dir = get_log_session_dir()
        print(f"[DEBUG] run_coordination: Set display.log_session_dir = {display.log_session_dir}")

        # Print status.json location for automation mode monitoring
        if display.log_session_dir:
            print(f"LOG_DIR: {display.log_session_dir}")
            print(f"STATUS: {display.log_session_dir / 'status.json'}")

        # Create coordination UI with web display
        ui = CoordinationUI(
            display=display,
            display_type="web",
        )

        await send_init_status("Starting coordination...", "starting", 100)

        # Final preparation status before starting
        await emit_preparation_status("Launching agents...", "Agents will appear momentarily")

        # Run coordination
        await ui.coordinate(orchestrator, question)

        # Save CLI-compatible metadata for multi-turn continuation
        await _save_session_metadata(
            session_id=session_id,
            question=question,
            orchestrator=orchestrator,
            config_path=str(resolved_path),
            log_session_dir=display.log_session_dir,
        )

        # Broadcast completion
        await manager.broadcast(
            session_id,
            {
                "type": "coordination_complete",
                "session_id": session_id,
            },
        )

        # Mark session as completed so it persists in session list
        manager.mark_session_completed(
            session_id,
            question=question,
            config=str(resolved_path) if resolved_path else None,
        )

    except Exception as e:
        # Log the full traceback for debugging
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"[WebUI Error] {error_msg}")
        traceback.print_exc()

        # Broadcast error
        await manager.broadcast(
            session_id,
            {
                "type": "error",
                "message": error_msg,
                "session_id": session_id,
            },
        )


def run_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False,
    config_path: Optional[str] = None,
    automation_mode: bool = False,
) -> None:
    """Run the web server.

    Args:
        host: Host to bind to
        port: Port to listen on
        reload: Enable auto-reload for development
        config_path: Default config path for coordination sessions
        automation_mode: If True, UI shows automation-friendly timeline view
    """
    try:
        import uvicorn
    except ImportError:
        raise ImportError(
            "uvicorn is not installed. Install with: pip install massgen",
        )

    # Set default config before starting server
    if config_path:
        set_default_config(config_path)

    # Create app directly with automation_mode (can't pass args via factory string)
    app = create_app(config_path=config_path, automation_mode=automation_mode)

    # In automation mode, suppress verbose logging to keep stdout clean
    if automation_mode:
        import logging
        import warnings

        # Suppress uvicorn access logs and info messages
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.error").setLevel(logging.WARNING)

        # Suppress websockets deprecation warnings
        warnings.filterwarnings("ignore", category=DeprecationWarning, module="websockets")
        warnings.filterwarnings("ignore", category=DeprecationWarning, module="uvicorn.protocols.websockets")

        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="warning",
        )
    else:
        uvicorn.run(
            app,
            host=host,
            port=port,
        )


# For running directly: python -m massgen.frontend.web.server
if __name__ == "__main__":
    run_server()
