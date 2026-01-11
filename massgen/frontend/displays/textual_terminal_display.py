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
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

from massgen.logger_config import get_log_session_dir, logger

from .terminal_display import TerminalDisplay

try:
    from rich.text import Text
    from textual import events, on
    from textual.app import App, ComposeResult
    from textual.containers import (
        Container,
        Horizontal,
        ScrollableContainer,
        Vertical,
        VerticalScroll,
    )
    from textual.message import Message
    from textual.reactive import reactive
    from textual.screen import ModalScreen
    from textual.widget import Widget
    from textual.widgets import (
        Button,
        Footer,
        Input,
        Label,
        RichLog,
        Select,
        Static,
        TextArea,
    )

    from .content_handlers import ThinkingContentHandler, ToolContentHandler
    from .content_normalizer import ContentNormalizer
    from .textual_widgets import (
        AgentTabBar,
        AgentTabChanged,
        CompletionFooter,
        MultiLineInput,
        PathSuggestionDropdown,
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


# Language mapping for syntax highlighting
FILE_LANG_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "jsx",
    ".tsx": "tsx",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "zsh",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".kt": "kotlin",
    ".swift": "swift",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".rb": "ruby",
    ".php": "php",
    ".sql": "sql",
    ".xml": "xml",
    ".r": "r",
    ".lua": "lua",
    ".vim": "vim",
    ".dockerfile": "dockerfile",
}

# Binary file extensions to reject for preview
BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".ico",
    ".webp",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".7z",
    ".rar",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".mp3",
    ".mp4",
    ".wav",
    ".avi",
    ".mov",
    ".mkv",
    ".pyc",
    ".pyo",
    ".class",
    ".o",
    ".obj",
}


def render_file_preview(
    file_path: Path,
    max_size: int = 50000,
    theme: str = "monokai",
) -> Tuple[Any, bool]:
    """Render file content with syntax highlighting or markdown.

    Args:
        file_path: Path to the file to preview.
        max_size: Maximum file size in bytes to render (default 50KB).
        theme: Syntax highlighting theme (default "monokai").

    Returns:
        Tuple of (renderable, is_rich) where:
        - renderable: Rich Markdown, Syntax, or plain string
        - is_rich: True if renderable is a Rich object, False for plain text
    """
    from rich.markdown import Markdown
    from rich.syntax import Syntax

    try:
        ext = file_path.suffix.lower()

        # Handle binary files
        if ext in BINARY_EXTENSIONS:
            return f"[Binary file: {ext}]", False

        # Check file size
        if file_path.stat().st_size > max_size:
            return f"[File too large: {file_path.stat().st_size:,} bytes]", False

        # Read content
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return "[Binary or non-UTF-8 file]", False

        # Empty file
        if not content.strip():
            return "[Empty file]", False

        # Markdown files - render as Markdown
        if ext in (".md", ".markdown"):
            return Markdown(content), True

        # Code files - render with syntax highlighting
        if ext in FILE_LANG_MAP:
            return (
                Syntax(
                    content,
                    FILE_LANG_MAP[ext],
                    theme=theme,
                    line_numbers=True,
                    word_wrap=True,
                ),
                True,
            )

        # Special files without extensions
        if file_path.name.lower() in ("dockerfile", "makefile", "jenkinsfile"):
            lang = file_path.name.lower()
            if lang == "makefile":
                lang = "make"
            return Syntax(content, lang, theme=theme, line_numbers=True, word_wrap=True), True

        # Default: plain text (truncate if very long)
        lines = content.split("\n")
        if len(lines) > 500:
            content = "\n".join(lines[:500]) + f"\n\n... [{len(lines) - 500} more lines]"
        return content, False

    except FileNotFoundError:
        return "[File not found]", False
    except PermissionError:
        return "[Permission denied]", False
    except Exception as e:
        return f"[Error reading file: {e}]", False


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


