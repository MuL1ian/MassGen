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

    def create_display(self, session_id: str, agent_ids: list) -> WebDisplay:
        """Create a new WebDisplay for a session."""

        async def broadcast_fn(message: Dict[str, Any]) -> None:
            await self.broadcast(session_id, message)

        display = WebDisplay(
            agent_ids=agent_ids,
            broadcast=broadcast_fn,
            session_id=session_id,
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


def create_app(config_path: Optional[str] = None) -> "FastAPI":
    """Create and configure the FastAPI application.

    Args:
        config_path: Default config path for coordination sessions
    """
    if not FASTAPI_AVAILABLE:
        raise ImportError(
            "FastAPI is not installed. Install with: pip install 'massgen[web]'",
        )

    # Store default config
    if config_path:
        set_default_config(config_path)

    app = FastAPI(
        title="MassGen Web UI",
        description="Real-time multi-agent coordination visualization",
        version="0.1.0",
    )

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

    @app.get("/api/configs")
    async def list_configs():
        """List all available config files."""
        configs = []

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

        # Sort by category then name
        configs.sort(key=lambda x: (x["category"], x["name"]))

        return {
            "configs": configs,
            "default": get_default_config(),
        }

    @app.get("/api/sessions")
    async def list_sessions():
        """List all active sessions."""
        sessions = []
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

        Scans the log directory structure to find workspace snapshots
        associated with each answer.
        """
        from massgen.logger_config import get_log_session_dir

        display = manager.get_display(session_id)
        agent_ids = display.agent_ids if display else []

        workspaces = []
        log_session_dir = get_log_session_dir()

        if not log_session_dir or not log_session_dir.exists():
            return {"workspaces": [], "current": []}

        # Scan for answer workspaces in log directory
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
                                    "answerLabel": f"answer{agent_index}.{answer_count}",
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

        # log_session_dir is already the turn directory (e.g., .massgen/massgen_logs/log_xxx/turn_1)
        # Look for final/<agent>/answer.txt directly
        final_dir = log_session_dir / "final"
        print(f"[DEBUG] get_final_answer: Looking for final_dir={final_dir}")

        if final_dir.exists():
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
                        return JSONResponse(
                            {"error": f"Failed to read answer: {str(e)}", "answer": None},
                            status_code=500,
                        )

        # Fallback: search in turn subdirectories (for older log structure or if log_session_dir is base)
        print("[DEBUG] get_final_answer: No final dir, searching turn subdirs")
        for turn_dir in sorted(log_session_dir.iterdir(), reverse=True):
            if not turn_dir.is_dir() or not turn_dir.name.startswith("turn_"):
                continue

            final_dir = turn_dir / "final"
            if not final_dir.exists():
                continue

            for agent_dir in final_dir.iterdir():
                if not agent_dir.is_dir():
                    continue

                answer_file = agent_dir / "answer.txt"
                if answer_file.exists():
                    try:
                        answer_content = answer_file.read_text(encoding="utf-8")
                        return {
                            "answer": answer_content,
                            "agent_id": agent_dir.name,
                            "path": str(answer_file),
                        }
                    except Exception as e:
                        return JSONResponse(
                            {"error": f"Failed to read answer: {str(e)}", "answer": None},
                            status_code=500,
                        )

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
                        **display.get_state_snapshot(),
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

    # Path to React build directory
    static_dir = Path(__file__).parent.parent.parent.parent / "webui" / "dist"

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

    try:
        # Import here to avoid circular imports
        from massgen.agent_config import AgentConfig
        from massgen.cli import (
            create_agents_from_config,
            load_config_file,
            resolve_config_path,
        )
        from massgen.frontend.coordination_ui import CoordinationUI
        from massgen.orchestrator import Orchestrator

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

        # Create agents from config
        agents = create_agents_from_config(
            config,
            orchestrator_config=orchestrator_cfg,
            config_path=str(resolved_path),
            memory_session_id=session_id,
        )

        # Get agent IDs
        agent_ids = list(agents.keys())

        # Create web display
        display = manager.create_display(session_id, agent_ids)

        # Broadcast init event with agent info
        await manager.broadcast(
            session_id,
            {
                "type": "init",
                "session_id": session_id,
                "question": question,
                "agents": agent_ids,
                "theme": "default",
                "timestamp": 0,
                "sequence": 0,
            },
        )

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

        # Create coordination UI with web display
        ui = CoordinationUI(
            display=display,
            display_type="web",
        )

        # Run coordination
        await ui.coordinate(orchestrator, question)

        # Broadcast completion
        await manager.broadcast(
            session_id,
            {
                "type": "coordination_complete",
                "session_id": session_id,
            },
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
) -> None:
    """Run the web server.

    Args:
        host: Host to bind to
        port: Port to listen on
        reload: Enable auto-reload for development
        config_path: Default config path for coordination sessions
    """
    try:
        import uvicorn
    except ImportError:
        raise ImportError(
            "uvicorn is not installed. Install with: pip install 'massgen[web]'",
        )

    # Set default config before starting server
    if config_path:
        set_default_config(config_path)

    uvicorn.run(
        "massgen.frontend.web.server:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )


# For running directly: python -m massgen.frontend.web.server
if __name__ == "__main__":
    run_server()
