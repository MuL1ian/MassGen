# -*- coding: utf-8 -*-
"""
Textual Terminal Display for MassGen Coordination

"""

import functools
import logging
import os
import re
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Deque, Dict, List, Optional, Set, Tuple

if TYPE_CHECKING:
    from massgen.frontend.displays.textual_widgets.plan_approval_modal import (
        PlanApprovalResult,
    )

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
    from textual.widgets import Button, Footer, Input, Label, RichLog, Static, TextArea

    from .content_handlers import (
        ThinkingContentHandler,
        ToolBatchTracker,
        ToolContentHandler,
    )
    from .content_normalizer import ContentNormalizer

    # Import extracted modals from the new textual/ package
    from .textual import (  # Browser modals; Status modals; Coordination modals; Content modals; Input modals; Shortcuts modal; Workspace modals; Agent output modal
        AgentOutputModal,
        AgentSelectorModal,
        AnswerBrowserModal,
        BroadcastPromptModal,
        BrowserTabsModal,
        ContextModal,
        ConversationHistoryModal,
        CoordinationTableModal,
        CostBreakdownModal,
        FileInspectionModal,
        KeyboardShortcutsModal,
        MCPStatusModal,
        MetricsModal,
        OrchestratorEventsModal,
        StructuredBroadcastPromptModal,
        SystemStatusModal,
        TextContentModal,
        TimelineModal,
        VoteResultsModal,
        WorkspaceBrowserModal,
    )
    from .textual_widgets import (
        AgentStatusRibbon,
        AgentTabBar,
        AgentTabChanged,
        BroadcastModeChanged,
        CompletionFooter,
        ExecutionStatusLine,
        FinalPresentationCard,
        ModeBar,
        ModeChanged,
        MultiLineInput,
        OverrideRequested,
        PathSuggestionDropdown,
        PlanDepthChanged,
        PlanOptionsPopover,
        PlanSelected,
        PlanSettingsClicked,
        QueuedInputBanner,
        SessionInfoClicked,
        SubagentCard,
        SubagentModal,
        TaskPlanCard,
        TaskPlanModal,
        TasksClicked,
        TimelineSection,
        ToolCallCard,
        ToolDetailModal,
        ToolSection,
        ViewPlanRequested,
        ViewSelected,
    )
    from .tui_modes import TuiModeState

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False

# TUI Debug logger - writes to /tmp/massgen_tui_debug.log
_tui_debug_logger: Optional[logging.Logger] = None


def get_tui_debug_logger() -> logging.Logger:
    """Get or create a debug logger for TUI that writes to /tmp."""
    global _tui_debug_logger
    if _tui_debug_logger is None:
        _tui_debug_logger = logging.getLogger("massgen.tui.debug")
        _tui_debug_logger.setLevel(logging.DEBUG)
        # Prevent propagation to root logger
        _tui_debug_logger.propagate = False
        # File handler to /tmp
        handler = logging.FileHandler("/tmp/massgen_tui_debug.log", mode="a")
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        _tui_debug_logger.addHandler(handler)
        # Write startup marker
        _tui_debug_logger.info("=" * 60)
        _tui_debug_logger.info("TUI Debug Session Started")
        _tui_debug_logger.info("=" * 60)
    return _tui_debug_logger