class ProgressIndicator(Static):
    """Animated spinner with optional progress bar for loading states.

    Provides visual feedback during async operations with configurable
    spinner styles and optional progress percentage display.
    """

    SPINNERS = {
        "unicode": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
        "ascii": ["|", "/", "-", "\\"],
        "dots": [".", "..", "...", ""],
    }

    progress = reactive(0.0)
    message = reactive("Loading...")
    is_spinning = reactive(False)

    def __init__(
        self,
        message: str = "Loading...",
        spinner_type: str = "unicode",
        show_progress: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._message = message
        self._spinner_type = spinner_type
        self._show_progress = show_progress
        self._spinner_index = 0
        self._spinner_timer = None
        self._frames = self.SPINNERS.get(spinner_type, self.SPINNERS["unicode"])

    def render(self) -> str:
        """Render the spinner with message."""
        if not self.is_spinning:
            return ""

        spinner_char = self._frames[self._spinner_index % len(self._frames)]

        if self._show_progress and self.progress > 0:
            return f"{spinner_char} {self.message} ({int(self.progress * 100)}%)"
        return f"{spinner_char} {self.message}"

    def start_spinner(self, message: str = None) -> None:
        """Start the spinner animation."""
        if message:
            self.message = message
        self.is_spinning = True
        self._spinner_index = 0
        self._start_animation()

    def stop_spinner(self) -> None:
        """Stop the spinner animation."""
        self.is_spinning = False
        if self._spinner_timer:
            self._spinner_timer.stop()
            self._spinner_timer = None
        self.refresh()

    def set_progress(self, value: float, message: str = None) -> None:
        """Update progress value (0.0 to 1.0) and optional message."""
        self.progress = max(0.0, min(1.0, value))
        if message:
            self.message = message
        self.refresh()

    def _start_animation(self) -> None:
        """Start the spinner animation timer."""
        if self._spinner_timer:
            self._spinner_timer.stop()

        def advance_spinner():
            if self.is_spinning:
                self._spinner_index = (self._spinner_index + 1) % len(self._frames)
                self.refresh()

        self._spinner_timer = self.set_interval(0.1, advance_spinner)

    def on_unmount(self) -> None:
        """Clean up timer when widget is removed."""
        self.stop_spinner()


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

    def send_new_answer(
        self,
        agent_id: str,
        content: str,
        answer_id: Optional[str] = None,
        answer_number: int = 1,
        answer_label: Optional[str] = None,
        workspace_path: Optional[str] = None,
    ) -> None:
        """Notify the TUI of a new answer - shows enhanced toast and tracks for browser.

        Args:
            agent_id: Agent that submitted the answer
            content: The answer content
            answer_id: Optional unique answer ID
            answer_number: The answer number for this agent (1, 2, etc.)
            answer_label: Label for this answer (e.g., "agent1.1")
            workspace_path: Absolute path to the workspace snapshot for this answer
        """
        if self._app:
            self._call_app_method(
                "notify_new_answer",
                agent_id,
                content,
                answer_id,
                answer_number,
                answer_label,
                workspace_path,
            )

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
        import sys

        print(f"[DEBUG] TextualDisplay.show_restart_banner called: attempt={attempt}, reason={reason[:50]}", file=sys.stderr)

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
        else:
            print("[DEBUG] show_restart_banner: self._app is None!", file=sys.stderr)

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

    async def prompt_for_broadcast_response(self, broadcast_request: Any) -> Optional[str]:
        """Prompt human for response to a broadcast question.

        Args:
            broadcast_request: BroadcastRequest object with question details

        Returns:
            Human's response string, or None if skipped/timeout
        """
        import asyncio

        if not self._app:
            return None

        # Extract details from broadcast request
        sender_agent_id = getattr(broadcast_request, "sender_agent_id", "Unknown Agent")
        question = getattr(broadcast_request, "question", "No question provided")
        timeout = getattr(broadcast_request, "timeout", 60)

        # Create a future to wait for the modal result
        response_future: asyncio.Future = asyncio.Future()

        def show_modal():
            """Show the broadcast modal and handle response."""
            modal = BroadcastPromptModal(sender_agent_id, question, timeout, self._app)

            async def handle_dismiss(result):
                if not response_future.done():
                    response_future.set_result(result)

            self._app.push_screen(modal, handle_dismiss)

        # Call from the app thread
        self._app.call_from_thread(show_modal)

        try:
            # Wait for response with timeout
            result = await asyncio.wait_for(response_future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            # Dismiss modal if still showing
            self._app.call_from_thread(lambda: self._app.pop_screen() if self._app.screen_stack else None)
            return None

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

    class StatusBarCancelClicked(Message):
        """Message emitted when the cancel button in StatusBar is clicked."""

    class StatusBar(Widget):
        """Persistent status bar showing orchestration state at the bottom of the TUI."""

        # CSS is in external theme files (dark.tcss/light.tcss)

        def __init__(self, agent_ids: List[str] | None = None):
            super().__init__(id="status_bar")
            self._vote_counts: Dict[str, int] = {}
            self._vote_history: List[Tuple[str, str, float]] = []  # (voter, voted_for, timestamp)
            self._current_phase = "idle"
            self._event_count = 0
            self._start_time: float | None = None
            self._timer_interval = None
            self._agent_ids = agent_ids or []
            self._last_leader: Optional[str] = None
            # Initialize vote counts to 0 for all agents
            for agent_id in self._agent_ids:
                self._vote_counts[agent_id] = 0

        def compose(self) -> ComposeResult:
            """Create the status bar layout with phase, progress, votes, events, MCP, cancel hint, and timer."""
            yield Static("⏳ Idle", id="status_phase")
            yield Static("", id="status_progress")  # Progress summary: "3 agents | 2 answers | 4/6 votes"
            yield Static("", id="status_votes")
            yield Static("", id="status_mcp")
            yield Static("📋 0 events", id="status_events", classes="clickable")
            yield Static("[dim]q:cancel • ?:help[/]", id="status_hints")  # Visible by default, hidden when idle
            yield Static("⏱️ 0:00", id="status_timer")
            yield Static("", id="status_cancel", classes="cancel-button hidden")

        def on_click(self, event: events.Click) -> None:
            """Handle click on the events counter or cancel button."""
            target = event.target
            if target and hasattr(target, "id"):
                if target.id == "status_events":
                    self.post_message(StatusBarEventsClicked())
                elif target.id == "status_cancel":
                    self.post_message(StatusBarCancelClicked())

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

            # Show/hide hints based on active phase
            try:
                hints_widget = self.query_one("#status_hints", Static)
                if phase in ("idle",):
                    hints_widget.add_class("hidden")
                else:
                    hints_widget.remove_class("hidden")
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

        def update_mcp_status(self, server_count: int, tool_count: int) -> None:
            """Update MCP indicator in status bar."""
            try:
                mcp_widget = self.query_one("#status_mcp", Static)
                if server_count > 0:
                    mcp_widget.update(f"🔌 {server_count}s/{tool_count}t")
                else:
                    mcp_widget.update("")
            except Exception:
                pass  # Widget not mounted yet

        def update_progress(
            self,
            agent_count: int,
            answer_count: int,
            vote_count: int,
            expected_votes: int = 0,
            winner: str = "",
        ) -> None:
            """Update progress summary in status bar.

            Args:
                agent_count: Number of agents in the session
                answer_count: Number of answers received
                vote_count: Number of votes cast
                expected_votes: Total expected votes (for X/Y display)
                winner: If set, display winner celebration instead
            """
            try:
                progress_widget = self.query_one("#status_progress", Static)

                if winner:
                    text = f"🏆 [bold yellow]{winner[:12]} wins![/]"
                else:
                    parts = []
                    if agent_count > 0:
                        parts.append(f"{agent_count} agents")
                    if answer_count > 0:
                        parts.append(f"{answer_count} answers")
                    if expected_votes > 0:
                        parts.append(f"{vote_count}/{expected_votes} votes")
                    elif vote_count > 0:
                        parts.append(f"{vote_count} votes")
                    text = " | ".join(parts) if parts else ""

                progress_widget.update(text)
            except Exception:
                pass  # Widget not mounted yet

        def add_vote(self, voted_for: str, voter: str = "") -> None:
            """Increment vote count for an agent and track history."""
            import time

            if voted_for not in self._vote_counts:
                self._vote_counts[voted_for] = 0
            self._vote_counts[voted_for] += 1
            self._vote_history.append((voter, voted_for, time.time()))
            self._update_votes_display(animate=True)

        def update_votes(self, vote_counts: Dict[str, int]) -> None:
            """Update all vote counts at once."""
            self._vote_counts = vote_counts.copy()
            self._update_votes_display()

        def _update_votes_display(self, animate: bool = False) -> None:
            """Update the votes display widget with leader highlighting."""
            if not self._vote_counts or all(v == 0 for v in self._vote_counts.values()):
                display_text = ""
                current_leader = None
            else:
                # Find the leader (max votes)
                max_votes = max(self._vote_counts.values())
                leaders = [aid for aid, count in self._vote_counts.items() if count == max_votes]
                current_leader = leaders[0] if len(leaders) == 1 else None  # No leader if tie

                # Format as "A:2 B:1" with leader highlighted
                parts = []
                for agent_id, count in sorted(self._vote_counts.items()):
                    if count > 0:
                        # Use first character or first 3 chars if agent ID is long
                        short_id = agent_id[0].upper() if len(agent_id) <= 3 else agent_id[:3]
                        if agent_id == current_leader:
                            # Highlight leader with crown
                            parts.append(f"[bold yellow]👑{short_id}:{count}[/]")
                        else:
                            parts.append(f"{short_id}:{count}")
                display_text = "🗳️ " + " ".join(parts) if parts else ""

            # Check if leader changed
            leader_changed = current_leader != self._last_leader and current_leader is not None
            self._last_leader = current_leader

            try:
                votes_widget = self.query_one("#status_votes", Static)
                votes_widget.update(display_text)

                # Trigger animation on vote update
                if animate:
                    votes_widget.add_class("vote-updated")
                    if leader_changed:
                        votes_widget.add_class("leader-changed")
                    # Remove animation classes after delay
                    self.set_timer(0.5, lambda: self._remove_vote_animation(votes_widget))
            except Exception:
                pass  # Widget not mounted yet

        def _remove_vote_animation(self, widget: Static) -> None:
            """Remove animation classes from vote widget."""
            try:
                widget.remove_class("vote-updated")
                widget.remove_class("leader-changed")
            except Exception:
                pass

        def get_standings_text(self) -> str:
            """Get current vote standings as text."""
            if not self._vote_counts or all(v == 0 for v in self._vote_counts.values()):
                return ""
            sorted_votes = sorted(self._vote_counts.items(), key=lambda x: -x[1])
            parts = [f"{aid[:8]}:{count}" for aid, count in sorted_votes if count > 0]
            return " | ".join(parts)

        def get_vote_history(self) -> List[Tuple[str, str, float]]:
            """Get the vote history list."""
            return self._vote_history.copy()

        def celebrate_winner(self, winner: str) -> None:
            """Highlight winner when consensus is reached."""
            self.add_class("consensus-reached")
            # Remove after animation
            self.set_timer(3.0, lambda: self.remove_class("consensus-reached"))

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

        def show_cancel_button(self, show: bool = True) -> None:
            """Show or hide the cancel button."""
            try:
                cancel_widget = self.query_one("#status_cancel", Static)
                if show:
                    cancel_widget.update("❌ Cancel")
                    cancel_widget.remove_class("hidden")
                else:
                    cancel_widget.add_class("hidden")
            except Exception:
                pass  # Widget not mounted yet

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

        # Minimal bindings - most features accessed via /slash commands
        # Only canonical shortcuts that users expect
        BINDINGS = [
            # Agent navigation
            Binding("tab", "next_agent", "Next Agent"),
            Binding("shift+tab", "prev_agent", "Prev Agent"),
            # Quit - canonical shortcuts
            Binding("ctrl+c", "quit", "Quit", priority=True),
            Binding("ctrl+d", "quit", "Quit", show=False),
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

            # Answer tracking for browser modal
            self._answers: List[Dict[str, Any]] = []  # All answers with metadata
            self._votes: List[Dict[str, Any]] = []  # All votes with metadata
            self._winner_agent_id: Optional[str] = None  # Winner when consensus reached

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

            self.final_stream_panel = FinalStreamPanel(coordination_display=self.coordination_display)
            yield self.final_stream_panel

            self.safe_indicator = Label("", id="safe_indicator")
            yield self.safe_indicator

            # Status bar showing phase, votes, events, timer (hidden during welcome)
            self._status_bar = StatusBar(agent_ids=agent_ids)
            if self._showing_welcome:
                self._status_bar.add_class("hidden")
            yield self._status_bar

            # Path autocomplete dropdown (hidden by default, floats above input area)
            self._path_dropdown = PathSuggestionDropdown(id="path_dropdown")
            yield self._path_dropdown

            # Input area container with text input
            with Container(id="input_area"):
                # Input header with hint and vim mode indicator (above input)
                with Horizontal(id="input_header"):
                    # Hint for submission (updated dynamically for vim mode)
                    self._input_hint = Static("Enter to submit • Shift+Enter for new line • /vim for vim mode", id="input_hint")
                    yield self._input_hint
                    # Vim mode indicator (hidden by default)
                    self._vim_indicator = Static("", id="vim_indicator")
                    yield self._vim_indicator

                # Multi-line input: Enter to submit, Shift+Enter for new line
                # Type @ to trigger path autocomplete
                self.question_input = MultiLineInput(
                    placeholder="Type your question (use @ for file context)...",
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
            # Auto-focus input field on startup
            if self.question_input:
                self.question_input.focus()

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

        def on_key(self, event: events.Key) -> None:
            """Handle key events for agent shortcuts and @ autocomplete.

            Number keys 1-9 switch to specific agents (when not typing).
            All other shortcuts use Ctrl modifiers and are handled via BINDINGS.
            """
            # DEBUG: Log all keys
            with open("/tmp/at_debug.log", "a") as f:
                f.write(f"[DEBUG App] on_key called: key={event.key}, dropdown_showing={hasattr(self, '_path_dropdown') and self._path_dropdown.is_showing}\n")
            # If @ autocomplete is showing, route keys to it first
            if hasattr(self, "_path_dropdown") and self._path_dropdown.is_showing:
                with open("/tmp/at_debug.log", "a") as f:
                    f.write(f"[DEBUG App] Routing to dropdown.handle_key for key={event.key}\n")
                if self._path_dropdown.handle_key(event):
                    with open("/tmp/at_debug.log", "a") as f:
                        f.write(f"[DEBUG App] Dropdown handled key={event.key}, stopping event\n")
                    event.prevent_default()
                    event.stop()
                    return

            # Don't handle shortcuts when typing in input (supports both Input and MultiLineInput/TextArea)
            if isinstance(self.focused, (Input, TextArea)) and getattr(self.focused, "id", None) == "question_input":
                # But allow Escape to unfocus from input
                if event.key == "escape":
                    self.set_focus(None)
                    self.notify("Press any shortcut key (h for help)", severity="information", timeout=2)
                    event.stop()
                # Note: Tab key when dropdown is showing is handled above
                return

            # Handle agent shortcuts
            self._handle_agent_shortcuts(event)

        def on_input_submitted(self, event: Input.Submitted) -> None:
            """Handle Enter key in the single-line Input widget (fallback)."""
            if event.input.id == "question_input":
                self._submit_question()

        def on_multi_line_input_submitted(self, event: MultiLineInput.Submitted) -> None:
            """Handle Enter in the multi-line input."""
            if event.input.id == "question_input":
                self._submit_question()

        @on(TextArea.Changed, "#question_input")
        def handle_question_input_changed(self, event: TextArea.Changed) -> None:
            """Handle TextArea changes to trigger @ autocomplete check."""
            if hasattr(self, "question_input") and hasattr(self.question_input, "_check_at_trigger"):
                self.question_input._check_at_trigger()

        def on_multi_line_input_vim_mode_changed(self, event: MultiLineInput.VimModeChanged) -> None:
            """Handle vim mode changes to update the indicator."""
            if event.input.id == "question_input":
                self._update_vim_indicator(event.vim_normal)

        def on_multi_line_input_at_prefix_changed(self, event: MultiLineInput.AtPrefixChanged) -> None:
            """Handle @ prefix changes for path autocomplete."""
            if event.input.id == "question_input" and hasattr(self, "_path_dropdown"):
                self._path_dropdown.update_suggestions(event.prefix)
                self.question_input.autocomplete_active = self._path_dropdown.is_showing

        def on_multi_line_input_at_dismissed(self, event: MultiLineInput.AtDismissed) -> None:
            """Handle @ autocomplete dismissal."""
            if event.input.id == "question_input" and hasattr(self, "_path_dropdown"):
                self._path_dropdown.dismiss()
                self.question_input.autocomplete_active = False

        def on_multi_line_input_tab_pressed_with_autocomplete(self, event: MultiLineInput.TabPressedWithAutocomplete) -> None:
            """Handle Tab press while autocomplete is active - select current item."""
            if event.input.id == "question_input" and hasattr(self, "_path_dropdown") and self._path_dropdown.is_showing:
                self._path_dropdown._select_current()

        def on_path_suggestion_dropdown_path_selected(self, event: PathSuggestionDropdown.PathSelected) -> None:
            """Handle path selection from autocomplete dropdown."""
            if hasattr(self, "question_input"):
                self.question_input.insert_completion(event.path, event.with_write)
                self.question_input.autocomplete_active = False

        def on_path_suggestion_dropdown_continue_browsing(self, event: PathSuggestionDropdown.ContinueBrowsing) -> None:
            """Handle directory selection to continue browsing."""
            if hasattr(self, "question_input"):
                self.question_input.update_at_prefix(event.prefix)

        def on_path_suggestion_dropdown_dismissed(self, event: PathSuggestionDropdown.Dismissed) -> None:
            """Handle dropdown dismissal."""
            if hasattr(self, "question_input"):
                self.question_input.autocomplete_active = False

        def _submit_question(self) -> None:
            """Submit the current question text."""
            text = self.question_input.text.strip()
            if not text:
                return

            self.question_input.clear()

            # Dismiss welcome screen on first real input
            if self._showing_welcome and not text.startswith("/"):
                self._dismiss_welcome()

            # Handle TUI-local slash commands first (like /vim)
            if text.startswith("/"):
                if self._handle_local_slash_command(text):
                    return  # Command was handled locally

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

        def _handle_local_slash_command(self, command: str) -> bool:
            """Handle TUI-local slash commands that should not be passed to the orchestrator.

            Args:
                command: The slash command string.

            Returns:
                True if the command was handled locally, False otherwise.
            """
            cmd = command.split()[0].lower()

            if cmd == "/vim":
                self._toggle_vim_mode()
                return True

            return False

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
                    self._show_context_modal()
                elif result.ui_action == "show_cost":
                    self._show_cost_breakdown_modal()
                elif result.ui_action == "show_workspace":
                    self._show_workspace_files_modal()
                elif result.ui_action == "show_metrics":
                    self._show_metrics_modal()
                elif result.ui_action == "show_mcp":
                    self.action_open_mcp_status()
                elif result.ui_action == "show_answers":
                    self.action_open_answer_browser()
                elif result.ui_action == "show_timeline":
                    self.action_open_timeline()
                elif result.ui_action == "show_files":
                    self.action_open_workspace_browser()
                elif result.ui_action == "show_browser":
                    self.action_open_unified_browser()
                elif result.ui_action == "toggle_vim":
                    self._toggle_vim_mode()
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
                elif cmd in ("/context",):
                    self._show_context_modal()
                elif cmd in ("/metrics", "/m"):
                    self._show_metrics_modal()
                elif cmd in ("/cost", "/c"):
                    self._show_cost_breakdown_modal()
                elif cmd in ("/workspace", "/w"):
                    self._show_workspace_files_modal()
                elif cmd in ("/mcp", "/p"):
                    self.action_open_mcp_status()
                elif cmd == "/vim":
                    self._toggle_vim_mode()
                else:
                    self.notify(f"Unknown command: {command}", severity="warning")

        def _toggle_vim_mode(self) -> None:
            """Toggle vim mode on the question input."""
            if not hasattr(self, "question_input") or self.question_input is None:
                return

            current = self.question_input.vim_mode
            self.question_input.vim_mode = not current

            if self.question_input.vim_mode:
                # Enter insert mode when enabling (more intuitive - user wants to type)
                self.question_input._vim_normal = False
                self.question_input.remove_class("vim-normal")
                self._update_vim_indicator(False)  # False = insert mode
            else:
                self.question_input._vim_normal = False
                self.question_input.remove_class("vim-normal")
                self._update_vim_indicator(None)  # None = vim mode off

        def _update_vim_indicator(self, vim_normal: bool | None) -> None:
            """Update the vim mode indicator.

            Args:
                vim_normal: True for normal mode, False for insert mode, None to hide.
            """
            if not hasattr(self, "_vim_indicator"):
                return

            if vim_normal is None:
                # Vim mode off - hide indicator
                self._vim_indicator.update("")
                self._vim_indicator.remove_class("vim-normal-indicator")
                self._vim_indicator.remove_class("vim-insert-indicator")
                if hasattr(self, "_input_hint"):
                    self._input_hint.update("Enter to submit • Shift+Enter for new line • /vim for vim mode")
            elif vim_normal:
                # Normal mode
                self._vim_indicator.update(" NORMAL ")
                self._vim_indicator.remove_class("vim-insert-indicator")
                self._vim_indicator.add_class("vim-normal-indicator")
                if hasattr(self, "_input_hint"):
                    self._input_hint.update("VIM: i/a insert • hjkl move • /vim off")
            else:
                # Insert mode
                self._vim_indicator.update(" INSERT ")
                self._vim_indicator.remove_class("vim-normal-indicator")
                self._vim_indicator.add_class("vim-insert-indicator")
                if hasattr(self, "_input_hint"):
                    self._input_hint.update("VIM: Esc normal • Enter submit • /vim off")

            # Force refresh to ensure visual update
            self._vim_indicator.refresh(layout=True)
            if hasattr(self, "_input_hint"):
                self._input_hint.refresh()

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
            """Display final answer modal with flush effect and winner celebration."""
            if not selected_agent:
                return

            # Track the winner
            self._winner_agent_id = selected_agent

            # Mark the winning answer(s) in tracked answers
            for ans in self._answers:
                if ans.get("agent_id") == selected_agent:
                    ans["is_winner"] = True
                    ans["is_final"] = True

            # Celebrate the winner
            self._celebrate_winner(selected_agent, answer)

            if self.final_stream_panel:
                # Get model name for the winning agent
                model_name = self.coordination_display.agent_models.get(selected_agent, "")
                self.final_stream_panel.begin(selected_agent, model_name, vote_results or {})
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
                # Get model name for the winning agent
                model_name = self.coordination_display.agent_models.get(agent_id, "")
                self.final_stream_panel.begin(agent_id, model_name, vote_results)

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
            # Notify with toast so user knows restart is happening
            short_reason = reason[:50] + "..." if len(reason) > 50 else reason
            self.notify(
                f"🔄 [bold red]RESTART[/] — Attempt {attempt}/{max_attempts}\n   {short_reason}",
                severity="warning",
                timeout=8,
            )

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
            self._show_modal_async(
                VoteResultsModal(
                    results_text=formatted_results,
                    vote_counts=self._vote_counts.copy() if hasattr(self, "_vote_counts") else None,
                    votes=self._votes.copy() if hasattr(self, "_votes") else None,
                ),
            )

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
            """Switch to next agent tab, or select in dropdown if showing."""
            # If dropdown is showing, Tab selects the current item
            if hasattr(self, "_path_dropdown") and self._path_dropdown.is_showing:
                self._path_dropdown._select_current()
                return
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
                text = ""
            self._show_modal_async(
                VoteResultsModal(
                    results_text=text,
                    vote_counts=self._vote_counts.copy() if hasattr(self, "_vote_counts") else None,
                    votes=self._votes.copy() if hasattr(self, "_votes") else None,
                ),
            )

        @keyboard_action
        def action_open_system_status(self):
            """Open system status log."""
            self._show_system_status_modal()

        @keyboard_action
        def action_open_orchestrator(self):
            """Open orchestrator events modal."""
            self._show_orchestrator_modal()

        @keyboard_action
        def action_open_agent_output(self):
            """Open full agent output modal for currently active agent."""
            agent_id = self._active_agent_id
            if not agent_id:
                # Fall back to first agent
                agent_id = self.coordination_display.agent_ids[0] if self.coordination_display.agent_ids else None
            if agent_id:
                self._show_agent_output_modal(agent_id)
            else:
                self.notify("No agent selected", severity="warning")

        @keyboard_action
        def action_open_cost_breakdown(self):
            """Open cost breakdown modal."""
            self._show_cost_breakdown_modal()

        @keyboard_action
        def action_open_metrics(self):
            """Open metrics modal."""
            self._show_metrics_modal()

        @keyboard_action
        def action_show_shortcuts(self):
            """Show keyboard shortcuts modal."""
            self._show_modal_async(KeyboardShortcutsModal())

        @keyboard_action
        def action_open_mcp_status(self):
            """Open MCP server status modal."""
            mcp_status = self._get_mcp_status()
            if not mcp_status["servers"]:
                self.notify("No MCP servers connected", severity="warning", timeout=3)
                return
            self._show_modal_async(MCPStatusModal(mcp_status))

        @keyboard_action
        def action_open_answer_browser(self):
            """Open answer browser modal."""
            if not self._answers:
                self.notify("No answers yet", severity="warning", timeout=3)
                return
            self._show_modal_async(
                AnswerBrowserModal(
                    answers=self._answers,
                    votes=self._votes,
                    agent_ids=self.coordination_display.agent_ids,
                    winner_agent_id=self._winner_agent_id,
                ),
            )

        @keyboard_action
        def action_open_timeline(self):
            """Open timeline visualization modal."""
            if not self._answers and not self._votes:
                self.notify("No activity yet", severity="warning", timeout=3)
                return
            self._show_modal_async(
                TimelineModal(
                    answers=self._answers,
                    votes=self._votes,
                    agent_ids=self.coordination_display.agent_ids,
                    winner_agent_id=self._winner_agent_id,
                ),
            )

        @keyboard_action
        def action_open_workspace_browser(self):
            """Open workspace browser modal to view answer snapshots."""
            if not self._answers:
                self.notify("No answers yet - workspaces available after agents submit", severity="warning", timeout=3)
                return
            self._show_modal_async(
                WorkspaceBrowserModal(
                    answers=self._answers,
                    agent_ids=self.coordination_display.agent_ids,
                ),
            )

        @keyboard_action
        def action_open_unified_browser(self):
            """Open unified browser modal with tabs for Answers, Votes, Workspace, Timeline."""
            if not self._answers and not self._votes:
                self.notify("No activity yet", severity="warning", timeout=3)
                return
            self._show_modal_async(
                BrowserTabsModal(
                    answers=self._answers,
                    votes=self._votes,
                    vote_counts=self._vote_counts.copy() if hasattr(self, "_vote_counts") else {},
                    agent_ids=self.coordination_display.agent_ids,
                    winner_agent_id=self._winner_agent_id,
                ),
            )

        def _get_mcp_status(self) -> Dict[str, Any]:
            """Gather MCP server status from orchestrator."""
            orchestrator = getattr(self.coordination_display, "orchestrator", None)
            if not orchestrator:
                return {"servers": [], "total_tools": 0}

            servers = []
            total_tools = 0

            # MCP client is typically shared across agents, check the first one with a backend
            agents = getattr(orchestrator, "agents", {})
            for agent_id, agent in agents.items():
                backend = getattr(agent, "backend", None)
                if not backend:
                    continue
                mcp_client = getattr(backend, "_mcp_client", None)
                if not mcp_client:
                    continue

                # Get server names
                server_names = []
                if hasattr(mcp_client, "get_server_names"):
                    server_names = mcp_client.get_server_names()
                elif hasattr(mcp_client, "_server_clients"):
                    server_names = list(mcp_client._server_clients.keys())

                # Get available tools
                all_tools = []
                if hasattr(mcp_client, "get_available_tools"):
                    all_tools = mcp_client.get_available_tools()

                for name in server_names:
                    # Filter tools for this server (MCP tools are prefixed with mcp__{server}__{tool})
                    server_tools = [t for t in all_tools if f"mcp__{name}__" in str(t)]
                    servers.append(
                        {
                            "name": name,
                            "connected": True,
                            "state": "connected",
                            "tools": server_tools,
                            "agent": agent_id,
                        },
                    )
                    total_tools += len(server_tools)

                # Only need to check one agent since MCP client is shared
                break

            return {"servers": servers, "total_tools": total_tools}

        def _show_orchestrator_modal(self):
            """Display orchestrator events in a modal."""
            events_text = "\n".join(self._orchestrator_events) if self._orchestrator_events else "No events yet."
            self._show_modal_async(OrchestratorEventsModal(events_text))

        def on_status_bar_events_clicked(self, event: StatusBarEventsClicked) -> None:
            """Handle click on status bar events counter - opens orchestrator events modal."""
            self._show_orchestrator_modal()

        # === Status Bar Notification Methods ===

        def notify_vote(self, voter: str, voted_for: str) -> None:
            """Called when a vote is cast. Updates status bar and shows toast with standings."""
            import time

            # Get model names for richer display
            voter_model = self.coordination_display.agent_models.get(voter, "")
            voted_for_model = self.coordination_display.agent_models.get(voted_for, "")

            # Track the vote for browser
            self._votes.append(
                {
                    "voter": voter,
                    "voter_model": voter_model,
                    "voted_for": voted_for,
                    "voted_for_model": voted_for_model,
                    "timestamp": time.time(),
                },
            )

            if self._status_bar:
                self._status_bar.add_vote(voted_for, voter)
                standings = self._status_bar.get_standings_text()

                # Update progress summary
                agent_count = len(self.coordination_display.agent_ids)
                answer_count = len(self._answers)
                vote_count = len(self._votes)
                # Expected votes = agents * (agents - 1) in typical voting round
                expected_votes = agent_count * (agent_count - 1) if agent_count > 1 else 0
                self._status_bar.update_progress(agent_count, answer_count, vote_count, expected_votes)

                # Enhanced toast with model info
                voter_display = f"{voter}" + (f" ({voter_model})" if voter_model else "")
                target_display = f"{voted_for}" + (f" ({voted_for_model})" if voted_for_model else "")

                if standings:
                    self.notify(
                        f"🗳️ [bold]{voter_display}[/] → [bold cyan]{target_display}[/]\n📊 {standings}",
                        timeout=4,
                    )
                else:
                    self.notify(
                        f"🗳️ [bold]{voter_display}[/] → [bold cyan]{target_display}[/]",
                        timeout=3,
                    )
            else:
                self.notify(f"🗳️ {voter} → {voted_for}", timeout=3)

        def notify_new_answer(
            self,
            agent_id: str,
            content: str,
            answer_id: Optional[str],
            answer_number: int,
            answer_label: Optional[str],
            workspace_path: Optional[str],
        ) -> None:
            """Called when an agent submits an answer. Shows enhanced toast, tool card, and tracks for browser."""
            import time

            # Get model name for richer display
            model_name = self.coordination_display.agent_models.get(agent_id, "")

            # Track the answer for browser
            self._answers.append(
                {
                    "agent_id": agent_id,
                    "model": model_name,
                    "content": content,
                    "answer_id": answer_id,
                    "answer_number": answer_number,
                    "answer_label": answer_label or f"{agent_id}.{answer_number}",
                    "workspace_path": workspace_path,
                    "timestamp": time.time(),
                    "is_final": False,
                    "is_winner": False,
                },
            )

            # Update progress summary in StatusBar
            if self._status_bar:
                agent_count = len(self.coordination_display.agent_ids)
                answer_count = len(self._answers)
                vote_count = len(self._votes)
                self._status_bar.update_progress(agent_count, answer_count, vote_count)

            # Enhanced toast with model info
            agent_display = f"{agent_id}" + (f" ({model_name})" if model_name else "")
            answer_count = len([a for a in self._answers if a["agent_id"] == agent_id])

            # Truncate content preview
            preview = content[:100] + "..." if len(content) > 100 else content
            preview = preview.replace("\n", " ")

            self.notify(
                f"📝 [bold green]New Answer[/] from [bold]{agent_display}[/]\n" f"   Answer #{answer_count}: {preview}",
                timeout=5,
            )

            # Also add a tool card for the new_answer action in the agent's panel
            # This provides visual feedback in the timeline view
            if agent_id in self.agent_widgets:
                panel = self.agent_widgets[agent_id]

                try:
                    timeline = panel.query_one(f"#{panel._timeline_section_id}", TimelineSection)

                    # Create tool display data with FULL content for the modal
                    from datetime import datetime

                    from .content_handlers import ToolDisplayData

                    tool_id = f"new_answer_{agent_id}_{answer_count}"

                    # Create truncated preview for card display
                    card_preview = content[:100].replace("\n", " ")
                    if len(content) > 100:
                        card_preview += "..."

                    now = datetime.now()
                    tool_data = ToolDisplayData(
                        tool_id=tool_id,
                        tool_name="workspace/new_answer",
                        display_name="Workspace/New Answer",
                        tool_type="workspace",
                        category="workspace",
                        icon="📝",
                        color="#4fc1ff",
                        status="success",
                        start_time=now,
                        end_time=now,
                        args_summary=f'content="{card_preview}"',
                        args_full=f'content="{content}"',  # Full content for modal
                        result_summary=f"Answer #{answer_count} submitted successfully",
                        result_full=content,  # Full answer content in result
                        elapsed_seconds=0.0,
                    )

                    # Add tool card directly to timeline
                    timeline.add_tool(tool_data)
                    # Mark as success immediately
                    tool_data.status = "success"
                    timeline.update_tool(tool_id, tool_data)

                    # Add a restart separator AFTER the answer card
                    # new_answer terminates a round, so separator marks end of this attempt
                    sep_label = f"⚡ RESTART — ROUND {answer_count} COMPLETE"
                    timeline.add_separator(sep_label)
                except Exception as e:
                    import sys
                    import traceback

                    print(f"[ERROR] Failed to add workspace/new_answer card: {e}", file=sys.stderr)
                    traceback.print_exc()

        def _celebrate_winner(self, winner_id: str, answer_preview: str) -> None:
            """Display prominent winner celebration effects.

            Args:
                winner_id: The winning agent's ID
                answer_preview: Preview of the winning answer
            """
            # Get model name for richer display
            model_name = self.coordination_display.agent_models.get(winner_id, "")

            # 1. Update StatusBar with winner announcement
            if self._status_bar:
                agent_count = len(self.coordination_display.agent_ids)
                answer_count = len(self._answers)
                vote_count = len(self._votes)
                self._status_bar.update_progress(
                    agent_count,
                    answer_count,
                    vote_count,
                    0,
                    winner=winner_id,
                )
                self._status_bar.celebrate_winner(winner_id)

            # 2. Add winner CSS class to the winning agent's tab
            try:
                tab_bar = self.query_one(AgentTabBar)
                for tab in tab_bar.query(".agent-tab"):
                    if getattr(tab, "agent_id", "") == winner_id:
                        tab.add_class("winner")
                        break
            except Exception:
                pass  # Tab bar might not be available

            # 3. Enhanced toast notification for winner
            winner_display = f"{winner_id}" + (f" ({model_name})" if model_name else "")

            # Truncate answer preview
            preview = answer_preview[:80].replace("\n", " ") if answer_preview else ""
            if len(answer_preview or "") > 80:
                preview += "..."

            self.notify(
                f"🏆 [bold yellow]Consensus Reached![/]\n" f"Winner: [bold]{winner_display}[/]\n" f"Preview: {preview}",
                severity="information",
                timeout=10,
            )

            # 4. Add orchestrator event
            self.add_orchestrator_event(f"🏆 Winner: {winner_id} selected by consensus")

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

        def _handle_agent_shortcuts(self, event: events.Key) -> bool:
            """Handle agent shortcuts. Returns True if event was handled.

            Single-key shortcuts (when not typing in input):
            - 1-9: Switch to agent by number
            - q: Cancel/stop current execution
            - s: System status
            - o: Orchestrator events
            - v: Vote results
            - w: Workspace browser
            - f: Final presentation / files
            - c: Cost breakdown
            - m: MCP status / metrics
            - a: Answer browser
            - t: Timeline
            - h or ?: Help/shortcuts
            """
            if self._keyboard_locked():
                return False

            key = event.character
            if not key:
                return False

            # Number keys for agent switching
            if key.isdigit() and key != "0":
                idx = int(key) - 1
                if 0 <= idx < len(self.coordination_display.agent_ids):
                    agent_id = self.coordination_display.agent_ids[idx]
                    self._switch_to_agent(agent_id)
                    event.stop()
                    return True

            key_lower = key.lower()

            # q - Cancel/quit current execution
            if key_lower == "q":
                self.coordination_display.request_cancellation()
                event.stop()
                return True

            # s - System status
            if key_lower == "s":
                self.action_open_system_status()
                event.stop()
                return True

            # o - Orchestrator events
            if key_lower == "o":
                self.action_open_orchestrator()
                event.stop()
                return True

            # v - Vote results
            if key_lower == "v":
                self.action_open_vote_results()
                event.stop()
                return True

            # w - Workspace browser
            if key_lower == "w":
                self.action_open_workspace_browser()
                event.stop()
                return True

            # f - Final presentation / file inspection
            if key_lower == "f":
                self._show_file_inspection_modal()
                event.stop()
                return True

            # c - Cost breakdown
            if key_lower == "c":
                self.action_open_cost_breakdown()
                event.stop()
                return True

            # m - MCP status or metrics
            if key_lower == "m":
                self.action_open_mcp_status()
                event.stop()
                return True

            # a - Answer browser
            if key_lower == "a":
                self.action_open_answer_browser()
                event.stop()
                return True

            # t - Timeline
            if key_lower == "t":
                self.action_open_timeline()
                event.stop()
                return True

            # h or ? - Help/shortcuts
            if key_lower == "h" or key == "?":
                self.action_show_shortcuts()
                event.stop()
                return True

            # i or / - Focus input (vim-like insert mode or search)
            if key_lower == "i" or key == "/":
                if hasattr(self, "question_input") and self.question_input:
                    self.question_input.focus()
                    event.stop()
                    return True

            # Escape when not in input - show hint
            if event.key == "escape":
                self.notify("Already in command mode. Press i or / to type.", severity="information", timeout=2)
                event.stop()
                return True

            return False

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

        def _show_cost_breakdown_modal(self):
            """Display cost breakdown in a modal."""
            self._show_modal_async(CostBreakdownModal(self.coordination_display))

        def _show_workspace_files_modal(self):
            """Display workspace files in a modal."""
            self._show_modal_async(WorkspaceFilesModal(self.coordination_display, self))

        def _show_context_modal(self):
            """Display context paths modal."""
            self._show_modal_async(ContextModal(self.coordination_display, self))

        def _show_metrics_modal(self):
            """Display tool metrics in a modal."""
            self._show_modal_async(MetricsModal(self.coordination_display))

        def _show_file_inspection_modal(self):
            """Display file inspection modal with tree view."""
            orchestrator = getattr(self.coordination_display, "orchestrator", None)
            workspace_path = None
            if orchestrator:
                workspace_dir = getattr(orchestrator, "workspace_dir", None)
                if workspace_dir:
                    workspace_path = Path(workspace_dir)
            if not workspace_path or not workspace_path.exists():
                self.notify("No workspace available", severity="warning")
                return
            self._show_modal_async(FileInspectionModal(workspace_path, self))

        def _show_agent_output_modal(self, agent_id: str):
            """Display full agent output in a modal."""
            # Get the agent outputs from the display
            agent_outputs = self.coordination_display.get_agent_content(agent_id)
            # Get model name from orchestrator if available
            model_name = None
            orchestrator = getattr(self.coordination_display, "orchestrator", None)
            if orchestrator:
                agents = getattr(orchestrator, "agents", {})
                if agent_id in agents:
                    agent = agents[agent_id]
                    model_name = getattr(agent, "model", None) or getattr(agent, "model_name", None)
            self._show_modal_async(AgentOutputModal(agent_id, agent_outputs, model_name))

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
            yield Label("Type /help for commands  •  Ctrl+C to quit", id="welcome_shortcuts_hint")

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
                    yield ProgressIndicator(
                        message="Waiting for agent...",
                        id=f"progress_{self._dom_safe_id}",
                    )

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
                    # Stop spinner animation
                    progress = self.query_one(f"#progress_{self._dom_safe_id}")
                    progress.stop_spinner()
                    # Hide container
                    loading = self.query_one(f"#{self._loading_id}")
                    loading.add_class("hidden")
                except Exception:
                    pass

        def _update_loading_text(self, text: str):
            """Update the loading indicator text."""
            try:
                progress = self.query_one(f"#progress_{self._dom_safe_id}")
                progress.message = text
            except Exception:
                pass

        def _start_loading_spinner(self, message: str = "Waiting for agent..."):
            """Start the loading spinner with a message."""
            try:
                progress = self.query_one(f"#progress_{self._dom_safe_id}")
                progress.start_spinner(message)
            except Exception:
                pass

        def on_mount(self) -> None:
            """Start the loading spinner when the panel is mounted."""
            self._start_loading_spinner("Waiting for agent...")

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
            """Show a highly visible restart separator in the TimelineSection."""
            # Reset tool row count for fresh alternation after restart
            self._tool_row_count = 0
            self._reasoning_header_shown = False

            # Build banner text
            banner_label = f"⚡ RESTART — ATTEMPT {attempt}"
            if reason and reason != "New attempt":
                short_reason = reason[:40] + "..." if len(reason) > 40 else reason
                banner_label += f" — {short_reason}"

            # Add to timeline using the RestartBanner widget
            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)
                timeline.add_separator(banner_label)

                # Clear the timeline for fresh content after restart
                # (optional - comment out if you want to keep history)
                # timeline.clear()

                # Hide completion footer for new attempt
                self._hide_completion_footer()
            except Exception as e:
                # Log error for debugging
                import sys

                print(f"[ERROR] show_restart_separator failed: {e}", file=sys.stderr)

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

            # Add spacing before time to separate it visually
            if self._start_time and self.status in ("working", "streaming"):
                elapsed = datetime.now() - self._start_time
                elapsed_str = self._format_elapsed(elapsed.total_seconds())
                parts.append(f"  ⏱ {elapsed_str}")  # Extra spaces before timer

            # Status in brackets at the end
            parts.append(f"  [{self.status}]")

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

    class KeyboardShortcutsModal(BaseModal):
        """Modal showing commands available during coordination."""

        def compose(self) -> ComposeResult:
            from textual.widgets import Static

            with Container(id="shortcuts_modal_container"):
                yield Label("📖  Commands & Shortcuts", id="shortcuts_modal_header")
                yield Label("Press Esc to unfocus input, then use single keys", id="shortcuts_hint")
                with Container(id="shortcuts_content"):
                    yield Static(
                        "[bold cyan]Quick Keys[/] [dim](when not typing)[/]\n"
                        "  [yellow]q[/]              Cancel/stop execution\n"
                        "  [yellow]w[/]              Workspace browser\n"
                        "  [yellow]v[/]              Vote results\n"
                        "  [yellow]a[/]              Answer browser\n"
                        "  [yellow]t[/]              Timeline\n"
                        "  [yellow]f[/]              File inspection\n"
                        "  [yellow]c[/]              Cost breakdown\n"
                        "  [yellow]m[/]              MCP status / metrics\n"
                        "  [yellow]s[/]              System status\n"
                        "  [yellow]o[/]              Orchestrator events\n"
                        "  [yellow]h[/] or [yellow]?[/]        This help\n"
                        "  [yellow]1-9[/]            Switch to agent N\n"
                        "\n"
                        "[bold cyan]Focus[/]\n"
                        "  [yellow]Esc[/]            Unfocus input (enable quick keys)\n"
                        "  [yellow]i[/] or [yellow]/[/]        Focus input (start typing)\n"
                        "\n"
                        "[bold cyan]Input[/]\n"
                        "  [yellow]Enter[/]          Submit question\n"
                        "  [yellow]Shift+Enter[/]    New line\n"
                        "  [yellow]Tab[/]            Next agent\n"
                        "  [yellow]Shift+Tab[/]      Previous agent\n"
                        "\n"
                        "[bold cyan]Quit[/]\n"
                        "  [yellow]Ctrl+C[/]         Exit MassGen\n"
                        "  [yellow]q[/]              Cancel current turn\n"
                        "\n"
                        "[dim]Type /help for slash commands[/]",
                        id="shortcuts_text",
                        markup=True,
                    )
                yield Button("Close (ESC)", id="close_shortcuts_button")

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "close_shortcuts_button":
                self.dismiss()

        def key_escape(self) -> None:
            self.dismiss()

    class MCPStatusModal(BaseModal):
        """Modal showing MCP server connection status and available tools."""

        def __init__(self, mcp_status: Dict[str, Any]):
            super().__init__()
            self.mcp_status = mcp_status

        def compose(self) -> ComposeResult:
            from textual.widgets import Static

            with Container(id="mcp_status_container"):
                yield Label("🔌 MCP Server Status", id="mcp_status_header")
                total_servers = len(self.mcp_status.get("servers", []))
                total_tools = self.mcp_status.get("total_tools", 0)
                yield Label(
                    f"{total_servers} server(s) connected • {total_tools} tools available",
                    id="mcp_status_summary",
                )
                with VerticalScroll(id="mcp_servers_list"):
                    servers = self.mcp_status.get("servers", [])
                    if servers:
                        for server in servers:
                            status_icon = "✅" if server.get("connected", False) else "❌"
                            name = server.get("name", "Unknown")
                            tool_count = len(server.get("tools", []))
                            state = server.get("state", "unknown")
                            tools_preview = ", ".join(server.get("tools", [])[:5])
                            if len(server.get("tools", [])) > 5:
                                tools_preview += "..."

                            yield Static(
                                f"{status_icon} [bold]{name}[/]\n" f"   Tools: {tool_count} available\n" f"   State: {state}\n" f"   [dim]{tools_preview}[/]",
                                classes="mcp-server-item",
                                markup=True,
                            )
                    else:
                        yield Static(
                            "[dim]No MCP servers connected[/]",
                            markup=True,
                        )
                yield Button("Close (ESC)", id="close_mcp_button")

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "close_mcp_button":
                self.dismiss()

        def key_escape(self) -> None:
            self.dismiss()

    class AnswerBrowserModal(BaseModal):
        """Modal for browsing all answers with filtering and details."""

        def __init__(
            self,
            answers: List[Dict[str, Any]],
            votes: List[Dict[str, Any]],
            agent_ids: List[str],
            winner_agent_id: Optional[str] = None,
        ):
            super().__init__()
            self.answers = answers
            self.votes = votes
            self.agent_ids = agent_ids
            self.winner_agent_id = winner_agent_id
            self._current_filter: Optional[str] = None  # None = all agents
            self._selected_answer_idx: int = 0

        def compose(self) -> ComposeResult:
            with Container(id="answer_browser_container"):
                yield Label("📋 Answer Browser", id="answer_browser_header")

                # Summary stats
                total_answers = len(self.answers)
                total_votes = len(self.votes)
                yield Label(
                    f"{total_answers} answers • {total_votes} votes",
                    id="answer_browser_summary",
                )

                # Agent filter
                with Horizontal(id="answer_filter_row"):
                    yield Label("Filter: ", id="filter_label")
                    options = [("All Agents", None)] + [(aid, aid) for aid in self.agent_ids]
                    yield Select(options, id="agent_filter", value=None)

                # Answer list (populated in on_mount)
                yield VerticalScroll(id="answer_list")

                # Answer detail panel
                with Container(id="answer_detail_panel"):
                    yield Label("Select an answer to view details", id="answer_detail_content")

                # Buttons
                with Horizontal(id="answer_browser_buttons"):
                    yield Button("Close (ESC)", id="close_browser_button")

        def on_mount(self) -> None:
            """Called when modal is mounted - populate the answer list."""
            self._render_answers()

        def _render_answers(self) -> None:
            """Render the answer list based on current filter."""
            from textual.widgets import Static

            answer_list = self.query_one("#answer_list", VerticalScroll)
            answer_list.remove_children()

            filtered = self.answers
            if self._current_filter:
                filtered = [a for a in self.answers if a["agent_id"] == self._current_filter]

            if not filtered:
                answer_list.mount(Static("[dim]No answers yet[/]", markup=True))
                return

            for idx, answer in enumerate(filtered):
                agent_id = answer["agent_id"]
                model = answer.get("model", "")
                answer_label = answer.get("answer_label", f"{agent_id}.{answer.get('answer_number', 1)}")
                timestamp = answer.get("timestamp", 0)
                is_winner = answer.get("is_winner", False) or agent_id == self.winner_agent_id

                # Format timestamp
                import datetime as dt_module

                time_str = dt_module.datetime.fromtimestamp(timestamp).strftime("%H:%M:%S") if timestamp else ""

                # Build display
                badge = ""
                if is_winner:
                    badge = " [bold yellow]🏆 WINNER[/]"
                elif answer.get("is_final"):
                    badge = " [bold green]✓ FINAL[/]"

                agent_display = f"{agent_id}" + (f" ({model})" if model else "")

                # Count votes for this agent
                vote_count = len([v for v in self.votes if v["voted_for"] == agent_id])

                # Build content preview
                content = answer.get("content", "")
                content_preview = content[:80] + "..." if len(content) > 80 else content
                content_preview = content_preview.replace("\n", " ")

                answer_list.mount(
                    Static(
                        f"[bold]{answer_label}[/] - {agent_display}{badge}\n" f"   [dim]{time_str}[/] • {vote_count} votes\n" f"   [dim]{content_preview}[/]",
                        classes="answer-item",
                        markup=True,
                    ),
                )

        def on_select_changed(self, event: Select.Changed) -> None:
            """Handle agent filter change."""
            self._current_filter = event.value
            self._render_answers()

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "close_browser_button":
                self.dismiss()

        def key_escape(self) -> None:
            self.dismiss()

    class TimelineModal(BaseModal):
        """Modal showing ASCII timeline visualization of answers and votes."""

        def __init__(
            self,
            answers: List[Dict[str, Any]],
            votes: List[Dict[str, Any]],
            agent_ids: List[str],
            winner_agent_id: Optional[str] = None,
        ):
            super().__init__()
            self.answers = answers
            self.votes = votes
            self.agent_ids = agent_ids
            self.winner_agent_id = winner_agent_id

        def compose(self) -> ComposeResult:
            from textual.widgets import Static

            with Container(id="timeline_container"):
                yield Label("📊 Timeline", id="timeline_header")
                yield Label(
                    "○ = answer, ◇ = vote, ★ = final/winner",
                    id="timeline_legend",
                )
                with VerticalScroll(id="timeline_content"):
                    yield Static(self._render_timeline(), id="timeline_diagram", markup=True)
                yield Button("Close (ESC)", id="close_timeline_button")

        def _render_timeline(self) -> str:
            """Render ASCII timeline visualization."""
            # Get unique agents from answers and votes, preserving order
            seen = set()
            all_agents = []
            for a in self.answers:
                if a["agent_id"] not in seen:
                    seen.add(a["agent_id"])
                    all_agents.append(a["agent_id"])
            for v in self.votes:
                if v["voter"] not in seen:
                    seen.add(v["voter"])
                    all_agents.append(v["voter"])
                if v["voted_for"] not in seen:
                    seen.add(v["voted_for"])
                    all_agents.append(v["voted_for"])

            if not all_agents:
                return "[dim]No activity yet[/]"

            # Collect events with timestamps
            events = []

            for answer in self.answers:
                events.append(
                    {
                        "type": "answer",
                        "agent_id": answer["agent_id"],
                        "label": answer.get("answer_label", ""),
                        "timestamp": answer.get("timestamp", 0),
                        "is_winner": answer.get("is_winner", False) or answer["agent_id"] == self.winner_agent_id,
                    },
                )

            for vote in self.votes:
                events.append(
                    {
                        "type": "vote",
                        "agent_id": vote["voter"],
                        "target": vote["voted_for"],
                        "timestamp": vote.get("timestamp", 0),
                    },
                )

            # Sort by timestamp
            events.sort(key=lambda e: e.get("timestamp", 0))

            if not events:
                return "[dim]No activity yet[/]"

            # Build simple text-based timeline
            lines = []
            lines.append("[bold cyan]Event Timeline[/]")
            lines.append("─" * 50)

            for i, event in enumerate(events, 1):
                import datetime as dt_module

                ts = event.get("timestamp", 0)
                time_str = dt_module.datetime.fromtimestamp(ts).strftime("%H:%M:%S") if ts else "??:??:??"

                if event["type"] == "answer":
                    agent = event["agent_id"]
                    label = event.get("label", "")
                    if event.get("is_winner"):
                        lines.append(f"  [dim]{time_str}[/]  [bold yellow]★[/] [bold]{agent}[/] submitted answer [yellow]{label}[/] [bold yellow](WINNER)[/]")
                    else:
                        lines.append(f"  [dim]{time_str}[/]  [green]○[/] [bold]{agent}[/] submitted answer [cyan]{label}[/]")
                elif event["type"] == "vote":
                    voter = event["agent_id"]
                    target = event.get("target", "?")
                    lines.append(f"  [dim]{time_str}[/]  [magenta]◇[/] [bold]{voter}[/] voted for [cyan]{target}[/]")

            lines.append("─" * 50)

            # Summary
            answer_count = len([e for e in events if e["type"] == "answer"])
            vote_count = len([e for e in events if e["type"] == "vote"])
            lines.append(f"[dim]Total: {answer_count} answers, {vote_count} votes[/]")

            return "\n".join(lines)

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "close_timeline_button":
                self.dismiss()

        def key_escape(self) -> None:
            self.dismiss()

    class BrowserTabsModal(BaseModal):
        """Unified browser modal with tabs for Answers, Votes, Workspace, and Timeline."""

        BINDINGS = [
            Binding("1", "tab_answers", "Answers"),
            Binding("2", "tab_votes", "Votes"),
            Binding("3", "tab_workspace", "Workspace"),
            Binding("4", "tab_timeline", "Timeline"),
            Binding("escape", "close", "Close"),
        ]

        def __init__(
            self,
            answers: List[Dict[str, Any]],
            votes: List[Dict[str, Any]],
            vote_counts: Dict[str, int],
            agent_ids: List[str],
            winner_agent_id: Optional[str] = None,
        ):
            super().__init__()
            self.answers = answers
            self.votes = votes
            self.vote_counts = vote_counts
            self.agent_ids = agent_ids
            self.winner_agent_id = winner_agent_id
            self._current_tab = "answers"

        def compose(self) -> ComposeResult:
            with Container(id="browser_tabs_container"):
                yield Static(
                    "[bold]1[/] Answers  [bold]2[/] Votes  [bold]3[/] Workspace  [bold]4[/] Timeline",
                    id="browser_tab_bar",
                )
                yield Static(self._render_current_tab(), id="browser_content")
                yield Button("Close (ESC)", id="close_browser_button")

        def _render_current_tab(self) -> str:
            """Render content for the current tab."""
            if self._current_tab == "answers":
                return self._render_answers_tab()
            elif self._current_tab == "votes":
                return self._render_votes_tab()
            elif self._current_tab == "workspace":
                return self._render_workspace_tab()
            elif self._current_tab == "timeline":
                return self._render_timeline_tab()
            return ""

        def _render_answers_tab(self) -> str:
            """Render answers list."""
            if not self.answers:
                return "[dim]No answers yet[/]"

            lines = ["[bold cyan]📝 Answers[/]", "─" * 50]

            for i, answer in enumerate(self.answers, 1):
                agent = answer.get("agent_id", "?")[:12]
                model = answer.get("model", "")[:15]
                label = answer.get("answer_label", f"#{i}")
                is_winner = answer.get("is_winner", False) or answer.get("agent_id") == self.winner_agent_id

                badge = " [bold yellow]🏆[/]" if is_winner else ""
                model_info = f" ({model})" if model else ""

                # Content preview
                content = answer.get("content", "")[:60].replace("\n", " ")
                if len(answer.get("content", "")) > 60:
                    content += "..."

                lines.append(f"  {i}. [bold]{agent}[/]{model_info} - {label}{badge}")
                lines.append(f"     [dim]{content}[/]")

            return "\n".join(lines)

        def _render_votes_tab(self) -> str:
            """Render vote distribution and individual votes."""
            lines = ["[bold cyan]🗳️ Votes[/]", "─" * 50]

            # Vote distribution
            if self.vote_counts:
                non_zero = {k: v for k, v in self.vote_counts.items() if v > 0}
                if non_zero:
                    max_votes = max(non_zero.values())
                    total = sum(non_zero.values())
                    lines.append("\n[bold]Distribution:[/]")
                    for agent, count in sorted(non_zero.items(), key=lambda x: -x[1]):
                        bar_width = int((count / max_votes) * 15) if max_votes > 0 else 0
                        bar = "█" * bar_width + "░" * (15 - bar_width)
                        prefix = "🏆 " if count == max_votes else "   "
                        pct = (count / total * 100) if total > 0 else 0
                        lines.append(f"{prefix}{agent[:10]:10} {bar} {count} ({pct:.0f}%)")

            # Individual votes
            if self.votes:
                lines.append("\n[bold]Vote History:[/]")
                for i, vote in enumerate(self.votes, 1):
                    voter = vote.get("voter", "?")[:10]
                    target = vote.get("voted_for", "?")[:10]
                    lines.append(f"  {i}. [dim]{voter}[/] → [bold]{target}[/]")
            elif not self.vote_counts:
                lines.append("[dim]No votes yet[/]")

            return "\n".join(lines)

        def _render_workspace_tab(self) -> str:
            """Render workspace info summary."""
            if not self.answers:
                return "[dim]No workspaces available yet[/]"

            lines = ["[bold cyan]📁 Workspaces[/]", "─" * 50]
            lines.append("[dim]Tip: Press 'w' for full workspace browser[/]\n")

            for i, answer in enumerate(self.answers, 1):
                agent = answer.get("agent_id", "?")[:12]
                workspace = answer.get("workspace_path", "")

                if workspace:
                    import os

                    if os.path.isdir(workspace):
                        try:
                            file_count = sum(1 for f in os.listdir(workspace) if os.path.isfile(os.path.join(workspace, f)))
                            lines.append(f"  {i}. [bold]{agent}[/]: {file_count} files")
                        except Exception:
                            lines.append(f"  {i}. [bold]{agent}[/]: [dim]path unavailable[/]")
                    else:
                        lines.append(f"  {i}. [bold]{agent}[/]: [dim]no workspace[/]")
                else:
                    lines.append(f"  {i}. [bold]{agent}[/]: [dim]no workspace[/]")

            return "\n".join(lines)

        def _render_timeline_tab(self) -> str:
            """Render timeline summary."""
            lines = ["[bold cyan]📅 Timeline[/]", "─" * 50]
            lines.append("[dim]Tip: Press 't' for detailed timeline[/]\n")

            # Build events from answers and votes
            events = []
            for answer in self.answers:
                events.append(
                    {
                        "type": "answer",
                        "timestamp": answer.get("timestamp", 0),
                        "agent": answer.get("agent_id", "?")[:10],
                        "label": answer.get("answer_label", "?"),
                        "is_winner": answer.get("is_winner", False) or answer.get("agent_id") == self.winner_agent_id,
                    },
                )
            for vote in self.votes:
                events.append(
                    {
                        "type": "vote",
                        "timestamp": vote.get("timestamp", 0),
                        "voter": vote.get("voter", "?")[:10],
                        "target": vote.get("voted_for", "?")[:10],
                    },
                )

            # Sort by timestamp
            events.sort(key=lambda x: x.get("timestamp", 0))

            for event in events[-10:]:  # Last 10 events
                import datetime as dt_module

                ts = event.get("timestamp", 0)
                time_str = dt_module.datetime.fromtimestamp(ts).strftime("%H:%M:%S") if ts else "??:??:??"

                if event["type"] == "answer":
                    symbol = "★" if event.get("is_winner") else "○"
                    lines.append(f"  {time_str} {symbol} {event['agent']} → {event['label']}")
                else:
                    lines.append(f"  {time_str} ◇ {event['voter']} → {event['target']}")

            lines.append(f"\n[dim]Total: {len(self.answers)} answers, {len(self.votes)} votes[/]")
            return "\n".join(lines)

        def _switch_tab(self, tab: str) -> None:
            """Switch to a different tab."""
            self._current_tab = tab
            try:
                content = self.query_one("#browser_content", Static)
                content.update(self._render_current_tab())

                # Update tab bar to show active tab
                tab_bar = self.query_one("#browser_tab_bar", Static)
                tabs = ["answers", "votes", "workspace", "timeline"]
                tab_labels = ["Answers", "Votes", "Workspace", "Timeline"]
                parts = []
                for i, (t, label) in enumerate(zip(tabs, tab_labels), 1):
                    if t == tab:
                        parts.append(f"[bold reverse] {i} {label} [/]")
                    else:
                        parts.append(f"[bold]{i}[/] {label}")
                tab_bar.update("  ".join(parts))
            except Exception:
                pass

        def action_tab_answers(self) -> None:
            """Switch to answers tab."""
            self._switch_tab("answers")

        def action_tab_votes(self) -> None:
            """Switch to votes tab."""
            self._switch_tab("votes")

        def action_tab_workspace(self) -> None:
            """Switch to workspace tab."""
            self._switch_tab("workspace")

        def action_tab_timeline(self) -> None:
            """Switch to timeline tab."""
            self._switch_tab("timeline")

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "close_browser_button":
                self.dismiss()

        def key_escape(self) -> None:
            self.dismiss()

    class WorkspaceBrowserModal(BaseModal):
        """Modal for browsing workspace files from answer snapshots."""

        def __init__(
            self,
            answers: List[Dict[str, Any]],
            agent_ids: List[str],
        ):
            super().__init__()
            self.answers = answers
            self.agent_ids = agent_ids
            # Default to most recent answer (last in list)
            self._selected_answer_idx: int = len(answers) - 1 if answers else 0
            self._current_files: List[Dict[str, Any]] = []
            self._selected_file_idx: int = 0
            self._load_counter: int = 0  # Counter to ensure unique widget IDs

        def compose(self) -> ComposeResult:
            with Container(id="workspace_browser_container"):
                yield Label("📁 Workspace Browser", id="workspace_browser_header")

                # Answer selector
                with Horizontal(id="workspace_answer_row"):
                    yield Label("Answer: ", id="workspace_answer_label")
                    # Build answer options - most recent answer selected by default
                    if self.answers:
                        options = [(f"{a.get('answer_label', f'Answer {i+1}')} - {a['agent_id']}", i) for i, a in enumerate(self.answers)]
                        default_idx = len(self.answers) - 1  # Most recent
                    else:
                        options = [("No answers yet", -1)]
                        default_idx = -1
                    yield Select(options, id="answer_selector", value=default_idx)

                # Split view: file list on left, preview on right
                with Horizontal(id="workspace_split"):
                    # File list
                    with Container(id="workspace_file_list_container"):
                        yield Label("[bold]Files[/]", id="file_list_header", markup=True)
                        yield VerticalScroll(id="workspace_file_list")

                    # File preview
                    with Container(id="workspace_preview_container"):
                        yield Label("[bold]Preview[/]", id="preview_header", markup=True)
                        yield VerticalScroll(id="workspace_preview")

                yield Button("Close (ESC)", id="close_workspace_browser_button")

        def on_mount(self) -> None:
            """Load files for the most recent answer."""
            if self.answers:
                # Load most recent answer (last in list)
                self._load_workspace_files(len(self.answers) - 1)

        def _load_workspace_files(self, answer_idx: int) -> None:
            """Load files from the workspace path of the selected answer."""
            import os

            from textual.widgets import Static

            file_list = self.query_one("#workspace_file_list", VerticalScroll)
            file_list.remove_children()
            self._current_files = []
            self._load_counter += 1  # Increment to ensure unique IDs

            if answer_idx < 0 or answer_idx >= len(self.answers):
                file_list.mount(Static("[dim]No answer selected[/]", markup=True))
                return

            answer = self.answers[answer_idx]
            workspace_path = answer.get("workspace_path")

            if not workspace_path or not os.path.isdir(workspace_path):
                file_list.mount(Static(f"[dim]No workspace available[/]\n[dim]{workspace_path or 'N/A'}[/]", markup=True))
                return

            # List files in workspace
            try:
                files = []
                for root, dirs, filenames in os.walk(workspace_path):
                    # Skip hidden directories
                    dirs[:] = [d for d in dirs if not d.startswith(".")]
                    for fname in filenames:
                        if not fname.startswith("."):
                            full_path = os.path.join(root, fname)
                            rel_path = os.path.relpath(full_path, workspace_path)
                            try:
                                stat = os.stat(full_path)
                                files.append(
                                    {
                                        "name": fname,
                                        "rel_path": rel_path,
                                        "full_path": full_path,
                                        "size": stat.st_size,
                                        "mtime": stat.st_mtime,
                                    },
                                )
                            except OSError:
                                pass

                self._current_files = sorted(files, key=lambda f: f["rel_path"])

                if not self._current_files:
                    file_list.mount(Static("[dim]Workspace is empty[/]", markup=True))
                    return

                for idx, f in enumerate(self._current_files):
                    size_str = self._format_size(f["size"])
                    file_list.mount(
                        Static(
                            f"[cyan]{f['rel_path']}[/] [dim]({size_str})[/]",
                            id=f"file_item_{self._load_counter}_{idx}",
                            classes="workspace-file-item",
                            markup=True,
                        ),
                    )

                # Auto-select first file
                if self._current_files:
                    self._preview_file(0)

            except Exception as e:
                file_list.mount(Static(f"[red]Error: {e}[/]", markup=True))

        def _format_size(self, size: int) -> str:
            """Format file size in human-readable format."""
            if size < 1024:
                return f"{size}B"
            elif size < 1024 * 1024:
                return f"{size // 1024}KB"
            else:
                return f"{size // (1024 * 1024)}MB"

        def _preview_file(self, file_idx: int) -> None:
            """Preview the selected file with syntax highlighting."""
            from textual.widgets import Static

            preview = self.query_one("#workspace_preview", VerticalScroll)
            preview.remove_children()

            if file_idx < 0 or file_idx >= len(self._current_files):
                preview.mount(Static("[dim]Select a file to preview[/]", markup=True))
                return

            f = self._current_files[file_idx]
            full_path = Path(f["full_path"])

            # Add file header
            header = Static(
                f"[bold cyan]{f['rel_path']}[/]\n[dim]{'─' * 40}[/]",
                markup=True,
            )
            preview.mount(header)

            # Use render_file_preview for syntax highlighting
            renderable, is_rich = render_file_preview(full_path)

            if is_rich:
                # Rich object (Syntax or Markdown)
                preview.mount(Static(renderable))
            else:
                # Plain text or error message
                preview.mount(Static(str(renderable), markup=True))

        def on_select_changed(self, event: Select.Changed) -> None:
            """Handle answer selection change."""
            if event.select.id == "answer_selector":
                answer_idx = event.value
                if isinstance(answer_idx, int) and answer_idx >= 0:
                    self._selected_answer_idx = answer_idx
                    self._load_workspace_files(answer_idx)

        def on_click(self, event) -> None:
            """Handle click on file items."""
            # Check if clicked on a file item
            if hasattr(event, "widget") and event.widget:
                widget_id = getattr(event.widget, "id", "")
                # ID format is now: file_item_{load_counter}_{idx}
                if widget_id and widget_id.startswith("file_item_"):
                    try:
                        # Get the last part which is the file index
                        idx = int(widget_id.split("_")[-1])
                        self._selected_file_idx = idx
                        self._preview_file(idx)
                    except (ValueError, IndexError):
                        pass

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "close_workspace_browser_button":
                self.dismiss()

        def key_escape(self) -> None:
            self.dismiss()

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
            from textual.widgets import ListItem, ListView

            with Container(id="selector_container"):
                yield Label("Select an option:", id="selector_header")

                items = [ListItem(Label(f"📄 View {agent_id}")) for agent_id in self.agent_ids]
                items.append(ListItem(Label("🎤 View Final Presentation Transcript")))
                items.append(ListItem(Label("📊 View System Status")))
                items.append(ListItem(Label("📋 View Coordination Table")))
                items.append(ListItem(Label("💰 View Cost Breakdown")))
                items.append(ListItem(Label("📁 View Workspace Files")))
                items.append(ListItem(Label("📈 View Tool Metrics")))

                yield ListView(*items, id="agent_list")
                yield Button("Cancel (ESC)", id="cancel_button")

        def on_list_view_selected(self, event):
            """Handle selection from list."""

            index = event.list_view.index
            num_agents = len(self.agent_ids)

            if index < num_agents:
                agent_id = self.agent_ids[index]
                path = self.coordination_display.agent_files.get(agent_id)
                if path:
                    self.app_ref._show_text_modal(Path(path), f"{agent_id} Output")
            elif index == num_agents:  # Final Presentation
                path = self.coordination_display.final_presentation_file
                if path:
                    self.app_ref._show_text_modal(Path(path), "Final Presentation")
            elif index == num_agents + 1:  # System Status
                self.app_ref._show_system_status_modal()
            elif index == num_agents + 2:  # Coordination Table
                self.app_ref._show_coordination_table_modal()
            elif index == num_agents + 3:  # Cost Breakdown
                self.app_ref._show_cost_breakdown_modal()
            elif index == num_agents + 4:  # Workspace Files
                self.app_ref._show_workspace_files_modal()
            elif index == num_agents + 5:  # Tool Metrics
                self.app_ref._show_metrics_modal()

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
        """Modal for detailed vote results with distribution visualization."""

        def __init__(
            self,
            results_text: str,
            vote_counts: Optional[Dict[str, int]] = None,
            votes: Optional[List[Dict[str, Any]]] = None,
        ):
            super().__init__()
            self.results_text = results_text
            self.vote_counts = vote_counts or {}
            self.votes = votes or []

        def _render_vote_distribution(self) -> str:
            """Render ASCII bar chart of vote distribution."""
            if not self.vote_counts:
                return ""

            # Filter out zero votes
            non_zero = {k: v for k, v in self.vote_counts.items() if v > 0}
            if not non_zero:
                return ""

            max_votes = max(non_zero.values())
            total_votes = sum(non_zero.values())
            lines = []
            lines.append("[bold cyan]Vote Distribution[/]")
            lines.append("─" * 45)

            # Sort by vote count (descending)
            for agent_id, count in sorted(non_zero.items(), key=lambda x: -x[1]):
                short_id = agent_id[:12]
                bar_width = int((count / max_votes) * 20) if max_votes > 0 else 0
                bar = "█" * bar_width + "░" * (20 - bar_width)
                pct = (count / total_votes * 100) if total_votes > 0 else 0

                # Winner gets trophy
                prefix = "🏆 " if count == max_votes else "   "
                lines.append(f"{prefix}[bold]{short_id:12}[/] {bar} {count}/{total_votes} ({pct:.0f}%)")

            lines.append("")
            return "\n".join(lines)

        def _render_vote_details(self) -> str:
            """Render individual vote details."""
            if not self.votes:
                return ""

            lines = []
            lines.append("[bold cyan]Individual Votes[/]")
            lines.append("─" * 45)

            for i, vote in enumerate(self.votes, 1):
                voter = vote.get("voter", "?")[:10]
                target = vote.get("voted_for", "?")[:10]
                reason = vote.get("reason", "")[:40]
                lines.append(f"  {i}. [dim]{voter}[/] → [bold]{target}[/]")
                if reason:
                    lines.append(f"     [italic dim]{reason}[/]")

            lines.append("")
            return "\n".join(lines)

        def compose(self) -> ComposeResult:
            # Build combined content
            distribution = self._render_vote_distribution()
            details = self._render_vote_details()

            # Combine distribution, details, and original text
            combined_parts = []
            if distribution:
                combined_parts.append(distribution)
            if details:
                combined_parts.append(details)
            if self.results_text:
                combined_parts.append("[bold cyan]Vote Summary[/]\n" + "─" * 45 + "\n" + self.results_text)

            full_content = "\n".join(combined_parts) if combined_parts else "No votes recorded."

            with Container(id="vote_results_container"):
                yield Label("🗳️ Voting Results", id="vote_header")
                yield Static(full_content, id="vote_results_content")
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

    class CostBreakdownModal(BaseModal):
        """Modal to display token usage and cost breakdown per agent."""

        def __init__(self, display: TextualTerminalDisplay):
            super().__init__()
            self.coordination_display = display

        def compose(self) -> ComposeResult:
            with Container(id="cost_breakdown_container"):
                yield Label("💰 Cost Breakdown", id="cost_header")
                yield TextArea(self._build_cost_table(), id="cost_content", read_only=True)
                yield Button("Close (ESC)", id="close_cost_button")

        def _build_cost_table(self) -> str:
            """Build a formatted cost breakdown table."""
            orchestrator = getattr(self.coordination_display, "orchestrator", None)
            if not orchestrator:
                return "No orchestrator available. Complete a turn first."

            agents = getattr(orchestrator, "agents", {})
            if not agents:
                return "No agents available."

            lines = []
            lines.append("Agent         │ Input   │ Output  │ Reason  │ Cached  │ Total   │ Cost")
            lines.append("──────────────┼─────────┼─────────┼─────────┼─────────┼─────────┼────────")

            total_input = 0
            total_output = 0
            total_reasoning = 0
            total_cached = 0
            total_all = 0
            total_cost = 0.0

            for agent_id, agent in agents.items():
                backend = getattr(agent, "backend", None)
                if not backend:
                    continue

                usage = backend.get_token_usage()
                input_tok = usage.input_tokens
                output_tok = usage.output_tokens
                reasoning_tok = usage.reasoning_tokens
                cached_tok = usage.cached_input_tokens
                total_tok = input_tok + output_tok + reasoning_tok
                cost = usage.estimated_cost

                total_input += input_tok
                total_output += output_tok
                total_reasoning += reasoning_tok
                total_cached += cached_tok
                total_all += total_tok
                total_cost += cost

                agent_name = agent_id[:12].ljust(12)
                lines.append(
                    f"{agent_name}  │ {input_tok:>7,} │ {output_tok:>7,} │ " f"{reasoning_tok:>7,} │ {cached_tok:>7,} │ {total_tok:>7,} │ ${cost:>6.4f}",
                )

            lines.append("──────────────┼─────────┼─────────┼─────────┼─────────┼─────────┼────────")
            lines.append(
                f"TOTAL         │ {total_input:>7,} │ {total_output:>7,} │ " f"{total_reasoning:>7,} │ {total_cached:>7,} │ {total_all:>7,} │ ${total_cost:>6.4f}",
            )

            return "\n".join(lines)

    class WorkspaceFilesModal(BaseModal):
        """Modal to display workspace files and open workspace directory."""

        def __init__(self, display: TextualTerminalDisplay, app: "TextualApp"):
            super().__init__()
            self.coordination_display = display
            self.app_ref = app
            self.workspace_path = self._get_workspace_path()

        def _get_workspace_path(self) -> Optional[Path]:
            """Get the workspace directory path."""
            orchestrator = getattr(self.coordination_display, "orchestrator", None)
            if not orchestrator:
                return None
            workspace_dir = getattr(orchestrator, "workspace_dir", None)
            if workspace_dir:
                return Path(workspace_dir)
            return None

        def compose(self) -> ComposeResult:
            with Container(id="workspace_container"):
                yield Label("📁 Workspace Files", id="workspace_header")
                yield TextArea(self._build_file_list(), id="workspace_content", read_only=True)
                with Horizontal(id="workspace_buttons"):
                    yield Button("Open Workspace", id="open_workspace_button")
                    yield Button("Close (ESC)", id="close_workspace_button")

        def _build_file_list(self) -> str:
            """Build a list of files in the workspace."""
            if not self.workspace_path or not self.workspace_path.exists():
                return "No workspace directory available."

            lines = [f"Workspace: {self.workspace_path}", ""]

            try:
                files = list(self.workspace_path.rglob("*"))
                files = [f for f in files if f.is_file()]

                if not files:
                    lines.append("No files in workspace.")
                else:
                    lines.append(f"Files ({len(files)} total):")
                    lines.append("-" * 50)

                    # Show first 20 files
                    for f in sorted(files)[:20]:
                        rel_path = f.relative_to(self.workspace_path)
                        size = f.stat().st_size
                        size_str = self._format_size(size)
                        lines.append(f"  {rel_path} ({size_str})")

                    if len(files) > 20:
                        lines.append(f"  ... and {len(files) - 20} more files")

            except Exception as e:
                lines.append(f"Error reading workspace: {e}")

            return "\n".join(lines)

        def _format_size(self, size: int) -> str:
            """Format file size in human-readable form."""
            for unit in ["B", "KB", "MB", "GB"]:
                if size < 1024:
                    return f"{size:.1f} {unit}" if unit != "B" else f"{size} {unit}"
                size /= 1024
            return f"{size:.1f} TB"

        def on_button_pressed(self, event: Button.Pressed) -> None:
            """Handle button presses."""
            if event.button.id == "open_workspace_button":
                self._open_workspace()
            elif event.button.id == "close_workspace_button":
                self.dismiss()

        def _open_workspace(self) -> None:
            """Open the workspace directory in the system file browser."""
            import platform
            import subprocess

            if not self.workspace_path or not self.workspace_path.exists():
                self.app_ref.notify("No workspace directory available", severity="warning")
                return

            try:
                system = platform.system()
                if system == "Darwin":  # macOS
                    subprocess.run(["open", str(self.workspace_path)])
                elif system == "Windows":
                    subprocess.run(["explorer", str(self.workspace_path)])
                else:  # Linux
                    subprocess.run(["xdg-open", str(self.workspace_path)])
                self.app_ref.notify(f"Opened: {self.workspace_path}", severity="information")
            except Exception as e:
                self.app_ref.notify(f"Error opening workspace: {e}", severity="error")

    class ContextModal(BaseModal):
        """Modal for managing context paths."""

        def __init__(self, display: TextualTerminalDisplay, app: "TextualApp"):
            super().__init__()
            self.coordination_display = display
            self.app_ref = app
            self.current_paths = self._get_current_paths()

        def _get_current_paths(self) -> List[str]:
            """Get current context paths from orchestrator config."""
            orchestrator = getattr(self.coordination_display, "orchestrator", None)
            if not orchestrator:
                return []
            orchestrator_cfg = getattr(orchestrator, "config", {})
            return orchestrator_cfg.get("context_paths", [])

        def compose(self) -> ComposeResult:
            with Container(id="context_container"):
                yield Label("📂 Context Paths", id="context_header")
                yield Label("Current paths that agents can access:", id="context_hint")
                yield TextArea(
                    self._format_paths(),
                    id="context_current_paths",
                    read_only=True,
                )
                yield Label("Add new path:", id="add_path_label")
                yield Input(placeholder="Enter path to add...", id="new_path_input")
                with Horizontal(id="context_buttons"):
                    yield Button("Add Path", id="add_path_button")
                    yield Button("Close (ESC)", id="close_context_button")

        def _format_paths(self) -> str:
            """Format current paths for display."""
            if not self.current_paths:
                return "No context paths configured."
            return "\n".join(f"  • {path}" for path in self.current_paths)

        def on_button_pressed(self, event: Button.Pressed) -> None:
            """Handle button presses."""
            if event.button.id == "add_path_button":
                self._add_path()
            elif event.button.id == "close_context_button":
                self.dismiss()

        def _add_path(self) -> None:
            """Add a new context path."""
            input_widget = self.query_one("#new_path_input", Input)
            new_path = input_widget.value.strip()

            if not new_path:
                self.app_ref.notify("Please enter a path", severity="warning")
                return

            path = Path(new_path).expanduser().resolve()
            if not path.exists():
                self.app_ref.notify(f"Path does not exist: {new_path}", severity="warning")
                return

            if str(path) in self.current_paths:
                self.app_ref.notify("Path already in context", severity="warning")
                return

            self.current_paths.append(str(path))
            self._update_orchestrator_paths()
            input_widget.value = ""

            # Refresh the display
            paths_area = self.query_one("#context_current_paths", TextArea)
            paths_area.load_text(self._format_paths())
            self.app_ref.notify(f"Added: {path}", severity="information")

        def _update_orchestrator_paths(self) -> None:
            """Update the orchestrator config with new paths."""
            orchestrator = getattr(self.coordination_display, "orchestrator", None)
            if orchestrator:
                if hasattr(orchestrator, "config"):
                    orchestrator.config["context_paths"] = self.current_paths.copy()

    class MetricsModal(BaseModal):
        """Modal to display tool execution metrics."""

        def __init__(self, display: TextualTerminalDisplay):
            super().__init__()
            self.coordination_display = display

        def compose(self) -> ComposeResult:
            with Container(id="metrics_container"):
                yield Label("📊 Tool Metrics", id="metrics_header")
                yield TextArea(self._build_metrics_table(), id="metrics_content", read_only=True)
                yield Button("Close (ESC)", id="close_metrics_button")

        def _build_metrics_table(self) -> str:
            """Build a formatted metrics table."""
            orchestrator = getattr(self.coordination_display, "orchestrator", None)
            if not orchestrator:
                return "No orchestrator available. Complete a turn first."

            # Try to get tool metrics from orchestrator or agents
            tool_metrics = self._collect_tool_metrics(orchestrator)

            if not tool_metrics:
                return "No tool execution metrics available yet."

            lines = []
            lines.append("Tool Name                │ Calls │ Success │ Failed │ Avg Time")
            lines.append("─────────────────────────┼───────┼─────────┼────────┼──────────")

            for tool_name, metrics in sorted(tool_metrics.items()):
                calls = metrics.get("calls", 0)
                success = metrics.get("success", 0)
                failed = metrics.get("failed", 0)
                avg_time = metrics.get("avg_time", 0.0)

                tool_display = tool_name[:23].ljust(23)
                lines.append(
                    f"{tool_display}  │ {calls:>5} │ {success:>7} │ {failed:>6} │ {avg_time:>7.2f}s",
                )

            return "\n".join(lines)

        def _collect_tool_metrics(self, orchestrator) -> Dict[str, Dict[str, Any]]:
            """Collect tool metrics from the orchestrator or agents."""
            metrics = {}

            # Try to get metrics from orchestrator's tool tracker if available
            tool_tracker = getattr(orchestrator, "tool_tracker", None)
            if tool_tracker:
                raw_metrics = getattr(tool_tracker, "metrics", {})
                for tool_name, data in raw_metrics.items():
                    metrics[tool_name] = {
                        "calls": data.get("call_count", 0),
                        "success": data.get("success_count", 0),
                        "failed": data.get("call_count", 0) - data.get("success_count", 0),
                        "avg_time": data.get("avg_duration", 0.0),
                    }
                return metrics

            # Fallback: try to collect from agents
            agents = getattr(orchestrator, "agents", {})
            for agent_id, agent in agents.items():
                backend = getattr(agent, "backend", None)
                if not backend:
                    continue
                tool_stats = getattr(backend, "tool_execution_stats", {})
                for tool_name, stats in tool_stats.items():
                    if tool_name not in metrics:
                        metrics[tool_name] = {
                            "calls": 0,
                            "success": 0,
                            "failed": 0,
                            "total_time": 0.0,
                        }
                    metrics[tool_name]["calls"] += stats.get("calls", 0)
                    metrics[tool_name]["success"] += stats.get("success", 0)
                    metrics[tool_name]["failed"] += stats.get("failed", 0)
                    metrics[tool_name]["total_time"] += stats.get("total_time", 0.0)

            # Calculate averages
            for tool_name in metrics:
                calls = metrics[tool_name]["calls"]
                if calls > 0:
                    metrics[tool_name]["avg_time"] = metrics[tool_name].get("total_time", 0.0) / calls
                else:
                    metrics[tool_name]["avg_time"] = 0.0

            return metrics

    class BroadcastPromptModal(BaseModal):
        """Modal for handling human input requests from agents during broadcast."""

        def __init__(self, sender_agent_id: str, question: str, timeout: int, app: "TextualApp"):
            super().__init__()
            self.sender_agent_id = sender_agent_id
            self.question = question
            self.timeout = timeout
            self.app_ref = app
            self.response: Optional[str] = None
            self._start_time = time.time()

        def compose(self) -> ComposeResult:
            with Container(id="broadcast_container"):
                yield Label("⏸ ALL AGENTS PAUSED - HUMAN INPUT NEEDED ⏸", id="broadcast_banner")
                yield Label(f"From: {self.sender_agent_id}", id="broadcast_sender")
                yield Label("Question:", id="broadcast_question_label")
                yield TextArea(self.question, id="broadcast_question", read_only=True)
                yield Label(f"Timeout: {self.timeout}s", id="broadcast_timeout")
                yield Label("Your response:", id="response_label")
                yield Input(placeholder="Type your response here...", id="broadcast_input")
                with Horizontal(id="broadcast_buttons"):
                    yield Button("Submit", id="submit_broadcast_button", variant="primary")
                    yield Button("Skip", id="skip_broadcast_button")

        def on_button_pressed(self, event: Button.Pressed) -> None:
            """Handle button presses."""
            if event.button.id == "submit_broadcast_button":
                input_widget = self.query_one("#broadcast_input", Input)
                self.response = input_widget.value.strip() or None
                self.dismiss(self.response)
            elif event.button.id == "skip_broadcast_button":
                self.response = None
                self.dismiss(None)

        def on_input_submitted(self, event: Input.Submitted) -> None:
            """Handle Enter key in input."""
            if event.input.id == "broadcast_input":
                self.response = event.value.strip() or None
                self.dismiss(self.response)

    class FileInspectionModal(BaseModal):
        """Modal for inspecting files in the workspace with tree view and preview."""

        def __init__(self, workspace_path: Path, app: "TextualApp"):
            super().__init__()
            self.workspace_path = workspace_path
            self.app_ref = app
            self.selected_file: Optional[Path] = None

        def compose(self) -> ComposeResult:
            from textual.widgets import DirectoryTree

            with Container(id="file_inspection_container"):
                yield Label("📁 File Inspection", id="file_inspection_header")
                with Horizontal(id="file_inspection_content"):
                    # Left panel: Directory tree
                    with Container(id="file_tree_panel"):
                        yield Label("Workspace Files:", id="tree_label")
                        if self.workspace_path and self.workspace_path.exists():
                            yield DirectoryTree(str(self.workspace_path), id="workspace_tree")
                        else:
                            yield Label("No workspace available", id="no_workspace_label")
                    # Right panel: File preview
                    with Container(id="file_preview_panel"):
                        yield Label("File Preview:", id="preview_label")
                        yield TextArea("Select a file to preview", id="file_preview", read_only=True)
                with Horizontal(id="file_inspection_buttons"):
                    yield Button("Open in Editor", id="open_editor_button")
                    yield Button("Close (ESC)", id="close_inspection_button")

        def on_directory_tree_file_selected(self, event) -> None:
            """Handle file selection in the tree."""
            self.selected_file = Path(event.path)
            self._update_preview()

        def _update_preview(self) -> None:
            """Update the file preview panel."""
            preview = self.query_one("#file_preview", TextArea)

            if not self.selected_file or not self.selected_file.exists():
                preview.load_text("Select a file to preview")
                return

            if self.selected_file.is_dir():
                preview.load_text(f"Directory: {self.selected_file.name}\n\nSelect a file to view its contents.")
                return

            # Check file size - limit preview to reasonable size
            try:
                file_size = self.selected_file.stat().st_size
                if file_size > 100000:  # 100KB limit
                    preview.load_text(f"File too large to preview ({file_size:,} bytes)\n\nUse 'Open in Editor' to view.")
                    return

                # Try to read as text
                content = self.selected_file.read_text(encoding="utf-8", errors="replace")
                # Limit lines for preview
                lines = content.split("\n")
                if len(lines) > 200:
                    content = "\n".join(lines[:200]) + f"\n\n... ({len(lines) - 200} more lines)"
                preview.load_text(content)
            except Exception as e:
                preview.load_text(f"Cannot preview file: {e}")

        def on_button_pressed(self, event: Button.Pressed) -> None:
            """Handle button presses."""
            if event.button.id == "open_editor_button":
                self._open_in_editor()
            elif event.button.id == "close_inspection_button":
                self.dismiss()

        def _open_in_editor(self) -> None:
            """Open the selected file in the system editor."""
            import platform
            import subprocess

            if not self.selected_file or not self.selected_file.exists():
                self.app_ref.notify("No file selected", severity="warning")
                return

            if self.selected_file.is_dir():
                self.app_ref.notify("Cannot open directory in editor", severity="warning")
                return

            try:
                system = platform.system()
                if system == "Darwin":  # macOS
                    subprocess.run(["open", str(self.selected_file)])
                elif system == "Windows":
                    subprocess.run(["start", str(self.selected_file)], shell=True)
                else:  # Linux
                    subprocess.run(["xdg-open", str(self.selected_file)])
                self.app_ref.notify(f"Opened: {self.selected_file.name}", severity="information")
            except Exception as e:
                self.app_ref.notify(f"Error opening file: {e}", severity="error")

    class AgentOutputModal(BaseModal):
        """Modal for viewing full agent output with syntax highlighting."""

        def __init__(self, agent_id: str, agent_outputs: List[str], model_name: Optional[str] = None):
            super().__init__()
            self.agent_id = agent_id
            self.agent_outputs = agent_outputs
            self.model_name = model_name or "Unknown"

        def compose(self) -> ComposeResult:
            with Container(id="agent_output_container"):
                yield Label(
                    f"📄 Full Output: {self.agent_id} ({self.model_name})",
                    id="agent_output_header",
                )
                yield Label(
                    f"Total lines: {len(self.agent_outputs)}",
                    id="agent_output_stats",
                )
                # Join all outputs and display in scrollable text area
                full_content = "\n".join(self.agent_outputs) if self.agent_outputs else "(No output recorded)"
                yield TextArea(full_content, id="agent_output_text", read_only=True)
                with Horizontal(id="agent_output_buttons"):
                    yield Button("Copy to Clipboard", id="copy_output_button")
                    yield Button("Save to File", id="save_output_button")
                    yield Button("Close (ESC)", id="close_output_button")

        def on_button_pressed(self, event: Button.Pressed) -> None:
            """Handle button presses."""
            if event.button.id == "close_output_button":
                self.dismiss()
            elif event.button.id == "copy_output_button":
                self._copy_to_clipboard()
            elif event.button.id == "save_output_button":
                self._save_to_file()

        def _copy_to_clipboard(self) -> None:
            """Copy output to system clipboard."""
            import platform
            import subprocess

            full_content = "\n".join(self.agent_outputs)
            try:
                system = platform.system()
                if system == "Darwin":  # macOS
                    process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                    process.communicate(full_content.encode("utf-8"))
                elif system == "Windows":
                    process = subprocess.Popen(["clip"], stdin=subprocess.PIPE, shell=True)
                    process.communicate(full_content.encode("utf-8"))
                else:  # Linux
                    process = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
                    process.communicate(full_content.encode("utf-8"))
                self.app.notify(f"Copied {len(self.agent_outputs)} lines to clipboard", severity="information")
            except Exception as e:
                self.app.notify(f"Failed to copy: {e}", severity="error")

        def _save_to_file(self) -> None:
            """Save output to a file in the log directory."""
            from datetime import datetime

            from massgen.logging.log_directory import get_log_session_dir

            try:
                output_dir = get_log_session_dir() / "agent_outputs"
                output_dir.mkdir(parents=True, exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{self.agent_id}_{timestamp}.txt"
                output_path = output_dir / filename

                full_content = "\n".join(self.agent_outputs)
                output_path.write_text(full_content, encoding="utf-8")

                self.app.notify(f"Saved to: {output_path.name}", severity="information")
            except Exception as e:
                self.app.notify(f"Failed to save: {e}", severity="error")

        def key_escape(self) -> None:
            """Close on Escape."""
            self.dismiss()

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
        """Live view of the winning agent's presentation stream with action buttons."""

        def __init__(self, coordination_display: "TextualTerminalDisplay" = None):
            super().__init__(id="final_stream_container")
            self.coordination_display = coordination_display
            self.agent_label = Label("", id="final_stream_label")
            self.log_view = RichLog(id="final_stream_log", highlight=True, markup=True, wrap=True)
            self.current_line_label = Label("", classes="streaming_label")
            self._line_buffer = ""
            self._header_base = ""
            self._vote_summary = ""
            self._is_streaming = False
            self._winner_agent_id = ""
            self._winner_model_name = ""
            self._final_content: List[str] = []
            self.styles.display = "none"

        def compose(self) -> ComposeResult:
            yield self.agent_label
            yield self.log_view
            yield self.current_line_label
            with Horizontal(id="final_stream_buttons", classes="hidden"):
                yield Button("Copy", id="final_copy_button", classes="action-primary")
                yield Button("Save", id="final_save_button")
                yield Button("Workspace", id="final_workspace_button")
            with Container(id="followup_container", classes="hidden"):
                yield Label("Ask a follow-up:", id="followup_label")
                yield Input(placeholder="Type follow-up question...", id="followup_input")

        def begin(self, agent_id: str, model_name: str, vote_results: Dict[str, Any]):
            """Reset panel with agent metadata including model name."""
            self.styles.display = "block"
            self._is_streaming = True
            self._winner_agent_id = agent_id
            self._winner_model_name = model_name or ""
            self._final_content = []
            self.add_class("streaming-active")

            # Build header with model name
            if model_name:
                self._header_base = f"🎤 Final Presentation — {agent_id} ({model_name})"
            else:
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

            # Hide buttons during streaming
            try:
                self.query_one("#final_stream_buttons").add_class("hidden")
                self.query_one("#followup_container").add_class("hidden")
            except Exception:
                pass

        def append_chunk(self, chunk: str):
            """Append streaming text with buffering."""
            if not chunk:
                return

            def log_and_store(line: str):
                self.log_view.write(line)
                self._final_content.append(line)

            self._line_buffer = _process_line_buffer(
                self._line_buffer,
                chunk,
                log_and_store,
            )
            self.current_line_label.update(self._line_buffer)

        def end(self):
            """Mark presentation as complete, show buttons and follow-up input."""
            if self._line_buffer.strip():
                self.log_view.write(self._line_buffer)
                self._final_content.append(self._line_buffer)
            self._line_buffer = ""
            self.current_line_label.update("")
            self._is_streaming = False
            self.remove_class("streaming-active")
            self.add_class("winner-complete")

            header = self._header_base or str(self.agent_label.renderable)
            if self._vote_summary:
                header = f"{header} | {self._vote_summary}"
            self.agent_label.update(f"{header} | ✅ Completed")

            # Show action buttons and follow-up input
            try:
                self.query_one("#final_stream_buttons").remove_class("hidden")
                self.query_one("#followup_container").remove_class("hidden")
            except Exception:
                pass

        def on_button_pressed(self, event: Button.Pressed) -> None:
            """Handle action button presses."""
            if event.button.id == "final_copy_button":
                self._copy_to_clipboard()
            elif event.button.id == "final_save_button":
                self._save_to_file()
            elif event.button.id == "final_workspace_button":
                self._open_workspace()

        def _copy_to_clipboard(self) -> None:
            """Copy final answer to system clipboard."""
            import platform
            import subprocess

            full_content = "\n".join(self._final_content)
            try:
                system = platform.system()
                if system == "Darwin":  # macOS
                    process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                    process.communicate(full_content.encode("utf-8"))
                elif system == "Windows":
                    process = subprocess.Popen(["clip"], stdin=subprocess.PIPE, shell=True)
                    process.communicate(full_content.encode("utf-8"))
                else:  # Linux
                    process = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
                    process.communicate(full_content.encode("utf-8"))
                self.app.notify(f"Copied {len(self._final_content)} lines to clipboard", severity="information")
            except Exception as e:
                self.app.notify(f"Failed to copy: {e}", severity="error")

        def _save_to_file(self) -> None:
            """Save final answer to a file in the log directory."""
            from datetime import datetime

            from massgen.logging.log_directory import get_log_session_dir

            try:
                output_dir = get_log_session_dir() / "final_answers"
                output_dir.mkdir(parents=True, exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"final_answer_{self._winner_agent_id}_{timestamp}.txt"
                output_path = output_dir / filename

                full_content = "\n".join(self._final_content)
                output_path.write_text(full_content, encoding="utf-8")

                self.app.notify(f"Saved to: {output_path.name}", severity="information")
            except Exception as e:
                self.app.notify(f"Failed to save: {e}", severity="error")

        def _open_workspace(self) -> None:
            """Open workspace browser for the winning agent."""
            if not self.coordination_display or not self._winner_agent_id:
                self.app.notify("Cannot open workspace: missing context", severity="warning")
                return

            # Find the app's method to show workspace browser
            try:
                app = self.app
                if hasattr(app, "_show_workspace_browser_for_agent"):
                    app._show_workspace_browser_for_agent(self._winner_agent_id)
                else:
                    self.app.notify("Workspace browser not available", severity="warning")
            except Exception as e:
                self.app.notify(f"Failed to open workspace: {e}", severity="error")

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
