# -*- coding: utf-8 -*-
"""
Content Handlers for MassGen TUI.

Type-specific processing logic for different content types.
Each handler processes normalized content and returns display-ready data.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from .content_normalizer import NormalizedContent


@dataclass
class ToolDisplayData:
    """Data for displaying a tool call."""

    tool_id: str
    tool_name: str
    display_name: str
    tool_type: str
    category: str
    icon: str
    color: str
    status: str  # running, success, error
    start_time: datetime
    end_time: Optional[datetime] = None
    args_summary: Optional[str] = None  # Truncated for card display
    args_full: Optional[str] = None  # Full args for modal
    result_summary: Optional[str] = None  # Truncated for card display
    result_full: Optional[str] = None  # Full result for modal
    error: Optional[str] = None
    elapsed_seconds: Optional[float] = None


@dataclass
class ToolState:
    """Internal state for tracking a pending tool."""

    tool_id: str
    tool_name: str
    display_name: str
    tool_type: str
    category: str
    icon: str
    color: str
    start_time: datetime
    args_full: Optional[str] = None  # Store full args when they arrive


# Tool categories with icons and colors (same as tool_card.py)
TOOL_CATEGORIES = {
    "filesystem": {
        "icon": "📁",
        "color": "#4ec9b0",
        "patterns": [
            "read_file",
            "write_file",
            "list_directory",
            "create_directory",
            "delete_file",
            "move_file",
            "copy_file",
            "file_exists",
            "get_file_info",
            "read_multiple_files",
            "edit_file",
            "directory_tree",
            "search_files",
            "find_files",
        ],
    },
    "web": {
        "icon": "🌐",
        "color": "#569cd6",
        "patterns": [
            "web_search",
            "search_web",
            "google_search",
            "fetch_url",
            "http_request",
            "browse",
            "scrape",
            "download",
        ],
    },
    "code": {
        "icon": "💻",
        "color": "#dcdcaa",
        "patterns": [
            "execute_command",
            "run_code",
            "bash",
            "python",
            "shell",
            "terminal",
            "exec",
            "run_script",
            "execute",
        ],
    },
    "database": {
        "icon": "🗄️",
        "color": "#c586c0",
        "patterns": [
            "query",
            "sql",
            "database",
            "db_",
            "select",
            "insert",
            "update",
            "delete_record",
        ],
    },
    "git": {
        "icon": "📦",
        "color": "#f14e32",
        "patterns": [
            "git_",
            "commit",
            "push",
            "pull",
            "clone",
            "branch",
            "merge",
            "checkout",
            "diff",
            "log",
            "status",
        ],
    },
    "api": {
        "icon": "🔌",
        "color": "#ce9178",
        "patterns": [
            "api_",
            "request",
            "post",
            "get",
            "put",
            "patch",
            "rest",
            "graphql",
            "endpoint",
        ],
    },
    "ai": {
        "icon": "🤖",
        "color": "#9cdcfe",
        "patterns": [
            "generate",
            "complete",
            "chat",
            "embed",
            "model",
            "inference",
            "predict",
            "classify",
        ],
    },
    "memory": {
        "icon": "🧠",
        "color": "#b5cea8",
        "patterns": [
            "memory",
            "remember",
            "recall",
            "store",
            "retrieve",
            "knowledge",
            "context",
        ],
    },
}


def get_tool_category(tool_name: str) -> Dict[str, str]:
    """Get category info for a tool name."""
    tool_lower = tool_name.lower()

    # Handle MCP tools (format: mcp__server__tool)
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__")
        if len(parts) >= 3:
            tool_lower = parts[-1].lower()

    # Check against category patterns
    for category_name, info in TOOL_CATEGORIES.items():
        for pattern in info["patterns"]:
            if pattern in tool_lower:
                return {
                    "icon": info["icon"],
                    "color": info["color"],
                    "category": category_name,
                }

    # Default to generic tool
    return {"icon": "🔧", "color": "#858585", "category": "tool"}


def format_tool_display_name(tool_name: str) -> str:
    """Format tool name for display."""
    # Handle MCP tools: mcp__server__tool -> server/tool
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__")
        if len(parts) >= 3:
            return f"{parts[1]}/{parts[2]}"
        elif len(parts) == 2:
            return parts[1]

    # Handle snake_case
    return tool_name.replace("_", " ").title()


def summarize_args(args: Dict[str, Any], max_len: int = 80) -> str:
    """Summarize tool arguments for display."""
    if not args:
        return ""

    parts = []
    for key, value in args.items():
        if isinstance(value, str):
            if len(value) > 30:
                value = value[:27] + "..."
            parts.append(f"{key}: {value}")
        elif isinstance(value, (int, float, bool)):
            parts.append(f"{key}: {value}")
        elif isinstance(value, (list, dict)):
            parts.append(f"{key}: [{type(value).__name__}]")

    result = ", ".join(parts)
    if len(result) > max_len:
        result = result[: max_len - 3] + "..."
    return result


def summarize_result(result: str, max_len: int = 100) -> str:
    """Summarize tool result for display."""
    if not result:
        return ""

    # Count lines
    lines = result.split("\n")
    line_count = len(lines)

    # Get first meaningful line
    first_line = ""
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("{") and not stripped.startswith("["):
            first_line = stripped
            break

    if not first_line:
        first_line = lines[0].strip() if lines else ""

    # Truncate if needed
    if len(first_line) > max_len:
        first_line = first_line[: max_len - 3] + "..."

    # Add line count indicator
    if line_count > 1:
        return f"{first_line} [{line_count} lines]"
    return first_line


class BaseContentHandler(ABC):
    """Base class for content handlers."""

    @abstractmethod
    def process(self, normalized: NormalizedContent) -> Any:
        """Process normalized content.

        Args:
            normalized: Normalized content from ContentNormalizer

        Returns:
            Handler-specific result, or None to filter out
        """


class ToolContentHandler(BaseContentHandler):
    """Handler for tool-related content.

    Tracks pending tools and matches completions to starts.
    """

    def __init__(self):
        self._pending_tools: Dict[str, ToolState] = {}
        self._tool_counter = 0
        self._completed_tools: set = set()  # Track completed tool IDs to avoid duplicates

    def process(self, normalized: NormalizedContent) -> Optional[ToolDisplayData]:
        """Process tool content and return display data."""
        if not normalized.tool_metadata:
            return None

        meta = normalized.tool_metadata
        event = meta.event

        if event == "start":
            return self._handle_start(meta)
        elif event == "args":
            return self._handle_args(meta)
        elif event == "complete":
            return self._handle_complete(meta, normalized.cleaned_content)
        elif event == "failed":
            return self._handle_failed(meta, normalized.cleaned_content)
        elif event == "info":
            return self._handle_info(meta, normalized.cleaned_content)

        return None

    def _normalize_tool_name(self, name: str) -> str:
        """Normalize tool name for matching.

        Handles variations like:
        - mcp__filesystem__write_file
        - filesystem/write_file
        - write_file
        """
        # Extract the actual tool name from various formats
        if "__" in name:
            # MCP format: mcp__server__tool
            parts = name.split("__")
            return parts[-1].lower()
        elif "/" in name:
            # Display format: server/tool
            parts = name.split("/")
            return parts[-1].lower()
        return name.lower()

    def _handle_start(self, meta) -> Optional[ToolDisplayData]:
        """Handle tool start event."""
        normalized_name = self._normalize_tool_name(meta.tool_name)

        # Check if we already have a pending tool with this name (avoid duplicates)
        if normalized_name in self._pending_tools:
            return None  # Skip duplicate start

        self._tool_counter += 1
        tool_id = f"tool_{self._tool_counter}"

        # Get category info
        category_info = get_tool_category(meta.tool_name)
        display_name = format_tool_display_name(meta.tool_name)

        # Create pending state using normalized name as key
        state = ToolState(
            tool_id=tool_id,
            tool_name=meta.tool_name,
            display_name=display_name,
            tool_type=meta.tool_type,
            category=category_info["category"],
            icon=category_info["icon"],
            color=category_info["color"],
            start_time=datetime.now(),
        )
        self._pending_tools[normalized_name] = state

        # Extract args summary if available
        args_summary = None
        if meta.args and "summary" in meta.args:
            args_summary = meta.args["summary"]

        return ToolDisplayData(
            tool_id=tool_id,
            tool_name=meta.tool_name,
            display_name=display_name,
            tool_type=meta.tool_type,
            category=category_info["category"],
            icon=category_info["icon"],
            color=category_info["color"],
            status="running",
            start_time=state.start_time,
            args_summary=args_summary,
        )

    def _handle_args(self, meta) -> Optional[ToolDisplayData]:
        """Handle tool args event - update existing tool with args."""
        normalized_name = self._normalize_tool_name(meta.tool_name)

        # Find the pending tool
        state = self._pending_tools.get(normalized_name)
        if not state:
            return None  # No matching tool to update

        # Extract full args and create summary
        args_full = None
        args_summary = None
        if meta.args and "summary" in meta.args:
            args_full = meta.args["summary"]  # This is actually the full args from normalizer
            # Create truncated summary for card display
            if len(args_full) > 80:
                args_summary = args_full[:77] + "..."
            else:
                args_summary = args_full

        if not args_full:
            return None

        # Store full args in state for later use
        state.args_full = args_full

        # Return update data with args
        return ToolDisplayData(
            tool_id=state.tool_id,
            tool_name=state.tool_name,
            display_name=state.display_name,
            tool_type=state.tool_type,
            category=state.category,
            icon=state.icon,
            color=state.color,
            status="running",  # Still running
            start_time=state.start_time,
            args_summary=args_summary,
            args_full=args_full,
        )

    def _handle_complete(self, meta, content: str) -> Optional[ToolDisplayData]:
        """Handle tool complete event."""
        normalized_name = self._normalize_tool_name(meta.tool_name)

        # Find the pending tool using normalized name
        state = self._pending_tools.pop(normalized_name, None)

        if not state:
            # No matching start - skip to avoid orphan completions creating cards
            # This happens when completion comes without a start (shouldn't happen normally)
            return None

        # Check if we already completed this tool (avoid duplicate completions)
        if state.tool_id in self._completed_tools:
            return None
        self._completed_tools.add(state.tool_id)

        end_time = datetime.now()
        elapsed = (end_time - state.start_time).total_seconds()

        return ToolDisplayData(
            tool_id=state.tool_id,
            tool_name=state.tool_name,
            display_name=state.display_name,
            tool_type=state.tool_type,
            category=state.category,
            icon=state.icon,
            color=state.color,
            status="success",
            start_time=state.start_time,
            end_time=end_time,
            elapsed_seconds=elapsed,
            args_full=state.args_full,  # Pass through stored args
            result_summary=summarize_result(content),
            result_full=content,  # Store full result for modal
        )

    def _handle_failed(self, meta, content: str) -> Optional[ToolDisplayData]:
        """Handle tool failed event."""
        normalized_name = self._normalize_tool_name(meta.tool_name)
        state = self._pending_tools.pop(normalized_name, None)

        if not state:
            # No matching start - skip
            return None

        # Check if already completed
        if state.tool_id in self._completed_tools:
            return None
        self._completed_tools.add(state.tool_id)

        end_time = datetime.now()
        elapsed = (end_time - state.start_time).total_seconds()

        return ToolDisplayData(
            tool_id=state.tool_id,
            tool_name=state.tool_name,
            display_name=state.display_name,
            tool_type=state.tool_type,
            category=state.category,
            icon=state.icon,
            color=state.color,
            status="error",
            start_time=state.start_time,
            end_time=end_time,
            elapsed_seconds=elapsed,
            args_full=state.args_full,  # Pass through stored args
            error=content if content else "Unknown error",  # Store full error
        )

    def _handle_info(self, meta, content: str) -> Optional[ToolDisplayData]:
        """Handle tool info event (registered tools, etc.)."""
        # These are informational, return None to not display as a card
        # The section header will show the count
        return None

    def get_pending_count(self) -> int:
        """Get count of pending (running) tools."""
        return len(self._pending_tools)

    def reset(self):
        """Reset handler state (for new session)."""
        self._pending_tools.clear()
        self._completed_tools.clear()
        self._tool_counter = 0


class ThinkingContentHandler(BaseContentHandler):
    """Handler for thinking/reasoning content.

    Filters JSON noise and cleans up streaming content.
    """

    # Additional patterns to filter beyond what normalizer catches
    EXTRA_FILTER_PATTERNS = [
        r"^\s*[\{\}]\s*$",  # Lone braces
        r"^\s*[\[\]]\s*$",  # Lone brackets
        r'^\s*"[^"]*"\s*:\s*$',  # JSON keys
        r"^\s*,\s*$",  # Lone commas
    ]

    def __init__(self):
        self._compiled_filters = [re.compile(p) for p in self.EXTRA_FILTER_PATTERNS]

    def process(self, normalized: NormalizedContent) -> Optional[str]:
        """Process thinking content and return cleaned text."""
        if not normalized.should_display:
            return None

        content = normalized.cleaned_content

        # Additional filtering
        for pattern in self._compiled_filters:
            if pattern.match(content):
                return None

        # Clean up bullet points if they're lone bullets
        if content.strip() in ("•", "-", "*", "·"):
            return None

        return content


class StatusContentHandler(BaseContentHandler):
    """Handler for status content.

    Extracts status type and returns minimal display data.
    """

    STATUS_TYPES = {
        "connected": ("●", "green", "Connected"),
        "disconnected": ("○", "red", "Disconnected"),
        "working": ("⟳", "yellow", "Working"),
        "streaming": ("▶", "cyan", "Streaming"),
        "completed": ("✓", "green", "Complete"),
        "error": ("✗", "red", "Error"),
        "waiting": ("○", "dim", "Waiting"),
    }

    def process(self, normalized: NormalizedContent) -> Optional[Dict[str, str]]:
        """Process status content and return display info."""
        content_lower = normalized.cleaned_content.lower()

        # Detect status type
        status_type = "unknown"
        if "completed" in content_lower or "complete" in content_lower:
            status_type = "completed"
        elif "working" in content_lower:
            status_type = "working"
        elif "streaming" in content_lower:
            status_type = "streaming"
        elif "error" in content_lower or "failed" in content_lower:
            status_type = "error"
        elif "connected" in content_lower:
            status_type = "connected"
        elif "waiting" in content_lower:
            status_type = "waiting"

        if status_type in self.STATUS_TYPES:
            icon, color, label = self.STATUS_TYPES[status_type]
            return {
                "type": status_type,
                "icon": icon,
                "color": color,
                "label": label,
            }

        return None


class PresentationContentHandler(BaseContentHandler):
    """Handler for final presentation content."""

    def process(self, normalized: NormalizedContent) -> Optional[str]:
        """Process presentation content."""
        if not normalized.should_display:
            return None

        content = normalized.cleaned_content

        # Filter "Providing answer:" prefix
        if content.startswith("Providing answer:"):
            return None

        return content
