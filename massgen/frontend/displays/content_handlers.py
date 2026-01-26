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

from .content_normalizer import ContentNormalizer, NormalizedContent


def get_mcp_server_name(tool_name: str) -> Optional[str]:
    """Extract MCP server name from mcp__server__tool format.

    Args:
        tool_name: The full tool name (e.g., "mcp__filesystem__write_file").

    Returns:
        Server name if this is an MCP tool (e.g., "filesystem"), None otherwise.
    """
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__")
        if len(parts) >= 2:
            return parts[1]
    return None


def get_mcp_tool_name(tool_name: str) -> Optional[str]:
    """Extract the actual tool name from mcp__server__tool format.

    Args:
        tool_name: The full tool name (e.g., "mcp__filesystem__write_file").

    Returns:
        Tool name if this is an MCP tool (e.g., "write_file"), None otherwise.
    """
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__")
        if len(parts) >= 3:
            return parts[2]
    return None


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
    status: str  # running, success, error, background
    start_time: datetime
    end_time: Optional[datetime] = None
    args_summary: Optional[str] = None  # Truncated for card display
    args_full: Optional[str] = None  # Full args for modal
    result_summary: Optional[str] = None  # Truncated for card display
    result_full: Optional[str] = None  # Full result for modal
    error: Optional[str] = None
    elapsed_seconds: Optional[float] = None
    async_id: Optional[str] = None  # ID for background operations (e.g., shell_id)


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
    tool_call_id: Optional[str] = None  # Unique ID for this tool call  # Store full args when they arrive


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
    "workspace": {
        "icon": "📝",
        "color": "#4fc1ff",
        "patterns": [
            "workspace",
            "new_answer",
            "vote",
            "answer",
            "coordination",
        ],
    },
    "human_input": {
        "icon": "💬",
        "color": "#d29922",  # Warning/gold color to match queued input banner
        "patterns": [
            "human_input",
            "user_input",
            "injected_input",
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

    # Strip injection markers that may appear in tool results
    result = ContentNormalizer.strip_injection_markers(result)

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
        self._deferred_args: Dict[str, str] = {}  # Queue for args arriving before tool start

    def process(self, normalized: NormalizedContent) -> Optional[ToolDisplayData]:
        """Process tool content and return display data."""
        if not normalized.tool_metadata:
            return None

        meta = normalized.tool_metadata
        event = meta.event
        # Get tool_call_id from metadata or normalized content
        tool_call_id = meta.tool_call_id or normalized.tool_call_id

        if event == "start":
            return self._handle_start(meta, tool_call_id)
        elif event == "args":
            return self._handle_args(meta, tool_call_id)
        elif event == "complete":
            return self._handle_complete(meta, normalized.cleaned_content, tool_call_id)
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

    def _shorten_paths_in_json(self, json_str: str, max_len: int) -> str:
        """Truncate JSON string, keeping path endings (filenames) visible.

        For tool arguments containing file paths, we want to show the filename
        at the end rather than truncating from the end and losing it.

        Args:
            json_str: The JSON string to truncate
            max_len: Maximum length for the result

        Returns:
            Truncated string with path endings preserved where possible
        """
        import re

        # Find long paths and shorten from beginning, keeping the filename visible
        def shorten_path(match: re.Match) -> str:
            path = match.group(1)
            if len(path) > 40:
                # Keep last 35 chars (usually the filename + some parent dirs)
                return f'"...{path[-35:]}"'
            return match.group(0)

        # Match quoted paths (starting with /)
        result = re.sub(r'"(/[^"]{40,})"', shorten_path, json_str)

        # If still too long, truncate from end
        if len(result) <= max_len:
            return result
        return result[: max_len - 3] + "..."

    def _detect_background_operation(
        self,
        tool_name: str,
        result_content: str,
    ) -> tuple[bool, Optional[str]]:
        """Detect if a tool result indicates a background/async operation.

        Background operations are tools that start a long-running process and
        return immediately with an ID to track the operation.

        Args:
            tool_name: Name of the tool.
            result_content: The result content from the tool.

        Returns:
            Tuple of (is_background, async_id).
            async_id is the identifier (e.g., shell_id) if found.
        """
        normalized_name = self._normalize_tool_name(tool_name)

        # Known background operation tools
        background_tools = {
            "start_background_shell",
            "start_shell",  # May also be async
        }

        if normalized_name not in background_tools:
            return False, None

        # Try to extract shell_id from result
        # Look for patterns like: shell_id: shell_abc123 or "shell_id": "shell_abc123"
        shell_id_match = re.search(
            r'["\']?shell_id["\']?\s*[:=]\s*["\']?(shell_[a-zA-Z0-9]+)["\']?',
            result_content,
        )
        if shell_id_match:
            return True, shell_id_match.group(1)

        # Also check for JSON-style response
        if '"shell_id"' in result_content or "'shell_id'" in result_content:
            return True, None

        # Tool name matches but no shell_id found - still mark as background
        # since the tool is designed for async operations
        return True, None

    def _handle_start(self, meta, tool_call_id: Optional[str] = None) -> Optional[ToolDisplayData]:
        """Handle tool start event."""
        normalized_name = self._normalize_tool_name(meta.tool_name)
        # Use tool_call_id as key if available, otherwise fall back to normalized name
        key = tool_call_id or normalized_name

        # Check if we already have a pending tool with this key (avoid duplicates)
        if key in self._pending_tools:
            return None  # Skip duplicate start

        self._tool_counter += 1
        tool_id = f"tool_{self._tool_counter}"

        # Get category info
        category_info = get_tool_category(meta.tool_name)
        display_name = format_tool_display_name(meta.tool_name)

        # Check for deferred args (args that arrived before tool start)
        # Try both tool_call_id and normalized_name for deferred args
        deferred_args = self._deferred_args.pop(key, None)
        if not deferred_args and tool_call_id:
            deferred_args = self._deferred_args.pop(normalized_name, None)

        # Create pending state using tool_call_id as key when available
        state = ToolState(
            tool_id=tool_id,
            tool_name=meta.tool_name,
            display_name=display_name,
            tool_type=meta.tool_type,
            category=category_info["category"],
            icon=category_info["icon"],
            color=category_info["color"],
            start_time=datetime.now(),
            args_full=deferred_args,  # Use deferred args if available
            tool_call_id=tool_call_id,
        )
        self._pending_tools[key] = state

        # Extract args summary if available (from meta or deferred)
        args_summary = None
        args_full = None
        if meta.args and "summary" in meta.args:
            args_full = meta.args["summary"]
            args_summary = args_full[:77] + "..." if len(args_full) > 80 else args_full
        elif deferred_args:
            args_full = deferred_args
            args_summary = deferred_args[:77] + "..." if len(deferred_args) > 80 else deferred_args

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
            args_full=args_full,
        )

    def _handle_args(self, meta, tool_call_id: Optional[str] = None) -> Optional[ToolDisplayData]:
        """Handle tool args event - update existing tool with args."""
        normalized_name = self._normalize_tool_name(meta.tool_name)
        # Use tool_call_id as key if available, otherwise fall back to normalized name
        key = tool_call_id or normalized_name

        # Extract full args and create summary
        args_full = None
        args_summary = None
        if meta.args and "summary" in meta.args:
            args_full = meta.args["summary"]  # This is actually the full args from normalizer
            # Create truncated summary for card display (path-aware)
            if len(args_full) > 80:
                args_summary = self._shorten_paths_in_json(args_full, 80)
            else:
                args_summary = args_full

        if not args_full:
            return None

        # Find the pending tool - try key first, then try other key format
        state = self._pending_tools.get(key)
        if not state and tool_call_id:
            # Fallback: try normalized name in case start came without tool_call_id
            state = self._pending_tools.get(normalized_name)

        if not state:
            # Args arrived before tool start - defer for later
            self._deferred_args[key] = args_full
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

    def _handle_complete(self, meta, content: str, tool_call_id: Optional[str] = None) -> Optional[ToolDisplayData]:
        """Handle tool complete event."""
        normalized_name = self._normalize_tool_name(meta.tool_name)
        # Use tool_call_id as key if available, otherwise fall back to normalized name
        key = tool_call_id or normalized_name

        # Find the pending tool using key
        state = self._pending_tools.pop(key, None)
        if not state and tool_call_id:
            # Fallback: try normalized name in case start came without tool_call_id
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

        # Use result from metadata if available (extracted from "Results for Calling..." pattern)
        # Otherwise fall back to cleaned content
        result_content = meta.result if meta.result else content
        cleaned_content = ContentNormalizer.strip_injection_markers(result_content) if result_content else ""

        # Fallback: if args weren't captured earlier, try to extract from content
        args_full = state.args_full
        if not args_full:
            # Try to find args in content (may have arrived inline with result)
            args_match = re.search(
                r"Arguments for Calling [^\s:]+:\s*(.+?)(?:Results for Calling|\Z)",
                content,
                re.IGNORECASE | re.DOTALL,
            )
            if args_match:
                args_full = args_match.group(1).strip()

        # Create args summary if we have args_full
        args_summary = None
        if args_full:
            args_summary = args_full[:77] + "..." if len(args_full) > 80 else args_full

        # Detect background/async operations
        # These are tools that start a long-running process and return immediately
        is_background, async_id = self._detect_background_operation(
            state.tool_name,
            cleaned_content,
        )

        return ToolDisplayData(
            tool_id=state.tool_id,
            tool_name=state.tool_name,
            display_name=state.display_name,
            tool_type=state.tool_type,
            category=state.category,
            icon=state.icon,
            color=state.color,
            status="background" if is_background else "success",
            start_time=state.start_time,
            end_time=None if is_background else end_time,  # No end time for background ops
            elapsed_seconds=None if is_background else elapsed,
            args_full=args_full,
            args_summary=args_summary,
            result_summary=summarize_result(cleaned_content),
            result_full=cleaned_content,  # Store cleaned result for modal
            async_id=async_id,
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

        # Fallback: if args weren't captured earlier, try to extract from content
        args_full = state.args_full
        if not args_full:
            args_match = re.search(
                r"Arguments for Calling [^\s:]+:\s*(.+?)(?:Results for Calling|Error|\Z)",
                content,
                re.IGNORECASE | re.DOTALL,
            )
            if args_match:
                args_full = args_match.group(1).strip()

        # Create args summary if we have args_full
        args_summary = None
        if args_full:
            args_summary = args_full[:77] + "..." if len(args_full) > 80 else args_full

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
            args_full=args_full,
            args_summary=args_summary,
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
        self._deferred_args.clear()
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

        # Filter "Providing answer:" prefix (may have emoji like 💡)
        if "Providing answer:" in content:
            return None

        return content


class ToolBatchTracker:
    """Tracks consecutive MCP tool calls for batching into tree views.

    Only batches when 2+ consecutive tools from the same server arrive.
    Single tools appear as normal ToolCallCard with fade-in animation.

    Flow:
    1. First MCP tool → show as normal ToolCallCard, track as "pending"
    2. Second consecutive tool from same server → convert to batch
    3. More tools from same server → add to batch
    4. Different server or non-MCP → finalize, start fresh
    """

    def __init__(self):
        self._current_server: Optional[str] = None
        self._current_batch_id: Optional[str] = None
        self._pending_tool_id: Optional[str] = None  # First tool, not yet batched
        self._batch_counter = 0
        self._batched_tool_ids: set = set()  # Track which tools are in batches
        self._content_since_last_tool: bool = False  # True if non-tool content arrived

    def mark_content_arrived(self) -> None:
        """Mark that non-tool content (thinking, text, status) has arrived.

        This is used to prevent batching tools that have content between them.
        Called whenever non-tool content is added to the timeline.
        """
        self._content_since_last_tool = True

    def process_tool(self, tool_data: ToolDisplayData) -> tuple[str, Optional[str], Optional[str], Optional[str]]:
        """Determine how to handle an incoming tool call.

        Returns:
            Tuple of (action, server_name, batch_id, pending_tool_id) where action is:
            - "standalone": Non-MCP tool, use regular ToolCallCard
            - "pending": First MCP tool, show as ToolCallCard but track for potential batch
            - "convert_to_batch": Second tool arrived - convert pending to batch
            - "add_to_batch": Add to existing batch
            - "update_standalone": Update a standalone/pending tool
            - "update_batch": Update existing tool in batch
        """
        # If content arrived since last tool, finalize batch and start fresh
        # This ensures chronological order is respected in the timeline
        if self._content_since_last_tool and tool_data.status == "running":
            self._finalize_pending()
            self._content_since_last_tool = False

        server_name = get_mcp_server_name(tool_data.tool_name)

        # Non-MCP tools get standalone treatment
        if server_name is None:
            self._finalize_pending()
            return ("standalone", None, None, None)

        # Check if this is an update (not "running")
        if tool_data.status != "running":
            if tool_data.tool_id in self._batched_tool_ids:
                return ("update_batch", server_name, self._current_batch_id, None)
            return ("update_standalone", server_name, None, None)

        # New tool starting (status == "running")

        # Already have an active batch for this server?
        if self._current_batch_id and self._current_server == server_name:
            self._batched_tool_ids.add(tool_data.tool_id)
            return ("add_to_batch", server_name, self._current_batch_id, None)

        # Have a pending tool from same server? → Convert to batch
        if self._pending_tool_id and self._current_server == server_name:
            self._batch_counter += 1
            self._current_batch_id = f"batch_{self._batch_counter}"
            pending_id = self._pending_tool_id
            self._batched_tool_ids.add(pending_id)
            self._batched_tool_ids.add(tool_data.tool_id)
            self._pending_tool_id = None
            return ("convert_to_batch", server_name, self._current_batch_id, pending_id)

        # Different server or first tool → finalize and track as pending
        self._finalize_pending()
        self._current_server = server_name
        self._pending_tool_id = tool_data.tool_id
        return ("pending", server_name, None, None)

    def _finalize_pending(self) -> None:
        """Finalize any pending tool (it stays as standalone)."""
        self._pending_tool_id = None
        self._current_server = None
        self._current_batch_id = None

    def finalize_current_batch(self) -> Optional[str]:
        """Called when non-tool content arrives to finalize tracking."""
        finalized_id = self._current_batch_id
        self._finalize_pending()
        return finalized_id

    def reset(self) -> None:
        """Reset the tracker state (e.g., for new round)."""
        self._current_server = None
        self._current_batch_id = None
        self._pending_tool_id = None
        self._batched_tool_ids.clear()  # Clear accumulated tool IDs to prevent memory growth
        self._content_since_last_tool = False

    @property
    def current_batch_id(self) -> Optional[str]:
        """Get the current batch ID if any."""
        return self._current_batch_id

    @property
    def current_server(self) -> Optional[str]:
        """Get the current server name if batching."""
        return self._current_server
