# -*- coding: utf-8 -*-
"""
Textual Terminal Display for MassGen Coordination

"""

import functools
import os
import re
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Deque, Dict, List, Optional

from massgen.logger_config import get_log_session_dir, logger

from .terminal_display import TerminalDisplay

try:
    from rich.text import Text
    from textual import events
    from textual.app import App, ComposeResult
    from textual.containers import Container, ScrollableContainer, Vertical
    from textual.message import Message
    from textual.screen import ModalScreen
    from textual.widget import Widget
    from textual.widgets import Button, Footer, Input, Label, RichLog, Static, TextArea

    from .content_handlers import ThinkingContentHandler, ToolContentHandler
    from .content_normalizer import ContentNormalizer
    from .textual_widgets import (
        AgentTabBar,
        AgentTabChanged,
        CompletionFooter,
        TimelineSection,
        ToolCallCard,
        ToolDetailModal,
        ToolSection,
    )

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False


# Tool message patterns for parsing
TOOL_PATTERNS = {
    # MCP tool patterns (Response API format)
    "mcp_start": re.compile(r"🔧 \[MCP\] Calling tool '([^']+)'"),
    "mcp_complete": re.compile(r"✅ \[MCP\] Tool '([^']+)' completed"),
    "mcp_failed": re.compile(r"❌ \[MCP\] Tool '([^']+)' failed: (.+)"),
    # MCP tool patterns (older format)
    "mcp_tool_start": re.compile(r"🔧 \[MCP Tool\] Calling ([^\.]+)\.\.\."),
    "mcp_tool_complete": re.compile(r"✅ \[MCP Tool\] ([^ ]+) completed"),
    # Custom tool patterns
    "custom_start": re.compile(r"🔧 \[Custom Tool\] Calling ([^\.]+)\.\.\."),
    "custom_complete": re.compile(r"✅ \[Custom Tool\] ([^ ]+) completed"),
    "custom_failed": re.compile(r"❌ \[Custom Tool Error\] (.+)"),
    # Arguments pattern
    "arguments": re.compile(r"^Arguments:(.+)", re.DOTALL),
    # Progress/status patterns
    "progress": re.compile(r"⏳.*progress|⏳.*in progress", re.IGNORECASE),
    "connected": re.compile(r"✅ \[MCP\] Connected to (\d+) servers?"),
    "unavailable": re.compile(r"⚠️ \[MCP\].*Setup failed"),
    # Injection patterns (cross-agent context sharing)
    "injection": re.compile(r"📥 \[INJECTION\] (.+)", re.DOTALL),
    # Reminder patterns (high priority task reminders)
    "reminder": re.compile(r"💡 \[REMINDER\] (.+)", re.DOTALL),
    # Session completed pattern
    "session_complete": re.compile(r"✅ \[MCP\] Session completed"),
}

# Tool category detection - maps tool names to semantic categories
TOOL_CATEGORIES = {
    "filesystem": {
        "icon": "📁",
        "color": "green",
        "patterns": [
            "read_file",
            "write_file",
            "list_directory",
            "create_directory",
            "delete_file",
            "move_file",
            "copy_file",
            "file_exists",
            "mcp__filesystem",
            "read_text_file",
            "write_text_file",
            "get_file_info",
            "search_files",
            "list_allowed_directories",
        ],
    },
    "web": {
        "icon": "🌐",
        "color": "blue",
        "patterns": [
            "web_search",
            "search_web",
            "google_search",
            "fetch_url",
            "browse",
            "http_get",
            "http_post",
            "scrape",
            "crawl",
            "mcp__brave",
            "mcp__web",
            "mcp__fetch",
        ],
    },
    "code": {
        "icon": "💻",
        "color": "yellow",
        "patterns": [
            "execute_command",
            "run_code",
            "bash",
            "python",
            "shell",
            "exec",
            "terminal",
            "command",
            "run_script",
            "execute_python",
            "mcp__code",
            "mcp__shell",
            "mcp__terminal",
        ],
    },
    "database": {
        "icon": "🗄️",
        "color": "magenta",
        "patterns": [
            "query",
            "sql",
            "database",
            "db_",
            "select",
            "insert",
            "mcp__postgres",
            "mcp__sqlite",
            "mcp__mysql",
            "mcp__mongo",
            "arbitrary_query",
            "schema_reference",
        ],
    },
    "git": {
        "icon": "🔀",
        "color": "red",
        "patterns": [
            "git_",
            "commit",
            "push",
            "pull",
            "branch",
            "merge",
            "mcp__git",
            "clone",
            "checkout",
            "diff",
            "log",
        ],
    },
    "api": {
        "icon": "🔌",
        "color": "cyan",
        "patterns": [
            "api_",
            "rest_",
            "graphql",
            "request",
            "endpoint",
            "mcp__slack",
            "mcp__discord",
            "mcp__twitter",
            "mcp__notion",
        ],
    },
    "ai": {
        "icon": "🤖",
        "color": "bright_magenta",
        "patterns": [
            "llm_",
            "ai_",
            "generate",
            "embed",
            "chat_completion",
            "mcp__openai",
            "mcp__anthropic",
            "mcp__gemini",
        ],
    },
    "weather": {
        "icon": "🌤️",
        "color": "bright_cyan",
        "patterns": [
            "weather",
            "forecast",
            "temperature",
            "get-forecast",
            "mcp__weather",
        ],
    },
    "memory": {
        "icon": "🧠",
        "color": "bright_yellow",
        "patterns": [
            "memory",
            "remember",
            "recall",
            "store",
            "retrieve",
            "mcp__memory",
            "knowledge",
            "context",
        ],
    },
}


def _get_tool_category(tool_name: str) -> dict:
    """Determine the semantic category of a tool based on its name.

    Args:
        tool_name: The tool name (e.g., "mcp__filesystem__read_file")

    Returns:
        Dict with icon, color, and category name
    """
    tool_lower = tool_name.lower()

    for category, info in TOOL_CATEGORIES.items():
        for pattern in info["patterns"]:
            if pattern in tool_lower:
                return {
                    "category": category,
                    "icon": info["icon"],
                    "color": info["color"],
                }

    # Default for unknown tools
    return {
        "category": "tool",
        "icon": "🔧",
        "color": "cyan",
    }


def _format_tool_name(tool_name: str) -> str:
    """Format tool name for display - strip prefixes and clean up.

    Args:
        tool_name: Raw tool name (e.g., "mcp__filesystem__read_file")

    Returns:
        Cleaned display name (e.g., "read_file")
    """
    # Strip common prefixes
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__")
        if len(parts) >= 3:
            # mcp__server__tool -> tool (server)
            return f"{parts[-1]} ({parts[1]})"
        elif len(parts) == 2:
            return parts[1]

    return tool_name


def _clean_tool_arguments(args_str: str) -> str:
    """Clean up tool arguments for display - extract key info from dicts/JSON.

    Args:
        args_str: Raw arguments string (may be dict repr or JSON)

    Returns:
        Clean, readable summary of the arguments
    """
    import json

    args_str = args_str.strip()

    # Try to parse as JSON/dict
    try:
        # Handle dict-like strings
        if args_str.startswith("{") or args_str.startswith("Arguments:"):
            clean = args_str.replace("Arguments:", "").strip()
            # Try JSON parse
            try:
                data = json.loads(clean)
            except json.JSONDecodeError:
                # Try eval for dict repr (safely)
                import ast

                try:
                    data = ast.literal_eval(clean)
                except (ValueError, SyntaxError):
                    data = None

            if isinstance(data, dict):
                # Extract key fields for nice display
                parts = []
                for key, value in data.items():
                    # Skip long content fields
                    if key in ("content", "body", "text", "data") and isinstance(value, str) and len(value) > 50:
                        parts.append(f"{key}: [{len(value)} chars]")
                    # Shorten paths
                    elif key in ("path", "file", "directory", "work_dir") and isinstance(value, str):
                        # Show just filename or last part of path
                        short_path = value.split("/")[-1] if "/" in value else value
                        if len(value) > 40:
                            parts.append(f"{key}: .../{short_path}")
                        else:
                            parts.append(f"{key}: {value}")
                    # Truncate command
                    elif key == "command" and isinstance(value, str):
                        if len(value) > 60:
                            parts.append(f"{key}: {value[:60]}...")
                        else:
                            parts.append(f"{key}: {value}")
                    # Skip internal fields
                    elif key.startswith("_"):
                        continue
                    # Show other fields truncated
                    elif isinstance(value, str) and len(value) > 50:
                        parts.append(f"{key}: {value[:50]}...")
                    elif isinstance(value, (list, dict)):
                        parts.append(f"{key}: [{type(value).__name__}]")
                    else:
                        parts.append(f"{key}: {value}")

                if parts:
                    return " | ".join(parts[:3])  # Max 3 fields
                return "[no args]"
    except Exception:
        pass

    # Fallback: just truncate
    if len(args_str) > 80:
        return args_str[:80] + "..."
    return args_str


def _clean_tool_result(result_str: str, tool_name: str = "") -> str:
    """Clean up tool result for display - summarize long output.

    Args:
        result_str: Raw result string
        tool_name: Tool name for context-aware formatting

    Returns:
        Clean, readable summary of the result
    """
    import json

    result_str = result_str.strip()

    # Handle common MCP result formats
    if result_str.startswith("{"):
        try:
            data = json.loads(result_str)
            if isinstance(data, dict):
                # Check for success/error status
                if "success" in data:
                    status = "✓" if data["success"] else "✗"
                    if "message" in data:
                        return f"{status} {data['message'][:60]}"
                    return f"{status} completed"

                # Check for content result
                if "content" in data:
                    content = data["content"]
                    if isinstance(content, str):
                        lines = content.count("\n") + 1
                        return f"[{lines} lines]"
                    return "[content]"

                # Check for exit code (command execution)
                if "exit_code" in data:
                    code = data["exit_code"]
                    status = "✓" if code == 0 else f"exit {code}"
                    return status

                # Generic dict - show key count
                return f"[{len(data)} fields]"
        except json.JSONDecodeError:
            pass

    # Handle path-related results
    if "Parent directory does not exist" in result_str:
        return "✗ directory not found"
    if "does not exist" in result_str:
        return "✗ not found"
    if "Permission denied" in result_str:
        return "✗ permission denied"

    # Handle file content (multiple lines)
    lines = result_str.split("\n")
    if len(lines) > 5:
        return f"[{len(lines)} lines]"

    # Short result - show truncated
    if len(result_str) > 60:
        return result_str[:60] + "..."
    return result_str


def _parse_tool_message(content: str) -> dict:
    """Parse tool message to extract structured info.

    Args:
        content: Tool message text from backend

    Returns:
        Dict with keys:
        - event: "start", "complete", "failed", "arguments", "progress", "status", "unknown"
        - tool_name: Name of the tool (if applicable)
        - tool_type: "mcp" or "custom"
        - category: Tool category info (icon, color, category name)
        - display_name: Formatted display name
        - error: Error message (if failed)
        - arguments: Arguments string (if arguments event)
        - raw: Original content (always present)
    """
    result = {"event": "unknown", "raw": content}

    def enrich_with_category(parsed: dict) -> dict:
        """Add category info to parsed result."""
        if "tool_name" in parsed:
            parsed["category"] = _get_tool_category(parsed["tool_name"])
            parsed["display_name"] = _format_tool_name(parsed["tool_name"])
        return parsed

    # Check MCP start patterns
    match = TOOL_PATTERNS["mcp_start"].search(content)
    if match:
        return enrich_with_category(
            {"event": "start", "tool_name": match.group(1), "tool_type": "mcp", "raw": content},
        )

    match = TOOL_PATTERNS["mcp_tool_start"].search(content)
    if match:
        return enrich_with_category(
            {"event": "start", "tool_name": match.group(1), "tool_type": "mcp", "raw": content},
        )

    # Check Custom tool start
    match = TOOL_PATTERNS["custom_start"].search(content)
    if match:
        return enrich_with_category(
            {"event": "start", "tool_name": match.group(1), "tool_type": "custom", "raw": content},
        )

    # Check MCP complete patterns
    match = TOOL_PATTERNS["mcp_complete"].search(content)
    if match:
        return enrich_with_category(
            {"event": "complete", "tool_name": match.group(1), "tool_type": "mcp", "raw": content},
        )

    match = TOOL_PATTERNS["mcp_tool_complete"].search(content)
    if match:
        return enrich_with_category(
            {"event": "complete", "tool_name": match.group(1), "tool_type": "mcp", "raw": content},
        )

    # Check Custom complete
    match = TOOL_PATTERNS["custom_complete"].search(content)
    if match:
        return enrich_with_category(
            {"event": "complete", "tool_name": match.group(1), "tool_type": "custom", "raw": content},
        )

    # Check MCP failed pattern
    match = TOOL_PATTERNS["mcp_failed"].search(content)
    if match:
        return enrich_with_category(
            {
                "event": "failed",
                "tool_name": match.group(1),
                "tool_type": "mcp",
                "error": match.group(2),
                "raw": content,
            },
        )

    # Check Custom failed pattern
    match = TOOL_PATTERNS["custom_failed"].search(content)
    if match:
        return {"event": "failed", "tool_type": "custom", "error": match.group(1), "raw": content}

    # Check arguments pattern
    match = TOOL_PATTERNS["arguments"].search(content)
    if match or content.strip().startswith("Arguments:"):
        return {"event": "arguments", "arguments": content, "raw": content}

    # Check progress pattern
    if TOOL_PATTERNS["progress"].search(content):
        return {"event": "progress", "raw": content}

    # Check status patterns (connected, unavailable)
    match = TOOL_PATTERNS["connected"].search(content)
    if match:
        return {"event": "status", "status_type": "connected", "server_count": match.group(1), "raw": content}

    if TOOL_PATTERNS["unavailable"].search(content):
        return {"event": "status", "status_type": "unavailable", "raw": content}

    # Check injection pattern (cross-agent context sharing)
    match = TOOL_PATTERNS["injection"].search(content)
    if match:
        return {"event": "injection", "content": match.group(1), "raw": content}

    # Check reminder pattern (high priority task reminders)
    match = TOOL_PATTERNS["reminder"].search(content)
    if match:
        return {"event": "reminder", "content": match.group(1), "raw": content}

    # Check session complete pattern
    if TOOL_PATTERNS["session_complete"].search(content):
        return {"event": "session_complete", "raw": content}

    return result