def tui_log(msg: str, level: str = "debug") -> None:
    """Log a debug message to /tmp/massgen_tui_debug.log."""
    log = get_tui_debug_logger()
    if level == "error":
        log.error(msg)
    elif level == "warning":
        log.warning(msg)
    elif level == "info":
        log.info(msg)
    else:
        log.debug(msg)


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
        self.max_buffer_size = kwargs.get("max_buffer_size", 200)  # Max items per agent buffer
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
        self._routing_to_post_eval_card = False  # Bug 2 fix: prevent timeline routing during post-eval

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
            # Faster flush for smoother streaming - 20 FPS (0.05s) provides
            # good balance between smooth appearance and performance
            if self._terminal_type in ("vscode", "windows_terminal"):
                default_buffer_flush = 0.1  # Faster than before (was 0.3s)
            else:
                # 0.05s (20 FPS) for smooth streaming, capped at refresh rate
                adaptive_flush = max(0.05, 1 / max(self.refresh_rate, 1))
                default_buffer_flush = min(adaptive_flush, 0.05)
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

    def reset_turn_state(self) -> None:
        """Reset turn-level state in the display for a new turn.

        Clears final answer state, content buffers, and other state
        that should not persist between turns.
        """
        # Final answer/presentation state - clear for new turn
        self._final_answer_cache = None
        self._final_answer_metadata.clear()
        self._final_stream_buffer = ""
        self._final_presentation_agent = None
        self._final_stream_active = False
        self._routing_to_post_eval_card = False

        # Post-evaluation content - clear for new turn
        self._post_evaluation_lines.clear()

        # Content buffers - clear for new turn
        with self._buffer_lock:
            for agent_id in self._buffers:
                self._buffers[agent_id].clear()

        # Web search chunks - reset for new turn
        for agent_id in self._recent_web_chunks:
            self._recent_web_chunks[agent_id].clear()

        # Reset app state if app exists
        if self._app:
            try:
                self._app.reset_turn_state()
            except Exception:
                pass

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
        try:
            if app_thread_id is not None and app_thread_id == threading.get_ident():
                callback(*args, **kwargs)
            else:
                self._app.call_from_thread(callback, *args, **kwargs)
        except RuntimeError:
            # App is no longer running (e.g., early cancellation)
            pass

    def set_input_handler(self, handler: Callable[[str], None]) -> None:
        """Set the callback for user-submitted input (questions or commands)"""
        self._input_handler = handler
        if self._app:
            try:
                self._app.set_input_handler(handler)
            except Exception:
                pass

    def set_human_input_hook(self, hook) -> None:
        """Set the human input hook for injecting user input during execution.

        Args:
            hook: HumanInputHook instance from orchestrator
        """
        logger.info(f"[Display] set_human_input_hook called, _app={self._app is not None}, hook={hook}")
        if self._app and hasattr(self._app, "set_human_input_hook"):
            try:
                self._app.set_human_input_hook(hook)
                logger.info("[Display] Successfully forwarded hook to app")
            except Exception as e:
                logger.warning(f"Failed to set human input hook on app: {e}")
        else:
            logger.warning(f"[Display] Cannot forward hook: _app={self._app}, has method={hasattr(self._app, 'set_human_input_hook') if self._app else 'N/A'}")

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

        # Suppress console logging to prevent interference with Textual display
        from massgen.logger_config import suppress_console_logging

        suppress_console_logging()

        if TEXTUAL_AVAILABLE:
            self._app = TextualApp(
                self,
                question,
                buffers=self._buffers,
                buffer_lock=self._buffer_lock,
                buffer_flush_interval=self.buffer_flush_interval,
            )

    def update_agent_content(
        self,
        agent_id: str,
        content: str,
        content_type: str = "thinking",
        tool_call_id: Optional[str] = None,
    ):
        """Update agent content with appropriate formatting.

        Args:
            agent_id: Agent identifier
            content: Content to display
            content_type: Type of content - "thinking", "tool", "status", "presentation"
            tool_call_id: Optional unique ID for tool calls (enables tracking across events)
        """
        # Bug 2 fix: Skip timeline updates if content is being routed to post-eval card
        # But allow tool content through - tools should be displayed during post-evaluation
        if hasattr(self, "_routing_to_post_eval_card") and self._routing_to_post_eval_card:
            if content_type != "tool":
                return

        if not content:
            return

        # Auto-set status to streaming when content arrives and agent is idle/waiting
        # This ensures the status indicator updates immediately when streaming starts
        current_status = self.agent_status.get(agent_id, "idle")
        if current_status in ("idle", "waiting"):
            self.agent_status[agent_id] = "streaming"  # Update local dict first
            self._call_app_method("update_agent_status", agent_id, "streaming")

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
                    "tool_call_id": tool_call_id,
                },
            )
            buffered_len = len(self._buffers[agent_id])
            # Trim buffer if it exceeds max size to prevent memory issues
            if buffered_len > self.max_buffer_size:
                # Keep critical items and the most recent half
                keep_count = self.max_buffer_size // 2
                critical = [e for e in self._buffers[agent_id][:-keep_count] if self._is_critical_content(e.get("content", ""), e.get("type", ""))]
                self._buffers[agent_id] = critical + self._buffers[agent_id][-keep_count:]
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

    def update_timeout_status(self, agent_id: str, timeout_state: Dict[str, Any]) -> None:
        """Update timeout display for an agent.

        Args:
            agent_id: The agent whose timeout status to update
            timeout_state: Timeout state from orchestrator.get_agent_timeout_state()
        """
        if self._app:
            self._call_app_method("update_agent_timeout", agent_id, timeout_state)

    def notify_subagent_spawn_started(
        self,
        agent_id: str,
        tool_name: str,
        args: Dict[str, Any],
        call_id: str,
    ) -> None:
        """Notify the TUI that subagent spawning has started.

        This is called from a background thread when spawn_subagents is invoked,
        BEFORE the blocking execution begins. This allows showing the SubagentCard
        immediately rather than waiting for the tool to complete.

        Args:
            agent_id: ID of the agent spawning subagents
            tool_name: Name of the spawn tool (e.g., spawn_subagents)
            args: Tool arguments containing tasks list
            call_id: Tool call ID
        """
        if self._app:
            self._call_app_method("show_subagent_card_from_spawn", agent_id, args, call_id)

    def update_hook_execution(
        self,
        agent_id: str,
        tool_call_id: Optional[str],
        hook_info: Dict[str, Any],
    ) -> None:
        """Update display with hook execution information.

        Args:
            agent_id: The agent whose tool call has hooks
            tool_call_id: Optional ID of the tool call this hook is attached to
            hook_info: Hook execution info dict
        """
        if self._app:
            self._call_app_method("update_hook_execution", agent_id, tool_call_id, hook_info)

    def update_token_usage(self, agent_id: str, usage: Dict[str, Any]) -> None:
        """Update token usage display for an agent.

        Phase 13.1: Wire token/cost updates from backend to status ribbon.

        Args:
            agent_id: The agent whose token usage to update
            usage: Token usage dict with input_tokens, output_tokens, estimated_cost
        """
        if self._app:
            self._call_app_method("update_token_usage", agent_id, usage)

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

    def notify_vote(self, voter: str, voted_for: str, reason: str = ""):
        """Notify the TUI of a vote cast - updates status bar, shows toast, and adds tool card."""
        if self._app:
            self._call_app_method("notify_vote", voter, voted_for, reason)

    def highlight_winner_quick(
        self,
        winner_id: str,
        vote_results: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Highlight the winning agent in no-refinement mode (skip_final_presentation).

        This marks the winner's tab with a trophy and adds a banner indicating
        the existing answer was used, without streaming a new final presentation.

        Args:
            winner_id: The winning agent's ID
            vote_results: Vote results dict with vote_counts, winner, is_tie, etc.
        """
        if self._app:
            self._call_app_method("highlight_winner_quick", winner_id, vote_results or {})

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

    def record_answer_with_context(
        self,
        agent_id: str,
        answer_label: str,
        context_sources: List[str],
        round_num: int,
    ) -> None:
        """Record an answer node with its context sources for timeline visualization.

        Args:
            agent_id: Agent who submitted the answer
            answer_label: Label like "agent1.1"
            context_sources: List of answer labels this agent saw (e.g., ["agent2.1"])
            round_num: Round number for this answer
        """
        if self._app:
            self._call_app_method(
                "record_answer_context",
                agent_id,
                answer_label,
                context_sources,
                round_num,
            )

    def notify_context_received(self, agent_id: str, context_sources: List[str]) -> None:
        """Notify the TUI when an agent receives context from other agents.

        Args:
            agent_id: Agent receiving context
            context_sources: List of answer labels this agent can now see
        """
        if self._app:
            self._call_app_method("update_agent_context", agent_id, context_sources)

    def notify_phase(self, phase: str):
        """Notify the TUI of a phase change - updates status bar."""
        tui_log(f"TextualTerminalDisplay.notify_phase called with phase='{phase}', _app={self._app is not None}")
        if self._app:
            self._call_app_method("notify_phase", phase)
        else:
            tui_log("  WARNING: _app is None, cannot forward notify_phase")

    def notify_completion(self, agent_id: str):
        """Notify the TUI of agent completion - shows toast."""
        if self._app:
            self._call_app_method("notify_completion", agent_id)

    def notify_error(self, agent_id: str, error: str):
        """Notify the TUI of an error - shows error toast."""
        if self._app:
            self._call_app_method("notify_error", agent_id, error)

    def update_loading_status(self, message: str):
        """Update the loading status text on all agent panels.

        Use this during initialization to show progress like:
        - "Creating agents..."
        - "Starting Docker containers..."
        - "Connecting to MCP servers..."
        """
        if self._app:
            self._call_app_method("_update_all_loading_text", message)

    def update_status_bar_votes(self, vote_counts: Dict[str, int]):
        """Update vote counts in the status bar."""
        if self._app:
            self._call_app_method("update_status_bar_votes", vote_counts)

    def _get_context_path_writes_footer(self) -> str:
        """Generate footer text for context path writes.

        Returns:
            Footer text if files were written, empty string otherwise.
        """
        if not self.orchestrator:
            return ""

        writes = self.orchestrator.get_context_path_writes() if hasattr(self.orchestrator, "get_context_path_writes") else []
        if not writes:
            return ""

        # Get categorized writes if available
        categorized = {}
        if hasattr(self.orchestrator, "get_context_path_writes_categorized"):
            categorized = self.orchestrator.get_context_path_writes_categorized()
        new_files = categorized.get("new", [])
        modified_files = categorized.get("modified", [])

        INLINE_THRESHOLD = 5  # Show inline if <= this many files

        # Create visually distinct section
        header = "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        if len(writes) <= INLINE_THRESHOLD:
            # Show files inline, split by category
            footer_lines = [
                header,
                "📂 **Context Path Changes**",
                "",
            ]
            if new_files:
                footer_lines.append("  **New files:**")
                for path in sorted(new_files):
                    footer_lines.append(f"    ✚ `{path}`")
            if modified_files:
                if new_files:
                    footer_lines.append("")  # Blank line between sections
                footer_lines.append("  **Modified files:**")
                for path in sorted(modified_files):
                    footer_lines.append(f"    ✎ `{path}`")
            return "\n".join(footer_lines)
        else:
            # Many files - write to log file and show summary
            log_file_path = self._write_context_path_log(writes, new_files, modified_files)
            summary = f"{len(new_files)} new, {len(modified_files)} modified"
            return f"{header}\n📂 **{len(writes)} Context Path Changes** ({summary})\n\n  See full list: `{log_file_path}`"

    def _write_context_path_log(
        self,
        writes: list[str],
        new_files: list[str] | None = None,
        modified_files: list[str] | None = None,
    ) -> str:
        """Write full context path write list to log directory.

        Args:
            writes: List of all file paths written to context paths.
            new_files: List of new file paths (optional, for categorized output).
            modified_files: List of modified file paths (optional, for categorized output).

        Returns:
            Path to the log file.
        """
        log_file = self.output_dir / "context_path_writes.txt"
        try:
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(f"Context Path Changes - {len(writes)} files\n")
                f.write("=" * 50 + "\n\n")

                if new_files or modified_files:
                    # Categorized output
                    if new_files:
                        f.write(f"New files ({len(new_files)}):\n")
                        for path in sorted(new_files):
                            f.write(f"  + {path}\n")
                        f.write("\n")
                    if modified_files:
                        f.write(f"Modified files ({len(modified_files)}):\n")
                        for path in sorted(modified_files):
                            f.write(f"  ~ {path}\n")
                else:
                    # Flat output (fallback)
                    for path in sorted(writes):
                        f.write(f"{path}\n")

            return str(log_file)
        except OSError as exc:
            logger.error(f"Failed to write context path log: {exc}")
            return ""

    def show_final_answer(self, answer: str, vote_results=None, selected_agent=None):
        """Show final answer completion card.

        Note: With the "final presentation as round N+1" approach, content has already
        been displayed through the normal pipeline (thinking, tools, response).
        This method adds the completion card and persists the final answer.
        """
        if not selected_agent:
            return

        display_answer = answer or ""
        try:
            logger.info(
                f"[FinalAnswer] show_final_answer: selected_agent={selected_agent} " f"answer_len={len(display_answer)} vote_keys={list((vote_results or {}).keys())}",
            )
        except Exception:
            pass

        # Add context path writes footer if any files were written
        context_writes_footer = self._get_context_path_writes_footer()
        if context_writes_footer:
            display_answer = display_answer.rstrip() + "\n" + context_writes_footer

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

        # Add completion card (post-evaluation section + action buttons)
        if self._app:
            self._call_app_method(
                "show_final_presentation",
                display_answer,
                vote_results,
                selected_agent,
            )

    def show_post_evaluation_content(self, content: str, agent_id: str):
        """Display post-evaluation streaming content.

        Bug 2 fix: _routing_to_post_eval_card flag is set at coordination level
        when post-eval starts, preventing duplicate routing to timeline.
        """
        eval_msg = f"\n[POST-EVALUATION]\n{content}"
        self._write_to_agent_file(agent_id, eval_msg)
        for line in content.splitlines() or [content]:
            clean = line.strip()
            if clean:
                self._post_evaluation_lines.append(clean)

        if self._app:
            self._call_app_method("show_post_evaluation", content, agent_id)

    def end_post_evaluation_content(self, agent_id: str):
        """Called when post-evaluation is complete to show footer with buttons."""
        # Bug 2 fix: Clear flag when post-eval ends
        self._routing_to_post_eval_card = False

        if self._app:
            self._call_app_method("end_post_evaluation", agent_id)

    def show_post_evaluation_tool_content(self, tool_name: str, args: dict, agent_id: str):
        """Called when a post-evaluation tool call (submit/restart) is detected."""
        if self._app:
            self._call_app_method("show_post_evaluation_tool", tool_name, args, agent_id)

    def show_restart_banner(self, reason: str, instructions: str, attempt: int, max_attempts: int):
        """Display restart decision banner."""
        banner_msg = f"\n{'=' * 60}\n" f"RESTART TRIGGERED (Attempt {attempt}/{max_attempts})\n" f"Reason: {reason}\n" f"Instructions: {instructions}\n" f"{'=' * 60}\n"

        self._write_to_system_file(banner_msg)

        if self._app:
            self._call_app_method("show_restart_banner", reason, instructions, attempt, max_attempts)

    def show_restart_context_panel(self, reason: str, instructions: str):
        """Display restart context panel at top of UI (for attempt 2+)."""
        self.restart_reason = reason
        self.restart_instructions = instructions

        if self._app:
            self._call_app_method("show_restart_context", reason, instructions)

    def show_agent_restart(self, agent_id: str, round_num: int):
        """Notify that a specific agent is starting a new round.

        This is called when an agent restarts due to new context from other agents.
        The TUI should show a fresh timeline for this agent.

        Args:
            agent_id: The agent that is restarting
            round_num: The new round number for this agent
        """
        if self._app:
            self._call_app_method("show_agent_restart", agent_id, round_num)

    def show_final_presentation_start(self, agent_id: str, vote_counts: Optional[Dict[str, int]] = None, answer_labels: Optional[Dict[str, str]] = None):
        """Notify that the final presentation phase is starting for the winning agent.

        This shows a fresh view with a distinct "Final Presentation" banner
        in green to indicate this is the winning agent presenting.

        Args:
            agent_id: The winning agent presenting the final answer
            vote_counts: Optional dict of {agent_id: vote_count} for vote summary display
            answer_labels: Optional dict of {agent_id: label} for display (e.g., {"agent1": "A1.1"})
        """
        if self._app:
            self._call_app_method("show_final_presentation_start", agent_id, vote_counts, answer_labels)

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

        # Restore console logging after Textual display is done
        from massgen.logger_config import restore_console_logging

        restore_console_logging()

    def reset_quit_request(self) -> None:
        """Reset the quit request flag at the start of each turn."""
        self._user_quit_requested = False

    def request_cancellation(self) -> None:
        """Request cancellation of the current turn."""
        self._user_quit_requested = True
        # Update execution status to show cancelled state
        if self._app and hasattr(self._app, "_show_cancelled_status"):
            self._call_app_method("_show_cancelled_status")

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

    def begin_turn(self, turn: int, question: str, previous_answer: Optional[str] = None) -> None:
        """Begin a new turn within an existing session.

        Updates the header and resets the UI for the new turn.
        Does NOT recreate the app.

        Args:
            turn: The turn number (1-indexed).
            question: The user's question for this turn.
            previous_answer: Optional summary of the previous turn's answer.
        """
        self.current_turn = turn
        self.question = question

        self.reset_quit_request()

        self._final_answer_cache = None
        self._final_answer_metadata = {}
        self._final_stream_active = False
        self._final_stream_buffer = ""
        self._final_presentation_agent = None

        # Fully reset UI for new turn (clears timelines, adds turn separator)
        if self._app:
            from massgen.logger_config import logger

            logger.info(f"[TUI] Calling prepare_for_new_turn(turn={turn})")
            self._call_app_method("prepare_for_new_turn", turn, previous_answer)
            logger.info("[TUI] prepare_for_new_turn complete, now calling update_turn_header")
            self._call_app_method("update_turn_header", turn, question)
            logger.info("[TUI] update_turn_header complete")

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
            mode_state = self.get_mode_state()
            if mode_state and mode_state.plan_mode == "execute":
                # Auto-exit execute mode after plan execution completes.
                self._call_app_method("_handle_plan_mode_change", "normal")

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

    async def prompt_for_broadcast_response(self, broadcast_request: Any) -> Optional[Any]:
        """Prompt human for response to a broadcast question.

        Args:
            broadcast_request: BroadcastRequest object with question details

        Returns:
            For simple questions: Human's response string, or None if skipped/timeout
            For structured questions: List of response dicts, or None if skipped/timeout
        """
        import asyncio

        if not self._app:
            return None

        # Extract details from broadcast request
        sender_agent_id = getattr(broadcast_request, "sender_agent_id", "Unknown Agent")
        base_timeout = getattr(broadcast_request, "timeout", 60)

        # Check if this is a structured question
        is_structured = getattr(broadcast_request, "is_structured", False)

        # For structured questions, use longer timeout (5 min) to give user time to answer all
        timeout = 300 if is_structured else base_timeout

        # Create a future to wait for the modal result
        response_future: asyncio.Future = asyncio.Future()

        # Track the modal we push so we only pop our own modal on timeout
        modal_ref = {"modal": None}

        def show_modal():
            """Show the appropriate broadcast modal and handle response."""
            if is_structured:
                # Use structured modal for questions with options
                structured_questions = getattr(broadcast_request, "structured_questions", [])
                modal = StructuredBroadcastPromptModal(
                    sender_agent_id,
                    structured_questions,
                    timeout,
                    self._app,
                )
            else:
                # Use simple modal for text questions
                question = getattr(broadcast_request, "question", "No question provided")
                if isinstance(question, str):
                    question_text = question
                else:
                    question_text = getattr(broadcast_request, "question_text", "No question provided")
                modal = BroadcastPromptModal(sender_agent_id, question_text, timeout, self._app)

            # Store reference to this specific modal
            modal_ref["modal"] = modal

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
            # Only dismiss if the current top screen is OUR modal (not a different one)
            def safe_pop():
                if self._app.screen_stack and modal_ref["modal"]:
                    current_screen = self._app.screen_stack[-1]
                    if current_screen is modal_ref["modal"]:
                        self._app.pop_screen()

            self._app.call_from_thread(safe_pop)
            return None

    def stream_final_answer_chunk(self, chunk: str, selected_agent: Optional[str], vote_results: Optional[Dict[str, Any]] = None):
        """DEPRECATED: Final presentation content now flows through update_agent_content().

        This method is kept for backwards compatibility but is no longer called.
        Content routing in coordination_ui.py sends all content through the normal
        pipeline, and final presentation is treated as round N+1.
        """
        # No-op - content now flows through update_agent_content()

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

    def get_mode_state(self) -> Optional["TuiModeState"]:
        """Get the current TUI mode state for orchestrator configuration.

        Returns:
            TuiModeState instance if the TextualApp is running, None otherwise.
        """
        if self._app and hasattr(self._app, "_mode_state"):
            return self._app._mode_state
        return None

    def show_plan_approval_modal(
        self,
        tasks: List[Dict[str, Any]],
        plan_path: Path,
        plan_data: Dict[str, Any],
        mode_state: "TuiModeState",
    ) -> None:
        """Show the plan approval modal and handle the result.

        Called from TextualInteractiveAdapter when planning completes.

        Args:
            tasks: List of tasks from the plan
            plan_path: Path to the plan file
            plan_data: Full plan data dictionary
            mode_state: TuiModeState instance to update
        """
        if not self._app:
            logger.warning("[PlanApproval] Cannot show modal - no app instance")
            mode_state.reset_plan_state()
            return

        from massgen.frontend.displays.textual_widgets.plan_approval_modal import (
            PlanApprovalModal,
            PlanApprovalResult,
        )

        def show_modal():
            try:
                modal = PlanApprovalModal(tasks, plan_path, plan_data)

                def handle_result(result: PlanApprovalResult) -> None:
                    try:
                        if result and result.approved:
                            self._execute_approved_plan(result, mode_state)
                        else:
                            # Cancelled - reset to normal mode
                            mode_state.reset_plan_state()
                            self._app.notify("Plan cancelled", severity="information")
                            if hasattr(self._app, "_mode_bar") and self._app._mode_bar:
                                self._app._mode_bar.set_plan_mode("normal")
                    except Exception as e:
                        logger.exception(f"[PlanApproval] Error handling modal result: {e}")
                        mode_state.reset_plan_state()
                        self._app.notify(f"Plan error: {e}", severity="error")
                        if hasattr(self._app, "_mode_bar") and self._app._mode_bar:
                            self._app._mode_bar.set_plan_mode("normal")

                self._app.push_screen(modal, handle_result)
            except Exception as e:
                logger.exception(f"[PlanApproval] Error showing modal: {e}")
                mode_state.reset_plan_state()
                self._app.notify(f"Failed to show plan approval: {e}", severity="error")
                if hasattr(self._app, "_mode_bar") and self._app._mode_bar:
                    self._app._mode_bar.set_plan_mode("normal")

        try:
            self._app.call_from_thread(show_modal)
        except Exception as e:
            logger.exception(f"[PlanApproval] call_from_thread failed: {e}")
            mode_state.reset_plan_state()
            # Can't notify via app if call_from_thread failed
            logger.error("[PlanApproval] Failed to dispatch modal to main thread")

    def _execute_approved_plan(
        self,
        approval: "PlanApprovalResult",
        mode_state: "TuiModeState",
    ) -> None:
        """Execute an approved plan by setting up execution mode and submitting prompt.

        Args:
            approval: PlanApprovalResult with plan data and path
            mode_state: TuiModeState instance to update
        """
        from massgen.logger_config import get_log_session_root
        from massgen.plan_storage import PlanStorage

        try:
            # Validate planning_started_turn is set
            if mode_state.planning_started_turn is None:
                # Recover by using current turn or defaulting to 0
                current_turn = 0
                if hasattr(self, "_current_turn"):
                    current_turn = self._current_turn or 0
                elif hasattr(self._app, "coordination_display"):
                    current_turn = getattr(self._app.coordination_display, "current_turn", 0)
                mode_state.planning_started_turn = current_turn
                logger.warning(
                    f"[PlanExecution] planning_started_turn was None, defaulting to {current_turn}",
                )

            # Get log directory for plan session
            log_dir = get_log_session_root()

            # Create and finalize plan session
            storage = PlanStorage()
            session = storage.create_plan(
                log_dir.name,
                str(log_dir),
                planning_prompt=mode_state.last_planning_question,
                planning_turn=mode_state.planning_started_turn,
            )

            # Copy workspace to frozen - use the parent of plan_path as workspace source
            workspace_source = approval.plan_path.parent
            # Use context paths captured during planning phase
            context_paths = mode_state.planning_context_paths or []
            storage.finalize_planning_phase(session, workspace_source, context_paths=context_paths)

            # Update mode state for execution
            mode_state.plan_mode = "execute"
            mode_state.plan_session = session

            # Update mode bar
            if hasattr(self._app, "_mode_bar") and self._app._mode_bar:
                self._app._mode_bar.set_plan_mode("execute")

            # Build execution prompt from original question
            original_question = mode_state.last_planning_question or "Execute the plan"

            from massgen.plan_execution import build_execution_prompt

            execution_prompt = build_execution_prompt(original_question)

            self._app.notify("Executing plan...", severity="information", timeout=3)

            # Submit execution prompt directly using _submit_question
            if hasattr(self._app, "_submit_question"):
                # Prevent duplicate submission by disabling input during auto-submit
                question_input = getattr(self._app, "question_input", None)
                if question_input:
                    # Disable to prevent user accidentally triggering duplicate submit
                    question_input.disabled = True
                    question_input.value = execution_prompt

                    def submit_and_reenable():
                        try:
                            self._app._submit_question(execution_prompt)
                        finally:
                            # Re-enable input after submission starts
                            # (actual processing lock handled by set_input_enabled)
                            if question_input:
                                question_input.disabled = False

                    self._app.call_later(submit_and_reenable)
                else:
                    # No input widget, just submit directly
                    self._app.call_later(lambda: self._app._submit_question(execution_prompt))
            else:
                logger.error("[PlanExecution] No _submit_question method found to execute plan")
                mode_state.reset_plan_state()

        except Exception as e:
            logger.exception(f"[PlanExecution] Failed to execute approved plan: {e}")
            self._app.notify(f"Failed to execute plan: {e}", severity="error")
            mode_state.reset_plan_state()
            if hasattr(self._app, "_mode_bar") and self._app._mode_bar:
                self._app._mode_bar.set_plan_mode("normal")

    def set_override_available(self, available: bool) -> None:
        """Set whether human override is available.

        Called by orchestrator after voting completes, before final presentation.

        Args:
            available: True if override is available, False otherwise.
        """
        if self._app and hasattr(self._app, "_mode_state"):
            self._app._mode_state.override_available = available
            if hasattr(self._app, "_mode_bar") and self._app._mode_bar:
                self._app._mode_bar.override_available = available


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

    class StatusBarCwdClicked(Message):
        """Message emitted when the CWD display in StatusBar is clicked."""

        def __init__(self, cwd: str, mode: str = "off") -> None:
            super().__init__()
            self.cwd = cwd
            self.mode = mode  # "off", "read", or "write"

    class StatusBarThemeClicked(Message):
        """Message emitted when the theme indicator in StatusBar is clicked."""

    class StatusBar(Widget):
        """Persistent status bar showing orchestration state at the bottom of the TUI."""

        # CSS is in external theme files (dark.tcss/light.tcss)

        # Spinner frames for activity indicator
        SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

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
            # Activity indicator state
            self._working_agents: Set[str] = set()
            self._spinner_frame = 0
            self._spinner_interval = None
            # Agent activity tracking for phase icons display
            self._agent_activities: Dict[str, str] = {}  # agent_id -> activity type
            self._agent_letters: Dict[str, str] = {}  # agent_id -> letter (A, B, C...)
            self._agent_order: List[str] = []  # ordered list of agent IDs
            # Per-agent answer and vote tracking
            self._agent_answer_counts: Dict[str, int] = {}  # agent_id -> number of answers
            self._agent_votes_received: Dict[str, int] = {}  # agent_id -> votes received for their answers
            # CWD context mode: "off", "read", or "write"
            self._cwd_context_mode = "off"
            # Initialize vote counts to 0 for all agents and register agents
            for idx, agent_id in enumerate(self._agent_ids):
                self._vote_counts[agent_id] = 0
                # Auto-register agents with letters A, B, C, etc.
                letter = chr(ord("A") + idx) if idx < 26 else str(idx + 1)
                self._agent_letters[agent_id] = letter
                self._agent_order.append(agent_id)
                self._agent_activities[agent_id] = "idle"
                self._agent_answer_counts[agent_id] = 0
                self._agent_votes_received[agent_id] = 0

        def compose(self) -> ComposeResult:
            """Create the status bar layout with phase, activity, progress, tools, votes, events, MCP, CWD, cancel hint, and timer.

            Layout: [phase] [activity] [progress] [tools] [votes] --- spacer --- [mcp] [cwd] [events] [hints] [timer] [cancel]
            """
            # Left-aligned items
            yield Static("⏳ Idle", id="status_phase")
            yield Static("", id="status_activity", classes="activity-indicator hidden")  # Pulsing activity indicator
            yield Static("", id="status_progress")  # Progress summary: "3 agents | 2 answers | 4/6 votes"
            yield Static("", id="status_tools", classes="hidden")  # Running tools counter: "🔧 3 running"
            yield Static("", id="status_votes")
            # Spacer to push right-side elements to the edge
            yield Static("", id="status_spacer")
            # Right-aligned items
            yield Static("", id="status_mcp")
            # Theme toggle indicator - clickable to toggle light/dark theme
            yield Static("[dim]D[/]", id="status_theme", classes="clickable")
            # CWD display - clickable to toggle auto-include as context
            cwd = Path.cwd()
            cwd_short = f"~/{cwd.name}" if len(str(cwd)) > 30 else str(cwd)
            yield Static(f"[dim]📁[/] {cwd_short}", id="status_cwd", classes="clickable")
            yield Static("📋 0 events", id="status_events", classes="clickable")
            yield Static("[dim]?:help[/]", id="status_hints")  # Always visible, shows q:cancel during coordination
            yield Static("⏱️ 0:00", id="status_timer")
            yield Static("", id="status_cancel", classes="cancel-button hidden")

        def on_click(self, event: events.Click) -> None:
            """Handle click on the events counter, cancel button, or CWD."""
            # Textual uses event.widget, not event.target
            widget = getattr(event, "widget", None)
            if widget and hasattr(widget, "id"):
                if widget.id == "status_events":
                    self.post_message(StatusBarEventsClicked())
                elif widget.id == "status_cancel":
                    self.post_message(StatusBarCancelClicked())
                elif widget.id == "status_cwd":
                    self.toggle_cwd_auto_include()
                elif widget.id == "status_theme":
                    self.post_message(StatusBarThemeClicked())

        def toggle_cwd_auto_include(self) -> None:
            """Cycle CWD context mode and update display."""
            # Cycle through modes
            modes = ["off", "read", "write"]
            current_idx = modes.index(self._cwd_context_mode)
            self._cwd_context_mode = modes[(current_idx + 1) % len(modes)]

            cwd = Path.cwd()
            cwd_short = f"~/{cwd.name}" if len(str(cwd)) > 30 else str(cwd)
            try:
                cwd_widget = self.query_one("#status_cwd", Static)
                if self._cwd_context_mode == "read":
                    cwd_widget.update(f"[green]📁 {cwd_short} \\[read][/]")
                elif self._cwd_context_mode == "write":
                    cwd_widget.update(f"[green]📁 {cwd_short} \\[read+write][/]")
                else:
                    cwd_widget.update(f"[dim]📁[/] {cwd_short}")
            except Exception:
                pass
            # Post message to notify app of the toggle
            self.post_message(StatusBarCwdClicked(str(cwd), self._cwd_context_mode))

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

            # Update hints based on phase - always show ?:help, add q:cancel during coordination
            try:
                hints_widget = self.query_one("#status_hints", Static)
                if phase in ("idle",):
                    hints_widget.update("[dim]?:help[/]")
                else:
                    hints_widget.update("[dim]q:cancel • ?:help[/]")
                hints_widget.remove_class("hidden")  # Always visible
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

        def update_running_tools(self, count: int) -> None:
            """Update running tools counter in status bar."""
            try:
                tools_widget = self.query_one("#status_tools", Static)
                if count > 0:
                    tools_widget.update(f"🔧 {count} running")
                    tools_widget.remove_class("hidden")
                else:
                    tools_widget.update("")
                    tools_widget.add_class("hidden")
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
            # Also update per-agent votes received tracking
            if voted_for in self._agent_votes_received:
                self._agent_votes_received[voted_for] = self._vote_counts[voted_for]
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

        def show_restart_count(self, attempt: int, max_attempts: int) -> None:
            """Show restart count in the phase indicator."""
            try:
                phase_widget = self.query_one("#status_phase", Static)
                phase_widget.update(f"🔄 Restart {attempt}/{max_attempts}")
                phase_widget.add_class("restart-active")
            except Exception:
                pass  # Widget not mounted yet

        def clear_restart_indicator(self) -> None:
            """Clear the restart indicator."""
            try:
                phase_widget = self.query_one("#status_phase", Static)
                phase_widget.remove_class("restart-active")
            except Exception:
                pass

        def set_agent_working(self, agent_id: str, working: bool = True) -> None:
            """Mark an agent as working or not working.

            Args:
                agent_id: The agent identifier
                working: True if agent is actively working, False if done
            """
            if working:
                self._working_agents.add(agent_id)
            else:
                self._working_agents.discard(agent_id)

            # Update activity indicator
            if self._working_agents:
                self._start_activity_spinner()
            else:
                self._stop_activity_spinner()

        def set_agent_activity(self, agent_id: str, activity: str) -> None:
            """Update agent activity type and refresh the activity display.

            Args:
                agent_id: The agent identifier
                activity: One of "idle", "thinking", "tool", "streaming", "voting", "waiting", "error"
            """
            if agent_id not in self._agent_letters:
                return  # Unknown agent

            self._agent_activities[agent_id] = activity

            # Start/stop spinner based on any active agents
            any_active = any(a != "idle" for a in self._agent_activities.values())
            if any_active and not self._spinner_interval:
                self._start_activity_spinner()
            elif not any_active and self._spinner_interval:
                self._stop_activity_spinner()
            else:
                # Just refresh the display without changing spinner state
                self._update_activity_display()

        def increment_agent_answer(self, agent_id: str) -> None:
            """Increment answer count for an agent."""
            if agent_id in self._agent_answer_counts:
                self._agent_answer_counts[agent_id] += 1

        def update_agent_votes_received(self, agent_id: str, votes: int) -> None:
            """Update the number of votes an agent has received."""
            if agent_id in self._agent_votes_received:
                self._agent_votes_received[agent_id] = votes

        def _start_activity_spinner(self) -> None:
            """Start the activity spinner animation."""
            if self._spinner_interval is not None:
                return  # Already running

            self._spinner_frame = 0
            self._update_activity_display()

            # Show the activity indicator
            try:
                activity_widget = self.query_one("#status_activity", Static)
                activity_widget.remove_class("hidden")
            except Exception:
                pass

            # Start animation interval (update every 100ms for smooth animation)
            self._spinner_interval = self.set_interval(0.1, self._animate_spinner)

        def _stop_activity_spinner(self) -> None:
            """Stop the activity spinner animation."""
            if self._spinner_interval:
                self._spinner_interval.stop()
                self._spinner_interval = None

            # Hide the activity indicator
            try:
                activity_widget = self.query_one("#status_activity", Static)
                activity_widget.add_class("hidden")
                activity_widget.update("")
            except Exception:
                pass

        def _animate_spinner(self) -> None:
            """Animate the spinner to next frame."""
            self._spinner_frame = (self._spinner_frame + 1) % len(self.SPINNER_FRAMES)
            self._update_activity_display()

        def _update_activity_display(self) -> None:
            """Update the activity indicator display with phase icons per agent.

            Format: [A⠙💭] [B⠙🔧] [C ○]
            - Active agents show spinner + phase icon
            - Idle agents show hollow circle
            """
            # Activity icons mapping
            ACTIVITY_ICONS = {
                "idle": "○",
                "thinking": "💭",
                "tool": "🔧",
                "streaming": "✍️",
                "voting": "🗳️",
                "waiting": "⏳",
                "error": "⚠️",
            }

            parts = []
            spinner = self.SPINNER_FRAMES[self._spinner_frame]

            for agent_id in self._agent_order:
                letter = self._agent_letters.get(agent_id, "?")
                activity = self._agent_activities.get(agent_id, "idle")
                icon = ACTIVITY_ICONS.get(activity, "○")

                if activity == "idle":
                    parts.append(f"[{letter} {icon}]")
                else:
                    parts.append(f"[{letter}{spinner}{icon}]")

            display = " ".join(parts)

            # Check if any agent is active
            any_active = any(a != "idle" for a in self._agent_activities.values())

            try:
                activity_widget = self.query_one("#status_activity", Static)
                activity_widget.update(display)
                # Show/hide based on any activity
                if any_active:
                    activity_widget.remove_class("hidden")
                else:
                    activity_widget.add_class("hidden")
            except Exception:
                pass

    # BaseModal is now imported from .textual package

    class TextualApp(App):
        """Main Textual application for MassGen coordination."""

        THEMES_DIR = Path(__file__).parent / "textual_themes"
        CSS_PATH = str(THEMES_DIR / "dark.tcss")

        # Minimal bindings - most features accessed via /slash commands
        # Only canonical shortcuts that users expect
        BINDINGS = [
            # Agent navigation
            Binding("tab", "next_agent", "Next Agent"),
            Binding("left", "prev_agent", "Prev Agent", show=False),
            Binding("right", "next_agent", "Next Agent", show=False),
            # Quit - Ctrl+D quits directly
            Binding("ctrl+d", "quit", "Quit", show=False),
            # Ctrl+C - context-aware: clear input / cancel turn, double to quit
            Binding("ctrl+c", "handle_ctrl_c", "Cancel/Quit", show=False),
            # CWD context toggle - priority so it works even when input focused
            Binding("ctrl+p", "toggle_cwd", "Toggle CWD", priority=True, show=False),
            # Subagent quick access
            Binding("ctrl+u", "show_subagents", "Subagents", priority=True, show=False),
            # Help - Ctrl+G for guide/help
            Binding("ctrl+g", "show_help", "Help", priority=True, show=False),
            # Mode toggles
            Binding("shift+tab", "toggle_plan_mode", "Plan Mode", priority=True),
            Binding("ctrl+o", "trigger_override", "Override", priority=True, show=False),
            # Task plan toggle
            Binding("ctrl+t", "toggle_task_plan", "Toggle Tasks", priority=True, show=False),
            # Theme toggle
            Binding("ctrl+shift+t", "toggle_theme", "Theme", priority=True, show=False),
        ]

        def __init__(
            self,
            display: TextualTerminalDisplay,
            question: str,
            buffers: Dict[str, List],
            buffer_lock: threading.Lock,
            buffer_flush_interval: float,
        ):
            # Determine CSS path based on theme (dark, light, or transparent)
            if display.theme == "light":
                css_path = self.THEMES_DIR / "light.tcss"
            elif display.theme == "transparent":
                css_path = self.THEMES_DIR / "transparent.tcss"
            else:
                css_path = self.THEMES_DIR / "dark.tcss"
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
            self._status_ribbon: Optional[AgentStatusRibbon] = None
            self._execution_status_line: Optional[ExecutionStatusLine] = None
            self._active_agent_id: Optional[str] = None
            # Final presentation state (streams into winner's AgentPanel)
            self._final_presentation_agent: Optional[str] = None
            self._final_presentation_card: Optional[FinalPresentationCard] = None
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

            # Conversation history tracking
            self._conversation_history: List[Dict[str, Any]] = []  # {question, answer, turn, timestamp}
            self._current_question: str = ""  # Track the current question

            # Restart and context tracking
            self._restart_history: List[Dict[str, Any]] = []  # Track all restarts
            self._current_restart: Dict[str, Any] = {}  # Current restart info
            self._context_per_agent: Dict[str, List[str]] = {}  # Which answers each agent has seen

            # CWD context mode: "off", "read", or "write"
            self._cwd_context_mode: str = "off"

            # Timer for updating execution status bar with spinner animation
            self._execution_status_timer = None

            # Agent pulsing animation state
            self._pulsing_agents: set = set()  # Set of agent_ids currently pulsing
            self._pulse_frame: int = 0
            self._pulse_timer = None

            # Human input during execution state
            self._queued_human_input: Optional[str] = None
            self._human_input_hook = None  # Set by orchestrator via set_human_input_hook()
            self._queued_input_banner: Optional[QueuedInputBanner] = None

            # TUI Mode State (plan mode, agent mode, refinement mode, override)
            self._mode_state = TuiModeState()
            self._mode_bar: Optional[ModeBar] = None

            if not self._keyboard_interactive_mode:
                self.BINDINGS = []

        def _keyboard_locked(self) -> bool:
            """Return True when keyboard input should be ignored.

            Keyboard is locked when:
            - safe_keyboard_mode is True (during sensitive operations)
            - _keyboard_interactive_mode is False (non-interactive)
            - execution is in progress (mode_state.is_locked())
            """
            if self.coordination_display.safe_keyboard_mode:
                return True
            if not self._keyboard_interactive_mode:
                return True
            # Block mode-changing keyboard shortcuts during execution
            if hasattr(self, "_mode_state") and self._mode_state.is_locked():
                return True
            return False

        def reset_turn_state(self) -> None:
            """Reset turn-level state for a new turn.

            Clears answer/vote tracking, winner state, context tracking,
            and UI state that should not persist between turns.
            """
            # Answer/voting state - clear for new turn
            self._answers.clear()
            self._votes.clear()
            self._winner_agent_id = None
            self._current_question = ""

            # Restart tracking - keep history but clear current
            self._current_restart = {}

            # Context tracking - agents start fresh for new turn
            self._context_per_agent.clear()

            # Orchestrator events - clear event log for new turn
            self._orchestrator_events.clear()

            # Human input queue - clear any stale queued input
            self._queued_human_input = None
            if self._queued_input_banner:
                try:
                    self._queued_input_banner.remove()
                    self._queued_input_banner = None
                except Exception:
                    pass

            # Agent pulsing - stop all pulse animations
            self._pulsing_agents.clear()

            # Final presentation state - clear winner's presentation
            self._final_presentation_agent = None
            self._final_presentation_card = None

        def compose(self) -> ComposeResult:
            """Compose the UI layout with adaptive agent arrangement."""
            len(self.coordination_display.agent_ids)
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

            turn = getattr(self.coordination_display, "current_turn", 1)
            agent_ids = self.coordination_display.agent_ids

            # Header removed - session info now in tab bar (right side)

            # === BOTTOM DOCKED WIDGETS (yield order: last yielded = very bottom) ===
            # Input area container - dock: bottom
            with Container(id="input_area"):
                # Input header with modes (left), plan status (right), vim indicator
                with Horizontal(id="input_header"):
                    # Mode bar - toggles for plan/agent/refinement modes (left side)
                    self._mode_bar = ModeBar(id="mode_bar")
                    yield self._mode_bar
                    # Input hint - hidden by default, used only for vim mode hints
                    self._input_hint = Static("", id="input_hint", classes="hidden")
                    yield self._input_hint
                    # Vim mode indicator (hidden by default)
                    self._vim_indicator = Static("", id="vim_indicator")
                    yield self._vim_indicator

                # Execution bar - shown ONLY during coordination, replaces input
                # Contains status text (left) and cancel button (right)
                with Horizontal(id="execution_bar"):
                    # Status text on left - shows agent activity icons
                    self._execution_status = Static("Working...", id="execution_status")
                    yield self._execution_status
                    # Spacer to push cancel button to right
                    yield Static("", id="execution_spacer")
                    # Cancel button - on right
                    self._cancel_button = Button("Cancel [q]", id="cancel_button", variant="error")
                    yield self._cancel_button

                # Queued input banner - mounted dynamically when needed (not in compose)
                # to avoid blocking input bar clicks
                self._queued_input_banner = None

                # Multi-line input: Enter to submit, Shift+Enter for new line
                # Type @ to trigger path autocomplete
                # Hint text is now part of placeholder (frees up space on input header row)
                self.question_input = MultiLineInput(
                    placeholder="Enter to submit • Shift+Enter for newline • @ for files • Ctrl+G help",
                    id="question_input",
                )
                yield self.question_input

            # Footer - dock: bottom (Textual built-in)
            self.footer_widget = Footer()
            yield self.footer_widget

            # Status bar - dock: bottom, yielded LAST so it's at very bottom
            self._status_bar = StatusBar(agent_ids=agent_ids)
            yield self._status_bar

            # === CONTENT WIDGETS (fill remaining space, in visual order top-to-bottom) ===
            # Tab bar for agent switching (flows below header, hidden during welcome)
            # NOTE: No dock:top - just flows naturally after docked widgets
            agent_models = getattr(self.coordination_display, "agent_models", {})
            self._tab_bar = AgentTabBar(
                agent_ids,
                agent_models=agent_models,
                turn=turn,
                question=self.question,
                id="agent_tab_bar",
            )
            if self._showing_welcome:
                self._tab_bar.add_class("hidden")
            yield self._tab_bar

            # Agent status ribbon - shows round, activity, timeout, tasks, tokens, cost
            initial_agent = agent_ids[0] if agent_ids else ""
            self._status_ribbon = AgentStatusRibbon(agent_id=initial_agent, id="agent_status_ribbon")
            if self._showing_welcome:
                self._status_ribbon.add_class("hidden")
            yield self._status_ribbon

            # Set initial active agent
            self._active_agent_id = agent_ids[0] if agent_ids else None

            # Welcome screen (shown initially, hidden when session starts)
            self._welcome_screen = WelcomeScreen(agents_info_list)
            if not self._showing_welcome:
                self._welcome_screen.add_class("hidden")
            yield self._welcome_screen

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

                # Phase 13.2: Execution status line - shows all agents' states at a glance
                # Placed at bottom of main content area, above mode bar
                self._execution_status_line = ExecutionStatusLine(
                    agent_ids=agent_ids,
                    focused_agent=initial_agent,
                    id="execution_status_line",
                )
                yield self._execution_status_line

            self.post_eval_panel = PostEvaluationPanel()
            yield self.post_eval_panel

            # FinalStreamPanel is deprecated - final answer now streams into winner's AgentPanel
            # Keep the instance but don't yield it (hidden)
            self.final_stream_panel = FinalStreamPanel(coordination_display=self.coordination_display)
            # yield self.final_stream_panel  # Hidden - using FinalPresentationCard in AgentPanel instead

            self.safe_indicator = Label("", id="safe_indicator")
            yield self.safe_indicator

            # Path autocomplete dropdown (hidden by default, floats above input area)
            self._path_dropdown = PathSuggestionDropdown(id="path_dropdown")
            yield self._path_dropdown

            # Plan options popover (hidden by default, shows when settings button clicked)
            self._plan_options_popover = PlanOptionsPopover(id="plan_options_popover")
            yield self._plan_options_popover

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
            self._update_theme_indicator()
            # Auto-focus input field on startup
            if self.question_input:
                self.question_input.focus()

            # DEBUG: Log widget state to file
            import json

            debug_info = {
                "header_widget": {
                    "exists": self.header_widget is not None,
                    "id": getattr(self.header_widget, "id", None) if self.header_widget else None,
                    "display": str(self.header_widget.display) if self.header_widget else None,
                    "visible": self.header_widget.visible if self.header_widget else None,
                    "classes": list(self.header_widget.classes) if self.header_widget else None,
                    "styles_dock": str(self.header_widget.styles.dock) if self.header_widget else None,
                    "styles_height": str(self.header_widget.styles.height) if self.header_widget else None,
                    "styles_display": str(self.header_widget.styles.display) if self.header_widget else None,
                },
                "status_bar": {
                    "exists": self._status_bar is not None,
                    "id": getattr(self._status_bar, "id", None) if self._status_bar else None,
                    "display": str(self._status_bar.display) if self._status_bar else None,
                    "visible": self._status_bar.visible if self._status_bar else None,
                    "classes": list(self._status_bar.classes) if self._status_bar else None,
                    "styles_dock": str(self._status_bar.styles.dock) if self._status_bar else None,
                    "styles_height": str(self._status_bar.styles.height) if self._status_bar else None,
                    "styles_display": str(self._status_bar.styles.display) if self._status_bar else None,
                },
                "tab_bar": {
                    "exists": self._tab_bar is not None,
                    "id": getattr(self._tab_bar, "id", None) if self._tab_bar else None,
                    "classes": list(self._tab_bar.classes) if self._tab_bar else None,
                    "styles_dock": str(self._tab_bar.styles.dock) if self._tab_bar else None,
                },
            }
            # Add execution_bar and cancel_button info
            try:
                execution_bar = self.query_one("#execution_bar")
                debug_info["execution_bar"] = {
                    "exists": True,
                    "id": execution_bar.id,
                    "classes": list(execution_bar.classes),
                    "display": str(execution_bar.styles.display),
                    "visible": execution_bar.visible,
                }
            except Exception as e:
                debug_info["execution_bar"] = {"exists": False, "error": str(e)}

            try:
                cancel_btn = self.query_one("#cancel_button")
                debug_info["cancel_button"] = {
                    "exists": True,
                    "id": cancel_btn.id,
                    "classes": list(cancel_btn.classes),
                    "display": str(cancel_btn.styles.display),
                    "visible": cancel_btn.visible,
                }
            except Exception as e:
                debug_info["cancel_button"] = {"exists": False, "error": str(e)}

            try:
                input_area = self.query_one("#input_area")
                debug_info["input_area"] = {
                    "exists": True,
                    "id": input_area.id,
                    "classes": list(input_area.classes),
                    "display": str(input_area.styles.display),
                }
            except Exception as e:
                debug_info["input_area"] = {"exists": False, "error": str(e)}

            with open("/tmp/textual_debug.json", "w") as f:
                json.dump(debug_info, f, indent=2, default=str)
            self.log("DEBUG: Widget info written to /tmp/textual_debug.json")
            tui_log("TUI mounted - debug info written to /tmp/textual_debug.json")

        def _dump_widget_sizes(self) -> None:
            """Dump full widget tree with sizes for debugging layout issues."""
            import json

            def get_widget_info(widget, depth=0):
                """Recursively get widget info."""
                info = {
                    "type": type(widget).__name__,
                    "id": widget.id,
                    "classes": list(widget.classes) if hasattr(widget, "classes") else [],
                    "size": {"width": widget.size.width, "height": widget.size.height} if hasattr(widget, "size") else None,
                    "region": {"x": widget.region.x, "y": widget.region.y, "width": widget.region.width, "height": widget.region.height} if hasattr(widget, "region") else None,
                    "content_size": {"width": widget.content_size.width, "height": widget.content_size.height} if hasattr(widget, "content_size") else None,
                    "styles": {
                        "width": str(widget.styles.width) if hasattr(widget.styles, "width") else None,
                        "height": str(widget.styles.height) if hasattr(widget.styles, "height") else None,
                        "padding": str(widget.styles.padding) if hasattr(widget.styles, "padding") else None,
                        "margin": str(widget.styles.margin) if hasattr(widget.styles, "margin") else None,
                        "border": str(widget.styles.border) if hasattr(widget.styles, "border") else None,
                    },
                    "children": [],
                }
                if depth < 8:  # Limit depth to avoid huge dumps
                    for child in widget.children:
                        info["children"].append(get_widget_info(child, depth + 1))
                return info

            tree = get_widget_info(self)
            with open("/tmp/widget_sizes.json", "w") as f:
                json.dump(tree, f, indent=2, default=str)

            # Also dump specific timeline info to separate file for easier debugging
            timeline_debug = []
            try:
                from massgen.frontend.displays.textual_widgets.content_sections import (
                    TimelineSection,
                )

                for ts in self.query(TimelineSection):
                    ts_info = {
                        "id": ts.id,
                        "size": {"width": ts.size.width, "height": ts.size.height},
                        "region": {"x": ts.region.x, "y": ts.region.y, "width": ts.region.width, "height": ts.region.height},
                        "content_size": {"width": ts.content_size.width, "height": ts.content_size.height},
                    }
                    # Get the scroll container
                    try:
                        container = ts.query_one("#timeline_container")
                        ts_info["container"] = {
                            "type": type(container).__name__,
                            "size": {"width": container.size.width, "height": container.size.height},
                            "region": {"x": container.region.x, "y": container.region.y, "width": container.region.width, "height": container.region.height},
                            "content_size": {"width": container.content_size.width, "height": container.content_size.height},
                            "virtual_size": {"width": container.virtual_size.width, "height": container.virtual_size.height},
                            "scroll_y": container.scroll_y,
                            "max_scroll_y": container.max_scroll_y,
                            "children_count": len(list(container.children)),
                            "children": [],
                        }
                        # Get first and last few children for debugging
                        children = list(container.children)
                        for i, child in enumerate(children[:5]):  # First 5
                            ts_info["container"]["children"].append(
                                {
                                    "index": i,
                                    "type": type(child).__name__,
                                    "id": child.id,
                                    "classes": list(child.classes),
                                    "size": {"width": child.size.width, "height": child.size.height},
                                    "region": {"y": child.region.y, "height": child.region.height},
                                },
                            )
                        if len(children) > 10:
                            ts_info["container"]["children"].append({"...": f"{len(children) - 10} more items..."})
                        for i, child in enumerate(children[-5:]):  # Last 5
                            if len(children) > 5:
                                ts_info["container"]["children"].append(
                                    {
                                        "index": len(children) - 5 + i,
                                        "type": type(child).__name__,
                                        "id": child.id,
                                        "classes": list(child.classes),
                                        "size": {"width": child.size.width, "height": child.size.height},
                                        "region": {"y": child.region.y, "height": child.region.height},
                                    },
                                )
                    except Exception as e:
                        ts_info["container_error"] = str(e)
                    timeline_debug.append(ts_info)
            except Exception as e:
                timeline_debug.append({"error": str(e)})

            with open("/tmp/timeline_debug.json", "w") as f:
                json.dump(timeline_debug, f, indent=2, default=str)

            tui_log("Widget sizes dumped to /tmp/widget_sizes.json and /tmp/timeline_debug.json")

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

        def _update_theme_indicator(self) -> None:
            """Update theme icon in status bar."""
            try:
                theme_widget = self.query_one("#status_theme", Static)
                theme = self.coordination_display.theme
                icon_map = {"dark": "D", "light": "L", "transparent": "T"}
                icon = f"[dim]{icon_map.get(theme, 'D')}[/]"
                theme_widget.update(icon)
            except Exception:
                pass  # Widget not mounted yet

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

            # Show tab bar, status ribbon, execution status line, main container, and status bar
            if self._tab_bar:
                self._tab_bar.remove_class("hidden")
            if self._status_ribbon:
                self._status_ribbon.remove_class("hidden")
            if self._execution_status_line:
                self._execution_status_line.remove_class("hidden")
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
            # If @ autocomplete is showing, route keys to it first
            if hasattr(self, "_path_dropdown") and self._path_dropdown.is_showing:
                if self._path_dropdown.handle_key(event):
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
                    return
                # Stop event propagation when input is focused to prevent shortcuts from triggering
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
                # Pass the submitted value which has paste placeholders expanded
                self._submit_question(event.value)

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

        def on_multi_line_input_quit_requested(self, event: MultiLineInput.QuitRequested) -> None:
            """Handle Ctrl+C on empty input - quit the application."""
            if event.input.id == "question_input":
                self.exit()

        def on_multi_line_input_quit_pending(self, event: MultiLineInput.QuitPending) -> None:
            """Handle first Ctrl+C - show hint to press again to quit."""
            if event.input.id == "question_input":
                self.notify("Press Ctrl+C again to quit", severity="warning", timeout=3)

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

        def _is_execution_in_progress(self) -> bool:
            """Check if agents are currently executing.

            Returns:
                True if in an executing phase, False if idle/presentation.
            """
            if self._status_bar and hasattr(self._status_bar, "_current_phase"):
                phase = self._status_bar._current_phase
                # Idle and presentation phases mean execution is done
                return phase not in ("idle", "presentation", "presenting")
            return False

        def _queue_human_input(self, text: str) -> None:
            """Queue human input for injection during execution.

            Args:
                text: The human input text to queue
            """
            self._queued_human_input = text

            # Send to hook if available
            if self._human_input_hook:
                self._human_input_hook.set_pending_input(text)

            # Show visual indicator - mount banner dynamically if not present
            try:
                if self._queued_input_banner is None:
                    self._queued_input_banner = QueuedInputBanner(id="queued_input_banner")
                    # Mount in the input_area container, before question_input
                    input_area = self.query_one("#input_area", Container)
                    input_area.mount(self._queued_input_banner, before=self.question_input)
                # Use add_message to stack multiple queued inputs
                self._queued_input_banner.add_message(text)
            except Exception as e:
                tui_log(f"[HumanInput] Failed to show banner: {e}")

            preview = text[:40] + "..." if len(text) > 40 else text
            self.notify(f'📝 Queued: "{preview}" (Ctrl+C to cancel and start new turn)', timeout=4)
            tui_log(f"[HumanInput] Queued input: {text[:50]}...")

        def _clear_queued_input(self) -> None:
            """Clear the queued human input after injection."""
            self._queued_human_input = None

            # Clear visual indicator
            if self._queued_input_banner:
                self._queued_input_banner.clear()

            tui_log("[HumanInput] Cleared queued input")

        def _on_human_input_injected(self, content: str) -> None:
            """Called when human input is injected into tool result.

            Clears the queued input banner and shows notification.
            The hook framework handles displaying the injection content
            on the tool card via hook_execution chunks.

            Args:
                content: The injected input content
            """
            # Clear the queued input banner
            self._clear_queued_input()

            # Show notification - the actual display on the tool card is handled
            # by the hook framework via hook_execution chunks
            preview = content[:40] + "..." if len(content) > 40 else content
            self.notify(f'💬 Injected: "{preview}"', severity="information", timeout=3)
            tui_log(f"[HumanInput] Input injected: {content[:50]}...")

        def set_human_input_hook(self, hook) -> None:
            """Set the human input hook reference from orchestrator.

            Args:
                hook: HumanInputHook instance to use for injection
            """
            self._human_input_hook = hook
            # Set callback so we're notified when input is injected
            if hook:
                hook.set_inject_callback(lambda content: self.call_from_thread(self._on_human_input_injected, content))
            tui_log(f"[HumanInput] Set human input hook: {hook}")

        def _submit_question(self, submitted_text: str | None = None) -> None:
            """Submit the current question text.

            During execution, input is queued for injection into the next tool result.
            Cancel execution first (Ctrl+C) if you want to start a new turn.

            Args:
                submitted_text: Pre-processed text from Submitted event (with paste
                    placeholders expanded). If None, reads from widget directly.
            """
            text = submitted_text.strip() if submitted_text else self.question_input.text.strip()
            tui_log(f"_submit_question called with text: '{text[:50]}...' (len={len(text)})")

            # In execute mode, allow empty submission (just press Enter to run the plan)
            is_execute_mode = self._mode_state.plan_mode == "execute"
            if not text and not is_execute_mode:
                tui_log("  Empty text and not execute mode, returning")
                return

            # Hide plan options popover on submission (especially for execute mode)
            if hasattr(self, "_plan_options_popover") and "visible" in self._plan_options_popover.classes:
                self._plan_options_popover.hide()

            # Clear any persistent cancelled state when user starts a new turn
            self._clear_cancelled_state()

            # CRITICAL: Check execution status FIRST before execute mode
            # During active execution, queue input (don't trigger new plan execution)
            # Execute mode is auto-cleared by end_turn() after execution completes
            is_executing = self._is_execution_in_progress()
            has_hook = self._human_input_hook is not None
            phase = self._status_bar._current_phase if self._status_bar else "unknown"
            tui_log(f"  is_executing={is_executing}, has_hook={has_hook}, phase={phase}")

            if not text.startswith("/") and is_executing and has_hook:
                tui_log("  -> Queueing input for injection")
                self._queue_human_input(text)
                return

            # In execute mode (and NOT currently executing), set up plan execution
            if is_execute_mode:
                text = self._setup_plan_execution(text)
                if text is None:
                    # Setup failed, error already shown
                    return

            # Clear input after determining routing (queued input was already cleared)
            self.question_input.clear()

            tui_log("  -> Submitting as new turn")

            # Auto-include CWD as context based on mode
            if self._cwd_context_mode != "off" and not text.startswith("/"):
                cwd = str(Path.cwd())
                # Add @cwd with appropriate permission suffix
                suffix = ":w" if self._cwd_context_mode == "write" else ""
                cwd_ref = f"@{cwd}{suffix}"
                # Prepend if not already present
                if f"@{cwd}" not in text:
                    text = f"{cwd_ref} {text}"
                    tui_log(f"  Auto-prepended CWD context: {cwd_ref}")

            # Dismiss welcome screen on first real input
            if self._showing_welcome and not text.startswith("/"):
                self._dismiss_welcome()

            # Handle TUI-local slash commands first (like /vim)
            if text.startswith("/"):
                if self._handle_local_slash_command(text):
                    tui_log("  Handled as local slash command")
                    return  # Command was handled locally

            tui_log(f"  _input_handler is: {self._input_handler}")
            if self._input_handler:
                tui_log("  Calling _input_handler...")

                # Store question for plan execution if in plan mode
                # Only capture the FIRST user input - don't overwrite with subsequent/injected inputs
                if not text.startswith("/") and self._mode_state.plan_mode == "plan":
                    if self._mode_state.last_planning_question is None:
                        self._mode_state.last_planning_question = text
                        self._mode_state.planning_started_turn = self.coordination_display.current_turn
                        tui_log(f"  Stored planning question (turn {self._mode_state.planning_started_turn}): {text[:50]}...")
                    else:
                        tui_log(f"  Plan question already set, not overwriting with: {text[:50]}...")

                self._input_handler(text)
                if not text.startswith("/"):
                    # Track the current question for history
                    self._current_question = text
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

            # Track the current question for history
            self._current_question = text
            main_container = self.query_one("#main_container", Container)
            main_container.remove_class("hidden")

            if self.header_widget:
                self.header_widget.update_question(text)

        def _submit_followup_question(self, question: str) -> None:
            """Submit a follow-up question from the final answer panel."""
            if not question:
                return

            # Dismiss welcome screen if still showing
            if self._showing_welcome:
                self._dismiss_welcome()

            # Track the question for history
            self._current_question = question

            # Update header with new question
            if self.header_widget:
                self.header_widget.update_question(question)

            # Show main container
            try:
                main_container = self.query_one("#main_container", Container)
                main_container.remove_class("hidden")
            except Exception:
                pass

            # Submit through the input handler
            if self._input_handler:
                self._input_handler(question)

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

            # TODO: Re-enable /theme command when additional themes are ready
            # if cmd == "/theme":
            #     self.action_toggle_theme()
            #     return True

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
                elif result.ui_action == "toggle_theme":
                    self.action_toggle_theme()
                elif result.ui_action == "show_history":
                    self._show_history_modal()
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
                elif cmd in ("/history", "/hist"):
                    self._show_history_modal()
                elif cmd in ("/timeline", "/t"):
                    self.action_open_timeline()
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
                # Vim mode off - hide indicator and input hint (hint is now in placeholder)
                self._vim_indicator.update("")
                self._vim_indicator.remove_class("vim-normal-indicator")
                self._vim_indicator.remove_class("vim-insert-indicator")
                if hasattr(self, "_input_hint"):
                    self._input_hint.update("")
                    self._input_hint.add_class("hidden")
            elif vim_normal:
                # Normal mode - show vim hints in input_hint
                self._vim_indicator.update(" NORMAL ")
                self._vim_indicator.remove_class("vim-insert-indicator")
                self._vim_indicator.add_class("vim-normal-indicator")
                if hasattr(self, "_input_hint"):
                    self._input_hint.update("VIM: i/a insert • hjkl move • /vim off")
                    self._input_hint.remove_class("hidden")
            else:
                # Insert mode - show vim hints in input_hint
                self._vim_indicator.update(" INSERT ")
                self._vim_indicator.remove_class("vim-normal-indicator")
                self._vim_indicator.add_class("vim-insert-indicator")
                if hasattr(self, "_input_hint"):
                    self._input_hint.update("VIM: Esc normal • Enter submit • /vim off")
                    self._input_hint.remove_class("hidden")

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
  Tab/←/→         - Navigate between agents
  Ctrl+G          - Show this help
  Ctrl+T          - Toggle task plan (collapse/expand)
  Ctrl+Shift+T    - Toggle light/dark theme
  Ctrl+P          - Toggle CWD context auto-include
  Ctrl+U          - Show subagents panel
  Ctrl+C          - Cancel current turn (double to quit)
  Ctrl+D          - Quit immediately

MODAL SHORTCUTS (when not typing):
  s               - System status log
  o               - Orchestrator events
  i               - Agent selector
  c               - Coordination table
  v               - Vote results

TOOL CARDS:
  Click           - Expand/collapse tool card
  Double-click    - Open full detail modal

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
                # Reset round state when doing full reset
                if hasattr(widget, "reset_round_state"):
                    widget.reset_round_state()
            self.notify("Agent panels reset", severity="information")

        def _update_all_loading_text(self, message: str) -> None:
            """Update loading text on all agent panels."""
            for widget in self.agent_widgets.values():
                widget._update_loading_text(message)

        async def _flush_buffers(self):
            """Flush buffered content to widgets.

            Uses frame-aware batching to prevent UI blocking:
            - Limits items processed per flush to max_buffer_batch (default 5)
            - Remaining items stay in buffer for next flush cycle
            """
            self._pending_flush = False
            all_updates = []
            max_items_per_agent = 5  # Limit to prevent blocking

            for agent_id in self.coordination_display.agent_ids:
                with self._buffer_lock:
                    if not self._buffers[agent_id]:
                        continue
                    # Take only max_items_per_agent items per flush
                    items_to_process = self._buffers[agent_id][:max_items_per_agent]
                    self._buffers[agent_id] = self._buffers[agent_id][max_items_per_agent:]

                if items_to_process and agent_id in self.agent_widgets:
                    all_updates.append((agent_id, items_to_process))

            if all_updates:
                with self.batch_update():
                    for agent_id, buffer_copy in all_updates:
                        for item in buffer_copy:
                            await self.update_agent_widget(
                                agent_id,
                                item["content"],
                                item.get("type", "thinking"),
                                item.get("tool_call_id"),
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

        async def update_agent_widget(
            self,
            agent_id: str,
            content: str,
            content_type: str,
            tool_call_id: Optional[str] = None,
        ):
            """Update agent widget with content."""
            if agent_id in self.agent_widgets:
                self.agent_widgets[agent_id].add_content(content, content_type, tool_call_id)

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
            # NOTE: Activity indicator removed from ribbon - see Phase 13.2 for ExecutionStatusLine
            # Update StatusBar activity indicator with granular phase icons
            if self._status_bar:
                # Map status strings to activity types for phase icons
                STATUS_TO_ACTIVITY = {
                    # Thinking states
                    "working": "thinking",
                    "thinking": "thinking",
                    "processing": "thinking",
                    # Streaming states
                    "streaming": "streaming",
                    # Tool execution states
                    "tool_call": "tool",
                    "mcp_tool_called": "tool",
                    "custom_tool_called": "tool",
                    "mcp_tool_response": "thinking",  # After tool, back to thinking
                    "custom_tool_response": "thinking",
                    "mcp_tool_error": "error",
                    "custom_tool_error": "error",
                    # Voting states
                    "voting": "voting",
                    "voted": "waiting",  # After voting, waiting for others
                    # Waiting states
                    "waiting": "waiting",
                    # Completion states - "completed" means agent finished one task,
                    # but may still be active in coordination (voting, restart, etc.)
                    # Only truly idle when coordination is done
                    "error": "error",
                    "complete": "waiting",  # Completed one task, waiting for coordination
                    "completed": "waiting",  # Same - waiting, not truly idle
                    "idle": "idle",
                    "done": "idle",
                    "finished": "idle",  # Only explicit "idle"/"done"/"finished" = truly idle
                }
                activity = STATUS_TO_ACTIVITY.get(status, "thinking")  # Default to thinking if unknown
                self._status_bar.set_agent_activity(agent_id, activity)
                # Also maintain backwards compatibility with set_agent_working
                is_working = activity not in ("idle",)
                self._status_bar.set_agent_working(agent_id, is_working)

                # Trigger pulsing animation for active agents
                from massgen.logger_config import logger

                logger.info(f"[PULSE] update_agent_status: agent={agent_id}, status={status}, activity={activity}")
                if activity in ("thinking", "tool", "streaming"):
                    self._start_agent_pulse(agent_id)
                else:
                    self._stop_agent_pulse(agent_id)

            # Phase 13.2: Update ExecutionStatusLine with agent state
            if self._execution_status_line:
                # Map to ExecutionStatusLine states
                # "voted" = green checkmark (waiting for consensus)
                # "done" = dim checkmark (final presentation in progress)
                STATE_MAP = {
                    "working": "working",
                    "thinking": "working",
                    "streaming": "working",
                    "processing": "working",
                    "tool_call": "working",
                    "mcp_tool_called": "working",
                    "custom_tool_called": "working",
                    "mcp_tool_response": "working",
                    "custom_tool_response": "working",
                    "voting": "working",
                    "voted": "voted",  # Green checkmark - agent voted
                    "waiting": "voted",  # Waiting for others after voting
                    "complete": "voted",  # Finished, waiting for consensus
                    "completed": "voted",
                    "done": "done",  # Dim checkmark - final presentation happening
                    "error": "error",
                    "cancelled": "cancelled",
                    "idle": "idle",
                }
                mapped_state = STATE_MAP.get(status, "working")
                self._execution_status_line.set_agent_state(agent_id, mapped_state)
            # Update execution status bar with new agent icons
            self._update_execution_status()

        def update_agent_timeout(self, agent_id: str, timeout_state: Dict[str, Any]):
            """Update agent timeout display.

            Args:
                agent_id: The agent whose timeout to update
                timeout_state: Timeout state from orchestrator
            """
            if agent_id in self.agent_widgets:
                self.agent_widgets[agent_id].update_timeout(timeout_state)

            # Also update the status ribbon timeout display
            if self._status_ribbon:
                remaining = timeout_state.get("remaining_soft")
                self._status_ribbon.set_timeout(agent_id, remaining)
                self._status_ribbon.set_timeout_state(agent_id, timeout_state)

        def update_hook_execution(
            self,
            agent_id: str,
            tool_call_id: Optional[str],
            hook_info: Dict[str, Any],
        ):
            """Update display with hook execution information.

            Args:
                agent_id: The agent whose tool call has hooks
                tool_call_id: Optional ID of the tool call
                hook_info: Hook execution info
            """
            from massgen.logger_config import logger

            logger.info(
                f"[MassGenApp] update_hook_execution: agent={agent_id}, " f"tool_call_id={tool_call_id}, has_widget={agent_id in self.agent_widgets}",
            )
            if agent_id in self.agent_widgets:
                self.agent_widgets[agent_id].add_hook_to_tool(tool_call_id, hook_info)
            else:
                logger.warning(f"[MassGenApp] Agent {agent_id} not in agent_widgets")

        def update_token_usage(self, agent_id: str, usage: Dict[str, Any]):
            """Update token usage display for an agent.

            Phase 13.1: Wire token/cost updates to status ribbon.

            Args:
                agent_id: The agent whose token usage to update
                usage: Token usage dict with input_tokens, output_tokens, estimated_cost
            """
            if self._status_ribbon:
                total_tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                self._status_ribbon.set_tokens(agent_id, total_tokens)
                self._status_ribbon.set_cost(agent_id, usage.get("estimated_cost", 0))

        def add_orchestrator_event(self, event: str):
            """Add orchestrator event to internal tracking."""
            timestamp = datetime.now().strftime("%H:%M:%S")
            self._orchestrator_events.append(f"{timestamp} {event}")

        def show_subagent_card_from_spawn(
            self,
            agent_id: str,
            args: Dict[str, Any],
            call_id: str,
        ):
            """Show SubagentCard immediately when spawn_subagents is called.

            This is called from a background thread via notify_subagent_spawn_started,
            BEFORE the blocking MCP tool execution begins. This allows showing the
            SubagentCard with pending subagents immediately rather than waiting
            for tool completion.

            Args:
                agent_id: ID of the agent spawning subagents
                args: Tool arguments containing tasks list
                call_id: Tool call ID for card identification
            """
            from massgen.subagent.models import SubagentDisplayData

            tui_log(f"show_subagent_card_from_spawn: agent_id={agent_id}, call_id={call_id}")

            # Validate we have tasks in args
            tasks = args.get("tasks", [])
            if not tasks:
                tui_log("show_subagent_card_from_spawn: no tasks in args")
                return

            tui_log(f"show_subagent_card_from_spawn: creating card for {len(tasks)} tasks")

            # Create SubagentDisplayData for each task (all pending/running)
            subagents = []
            for i, task_data in enumerate(tasks):
                subagent_id = task_data.get("subagent_id", task_data.get("id", f"subagent_{i}"))
                task_desc = task_data.get("task", "")

                subagents.append(
                    SubagentDisplayData(
                        id=subagent_id,
                        task=task_desc,
                        status="running",  # All start as running
                        progress_percent=0,
                        elapsed_seconds=0.0,
                        timeout_seconds=task_data.get("timeout_seconds", 300),
                        workspace_path="",  # Not yet assigned
                        workspace_file_count=0,
                        last_log_line="Starting...",
                        error=None,
                        answer_preview=None,
                        log_path=None,
                    ),
                )

            if not subagents:
                return

            # Get the agent's timeline and add the card
            if agent_id in self.agent_widgets:
                panel = self.agent_widgets[agent_id]
                try:
                    timeline = panel.query_one(f"#{panel._timeline_section_id}", TimelineSection)

                    # Create and add SubagentCard to timeline
                    card = SubagentCard(
                        subagents=subagents,
                        tool_call_id=call_id,
                        id=f"subagent_{call_id}",
                    )
                    timeline.add_widget(card)
                    tui_log(
                        f"show_subagent_card_from_spawn: added SubagentCard with {len(subagents)} pending subagents",
                    )
                except Exception as e:
                    tui_log(f"show_subagent_card_from_spawn: failed to add card: {e}")
            else:
                tui_log(f"show_subagent_card_from_spawn: agent {agent_id} not in agent_widgets")

        def show_final_presentation(
            self,
            answer: str,
            vote_results=None,
            selected_agent=None,
        ):
            """Display final answer modal with flush effect and winner celebration."""
            import time

            if not selected_agent:
                return

            # Track the winner
            self._winner_agent_id = selected_agent

            # Mark the winning answer(s) in tracked answers and extract workspace_path
            winner_workspace_path = None
            for ans in self._answers:
                if ans.get("agent_id") == selected_agent:
                    ans["is_winner"] = True
                    ans["is_final"] = True
                    # Get workspace_path from the most recent winning answer
                    if ans.get("workspace_path"):
                        winner_workspace_path = ans.get("workspace_path")

            # Add to conversation history
            if self._current_question and answer:
                model_name = self.coordination_display.agent_models.get(selected_agent, "")
                self._conversation_history.append(
                    {
                        "question": self._current_question,
                        "answer": answer,
                        "agent_id": selected_agent,
                        "model": model_name,
                        "turn": len(self._conversation_history) + 1,
                        "timestamp": time.time(),
                        "workspace_path": winner_workspace_path,
                    },
                )

            # Celebrate the winner
            self._celebrate_winner(selected_agent, answer)

            # Add completion card with the final answer
            self._add_final_completion_card(selected_agent, vote_results or {}, answer)

        def _add_final_completion_card(self, agent_id: str, vote_results: Dict[str, Any], answer: str = ""):
            """Add completion card with the final answer at the end of final presentation.

            This card provides:
            - Final answer content
            - Vote summary
            - Action buttons (Copy, Workspace)
            - Continue conversation prompt
            """
            try:
                logger.info(
                    f"[FinalAnswer] _add_final_completion_card: agent_id={agent_id} " f"answer_len={len(answer)} vote_keys={list(vote_results.keys())}",
                )
            except Exception:
                pass

            # Prevent duplicate cards
            if hasattr(self, "_final_completion_added") and self._final_completion_added:
                return
            self._final_completion_added = True
            self._final_header_added = True  # Compat flag for other code paths

            # Track for post-evaluation routing
            self._final_presentation_agent = agent_id

            # 1. Auto-switch to winner's tab and mark with trophy
            if self._tab_bar:
                self._tab_bar.set_active(agent_id)
                self._tab_bar.set_winner(agent_id)

            # 2. Update ExecutionStatusLine: all agents to done
            if self._execution_status_line:
                for aid in self._execution_status_line._agent_ids:
                    self._execution_status_line.set_agent_state(aid, "done")

            # 3. Show the winner's panel (hide others)
            if agent_id in self.agent_widgets:
                if self._active_agent_id and self._active_agent_id in self.agent_widgets:
                    self.agent_widgets[self._active_agent_id].add_class("hidden")
                self.agent_widgets[agent_id].remove_class("hidden")
                self._active_agent_id = agent_id

            if agent_id not in self.agent_widgets:
                return

            panel = self.agent_widgets[agent_id]

            try:
                timeline = panel.query_one(f"#{panel._timeline_section_id}", TimelineSection)

                # Get coordination_tracker for answer label lookup
                tracker = None
                if hasattr(self.coordination_display, "orchestrator") and self.coordination_display.orchestrator:
                    tracker = getattr(self.coordination_display.orchestrator, "coordination_tracker", None)

                # Build formatted vote results for the card
                vote_counts = vote_results.get("vote_counts", {})
                winner = vote_results.get("winner", agent_id)
                is_tie = vote_results.get("is_tie", False)

                def get_answer_label(aid):
                    """Convert agent ID to answer label (e.g., 'A1.1')."""
                    if tracker:
                        label = tracker.get_latest_answer_label(aid)
                        if label:
                            return label.replace("agent", "A")
                        num = tracker._get_agent_number(aid)
                        return f"A{num}" if num else aid
                    return aid

                # Build formatted vote results for the card
                formatted_vote_results = {
                    "vote_counts": {get_answer_label(aid): cnt for aid, cnt in vote_counts.items()},
                    "winner": get_answer_label(winner),
                    "is_tie": is_tie,
                }

                # Get context paths from orchestrator
                context_paths = {}
                if hasattr(self.coordination_display, "orchestrator") and self.coordination_display.orchestrator:
                    orch = self.coordination_display.orchestrator
                    if hasattr(orch, "get_context_path_writes_categorized"):
                        context_paths = orch.get_context_path_writes_categorized()

                # Remove any existing completion card to avoid duplicate ID issues
                try:
                    existing_card = timeline.query_one("#final_presentation_card", FinalPresentationCard)
                    existing_card.remove()
                except Exception:
                    pass  # No existing card, that's fine

                # Create the final answer card with content
                card = FinalPresentationCard(
                    agent_id=agent_id,
                    vote_results=formatted_vote_results,
                    context_paths=context_paths,
                    id="final_presentation_card",
                )

                # Tag with current round for CSS visibility switching
                current_round = getattr(panel, "_current_round", 1)
                card.add_class(f"round-{current_round}")

                timeline.add_widget(card)
                self._final_presentation_card = card

                # Stop the round timer - final presentation is the end state
                if self._status_ribbon:
                    self._status_ribbon.stop_all_round_timers()

                try:
                    logger.info(
                        f"[FinalAnswer] Timeline children after card add: {len(list(timeline.children))} " f"current_round={current_round}",
                    )
                except Exception:
                    pass

                # Set the answer content and mark as complete
                def set_content_and_complete():
                    if answer:
                        card.append_chunk(answer)
                    card.complete()
                    try:
                        logger.info(
                            "[FinalAnswer] Card completed and locked to timeline",
                        )
                    except Exception:
                        pass
                    # Auto-lock timeline to show only final answer
                    timeline.lock_to_final_answer("final_presentation_card")
                    card.set_locked_mode(True)
                    # Auto-collapse task plan when final presentation shows
                    try:
                        pinned_container = panel.query_one(f"#{panel._pinned_task_plan_id}", Container)
                        pinned_container.add_class("collapsed")
                        panel._task_plan_visible = False
                    except Exception:
                        pass
                    # Update input placeholder to encourage follow-up
                    if hasattr(self, "question_input"):
                        self.question_input.placeholder = "Type your follow-up question..."

                self.set_timer(0.1, set_content_and_complete)

                # Scroll to show the card
                timeline.scroll_to_widget("final_presentation_card")

            except Exception as e:
                logger.debug(f"Failed to create final completion card: {e}")

        def show_post_evaluation(self, content: str, agent_id: str):
            """Show post-evaluation content in the FinalPresentationCard.

            Routes post-evaluation content to the unified card instead of
            using separate banners and timeline items.
            """
            import re

            # Route to the FinalPresentationCard if available
            if self._final_presentation_card:
                # Filter out JSON tool call content before passing to card
                if content:
                    stripped = content.strip()

                    # Skip JSON fragments and tool call content
                    json_indicators = [
                        '"action_type"',
                        '"submit_data"',
                        '"restart_data"',
                        '"action": "submit"',
                        '"confirmed": true',
                        '"confirmed":true',
                        '": "submit"',
                        '": "restart_orchestration"',
                    ]

                    is_json_fragment = any(ind in content for ind in json_indicators)

                    # Also skip lines that are just JSON syntax
                    is_json_syntax = stripped in ["{", "}", "```json", "```", '",', '",']
                    is_json_syntax = is_json_syntax or stripped.startswith('"action')
                    is_json_syntax = is_json_syntax or stripped.startswith('"confirmed')
                    is_json_syntax = is_json_syntax or stripped.startswith('"submit')
                    is_json_syntax = is_json_syntax or stripped.startswith('"restart')

                    if not is_json_fragment and not is_json_syntax:
                        # Filter out any remaining JSON blocks
                        clean_content = content

                        # Remove JSON code blocks
                        clean_content = re.sub(r"```json\s*\{[\s\S]*?\}\s*```", "", clean_content)

                        # Remove inline JSON objects with action_type
                        clean_content = re.sub(
                            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*"action_type"[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',
                            "",
                            clean_content,
                            flags=re.DOTALL,
                        )

                        # Clean up any leftover JSON fragments
                        clean_content = re.sub(r"^\s*[\{\}]\s*$", "", clean_content, flags=re.MULTILINE)

                        clean_content = clean_content.strip()
                        if clean_content:
                            # Set status to evaluating and add content
                            self._final_presentation_card.set_post_eval_status("evaluating", clean_content)

            self.add_orchestrator_event(f"[POST-EVALUATION] {agent_id}: {content}")

        def show_post_evaluation_tool(self, tool_name: str, args: dict, agent_id: str):
            """Update FinalPresentationCard with post-evaluation tool decision.

            Args:
                tool_name: "submit" or "restart_orchestration"
                args: Tool arguments dict
                agent_id: The winner agent ID
            """
            # Update the FinalPresentationCard status based on tool decision
            if self._final_presentation_card:
                if tool_name == "submit":
                    self._final_presentation_card.set_post_eval_status("verified")
                elif tool_name == "restart_orchestration":
                    reason = args.get("reason", "No reason provided")
                    self._final_presentation_card.set_post_eval_status("restart", f"Reason: {reason}")

        def end_post_evaluation(self, agent_id: str):
            """Mark post-evaluation as complete via the FinalPresentationCard.

            This finalizes the card by:
            1. Marking post-eval as verified (if not already set to restart)
            2. Calling complete() to show footer with Copy/Workspace buttons
            3. Storing the final answer content for view-based navigation
            """
            # Finalize the FinalPresentationCard
            if self._final_presentation_card:
                # Mark as verified when post-eval completes (unless it's a restart request)
                if self._final_presentation_card._post_eval_status in ("none", "evaluating"):
                    self._final_presentation_card.set_post_eval_status("verified")

                # Mark the card as complete (shows footer with buttons)
                self._final_presentation_card.complete()

                # Auto-lock timeline to show only final answer
                if agent_id in self.agent_widgets:
                    panel = self.agent_widgets[agent_id]
                    try:
                        timeline = panel.query_one(f"#{panel._timeline_section_id}", TimelineSection)
                        timeline.lock_to_final_answer("final_presentation_card")
                        self._final_presentation_card.set_locked_mode(True)
                        # Update input placeholder to encourage follow-up
                        if hasattr(self, "question_input"):
                            self.question_input.placeholder = "Type your follow-up question..."
                    except Exception:
                        pass

                # Phase 12.4: Store final answer for view-based navigation
                if agent_id in self.agent_widgets:
                    panel = self.agent_widgets[agent_id]

                    # Get the final answer content from the card
                    final_content = getattr(self._final_presentation_card, "_answer_content", "")
                    vote_results = getattr(self._final_presentation_card, "_vote_results", {})

                    # Store for the FinalAnswerView
                    final_metadata = {
                        "winner": agent_id,
                        "vote_counts": vote_results.get("vote_counts", {}),
                        "total_rounds": panel.get_current_round(),
                        "agreement": sum(1 for v in vote_results.get("vote_counts", {}).values() if v > 0),
                        "total_agents": len(self.agent_widgets),
                    }
                    panel.set_final_answer(final_content, final_metadata)

                    # Mark all agents' ribbons as having final answer available
                    if self._status_ribbon:
                        for aid in self.agent_widgets:
                            self._status_ribbon.set_final_answer_available(aid, True)

                    try:
                        timeline = panel.query_one(f"#{panel._timeline_section_id}", TimelineSection)
                        timeline._auto_scroll()
                    except Exception:
                        pass

        def begin_final_stream(self, agent_id: str, vote_results: Dict[str, Any]):
            """DEPRECATED: Start final presentation streaming.

            This method is kept for backwards compatibility but is no longer the
            primary path. Use _add_final_completion_card() instead.

            Final presentation content now flows through the normal pipeline
            (update_agent_content), and a completion card is added at the end.
            """
            # Prevent duplicate cards - check if we've already started or if winner was quick-highlighted
            if hasattr(self, "_final_header_added") and self._final_header_added:
                return
            if hasattr(self, "_winner_quick_highlighted") and self._winner_quick_highlighted:
                # Winner already shown via highlight_winner_quick, skip adding another card
                # But still set up for streaming - the card was already created by highlight_winner_quick
                self._final_presentation_agent = agent_id
                self._final_header_added = True  # Prevent future duplicates
                if agent_id in self.agent_widgets:
                    panel = self.agent_widgets[agent_id]
                    try:
                        timeline = panel.query_one(f"#{panel._timeline_section_id}", TimelineSection)
                        self._final_stream_timeline = timeline
                    except Exception:
                        pass
                return

            # Store the winner agent for routing chunks
            self._final_presentation_agent = agent_id
            self._final_presentation_card = None  # Will hold the FinalPresentationCard
            self._final_stream_timeline = None  # Track timeline for streaming
            self._final_header_added = True  # Track that card was added
            self._post_eval_header_added = False  # Reset post-eval tracking

            # 1. Auto-switch to winner's tab
            if self._tab_bar:
                self._tab_bar.set_active(agent_id)
                self._tab_bar.set_winner(agent_id)

            # 1.5. Update ExecutionStatusLine: dim checkmarks for non-presenting, dots for presenter
            if self._execution_status_line:
                for aid in self._execution_status_line._agent_ids:
                    if aid == agent_id:
                        # Presenting agent goes back to working dots
                        self._execution_status_line.set_agent_state(aid, "working")
                    else:
                        # Non-presenting agents get dim checkmark
                        self._execution_status_line.set_agent_state(aid, "done")

            # 2. Show the agent panel for the winner (remove hidden class)
            if agent_id in self.agent_widgets:
                if self._active_agent_id and self._active_agent_id in self.agent_widgets:
                    self.agent_widgets[self._active_agent_id].add_class("hidden")
                self.agent_widgets[agent_id].remove_class("hidden")
                self._active_agent_id = agent_id

            # 3. Create FinalPresentationCard and add to timeline
            if agent_id in self.agent_widgets:
                panel = self.agent_widgets[agent_id]

                try:
                    timeline = panel.query_one(f"#{panel._timeline_section_id}", TimelineSection)
                    self._final_stream_timeline = timeline

                    # Get coordination_tracker for answer label lookup
                    tracker = None
                    if hasattr(self.coordination_display, "orchestrator") and self.coordination_display.orchestrator:
                        tracker = getattr(self.coordination_display.orchestrator, "coordination_tracker", None)

                    # Build formatted vote results for the card
                    vote_counts = vote_results.get("vote_counts", {})
                    winner = vote_results.get("winner", agent_id)
                    is_tie = vote_results.get("is_tie", False)

                    def get_answer_label(aid):
                        """Convert agent ID to answer label (e.g., 'A1.1')."""
                        if tracker:
                            label = tracker.get_latest_answer_label(aid)
                            if label:
                                return label.replace("agent", "A")
                            # Fallback to agent number
                            num = tracker._get_agent_number(aid)
                            return f"A{num}" if num else aid
                        return aid

                    # Build formatted vote results for the card
                    formatted_vote_results = {
                        "vote_counts": {get_answer_label(aid): cnt for aid, cnt in vote_counts.items()},
                        "winner": get_answer_label(winner),
                        "is_tie": is_tie,
                    }

                    # Create the unified card
                    card = FinalPresentationCard(
                        agent_id=agent_id,
                        vote_results=formatted_vote_results,
                        id="final_presentation_card",
                    )
                    # Tag with current round for CSS visibility switching
                    current_round = getattr(panel, "_current_round", 1)
                    card.add_class(f"round-{current_round}")
                    # Note: Removed full-width-mode to allow tool cards to be visible
                    # during final presentation (was causing content cutoff issue)
                    timeline.add_widget(card)
                    self._final_presentation_card = card

                    # Scroll to show the card
                    timeline.scroll_to_widget("final_presentation_card")
                except Exception as e:
                    logger.debug(f"Failed to create final presentation card: {e}")

        def update_final_stream(self, chunk: str):
            """DEPRECATED: Append streaming chunks to the FinalPresentationCard.

            This method is kept for backwards compatibility but is no longer the
            primary path. Final presentation content now flows through the normal
            pipeline (update_agent_content).
            """
            if not chunk:
                return

            # Buffer chunks if card doesn't exist yet (race condition with highlight_winner_quick)
            if not self._final_presentation_card:
                if not hasattr(self, "_pending_final_chunks"):
                    self._pending_final_chunks = []
                self._pending_final_chunks.append(chunk)
                return

            # Flush any pending chunks first (from before card was created)
            if hasattr(self, "_pending_final_chunks") and self._pending_final_chunks:
                for pending_chunk in self._pending_final_chunks:
                    try:
                        self._final_presentation_card.append_chunk(pending_chunk)
                    except Exception as e:
                        logger.error(f"FinalPresentationCard.append_chunk (pending) failed: {e}")
                self._pending_final_chunks = []

            # Now append the current chunk
            try:
                self._final_presentation_card.append_chunk(chunk)
            except Exception as e:
                logger.error(f"FinalPresentationCard.append_chunk failed: {e}")

        def end_final_stream(self):
            """DEPRECATED: Mark the final presentation streaming as complete.

            This method is kept for backwards compatibility but is no longer the
            primary path. The completion card (with footer) is now added via
            _add_final_completion_card().
            """
            # Only end if we actually started
            if not getattr(self, "_final_header_added", False):
                return

            # Mark the card's streaming as complete (but don't show footer yet)
            # Footer will appear after post-evaluation via end_post_evaluation
            if self._final_presentation_card:
                # Don't call complete() yet - that shows footer
                # Just flush the buffer
                pass

            # Clear the streaming timeline reference (keep card for post-eval)
            self._final_stream_timeline = None

            if self.post_eval_panel and not self.coordination_display._post_evaluation_lines:
                self.post_eval_panel.hide()

        def highlight_winner_quick(self, winner_id: str, vote_results: Dict[str, Any]) -> None:
            """Highlight the winner in no-refinement mode (skip_final_presentation).

            This is called when refinement is OFF, so we just mark the winner
            without streaming a new final presentation. The existing answer
            was already shown via new_answer tool cards.

            Args:
                winner_id: The winning agent's ID
                vote_results: Vote results dict with vote_counts, winner, is_tie, etc.
            """
            # Prevent duplicate highlighting or if final presentation already started
            if hasattr(self, "_winner_quick_highlighted") and self._winner_quick_highlighted:
                return
            if hasattr(self, "_final_header_added") and self._final_header_added:
                return  # Final presentation banner already added
            self._winner_quick_highlighted = True

            # 1. Auto-switch to winner's tab and mark with trophy
            if self._tab_bar:
                self._tab_bar.set_active(winner_id)
                self._tab_bar.set_winner(winner_id)

            # 1.5. Update ExecutionStatusLine: all agents to done (no streaming in quick mode)
            if self._execution_status_line:
                for aid in self._execution_status_line._agent_ids:
                    self._execution_status_line.set_agent_state(aid, "done")

            # 2. Show the winner's panel (hide others)
            if winner_id in self.agent_widgets:
                if self._active_agent_id and self._active_agent_id in self.agent_widgets:
                    self.agent_widgets[self._active_agent_id].add_class("hidden")
                self.agent_widgets[winner_id].remove_class("hidden")
                self._active_agent_id = winner_id

            # 3. Add a "WINNER SELECTED" card to the winner's timeline using FinalPresentationCard
            if winner_id in self.agent_widgets:
                panel = self.agent_widgets[winner_id]
                try:
                    timeline = panel.query_one(f"#{panel._timeline_section_id}", TimelineSection)

                    # Get coordination_tracker for answer label lookup
                    tracker = None
                    if hasattr(self.coordination_display, "orchestrator") and self.coordination_display.orchestrator:
                        tracker = getattr(self.coordination_display.orchestrator, "coordination_tracker", None)

                    # Build vote summary with answer labels (A1.1 format)
                    vote_counts = vote_results.get("vote_counts", {})
                    winner = vote_results.get("winner", winner_id)
                    is_tie = vote_results.get("is_tie", False)

                    def get_answer_label(aid):
                        """Convert agent ID to answer label (e.g., 'A1.1')."""
                        if tracker:
                            label = tracker.get_latest_answer_label(aid)
                            if label:
                                return label.replace("agent", "A")
                            # Fallback to agent number
                            num = tracker._get_agent_number(aid)
                            return f"A{num}" if num else aid
                        return aid

                    # Build formatted vote results for the card
                    formatted_vote_results = {
                        "vote_counts": {get_answer_label(aid): cnt for aid, cnt in vote_counts.items()},
                        "winner": get_answer_label(winner),
                        "is_tie": is_tie,
                    }

                    # Create the completion card (no streaming content - answer is already in timeline)
                    card = FinalPresentationCard(
                        agent_id=winner_id,
                        vote_results=formatted_vote_results,
                        id="winner_selected_card",
                    )
                    # Tag with current round for CSS visibility switching
                    card.add_class(f"round-{self._current_round}")
                    # Use completion-only mode - content already in timeline via normal pipeline
                    card.add_class("completion-only")
                    timeline.add_widget(card)
                    self._final_presentation_card = card

                    # Auto-lock timeline to show only final answer
                    def auto_lock_after_add():
                        try:
                            timeline.lock_to_final_answer("winner_selected_card")
                            card.set_locked_mode(True)
                            # Update input placeholder to encourage follow-up
                            if hasattr(self, "question_input"):
                                self.question_input.placeholder = "Type your follow-up question..."
                        except Exception:
                            pass

                    self.set_timer(0.1, auto_lock_after_add)

                    # Scroll to show the card
                    timeline.scroll_to_widget("winner_selected_card")

                    # Phase 12.4: Mark final answer as available for view-based navigation
                    # Note: Final answer content will be set via set_final_answer() when streaming completes
                    # For now, mark final answer as available in the ribbon
                    if self._status_ribbon:
                        self._status_ribbon.set_final_answer_available(winner_id, True)

                except Exception as e:
                    logger.debug(f"Failed to add winner selected card: {e}")

            # 4. Show toast notification
            self.notify(f"🏆 [bold]{winner_id}[/] selected as winner!", timeout=4)

        def clear_winner_state(self):
            """Reset winner highlighting and panel dimming for a new turn."""
            # Clear winner status from tab bar
            if self._tab_bar:
                self._tab_bar.clear_winner()

            # Undim all panels
            for panel in self.agent_widgets.values():
                panel.undim()

            # Reset final presentation tracking flags for the new turn
            self._final_header_added = False
            self._final_completion_added = False  # Reset completion card flag
            self._post_eval_header_added = False
            self._post_eval_footer_added = False
            self._final_stream_content = ""
            self._final_stream_timeline = None
            self._final_presentation_agent = None
            self._winner_quick_highlighted = False

        def prepare_for_new_turn(self, turn: int, previous_answer: Optional[str] = None):
            """Fully reset the UI for a new turn while preserving conversation context.

            Args:
                turn: The new turn number (1-indexed)
                previous_answer: Optional summary of the previous turn's answer
            """
            from massgen.logger_config import logger

            logger.info(f"[TUI-App] prepare_for_new_turn() called: turn={turn}, has_previous_answer={previous_answer is not None}")
            # Clear winner state and flags
            self.clear_winner_state()
            logger.info("[TUI-App] Winner state cleared")

            # Clear timeline content from all agent panels
            logger.info(f"[TUI-App] Clearing timelines for {len(self.agent_widgets)} agent panels")
            for agent_id, panel in self.agent_widgets.items():
                try:
                    logger.info(f"[TUI-App] Processing agent {agent_id}")
                    timeline = panel.query_one(f"#{panel._timeline_section_id}", TimelineSection)
                    logger.info(f"[TUI-App] Found timeline widget for {agent_id}")
                    # Clear the timeline content (add Round 1 only for turn 1)
                    timeline.clear(add_round_1=(turn == 1))
                    logger.info(f"[TUI-App] Timeline cleared for {agent_id}, add_round_1={turn == 1}")

                    # Add a turn separator banner if this is turn 2+
                    if turn > 1:
                        logger.info(f"[TUI-App] Adding turn {turn} banner for {agent_id}")
                        from massgen.frontend.displays.textual_widgets.content_sections import (
                            RestartBanner,
                        )

                        # CRITICAL: Suppress auto Round 1 insertion before adding turn banner.
                        # add_widget() calls _ensure_round_1_shown() which would add Round 1
                        # ABOVE the turn banner. We add Round 1 explicitly BELOW it instead.
                        timeline._round_1_shown = True

                        # Create a turn separator that shows context from previous turn
                        separator_label = f"══════ Turn {turn} ══════"
                        turn_banner = RestartBanner(
                            label=separator_label,
                            id=f"turn_{turn}_separator",
                        )
                        timeline.add_widget(turn_banner)
                        logger.info(f"[TUI-App] Turn banner added to timeline for {agent_id}")

                        # If we have a previous answer summary, show it collapsed
                        if previous_answer:
                            logger.info(f"[TUI-App] Adding previous answer context for {agent_id}")
                            from textual.widgets import Static

                            summary = previous_answer[:200] + "..." if len(previous_answer) > 200 else previous_answer
                            context_widget = Static(
                                f"[dim]Previous: {summary}[/]",
                                id=f"turn_{turn}_context",
                                markup=True,
                            )
                            timeline.add_widget(context_widget)

                        # CRITICAL: Add Round 1 separator BELOW the turn banner (and optional context)
                        # This ensures proper order: Turn X → [Context] → Round 1 → Content
                        logger.info(f"[TUI-App] Adding Round 1 separator for {agent_id}")
                        timeline.add_separator("Round 1", round_number=1)
                        timeline._round_1_shown = True  # Prevent _ensure_round_1_shown() from adding it again
                        logger.info("[TUI-App] Round 1 separator added, _round_1_shown set to True")

                        # Scroll to the turn banner to show the new turn at the top
                        try:
                            turn_banner.scroll_visible()
                            logger.info(f"[TUI-App] Scrolled to turn banner for {agent_id}")
                        except Exception as e:
                            logger.warning(f"[TUI-App] Failed to scroll to turn banner for {agent_id}: {e}")

                except Exception as e:
                    logger.error(f"[TUI-App] Failed to prepare timeline for {agent_id}: {e}", exc_info=True)

            # Reset any modal state
            # (modals should auto-dismiss but just in case)

            # Scroll to top of timelines (only for turn 1, turn 2+ scrolls to turn banner)
            if turn == 1:
                logger.info("[TUI-App] Scrolling to top for turn 1")
                for panel in self.agent_widgets.values():
                    try:
                        timeline = panel.query_one(f"#{panel._timeline_section_id}", TimelineSection)
                        timeline.scroll_home()
                    except Exception:
                        pass

            logger.info(f"[TUI-App] prepare_for_new_turn() complete for turn {turn}")

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
            # Update tab bar session info (turn + question)
            if self._tab_bar:
                self._tab_bar.update_turn(turn)
                self._tab_bar.update_question(question)
            if turn > 1:
                from massgen.logger_config import logger

                logger.info(f"[TUI] update_turn_header called for turn {turn}")

                separator = f"\n{'='*50}\n   TURN {turn}\n{'='*50}\n"
                for agent_id, widget in self.agent_widgets.items():
                    if hasattr(widget, "content_log"):
                        widget.content_log.write(separator)

                # CRITICAL: Reset round state for all agents at the start of each new turn
                # This ensures rounds restart at R1 for the new turn
                logger.info(f"[TUI] Resetting round state for {len(self.agent_widgets)} agent panels")
                for agent_id, widget in self.agent_widgets.items():
                    if hasattr(widget, "reset_round_state"):
                        logger.info(f"[TUI] Calling reset_round_state() on panel for agent {agent_id}")
                        widget.reset_round_state()
                        logger.info(f"[TUI] After reset: panel._current_round={widget._current_round}, panel._viewed_round={widget._viewed_round}")

                # CRITICAL: Reset status ribbon for all agents
                # The ribbon is at app level, not inside panels, so reset it directly
                if self._status_ribbon:
                    logger.info("[TUI] Resetting status ribbon for all agents")
                    self._status_ribbon.reset_round_state_all_agents()
                    logger.info("[TUI] Status ribbon reset complete")

                # CRITICAL: Reset turn-level state (answers, votes, buffers, etc.)
                # This ensures clean state for each new turn
                self.coordination_display.reset_turn_state()

        def set_input_enabled(self, enabled: bool):
            """Enable or disable mode controls during execution.

            Note: The input field is NEVER disabled - users can always type.
            During execution, input is queued for injection via HumanInputHook.

            Args:
                enabled: True when idle (normal input), False during execution (input queued).
            """
            # NOTE: We intentionally do NOT disable question_input anymore.
            # Users can type during execution and input gets queued for injection.
            # The _submit_question method handles this queueing logic.

            # Lock/unlock mode controls during execution
            # Defensive: ensure lock is released even if error occurs
            try:
                if enabled:
                    self._mode_state.unlock()
                else:
                    self._mode_state.lock()
            except Exception as e:
                # Ensure lock is released even if error occurs
                logger.error(f"Error in set_input_enabled: {e}")
                try:
                    self._mode_state.unlock()
                except Exception:
                    pass  # Best effort to recover
                raise

            # Update mode bar enabled state
            if self._mode_bar:
                self._mode_bar.set_enabled(enabled)

        def show_restart_banner(
            self,
            reason: str,
            instructions: str,
            attempt: int,
            max_attempts: int,
        ):
            """Show restart banner in header and all agent panels."""
            import time

            # Track the restart
            self._current_restart = {
                "attempt": attempt,
                "max_attempts": max_attempts,
                "reason": reason,
                "instructions": instructions,
                "timestamp": time.time(),
                "answers_at_restart": [a["answer_label"] for a in self._answers],
            }
            self._restart_history.append(self._current_restart.copy())

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

            # Update StatusBar to show restart count
            if self._status_bar:
                self._update_status_bar_restart_info()
                # Reset all agents to "thinking" state since they'll be working again
                for agent_id in self._status_bar._agent_order:
                    self._status_bar.set_agent_activity(agent_id, "thinking")

            # Also show prominent restart separator in ALL agent panels
            for agent_id, panel in self.agent_widgets.items():
                panel.show_restart_separator(attempt, reason)

        def show_restart_context(self, reason: str, instructions: str):
            """Show restart context."""
            if self.header_widget:
                self.header_widget.show_restart_context(reason, instructions)

        def show_agent_restart(self, agent_id: str, round_num: int):
            """Show that a specific agent is starting a new round.

            This is called when an agent restarts due to new context from other agents.
            Only affects the specified agent's panel.

            Args:
                agent_id: The agent that is restarting
                round_num: The new round number for this agent
            """
            panel = self.agent_widgets.get(agent_id)
            if panel:
                # Use start_new_round which handles timeline visibility and ribbon update
                panel.start_new_round(round_num, is_context_reset=False)

        def show_final_presentation_start(self, agent_id: str, vote_counts: Optional[Dict[str, int]] = None, answer_labels: Optional[Dict[str, str]] = None):
            """Show that the final presentation is starting for the winning agent.

            This shows a fresh view with a distinct "Final Presentation" banner.

            Args:
                agent_id: The winning agent presenting the final answer
                vote_counts: Optional dict of {agent_id: vote_count} for vote summary display
                answer_labels: Optional dict of {agent_id: label} for display (e.g., {"agent1": "A1.1"})
            """
            panel = self.agent_widgets.get(agent_id)
            if panel:
                # Use start_final_presentation which shows distinct green banner
                panel.start_final_presentation(vote_counts=vote_counts, answer_labels=answer_labels)

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

        def action_prev_agent(self):
            """Switch to previous agent tab."""
            if self._tab_bar:
                prev_agent = self._tab_bar.get_previous_agent()
                if prev_agent:
                    self._switch_to_agent(prev_agent)

        def action_show_subagents(self):
            """Show subagent modal for first running subagent.

            Searches all agent panels for subagent cards and opens the modal
            for the first running subagent found (or first overall).
            """
            # Find subagent cards in all agent panels
            for panel in self.agent_widgets.values():
                try:
                    subagent_cards = panel.query(SubagentCard)
                    for card in subagent_cards:
                        if card.subagents:
                            # Find first running subagent
                            running = [sa for sa in card.subagents if sa.status == "running"]
                            if running:
                                self.push_screen(SubagentModal(running[0], card.subagents))
                                return
                            # Fallback to first subagent
                            self.push_screen(SubagentModal(card.subagents[0], card.subagents))
                            return
                except Exception:
                    continue

            self.notify("No active subagents", severity="information", timeout=2)

        def _switch_to_agent(self, agent_id: str) -> None:
            """Switch the visible agent tab.

            Args:
                agent_id: The agent ID to switch to.
            """
            tui_log(f"_switch_to_agent called: {agent_id}, current: {self._active_agent_id}")
            tui_log(f"  agent_widgets keys: {list(self.agent_widgets.keys())}")
            try:
                if agent_id == self._active_agent_id:
                    tui_log(f"  Already on {agent_id}, skipping")
                    return

                # Hide current panel
                if self._active_agent_id and self._active_agent_id in self.agent_widgets:
                    tui_log(f"  Hiding panel: {self._active_agent_id}")
                    self.agent_widgets[self._active_agent_id].add_class("hidden")

                # Show new panel - only if agent exists
                if agent_id in self.agent_widgets:
                    tui_log(f"  Showing panel: {agent_id}")
                    new_panel = self.agent_widgets[agent_id]
                    new_panel.remove_class("hidden")
                    # Auto-scroll to bottom so user sees latest content
                    try:
                        timeline = new_panel.query_one("#timeline_container", ScrollableContainer)
                        timeline._scroll_to_end(animate=False, force=True)
                    except Exception:
                        pass  # Timeline may not exist yet
                else:
                    tui_log(f"  Panel not found for: {agent_id}", level="warning")
                    # Agent panel doesn't exist yet, just update state

                # Update tab bar
                if self._tab_bar:
                    tui_log(f"  Updating tab bar active: {agent_id}")
                    self._tab_bar.set_active(agent_id)

                # Update status ribbon to show this agent's status
                if self._status_ribbon:
                    tui_log(f"  Updating status ribbon for: {agent_id}")
                    self._status_ribbon.set_agent(agent_id)

                # Phase 13.2: Update execution status line focused agent
                if self._execution_status_line:
                    self._execution_status_line.set_focused_agent(agent_id)

                self._active_agent_id = agent_id
                tui_log(f"  Switch complete to: {agent_id}")

                # Update current_agent_index for compatibility with existing methods
                try:
                    self.current_agent_index = self.coordination_display.agent_ids.index(agent_id)
                except ValueError:
                    pass
            except Exception as e:
                tui_log(f"  ERROR in _switch_to_agent: {e}", level="error")
                # Don't crash on tab switch errors

        def on_agent_tab_changed(self, event: AgentTabChanged) -> None:
            """Handle tab click from AgentTabBar."""
            tui_log(f"on_agent_tab_changed: {event.agent_id}")

            # In single-agent mode, clicking a different tab changes the selected agent
            if self._mode_state.is_single_agent_mode():
                # Block agent switching during execution
                if self._mode_state.is_locked():
                    tui_log("  Agent switch blocked - execution in progress")
                    self.notify("Cannot switch agents during execution", severity="warning", timeout=2)
                    event.stop()
                    return

                tui_log(f"  Single-agent mode: selecting {event.agent_id}")
                self._mode_state.selected_single_agent = event.agent_id
                if self._tab_bar:
                    self._tab_bar.set_single_agent_mode(True, event.agent_id)
                # Update agent panels with "in use" state
                self._update_agent_panels_in_use_state(event.agent_id)
                self.notify(f"Single agent: {event.agent_id}", severity="information", timeout=2)

            self._switch_to_agent(event.agent_id)
            event.stop()

        def on_view_selected(self, event: ViewSelected) -> None:
            """Handle view selection from AgentStatusRibbon dropdown.

            Switches the agent panel to show either a specific round or the final answer.
            """
            if event.agent_id not in self.agent_widgets:
                return

            panel = self.agent_widgets[event.agent_id]

            if event.view_type == "final_answer":
                panel.switch_to_final_answer()
            elif event.view_type == "round" and event.round_number is not None:
                # Check if we're currently viewing final answer BEFORE changing state
                was_viewing_final = panel._current_view == "final_answer"
                if was_viewing_final:
                    panel.switch_from_final_answer()
                panel.switch_to_round(event.round_number)

            event.stop()

        def on_session_info_clicked(self, event: SessionInfoClicked) -> None:
            """Handle click on session info to show full prompt."""
            tui_log(f"on_session_info_clicked: turn={event.turn}")
            # Show the full prompt in a text modal
            self.push_screen(
                TextContentModal(
                    title=f"Turn {event.turn} • Prompt",
                    content=event.question or "(No prompt)",
                ),
            )
            event.stop()

        # ============================================================
        # Mode Change Handlers
        # ============================================================

        def on_mode_changed(self, event: ModeChanged) -> None:
            """Handle mode toggle changes from ModeBar."""
            tui_log(f"on_mode_changed: {event.mode_type}={event.value}")

            # Block mode changes during execution
            if self._mode_state.is_locked():
                tui_log("  -> BLOCKED: execution in progress")
                self.notify(
                    "Cannot change modes during execution. Wait for completion or cancel first.",
                    severity="warning",
                    timeout=3,
                )
                # Revert the toggle to its previous state
                if event.mode_type == "plan" and self._mode_bar:
                    self._mode_bar.set_plan_mode(self._mode_state.plan_mode)
                elif event.mode_type == "agent" and self._mode_bar:
                    self._mode_bar.set_agent_mode(self._mode_state.agent_mode)
                elif event.mode_type == "refinement" and self._mode_bar:
                    self._mode_bar.set_refinement_mode(self._mode_state.refinement_enabled)
                event.stop()
                return

            if event.mode_type == "plan":
                self._handle_plan_mode_change(event.value)
            elif event.mode_type == "agent":
                self._handle_agent_mode_change(event.value)
            elif event.mode_type == "refinement":
                self._handle_refinement_mode_change(event.value == "on")

            event.stop()

        def on_override_requested(self, event: OverrideRequested) -> None:
            """Handle override button press from ModeBar."""
            tui_log("on_override_requested")
            self.action_trigger_override()
            event.stop()

        def on_plan_settings_clicked(self, event: PlanSettingsClicked) -> None:
            """Handle plan settings button click - show/hide plan options popover."""
            tui_log("on_plan_settings_clicked - START")

            # Block during execution
            if self._mode_state.is_locked():
                tui_log("  -> BLOCKED: execution in progress")
                self.notify(
                    "Cannot change plan settings during execution.",
                    severity="warning",
                    timeout=2,
                )
                event.stop()
                return

            if hasattr(self, "_plan_options_popover"):
                popover = self._plan_options_popover
                tui_log(f"  popover exists, visible={'visible' in popover.classes}, classes={list(popover.classes)}")
                if "visible" in popover.classes:
                    # Already visible - just hide it
                    tui_log("  -> hiding popover")
                    popover.hide()
                else:
                    # Not visible - update state and recompose to show plans, then show
                    tui_log("  -> updating state and showing")
                    self._update_plan_options_popover_state()
                    tui_log(f"  -> after state update, plans count: {len(popover._available_plans)}")
                    # Reset initialized flag before recompose to ignore spurious events
                    popover._initialized = False
                    tui_log("  -> set _initialized=False")
                    popover.refresh(recompose=True)
                    tui_log("  -> after refresh(recompose=True)")
                    # Use call_later to show after recompose completes (show() sets _initialized=True)
                    tui_log("  -> calling call_later(popover.show)")
                    self.call_later(popover.show)
            else:
                tui_log("  popover does not exist!")
            tui_log("on_plan_settings_clicked - END")
            event.stop()

        def on_plan_selected(self, event: PlanSelected) -> None:
            """Handle plan selection from popover."""
            tui_log(f"on_plan_selected: plan_id={event.plan_id}, is_new={event.is_new}")

            # Block during execution
            if self._mode_state.is_locked():
                tui_log("  -> BLOCKED: execution in progress")
                self.notify("Cannot change plan selection during execution.", severity="warning", timeout=2)
                event.stop()
                return

            if event.is_new:
                # User wants to create a new plan
                self._mode_state.selected_plan_id = None
                self.notify("Will create new plan on next query", severity="information", timeout=2)
            elif event.plan_id:
                # Specific plan selected
                self._mode_state.selected_plan_id = event.plan_id
                self.notify(f"Selected plan: {event.plan_id[:15]}...", severity="information", timeout=2)
            else:
                # Latest plan (auto) - don't notify on initial load
                self._mode_state.selected_plan_id = None
                # Only notify if popover is visible (user actually selected)
                if hasattr(self, "_plan_options_popover") and "visible" in self._plan_options_popover.classes:
                    pass  # Don't notify for "latest" - it's the default

            # Don't auto-hide - let user close with Close button or click settings again
            event.stop()

        def on_plan_depth_changed(self, event: PlanDepthChanged) -> None:
            """Handle plan depth change from popover."""
            tui_log(f"on_plan_depth_changed: depth={event.depth}")

            # Block during execution
            if self._mode_state.is_locked():
                tui_log("  -> BLOCKED: execution in progress")
                self.notify("Cannot change plan depth during execution.", severity="warning", timeout=2)
                event.stop()
                return

            self._mode_state.plan_config.depth = event.depth
            self.notify(f"Plan depth: {event.depth}", severity="information", timeout=2)
            event.stop()

        def on_broadcast_mode_changed(self, event: BroadcastModeChanged) -> None:
            """Handle broadcast mode change from popover."""
            tui_log(f"on_broadcast_mode_changed: broadcast={event.broadcast}")

            # Block during execution
            if self._mode_state.is_locked():
                tui_log("  -> BLOCKED: execution in progress")
                self.notify("Cannot change broadcast mode during execution.", severity="warning", timeout=2)
                event.stop()
                return

            self._mode_state.plan_config.broadcast = event.broadcast

            if event.broadcast == "human":
                self.notify("Broadcast: Agents can ask human questions", severity="information", timeout=2)
            elif event.broadcast == "agents":
                self.notify("Broadcast: Agents debate without human", severity="information", timeout=2)
            else:
                self.notify("Broadcast: Fully autonomous (no questions)", severity="warning", timeout=2)
            event.stop()

        def on_view_plan_requested(self, event: ViewPlanRequested) -> None:
            """Handle request to view full plan details in a modal."""
            tui_log(f"on_view_plan_requested: plan_id={event.plan_id}, tasks={len(event.tasks)}")

            if not event.tasks:
                self.notify("No tasks in this plan", severity="warning", timeout=2)
                event.stop()
                return

            # Open TaskPlanModal with the plan's tasks
            modal = TaskPlanModal(tasks=event.tasks)
            self.push_screen(modal)
            event.stop()

        def _update_plan_options_popover_state(self) -> None:
            """Update the plan options popover internal state (without recompose)."""
            if not hasattr(self, "_plan_options_popover"):
                return

            try:
                from massgen.plan_storage import PlanStorage

                storage = PlanStorage()
                plans = storage.get_all_plans(limit=5)

                # Update popover internal state
                popover = self._plan_options_popover
                popover._plan_mode = self._mode_state.plan_mode
                popover._available_plans = plans
                popover._current_plan_id = self._mode_state.selected_plan_id
                popover._current_depth = self._mode_state.plan_config.depth
                popover._current_broadcast = self._mode_state.plan_config.broadcast
                # Don't recompose - let the popover show with updated state
            except Exception as e:
                tui_log(f"_update_plan_options_popover_state error: {e}")

        def _enter_execute_mode(self) -> None:
            """Enter execute mode and show plan selector if plans exist.

            Called from action_toggle_plan_mode when transitioning from plan → execute.
            If no plans exist, stays in plan mode and shows a warning.
            """
            tui_log("_enter_execute_mode - START")

            try:
                from massgen.plan_storage import PlanStorage

                storage = PlanStorage()
                plans = storage.get_all_plans(limit=10)
                tui_log(f"  -> found {len(plans)} plans")

                if not plans:
                    # No plans available - stay in plan mode
                    # Revert mode bar if it was already set to "execute"
                    if self._mode_bar:
                        self._mode_bar.set_plan_mode("plan")
                    self.notify(
                        "No plans available. Create one first by submitting a query in Plan mode.",
                        severity="warning",
                        timeout=3,
                    )
                    tui_log("  -> no plans, staying in plan mode")
                    return

                # Set execute mode
                self._mode_state.plan_mode = "execute"
                if self._mode_bar:
                    self._mode_bar.set_plan_mode("execute")

                # Update input placeholder for execute mode
                if hasattr(self, "question_input"):
                    self.question_input.placeholder = "Press Enter to execute selected plan • or type instructions"

                # Show the plan selector popover
                self._show_plan_selector_popover(plans)

                self.notify("Execute Mode: Select a plan to run", severity="information", timeout=3)
                tui_log("_enter_execute_mode - END (success)")

            except Exception as e:
                tui_log(f"_enter_execute_mode error: {e}")
                self.notify(f"Error loading plans: {e}", severity="error", timeout=3)

        def _show_plan_selector_popover(self, plans: list) -> None:
            """Show the plan options popover configured for execute mode.

            Args:
                plans: List of available PlanSession objects.
            """
            tui_log(f"_show_plan_selector_popover: {len(plans)} plans")

            if not hasattr(self, "_plan_options_popover"):
                tui_log("  -> popover does not exist!")
                return

            popover = self._plan_options_popover

            # Update popover state for execute mode
            popover._plan_mode = "execute"
            popover._available_plans = plans
            popover._current_plan_id = self._mode_state.selected_plan_id

            # Reset initialized flag before recompose to ignore spurious events
            popover._initialized = False
            tui_log("  -> set _initialized=False, calling refresh(recompose=True)")

            # Recompose to show execute mode UI (plan selector)
            popover.refresh(recompose=True)

            # Show popover after recompose completes
            self.call_later(popover.show)
            tui_log("  -> called call_later(popover.show)")

        def _setup_plan_execution(self, user_text: str) -> Optional[str]:
            """Set up plan execution and return the execution prompt.

            Called from _submit_question when in execute mode.

            Args:
                user_text: User's input text (may be empty or contain instructions).

            Returns:
                The execution prompt to submit, or None if setup failed.
            """
            tui_log(f"_setup_plan_execution: user_text='{user_text[:50] if user_text else '(empty)'}'")

            try:
                from massgen.plan_execution import build_execution_prompt
                from massgen.plan_storage import PlanStorage

                # Get the selected plan
                plan_id = self._mode_state.selected_plan_id
                storage = PlanStorage()
                plans = storage.get_all_plans(limit=10)

                if not plans:
                    self.notify("No plans available to execute", severity="error", timeout=3)
                    tui_log("  -> no plans available")
                    return None

                # Find the plan to execute
                if plan_id and plan_id != "latest":
                    # Find specific plan
                    plan = None
                    for p in plans:
                        if p.plan_id == plan_id:
                            plan = p
                            break
                    if not plan:
                        self.notify(f"Plan '{plan_id}' not found", severity="error", timeout=3)
                        tui_log(f"  -> plan not found: {plan_id}")
                        return None
                else:
                    # Use latest plan
                    plan = plans[0]

                tui_log(f"  -> using plan: {plan.plan_id}")

                # Set the plan session on mode state (needed for workspace setup)
                self._mode_state.plan_session = plan

                # Load metadata to get the original planning prompt
                try:
                    metadata = plan.load_metadata()
                    original_question = getattr(metadata, "planning_prompt", None) or user_text or "Execute the plan"
                except Exception:
                    original_question = user_text or "Execute the plan"

                # If user provided additional instructions, append them
                if user_text:
                    execution_prompt = build_execution_prompt(f"{original_question}\n\nAdditional instructions: {user_text}")
                else:
                    execution_prompt = build_execution_prompt(original_question)

                tui_log(f"  -> execution_prompt: {execution_prompt[:100]}...")

                # Reset placeholder since we're leaving execute mode conceptually
                if hasattr(self, "question_input"):
                    self.question_input.placeholder = "Enter to submit • Shift+Enter for newline • @ for files • Ctrl+G help"

                self.notify("Executing plan...", severity="information", timeout=3)
                return execution_prompt

            except Exception as e:
                tui_log(f"_setup_plan_execution error: {e}")
                self.notify(f"Failed to set up plan execution: {e}", severity="error", timeout=3)
                return None

        def _handle_plan_mode_change(self, mode: str) -> None:
            """Handle plan mode toggle.

            Args:
                mode: "normal", "plan", or "execute".
            """
            tui_log(f"_handle_plan_mode_change: {mode}")

            if mode == "plan":
                self._mode_state.plan_mode = mode
                if self._mode_bar:
                    self._mode_bar.set_plan_mode(mode)
                self.notify("Plan Mode: ON - Submit query to create plan", severity="information", timeout=3)
            elif mode == "execute":
                # Entering execute mode - use helper which handles plan loading and popover
                # Note: The mode bar already shows "execute", but _enter_execute_mode
                # may revert to "plan" if no plans exist
                self._enter_execute_mode()
            elif mode == "normal":
                self._mode_state.reset_plan_state()
                if self._mode_bar:
                    self._mode_bar.set_plan_mode(mode)
                # Hide popover if visible
                if hasattr(self, "_plan_options_popover") and "visible" in self._plan_options_popover.classes:
                    self._plan_options_popover.hide()
                # Reset input placeholder
                if hasattr(self, "question_input"):
                    self.question_input.placeholder = "Enter to submit • Shift+Enter for newline • @ for files • Ctrl+G help"
                self.notify("Plan Mode: OFF", severity="information", timeout=2)

        def _handle_agent_mode_change(self, mode: str) -> None:
            """Handle agent mode toggle.

            Args:
                mode: "multi" or "single".
            """
            tui_log(f"_handle_agent_mode_change: {mode}")
            self._mode_state.agent_mode = mode

            if mode == "single":
                # Select the currently active agent as the single agent
                selected = self._active_agent_id or (self.coordination_display.agent_ids[0] if self.coordination_display.agent_ids else None)
                self._mode_state.selected_single_agent = selected
                if self._tab_bar and selected:
                    self._tab_bar.set_single_agent_mode(True, selected)
                # Update agent panels with "in use" state
                self._update_agent_panels_in_use_state(selected)
                self.notify(f"Single-Agent Mode: {selected}", severity="information", timeout=3)
            else:
                # Multi-agent mode
                self._mode_state.selected_single_agent = None
                if self._tab_bar:
                    self._tab_bar.set_single_agent_mode(False)
                # All panels are in use in multi-agent mode
                self._update_agent_panels_in_use_state(None)
                self.notify("Multi-Agent Mode", severity="information", timeout=2)

        def _update_agent_panels_in_use_state(self, selected_agent: Optional[str]) -> None:
            """Update the 'in use' state for all agent panels.

            Args:
                selected_agent: The selected agent ID in single-agent mode, or None for multi-agent mode.
            """
            if not hasattr(self, "agent_widgets"):
                return

            for agent_id, panel in self.agent_widgets.items():
                if hasattr(panel, "set_in_use"):
                    if selected_agent is None:
                        # Multi-agent mode: all panels in use
                        panel.set_in_use(True)
                    else:
                        # Single-agent mode: only selected panel in use
                        panel.set_in_use(agent_id == selected_agent)

        def _handle_refinement_mode_change(self, enabled: bool) -> None:
            """Handle refinement mode toggle.

            Args:
                enabled: True for refinement on, False for off.
            """
            tui_log(f"_handle_refinement_mode_change: {enabled}")
            self._mode_state.refinement_enabled = enabled

            if enabled:
                self.notify("Refinement: ON (normal voting)", severity="information", timeout=2)
            else:
                if self._mode_state.agent_mode == "single":
                    self.notify("Refinement: OFF (direct answer, no voting)", severity="warning", timeout=3)
                else:
                    self.notify("Refinement: OFF (vote after first answer)", severity="warning", timeout=3)

        @keyboard_action
        def action_toggle_plan_mode(self) -> None:
            """Toggle plan mode: normal → plan → execute → normal (Shift+Tab shortcut)."""
            tui_log("action_toggle_plan_mode")

            # Block during execution (keyboard_action decorator handles this,
            # but add explicit check with user message for clarity)
            if self._mode_state.is_locked():
                self.notify(
                    "Cannot change plan mode during execution. Wait for completion or cancel first.",
                    severity="warning",
                    timeout=3,
                )
                return

            if self._mode_state.plan_mode == "normal":
                # normal → plan
                self._mode_state.plan_mode = "plan"
                if self._mode_bar:
                    self._mode_bar.set_plan_mode("plan")
                self.notify("Plan Mode: ON - Submit query to create plan", severity="information", timeout=3)
            elif self._mode_state.plan_mode == "plan":
                # plan → execute (show plan selector if plans exist)
                self._enter_execute_mode()
            elif self._mode_state.plan_mode == "execute":
                # execute → normal
                self._mode_state.reset_plan_state()
                if self._mode_bar:
                    self._mode_bar.set_plan_mode("normal")
                # Hide popover if visible
                if hasattr(self, "_plan_options_popover") and "visible" in self._plan_options_popover.classes:
                    self._plan_options_popover.hide()
                # Reset input placeholder
                if hasattr(self, "question_input"):
                    self.question_input.placeholder = "Enter to submit • Shift+Enter for newline • @ for files • Ctrl+G help"
                self.notify("Plan Mode: OFF", severity="information", timeout=2)

        @keyboard_action
        def action_trigger_override(self) -> None:
            """Trigger human override of final answer selection (Ctrl+O shortcut)."""
            tui_log("action_trigger_override")

            if not self._mode_state.override_available:
                self.notify("Override not available (voting not complete)", severity="warning", timeout=2)
                return

            if not self._answers:
                self.notify("No answers to override", severity="warning", timeout=2)
                return

            # Show the answer browser modal for override selection
            # TODO: Create dedicated OverrideModal or enhance AnswerBrowserModal
            self.action_open_answer_browser()

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

        def on_task_plan_card_open_modal(self, event: TaskPlanCard.OpenModal) -> None:
            """Handle task plan card click - show task plan modal."""
            modal = TaskPlanModal(
                tasks=event.tasks,
                focused_task_id=event.focused_task_id,
            )
            self.push_screen(modal)
            event.stop()

        def on_subagent_card_open_modal(self, event: SubagentCard.OpenModal) -> None:
            """Handle subagent card click - show subagent modal with log streaming."""
            modal = SubagentModal(
                subagent=event.subagent,
                all_subagents=event.all_subagents,
            )
            self.push_screen(modal)
            event.stop()

        def on_tasks_clicked(self, event: TasksClicked) -> None:
            """Handle tasks label click in ribbon - show task plan modal."""
            if event.agent_id in self.agent_widgets:
                panel = self.agent_widgets[event.agent_id]
                if panel._active_task_plan_tasks:
                    modal = TaskPlanModal(tasks=panel._active_task_plan_tasks)
                    self.push_screen(modal)
            event.stop()

        def on_button_pressed(self, event: Button.Pressed) -> None:
            """Handle button clicks in main app."""
            if event.button.id == "cancel_button":
                # Trigger cancellation (same as Ctrl+C)
                self.coordination_display.request_cancellation()
                self.notify("Cancelling turn...", severity="warning", timeout=2)
                event.stop()

        def _handle_cancel(self) -> None:
            """Handle cancel action from button or 'q' key."""
            if hasattr(self.coordination_display, "orchestrator") and self.coordination_display.orchestrator:
                # Request cancellation from orchestrator
                self.notify("Cancellation requested...", severity="warning")
                # Set cancel flag if orchestrator supports it
                if hasattr(self.coordination_display.orchestrator, "cancel_requested"):
                    self.coordination_display.orchestrator.cancel_requested = True
            else:
                self.notify("Nothing to cancel", severity="information")

        def action_toggle_safe_keyboard(self):
            """Toggle safe keyboard mode to ignore hotkeys."""
            self.coordination_display.safe_keyboard_mode = not self.coordination_display.safe_keyboard_mode
            status = "ON" if self.coordination_display.safe_keyboard_mode else "OFF"
            self.add_orchestrator_event(f"Keyboard safe mode {status}")
            self._update_safe_indicator()

        def action_agent_selector(self):
            """Show agent selector."""
            self.show_agent_selector()

        def action_coordination_table(self):
            """Show coordination table."""
            self._show_coordination_table_modal()

        def action_quit(self):
            """Quit the application."""
            self.exit()

        def action_handle_ctrl_c(self) -> None:
            """Handle Ctrl+C: clear input / cancel turn, or quit if nothing to do."""
            # Check if input is focused and has content
            if hasattr(self, "question_input") and self.question_input.has_focus:
                if self.question_input.value:
                    # Clear input
                    self.question_input.value = ""
                    self.notify("Input cleared", timeout=1)
                    return

            # Check if there's an active turn to cancel
            has_active_turn = (
                hasattr(self.coordination_display, "_user_quit_requested")
                and not self.coordination_display._user_quit_requested
                and hasattr(self.coordination_display, "orchestrator")
                and self.coordination_display.orchestrator is not None
            )

            if has_active_turn:
                # Cancel the turn
                self.coordination_display.request_cancellation()
                self.notify("Cancelling turn...", severity="warning", timeout=2)
            else:
                # Nothing to cancel, input empty - quit
                self.exit()

        def action_toggle_cwd(self) -> None:
            """Toggle CWD auto-include (Ctrl+P binding)."""
            self._toggle_cwd_auto_include()

        def action_toggle_task_plan(self) -> None:
            """Toggle task plan visibility (Ctrl+T binding)."""
            if self._active_agent_id and self._active_agent_id in self.agent_widgets:
                self.agent_widgets[self._active_agent_id].toggle_task_plan()

        def action_toggle_theme(self) -> None:
            """Toggle between dark, light, and transparent themes (Ctrl+Shift+T binding)."""
            from textual.css.stylesheet import Stylesheet

            current = self.coordination_display.theme
            # Cycle: dark -> light -> transparent -> dark
            theme_cycle = {"dark": "light", "light": "transparent", "transparent": "dark"}
            new_theme = theme_cycle.get(current, "dark")

            # Load and apply new CSS
            css_path = self.THEMES_DIR / f"{new_theme}.tcss"
            if not css_path.exists():
                self.notify(f"Theme file not found: {css_path}", severity="error")
                return

            try:
                # Create a fresh stylesheet with the new CSS
                new_stylesheet = Stylesheet(variables=self.get_css_variables())
                new_stylesheet.read(css_path)
                new_stylesheet.parse()

                # Replace the app's stylesheet (this is what refresh_css uses)
                self.stylesheet = new_stylesheet

                # Update the theme state AFTER successfully loading CSS
                self.coordination_display.theme = new_theme

                # Now refresh_css will use the new stylesheet
                # It calls: stylesheet.set_variables(), reparse(), update()
                self.refresh_css(animate=False)

                # Force full repaint of all widgets
                self.refresh(repaint=True, layout=True)

                # Also refresh the screen
                if self.screen.is_mounted:
                    self.screen.refresh(repaint=True, layout=True)

            except Exception as e:
                self.notify(f"Theme error: {e}", severity="error", timeout=3)
                logger.exception(f"Failed to toggle theme: {e}")
                return

            # Update status bar indicator
            self._update_theme_indicator()
            self.notify(f"Theme: {new_theme.title()}", timeout=1.5)

        def action_show_help(self) -> None:
            """Show help modal (Ctrl+/ binding)."""
            self._show_help_modal()

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

        def action_open_system_status(self):
            """Open system status log."""
            self._show_system_status_modal()

        def action_open_orchestrator(self):
            """Open orchestrator events modal."""
            self._show_orchestrator_modal()

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

        def action_open_cost_breakdown(self):
            """Open cost breakdown modal."""
            self._show_cost_breakdown_modal()

        def action_open_metrics(self):
            """Open metrics modal."""
            self._show_metrics_modal()

        def action_show_shortcuts(self):
            """Show keyboard shortcuts modal."""
            self._show_modal_async(KeyboardShortcutsModal())

        def action_open_mcp_status(self):
            """Open MCP server status modal."""
            mcp_status = self._get_mcp_status()
            if not mcp_status["servers"]:
                self.notify("No MCP servers connected", severity="warning", timeout=3)
                return
            self._show_modal_async(MCPStatusModal(mcp_status))

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
                    restart_history=self._restart_history,
                ),
            )

        def action_open_workspace_browser(self):
            """Open workspace browser modal to view answer snapshots."""
            from pathlib import Path

            # Get current workspace paths for ALL agents
            agent_workspace_paths: Dict[str, str] = {}
            agent_final_paths: Dict[str, str] = {}
            orchestrator = getattr(self.coordination_display, "orchestrator", None)

            logger.info(f"[WorkspaceBrowser] orchestrator: {orchestrator is not None}")

            if orchestrator:
                # Get current workspaces
                for agent_id, agent in getattr(orchestrator, "agents", {}).items():
                    fm = getattr(getattr(agent, "backend", None), "filesystem_manager", None)
                    if fm:
                        workspace = getattr(fm, "get_current_workspace", lambda: None)()
                        if workspace:
                            agent_workspace_paths[agent_id] = str(workspace)

                # Scan for final workspaces in log directory
                log_dir = getattr(orchestrator, "log_session_dir", None)
                logger.info(f"[WorkspaceBrowser] log_dir: {log_dir}")

                if log_dir:
                    log_path = Path(log_dir)

                    def scan_for_final(base_dir: Path) -> Dict[str, str]:
                        found = {}
                        final_dir = base_dir / "final"
                        logger.info(f"[WorkspaceBrowser] Checking final_dir: {final_dir}, exists: {final_dir.exists()}")
                        if final_dir.exists() and final_dir.is_dir():
                            for agent_dir in final_dir.iterdir():
                                logger.info(f"[WorkspaceBrowser] Found agent_dir: {agent_dir.name}")
                                if agent_dir.is_dir() and agent_dir.name.startswith("agent_"):
                                    ws_path = agent_dir / "workspace"
                                    logger.info(f"[WorkspaceBrowser] ws_path: {ws_path}, exists: {ws_path.exists()}")
                                    if ws_path.exists():
                                        found[agent_dir.name] = str(ws_path)
                        return found

                    # Try direct final/ directory
                    agent_final_paths = scan_for_final(log_path)
                    logger.info(f"[WorkspaceBrowser] Direct scan result: {agent_final_paths}")

                    # If not found, try turn_*/attempt_* subdirectories
                    if not agent_final_paths:
                        for turn_dir in sorted(log_path.glob("turn_*"), reverse=True):
                            for attempt_dir in sorted(turn_dir.glob("attempt_*"), reverse=True):
                                logger.info(f"[WorkspaceBrowser] Checking attempt_dir: {attempt_dir}")
                                agent_final_paths = scan_for_final(attempt_dir)
                                if agent_final_paths:
                                    break
                            if agent_final_paths:
                                break

            logger.info(f"[WorkspaceBrowser] Final agent_final_paths: {agent_final_paths}")
            logger.info(f"[WorkspaceBrowser] agent_workspace_paths: {agent_workspace_paths}")

            # Allow opening even without answers if we have current or final workspace
            if not self._answers and not agent_workspace_paths and not agent_final_paths:
                self.notify("No answers yet - workspaces available after agents submit", severity="warning", timeout=3)
                return

            self._show_modal_async(
                WorkspaceBrowserModal(
                    answers=self._answers,
                    agent_ids=self.coordination_display.agent_ids,
                    agent_workspace_paths=agent_workspace_paths,
                    agent_final_paths=agent_final_paths,
                ),
            )

        def _show_workspace_browser_for_agent(self, agent_id: str):
            """Open workspace browser focused on the winning agent's final workspace.

            Args:
                agent_id: The agent ID to show workspace for (typically the winner)
            """
            from pathlib import Path

            # Get current workspace paths for ALL agents
            agent_workspace_paths: Dict[str, str] = {}
            final_workspace_paths: Dict[str, str] = {}
            orchestrator = getattr(self.coordination_display, "orchestrator", None)

            if orchestrator:
                # Get current workspaces
                for aid, agent in getattr(orchestrator, "agents", {}).items():
                    fm = getattr(getattr(agent, "backend", None), "filesystem_manager", None)
                    if fm:
                        workspace = getattr(fm, "get_current_workspace", lambda: None)()
                        if workspace:
                            agent_workspace_paths[aid] = str(workspace)

                # Scan for final workspaces in log directory
                log_dir = getattr(orchestrator, "log_session_dir", None)
                if log_dir:
                    log_path = Path(log_dir)

                    def scan_for_final(base_dir: Path) -> Dict[str, str]:
                        found = {}
                        final_dir = base_dir / "final"
                        if final_dir.exists() and final_dir.is_dir():
                            for agent_dir in final_dir.iterdir():
                                if agent_dir.is_dir() and agent_dir.name.startswith("agent_"):
                                    ws_path = agent_dir / "workspace"
                                    if ws_path.exists():
                                        found[agent_dir.name] = str(ws_path)
                        return found

                    # Try direct final/ directory
                    final_workspace_paths = scan_for_final(log_path)

                    # If not found, try turn_*/attempt_* subdirectories
                    if not final_workspace_paths:
                        for turn_dir in sorted(log_path.glob("turn_*"), reverse=True):
                            for attempt_dir in sorted(turn_dir.glob("attempt_*"), reverse=True):
                                final_workspace_paths = scan_for_final(attempt_dir)
                                if final_workspace_paths:
                                    break
                            if final_workspace_paths:
                                break

            # Merge final workspaces into agent_workspace_paths with special key
            # The modal will detect keys ending with "-final" as final workspaces
            agent_final_paths: Dict[str, str] = {}
            for aid, path in final_workspace_paths.items():
                agent_final_paths[aid] = path

            if not self._answers and not agent_workspace_paths and not agent_final_paths:
                self.notify("No workspace available yet", severity="warning", timeout=3)
                return

            self._show_modal_async(
                WorkspaceBrowserModal(
                    answers=self._answers,
                    agent_ids=self.coordination_display.agent_ids,
                    agent_workspace_paths=agent_workspace_paths,
                    agent_final_paths=agent_final_paths,
                    default_agent=agent_id,
                    default_to_final=True,
                ),
            )

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

        def on_status_bar_cwd_clicked(self, event: StatusBarCwdClicked) -> None:
            """Handle CWD mode change from status bar click."""
            self._cwd_context_mode = event.mode
            # No toast - the visual update in the hint/status bar is enough

        def on_status_bar_theme_clicked(self, event: StatusBarThemeClicked) -> None:
            """Handle theme toggle from status bar click."""
            self.action_toggle_theme()

        def _toggle_cwd_auto_include(self) -> None:
            """Cycle CWD context mode: off → read → write → off (Ctrl+P)."""
            # Cycle through modes
            modes = ["off", "read", "write"]
            current_idx = modes.index(self._cwd_context_mode)
            self._cwd_context_mode = modes[(current_idx + 1) % len(modes)]

            cwd = Path.cwd()
            cwd_short = f"~/{cwd.name}" if len(str(cwd)) > 30 else str(cwd)

            # Update status bar display if available
            if self._status_bar:
                self._status_bar._cwd_context_mode = self._cwd_context_mode
                try:
                    cwd_widget = self._status_bar.query_one("#status_cwd", Static)
                    if self._cwd_context_mode == "read":
                        cwd_widget.update(f"[green]📁 {cwd_short} \\[read][/]")
                    elif self._cwd_context_mode == "write":
                        cwd_widget.update(f"[green]📁 {cwd_short} \\[read+write][/]")
                    else:
                        cwd_widget.update(f"[dim]📁[/] {cwd_short}")
                except Exception:
                    pass

            # Update welcome screen hint if showing
            self._update_cwd_hint()

        def _update_cwd_hint(self) -> None:
            """Update the CWD hint display on welcome screen."""
            try:
                cwd = Path.cwd()
                cwd_short = f"~/{cwd.name}" if len(str(cwd)) > 30 else str(cwd)
                hint_widget = self.query_one("#cwd_hint", Static)
                at_hint = "  •  @ for other paths"
                if self._cwd_context_mode == "read":
                    hint_widget.update(f"[green]● Ctrl+P: File access to {cwd_short} \\[r][/][dim]{at_hint}[/]")
                elif self._cwd_context_mode == "write":
                    hint_widget.update(f"[green]● Ctrl+P: File access to {cwd_short} \\[rw][/][dim]{at_hint}[/]")
                else:
                    hint_widget.update(f"[dim]○ Ctrl+P: File access to {cwd_short}{at_hint}[/]")
            except Exception:
                pass

        def _update_status_bar_restart_info(self) -> None:
            """Update StatusBar to show restart count."""
            if not self._status_bar or not self._current_restart:
                return
            try:
                # Show restart info in the progress area
                attempt = self._current_restart.get("attempt", 1)
                max_attempts = self._current_restart.get("max_attempts", 3)
                self._status_bar.show_restart_count(attempt, max_attempts)
            except Exception:
                pass

        # === Status Bar Notification Methods ===

        def notify_vote(self, voter: str, voted_for: str, reason: str = "") -> None:
            """Called when a vote is cast. Updates status bar, shows toast, and adds tool card."""
            import time
            from datetime import datetime

            from .content_handlers import ToolDisplayData

            # Get model names for richer display
            voter_model = self.coordination_display.agent_models.get(voter, "")
            voted_for_model = self.coordination_display.agent_models.get(voted_for, "")

            # Get voted-for answer label from coordination tracker (for swimlane display)
            voted_for_label = None
            tracker = None
            if hasattr(self.coordination_display, "orchestrator") and self.coordination_display.orchestrator:
                tracker = getattr(self.coordination_display.orchestrator, "coordination_tracker", None)
            if tracker:
                voted_for_label = tracker.get_voted_for_label(voter, voted_for)

            # Track the vote for browser
            vote_count = len(self._votes) + 1
            self._votes.append(
                {
                    "voter": voter,
                    "voter_model": voter_model,
                    "voted_for": voted_for,
                    "voted_for_model": voted_for_model,
                    "voted_for_label": voted_for_label,  # Answer label like "1.2" for swimlane display
                    "reason": reason,
                    "timestamp": time.time(),
                },
            )

            if self._status_bar:
                self._status_bar.add_vote(voted_for, voter)
                standings = self._status_bar.get_standings_text()

                # Update progress summary
                agent_count = len(self.coordination_display.agent_ids)
                answer_count = len(self._answers)
                # Expected votes = agents * (agents - 1) in typical voting round
                expected_votes = agent_count * (agent_count - 1) if agent_count > 1 else 0
                self._status_bar.update_progress(agent_count, answer_count, vote_count, expected_votes)

                # Enhanced toast with model info - explicitly say "voted for"
                voter_display = f"{voter}" + (f" ({voter_model})" if voter_model else "")
                target_display = f"{voted_for}" + (f" ({voted_for_model})" if voted_for_model else "")

                if standings:
                    self.notify(
                        f"🗳️ [bold]{voter_display}[/] voted for [bold cyan]{target_display}[/]\n📊 {standings}",
                        timeout=4,
                    )
                else:
                    self.notify(
                        f"🗳️ [bold]{voter_display}[/] voted for [bold cyan]{target_display}[/]",
                        timeout=3,
                    )
            else:
                self.notify(f"🗳️ {voter} voted for {voted_for}", timeout=3)

            # Add vote tool card to the voter's timeline
            if voter in self.agent_widgets:
                panel = self.agent_widgets[voter]
                try:
                    timeline = panel.query_one(f"#{panel._timeline_section_id}", TimelineSection)

                    # Truncate reason for card display
                    reason_preview = reason[:80] + "..." if len(reason) > 80 else reason
                    reason_preview = reason_preview.replace("\n", " ")

                    now = datetime.now()
                    tool_id = f"vote_{voter}_{vote_count}"
                    tool_data = ToolDisplayData(
                        tool_id=tool_id,
                        tool_name="workspace/vote",
                        display_name="Workspace/Vote",
                        tool_type="workspace",
                        category="workspace",
                        icon="🗳️",
                        color="#a371f7",  # Purple for voting
                        status="success",
                        start_time=now,
                        end_time=now,
                        args_summary=f'voted_for="{voted_for}"',
                        args_full=f'voted_for="{voted_for}", reason="{reason}"',
                        result_summary=f"Voted for {voted_for}",
                        result_full=f"Voted for {voted_for}\nReason: {reason}" if reason else f"Voted for {voted_for}",
                        elapsed_seconds=0.0,
                    )

                    # Add tool card to timeline and mark as success immediately
                    # Phase 12: Pass round_number for CSS visibility
                    current_round = panel._current_round
                    timeline.add_tool(tool_data, round_number=current_round)
                    tool_data.status = "success"
                    timeline.update_tool(tool_id, tool_data)

                    # Add "VOTED" separator banner with answer labels
                    # Get coordination_tracker to resolve answer labels
                    tracker = None
                    if hasattr(self.coordination_display, "orchestrator") and self.coordination_display.orchestrator:
                        tracker = getattr(self.coordination_display.orchestrator, "coordination_tracker", None)

                    if tracker:
                        # Get voted-for answer label from voter's context
                        target_label = tracker.get_voted_for_label(voter, voted_for)

                        if target_label:
                            # Convert from "agent1.1" format to "A1.1" format
                            target_label.replace("agent", "A")
                        else:
                            # Fallback to agent number if label not available
                            target_num = tracker._get_agent_number(voted_for)
                            f"A{target_num}" if target_num else voted_for

                        # NOTE: Vote separator banner disabled - clutters UI
                        # sep_label = f"🗳️ VOTED → {target_short}"
                        # timeline.add_separator(sep_label, round_number=current_round)
                except Exception:
                    pass  # Silently ignore if panel not found

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
                # Increment per-agent answer count
                self._status_bar.increment_agent_answer(agent_id)

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
                    # Phase 12: Pass round_number for CSS visibility
                    timeline.add_tool(tool_data, round_number=panel._current_round)
                    # Mark as success immediately
                    tool_data.status = "success"
                    timeline.update_tool(tool_id, tool_data)

                    # Phase 12: No inline separator - view dropdown handles round navigation
                    # The round will change when orchestrator calls _add_restart_content

                    # Reset per-round state (badges) now that answer is submitted
                    # The background shells will be killed by orchestrator when new round starts
                    panel._reset_round_state()
                except Exception as e:
                    import sys
                    import traceback

                    print(f"[ERROR] Failed to add workspace/new_answer card: {e}", file=sys.stderr)
                    traceback.print_exc()

        def update_agent_context(self, agent_id: str, context_sources: List[str]) -> None:
            """Update agent panel to show what context this agent has received.

            Called when an agent receives context from other agents' answers.

            Args:
                agent_id: Agent receiving context
                context_sources: List of answer labels this agent can see
            """
            # Store context for this agent
            self._context_per_agent[agent_id] = context_sources.copy()

            # Update agent panel header to show context
            if agent_id in self.agent_widgets:
                panel = self.agent_widgets[agent_id]
                panel.update_context_display(context_sources)

        def record_answer_context(
            self,
            agent_id: str,
            answer_label: str,
            context_sources: List[str],
            round_num: int,
        ) -> None:
            """Record context sources for an answer and update agent panel display.

            Args:
                agent_id: Agent who submitted the answer
                answer_label: Label like "agent1.1"
                context_sources: List of answer labels this agent saw (e.g., ["agent2.1"])
                round_num: Round number for this answer
            """
            # Store context for this agent (already done by update_agent_context, but ensure consistency)
            self._context_per_agent[agent_id] = context_sources.copy()

            # Update the answer record if it exists
            for ans in self._answers:
                if ans.get("answer_label") == answer_label:
                    ans["context_sources"] = context_sources.copy()
                    break

            # Update agent panel header to show context
            if agent_id in self.agent_widgets:
                panel = self.agent_widgets[agent_id]
                panel.update_context_display(context_sources)

                # If this is a new round for this panel, start the new round
                if round_num > panel._current_round:
                    panel.start_new_round(round_num, is_context_reset=False)

            # Update status ribbon with round number
            if self._status_ribbon:
                self._status_ribbon.set_round(agent_id, round_num)

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
            """Called on phase change. Updates status bar phase indicator and input area mode."""
            tui_log(f"notify_phase called with phase='{phase}'")
            if self._status_bar:
                self._status_bar.update_phase(phase)

            # Toggle execution mode on input area based on phase
            try:
                input_area = self.query_one("#input_area")
                if phase in ("idle", "presentation", "presenting"):
                    # Not executing - show normal input
                    tui_log(f"  Phase '{phase}' -> removing execution-mode class")
                    input_area.remove_class("execution-mode")
                    # Stop execution status update timer
                    if hasattr(self, "_execution_status_timer") and self._execution_status_timer:
                        self._execution_status_timer.stop()
                        self._execution_status_timer = None

                    # If there's queued input that wasn't injected, submit it as a new turn
                    if self._queued_human_input:
                        pending_input = self._queued_human_input
                        self._clear_queued_input()
                        # Clear hook's pending input too
                        if self._human_input_hook:
                            self._human_input_hook.clear_pending_input()
                        tui_log(f"[HumanInput] Turn ended with queued input, submitting as new turn: {pending_input[:50]}...")
                        # Submit as new question (use set_timer to avoid recursion issues)
                        self.set_timer(0.1, lambda: self._submit_question(pending_input))
                else:
                    # Executing (initial_answer, enforcement, coordinating) - show status
                    tui_log(f"  Phase '{phase}' -> adding execution-mode class")
                    input_area.add_class("execution-mode")
                    # Start timer to periodically update execution status (for spinner animation)
                    if not hasattr(self, "_execution_status_timer") or not self._execution_status_timer:
                        self._execution_status_timer = self.set_interval(0.1, self._update_execution_status)
                tui_log(f"  input_area classes after: {input_area.classes}")
            except Exception as e:
                tui_log(f"  Exception toggling execution-mode: {e}")

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

            # Also update execution status line with vote info
            self._update_execution_status(vote_counts=vote_counts)

        def _update_execution_status(self, vote_counts: Dict[str, int] | None = None) -> None:
            """Update the execution status line with per-agent progress and activity.

            Format: A: 2 ans, 3 votes 💭  |  B: 1 ans, 2 votes 🔧  |  ⏱ 16s
            """
            try:
                if hasattr(self, "_execution_status"):
                    # Build status text
                    parts = []

                    # Add per-agent stats from status bar
                    if hasattr(self, "_status_bar") and self._status_bar:
                        ACTIVITY_ICONS = {
                            "idle": "○",
                            "thinking": "💭",
                            "tool": "🔧",
                            "streaming": "✍️",
                            "voting": "🗳️",
                            "waiting": "⏳",
                            "error": "⚠️",
                        }
                        SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
                        spinner = SPINNER_FRAMES[self._status_bar._spinner_frame]

                        agent_parts = []
                        for agent_id in self._status_bar._agent_order:
                            letter = self._status_bar._agent_letters.get(agent_id, "?")
                            activity = self._status_bar._agent_activities.get(agent_id, "idle")
                            icon = ACTIVITY_ICONS.get(activity, "○")
                            answers = self._status_bar._agent_answer_counts.get(agent_id, 0)
                            votes = self._status_bar._agent_votes_received.get(agent_id, 0)

                            # Build agent status string with spaces
                            stats_parts = []
                            if answers > 0:
                                stats_parts.append(f"{answers} ans")
                            if votes > 0:
                                stats_parts.append(f"{votes} votes")
                            stats = ", ".join(stats_parts) if stats_parts else ""

                            # Format: "A: 2 ans, 3 votes 💭" or "A: 💭" if no stats yet
                            if activity == "idle":
                                if stats:
                                    agent_parts.append(f"{letter}: {stats}  {icon}")
                                else:
                                    agent_parts.append(f"{letter}: {icon}")
                            else:
                                if stats:
                                    agent_parts.append(f"{letter}: {stats}  {spinner} {icon}")
                                else:
                                    agent_parts.append(f"{letter}: {spinner} {icon}")

                        if agent_parts:
                            parts.append("  |  ".join(agent_parts))
                        else:
                            parts.append("Working...")
                    else:
                        parts.append("Working...")

                    # Add elapsed time
                    if hasattr(self, "_status_bar") and self._status_bar and hasattr(self._status_bar, "_start_time"):
                        start_time = self._status_bar._start_time
                        if start_time:
                            elapsed = time.time() - start_time
                            mins = int(elapsed // 60)
                            secs = int(elapsed % 60)
                            if mins > 0:
                                parts.append(f"⏱ {mins}m {secs}s")
                            else:
                                parts.append(f"⏱ {secs}s")

                    self._execution_status.update("  |  ".join(parts))
            except Exception:
                pass

        def _show_cancelled_status(self) -> None:
            """Stop execution status updates and show cancelled state with PERSISTENT visual feedback.

            The cancelled state persists until the user submits a new question, making it
            clear that the system is waiting for input rather than auto-dismissing.
            """
            try:
                # Stop the execution status timer
                if hasattr(self, "_execution_status_timer") and self._execution_status_timer:
                    self._execution_status_timer.stop()
                    self._execution_status_timer = None

                # Set all agents to idle in status bar
                if hasattr(self, "_status_bar") and self._status_bar:
                    for agent_id in self._status_bar._agent_order:
                        self._status_bar.set_agent_activity(agent_id, "idle")

                # Update ExecutionStatusLine to show cancelled state
                if hasattr(self, "_execution_status_line") and self._execution_status_line:
                    for agent_id in self._execution_status_line._agent_ids:
                        self._execution_status_line.set_agent_state(agent_id, "cancelled")

                # Stop all pulsing animations
                self._stop_all_pulses()

                # Stop round timers in ribbon
                if hasattr(self, "_status_ribbon") and self._status_ribbon:
                    self._status_ribbon.stop_all_round_timers()

                # Mark cancelled state in mode tracker (persists until new input)
                if hasattr(self.coordination_display, "_mode_state"):
                    self.coordination_display._mode_state.was_cancelled = True

                # Update execution status to show cancelled
                if hasattr(self, "_execution_status"):
                    # Get elapsed time for final display
                    elapsed_text = ""
                    if hasattr(self, "_status_bar") and self._status_bar and hasattr(self._status_bar, "_start_time"):
                        start_time = self._status_bar._start_time
                        if start_time:
                            elapsed = time.time() - start_time
                            mins = int(elapsed // 60)
                            secs = int(elapsed % 60)
                            if mins > 0:
                                elapsed_text = f"  |  ⏱ {mins}m {secs}s"
                            else:
                                elapsed_text = f"  |  ⏱ {secs}s"

                    self._execution_status.update(f"❌ Cancelled{elapsed_text}")

                # Add PERSISTENT visual state change - red tint on main container
                # This persists until user submits a new question
                try:
                    main = self.query_one("#main_container")
                    main.add_class("cancelled-state")

                    # Update placeholder to indicate waiting for input
                    if hasattr(self, "question_input"):
                        self.question_input.placeholder = "Type to continue • Previous turn was cancelled"

                    # Show notification (brief)
                    self.notify("Execution cancelled - type to continue", severity="warning", timeout=3)

                    # NO auto-dismiss timer - state persists until user provides new input
                except Exception:
                    pass
            except Exception:
                pass

        def _clear_cancelled_state(self) -> None:
            """Clear the persistent cancelled state when user starts a new turn."""
            try:
                # Clear mode state flag
                if hasattr(self.coordination_display, "_mode_state"):
                    self.coordination_display._mode_state.reset_cancelled_state()

                # Remove visual cancelled state
                try:
                    main = self.query_one("#main_container")
                    main.remove_class("cancelled-state")
                except Exception:
                    pass

                # Restore default placeholder
                if hasattr(self, "question_input"):
                    self.question_input.placeholder = "Enter to submit • Shift+Enter for newline • @ for files • Ctrl+G help"
            except Exception:
                pass

        # =====================================================================
        # Agent Pulsing Animation
        # =====================================================================

        _PULSE_FRAMES = ["pulse-bright", "pulse-bright", "pulse-normal", "pulse-normal"]

        def _start_agent_pulse(self, agent_id: str) -> None:
            """Start pulsing animation for an active agent.

            NOTE: Pulsing animation disabled - was too distracting.
            Left as no-op to avoid breaking callers.
            """
            return  # Pulsing disabled

            self._pulsing_agents.add(agent_id)
            logger.info(f"[PULSE] Added {agent_id} to pulsing_agents: {self._pulsing_agents}")

            # Start the timer if not already running
            if not self._pulse_timer:
                self._pulse_frame = 0
                self._pulse_timer = self.set_interval(0.25, self._animate_agent_pulse)
                logger.info("[PULSE] Started pulse timer")

        def _stop_agent_pulse(self, agent_id: str) -> None:
            """Stop pulsing animation for an agent."""
            if agent_id not in self._pulsing_agents:
                return

            self._pulsing_agents.discard(agent_id)

            # Remove pulse classes from the panel
            try:
                panel = self.agent_widgets.get(agent_id)
                if panel:
                    panel.remove_class("pulse-bright", "pulse-normal")
            except Exception:
                pass

            # Stop the timer if no agents are pulsing
            if not self._pulsing_agents and self._pulse_timer:
                self._pulse_timer.stop()
                self._pulse_timer = None

        def _stop_all_pulses(self) -> None:
            """Stop all agent pulsing animations."""
            for agent_id in list(self._pulsing_agents):
                self._stop_agent_pulse(agent_id)

        def _animate_agent_pulse(self) -> None:
            """Animate the pulsing effect on active agent panels."""
            from massgen.logger_config import logger

            if not self._pulsing_agents:
                return

            # Advance frame
            self._pulse_frame = (self._pulse_frame + 1) % len(self._PULSE_FRAMES)
            frame_class = self._PULSE_FRAMES[self._pulse_frame]
            prev_frame_class = self._PULSE_FRAMES[(self._pulse_frame - 1) % len(self._PULSE_FRAMES)]

            for agent_id in self._pulsing_agents:
                try:
                    panel = self.agent_widgets.get(agent_id)
                    if panel:
                        # Remove previous frame class, add current
                        if prev_frame_class != frame_class:
                            panel.remove_class(prev_frame_class)
                        panel.add_class(frame_class)
                        logger.debug(f"[PULSE] Applied {frame_class} to {agent_id}, classes={panel.classes}")
                    else:
                        logger.warning(f"[PULSE] Panel not found for {agent_id}, available: {list(self.agent_widgets.keys())}")
                except Exception as e:
                    logger.error(f"[PULSE] Error animating {agent_id}: {e}")

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

            Note: Info shortcuts always work - they're read-only views.
            No need to check keyboard lock since none of these change modes.
            """
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

            # q - Exit scroll mode and go to bottom
            if key_lower == "q":
                self._exit_scroll_mode()
                event.stop()
                return True

            # s - System status
            if key_lower == "s":
                self.action_open_system_status()
                event.stop()
                return True

            # o - Full agent output (repurposed from orchestrator events)
            if key_lower == "o":
                self.action_open_agent_output()
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

            # f - Removed (merged into 'w' workspace browser)

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

            # t - Timeline/Browser (unified tabbed view)
            if key_lower == "t":
                self.action_open_unified_browser()
                event.stop()
                return True

            # ? - Help/shortcuts
            if key == "?":
                self.action_show_shortcuts()
                event.stop()
                return True

            # D - Dump widget sizes for debugging
            if key == "D":
                self._dump_widget_sizes()
                self.notify("Widget sizes dumped to /tmp/widget_sizes.json", severity="information")
                event.stop()
                return True

            # h - History
            if key_lower == "h":
                self._show_history_modal()
                event.stop()
                return True

            # i or / - Focus input (vim-like insert mode or search)
            if key_lower == "i" or key == "/":
                if hasattr(self, "question_input") and self.question_input:
                    self.question_input.focus()
                    event.stop()
                    return True

            # Escape when not in input - show hint or exit scroll mode
            if event.key == "escape":
                # If in scroll mode, exit it
                if self._in_scroll_mode():
                    self._exit_scroll_mode()
                    event.stop()
                    return True
                self.notify("Already in command mode. Press i or / to type.", severity="information", timeout=2)
                event.stop()
                return True

            return False

        def _in_scroll_mode(self) -> bool:
            """Check if any timeline is in scroll mode."""
            try:
                for timeline in self.query(TimelineSection):
                    if timeline.in_scroll_mode:
                        return True
            except Exception:
                pass
            return False

        def _exit_scroll_mode(self) -> None:
            """Exit scroll mode on all timelines and scroll to bottom."""
            exited = False
            try:
                for timeline in self.query(TimelineSection):
                    if timeline.in_scroll_mode:
                        timeline.exit_scroll_mode()
                        exited = True
            except Exception:
                pass
            if exited:
                self.notify("Resumed auto-scroll", severity="information", timeout=1)

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
            """Display workspace files in a modal (uses WorkspaceBrowserModal)."""
            self._show_workspace_browser()

        def _show_context_modal(self):
            """Display context paths modal."""
            self._show_modal_async(ContextModal(self.coordination_display, self))

        def _show_metrics_modal(self):
            """Display tool metrics in a modal."""
            self._show_modal_async(MetricsModal(self.coordination_display))

        def _show_history_modal(self):
            """Display conversation history in a modal."""
            self._show_modal_async(
                ConversationHistoryModal(
                    self._conversation_history,
                    self._current_question,
                    self.coordination_display.agent_ids,
                ),
            )

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
                    # Model is stored on backend.model, not directly on agent
                    backend = getattr(agent, "backend", None)
                    if backend:
                        model_name = getattr(backend, "model", None)
                    # Fallback to agent-level attributes
                    if not model_name:
                        model_name = getattr(agent, "model", None) or getattr(agent, "model_name", None)
            # Get all agents for toggle functionality
            all_agents = {}
            if orchestrator:
                for aid, agent in getattr(orchestrator, "agents", {}).items():
                    agent_model = None
                    backend = getattr(agent, "backend", None)
                    if backend:
                        agent_model = getattr(backend, "model", None)
                    all_agents[aid] = {
                        "outputs": self.coordination_display.get_agent_content(aid),
                        "model": agent_model,
                    }
            self._show_modal_async(AgentOutputModal(agent_id, agent_outputs, model_name, all_agents, self._current_question))

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
            yield Label("Multi-Agent Collaboration System", id="welcome_tagline")
            # Show agent list
            if self.agents_info:
                agents_list = "  •  ".join(self.agents_info)
                yield Label(agents_list, id="welcome_agents")
            else:
                yield Label(f"Ready with {len(self.agents_info)} agents", id="welcome_agents")
            yield Label("Type your question below to begin...", id="welcome_hint")
            # CWD context hint - shows current mode, explains what it does
            cwd = Path.cwd()
            cwd_short = f"~/{cwd.name}" if len(str(cwd)) > 30 else str(cwd)
            # Use fixed-width format: ○/● indicator + consistent text
            yield Static(f"[dim]Ctrl+P file access to {cwd_short}  •  @ for other paths[/]", id="cwd_hint")
            yield Static("[dim]Ctrl+G help  •  Ctrl+C quit[/]", id="shortcuts_hint")

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
            # Set initial content
            self.update(self._build_status_line())

        def _build_status_line(self) -> str:
            """Build compact status line with optional question preview."""
            num_agents = len(self.agents_info)
            base = f"MassGen • {num_agents} agents • Turn {self.turn}"

            # Add truncated question if available
            if self.question and self.question != "Welcome! Type your question below...":
                # Truncate question to fit in header (max ~100 chars for better visibility)
                q = self.question.replace("\n", " ").strip()
                q = q[:100] + "..." if len(q) > 100 else q
                return f"{base} • {q}"
            return base

        def update_question(self, question: str) -> None:
            """Update the displayed question and refresh header."""
            self.question = question
            self.update(self._build_status_line())

        def update_turn(self, turn: int) -> None:
            """Update the displayed turn number."""
            self.turn = turn
            self.update(self._build_status_line())

        def show_restart_banner(
            self,
            reason: str,
            instructions: str,
            attempt: int,
            max_attempts: int,
        ):
            """Show restart banner."""
            banner_text = f"RESTART ({attempt}/{max_attempts}): {reason}"
            self.update(banner_text)

        def show_restart_context(self, reason: str, instructions: str):
            """Show restart context - handled via status line."""
            pass  # Restart info shown via show_restart_banner  # Restart info shown via show_restart_banner

    class AgentPanel(Container):
        """Panel for individual agent output.

        Note: This is a Container, not ScrollableContainer. Scrolling happens
        in the inner TimelineSection widget which inherits from ScrollableContainer.
        """

        def __init__(self, agent_id: str, display: TextualTerminalDisplay, key_index: int = 0):
            self.agent_id = agent_id
            self.coordination_display = display
            self.key_index = key_index
            self._dom_safe_id = self._make_dom_safe_id(agent_id)
            # Assign color class based on key_index (cycles through 8 colors)
            color_class = f"agent-color-{((key_index - 1) % 8) + 1}" if key_index > 0 else "agent-color-1"
            super().__init__(id=f"agent_{self._dom_safe_id}", classes=color_class)
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
            self._not_in_use_id = f"not_in_use_{self._dom_safe_id}"
            self._is_in_use = True  # Track if panel is active in single-agent mode

            # New section-based content handlers
            self._tool_handler = ToolContentHandler()
            self._thinking_handler = ThinkingContentHandler()
            self._batch_tracker = ToolBatchTracker()

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

            # Context tracking (per-round for view switching)
            self._context_sources: List[str] = []
            self._context_by_round: Dict[int, List[str]] = {}  # round_num -> context_sources
            self._context_label_id = f"context_{self._dom_safe_id}"

            # Timer for updating elapsed time display
            self._header_timer = None

            # Timeout state tracking (for per-agent timeout display)
            self._timeout_state: Optional[Dict[str, Any]] = None

            # Task plan tracking for toggle feature
            self._active_task_plan_id: Optional[str] = None
            self._active_task_plan_tasks: Optional[List[Dict[str, Any]]] = None
            self._task_plan_visible: bool = False
            self._task_plan_toggle_id = f"task_plan_toggle_{self._dom_safe_id}"
            self._task_plan_display_id = f"task_plan_display_{self._dom_safe_id}"

            # Phase 12: CSS-based round navigation (no storage needed - widgets stay in DOM)
            self._current_round: int = 1  # which round content is being received
            self._current_view: str = "round"  # "round" or "final_answer"
            self._viewed_round: int = 1  # which round is currently displayed

            # Final answer storage
            self._final_answer_content: Optional[str] = None
            self._final_answer_metadata: Optional[Dict[str, Any]] = None

            # Terminal tool transition tracking (new_answer, vote)
            # When a terminal tool completes, we delay round transitions so users can see the action
            self._last_tool_was_terminal: bool = False
            self._transition_pending: bool = False
            self._transition_timer: Optional[Any] = None
            self._pending_round_transition: Optional[Tuple[int, bool]] = None  # (round_num, is_context_reset)

            # Final presentation tracking
            # When True, content flows through the normal pipeline but is tagged as final presentation
            self._is_final_presentation_round: bool = False

        def reset_round_state(self) -> None:
            """Reset round tracking state for a new turn."""
            from massgen.logger_config import logger

            logger.info(f"[AgentPanel] reset_round_state() called for agent {self.agent_id}")
            logger.info(f"[AgentPanel] Before reset: _current_round={self._current_round}, _viewed_round={self._viewed_round}")

            self._current_round = 1
            self._viewed_round = 1
            self._context_by_round.clear()
            self._is_final_presentation_round = False
            self._final_answer_content = None
            self._final_answer_metadata = None

            logger.info(f"[AgentPanel] After reset: _current_round={self._current_round}, _viewed_round={self._viewed_round}")

            # Reset round state in child widgets
            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)
                logger.info("[AgentPanel] Found timeline widget, calling timeline.reset_round_state()")
                timeline.reset_round_state()
                logger.info(f"[AgentPanel] Timeline reset complete: _viewed_round={timeline._viewed_round}, _round_1_shown={timeline._round_1_shown}")
            except Exception as e:
                logger.warning(f"Failed to reset timeline round state for {self.agent_id}: {e}")

            # NOTE: Don't reset ribbon here - it's at app level, not inside panel
            # The ribbon is reset directly in update_turn_header() via self._status_ribbon.reset_round_state_all_agents()
            logger.info("[AgentPanel] Skipping ribbon reset (handled at app level)")

        def compose(self) -> ComposeResult:
            with Vertical():
                # NOTE: Agent header row removed in Phase 8c/10 - redundant with tab bar + status ribbon
                # Agent ID shown in tabs, round number shown in ribbon
                # Background tasks can be viewed via tool cards in timeline

                # Context sources label (hidden by default, shown when context is injected)
                yield Label(
                    "",
                    id=self._context_label_id,
                    classes="context-label hidden",
                )

                # Loading indicator - centered, shown when waiting with no content
                with Container(id=self._loading_id, classes="loading-container"):
                    yield ProgressIndicator(
                        message="Ready",
                        id=f"progress_{self._dom_safe_id}",
                    )

                # "Not in use" overlay - shown for inactive agents in single-agent mode
                with Container(id=self._not_in_use_id, classes="not-in-use-overlay hidden"):
                    yield Label("👤 Not in use", classes="not-in-use-label")
                    yield Label("Single-agent mode active", classes="not-in-use-sublabel")

                # Pinned task plan - stays at top, collapsible (hidden until task plan created)
                self._pinned_task_plan_id = f"pinned_task_plan_{self._dom_safe_id}"
                yield Container(id=self._pinned_task_plan_id, classes="pinned-task-plan hidden")

                # Chronological timeline layout - tools and text interleaved
                yield TimelineSection(id=self._timeline_section_id)

                # Final Answer view (hidden by default, shown via view dropdown)
                from .textual_widgets import FinalAnswerView

                self._final_answer_view_id = f"final_answer_view_{self._dom_safe_id}"
                yield FinalAnswerView(
                    agent_id=self.agent_id,
                    id=self._final_answer_view_id,
                )

                yield CompletionFooter(id=self._completion_footer_id)

                # Legacy RichLog kept for fallback/compatibility
                yield self.content_log
                yield self.current_line_label

        # NOTE: on_click handler removed in Phase 8c/10 - header badges no longer exist
        # Background tasks can be viewed via tool cards in timeline
        # Task plan is shown in collapsible TaskPlanCard

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
            self._start_loading_spinner("Ready")

            # Note: Round 1 banner is added by TimelineSection.on_mount

            # Initialize ribbon with Round 1 so the dropdown shows it immediately
            try:
                app = self.app
                if hasattr(app, "_status_ribbon") and app._status_ribbon:
                    app._status_ribbon.set_round(self.agent_id, 1, False)
                    logger.debug(f"AgentPanel.on_mount: Initialized ribbon with Round 1 for {self.agent_id}")
            except Exception as e:
                logger.debug(f"AgentPanel.on_mount: Failed to initialize ribbon: {e}")

        def set_in_use(self, in_use: bool) -> None:
            """Set whether this panel is in use (for single-agent mode).

            Args:
                in_use: True if this agent is active, False to show "Not in use" overlay.
            """
            self._is_in_use = in_use
            try:
                overlay = self.query_one(f"#{self._not_in_use_id}")
                if in_use:
                    overlay.add_class("hidden")
                else:
                    overlay.remove_class("hidden")
            except Exception:
                pass

        def is_in_use(self) -> bool:
            """Check if this panel is currently in use."""
            return self._is_in_use

        def update_context_display(self, context_sources: List[str]) -> None:
            """Update the context sources display in the panel header.

            Args:
                context_sources: List of answer labels this agent can see (e.g., ["agent1.1", "agent2.1"])
            """
            self._context_sources = context_sources.copy()
            # Store context by current round for view switching
            self._context_by_round[self._current_round] = context_sources.copy()

            try:
                context_label = self.query_one(f"#{self._context_label_id}", Label)

                if context_sources:
                    # Format: "Context: A1.1, A2.1" or "Context: A1.1 +2 more"
                    # Shorten labels: "agent1.1" -> "A1.1"
                    short_labels = []
                    for label in context_sources[:3]:
                        # Convert "agent1.1" to "A1.1"
                        if label.startswith("agent"):
                            short_labels.append("A" + label[5:])
                        else:
                            short_labels.append(label)

                    ctx_text = f"Context: {', '.join(short_labels)}"
                    if len(context_sources) > 3:
                        ctx_text += f" +{len(context_sources) - 3}"

                    context_label.update(ctx_text)
                    context_label.remove_class("hidden")
                else:
                    context_label.update("")
                    context_label.add_class("hidden")
            except Exception:
                pass

        def update_task_plan(self, tasks: List[Dict[str, Any]], plan_id: str = None, operation: str = "create") -> None:
            """Update the active task plan for this agent.

            Args:
                tasks: List of task dictionaries
                plan_id: ID of the task plan (tool_id)
                operation: Type of operation (create, update, etc.)
            """
            self._active_task_plan_id = plan_id
            # Deep copy each task dict to avoid reference issues
            self._active_task_plan_tasks = [t.copy() for t in tasks] if tasks else None

            # Debug: log task statuses
            if tasks:
                completed = sum(1 for t in tasks if t.get("status") in ("completed", "verified"))
                verified = sum(1 for t in tasks if t.get("status") == "verified")
                in_progress = sum(1 for t in tasks if t.get("status") == "in_progress")
                tui_log(f"update_task_plan: {completed} completed, {verified} verified, {in_progress} in_progress (of {len(tasks)} total)")

                # Update ribbon tasks display
                try:
                    ribbon = self.coordination_display._agent_status_ribbon
                    if ribbon:
                        ribbon.set_tasks(self.agent_id, completed, len(tasks))
                except Exception:
                    pass

        def _refresh_header(self) -> None:
            """Refresh the header display.

            NOTE: Agent header row removed in Phase 8c/10 - now a no-op.
            Round number shown in status ribbon, agent ID in tabs.
            Background tasks visible via tool cards in timeline.
            """
            # Header row was removed - ribbon and tabs show this info now

        def toggle_task_plan(self) -> None:
            """Toggle the visibility of the pinned task plan."""
            if not self._active_task_plan_tasks:
                return

            self._task_plan_visible = not self._task_plan_visible

            try:
                pinned_container = self.query_one(f"#{self._pinned_task_plan_id}", Container)
                if self._task_plan_visible:
                    pinned_container.remove_class("collapsed")
                else:
                    pinned_container.add_class("collapsed")
            except Exception:
                pass

        def _update_pinned_task_plan(
            self,
            tasks: List[Dict[str, Any]],
            focused_task_id: Optional[str] = None,
            operation: str = "update",
            show_notification: bool = True,
        ) -> None:
            """Update the pinned task plan widget.

            Args:
                tasks: List of task dictionaries
                focused_task_id: Task to highlight
                operation: Type of operation
                show_notification: Whether to show update notification in timeline
            """
            from massgen.frontend.displays.textual_widgets import TaskPlanCard

            try:
                pinned_container = self.query_one(f"#{self._pinned_task_plan_id}", Container)

                # Find existing card or create new one
                existing_card = None
                try:
                    existing_card = pinned_container.query_one(TaskPlanCard)
                except Exception:
                    pass

                if existing_card:
                    # Update existing card (per-task highlighting handled inside)
                    existing_card.update_tasks(tasks, focused_task_id=focused_task_id, operation=operation)
                else:
                    # Create new card
                    card = TaskPlanCard(
                        tasks=tasks,
                        focused_task_id=focused_task_id,
                        operation=operation,
                        id=f"pinned_card_{self._dom_safe_id}",
                    )
                    pinned_container.mount(card)

                # Show the pinned area
                pinned_container.remove_class("hidden")
                self._task_plan_visible = True

                # NOTE: Task update notifications removed - pinned task card at top
                # already shows current status, so inline notifications are redundant

            except Exception as e:
                tui_log(f"_update_pinned_task_plan error: {e}")

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
            """Handle restart - start new round with view-based navigation.

            With Phase 12 view-based navigation, restarts create a new round that
            users can switch to via the dropdown. This clears the timeline for fresh
            content and updates the round tracking.
            """
            # Mark that non-tool content arrived (prevents future batching across this content)
            self._batch_tracker.mark_content_arrived()
            # Finalize any current batch when restart occurs
            self._batch_tracker.finalize_current_batch()

            # Determine if this was a context reset
            is_context_reset = "context" in reason.lower() or "reset" in reason.lower()

            # Start the new round (clears timeline, updates ribbon, stores content)
            self.start_new_round(attempt, is_context_reset)

            # Reset per-attempt UI state
            self._tool_row_count = 0
            self._reasoning_header_shown = False

        def add_content(self, content: str, content_type: str, tool_call_id: Optional[str] = None):
            """Add content to agent panel using section-based routing.

            Content is normalized and routed to appropriate sections:
            - Tool content -> ToolSection (collapsible tool cards)
            - Thinking/text -> ThinkingSection (streaming RichLog)
            - Status -> Updates status badge
            - Presentation -> ThinkingSection with completion footer
            - Restart -> Restart separator in ThinkingSection

            Args:
                content: The content to add
                content_type: Type hint from backend
                tool_call_id: Optional unique ID for this tool call
            """
            self._hide_loading()  # Hide loading when any content arrives

            # Normalize content first, passing tool_call_id
            normalized = ContentNormalizer.normalize(content, content_type, tool_call_id)

            # Route based on detected content type
            if normalized.content_type.startswith("tool_"):
                self._add_tool_content(normalized, content, content_type)
            elif normalized.content_type == "status":
                self._add_status_content(normalized)
            elif normalized.content_type == "presentation":
                self._add_presentation_content(normalized)
            elif content_type == "restart":
                self._add_restart_content(content)
            elif normalized.content_type == "injection":
                self._add_injection_content(normalized)
            elif normalized.content_type == "reminder":
                self._add_reminder_content(normalized)
            elif normalized.content_type in ("thinking", "text", "content"):
                self._add_thinking_content(normalized, content_type)
            else:
                # Fallback: route to thinking section if displayable
                if normalized.should_display:
                    self._add_thinking_content(normalized, content_type)

        def _add_tool_content(self, normalized, raw_content: str, raw_type: str):
            """Route tool content to TimelineSection (chronologically).

            Note: Restart detection is handled solely via show_restart_separator()
            called from the orchestrator. We removed the duplicate detection here
            that used _session_count to avoid conflicting round transitions.

            MCP tools from the same server are batched into ToolBatchCard when 2+
            consecutive tools arrive. Single tools appear as normal ToolCallCard.
            """
            # Flush any pending line buffer content to timeline before processing tool
            # This ensures thinking/reasoning content that didn't end with newline is preserved
            self._flush_line_buffer_to_timeline()

            # Process through handler
            tool_data = self._tool_handler.process(normalized)

            if not tool_data:
                return

            # Phase 12: No viewing_current check needed - CSS visibility handles it
            # Add or update tool card in TimelineSection (chronologically)
            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)

                # Check if this is a Planning MCP tool - we'll show TaskPlanCard instead
                is_planning_tool = self._is_planning_mcp_tool(tool_data.tool_name)
                # Check if this is a subagent tool - we'll show SubagentCard instead
                is_subagent_tool = self._is_subagent_tool(tool_data.tool_name)

                # Skip batching for special tool types (planning, subagent)
                skip_batching = is_planning_tool or is_subagent_tool

                # Debug: Log tool content (skip planning tools for cleaner trace)
                # Only log new tools (running status) or completions, not args updates
                if not is_planning_tool:
                    # Check if this is an args update for existing tool
                    existing_card = timeline.get_tool(tool_data.tool_id) if tool_data.status == "running" else None
                    existing_batch = timeline.get_tool_batch(tool_data.tool_id) if tool_data.status == "running" and not skip_batching else None
                    existing_card is not None or existing_batch is not None

                if tool_data.status == "running":
                    # Check if this is an args update for existing tool
                    existing_card = timeline.get_tool(tool_data.tool_id)
                    existing_batch = timeline.get_tool_batch(tool_data.tool_id) if not skip_batching else None

                    if existing_card:
                        # Update existing standalone card with args
                        if tool_data.args_summary:
                            existing_card.set_params(tool_data.args_summary, tool_data.args_full)
                    elif existing_batch:
                        # Update existing tool in batch with args
                        timeline.update_tool_in_batch(tool_data.tool_id, tool_data)
                    elif is_subagent_tool:
                        # Subagent tool starting - show SubagentCard with pending tasks from args
                        self._show_subagent_card_from_args(tool_data, timeline)
                    elif is_planning_tool:
                        # Planning tools are skipped - TaskPlanCard is shown on completion
                        pass
                    elif not skip_batching:
                        # Check if this MCP tool should be batched
                        action, server_name, batch_id, pending_id = self._batch_tracker.process_tool(tool_data)

                        if action == "pending":
                            # First MCP tool - show as normal card, track for potential batch
                            timeline.add_tool(tool_data, round_number=self._current_round)
                        elif action == "convert_to_batch" and server_name and batch_id and pending_id:
                            # Second tool from same server - convert to batch
                            timeline.convert_tool_to_batch(
                                pending_id,
                                tool_data,
                                batch_id,
                                server_name,
                                round_number=self._current_round,
                            )
                        elif action == "add_to_batch" and batch_id:
                            # Add to existing batch
                            timeline.add_tool_to_batch(batch_id, tool_data)
                        else:
                            # Standalone non-MCP tool
                            timeline.add_tool(tool_data, round_number=self._current_round)
                    else:
                        # Fallback for other special tools
                        timeline.add_tool(tool_data, round_number=self._current_round)
                else:
                    # Tool completed/failed - update the card in timeline
                    # Phase 12: No storage needed - widgets stay in DOM with round tags
                    if not is_planning_tool and not is_subagent_tool:
                        # Use batch tracker to determine if this is a batch or standalone update
                        action, server_name, batch_id, _ = self._batch_tracker.process_tool(tool_data)

                        if action == "update_batch" and timeline.get_tool_batch(tool_data.tool_id):
                            timeline.update_tool_in_batch(tool_data.tool_id, tool_data)
                        else:
                            # Update standalone tool card with result/error
                            timeline.update_tool(tool_data.tool_id, tool_data)

                    # Check if this is a Planning MCP tool and display TaskPlanCard
                    tui_log(f"_add_tool_content: tool_status={tool_data.status}, tool_name={tool_data.tool_name}")
                    if tool_data.status == "success":
                        self._check_and_display_task_plan(tool_data, timeline)
                        # Check if this is a subagent tool - update existing card with results
                        if is_subagent_tool:
                            self._update_subagent_card_with_results(tool_data, timeline)

                        # Check if this is a terminal tool (new_answer, vote) and mark for delayed transition
                        tool_name_lower = tool_data.tool_name.lower()
                        if "new_answer" in tool_name_lower or "vote" in tool_name_lower:
                            self.mark_terminal_tool_complete()
                            tui_log(f"Terminal tool completed: {tool_data.tool_name}")

                    # Refresh header if this is a background operation (to show bg badge)
                    if tool_data.status == "background":
                        self._refresh_header()

                # Update running tools count in status bar
                self._update_running_tools_count()
            except Exception as e:
                # Fallback to legacy RichLog
                tui_log(f"Tool content error: {e}")
                self._handle_tool_content(raw_content)

            self._line_buffer = ""
            self.current_line_label.update(Text(""))

        def _add_status_content(self, normalized):
            """Route status content to TimelineSection with subtle display."""
            if not normalized.should_display:
                return

            # Mark that non-tool content arrived (prevents future batching across this content)
            self._batch_tracker.mark_content_arrived()
            # Finalize any current batch when non-tool content arrives
            self._batch_tracker.finalize_current_batch()

            # Detect session completion for restart tracking
            if "completed" in normalized.cleaned_content.lower():
                self._session_completed = True
                # NOTE: Completion footer disabled - clutters UI
                # self._show_completion_footer()

            # Add status to timeline as a subtle line
            # Phase 12: Pass round_number for CSS visibility
            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)
                timeline.add_text(f"● {normalized.cleaned_content}", style="dim cyan", text_class="status", round_number=self._current_round)
            except Exception:
                # Fallback
                status_bar = self._make_full_width_bar(f"  📊  {normalized.cleaned_content}", "bold yellow on #2d333b")
                self.content_log.write(status_bar)

            self._line_buffer = ""
            self.current_line_label.update(Text(""))

        def _update_running_tools_count(self) -> None:
            """Update running tools counter in status bar."""
            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)
                count = timeline.get_running_tools_count()
                if self._status_bar:
                    self._status_bar.update_running_tools(count)
            except Exception:
                pass  # Silently fail if timeline not found

        def _add_presentation_content(self, normalized):
            """Route presentation content to TimelineSection."""
            if not normalized.should_display:
                return

            # Mark that non-tool content arrived (prevents future batching across this content)
            self._batch_tracker.mark_content_arrived()
            # Finalize any current batch when non-tool content arrives
            self._batch_tracker.finalize_current_batch()

            # Mark presentation shown for restart detection
            if "Providing answer" in normalized.original:
                self._presentation_shown = True
                # NOTE: Completion footer disabled - clutters UI
                # self._show_completion_footer()

            # Add to timeline with response styling
            # Phase 12: Pass round_number for CSS visibility
            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)
                timeline.add_text(normalized.cleaned_content, style="bold #4ec9b0", text_class="response", round_number=self._current_round)
            except Exception:
                # Fallback
                self.content_log.write(Text(f"🎤 {normalized.cleaned_content}", style="magenta"))

            self._line_buffer = ""
            self.current_line_label.update(Text(""))

        def _add_restart_content(self, content: str):
            """Handle round transition - start a new round with view-based navigation.

            With Phase 12 view-based navigation, rounds are separated by the dropdown
            selector rather than inline banners. This method:
            1. Parses the round number
            2. Starts the new round (which clears the timeline)
            3. Does NOT add inline separators (use dropdown to switch views)
            """
            # Parse attempt number
            attempt = 1
            is_context_reset = "context" in content.lower() or "reset" in content.lower()

            if "attempt:" in content:
                try:
                    parts = content.split("attempt:")
                    if len(parts) > 1:
                        attempt_part = parts[1].split()[0]
                        attempt = int(attempt_part)
                except (ValueError, IndexError):
                    pass

            # Start the new round (clears timeline, updates ribbon)
            # No inline separator - view dropdown handles round navigation
            self.start_new_round(attempt, is_context_reset)

            self._line_buffer = ""
            self.current_line_label.update(Text(""))

        def _flush_line_buffer_to_timeline(self, text_class: str = None) -> None:
            """Flush any remaining line buffer content to the timeline.

            Called when content type changes (e.g., thinking -> tool) to ensure
            all content is written, even if it didn't end with a newline.

            Args:
                text_class: CSS class for the content. If None, uses the last
                    text_class that was used (tracked via _last_text_class).
            """
            if self._line_buffer.strip():
                # Use stored text_class if not provided - this preserves the correct
                # type when flushing buffered content on content type transitions
                if text_class is None:
                    text_class = getattr(self, "_last_text_class", "content-inline")
                try:
                    timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)
                    timeline.add_text(
                        self._line_buffer,
                        style="dim italic",
                        text_class=text_class,
                        round_number=self._current_round,
                    )
                except Exception:
                    pass
                self._line_buffer = ""
                self.current_line_label.update(Text(""))

        def _add_thinking_content(self, normalized, raw_type: str):
            """Route thinking/text content to TimelineSection.

            Phase 15.5: Only display thinking/reasoning content, skip plain text.
            Tool cards (answer, vote, etc.) already show meaningful output,
            so raw text is redundant and clutters the UI.
            """
            # Process through handler for extra filtering
            cleaned = self._thinking_handler.process(normalized)
            if not cleaned:
                return

            # Mark that non-tool content arrived (prevents future batching across this content)
            self._batch_tracker.mark_content_arrived()
            # Finalize any current batch when non-tool content arrives
            self._batch_tracker.finalize_current_batch()

            # Check if this is coordination content
            is_coordination = getattr(normalized, "is_coordination", False)

            # Phase 15.5: Display thinking and content, skip other types
            if not is_coordination and raw_type not in ("thinking", "content", "text"):
                return  # Skip non-displayable content

            # Add to timeline
            # Phase 12: No storage needed - widgets stay in DOM with round tags
            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)

                # Handle line buffering for streaming
                # Capture current_round in closure for CSS visibility tagging
                current_round = self._current_round

                # Use different text_class for thinking vs content
                # This affects how TimelineSection labels the CollapsibleTextCard
                # NOTE: Use normalized.content_type instead of raw_type to ensure
                # consistent labeling even if the backend sent a different content_type
                text_class = "thinking-inline" if normalized.content_type == "thinking" else "content-inline"

                # Flush line buffer if content type changed to prevent type mixing
                # This ensures incomplete lines from previous type don't get labeled with new type
                if not hasattr(self, "_last_text_class"):
                    self._last_text_class = text_class
                if self._last_text_class != text_class and self._line_buffer.strip():
                    # Flush with the PREVIOUS text_class before switching
                    prev_text_class = self._last_text_class
                    timeline.add_text(self._line_buffer, style="dim italic", text_class=prev_text_class, round_number=current_round)
                    self._line_buffer = ""
                self._last_text_class = text_class

                def write_line(line: str):
                    # Phase 12: Pass round_number for CSS visibility
                    timeline.add_text(line, style="dim italic", text_class=text_class, round_number=current_round)

                # Use original content for line buffer to preserve inter-token
                # whitespace (e.g. " CSS") that strip_prefixes/clean_content
                # would remove. The handler check above already validated the
                # content is displayable.
                buffer_content = normalized.original if normalized.original else cleaned
                self._line_buffer = _process_line_buffer(
                    self._line_buffer,
                    buffer_content,
                    write_line,
                )
                self.current_line_label.update(Text(self._line_buffer))
            except Exception:
                # Fallback to legacy RichLog
                # Use normalized.content_type for consistency
                if normalized.content_type == "thinking":
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

        def _add_injection_content(self, normalized):
            """Add injection content (cross-agent context sharing) to timeline.

            Displays as a styled purple bar in the timeline.
            """
            if not normalized.should_display:
                return

            # Mark that non-tool content arrived (prevents future batching across this content)
            self._batch_tracker.mark_content_arrived()
            # Finalize any current batch when non-tool content arrives
            self._batch_tracker.finalize_current_batch()

            content = normalized.cleaned_content
            # Truncate preview if very long
            preview = content[:100] + "..." if len(content) > 100 else content
            preview = preview.replace("\n", " ")

            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)
                # Add as styled text with injection class
                # Phase 12: Pass round_number for CSS visibility
                timeline.add_text(
                    f"📥 Context Update: {preview}",
                    style="bold",
                    text_class="injection",
                    round_number=self._current_round,
                )
            except Exception:
                # Fallback to legacy RichLog
                self.content_log.write(Text(f"📥 Context Update: {preview}", style="bold magenta"))

        def _add_reminder_content(self, normalized):
            """Add reminder content (high priority task reminders) to TaskPlanCard.

            Attaches the reminder to the most recent TaskPlanCard if one exists,
            otherwise displays as a standalone styled bar in the timeline.
            """
            if not normalized.should_display:
                return

            # Mark that non-tool content arrived (prevents future batching across this content)
            self._batch_tracker.mark_content_arrived()
            # Finalize any current batch when non-tool content arrives
            self._batch_tracker.finalize_current_batch()

            content = normalized.cleaned_content

            # Try to attach reminder to the most recent TaskPlanCard
            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)

                # Look for the most recent TaskPlanCard by active task plan ID
                task_plan_card = None
                if self._active_task_plan_id:
                    try:
                        from massgen.frontend.displays.textual_widgets import (
                            TaskPlanCard,
                        )

                        task_plan_card = timeline.query_one(
                            f"#task_plan_{self._active_task_plan_id}",
                            TaskPlanCard,
                        )
                    except Exception:
                        pass

                # If no card found by ID, try to find any TaskPlanCard in timeline
                if not task_plan_card:
                    try:
                        from massgen.frontend.displays.textual_widgets import (
                            TaskPlanCard,
                        )

                        cards = list(timeline.query(TaskPlanCard))
                        if cards:
                            task_plan_card = cards[-1]  # Most recent card
                    except Exception:
                        pass

                if task_plan_card:
                    # Attach reminder to the TaskPlanCard
                    task_plan_card.set_reminder(content)
                    return

                # Fallback: display as standalone text in timeline
                preview = content[:100] + "..." if len(content) > 100 else content
                preview = preview.replace("\n", " ")
                # Phase 12: Pass round_number for CSS visibility
                timeline.add_text(
                    f"💡 Reminder: {preview}",
                    style="bold",
                    text_class="reminder",
                    round_number=self._current_round,
                )
            except Exception:
                # Fallback to legacy RichLog
                preview = content[:100] + "..." if len(content) > 100 else content
                preview = preview.replace("\n", " ")
                self.content_log.write(Text(f"💡 Reminder: {preview}", style="bold yellow"))

        def _is_planning_mcp_tool(self, tool_name: str) -> bool:
            """Check if a tool is a Planning MCP tool (should show TaskPlanCard instead of tool card).

            Args:
                tool_name: The tool name to check

            Returns:
                True if this is a Planning MCP tool
            """
            planning_tools = [
                "create_task_plan",
                "update_task_status",
                "add_task",
                "edit_task",
                "get_task_plan",
                "delete_task",
                "get_ready_tasks",
                "get_blocked_tasks",
            ]
            tool_lower = tool_name.lower()
            return any(pt in tool_lower for pt in planning_tools)

        def _is_subagent_tool(self, tool_name: str) -> bool:
            """Check if a tool is a subagent tool (should show SubagentCard instead of tool card).

            Args:
                tool_name: The tool name to check

            Returns:
                True if this is a subagent spawning tool
            """
            subagent_tools = [
                "spawn_subagents",
                "spawn_subagent",
            ]
            tool_lower = tool_name.lower()
            return any(st in tool_lower for st in subagent_tools)

        def _show_subagent_card_from_args(self, tool_data, timeline) -> None:
            """Show SubagentCard when spawn_subagents tool starts, parsing tasks from args.

            This allows users to see subagents as they're being spawned, not just after completion.
            NOTE: This is a fallback path - the callback via show_subagent_card_from_spawn
            should create the card immediately. This path only runs when the "running" chunk
            arrives (which may be delayed due to stream buffering).
            """
            import json

            from massgen.subagent.models import SubagentDisplayData

            # Check if card already exists (created by callback)
            card_id = f"subagent_{tool_data.tool_id}"
            try:
                timeline.query_one(f"#{card_id}", SubagentCard)
                tui_log(f"_show_subagent_card_from_args: card {card_id} already exists, skipping")
                return
            except Exception:
                pass  # Card doesn't exist, continue to create it

            # Also check for any SubagentCard in the timeline (callback might use different ID)
            try:
                cards = list(timeline.query(SubagentCard))
                if cards:
                    tui_log(f"_show_subagent_card_from_args: SubagentCard already exists ({cards[0].id}), skipping")
                    return
            except Exception:
                pass

            # Parse args to get task list
            args = tool_data.args_full
            if not args:
                tui_log("_show_subagent_card_from_args: no args_full")
                return

            try:
                args_data = json.loads(args)
            except (json.JSONDecodeError, TypeError):
                tui_log(f"_show_subagent_card_from_args: failed to parse args: {args[:100]}")
                return

            if not isinstance(args_data, dict):
                return

            # Extract tasks from args
            tasks = args_data.get("tasks", [])
            if not tasks:
                tui_log("_show_subagent_card_from_args: no tasks in args")
                return

            tui_log(f"_show_subagent_card_from_args: found {len(tasks)} tasks to spawn")

            # Create SubagentDisplayData for each task (all pending/running)
            subagents = []
            for task_data in tasks:
                subagent_id = task_data.get("subagent_id", task_data.get("id", f"subagent_{len(subagents)}"))
                task_desc = task_data.get("task", "")

                subagents.append(
                    SubagentDisplayData(
                        id=subagent_id,
                        task=task_desc,
                        status="running",  # All start as running
                        progress_percent=0,
                        elapsed_seconds=0.0,
                        timeout_seconds=task_data.get("timeout_seconds", 300),
                        workspace_path="",  # Not yet assigned
                        workspace_file_count=0,
                        last_log_line="Starting...",
                        error=None,
                        answer_preview=None,
                        log_path=None,
                    ),
                )

            if not subagents:
                return

            # Create and add SubagentCard to timeline
            card = SubagentCard(
                subagents=subagents,
                tool_call_id=tool_data.tool_id,
                id=f"subagent_{tool_data.tool_id}",
            )
            timeline.add_widget(card)
            tui_log(f"_show_subagent_card_from_args: added SubagentCard with {len(subagents)} pending subagents")

        def _update_subagent_card_with_results(self, tool_data, timeline) -> None:
            """Update existing SubagentCard with completion results.

            Called when spawn_subagents tool completes to update status, progress, answers, etc.
            """
            import json

            from massgen.subagent.models import SubagentDisplayData

            # Find existing card - check both possible IDs since callback might use different ID
            card_id = f"subagent_{tool_data.tool_id}"
            card = None
            try:
                card = timeline.query_one(f"#{card_id}", SubagentCard)
                tui_log(f"_update_subagent_card_with_results: found card by tool_id: {card_id}")
            except Exception:
                # Also try querying by tool_call_id if different
                if hasattr(tool_data, "tool_call_id") and tool_data.tool_call_id != tool_data.tool_id:
                    alt_id = f"subagent_{tool_data.tool_call_id}"
                    try:
                        card = timeline.query_one(f"#{alt_id}", SubagentCard)
                        tui_log(f"_update_subagent_card_with_results: found card by tool_call_id: {alt_id}")
                    except Exception:
                        pass

                # Try finding ANY SubagentCard in the timeline
                if card is None:
                    try:
                        cards = list(timeline.query(SubagentCard))
                        if cards:
                            card = cards[0]  # Use first matching card
                            tui_log(f"_update_subagent_card_with_results: found card by query: {card.id}")
                    except Exception:
                        pass

            if card is None:
                tui_log(f"_update_subagent_card_with_results: no card found (tried {card_id}), skipping duplicate creation")
                # Don't create a new card - the callback already created one
                # Just log and return to avoid duplicates
                return

            # Parse results
            result = tool_data.result_full
            if not result:
                return

            try:
                result_data = json.loads(result)
            except (json.JSONDecodeError, TypeError):
                return

            if not isinstance(result_data, dict):
                return

            # Extract spawned subagents list
            spawned = result_data.get("results", result_data.get("spawned_subagents", result_data.get("subagents", [])))
            if not spawned:
                return

            # Build updated subagent list
            updated_subagents = []
            for sa_data in spawned:
                # Map status from result to our display status
                raw_status = sa_data.get("status", "running")
                if raw_status == "completed":
                    display_status = "completed"
                    progress = 100
                elif raw_status == "completed_but_timeout":
                    display_status = "timeout"
                    progress = sa_data.get("completion_percentage", 100)
                elif raw_status == "failed":
                    display_status = "failed"
                    progress = 0
                else:
                    display_status = "running"
                    progress = 0

                elapsed = sa_data.get("execution_time_seconds", 0.0)

                # Count files in workspace if it exists
                workspace_path = sa_data.get("workspace", "")
                file_count = 0
                if workspace_path:
                    from pathlib import Path

                    workspace = Path(workspace_path)
                    if workspace.exists():
                        try:
                            file_count = sum(1 for _ in workspace.rglob("*") if _.is_file())
                        except Exception:
                            pass

                # Try to get task from original card data
                task = sa_data.get("task", "")
                if not task:
                    # Try to find in existing card
                    subagent_id = sa_data.get("subagent_id", sa_data.get("id", "unknown"))
                    for existing in card.subagents:
                        if existing.id == subagent_id:
                            task = existing.task
                            break

                updated_subagents.append(
                    SubagentDisplayData(
                        id=sa_data.get("subagent_id", sa_data.get("id", "unknown")),
                        task=task,
                        status=display_status,
                        progress_percent=progress,
                        elapsed_seconds=elapsed,
                        timeout_seconds=sa_data.get("timeout_seconds", 300),
                        workspace_path=workspace_path,
                        workspace_file_count=file_count,
                        last_log_line=sa_data.get("error", "") if sa_data.get("error") else "",
                        error=sa_data.get("error"),
                        answer_preview=sa_data.get("answer", "")[:200] if sa_data.get("answer") else None,
                        log_path=sa_data.get("log_path"),
                    ),
                )

            if updated_subagents:
                card.update_subagents(updated_subagents)
                tui_log(f"_update_subagent_card_with_results: updated card with {len(updated_subagents)} subagents")

        def _check_and_display_subagent_card(self, tool_data, timeline) -> None:
            """Check if tool result is from subagent spawn and display SubagentCard.

            Subagent tools include:
            - spawn_subagents
            - spawn_subagent
            """
            import json

            from massgen.subagent.models import SubagentDisplayData

            # Check if tool name matches a subagent tool
            tool_name = tool_data.tool_name.lower()
            tui_log(f"_check_and_display_subagent_card: tool_name={tool_name}, is_subagent={self._is_subagent_tool(tool_name)}")
            if not self._is_subagent_tool(tool_name):
                return

            # Try to parse the result as JSON to extract spawned subagents
            result = tool_data.result_full
            if not result:
                return

            try:
                result_data = json.loads(result)
            except (json.JSONDecodeError, TypeError):
                return

            if not isinstance(result_data, dict):
                return

            # Extract spawned subagents list
            # The spawn_subagents tool returns results in "results" key
            spawned = result_data.get("results", result_data.get("spawned_subagents", result_data.get("subagents", [])))
            tui_log(f"_check_and_display_subagent_card: found {len(spawned) if spawned else 0} spawned subagents")
            if not spawned:
                return

            # Create SubagentDisplayData for each spawned subagent
            subagents = []
            for sa_data in spawned:
                # Map status from result to our display status
                raw_status = sa_data.get("status", "running")
                if raw_status == "completed":
                    display_status = "completed"
                    progress = 100
                elif raw_status == "completed_but_timeout":
                    display_status = "timeout"
                    progress = sa_data.get("completion_percentage", 100)
                elif raw_status == "failed":
                    display_status = "failed"
                    progress = 0
                else:
                    display_status = "running"
                    progress = 0

                elapsed = sa_data.get("execution_time_seconds", 0.0)

                # Count files in workspace if it exists
                workspace_path = sa_data.get("workspace", "")
                file_count = 0
                if workspace_path:
                    from pathlib import Path

                    workspace = Path(workspace_path)
                    if workspace.exists():
                        try:
                            file_count = sum(1 for _ in workspace.rglob("*") if _.is_file())
                        except Exception:
                            pass

                subagents.append(
                    SubagentDisplayData(
                        id=sa_data.get("subagent_id", sa_data.get("id", "unknown")),
                        task=sa_data.get("task", ""),  # May be empty if not in result
                        status=display_status,
                        progress_percent=progress,
                        elapsed_seconds=elapsed,
                        timeout_seconds=sa_data.get("timeout_seconds", 300),
                        workspace_path=workspace_path,
                        workspace_file_count=file_count,
                        last_log_line=sa_data.get("error", "") if sa_data.get("error") else "",
                        error=sa_data.get("error"),
                        answer_preview=sa_data.get("answer", "")[:200] if sa_data.get("answer") else None,
                        log_path=sa_data.get("log_path"),
                    ),
                )

            if not subagents:
                return

            # Create and add SubagentCard to timeline
            card = SubagentCard(
                subagents=subagents,
                tool_call_id=tool_data.tool_id,
                id=f"subagent_{tool_data.tool_id}",
            )
            timeline.add_widget(card)
            tui_log(f"_check_and_display_subagent_card: added SubagentCard with {len(subagents)} subagents")

        def _check_and_display_task_plan(self, tool_data, timeline) -> None:
            """Check if tool result is from Planning MCP and display/update TaskPlanCard.

            Instead of adding a new card each time, this method:
            - Creates a single persistent TaskPlanCard on first create_task_plan
            - Updates that same card in place for subsequent updates

            Planning MCP tools include:
            - create_task_plan
            - update_task_status
            - add_task
            - edit_task
            - get_task_plan
            """
            import json

            # Planning MCP tool names
            PLANNING_TOOLS = {
                "create_task_plan": "create",
                "update_task_status": "update",
                "add_task": "add",
                "edit_task": "edit",
                "get_task_plan": "get",
            }

            # Check if tool name matches a planning tool
            tool_name = tool_data.tool_name.lower()
            tui_log(f"_check_and_display_task_plan: tool_name={tool_name}")
            operation = None
            for planning_tool, op in PLANNING_TOOLS.items():
                if planning_tool in tool_name:
                    operation = op
                    break

            if not operation:
                tui_log(f"_check_and_display_task_plan: no operation match for {tool_name}")
                return

            # Try to parse the result as JSON to extract tasks
            result = tool_data.result_full
            tui_log(f"_check_and_display_task_plan: result_full={result[:200] if result else 'None'}...")
            if not result:
                tui_log("_check_and_display_task_plan: no result_full")
                return

            try:
                result_data = json.loads(result)
            except (json.JSONDecodeError, TypeError) as e:
                tui_log(f"_check_and_display_task_plan: JSON parse error: {e}")
                return

            # Check if the result has task data
            if not isinstance(result_data, dict):
                return

            # Extract tasks list
            tasks = []
            focused_task_id = None

            if "tasks" in result_data:
                tasks = result_data["tasks"]
            elif "plan" in result_data and isinstance(result_data["plan"], dict):
                tasks = result_data["plan"].get("tasks", [])

            # For update_task_status, update the existing task plan with the new status
            if operation in ("update", "edit") and "task" in result_data:
                updated_task = result_data["task"]
                focused_task_id = updated_task.get("id")
                updated_status = updated_task.get("status")
                tui_log(f"_check_and_display_task_plan: update/edit - task_id={focused_task_id}, new_status={updated_status}")

                # If we have a cached task plan, update it with the new task status
                if self._active_task_plan_tasks and not tasks:
                    tasks = [t.copy() for t in self._active_task_plan_tasks]  # Deep copy task dicts
                    # Update the task in our cached list
                    task_found = False
                    for i, task in enumerate(tasks):
                        if task.get("id") == focused_task_id:
                            tui_log(f"_check_and_display_task_plan: found task at index {i}, old_status={task.get('status')}")
                            tasks[i] = updated_task.copy()  # Copy the updated task too
                            task_found = True
                            break
                    if not task_found:
                        tui_log(f"_check_and_display_task_plan: task {focused_task_id} NOT found in cached tasks")

            if not tasks:
                tui_log("_check_and_display_task_plan: no tasks found in result")
                return

            tui_log(f"_check_and_display_task_plan: found {len(tasks)} tasks, updating pinned area")

            # Update the pinned task plan area (shows notification for updates)
            self._update_pinned_task_plan(
                tasks=tasks,
                focused_task_id=focused_task_id,
                operation=operation,
                show_notification=(operation != "create"),  # Only show notification for updates
            )

            # Update the agent panel's task plan tracking
            self.update_task_plan(tasks, plan_id=tool_data.tool_id, operation=operation)

        def _clear_timeline(self):
            """Clear the timeline for a new session/round."""
            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)
                timeline.clear()
            except Exception:
                pass

            # Reset per-round state
            self._reset_round_state()

        def _reset_round_state(self):
            """Reset per-round state (task plan, background tools indicator, etc.)."""
            # Clear task plan tracking
            self._active_task_plan_id = None
            self._active_task_plan_tasks = None

            # Clear pinned task plan UI container
            try:
                pinned_container = self.query_one(f"#{self._pinned_task_plan_id}", Container)
                pinned_container.remove_children()
                pinned_container.add_class("hidden")
                pinned_container.remove_class("collapsed")
                self._task_plan_visible = True  # Reset visibility state for next round
            except Exception:
                pass

            # Clear tools tracking (resets bg count) but keep visual timeline
            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)
                timeline.clear_tools_tracking()
            except Exception:
                pass

            # Refresh header to hide badges (bg shells will be killed by orchestrator)
            self._refresh_header()

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

        # ========================================================================
        # Phase 12: CSS-based round navigation
        # ========================================================================
        # Storage methods removed - widgets stay in DOM with round-N tags

        def start_new_round(self, round_number: int, is_context_reset: bool = False) -> None:
            """Start a new round - update tracking and switch visibility.

            Phase 12: With CSS-based visibility, all round content stays in the DOM.
            We switch visibility to show the new round and hide old round content.

            Terminal Tool Delay: When a terminal tool (new_answer, vote) just completed,
            we delay the transition by 3 seconds so users can see the completed action
            before the view switches to the new round.

            IMPORTANT: This method is atomic - tracking is updated FIRST before any
            visibility changes to ensure all new content gets tagged with the correct
            round number.

            Args:
                round_number: The new round number
                is_context_reset: Whether this round started with a context reset
            """
            from massgen.logger_config import logger

            logger.debug(
                f"AgentPanel.start_new_round: round={round_number}, " f"prev_round={self._current_round}, context_reset={is_context_reset}",
            )

            # Terminal tool transition delay - give users time to see completed action
            if self._transition_pending:
                # Already waiting for a transition - update the pending round
                self._pending_round_transition = (round_number, is_context_reset)
                return

            if self._last_tool_was_terminal:
                # Delay transition so users can see the completed terminal tool
                self._transition_pending = True
                self._pending_round_transition = (round_number, is_context_reset)
                self._transition_timer = self.set_timer(5.0, self._execute_round_transition)
                self._last_tool_was_terminal = False  # Reset for next round

                # Show a subtle notification
                try:
                    self.notify("Round complete - transitioning in 5s", timeout=3)
                except Exception:
                    pass  # Notification is optional
                return

            # Execute the round transition immediately
            self._execute_round_transition_impl(round_number, is_context_reset)

        def _execute_round_transition(self) -> None:
            """Execute a delayed round transition (called by timer)."""
            self._transition_pending = False
            self._transition_timer = None

            if self._pending_round_transition:
                round_number, is_context_reset = self._pending_round_transition
                self._pending_round_transition = None
                self._execute_round_transition_impl(round_number, is_context_reset)

        def _execute_round_transition_impl(self, round_number: int, is_context_reset: bool = False) -> None:
            """Execute the actual round transition logic."""
            from massgen.logger_config import logger

            # Step 1: Update round tracking FIRST (before any visibility changes)
            # This ensures all subsequent content gets tagged with the new round number
            self._current_round = round_number
            self._viewed_round = round_number  # Auto-follow to new round
            self._current_view = "round"

            # Step 2: Switch timeline visibility to new round (hides old round content)
            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)
                timeline.switch_to_round(round_number)
                # Clear tools tracking so new round's tool_ids don't collide with old round's
                timeline.clear_tools_tracking()

                # Step 3: Add "Round X" banner at the top of each new round
                if round_number > 1:
                    # Build subtitle based on restart context
                    subtitle = "Restart"
                    if is_context_reset:
                        subtitle += " • Context cleared"
                    timeline.add_separator(f"Round {round_number}", round_number=round_number, subtitle=subtitle)
            except Exception as e:
                logger.error(f"AgentPanel.start_new_round timeline error: {e}")

            # Step 4: Reset per-round UI state
            self._hide_completion_footer()
            self._tool_handler.reset()
            self._batch_tracker.reset()
            self._reasoning_header_shown = False

            # Step 5: Clear context display for new round (will be updated when context is injected)
            self._restore_context_for_round(round_number)

            # Step 6: Notify the status ribbon about the new round
            self._update_ribbon_round(round_number, is_context_reset)

            logger.debug(f"AgentPanel.start_new_round: completed round={round_number}")

        def mark_terminal_tool_complete(self) -> None:
            """Mark that a terminal tool (new_answer, vote) has just completed.

            This triggers a delayed transition when start_new_round is called,
            giving users time to see the completed action before the view switches.
            """
            self._last_tool_was_terminal = True

        def start_final_presentation(self, vote_counts: Optional[Dict[str, int]] = None, answer_labels: Optional[Dict[str, str]] = None) -> None:
            """Start the final presentation phase - shows fresh view with distinct banner.

            This is similar to start_new_round but uses a "Final Presentation" banner
            with a distinct green color scheme to indicate the winning agent presenting.

            Args:
                vote_counts: Optional dict of {agent_id: vote_count} for vote summary display
                answer_labels: Optional dict of {agent_id: label} for display (e.g., {"agent1": "A1.1"})
            """
            from massgen.logger_config import logger

            # Increment round for final presentation
            new_round = self._current_round + 1

            logger.debug(
                f"AgentPanel.start_final_presentation: agent={self.agent_id}, " f"new_round={new_round}",
            )

            # Step 1: Update round tracking
            self._current_round = new_round
            self._viewed_round = new_round
            self._current_view = "round"
            self._is_final_presentation_round = True  # Mark as final presentation round

            # Step 2: Build vote summary subtitle using answer labels (e.g., "A1.1")
            subtitle = ""
            if vote_counts:
                # Format: "Votes: A1.1(2), A2.1(1)"
                sorted_votes = sorted(vote_counts.items(), key=lambda x: x[1], reverse=True)
                vote_parts = []
                for agent_id, count in sorted_votes:
                    # Use answer label if available, otherwise fall back to shortened agent name
                    if answer_labels and agent_id in answer_labels:
                        label = answer_labels[agent_id]
                    else:
                        # Fallback: "agent_a" -> "Aa", "agent1" -> "A1"
                        label = agent_id.replace("agent_", "A").replace("agent", "A")
                    vote_parts.append(f"{label} ({count})")
                subtitle = f"Votes: {', '.join(vote_parts)}"

            # Step 3: Switch timeline visibility and add final presentation banner
            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)
                timeline.switch_to_round(new_round)
                # Clear tool tracking to prevent tool_id collisions with previous round
                timeline.clear_tools_tracking()

                # Add "Final Presentation" banner with distinct styling and vote summary
                timeline.add_separator("FINAL PRESENTATION", round_number=new_round, subtitle=subtitle)
            except Exception as e:
                logger.error(f"AgentPanel.start_final_presentation timeline error: {e}")

            # Step 4: Reset per-round UI state
            self._hide_completion_footer()
            self._tool_handler.reset()
            self._batch_tracker.reset()
            self._reasoning_header_shown = False

            # Step 4: Clear context display for final presentation (will be updated if needed)
            self._restore_context_for_round(new_round)

            # Step 5: Update ribbon to show "F" for final presentation round
            try:
                app = self.app
                if hasattr(app, "_status_ribbon") and app._status_ribbon:
                    # Mark this as a final presentation round - shows "F" instead of "R{n}"
                    app._status_ribbon.set_round(self.agent_id, new_round, is_final_presentation=True)
            except Exception:
                pass

            logger.debug("AgentPanel.start_final_presentation: completed")

        def _update_ribbon_round(self, round_number: int, is_context_reset: bool = False) -> None:
            """Update the status ribbon with the current round info."""
            try:
                # Find the ribbon in the parent hierarchy
                app = self.app
                if hasattr(app, "_status_ribbon") and app._status_ribbon:
                    app._status_ribbon.set_round(self.agent_id, round_number, is_context_reset)
            except Exception:
                pass

        def switch_to_round(self, round_number: int) -> None:
            """Scroll to a specific round in the unified timeline.

            All round content stays visible in a continuous timeline.
            Selecting a round smoothly scrolls to that round's separator banner.

            Args:
                round_number: The round number to scroll to
            """
            self._viewed_round = round_number
            self._current_view = "round"

            # Use TimelineSection's scroll-to behavior
            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)
                timeline.switch_to_round(round_number)
            except Exception:
                pass

            # Update ribbon to show we're viewing this round
            try:
                app = self.app
                if hasattr(app, "_status_ribbon") and app._status_ribbon:
                    app._status_ribbon.set_viewed_round(self.agent_id, round_number)
            except Exception:
                pass

            # Restore context display for this round
            self._restore_context_for_round(round_number)

        def _restore_context_for_round(self, round_number: int) -> None:
            """Restore the context display for a specific round.

            When viewing historical rounds, show the context that was active during that round.
            """
            # Get context sources for this round (empty if not set)
            context_sources = self._context_by_round.get(round_number, [])
            self._context_sources = context_sources

            try:
                context_label = self.query_one(f"#{self._context_label_id}", Label)

                if context_sources:
                    # Format: "Context: A1.1, A2.1" (same as update_context_display)
                    short_labels = []
                    for label in context_sources[:3]:
                        if label.startswith("agent"):
                            short_labels.append("A" + label[5:])
                        else:
                            short_labels.append(label)

                    ctx_text = f"Context: {', '.join(short_labels)}"
                    if len(context_sources) > 3:
                        ctx_text += f" +{len(context_sources) - 3}"

                    context_label.update(ctx_text)
                    context_label.remove_class("hidden")
                else:
                    context_label.update("")
                    context_label.add_class("hidden")
            except Exception:
                pass

        def switch_to_final_answer(self) -> None:
            """Switch the view to display the final answer."""
            from .textual_widgets import FinalAnswerView

            self._current_view = "final_answer"

            # Hide timeline, show final answer view
            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)
                timeline.add_class("hidden")
            except Exception:
                pass

            # Show the final answer view and update its content
            try:
                final_view = self.query_one(f"#{self._final_answer_view_id}", FinalAnswerView)
                if self._final_answer_content:
                    final_view.set_content(self._final_answer_content)
                if self._final_answer_metadata:
                    final_view.set_metadata(self._final_answer_metadata)
                final_view.show()
            except Exception as e:
                tui_log(f"switch_to_final_answer error showing view: {e}")

            # Update ribbon
            try:
                app = self.app
                if hasattr(app, "_status_ribbon") and app._status_ribbon:
                    app._status_ribbon.set_viewing_final_answer(self.agent_id, True)
            except Exception:
                pass

        def switch_from_final_answer(self) -> None:
            """Switch back from final answer view to round view."""
            from .textual_widgets import FinalAnswerView

            self._current_view = "round"

            # Show timeline, hide final answer view
            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)
                timeline.remove_class("hidden")
            except Exception:
                pass

            try:
                final_view = self.query_one(f"#{self._final_answer_view_id}", FinalAnswerView)
                final_view.hide()
            except Exception:
                pass

            # Update ribbon
            try:
                app = self.app
                if hasattr(app, "_status_ribbon") and app._status_ribbon:
                    app._status_ribbon.set_viewing_final_answer(self.agent_id, False)
            except Exception:
                pass

        def set_final_answer(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
            """Store the final answer content for this agent.

            Args:
                content: The final answer text
                metadata: Optional metadata (votes, presenting agent, rounds, etc.)
            """
            self._final_answer_content = content
            self._final_answer_metadata = metadata or {}

            # Mark final answer as available in the ribbon
            try:
                app = self.app
                if hasattr(app, "_status_ribbon") and app._status_ribbon:
                    app._status_ribbon.set_final_answer_available(self.agent_id, True)
            except Exception:
                pass

        def get_current_round(self) -> int:
            """Get the current round number being received."""
            return self._current_round

        def get_viewed_round(self) -> int:
            """Get the round number currently being viewed."""
            return self._viewed_round

        def get_view_state(self) -> Tuple[str, Optional[int]]:
            """Get the current view state.

            Returns:
                Tuple of (view_type, round_number) where view_type is "round" or "final_answer"
            """
            if self._current_view == "final_answer":
                return ("final_answer", None)
            return ("round", self._viewed_round)

        # ========================================================================
        # End Phase 12.2
        # ========================================================================

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
                # Start timer to update elapsed time display
                self._start_header_timer()
            elif status == "streaming":
                self._update_loading_text("📝 Agent responding...")
                # Keep timer running during streaming
                if self._header_timer is None:
                    self._start_header_timer()
            elif status in ("completed", "error", "waiting"):
                self._start_time = None
                # Stop timer when done
                self._stop_header_timer()

            self.status = status
            self.remove_class("status-waiting", "status-working", "status-streaming", "status-completed", "status-error")
            self.add_class(f"status-{status}")

            # Update header labels
            self._refresh_header()

        def dim(self) -> None:
            """Dim this panel to indicate it's not the active/winner panel."""
            self.add_class("dimmed-panel")

        def undim(self) -> None:
            """Remove dimming from this panel."""
            self.remove_class("dimmed-panel")

        def _start_header_timer(self) -> None:
            """Start the header timer to update elapsed time."""
            if self._header_timer is None:
                self._header_timer = self.set_interval(1.0, self._update_header_timer)

        def _stop_header_timer(self) -> None:
            """Stop the header timer."""
            if self._header_timer is not None:
                self._header_timer.stop()
                self._header_timer = None

        def _update_header_timer(self) -> None:
            """Update the header with current elapsed time."""
            if self._start_time is None:
                self._stop_header_timer()
                return
            # Update header labels
            self._refresh_header()

        def update_timeout(self, timeout_state: Dict[str, Any]) -> None:
            """Update timeout display state.

            Args:
                timeout_state: Timeout state from orchestrator.get_agent_timeout_state()
            """
            self._timeout_state = timeout_state
            # Header refresh happens via the timer (_update_header_timer runs every second)

        def jump_to_latest(self):
            """Scroll to latest entry if supported."""
            try:
                self.content_log.scroll_end(animate=False)
            except Exception:
                try:
                    self.content_log.scroll_end()
                except Exception:
                    pass

        def add_hook_to_tool(self, tool_call_id: Optional[str], hook_info: Dict[str, Any]):
            """Route hook execution info to the TimelineSection's tool card.

            Args:
                tool_call_id: The tool call ID to attach the hook to
                hook_info: Hook execution information dict
            """
            from massgen.logger_config import logger

            logger.info(
                f"[AgentPanel] add_hook_to_tool called: agent={self.agent_id}, " f"tool_call_id={tool_call_id}, hook={hook_info.get('hook_name')}",
            )
            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)
                logger.info(f"[AgentPanel] Found timeline section: {timeline}")
                timeline.add_hook_to_tool(tool_call_id, hook_info)
            except Exception as e:
                logger.error(f"[AgentPanel] add_hook_to_tool failed: {e}")
                pass  # Timeline section not found or not available

        def _header_text_left(self) -> str:
            """Compose left side of header: agent info, backend, status."""
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

            # Add timeout countdown if active
            if self._timeout_state and self.status in ("working", "streaming"):
                timeout_text = self._format_timeout_display()
                if timeout_text:
                    parts.append(timeout_text)

            # Status in brackets
            parts.append(f"  [{self.status}]")

            return " ".join(parts)

        def _format_bg_badge(self) -> str:
            """Format background tasks badge text."""
            bg_count = self._get_background_tools_count()
            if bg_count > 0:
                return f"⚙️ {bg_count} bg"
            return ""

        def _format_tasks_badge(self) -> str:
            """Format task plan badge text.

            Note: Disabled - task info now shown in collapsible TaskPlanCard.
            """
            return ""

        def _header_text_right(self) -> str:
            """Compose right side of header (for compatibility)."""
            parts = []
            bg_badge = self._format_bg_badge()
            if bg_badge:
                parts.append(bg_badge)
            tasks_badge = self._format_tasks_badge()
            if tasks_badge:
                parts.append(tasks_badge)
            return "  ".join(parts)

        def _get_background_tools_count(self) -> int:
            """Get count of background/async operations for this agent."""
            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)
                return timeline.get_background_tools_count()
            except Exception:
                return 0

        def _get_background_tools(self) -> list:
            """Get list of background/async operations for this agent."""
            try:
                timeline = self.query_one(f"#{self._timeline_section_id}", TimelineSection)
                return timeline.get_background_tools()
            except Exception:
                return []

        def _header_text(self) -> str:
            """Compose full header text (for compatibility)."""
            left = self._header_text_left()
            right = self._header_text_right()
            if right:
                return f"{left}  {right}"
            return left

        def _format_task_plan_header(self) -> Optional[str]:
            """Format task plan summary for header display.

            Returns:
                Formatted task plan string or None if no active plan.
            """
            if not self._active_task_plan_tasks:
                return None

            total = len(self._active_task_plan_tasks)
            # Count both "completed" and "verified" as done
            completed = sum(1 for t in self._active_task_plan_tasks if t.get("status") in ("completed", "verified"))
            in_progress = sum(1 for t in self._active_task_plan_tasks if t.get("status") == "in_progress")

            # Format: "Tasks: 3/9" or "Tasks: 3/9 ●2" if tasks in progress
            task_text = f"Tasks: {completed}/{total}"
            if in_progress > 0:
                task_text += f" ●{in_progress}"

            return task_text

        def _format_timeout_display(self) -> Optional[str]:
            """Format timeout countdown for display in header.

            Returns:
                Formatted timeout string or None if no timeout active.
            """
            if not self._timeout_state:
                return None

            active_timeout = self._timeout_state.get("active_timeout")
            if not active_timeout:
                return None

            round_start_time = self._timeout_state.get("round_start_time")
            grace_seconds = self._timeout_state.get("grace_seconds", 0)
            soft_timeout_fired = self._timeout_state.get("soft_timeout_fired", False)

            if round_start_time is None:
                return None

            # Calculate remaining time locally for smooth 1-second updates
            elapsed = time.time() - round_start_time
            remaining_soft = max(0, active_timeout - elapsed)
            remaining_hard = max(0, active_timeout + grace_seconds - elapsed)
            is_hard_blocked = remaining_hard == 0

            # Get round number (0 = initial answer, 1+ = voting rounds)
            round_num = self._timeout_state.get("round_number", 0)

            # Format time as M:SS
            def fmt_time(secs: float) -> str:
                mins = int(secs // 60)
                s = int(secs % 60)
                return f"{mins}:{s:02d}"

            # Format the limit time
            limit_str = fmt_time(active_timeout)

            if is_hard_blocked:
                # Hard timeout active - tools are blocked
                return f"| [bold red]🚫 BLOCKED - round {round_num} limit was {limit_str}[/bold red]"
            elif soft_timeout_fired:
                # In grace period - show remaining time until hard block
                return f"| [bold yellow]⚠️ Round {round_num} grace: {fmt_time(remaining_hard)} left[/bold yellow]"
            elif remaining_soft <= 60:
                # Less than 1 minute - show warning in yellow
                return f"| [yellow]⏰ Round {round_num}: {fmt_time(remaining_soft)} / {limit_str}[/yellow]"
            else:
                # Normal countdown - show remaining / limit
                return f"| [dim]Round {round_num}: {fmt_time(remaining_soft)} / {limit_str}[/dim]"

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

    # =============================================================================
    # Modal classes have been extracted to massgen/frontend/displays/textual/widgets/modals/
    # They are now imported at module level:
    # - KeyboardShortcutsModal, MCPStatusModal
    # - AnswerBrowserModal, TimelineModal, BrowserTabsModal, WorkspaceBrowserModal
    # - VoteResultsModal, OrchestratorEventsModal, CoordinationTableModal, AgentSelectorModal
    # - SystemStatusModal, TextContentModal, CostBreakdownModal, MetricsModal
    # - ContextModal, ConversationHistoryModal, TurnDetailModal
    # - BroadcastPromptModal, StructuredBroadcastPromptModal
    # - WorkspaceFilesModal, FileInspectionModal
    # - AgentOutputModal
    # =============================================================================

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
        """Live view of the winning agent's presentation stream with action buttons.

        Layout principle: User sees everything they need at a glance without scrolling.
        - Fixed header with winner info and status
        - Scrollable content area for the full answer
        - Fixed footer with action buttons and follow-up input
        """

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
            # Fixed header section
            with Vertical(id="final_stream_header"):
                yield self.agent_label
            # Scrollable content area - takes remaining space
            with VerticalScroll(id="final_stream_content"):
                yield self.log_view
                yield self.current_line_label
            # Fixed footer section with buttons and follow-up input
            with Vertical(id="final_stream_footer", classes="hidden"):
                with Horizontal(id="final_stream_buttons"):
                    yield Button("Copy", id="final_copy_button", classes="action-primary")
                    yield Button("Workspace", id="final_workspace_button")
                yield Label("Ask a follow-up question:", id="followup_label")
                yield Input(placeholder="Continue the conversation...", id="followup_input")

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

            # Hide footer during streaming (will show when complete)
            try:
                self.query_one("#final_stream_footer").add_class("hidden")
            except Exception:
                pass

            # Hide the main input area when final answer is displayed (webui parity)
            try:
                input_area = self.app.query_one("#input_area")
                input_area.add_class("hidden")
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

            # Show footer with buttons and follow-up input
            try:
                self.query_one("#final_stream_footer").remove_class("hidden")
                # Focus the follow-up input
                followup_input = self.query_one("#followup_input", Input)
                followup_input.focus()
            except Exception:
                pass

        def on_button_pressed(self, event: Button.Pressed) -> None:
            """Handle action button presses."""
            if event.button.id == "final_copy_button":
                self._copy_to_clipboard()
            elif event.button.id == "final_workspace_button":
                self._open_workspace()

        @on(Input.Submitted, "#followup_input")
        def on_followup_submitted(self, event: Input.Submitted) -> None:
            """Handle follow-up question submission."""
            question = event.value.strip()
            if not question:
                return

            # Clear the input
            event.input.value = ""

            # Hide the final stream panel and show main input
            self.styles.display = "none"
            self.remove_class("winner-complete")

            # Show the main input area again
            try:
                input_area = self.app.query_one("#input_area")
                input_area.remove_class("hidden")
            except Exception:
                pass

            # Submit the follow-up question through the app
            if hasattr(self.app, "_submit_followup_question"):
                self.app._submit_followup_question(question)
            elif self.coordination_display:
                # Fallback: use the question callback if available
                try:
                    self.app.call_later(
                        lambda: self.coordination_display._handle_question_submit(question),
                    )
                except Exception as e:
                    self.app.notify(f"Failed to submit follow-up: {e}", severity="error")

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