def _process_line_buffer(
    buffer: str,
    content: str,
    log_writer: Callable[[str], None],
) -> str:
    """Process content with line buffering, return updated buffer.

    Args:
        buffer: Current line buffer content.
        content: New content to append.
        log_writer: Callable to write complete lines.

    Returns:
        Updated buffer containing incomplete line.
    """
    buffer += content
    if "\n" in buffer:
        lines = buffer.split("\n")
        for line in lines[:-1]:
            if line.strip():
                log_writer(line)
        return lines[-1]
    return buffer


# Emoji fallback mapping for terminals without Unicode support
EMOJI_FALLBACKS = {
    "🚀": ">>",  # Launch
    "💡": "(!)",  # Question
    "🤖": "[A]",  # Agent
    "✅": "[✓]",  # Success
    "❌": "[X]",  # Error
    "🔄": "[↻]",  # Processing
    "📊": "[=]",  # Stats
    "🎯": "[>]",  # Target
    "⚡": "[!]",  # Fast
    "🎤": "[M]",  # Presentation
    "🔍": "[?]",  # Search/Evaluation
    "⚠️": "[!]",  # Warning
    "📋": "[□]",  # Summary
    "🧠": "[B]",  # Brain/Reasoning
}

CRITICAL_PATTERNS = {
    "vote": "✅ Vote recorded",
    "status": ["📊 Status changed", "Status: "],
    "tool": "🔧",
    "presentation": "🎤 Final Presentation",
}

CRITICAL_CONTENT_TYPES = {"status", "presentation", "tool", "vote", "error"}


class TextualTerminalDisplay(TerminalDisplay):
    """Textual-based terminal display with feature parity to Rich."""

    def __init__(self, agent_ids: List[str], **kwargs: Any):
        super().__init__(agent_ids, **kwargs)
        self._validate_agent_ids()
        self._dom_id_mapping: Dict[str, str] = {}

        # Agent models mapping (agent_id -> model name) for display
        self.agent_models: Dict[str, str] = kwargs.get("agent_models", {})

        self.theme = kwargs.get("theme", "dark")
        self.refresh_rate = kwargs.get("refresh_rate")
        self.enable_syntax_highlighting = kwargs.get("enable_syntax_highlighting", True)
        self.show_timestamps = kwargs.get("show_timestamps", True)
        self.max_line_length = kwargs.get("max_line_length", 100)
        self.max_web_search_lines = kwargs.get("max_web_search_lines", 4)
        self.truncate_web_on_status_change = kwargs.get("truncate_web_on_status_change", True)
        self.max_web_lines_on_status_change = kwargs.get("max_web_lines_on_status_change", 3)
        # Runtime toggle to ignore hotkeys/key handling when enabled
        self.safe_keyboard_mode = kwargs.get("safe_keyboard_mode", False)
        self.max_buffer_batch = kwargs.get("max_buffer_batch", 50)
        self._keyboard_interactive_mode = kwargs.get("keyboard_interactive_mode", True)

        # File output
        default_output_dir = kwargs.get("output_dir")
        if default_output_dir is None:
            try:
                default_output_dir = get_log_session_dir() / "agent_outputs"
            except Exception:
                default_output_dir = Path("output") / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(default_output_dir)
        self.agent_files = {}
        self.system_status_file = None
        self.final_presentation_file = None
        self.final_presentation_latest = None

        # Textual app
        self._app = None

        # Display state
        self.question = ""
        self.log_filename = None
        self.restart_reason = None
        self.restart_instructions = None
        self._final_answer_cache: Optional[str] = None
        self._final_answer_metadata: Dict[str, Any] = {}
        self._post_evaluation_lines: Deque[str] = deque(maxlen=20)
        self._final_stream_active = False
        self._final_stream_buffer: str = ""
        self._final_presentation_agent: Optional[str] = None

        self._app_ready = threading.Event()
        self._input_handler: Optional[Callable[[str], None]] = None
        self.orchestrator = None
        self._user_quit_requested = False
        self.session_id = None
        self.current_turn = 1

        self.emoji_support = self._detect_emoji_support()
        self._terminal_type = self._detect_terminal_type()

        if self.refresh_rate is None:
            self.refresh_rate = self._get_adaptive_refresh_rate(self._terminal_type)
        else:
            self.refresh_rate = int(self.refresh_rate)

        if self.enable_syntax_highlighting is None:
            self.enable_syntax_highlighting = True

        default_buffer_flush = kwargs.get("buffer_flush_interval")
        if default_buffer_flush is None:
            if self._terminal_type in ("vscode", "windows_terminal"):
                default_buffer_flush = 0.3
            else:
                adaptive_flush = max(0.1, 1 / max(self.refresh_rate, 1))
                default_buffer_flush = min(adaptive_flush, 0.15)
        self.buffer_flush_interval = default_buffer_flush
        self._buffers = {agent_id: [] for agent_id in self.agent_ids}
        self._buffer_lock = threading.Lock()
        self._recent_web_chunks: Dict[str, Deque[str]] = {agent_id: deque(maxlen=self.max_web_search_lines) for agent_id in self.agent_ids}

    def _validate_agent_ids(self):
        """Validate agent IDs for security and robustness."""
        if not self.agent_ids:
            raise ValueError("At least one agent ID is required")

        MAX_AGENT_ID_LENGTH = 100

        for agent_id in self.agent_ids:
            if len(agent_id) > MAX_AGENT_ID_LENGTH:
                truncated_preview = agent_id[:50] + "..."
                raise ValueError(f"Agent ID exceeds maximum length of {MAX_AGENT_ID_LENGTH} characters: {truncated_preview}")

            if not agent_id or not agent_id.strip():
                raise ValueError("Agent ID cannot be empty or whitespace-only")

        if len(self.agent_ids) != len(set(self.agent_ids)):
            raise ValueError("Duplicate agent IDs detected")

    def _detect_emoji_support(self) -> bool:
        """Detect if terminal supports emoji."""
        import locale

        term_program = os.environ.get("TERM_PROGRAM", "")
        if term_program in ["vscode", "iTerm.app", "Apple_Terminal"]:
            return True

        if os.environ.get("WT_SESSION"):
            return True

        if os.environ.get("WT_PROFILE_ID"):
            return True

        try:
            encoding = locale.getpreferredencoding()
            if encoding.lower() in ["utf-8", "utf8"]:
                return True
        except Exception:
            pass

        lang = os.environ.get("LANG", "")
        if "UTF-8" in lang or "utf8" in lang:
            return True

        return False

    def _get_icon(self, emoji: str) -> str:
        """Get emoji or fallback based on terminal support."""
        if self.emoji_support:
            return emoji
        return EMOJI_FALLBACKS.get(emoji, emoji)

    def _is_critical_content(self, content: str, content_type: str) -> bool:
        """Identify content that should flush immediately."""
        if content_type in CRITICAL_CONTENT_TYPES:
            return True

        lowered = content.lower()
        if "vote recorded" in lowered:
            return True

        for value in CRITICAL_PATTERNS.values():
            if isinstance(value, list):
                if any(pattern in content for pattern in value):
                    return True
            else:
                if value in content:
                    return True
        return False

    def _detect_terminal_type(self) -> str:
        """Detect terminal type and capabilities."""
        if os.environ.get("TERM_PROGRAM") == "vscode":
            return "vscode"

        if os.environ.get("TERM_PROGRAM") == "iTerm.app":
            return "iterm"

        if os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_CLIENT"):
            return "ssh"

        if os.environ.get("WT_SESSION"):
            return "windows_terminal"

        return "unknown"

    def _get_adaptive_refresh_rate(self, terminal_type: str) -> int:
        """Get optimal refresh rate based on terminal."""
        rates = {
            "ssh": 4,
            "vscode": 4,
            "iterm": 10,
            "windows_terminal": 4,
            "unknown": 6,
        }
        return rates.get(terminal_type, 6)

    def _write_to_agent_file(self, agent_id: str, content: str):
        """Write content to agent's output file."""
        if agent_id not in self.agent_files:
            return

        file_path = self.agent_files[agent_id]
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                suffix = "" if content.endswith("\n") else "\n"
                f.write(content + suffix)
                f.flush()
        except OSError as exc:
            logger.warning(f"Failed to append to agent log {file_path} for {agent_id}: {exc}")

    def _write_to_system_file(self, content: str):
        """Write content to system status file."""
        if not self.system_status_file:
            return

        try:
            with open(self.system_status_file, "a", encoding="utf-8") as f:
                if self.show_timestamps:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    f.write(f"[{timestamp}] {content}\n")
                else:
                    f.write(f"{content}\n")
                f.flush()
        except OSError as exc:
            logger.warning(f"Failed to append to system status log {self.system_status_file}: {exc}")

    def _call_app_method(self, method_name: str, *args: Any, **kwargs: Any):
        """Invoke a Textual app method safely regardless of calling thread."""
        if not self._app:
            return

        callback = getattr(self._app, method_name, None)
        if not callback:
            return

        app_thread_id = getattr(self._app, "_thread_id", None)
        if app_thread_id is not None and app_thread_id == threading.get_ident():
            callback(*args, **kwargs)
        else:
            self._app.call_from_thread(callback, *args, **kwargs)

    def set_input_handler(self, handler: Callable[[str], None]) -> None:
        """Set the callback for user-submitted input (questions or commands)"""
        self._input_handler = handler
        if self._app:
            try:
                self._app.set_input_handler(handler)
            except Exception:
                pass

    def initialize(self, question: str, log_filename: Optional[str] = None):
        """Initialize display with file output."""
        self.question = question
        self.log_filename = log_filename

        if self._app is not None:
            return
        self.output_dir = Path(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        for agent_id in self.agent_ids:
            file_path = self.output_dir / f"{agent_id}.txt"
            self.agent_files[agent_id] = file_path
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"=== {agent_id.upper()} OUTPUT LOG ===\n\n")

        self.system_status_file = self.output_dir / "system_status.txt"
        with open(self.system_status_file, "w", encoding="utf-8") as f:
            f.write("=== SYSTEM STATUS LOG ===\n")
            f.write(f"Question: {question}\n\n")

        self.final_presentation_file = None
        self.final_presentation_latest = None

        if TEXTUAL_AVAILABLE:
            self._app = TextualApp(
                self,
                question,
                buffers=self._buffers,
                buffer_lock=self._buffer_lock,
                buffer_flush_interval=self.buffer_flush_interval,
            )

    def update_agent_content(self, agent_id: str, content: str, content_type: str = "thinking"):
        """Update agent content with appropriate formatting.

        Args:
            agent_id: Agent identifier
            content: Content to display
            content_type: Type of content - "thinking", "tool", "status", "presentation"
        """
        if not content:
            return

        display_type = "status" if content_type == "thinking" and self._is_critical_content(content, content_type) else content_type

        prepared = self._prepare_agent_content(agent_id, content, display_type)

        self.agent_outputs[agent_id].append(content)
        self._write_to_agent_file(agent_id, content)

        if not prepared:
            return

        is_critical = self._is_critical_content(content, display_type)

        with self._buffer_lock:
            self._buffers[agent_id].append(
                {
                    "content": prepared,
                    "type": display_type,
                    "timestamp": datetime.now(),
                    "force_jump": False,
                },
            )
            buffered_len = len(self._buffers[agent_id])

        if self._app and (is_critical or buffered_len >= self.max_buffer_batch):
            self._app.request_flush()

    def update_agent_status(self, agent_id: str, status: str):
        """Update status for a specific agent."""
        self.agent_status[agent_id] = status
        self._reset_web_cache(agent_id, truncate_history=self.truncate_web_on_status_change)

        if self._app:
            self._app.request_flush()
        with self._buffer_lock:
            existing = self._buffers.get(agent_id, [])
            preserved: List[Dict[str, Any]] = []
            for entry in existing:
                entry_content = entry.get("content", "")
                entry_type = entry.get("type", "thinking")
                if self._is_critical_content(entry_content, entry_type):
                    preserved.append(entry)
            self._buffers[agent_id] = preserved
            self._buffers[agent_id].append(
                {
                    "content": f"📊 Status changed to {status}",
                    "type": "status",
                    "timestamp": datetime.now(),
                    "force_jump": True,
                },
            )

        if self._app:
            self._call_app_method("update_agent_status", agent_id, status)

        status_msg = f"\n[Status Changed: {status.upper()}]\n"
        self._write_to_agent_file(agent_id, status_msg)

    def add_orchestrator_event(self, event: str):
        """Add an orchestrator coordination event."""
        self.orchestrator_events.append(event)
        self._write_to_system_file(event)

        if self._app:
            self._app.request_flush()
            self._call_app_method("add_orchestrator_event", event)
            # Also increment status bar event counter
            self._call_app_method("add_status_bar_event")

    # === Status Bar Notification Bridge Methods ===

    def notify_vote(self, voter: str, voted_for: str):
        """Notify the TUI of a vote cast - updates status bar and shows toast."""
        if self._app:
            self._call_app_method("notify_vote", voter, voted_for)

    def notify_phase(self, phase: str):
        """Notify the TUI of a phase change - updates status bar."""
        if self._app:
            self._call_app_method("notify_phase", phase)

    def notify_completion(self, agent_id: str):
        """Notify the TUI of agent completion - shows toast."""
        if self._app:
            self._call_app_method("notify_completion", agent_id)

    def notify_error(self, agent_id: str, error: str):
        """Notify the TUI of an error - shows error toast."""
        if self._app:
            self._call_app_method("notify_error", agent_id, error)

    def update_status_bar_votes(self, vote_counts: Dict[str, int]):
        """Update vote counts in the status bar."""
        if self._app:
            self._call_app_method("update_status_bar_votes", vote_counts)

    def show_final_answer(self, answer: str, vote_results=None, selected_agent=None):
        """Show final answer with flush effect."""
        if not selected_agent:
            return

        stream_buffer = self._final_stream_buffer.strip() if hasattr(self, "_final_stream_buffer") else ""
        display_answer = answer or stream_buffer
        if self._final_stream_active:
            self._end_final_answer_stream()
        elif not stream_buffer and self._app:
            self._final_stream_active = True
            self._final_stream_buffer = display_answer
            self._call_app_method(
                "begin_final_stream",
                selected_agent,
                vote_results or {},
            )
            self._call_app_method("update_final_stream", display_answer)
        self._final_answer_metadata = {
            "selected_agent": selected_agent,
            "vote_results": vote_results or {},
        }
        self._final_presentation_agent = selected_agent

        # Write to final presentation file(s)
        persist_needed = self._final_answer_cache is None or self._final_answer_cache != display_answer
        if persist_needed:
            self._persist_final_presentation(display_answer, selected_agent, vote_results)
            self._final_answer_cache = display_answer

        self._write_to_system_file("Final presentation ready.")

        if self._app:
            self._call_app_method(
                "show_final_presentation",
                display_answer,
                vote_results,
                selected_agent,
            )

    def show_post_evaluation_content(self, content: str, agent_id: str):
        """Display post-evaluation streaming content."""
        eval_msg = f"\n[POST-EVALUATION]\n{content}"
        self._write_to_agent_file(agent_id, eval_msg)
        for line in content.splitlines() or [content]:
            clean = line.strip()
            if clean:
                self._post_evaluation_lines.append(clean)

        if self._app:
            self._app.call_from_thread(
                self._app.show_post_evaluation,
                content,
                agent_id,
            )

    def show_restart_banner(self, reason: str, instructions: str, attempt: int, max_attempts: int):
        """Display restart decision banner."""
        banner_msg = f"\n{'=' * 60}\n" f"RESTART TRIGGERED (Attempt {attempt}/{max_attempts})\n" f"Reason: {reason}\n" f"Instructions: {instructions}\n" f"{'=' * 60}\n"

        self._write_to_system_file(banner_msg)

        if self._app:
            self._app.call_from_thread(
                self._app.show_restart_banner,
                reason,
                instructions,
                attempt,
                max_attempts,
            )

    def show_restart_context_panel(self, reason: str, instructions: str):
        """Display restart context panel at top of UI (for attempt 2+)."""
        self.restart_reason = reason
        self.restart_instructions = instructions

        if self._app:
            self._app.call_from_thread(
                self._app.show_restart_context,
                reason,
                instructions,
            )

    def cleanup(self):
        """Cleanup and exit Textual app."""
        if self._app:
            self._app.exit()
            self._app = None
        self._post_evaluation_lines.clear()
        self._final_stream_active = False
        self._final_stream_buffer = ""
        self._final_answer_cache = None
        self._final_answer_metadata = {}
        self._final_presentation_agent = None

    def reset_quit_request(self) -> None:
        """Reset the quit request flag at the start of each turn."""
        self._user_quit_requested = False

    def request_cancellation(self) -> None:
        """Request cancellation of the current turn."""
        self._user_quit_requested = True
        if self._app and hasattr(self._app, "notify"):
            self._call_app_method("notify", "Cancelling turn...", severity="warning")

    # =========================================================================
    # Multi-turn Lifecycle Methods
    # =========================================================================

    def start_session(
        self,
        initial_question: str,
        log_filename: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Start a new interactive session - creates the app ONCE."""
        self.session_id = session_id
        self.current_turn = 1

        # Only initialize if app doesn't exist
        if self._app is None:
            self.initialize(initial_question, log_filename)

    def begin_turn(self, turn: int, question: str) -> None:
        """Begin a new turn within an existing session.

        Updates the header and optionally resets buffers/panels.
        Does NOT recreate the app.

        Args:
            turn: The turn number (1-indexed).
            question: The user's question for this turn.
        """
        self.current_turn = turn
        self.question = question

        self.reset_quit_request()

        self._final_answer_cache = None
        self._final_answer_metadata = {}
        self._final_stream_active = False
        self._final_stream_buffer = ""
        self._final_presentation_agent = None

        if self._app:
            self._call_app_method("update_turn_header", turn, question)

        for agent_id in self.agent_ids:
            separator = f"\n{'='*60}\n=== TURN {turn} ===\n{'='*60}\n"
            self._write_to_agent_file(agent_id, separator)

        self._write_to_system_file(f"\n=== TURN {turn} ===\nQuestion: {question}\n")

    def end_turn(
        self,
        turn: int,
        answer: Optional[str] = None,
        error: Optional[Exception] = None,
        was_cancelled: bool = False,
    ) -> None:
        """End the current turn"""
        if self._app:
            self._call_app_method("set_input_enabled", True)

        if was_cancelled:
            self._write_to_system_file(f"Turn {turn} cancelled by user.")
        elif error:
            self._write_to_system_file(f"Turn {turn} failed: {error}")
        else:
            self._write_to_system_file(f"Turn {turn} completed successfully.")

    def is_session_active(self) -> bool:
        """Check if a session is currently active (app is running)"""
        return self._app is not None

    def run(self):
        """Run Textual app in main thread."""
        if self._app and TEXTUAL_AVAILABLE:
            self._app.run()

    async def run_async(self):
        """Run Textual app within an existing asyncio event loop."""
        if self._app and TEXTUAL_AVAILABLE:
            await self._app.run_async()

    # Rich parity methods (not in BaseDisplay, but needed for feature parity)
    def display_vote_results(self, vote_results: Dict[str, Any]):
        """Display vote results in formatted table."""
        formatted = self._format_vote_results(vote_results)
        self._call_app_method("display_vote_results", formatted)
        self._write_to_system_file(f"Vote Results: {vote_results}")

    def display_coordination_table(self):
        """Display coordination table using existing builder."""
        table_text = self._format_coordination_table_from_orchestrator()
        self._call_app_method("display_coordination_table", table_text)

    def update_system_status(self, status: str) -> None:
        """Display system-level status updates (initialization, cancellation, etc.)"""
        self._write_to_system_file(f"System status: {status}")

        if self._app:
            self._call_app_method("add_orchestrator_event", status)

    def _format_coordination_table_from_orchestrator(self) -> str:
        """Build coordination table text with best effort."""
        table_text = "Coordination data is not available yet."
        try:
            from massgen.frontend.displays.create_coordination_table import (
                CoordinationTableBuilder,
            )

            tracker = getattr(self.orchestrator, "coordination_tracker", None)
            if tracker:
                events_data = [event.to_dict() for event in getattr(tracker, "events", [])]
                session_data = {
                    "session_metadata": {
                        "user_prompt": getattr(tracker, "user_prompt", ""),
                        "agent_ids": getattr(tracker, "agent_ids", []),
                        "start_time": getattr(tracker, "start_time", None),
                        "end_time": getattr(tracker, "end_time", None),
                        "final_winner": getattr(tracker, "final_winner", None),
                    },
                    "events": events_data,
                }
                builder = CoordinationTableBuilder(session_data)
                table_text = self._format_coordination_table(builder)
        except Exception as exc:
            table_text = f"Unable to build coordination table: {exc}"

        return table_text

    def show_agent_selector(self):
        """Show interactive agent selector modal."""
        self._call_app_method("show_agent_selector")

    def stream_final_answer_chunk(self, chunk: str, selected_agent: Optional[str], vote_results: Optional[Dict[str, Any]] = None):
        """Stream incoming final presentation content into the Textual UI."""
        if not chunk:
            return

        # Don't stream if no valid agent is selected
        if not selected_agent:
            return

        if not self._final_stream_active:
            if self._app:
                self._app.buffer_flush_interval = min(self._app.buffer_flush_interval, 0.05)
            self._final_stream_active = True
            self._final_stream_buffer = ""
            self._final_answer_metadata = {
                "selected_agent": selected_agent,
                "vote_results": vote_results or {},
            }
            self._final_presentation_agent = selected_agent
            if self._app:
                self._call_app_method(
                    "begin_final_stream",
                    selected_agent,
                    vote_results or {},
                )

        # Preserve natural spacing; avoid forcing newlines between streamed chunks
        spacer = ""
        if self._final_stream_buffer:
            prev = self._final_stream_buffer[-1]
            next_char = chunk[0] if chunk else ""
            if not prev.isspace() and next_char and not next_char.isspace():
                spacer = " "
        self._final_stream_buffer += f"{spacer}{chunk}"

        if self._app:
            self._call_app_method("update_final_stream", chunk)

    def _end_final_answer_stream(self):
        """Hide streaming panel when final presentation completes."""
        if not self._final_stream_active:
            return
        self._final_stream_active = False
        if self._app:
            self._call_app_method("end_final_stream")
        if self._final_stream_buffer and not self._final_answer_cache:
            final_content = self._final_stream_buffer.strip()
            self._persist_final_presentation(
                final_content,
                self._final_presentation_agent,
                self._final_answer_metadata.get("vote_results"),
            )
            self._final_answer_cache = final_content

    def _prepare_agent_content(self, agent_id: str, content: str, content_type: str) -> Optional[str]:
        """Normalize agent content, apply filters, and truncate noisy sections."""
        if not content:
            return None

        if agent_id not in self._recent_web_chunks:
            self._recent_web_chunks[agent_id] = deque(maxlen=self.max_web_search_lines)

        if self._should_filter_content(content, content_type):
            return None

        if content_type in {"status", "presentation", "tool"}:
            self._reset_web_cache(agent_id)

        if self._is_web_search_content(content):
            truncated = self._truncate_web_content(content)
            history = self._recent_web_chunks.get(agent_id)
            if history is not None:
                history.append(truncated)
            return truncated

        return content

    def _truncate_web_content(self, content: str) -> str:
        """Trim verbose web search snippets while keeping the useful prefix."""
        max_len = min(60, self.max_line_length // 2)
        if len(content) <= max_len:
            return content

        truncated = content[:max_len]
        for token in [". ", "! ", "? ", ", "]:
            idx = truncated.rfind(token)
            if idx > max_len // 2:
                truncated = truncated[: idx + 1]
                break
        return truncated.rstrip() + "..."

    def _should_filter_content(self, content: str, content_type: str) -> bool:
        """Drop metadata-only lines and ultra-long noise blocks."""
        if content_type in {"status", "presentation", "error", "tool"}:
            return False

        stripped = content.strip()
        if stripped.startswith("...") and stripped.endswith("..."):
            return True

        if len(stripped) > 1500 and self._is_web_search_content(stripped):
            return True

        return False

    def _is_web_search_content(self, content: str) -> bool:
        """Heuristic detection for web-search/tool snippets."""
        lowered = content.lower()
        markers = [
            "search query",
            "search result",
            "web search",
            "url:",
            "source:",
        ]
        return any(marker in lowered for marker in markers) or lowered.startswith("http")

    def _reset_web_cache(self, agent_id: str, truncate_history: bool = False):
        """Reset stored web search snippets after a status change."""
        if agent_id in self._recent_web_chunks:
            self._recent_web_chunks[agent_id].clear()

        if truncate_history:
            with self._buffer_lock:
                buf = self._buffers.get(agent_id, [])
                if buf:
                    trimmed: List[Dict[str, Any]] = []
                    web_count = 0
                    for entry in reversed(buf):
                        if self._is_web_search_content(entry.get("content", "")):
                            web_count += 1
                            if web_count > self.max_web_lines_on_status_change:
                                continue
                        trimmed.append(entry)
                    trimmed.reverse()
                    self._buffers[agent_id] = trimmed

    def _format_vote_results(self, vote_results: Dict[str, Any]) -> str:
        """Turn vote results dict into a readable multiline string for Textual modal."""
        if not vote_results:
            return "No vote data is available yet."

        lines = ["🗳️ Vote Results", "=" * 40]
        vote_counts = vote_results.get("vote_counts", {})
        winner = vote_results.get("winner")
        is_tie = vote_results.get("is_tie", False)

        if vote_counts:
            lines.append("\n📊 Vote Count:")
            for agent_id, count in sorted(vote_counts.items(), key=lambda item: item[1], reverse=True):
                prefix = "🏆 " if agent_id == winner else "   "
                tie_note = " (tie-broken)" if is_tie and agent_id == winner else ""
                lines.append(f"{prefix}{agent_id}: {count} vote{'s' if count != 1 else ''}{tie_note}")

        voter_details = vote_results.get("voter_details", {})
        if voter_details:
            lines.append("\n🔍 Rationale:")
            for voted_for, voters in voter_details.items():
                lines.append(f"→ {voted_for}")
                for detail in voters:
                    reason = detail.get("reason", "").strip()
                    voter = detail.get("voter", "unknown")
                    lines.append(f'   • {voter}: "{reason}"')

        total_votes = vote_results.get("total_votes", 0)
        agents_voted = vote_results.get("agents_voted", 0)
        lines.append(f"\n📈 Participation: {agents_voted}/{total_votes} agents voted")
        if is_tie:
            lines.append("⚖️  Tie broken by coordinator ordering")

        mapping = vote_results.get("agent_mapping", {})
        if mapping:
            lines.append("\n🔀 Agent Mapping:")
            for anon_id, real_id in mapping.items():
                lines.append(f"   {anon_id} → {real_id}")

        return "\n".join(lines)

    def _format_coordination_table(self, builder: Any) -> str:
        """Compose summary metadata plus plain-text table for Textual modal."""
        table_text = builder.generate_event_table()
        metadata = builder.session_metadata if hasattr(builder, "session_metadata") else {}
        lines = ["📋 Coordination Session", "=" * 40]
        if metadata:
            question = metadata.get("user_prompt") or ""
            if question:
                lines.append(f"💡 Question: {question}")
            final_winner = metadata.get("final_winner")
            if final_winner:
                lines.append(f"🏆 Winner: {final_winner}")
            start = metadata.get("start_time")
            end = metadata.get("end_time")
            if start and end:
                lines.append(f"⏱️  Duration: {start} → {end}")
        lines.append("\n" + table_text)
        lines.append("\nTip: Use the mouse wheel or drag the scrollbar to explore this view.")
        return "\n".join(lines)

    def _persist_final_presentation(self, content: str, selected_agent: Optional[str], vote_results: Optional[Dict[str, Any]]):
        """Persist final presentation to files with latest pointer."""
        header = ["=== FINAL PRESENTATION ==="]
        if selected_agent:
            header.append(f"Selected Agent: {selected_agent}")
        if vote_results:
            header.append(f"Vote Results: {vote_results}")
        header.append("")  # blank line
        final_text = "\n".join(header) + f"{content}\n"

        targets: List[Path] = []
        if selected_agent:
            agent_file = self.output_dir / f"final_presentation_{selected_agent}.txt"
            self.final_presentation_file = agent_file
            self.final_presentation_latest = self.output_dir / f"final_presentation_{selected_agent}_latest.txt"
            targets.append(agent_file)
        else:
            if self.final_presentation_file is None:
                self.final_presentation_file = self.output_dir / "final_presentation.txt"
            if self.final_presentation_latest is None:
                self.final_presentation_latest = self.output_dir / "final_presentation_latest.txt"
            targets.append(self.final_presentation_file)

        for path in targets:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(final_text)
            except OSError as exc:
                logger.error(f"Failed to persist final presentation to {path}: {exc}")

        if self.final_presentation_latest:
            try:
                if self.final_presentation_latest.exists() or self.final_presentation_latest.is_symlink():
                    self.final_presentation_latest.unlink()
                self.final_presentation_latest.symlink_to(targets[-1].name)
            except (OSError, NotImplementedError) as exc:
                logger.warning(f"Failed to create final presentation symlink at {self.final_presentation_latest}: {exc}")


# Textual App Implementation
if TEXTUAL_AVAILABLE:
    from textual.binding import Binding
    from textual.widgets import ListItem, ListView

    def keyboard_action(func):
        """Decorator to skip action when keyboard is locked."""

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if self._keyboard_locked():
                return
            return func(self, *args, **kwargs)

        return wrapper

    class StatusBarEventsClicked(Message):
        """Message emitted when the events counter in StatusBar is clicked."""

    class StatusBar(Widget):
        """Persistent status bar showing orchestration state at the bottom of the TUI."""

        DEFAULT_CSS = """
        StatusBar {
            dock: bottom;
            height: 1;
            background: $surface;
            color: $text;
            padding: 0 1;
            layout: horizontal;
        }
        """

        def __init__(self, agent_ids: List[str] | None = None):
            super().__init__(id="status_bar")
            self._vote_counts: Dict[str, int] = {}
            self._current_phase = "idle"
            self._event_count = 0
            self._start_time: float | None = None
            self._timer_interval = None
            self._agent_ids = agent_ids or []
            # Initialize vote counts to 0 for all agents
            for agent_id in self._agent_ids:
                self._vote_counts[agent_id] = 0

        def compose(self) -> ComposeResult:
            """Create the status bar layout with phase, votes, events, and timer."""
            yield Static("⏳ Idle", id="status_phase")
            yield Static("", id="status_votes")
            yield Static("📋 0 events", id="status_events", classes="clickable")
            yield Static("⏱️ 0:00", id="status_timer")

        def on_click(self, event: events.Click) -> None:
            """Handle click on the events counter to open events modal."""
            # Check if click was on the events element
            target = event.target
            if target and hasattr(target, "id") and target.id == "status_events":
                self.post_message(StatusBarEventsClicked())

        def update_phase(self, phase: str) -> None:
            """Update the phase indicator."""
            self._current_phase = phase
            # Map workflow phases to display
            phase_icons = {
                "idle": "⏳ Idle",
                "coordinating": "🔄 Coordinating",
                "initial_answer": "✏️ Answering",
                "enforcement": "🗳️ Voting",
                "presenting": "🎯 Presenting",
                "presentation": "🎯 Presenting",
            }
            display_text = phase_icons.get(phase, f"📋 {phase.title()}")

            try:
                phase_widget = self.query_one("#status_phase", Static)
                phase_widget.update(display_text)
            except Exception:
                pass  # Widget not mounted yet

            # Update phase-based styling
            self.remove_class("phase-idle")
            self.remove_class("phase-initial")
            self.remove_class("phase-enforcement")
            self.remove_class("phase-presentation")
            if phase in ("initial_answer", "coordinating"):
                self.add_class("phase-initial")
            elif phase == "enforcement":
                self.add_class("phase-enforcement")
            elif phase in ("presenting", "presentation"):
                self.add_class("phase-presentation")
            else:
                self.add_class("phase-idle")

        def add_vote(self, voted_for: str) -> None:
            """Increment vote count for an agent."""
            if voted_for not in self._vote_counts:
                self._vote_counts[voted_for] = 0
            self._vote_counts[voted_for] += 1
            self._update_votes_display()

        def update_votes(self, vote_counts: Dict[str, int]) -> None:
            """Update all vote counts at once."""
            self._vote_counts = vote_counts.copy()
            self._update_votes_display()

        def _update_votes_display(self) -> None:
            """Update the votes display widget."""
            if not self._vote_counts or all(v == 0 for v in self._vote_counts.values()):
                display_text = ""
            else:
                # Format as "A:2 B:1" - use first character of agent ID
                parts = []
                for agent_id, count in sorted(self._vote_counts.items()):
                    if count > 0:
                        # Use first character or first 3 chars if agent ID is long
                        short_id = agent_id[0].upper() if len(agent_id) <= 3 else agent_id[:3]
                        parts.append(f"{short_id}:{count}")
                display_text = "🗳️ " + " ".join(parts) if parts else ""

            try:
                votes_widget = self.query_one("#status_votes", Static)
                votes_widget.update(display_text)
            except Exception:
                pass  # Widget not mounted yet

        def add_event(self) -> None:
            """Increment the event counter."""
            self._event_count += 1
            self._update_events_display()

        def _update_events_display(self) -> None:
            """Update the events counter display."""
            display_text = f"📋 {self._event_count} events"
            try:
                events_widget = self.query_one("#status_events", Static)
                events_widget.update(display_text)
            except Exception:
                pass  # Widget not mounted yet

        def start_timer(self) -> None:
            """Start the elapsed timer."""
            self._start_time = time.time()
            self._schedule_timer_update()

        def _schedule_timer_update(self) -> None:
            """Schedule the next timer update."""
            if self._start_time is not None:
                self._timer_interval = self.set_interval(1.0, self._update_timer)

        def _update_timer(self) -> None:
            """Update the timer display."""
            if self._start_time is None:
                return
            elapsed = time.time() - self._start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            display_text = f"⏱️ {minutes}:{seconds:02d}"
            try:
                timer_widget = self.query_one("#status_timer", Static)
                timer_widget.update(display_text)
            except Exception:
                pass  # Widget not mounted yet

        def stop_timer(self) -> None:
            """Stop the timer updates."""
            if self._timer_interval:
                self._timer_interval.stop()
                self._timer_interval = None

        def reset(self) -> None:
            """Reset the status bar to initial state."""
            self._vote_counts = {agent_id: 0 for agent_id in self._agent_ids}
            self._event_count = 0
            self._start_time = None
            self.stop_timer()
            self.update_phase("idle")
            self._update_votes_display()
            self._update_events_display()
            try:
                timer_widget = self.query_one("#status_timer", Static)
                timer_widget.update("⏱️ 0:00")
            except Exception:
                pass

    class BaseModal(ModalScreen):
        """Base modal with common dismiss behavior for ESC and close buttons."""

        def on_button_pressed(self, event: Button.Pressed):
            if event.button.id and (event.button.id.startswith("close") or event.button.id == "cancel_button"):
                self.dismiss()

        def on_key(self, event: events.Key):
            if event.key == "escape":
                self.dismiss()
                event.stop()

    class TextualApp(App):
        """Main Textual application for MassGen coordination."""

        THEMES_DIR = Path(__file__).parent / "textual_themes"
        CSS_PATH = str(THEMES_DIR / "dark.tcss")

        BINDINGS = [
            Binding("tab", "next_agent", "Next"),
            Binding("shift+tab", "prev_agent", "Prev"),
            Binding("s", "open_system_status", "Status"),
            Binding("o", "open_orchestrator", "Events"),
            Binding("v", "open_vote_results", "Votes"),
            Binding("q", "quit", "Quit"),
            Binding("ctrl+q", "quit", "Quit", show=False),
            Binding("escape", "quit", "Quit", show=False),
        ]

        def __init__(
            self,
            display: TextualTerminalDisplay,
            question: str,
            buffers: Dict[str, List],
            buffer_lock: threading.Lock,
            buffer_flush_interval: float,
        ):
            css_path = self.THEMES_DIR / ("light.tcss" if display.theme == "light" else "dark.tcss")
            super().__init__(css_path=str(css_path))
            self.coordination_display = display
            self.question = question
            self._buffers = buffers
            self._buffer_lock = buffer_lock
            self.buffer_flush_interval = buffer_flush_interval
            self._keyboard_interactive_mode = display._keyboard_interactive_mode

            self.agent_widgets = {}
            self.header_widget = None
            self.footer_widget = None
            self.post_eval_panel = None
            self.final_stream_panel = None
            self.safe_indicator = None
            self._tab_bar: Optional[AgentTabBar] = None
            self._active_agent_id: Optional[str] = None
            self._welcome_screen: Optional["WelcomeScreen"] = None
            self._status_bar: Optional["StatusBar"] = None
            # Show welcome if no real question (detect placeholder strings)
            is_placeholder = not question or question.lower().startswith("welcome")
            self._showing_welcome = is_placeholder

            self.current_agent_index = 0
            self._pending_flush = False
            self._resize_debounce_handle = None
            self._thread_id: Optional[int] = None
            self._orchestrator_events: List[str] = []
            self._input_handler: Optional[Callable[[str], None]] = None

            if not self._keyboard_interactive_mode:
                self.BINDINGS = []

        def _keyboard_locked(self) -> bool:
            """Return True when keyboard input should be ignored."""
            return self.coordination_display.safe_keyboard_mode or not self._keyboard_interactive_mode

        def compose(self) -> ComposeResult:
            """Compose the UI layout with adaptive agent arrangement."""
            num_agents = len(self.coordination_display.agent_ids)
            agents_info_list = []
            # Use agent_models dict passed at display creation time
            agent_models = getattr(self.coordination_display, "agent_models", {})
            for agent_id in self.coordination_display.agent_ids:
                agent_info = agent_id
                # Get model from agent_models dict (populated at display creation)
                if agent_id in agent_models and agent_models[agent_id]:
                    model = agent_models[agent_id]
                    agent_info = f"{agent_id} ({model})"
                agents_info_list.append(agent_info)

            session_id = getattr(self.coordination_display, "session_id", None)
            turn = getattr(self.coordination_display, "current_turn", 1)
            mode = "Single Agent" if num_agents == 1 else "Multi-Agent"

            # Welcome screen (shown initially, hidden when session starts)
            self._welcome_screen = WelcomeScreen(agents_info_list)
            if not self._showing_welcome:
                self._welcome_screen.add_class("hidden")
            yield self._welcome_screen

            # Header (hidden during welcome)
            self.header_widget = HeaderWidget(
                question=self.question,
                session_id=session_id,
                turn=turn,
                agents_info=agents_info_list,
                mode=mode,
            )
            if self._showing_welcome:
                self.header_widget.add_class("hidden")
            yield self.header_widget

            # Create tab bar for agent switching (hidden during welcome)
            agent_ids = self.coordination_display.agent_ids
            self._tab_bar = AgentTabBar(agent_ids, id="agent_tab_bar")
            if self._showing_welcome:
                self._tab_bar.add_class("hidden")
            yield self._tab_bar

            # Set initial active agent
            self._active_agent_id = agent_ids[0] if agent_ids else None

            # Main container with agent panels (hidden during welcome)
            with Container(id="main_container", classes="hidden" if self._showing_welcome else ""):
                with Container(id="agents_container"):
                    for idx, agent_id in enumerate(agent_ids):
                        # Only first agent is visible, rest are hidden
                        is_hidden = idx > 0
                        agent_widget = AgentPanel(agent_id, self.coordination_display, idx + 1)
                        if is_hidden:
                            agent_widget.add_class("hidden")
                        self.agent_widgets[agent_id] = agent_widget
                        yield agent_widget

            self.post_eval_panel = PostEvaluationPanel()
            yield self.post_eval_panel

            self.final_stream_panel = FinalStreamPanel()
            yield self.final_stream_panel

            self.safe_indicator = Label("", id="safe_indicator")
            yield self.safe_indicator

            # Status bar showing phase, votes, events, timer (hidden during welcome)
            self._status_bar = StatusBar(agent_ids=agent_ids)
            if self._showing_welcome:
                self._status_bar.add_class("hidden")
            yield self._status_bar

            self.question_input = Input(
                placeholder="Type your question or /help for commands...",
                id="question_input",
            )
            yield self.question_input

            self.footer_widget = Footer()
            yield self.footer_widget

        def _get_layout_class(self, num_agents: int) -> str:
            """Return CSS class for adaptive layout based on agent count."""
            if num_agents == 1:
                return "single-agent"
            elif num_agents == 2:
                return "two-agents"
            elif num_agents == 3:
                return "three-agents"
            else:
                return "many-agents"

        async def on_mount(self):
            """Set up periodic buffer flushing when app starts."""
            self._thread_id = threading.get_ident()
            self.coordination_display._app_ready.set()
            self.set_interval(self.buffer_flush_interval, self._flush_buffers)
            if self.coordination_display.restart_reason and self.header_widget:
                self.header_widget.show_restart_context(
                    self.coordination_display.restart_reason,
                    self.coordination_display.restart_instructions or "",
                )
            self._update_safe_indicator()

        def _update_safe_indicator(self):
            """Show/hide safe keyboard status in footer area."""
            if not self.safe_indicator:
                return
            if self.coordination_display.safe_keyboard_mode:
                self.safe_indicator.update("🔒 Safe keys: ON")
                self.safe_indicator.styles.display = "block"
            elif not self._keyboard_interactive_mode:
                self.safe_indicator.update("⌨ Keyboard input disabled")
                self.safe_indicator.styles.display = "block"
            else:
                self.safe_indicator.update("")
                self.safe_indicator.styles.display = "none"

        def set_input_handler(self, handler: Callable[[str], None]) -> None:
            """Set the input handler callback for controller integration."""
            self._input_handler = handler

        def _dismiss_welcome(self) -> None:
            """Dismiss the welcome screen and show the main UI."""
            if not self._showing_welcome:
                return
            self._showing_welcome = False

            # Hide welcome screen
            if self._welcome_screen:
                self._welcome_screen.add_class("hidden")

            # Show header, tab bar, main container, and status bar
            if self.header_widget:
                self.header_widget.remove_class("hidden")
            if self._tab_bar:
                self._tab_bar.remove_class("hidden")
            if self._status_bar:
                self._status_bar.remove_class("hidden")
                self._status_bar.start_timer()
            try:
                main_container = self.query_one("#main_container", Container)
                main_container.remove_class("hidden")
            except Exception:
                pass

        def on_input_submitted(self, event: Input.Submitted) -> None:
            """Handle user input submission - delegate to controller."""
            text = event.value.strip()
            if not text:
                return

            self.question_input.clear()

            # Dismiss welcome screen on first real input
            if self._showing_welcome and not text.startswith("/"):
                self._dismiss_welcome()

            if self._input_handler:
                self._input_handler(text)
                if not text.startswith("/"):
                    try:
                        main_container = self.query_one("#main_container", Container)
                        main_container.remove_class("hidden")
                        if self.header_widget:
                            self.header_widget.update_question(text)
                    except Exception:
                        pass
                return

            if text.startswith("/"):
                self._handle_slash_command(text)
                return

            main_container = self.query_one("#main_container", Container)
            main_container.remove_class("hidden")

            if self.header_widget:
                self.header_widget.update_question(text)

        def _handle_slash_command(self, command: str) -> None:
            """Handle slash commands within the TUI using unified SlashCommandDispatcher."""
            try:
                from massgen.frontend.interactive_controller import (
                    SessionContext,
                    SlashCommandDispatcher,
                )

                context = SessionContext(
                    session_id=getattr(self.coordination_display, "session_id", None),
                    current_turn=getattr(self.coordination_display, "current_turn", 0),
                    agents={},
                )

                dispatcher = SlashCommandDispatcher(context=context, adapter=None)
                result = dispatcher.dispatch(command)

                if result.should_exit:
                    self.exit()
                    return

                if result.reset_ui_view:
                    self._reset_agent_panels()

                if result.ui_action == "show_help":
                    self._show_help_modal()
                elif result.ui_action == "show_status":
                    self._show_system_status_modal()
                elif result.ui_action == "show_events":
                    self._show_orchestrator_modal()
                elif result.ui_action == "show_vote":
                    self.action_open_vote_results()
                elif result.ui_action == "show_turn_inspection":
                    self.action_agent_selector()
                elif result.ui_action == "list_all_turns":
                    self.action_agent_selector()
                elif result.ui_action == "cancel_turn":
                    self.coordination_display.request_cancellation()
                elif result.ui_action == "prompt_context_paths":
                    self.notify("Context path modification not available in Textual mode.", severity="warning")
                elif result.message and not result.ui_action:
                    self.notify(result.message, severity="information" if result.handled else "warning")

                if not result.handled:
                    self.notify(result.message or f"Unknown command: {command}", severity="warning")

            except ImportError:
                cmd = command.lower().strip()
                if cmd in ("/help", "/h", "/?"):
                    self._show_help_modal()
                elif cmd in ("/quit", "/q", "/exit"):
                    self.exit()
                elif cmd in ("/reset", "/clear"):
                    self._reset_agent_panels()
                elif cmd.startswith("/inspect"):
                    self.action_agent_selector()
                elif cmd in ("/status", "/s"):
                    self._show_system_status_modal()
                elif cmd in ("/events", "/o"):
                    self._show_orchestrator_modal()
                elif cmd in ("/vote", "/v"):
                    self.action_open_vote_results()
                else:
                    self.notify(f"Unknown command: {command}", severity="warning")

        def _show_help_modal(self) -> None:
            """Show help information in a modal."""
            try:
                from massgen.frontend.interactive_controller import (
                    SlashCommandDispatcher,
                )

                command_help = SlashCommandDispatcher.build_help_text()
            except ImportError:
                command_help = "Help unavailable."

            help_text = f"""MassGen Textual UI Commands

SLASH COMMANDS:
{command_help}

KEYBOARD SHORTCUTS:
  Tab/Shift+Tab   - Navigate agents
  s               - System status log
  o               - Orchestrator events
  i               - Agent selector
  c               - Coordination table
  v               - Vote results
  Ctrl+Q          - Quit
  Ctrl+K          - Toggle safe keyboard mode

Type your question and press Enter to ask the agents.
"""
            self._show_modal_async(TextContentModal("MassGen Help", help_text))

        def _reset_agent_panels(self) -> None:
            """Reset agent panels for new question."""
            for agent_id, widget in self.agent_widgets.items():
                widget.content_log.clear()
                widget.update_status("waiting")
                widget._line_buffer = ""
                widget.current_line_label.update("")
            self.notify("Agent panels reset", severity="information")

        async def _flush_buffers(self):
            """Flush buffered content to widgets."""
            self._pending_flush = False
            all_updates = []
            for agent_id in self.coordination_display.agent_ids:
                with self._buffer_lock:
                    if not self._buffers[agent_id]:
                        continue
                    buffer_copy = self._buffers[agent_id].copy()
                    self._buffers[agent_id].clear()

                if buffer_copy and agent_id in self.agent_widgets:
                    all_updates.append((agent_id, buffer_copy))

            if all_updates:
                with self.batch_update():
                    for agent_id, buffer_copy in all_updates:
                        for item in buffer_copy:
                            await self.update_agent_widget(
                                agent_id,
                                item["content"],
                                item.get("type", "thinking"),
                            )
                            if item.get("force_jump"):
                                widget = self.agent_widgets.get(agent_id)
                                if widget:
                                    widget.jump_to_latest()

        def request_flush(self):
            """Request a near-immediate flush (debounced)."""
            if self._pending_flush:
                return
            self._pending_flush = True
            try:
                if threading.get_ident() == getattr(self, "_thread_id", None):
                    self.call_later(self._flush_buffers)
                else:
                    self.call_from_thread(self._flush_buffers)
            except Exception:
                self._pending_flush = False

        def _show_modal_async(self, modal: ModalScreen) -> None:
            """Display a modal screen asynchronously."""

            async def _show():
                await self.push_screen(modal)

            self.call_later(lambda: self.run_worker(_show()))

        async def update_agent_widget(self, agent_id: str, content: str, content_type: str):
            """Update agent widget with content."""
            if agent_id in self.agent_widgets:
                self.agent_widgets[agent_id].add_content(content, content_type)

        def update_agent_status(self, agent_id: str, status: str):
            """Update agent status."""
            if agent_id in self.agent_widgets:
                self.agent_widgets[agent_id].update_status(status)
                # Only jump to latest if this is the active agent
                if agent_id == self._active_agent_id:
                    self.agent_widgets[agent_id].jump_to_latest()
            # Also update the tab bar status badge
            if self._tab_bar:
                self._tab_bar.update_agent_status(agent_id, status)

        def add_orchestrator_event(self, event: str):
            """Add orchestrator event to internal tracking."""
            timestamp = datetime.now().strftime("%H:%M:%S")
            self._orchestrator_events.append(f"{timestamp} {event}")

        def show_final_presentation(
            self,
            answer: str,
            vote_results=None,
            selected_agent=None,
        ):
            """Display final answer modal with flush effect."""
            if not selected_agent:
                return
            if self.final_stream_panel:
                self.final_stream_panel.begin(selected_agent, vote_results or {})
                if answer:
                    self.final_stream_panel.append_chunk(answer)
                self.final_stream_panel.end()

        def show_post_evaluation(self, content: str, agent_id: str):
            """Show post-evaluation content."""
            if self.post_eval_panel:
                lines = list(self.coordination_display._post_evaluation_lines)
                self.post_eval_panel.update_lines(agent_id, lines)
            self.add_orchestrator_event(f"[POST-EVALUATION] {agent_id}: {content}")
            if self.final_stream_panel:
                self.final_stream_panel.end()

        def begin_final_stream(self, agent_id: str, vote_results: Dict[str, Any]):
            """Show streaming panel when the final agent starts presenting."""
            if self.final_stream_panel:
                self.final_stream_panel.begin(agent_id, vote_results)

        def update_final_stream(self, chunk: str):
            """Append streaming chunks to the panel."""
            if self.final_stream_panel:
                self.final_stream_panel.append_chunk(chunk)

        def end_final_stream(self):
            """Hide streaming panel after presentation ends."""
            if self.final_stream_panel:
                self.final_stream_panel.end()
            if self.post_eval_panel and not self.coordination_display._post_evaluation_lines:
                self.post_eval_panel.hide()

        # =====================================================================
        # Multi-turn Lifecycle Methods
        # =====================================================================

        def update_turn_header(self, turn: int, question: str):
            """Update the header with new turn number and question.

            Args:
                turn: The turn number (1-indexed).
                question: The user's question for this turn.
            """
            try:
                main_container = self.query_one("#main_container", Container)
                main_container.remove_class("hidden")
            except Exception:
                pass
            if self.header_widget:
                self.header_widget.update_question(question)
                self.header_widget.update_turn(turn)
            if turn > 1:
                separator = f"\n{'='*50}\n   TURN {turn}\n{'='*50}\n"
                for agent_id, widget in self.agent_widgets.items():
                    if hasattr(widget, "content_log"):
                        widget.content_log.write(separator)

        def set_input_enabled(self, enabled: bool):
            """Enable or disable the input widget.

            Args:
                enabled: True to enable input, False to disable.
            """
            if hasattr(self, "question_input") and self.question_input:
                self.question_input.disabled = not enabled
                if enabled:
                    self.question_input.focus()

        def show_restart_banner(
            self,
            reason: str,
            instructions: str,
            attempt: int,
            max_attempts: int,
        ):
            """Show restart banner in header and all agent panels."""
            if self.header_widget:
                self.header_widget.show_restart_banner(
                    reason,
                    instructions,
                    attempt,
                    max_attempts,
                )

            # Also show prominent restart separator in ALL agent panels
            for agent_id, panel in self.agent_widgets.items():
                panel.show_restart_separator(attempt, reason)

        def show_restart_context(self, reason: str, instructions: str):
            """Show restart context."""
            if self.header_widget:
                self.header_widget.show_restart_context(reason, instructions)

        def display_vote_results(self, formatted_results: str):
            """Display vote results."""
            self.add_orchestrator_event("🗳️ Voting complete. Press 'v' to inspect details.")
            self._latest_vote_results_text = formatted_results
            self._show_modal_async(VoteResultsModal(formatted_results))

        def display_coordination_table(self, table_text: str):
            """Display coordination table."""
            self._show_modal_async(CoordinationTableModal(table_text))

        def show_agent_selector(self):
            """Show agent selector modal."""
            modal = AgentSelectorModal(
                self.coordination_display.agent_ids,
                self.coordination_display,
                self,
            )
            self.push_screen(modal)

        @keyboard_action
        def action_next_agent(self):
            """Switch to next agent tab."""
            if self._tab_bar:
                next_agent = self._tab_bar.get_next_agent()
                if next_agent:
                    self._switch_to_agent(next_agent)

        @keyboard_action
        def action_prev_agent(self):
            """Switch to previous agent tab."""
            if self._tab_bar:
                prev_agent = self._tab_bar.get_previous_agent()
                if prev_agent:
                    self._switch_to_agent(prev_agent)

        def _switch_to_agent(self, agent_id: str) -> None:
            """Switch the visible agent tab.

            Args:
                agent_id: The agent ID to switch to.
            """
            if agent_id == self._active_agent_id:
                return

            # Hide current panel
            if self._active_agent_id and self._active_agent_id in self.agent_widgets:
                self.agent_widgets[self._active_agent_id].add_class("hidden")

            # Show new panel
            if agent_id in self.agent_widgets:
                self.agent_widgets[agent_id].remove_class("hidden")
                self.agent_widgets[agent_id].focus()

            # Update tab bar
            if self._tab_bar:
                self._tab_bar.set_active(agent_id)

            self._active_agent_id = agent_id

            # Update current_agent_index for compatibility with existing methods
            try:
                self.current_agent_index = self.coordination_display.agent_ids.index(agent_id)
            except ValueError:
                pass

        def on_agent_tab_changed(self, event: AgentTabChanged) -> None:
            """Handle tab click from AgentTabBar."""
            self._switch_to_agent(event.agent_id)
            event.stop()

        def on_tool_call_card_tool_card_clicked(self, event: ToolCallCard.ToolCardClicked) -> None:
            """Handle tool card click - show detail modal."""
            card = event.card
            modal = ToolDetailModal(
                tool_name=card.display_name,
                icon=card.icon,
                status=card.status,
                elapsed=card.elapsed_str,
                args=card.params,
                result=card.result,
                error=card.error,
            )
            self.push_screen(modal)
            event.stop()

        def action_toggle_safe_keyboard(self):
            """Toggle safe keyboard mode to ignore hotkeys."""
            self.coordination_display.safe_keyboard_mode = not self.coordination_display.safe_keyboard_mode
            status = "ON" if self.coordination_display.safe_keyboard_mode else "OFF"
            self.add_orchestrator_event(f"Keyboard safe mode {status}")
            self._update_safe_indicator()

        @keyboard_action
        def action_agent_selector(self):
            """Show agent selector."""
            self.show_agent_selector()

        @keyboard_action
        def action_coordination_table(self):
            """Show coordination table."""
            self._show_coordination_table_modal()

        @keyboard_action
        def action_quit(self):
            """Quit the application."""
            self.exit()

        @keyboard_action
        def action_open_vote_results(self):
            """Open vote results modal."""
            text = getattr(self, "_latest_vote_results_text", "")
            if not text:
                status = getattr(self.coordination_display, "_final_answer_metadata", {}) or {}
                text = self.coordination_display._format_vote_results(status.get("vote_results", {})) if hasattr(self.coordination_display, "_format_vote_results") else ""
            if not text.strip():
                text = "Vote results unavailable."
            self._show_modal_async(VoteResultsModal(text))

        @keyboard_action
        def action_open_system_status(self):
            """Open system status log."""
            self._show_system_status_modal()

        @keyboard_action
        def action_open_orchestrator(self):
            """Open orchestrator events modal."""
            self._show_orchestrator_modal()

        def _show_orchestrator_modal(self):
            """Display orchestrator events in a modal."""
            events_text = "\n".join(self._orchestrator_events) if self._orchestrator_events else "No events yet."
            self._show_modal_async(OrchestratorEventsModal(events_text))

        def on_status_bar_events_clicked(self, event: StatusBarEventsClicked) -> None:
            """Handle click on status bar events counter - opens orchestrator events modal."""
            self._show_orchestrator_modal()

        # === Status Bar Notification Methods ===

        def notify_vote(self, voter: str, voted_for: str) -> None:
            """Called when a vote is cast. Updates status bar and shows toast."""
            if self._status_bar:
                self._status_bar.add_vote(voted_for)
            self.notify(f"🗳️ {voter} → {voted_for}", timeout=3)

        def notify_phase(self, phase: str) -> None:
            """Called on phase change. Updates status bar phase indicator."""
            if self._status_bar:
                self._status_bar.update_phase(phase)

        def notify_completion(self, agent_id: str) -> None:
            """Called when an agent completes their work."""
            self.notify(f"✅ {agent_id} completed", severity="information", timeout=3)

        def notify_error(self, agent_id: str, error: str) -> None:
            """Called on agent error."""
            self.notify(f"❌ {agent_id}: {error}", severity="error", timeout=5)

        def add_status_bar_event(self) -> None:
            """Increment the event counter in the status bar."""
            if self._status_bar:
                self._status_bar.add_event()

        def update_status_bar_votes(self, vote_counts: Dict[str, int]) -> None:
            """Update all vote counts in the status bar at once."""
            if self._status_bar:
                self._status_bar.update_votes(vote_counts)

        def on_key(self, event: events.Key):
            """Map number keys directly to agent inspection, mirroring Rich UI."""
            if self._keyboard_locked():
                return

            key = event.character
            if not key:
                return

            if key.isdigit() and key != "0":
                idx = int(key) - 1
                if 0 <= idx < len(self.coordination_display.agent_ids):
                    agent_id = self.coordination_display.agent_ids[idx]
                    self._switch_to_agent(agent_id)
                    event.stop()
                    return

            if key.lower() == "s":
                self.action_open_system_status()
                event.stop()
                return

            if key.lower() == "o":
                self.action_open_orchestrator()
                event.stop()
                return

        def _show_coordination_table_modal(self):
            """Display coordination table in a modal."""
            table_text = self.coordination_display._format_coordination_table_from_orchestrator()
            self._show_modal_async(CoordinationTableModal(table_text))

        def _show_text_modal(self, path: Path, title: str):
            """Display file content in a modal."""
            content = ""
            try:
                if path.exists():
                    content = path.read_text(encoding="utf-8")
            except Exception:
                pass
            if not content:
                content = "Content unavailable."
            self._show_modal_async(TextContentModal(title, content))

        def _show_system_status_modal(self):
            """Display system status log in a modal."""
            content = ""
            status_path = self.coordination_display.system_status_file
            if status_path and Path(status_path).exists():
                try:
                    content = Path(status_path).read_text(encoding="utf-8")
                except Exception:
                    pass
            if not content:
                content = "System status log is empty or unavailable."
            self._show_modal_async(SystemStatusModal(content))

        def on_resize(self, event: events.Resize) -> None:
            """Refresh widgets when the terminal window is resized with debounce."""
            if self._resize_debounce_handle:
                try:
                    self._resize_debounce_handle.cancel()
                except Exception:
                    pass

            debounce_time = 0.15 if self.coordination_display._terminal_type in ("vscode", "windows_terminal") else 0.05
            try:
                self._resize_debounce_handle = self.set_timer(debounce_time, lambda: self.refresh(layout=True))
            except Exception:
                self.call_later(lambda: self.refresh(layout=True))

    # Widget implementations
    class WelcomeScreen(Container):
        """Welcome screen with ASCII logo shown on startup."""

        MASSGEN_LOGO = """\
   ███╗   ███╗  █████╗  ███████╗ ███████╗  ██████╗  ███████╗ ███╗   ██╗
   ████╗ ████║ ██╔══██╗ ██╔════╝ ██╔════╝ ██╔════╝  ██╔════╝ ████╗  ██║
   ██╔████╔██║ ███████║ ███████╗ ███████╗ ██║  ███╗ █████╗   ██╔██╗ ██║
   ██║╚██╔╝██║ ██╔══██║ ╚════██║ ╚════██║ ██║   ██║ ██╔══╝   ██║╚██╗██║
   ██║ ╚═╝ ██║ ██║  ██║ ███████║ ███████║ ╚██████╔╝ ███████╗ ██║ ╚████║
   ╚═╝     ╚═╝ ╚═╝  ╚═╝ ╚══════╝ ╚══════╝  ╚═════╝  ╚══════╝ ╚═╝  ╚═══╝"""

        def __init__(self, agents_info: list = None):
            super().__init__(id="welcome_screen")
            self.agents_info = agents_info or []

        def compose(self) -> ComposeResult:
            yield Label(self.MASSGEN_LOGO, id="welcome_logo")
            yield Label("🤖 Multi-Agent Collaboration System", id="welcome_tagline")
            # Show agent list
            if self.agents_info:
                agents_list = "  •  ".join(self.agents_info)
                yield Label(agents_list, id="welcome_agents")
            else:
                yield Label(f"Ready with {len(self.agents_info)} agents", id="welcome_agents")
            yield Label("Type your question below to begin...", id="welcome_hint")

    class HeaderWidget(Static):
        """Compact header widget showing minimal branding and session info."""

        def __init__(
            self,
            question: str,
            session_id: str = None,
            turn: int = 1,
            agents_info: list = None,
            mode: str = "Multi-Agent",
        ):
            super().__init__(id="header_widget")
            self.question = question
            self.session_id = session_id
            self.turn = turn
            self.agents_info = agents_info or []
            self.mode = mode

        def _build_status_line(self) -> str:
            """Build compact status line with optional question preview."""
            session_id_display = self.session_id or "new"
            num_agents = len(self.agents_info)
            base = f"🤖 MassGen | {num_agents} agents | Turn {self.turn}"

            # Add truncated question if available
            if self.question and self.question != "Welcome! Type your question below...":
                # Truncate question to fit in header (max ~40 chars)
                q = self.question[:40] + "..." if len(self.question) > 40 else self.question
                return f"{base} | 💬 {q}"
            return f"{base} | {session_id_display}"

        def compose(self) -> ComposeResult:
            yield Label(self._build_status_line(), id="status_line_label")

        def update_question(self, question: str) -> None:
            """Update the displayed question and refresh header."""
            self.question = question
            try:
                status_label = self.query_one("#status_line_label", Label)
                status_label.update(self._build_status_line())
            except Exception:
                pass

        def update_turn(self, turn: int) -> None:
            """Update the displayed turn number."""
            self.turn = turn
            try:
                status_label = self.query_one("#status_line_label", Label)
                status_label.update(self._build_status_line())
            except Exception:
                pass

        def show_restart_banner(
            self,
            reason: str,
            instructions: str,
            attempt: int,
            max_attempts: int,
        ):
            """Show restart banner."""
            banner_text = f"⚠️ RESTART ({attempt}/{max_attempts}): {reason}"
            try:
                status_label = self.query_one("#status_line_label", Label)
                status_label.update(banner_text)
            except Exception:
                pass

        def show_restart_context(self, reason: str, instructions: str):
            """Show restart context - handled via status line."""
            pass  # Restart info shown via show_restart_banner

    class AgentPanel(ScrollableContainer):
        """Panel for individual agent output."""

        def __init__(self, agent_id: str, display: TextualTerminalDisplay, key_index: int = 0):
            self.agent_id = agent_id
            self.coordination_display = display
            self.key_index = key_index
            self._dom_safe_id = self._make_dom_safe_id(agent_id)
            super().__init__(id=f"agent_{self._dom_safe_id}")
            self.status = "waiting"
            self._start_time: Optional[datetime] = None
            self._has_content = False  # Track if we've received any content

            # Legacy RichLog for fallback
            self.content_log = RichLog(
                id=f"log_{self._dom_safe_id}",
                highlight=self.coordination_display.enable_syntax_highlighting,
                markup=True,
                wrap=True,
            )
            self._line_buffer = ""
            self.current_line_label = Label("", classes="streaming_label")
            self._header_dom_id = f"header_{self._dom_safe_id}"
            self._loading_id = f"loading_{self._dom_safe_id}"

            # New section-based content handlers
            self._tool_handler = ToolContentHandler()
            self._thinking_handler = ThinkingContentHandler()

            # Section widget IDs - using timeline for chronological view
            self._timeline_section_id = f"timeline_section_{self._dom_safe_id}"
            # Keep old IDs as aliases for compatibility
            self._tool_section_id = self._timeline_section_id
            self._thinking_section_id = self._timeline_section_id
            self._status_badge_id = f"status_badge_{self._dom_safe_id}"
            self._completion_footer_id = f"completion_footer_{self._dom_safe_id}"

            # Legacy tool tracking (kept for restart detection)
            self._pending_tool: Optional[dict] = None
            self._tool_row_count = 0
            self._reasoning_header_shown = False

            # Session/restart tracking
            self._session_completed = False
            self._session_count = 1
            self._presentation_shown = False

        def compose(self) -> ComposeResult:
            with Vertical():
                yield Label(
                    self._header_text(),
                    id=self._header_dom_id,
                )
                # Loading indicator - centered, shown when waiting with no content
                with Container(id=self._loading_id, classes="loading-container"):
                    yield Label("⏳ Waiting for agent...", classes="loading-text")

                # Chronological timeline layout - tools and text interleaved
                yield TimelineSection(id=self._timeline_section_id)
                yield CompletionFooter(id=self._completion_footer_id)

                # Legacy RichLog kept for fallback/compatibility
                yield self.content_log
                yield self.current_line_label

        def _hide_loading(self):
            """Hide the loading indicator when content arrives."""
            if not self._has_content:
                self._has_content = True
                try:
                    loading = self.query_one(f"#{self._loading_id}")
                    loading.add_class("hidden")
                except Exception:
                    pass

        def _update_loading_text(self, text: str):
            """Update the loading indicator text."""
            try:
                loading = self.query_one(f"#{self._loading_id} .loading-text")
                loading.update(text)
            except Exception:
                pass

        def _make_full_width_bar(self, content: str, style: str) -> Text:
            """Create a full-width bar with background color spanning the entire display.

            Args:
                content: The text content
                style: Rich style string (including 'on #color' for background)

            Returns:
                Text object padded to full width with single line spacing
            """
            # Get terminal width dynamically - add extra padding to ensure full coverage
            try:
                width = self.app.size.width
                if width < 80:
                    width = 200
                else:
                    # Add extra width to account for any padding/margins and ensure full coverage
                    width = width + 50
            except Exception:
                width = 300  # Large fallback to ensure full coverage

            # Pad content to fill entire width and beyond
            padded = content.ljust(width)
            text = Text()
            # Always add a single blank line before for consistent spacing
            text.append("\n")
            text.append(padded, style=style)
            return text

        def _format_tool_line(self, parsed: dict, event: str) -> Text:
            """Format a tool event as a full-width bar with alternating colors.

            Design: Full-width bars with clear visual separation
            - Each tool line spans the full width
            - Alternating background colors for row separation
            - Special colors for success/error states

            Args:
                parsed: Parsed tool message dict
                event: Event type (start, complete, failed, etc.)

            Returns:
                Styled Rich Text object
            """
            category = parsed.get("category", {"icon": "🔧", "color": "cyan", "category": "tool"})
            display_name = parsed.get("display_name", parsed.get("tool_name", "unknown"))
            icon = category["icon"]

            # Alternating row backgrounds for clear separation
            self._tool_row_count += 1
            is_odd_row = self._tool_row_count % 2 == 1
            bg_row_odd = "on #2d333b"  # Slightly lighter
            bg_row_even = "on #22272e"  # Slightly darker

            # Special backgrounds for status
            bg_success = "on #1c4532"  # Dark green
            bg_error = "on #4a1c1c"  # Dark red
            bg_warning = "on #4a4520"  # Dark yellow
            bg_injection = "on #2d2d4a"  # Dark purple/blue for injections
            bg_reminder = "on #4a3d2d"  # Dark orange for reminders

            # Get alternating background
            bg_alt = bg_row_odd if is_odd_row else bg_row_even

            if event == "start":
                # Track start time for this tool
                self._pending_tool = {
                    "name": parsed.get("tool_name"),
                    "start_time": datetime.now(),
                    "display_name": display_name,
                    "category": category,
                }
                # Reset reasoning header on new tool
                self._reasoning_header_shown = False
                # Format: full-width bar with icon + name (bold)
                content = f"  {icon}  {display_name}"
                return self._make_full_width_bar(content, f"bold white {bg_alt}")

            elif event == "complete":
                # Calculate elapsed time
                elapsed_str = ""
                if self._pending_tool and self._pending_tool.get("name") == parsed.get("tool_name"):
                    elapsed = (datetime.now() - self._pending_tool["start_time"]).total_seconds()
                    if elapsed < 60:
                        elapsed_str = f" ({elapsed:.1f}s)"
                    else:
                        mins = int(elapsed // 60)
                        secs = int(elapsed % 60)
                        elapsed_str = f" ({mins}m{secs}s)"
                    self._pending_tool = None

                # Format: success bar - always green background (bold)
                content = f"  ✓  {display_name} completed{elapsed_str}"
                return self._make_full_width_bar(content, f"bold white {bg_success}")

            elif event == "failed":
                error = parsed.get("error", "Unknown error")
                if len(error) > 50:
                    error = error[:50] + "..."
                elapsed_str = ""
                if self._pending_tool:
                    elapsed = (datetime.now() - self._pending_tool["start_time"]).total_seconds()
                    elapsed_str = f" ({elapsed:.1f}s)"
                    self._pending_tool = None

                # Format: error bar - always red background (bold)
                content = f"  ✗  {display_name} failed: {error}{elapsed_str}"
                return self._make_full_width_bar(content, f"bold white {bg_error}")

            elif event == "injection":
                # Cross-agent context sharing - prominent purple bar
                injection_content = parsed.get("content", "")
                preview = injection_content[:80] + "..." if len(injection_content) > 80 else injection_content
                content = f"  📥  Context Update: {preview}"
                return self._make_full_width_bar(content, f"bold white {bg_injection}")

            elif event == "reminder":
                # High priority task reminder - orange bar
                reminder_content = parsed.get("content", "")
                preview = reminder_content[:80] + "..." if len(reminder_content) > 80 else reminder_content
                content = f"  💡  Reminder: {preview}"
                return self._make_full_width_bar(content, f"bold white {bg_reminder}")

            elif event == "session_complete":
                # Session completed - green bar
                content = "  ✓  Session completed"
                return self._make_full_width_bar(content, f"bold white {bg_success}")

            elif event == "arguments":
                args = parsed.get("arguments", parsed.get("raw", ""))
                args_clean = _clean_tool_arguments(args)
                content = f"      └ {args_clean}"
                return self._make_full_width_bar(content, f"{bg_alt}")

            elif event == "status":
                status_type = parsed.get("status_type", "")
                raw = parsed.get("raw", "")
                if status_type == "connected":
                    clean = raw.replace("[MCP]", "").replace("✅", "").strip()
                    content = f"  ✓  {clean}"
                    return self._make_full_width_bar(content, f"bold white {bg_success}")
                elif status_type == "unavailable":
                    clean = raw.replace("[MCP]", "").replace("⚠️", "").strip()
                    content = f"  ⚠  {clean}"
                    return self._make_full_width_bar(content, f"bold yellow {bg_warning}")
                else:
                    content = f"  •  {raw}"
                    return self._make_full_width_bar(content, f"{bg_alt}")

            elif event == "progress":
                raw = parsed.get("raw", "")
                clean = raw.replace("⏳", "").strip()
                content = f"      ⏳ {clean}"
                return self._make_full_width_bar(content, f"italic {bg_alt}")

            else:
                # Unknown tool content
                raw = parsed.get("raw", "")

                # Check if it looks like results output
                if "MCP: Results" in raw or "Results for" in raw:
                    result_part = raw
                    if ": {" in raw:
                        result_part = raw[raw.index(": {") + 2 :]
                    elif "Results" in raw and "{" in raw:
                        result_part = raw[raw.index("{") :]
                    clean_result = _clean_tool_result(result_part)
                    content = f"      └ {clean_result}"
                    return self._make_full_width_bar(content, f"{bg_alt}")

                # Check if it's an arguments line
                if "Arguments:" in raw or "MCP: Arguments" in raw:
                    args_part = raw
                    if "Arguments:" in raw:
                        args_part = raw[raw.index("Arguments:") :]
                    clean_args = _clean_tool_arguments(args_part)
                    content = f"      └ {clean_args}"
                    return self._make_full_width_bar(content, f"{bg_alt}")

                # Check if it looks like raw dict/JSON output
                if "{" in raw and "}" in raw:
                    clean = _clean_tool_result(raw)
                    content = f"      └ {clean}"
                    return self._make_full_width_bar(content, f"{bg_alt}")

                # Clean common prefixes and truncate
                clean = raw.replace("🔧", "").replace("[MCP]", "").replace("[Custom Tool]", "").strip()
                if len(clean) > 80:
                    clean = clean[:80] + "..."
                content = f"  •  {clean}"
                return self._make_full_width_bar(content, f"{bg_alt}")

        def _format_restart_banner(self) -> Text:
            """Create a highly visible full-width restart banner."""
            content = " ⚡⚡⚡  RESTART  ⚡⚡⚡ "
            # Bright orange/red background, centered
            banner = "═" * 50 + content + "═" * 50
            return self._make_full_width_bar(banner, "bold white on #c53030")

        def _handle_tool_content(self, content: str):
            """Handle tool-related content by formatting as styled bars in RichLog.

            Uses full-width styled bars with status colors for clear visual hierarchy.
            """
            self._hide_loading()  # Hide loading when tool content arrives
            parsed = _parse_tool_message(content)
            event = parsed.get("event", "unknown")

            formatted = self._format_tool_line(parsed, event)
            self.content_log.write(formatted)

        def show_restart_separator(self, attempt: int = 1, reason: str = ""):
            """Show a highly visible restart separator in the content log."""
            # Reset tool row count for fresh alternation after restart
            self._tool_row_count = 0
            self._reasoning_header_shown = False

            # Get full width for the separator
            try:
                width = self.app.size.width + 50
            except Exception:
                width = 300

            # Build banner text
            banner_text = f"  ⚡  RESTART — ATTEMPT {attempt}  ⚡"
            if reason and reason != "New attempt":
                short_reason = reason[:50] + "..." if len(reason) > 50 else reason
                banner_text += f"  —  {short_reason}"

            # Create the full-width restart banner
            self.content_log.write(Text(""))  # Blank line before
            self.content_log.write(Text(""))  # Extra blank line
            self.content_log.write(Text("━" * width, style="bold #ff6b6b"))
            self.content_log.write(Text(banner_text.ljust(width), style="bold white on #d63031"))
            self.content_log.write(Text("━" * width, style="bold #ff6b6b"))
            self.content_log.write(Text(""))  # Blank line after  # Extra blank line  # Blank line after

        def add_content(self, content: str, content_type: str):
            """Add content to agent panel using section-based routing.

            Content is normalized and routed to appropriate sections:
            - Tool content -> ToolSection (collapsible tool cards)
            - Thinking/text -> ThinkingSection (streaming RichLog)
            - Status -> Updates status badge
            - Presentation -> ThinkingSection with completion footer
            - Restart -> Restart separator in ThinkingSection
            """
            self._hide_loading()  # Hide loading when any content arrives

            # Normalize content first
            normalized = ContentNormalizer.normalize(content, content_type)

            # Route based on detected content type
            if normalized.content_type.startswith("tool_"):
                self._add_tool_content(normalized, content, content_type)
            elif normalized.content_type == "status":
                self._add_status_content(normalized)
            elif normalized.content_type == "presentation":
                self._add_presentation_content(normalized)
            elif content_type == "restart":
                self._add_restart_content(content)
            elif normalized.content_type in ("thinking", "text"):
                self._add_thinking_content(normalized, content_type)
            else:
                # Fallback: route to thinking section if displayable
                if normalized.should_display:
                    self._add_thinking_content(normalized, content_type)

        def _add_tool_content(self, normalized, raw_content: str, raw_type: str):
            """Route tool content to TimelineSection (chronologically)."""
            # Check for session restart indicator
            is_session_start = ("Registered" in raw_content and "tools" in raw_content) or ("Connected to" in raw_content and "server" in raw_content)

            if is_session_start and self._presentation_shown:
                # New session starting after a presentation
                self._session_count += 1
                self._add_restart_content(f"attempt:{self._session_count} New attempt")
                self._presentation_shown = False
                self._session_completed = False
                self._tool_handler.reset()
                self._clear_timeline()

            # Process through handler
            tool_data = self._tool_handler.process(normalized)
            if not tool_data:
                return

            # Add or update tool card in TimelineSection (chronologically)
            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)

                if tool_data.status == "running":
                    # Check if this is an args update for existing tool
                    existing_card = timeline.get_tool(tool_data.tool_id)
                    if existing_card:
                        # Update existing card with args (both truncated and full)
                        if tool_data.args_summary:
                            existing_card.set_params(tool_data.args_summary, tool_data.args_full)
                    else:
                        # New tool started - add card to timeline
                        timeline.add_tool(tool_data)
                else:
                    # Tool completed/failed - update existing card
                    timeline.update_tool(tool_data.tool_id, tool_data)
            except Exception:
                # Fallback to legacy RichLog
                self._handle_tool_content(raw_content)

            self._line_buffer = ""
            self.current_line_label.update(Text(""))

        def _add_status_content(self, normalized):
            """Route status content to TimelineSection with subtle display."""
            if not normalized.should_display:
                return

            # Detect session completion for restart tracking
            if "completed" in normalized.cleaned_content.lower():
                self._session_completed = True
                self._show_completion_footer()

            # Add status to timeline as a subtle line
            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)
                timeline.add_text(f"● {normalized.cleaned_content}", style="dim cyan", text_class="status")
            except Exception:
                # Fallback
                status_bar = self._make_full_width_bar(f"  📊  {normalized.cleaned_content}", "bold yellow on #2d333b")
                self.content_log.write(status_bar)

            self._line_buffer = ""
            self.current_line_label.update(Text(""))

        def _add_presentation_content(self, normalized):
            """Route presentation content to TimelineSection."""
            if not normalized.should_display:
                return

            # Mark presentation shown for restart detection
            if "Providing answer" in normalized.original:
                self._presentation_shown = True
                self._show_completion_footer()

            # Add to timeline with response styling
            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)
                timeline.add_text(normalized.cleaned_content, style="bold #4ec9b0", text_class="response")
            except Exception:
                # Fallback
                self.content_log.write(Text(f"🎤 {normalized.cleaned_content}", style="magenta"))

            self._line_buffer = ""
            self.current_line_label.update(Text(""))

        def _add_restart_content(self, content: str):
            """Handle restart separator."""
            # Parse attempt number
            attempt = 1
            reason = content
            if "attempt:" in content:
                try:
                    parts = content.split("attempt:")
                    if len(parts) > 1:
                        attempt_part = parts[1].split()[0]
                        attempt = int(attempt_part)
                        reason = content.replace(f"attempt:{attempt}", "").strip()
                except (ValueError, IndexError):
                    pass

            # Add to timeline as separator
            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)
                label = f"⚡ RESTART — ATTEMPT {attempt}"
                if reason and reason != "New attempt":
                    short_reason = reason[:30] + "..." if len(reason) > 30 else reason
                    label += f" — {short_reason}"
                timeline.add_separator(label)

                # Hide completion footer for new attempt
                self._hide_completion_footer()
            except Exception:
                # Fallback to legacy method
                self.show_restart_separator(attempt, reason)

            self._line_buffer = ""
            self.current_line_label.update(Text(""))

        def _add_thinking_content(self, normalized, raw_type: str):
            """Route thinking/text content to TimelineSection.

            Coordination content (voting, reasoning about other agents) is
            routed to a collapsible ReasoningSection within the timeline.
            """
            # Process through handler for extra filtering
            cleaned = self._thinking_handler.process(normalized)
            if not cleaned:
                return

            # Check if this is coordination content
            is_coordination = getattr(normalized, "is_coordination", False)

            # Add to timeline
            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)

                # Handle line buffering for streaming
                def write_line(line: str):
                    if is_coordination:
                        # Route to collapsible reasoning section
                        timeline.add_reasoning(line)
                    elif raw_type == "thinking":
                        timeline.add_text(line, style="dim", text_class="thinking")
                    else:
                        timeline.add_text(line)

                self._line_buffer = _process_line_buffer(
                    self._line_buffer,
                    cleaned,
                    write_line,
                )
                self.current_line_label.update(Text(self._line_buffer))
            except Exception:
                # Fallback to legacy RichLog
                if raw_type == "thinking":
                    self._line_buffer = _process_line_buffer(
                        self._line_buffer,
                        cleaned,
                        lambda line: self.content_log.write(Text(f"     {line}", style="dim")),
                    )
                    self.current_line_label.update(Text(self._line_buffer, style="dim"))
                else:
                    self._line_buffer = _process_line_buffer(
                        self._line_buffer,
                        cleaned,
                        lambda line: self.content_log.write(Text(line)),
                    )
                    self.current_line_label.update(Text(self._line_buffer))

        def _clear_timeline(self):
            """Clear the timeline for a new session."""
            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)
                timeline.clear()
            except Exception:
                pass

        def _clear_tool_section(self):
            """Clear the tool section for a new session (legacy, calls _clear_timeline)."""
            self._clear_timeline()
            try:
                tool_section = self.query_one(f"#{self._tool_section_id}", ToolSection)
                tool_section.clear()
            except Exception:
                pass

        def _show_completion_footer(self):
            """Show the completion footer."""
            try:
                footer = self.query_one(f"#{self._completion_footer_id}", CompletionFooter)
                footer.show_completed()
            except Exception:
                pass

        def _hide_completion_footer(self):
            """Hide the completion footer."""
            try:
                footer = self.query_one(f"#{self._completion_footer_id}", CompletionFooter)
                footer.hide()
            except Exception:
                pass

        def update_status(self, status: str):
            """Update agent status."""
            if self._line_buffer.strip():
                self.content_log.write(Text(self._line_buffer))
                self._line_buffer = ""
                self.current_line_label.update(Text(""))

            if status == "working" and self.status != "working":
                self._start_time = datetime.now()
                # Update loading text when working
                self._update_loading_text("🔄 Agent thinking...")
            elif status == "streaming":
                self._update_loading_text("📝 Agent responding...")
            elif status in ("completed", "error", "waiting"):
                self._start_time = None

            self.status = status
            self.remove_class("status-waiting", "status-working", "status-streaming", "status-completed", "status-error")
            self.add_class(f"status-{status}")

            header = self.query_one(f"#{self._header_dom_id}")
            header.update(self._header_text())

        def jump_to_latest(self):
            """Scroll to latest entry if supported."""
            try:
                self.content_log.scroll_end(animate=False)
            except Exception:
                try:
                    self.content_log.scroll_end()
                except Exception:
                    pass

        def _header_text(self) -> str:
            """Compose header text with backend metadata, keyboard hint, and elapsed time."""
            backend = self.coordination_display._get_agent_backend_name(self.agent_id)
            status_icon = self._status_icon(self.status)

            parts = [f"{status_icon} {self.agent_id}"]
            if backend and backend != "Unknown":
                parts.append(f"({backend})")
            if self.key_index and 1 <= self.key_index <= 9:
                parts.append(f"[{self.key_index}]")
            if self._start_time and self.status in ("working", "streaming"):
                elapsed = datetime.now() - self._start_time
                elapsed_str = self._format_elapsed(elapsed.total_seconds())
                parts.append(f"⏱{elapsed_str}")
            parts.append(f"[{self.status}]")

            return " ".join(parts)

        def _format_elapsed(self, seconds: float) -> str:
            """Format elapsed seconds into human-readable string."""
            if seconds < 60:
                return f"{int(seconds)}s"
            elif seconds < 3600:
                mins = int(seconds // 60)
                secs = int(seconds % 60)
                return f"{mins}m{secs}s"
            else:
                hours = int(seconds // 3600)
                mins = int((seconds % 3600) // 60)
                return f"{hours}h{mins}m"

        def _status_icon(self, status: str) -> str:
            """Return emoji (or fallback) for the given status."""
            icon_map = {
                "waiting": "⏳",
                "working": "🔄",
                "streaming": "📝",
                "completed": "✅",
                "error": "❌",
            }
            return self.coordination_display._get_icon(icon_map.get(status, "🤖"))

        def _make_dom_safe_id(self, raw_id: str) -> str:
            """Convert arbitrary agent IDs into Textual-safe DOM identifiers."""
            MAX_DOM_ID_LENGTH = 80

            truncated = raw_id[:MAX_DOM_ID_LENGTH] if len(raw_id) > MAX_DOM_ID_LENGTH else raw_id
            safe = re.sub(r"[^0-9a-zA-Z_-]", "_", truncated)

            if not safe:
                safe = "agent_default"

            if safe[0].isdigit():
                safe = f"agent_{safe}"

            base_safe = safe
            counter = 1
            used_ids = set(self.coordination_display._dom_id_mapping.values())

            while safe in used_ids:
                suffix = f"__{counter}"
                max_base_len = MAX_DOM_ID_LENGTH - len(suffix)
                safe = base_safe[:max_base_len] + suffix
                counter += 1

            if safe != base_safe:
                logger.debug(
                    f"DOM ID collision resolved for agent '{raw_id}': " f"'{base_safe}' -> '{safe}' (suffix added to avoid duplicate)",
                )

            self.coordination_display._dom_id_mapping[raw_id] = safe

            return safe

    class OrchestratorEventsModal(BaseModal):
        """Modal to display orchestrator events."""

        def __init__(self, events_text: str):
            super().__init__()
            self.events_text = events_text

        def compose(self) -> ComposeResult:
            with Container(id="orchestrator_modal_container"):
                yield Label("📋 Orchestrator Events", id="orchestrator_modal_header")
                yield Label("Press 'o' anytime to view events", id="orchestrator_hint")
                yield TextArea(self.events_text, id="orchestrator_events_content", read_only=True)
                yield Button("Close (ESC)", id="close_orchestrator_button")

    class AgentSelectorModal(BaseModal):
        """Interactive agent selection menu."""

        def __init__(self, agent_ids: List[str], display: TextualTerminalDisplay, app: "TextualApp"):
            super().__init__()
            self.agent_ids = agent_ids
            self.coordination_display = display
            self.app_ref = app

        def compose(self) -> ComposeResult:
            with Container(id="selector_container"):
                yield Label("Select an agent to view:", id="selector_header")

                items = [ListItem(Label(f"📄 View {agent_id}")) for agent_id in self.agent_ids]
                items.append(ListItem(Label("🎤 View Final Presentation Transcript")))
                items.append(ListItem(Label("📊 View System Status")))
                items.append(ListItem(Label("📋 View Coordination Table")))

                yield ListView(*items, id="agent_list")
                yield Button("Cancel (ESC)", id="cancel_button")

        def on_list_view_selected(self, event: ListView.Selected):
            """Handle selection from list."""
            index = event.list_view.index
            if index < len(self.agent_ids):
                agent_id = self.agent_ids[index]
                path = self.coordination_display.agent_files.get(agent_id)
                if path:
                    self.app_ref._show_text_modal(Path(path), f"{agent_id} Output")
            elif index == len(self.agent_ids):
                path = self.coordination_display.final_presentation_file
                if path:
                    self.app_ref._show_text_modal(Path(path), "Final Presentation")
            elif index == len(self.agent_ids) + 1:
                self.app_ref._show_system_status_modal()
            elif index == len(self.agent_ids) + 2:
                self.app_ref._show_coordination_table_modal()

            self.dismiss()

    class CoordinationTableModal(BaseModal):
        """Modal to display coordination table."""

        def __init__(self, table_content: str):
            super().__init__()
            self.table_content = table_content

        def compose(self) -> ComposeResult:
            with Container(id="table_container"):
                yield Label("📋 Coordination Table", id="table_header")
                yield Label("Use the mouse wheel or scrollbar to navigate", id="table_hint")
                yield TextArea(
                    self.table_content,
                    id="table_content",
                    read_only=True,
                )
                yield Button("Close (ESC)", id="close_button")

    class VoteResultsModal(BaseModal):
        """Modal for detailed vote results."""

        def __init__(self, results_text: str):
            super().__init__()
            self.results_text = results_text

        def compose(self) -> ComposeResult:
            with Container(id="vote_results_container"):
                yield Label("🗳️ Voting Breakdown", id="vote_header")
                yield TextArea(self.results_text, id="vote_results", read_only=True)
                yield Button("Close (ESC)", id="close_vote_button")

    class SystemStatusModal(BaseModal):
        """Modal to display system status log."""

        def __init__(self, content: str):
            super().__init__()
            self.content = content

        def compose(self) -> ComposeResult:
            with Container(id="system_status_container"):
                yield Label("📋 System Status Log", id="system_status_header")
                yield TextArea(self.content, id="system_status_content", read_only=True)
                yield Button("Close (ESC)", id="close_system_status_button")

    class TextContentModal(BaseModal):
        """Generic modal to display text content from a file or buffer."""

        def __init__(self, title: str, content: str):
            super().__init__()
            self.title = title
            self.content = content

        def compose(self) -> ComposeResult:
            with Container(id="text_content_container"):
                yield Label(self.title, id="text_content_header")
                yield TextArea(self.content, id="text_content_body", read_only=True)
                yield Button("Close (ESC)", id="close_text_content_button")

    class PostEvaluationPanel(Static):
        """Displays the most recent post-evaluation snippets."""

        def __init__(self):
            super().__init__(id="post_eval_container")
            self.agent_label = Label("", id="post_eval_label")
            self.log_view = RichLog(id="post_eval_log", highlight=True, markup=True, wrap=True)
            self.styles.display = "none"

        def compose(self) -> ComposeResult:
            yield self.agent_label
            yield self.log_view

        def update_lines(self, agent_id: str, lines: List[str]):
            """Show the last few post-evaluation lines."""
            self.styles.display = "block"
            self.agent_label.update(f"🔍 Post-Evaluation — {agent_id}")
            self.log_view.clear()
            if not lines:
                self.log_view.write("Evaluating answer...")
                return
            for entry in lines[-5:]:
                self.log_view.write(entry)

        def hide(self):
            """Hide the post-evaluation panel."""
            self.styles.display = "none"

    class FinalStreamPanel(Static):
        """Live view of the winning agent's presentation stream."""

        def __init__(self):
            super().__init__(id="final_stream_container")
            self.agent_label = Label("", id="final_stream_label")
            self.log_view = RichLog(id="final_stream_log", highlight=True, markup=True, wrap=True)
            self.current_line_label = Label("", classes="streaming_label")
            self._line_buffer = ""
            self._header_base = ""
            self._vote_summary = ""
            self._is_streaming = False
            self.styles.display = "none"

        def compose(self) -> ComposeResult:
            yield self.agent_label
            yield self.log_view
            yield self.current_line_label

        def begin(self, agent_id: str, vote_results: Dict[str, Any]):
            """Reset panel with agent metadata."""
            self.styles.display = "block"
            self._is_streaming = True
            self.add_class("streaming-active")
            self._header_base = f"🎤 Final Presentation — {agent_id}"
            self._vote_summary = self._format_vote_summary(vote_results or {})
            header = self._header_base
            if self._vote_summary:
                header = f"{header} | {self._vote_summary} | 🔴 LIVE"
            else:
                header = f"{header} | 🔴 LIVE"
            self.agent_label.update(header)
            self.log_view.clear()
            self._line_buffer = ""
            self.current_line_label.update("")

        def append_chunk(self, chunk: str):
            """Append streaming text with buffering."""
            if not chunk:
                return

            self._line_buffer = _process_line_buffer(
                self._line_buffer,
                chunk,
                lambda line: self.log_view.write(line),
            )
            self.current_line_label.update(self._line_buffer)

        def end(self):
            """Mark presentation as complete but keep visible."""
            if self._line_buffer.strip():
                self.log_view.write(self._line_buffer)
            self._line_buffer = ""
            self.current_line_label.update("")
            self._is_streaming = False
            self.remove_class("streaming-active")

            header = self._header_base or str(self.agent_label.renderable)
            if self._vote_summary:
                header = f"{header} | {self._vote_summary}"
            self.agent_label.update(f"{header} | ✅ Completed")

        def _format_vote_summary(self, vote_results: Dict[str, Any]) -> str:
            """Condensed vote summary for header."""
            if not vote_results:
                return ""
            mapping = vote_results.get("vote_counts") or {}
            if not mapping:
                return ""
            winner = vote_results.get("winner")
            is_tie = vote_results.get("is_tie", False)
            summary_pairs = ", ".join(f"{aid}:{count}" for aid, count in mapping.items())
            if winner:
                tie_note = " (tie)" if is_tie else ""
                return f"Votes — {summary_pairs}; Winner: {winner}{tie_note}"
            return f"Votes — {summary_pairs}"


def is_textual_available() -> bool:
    """Check if Textual is available."""
    return TEXTUAL_AVAILABLE


def create_textual_display(agent_ids: List[str], **kwargs) -> Optional[TextualTerminalDisplay]:
    """Factory function to create Textual display if available."""
    if not TEXTUAL_AVAILABLE:
        return None
    return TextualTerminalDisplay(agent_ids, **kwargs)
