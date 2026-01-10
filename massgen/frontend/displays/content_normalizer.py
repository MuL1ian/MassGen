# -*- coding: utf-8 -*-
"""
Content Normalizer for MassGen TUI.

Provides a single entry point for normalizing all content before display.
Strips backend emojis, detects content types, and extracts metadata.

Design Philosophy:
- Minimal filtering - only remove obvious noise (JSON fragments, empty lines)
- Keep internal reasoning visible - it's valuable for understanding agent coordination
- Categorize content for organized display (tools, thinking, status, presentation)
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional

# Content types recognized by the display system
ContentType = Literal[
    "tool_start",
    "tool_complete",
    "tool_failed",
    "tool_info",
    "thinking",
    "status",
    "presentation",
    "injection",
    "reminder",
    "text",
    "coordination",  # New type for voting/coordination content
]

# Patterns for stripping backend prefixes
STRIP_PATTERNS = [
    # Emojis at start of line
    (r"^[\U0001F300-\U0001F9FF\u2600-\u26FF\u2700-\u27BF]+\s*", ""),
    # Common prefixes
    (r"^\[MCP\]\s*", ""),
    (r"^\[Custom Tool\]\s*", ""),
    (r"^\[Custom Tools\]\s*", ""),
    (r"^\[INJECTION\]\s*", ""),
    (r"^\[REMINDER\]\s*", ""),
    (r"^MCP:\s*", ""),
    (r"^Custom Tool:\s*", ""),
    # Double emoji patterns
    (r"^[📊📁🔧✅❌⏳📥💡🎤🧠📋🔄⚡🌐💻🗄️📦🔌🤖]\s*[📊📁🔧✅❌⏳📥💡🎤🧠📋🔄⚡🌐💻🗄️📦🔌🤖]\s*", ""),
]

# Compiled regex patterns for performance
COMPILED_STRIP_PATTERNS = [(re.compile(p), r) for p, r in STRIP_PATTERNS]

# Patterns for detecting tool events
TOOL_START_PATTERNS = [
    r"Calling (?:tool )?['\"]?([^\s'\"\.]+)['\"]?",
    r"Tool call: (\w+)",
    r"Executing (\w+)",
    r"Starting tool[:\s]+(\w+)",
]

# Pattern to match "Arguments for Calling tool_name: {args}"
TOOL_ARGS_PATTERNS = [
    r"Arguments for Calling ([^\s:]+):\s*(.+)",
]

TOOL_COMPLETE_PATTERNS = [
    r"Tool ['\"]?(\w+)['\"]? (?:completed|finished|succeeded)",
    r"(\w+) completed",
    r"Result from (\w+)",
    r"Results for Calling ([^\s:]+):",  # MCP result pattern
]

TOOL_FAILED_PATTERNS = [
    r"Tool ['\"]?(\w+)['\"]? failed",
    r"Error (?:in|from) (\w+)",
    r"(\w+) failed",
]

TOOL_INFO_PATTERNS = [
    r"Registered (\d+) tools?",
    r"Connected to (\d+) (?:MCP )?servers?",
    r"Tools initialized",
]

# Minimal JSON noise patterns - just obvious fragments that are never useful
JSON_NOISE_PATTERNS = [
    r"^\s*\{\s*\}\s*$",  # Empty object {}
    r"^\s*\[\s*\]\s*$",  # Empty array []
    r"^\s*[\{\}]\s*$",  # Just { or }
    r"^\s*[\[\]]\s*$",  # Just [ or ]
    r"^\s*,\s*$",  # Just comma
    r'^\s*"\s*$',  # Just quote
    r"^\s*```\s*$",  # Empty code fence
    r"^\s*```json\s*$",  # JSON code fence opener
]

COMPILED_JSON_NOISE = [re.compile(p) for p in JSON_NOISE_PATTERNS]

# Patterns to detect coordination/voting content (for categorization, not filtering)
COORDINATION_PATTERNS = [
    r"Voting for \[",
    r"Vote for \[",
    r"I will vote for",
    r"I'll vote for",
    r"Agent \d+ provides",
    r"agents? (?:have|has) (?:all )?correctly",
    r"existing answers",
    r"current answers",
    r"restarting due to new answers",
]

COMPILED_COORDINATION_PATTERNS = [re.compile(p, re.IGNORECASE) for p in COORDINATION_PATTERNS]


@dataclass
class ToolMetadata:
    """Metadata extracted from tool events."""

    tool_name: str
    tool_type: str = "unknown"  # mcp, custom, etc.
    event: str = "unknown"  # start, complete, failed
    args: Optional[Dict[str, Any]] = None
    result: Optional[str] = None
    error: Optional[str] = None
    tool_count: Optional[int] = None  # For "Registered X tools" messages


@dataclass
class NormalizedContent:
    """Result of normalizing content."""

    content_type: ContentType
    cleaned_content: str
    original: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tool_metadata: Optional[ToolMetadata] = None
    should_display: bool = True  # Set to False to filter out
    is_coordination: bool = False  # Flag for coordination content (for grouping)


class ContentNormalizer:
    """Normalizes content from orchestrator before display.

    This is the single entry point for all content processing.
    It strips backend prefixes, detects content types, and extracts metadata.
    """

    @staticmethod
    def strip_prefixes(content: str) -> str:
        """Strip backend-added prefixes and emojis from content."""
        result = content
        for pattern, replacement in COMPILED_STRIP_PATTERNS:
            result = pattern.sub(replacement, result)
        return result.strip()

    @staticmethod
    def _extract_args_from_content(content: str, tool_name: str) -> Optional[str]:
        """Try to extract args summary from tool content."""
        patterns = [
            rf"{re.escape(tool_name)}\s*(?:with\s*)?\{{([^}}]+)\}}",  # tool {args}
            rf"{re.escape(tool_name)}\s*\(([^)]+)\)",  # tool(args)
            rf"{re.escape(tool_name)}[:\s]+(.+?)(?:\s*$|\s*\n)",  # tool: args
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                args_str = match.group(1).strip()
                if args_str and len(args_str) > 2:
                    return args_str

        # Try to find key:value pairs after tool name
        idx = content.lower().find(tool_name.lower())
        if idx >= 0:
            after = content[idx + len(tool_name) :].strip()
            kv_match = re.search(r'(\w+)[=:]\s*["\']?([^"\'\s,]+)', after)
            if kv_match:
                return f"{kv_match.group(1)}={kv_match.group(2)}"

        return None

    @staticmethod
    def detect_tool_event(content: str) -> Optional[ToolMetadata]:
        """Detect if content is a tool event and extract metadata."""
        # Check for tool args message FIRST
        for pattern in TOOL_ARGS_PATTERNS:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                tool_name = match.group(1) if len(match.groups()) >= 1 else "unknown"
                args_str = match.group(2).strip() if len(match.groups()) >= 2 else ""
                return ToolMetadata(
                    tool_name=tool_name,
                    event="args",
                    args={"summary": args_str} if args_str else None,
                )

        # Check for tool start
        for pattern in TOOL_START_PATTERNS:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                tool_name = match.group(1) if match.groups() else "unknown"
                tool_type = "mcp" if "mcp__" in content.lower() else "custom"
                args_str = ContentNormalizer._extract_args_from_content(content, tool_name)
                return ToolMetadata(
                    tool_name=tool_name,
                    tool_type=tool_type,
                    event="start",
                    args={"summary": args_str} if args_str else None,
                )

        # Check for tool complete
        for pattern in TOOL_COMPLETE_PATTERNS:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                tool_name = match.group(1) if match.groups() else "unknown"
                return ToolMetadata(tool_name=tool_name, event="complete")

        # Check for tool failed
        for pattern in TOOL_FAILED_PATTERNS:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                tool_name = match.group(1) if match.groups() else "unknown"
                return ToolMetadata(tool_name=tool_name, event="failed")

        # Check for tool info
        for pattern in TOOL_INFO_PATTERNS:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                count = int(match.group(1)) if match.groups() else None
                return ToolMetadata(tool_name="system", event="info", tool_count=count)

        return None

    @staticmethod
    def is_json_noise(content: str) -> bool:
        """Check if content is pure JSON noise that should be filtered."""
        content_stripped = content.strip()

        # Empty or very short
        if len(content_stripped) < 2:
            return True

        # Check against noise patterns
        for pattern in COMPILED_JSON_NOISE:
            if pattern.match(content_stripped):
                return True

        return False

    @staticmethod
    def is_coordination_content(content: str) -> bool:
        """Check if content is coordination/voting related (for categorization)."""
        for pattern in COMPILED_COORDINATION_PATTERNS:
            if pattern.search(content):
                return True
        return False

    @staticmethod
    def clean_content(content: str) -> str:
        """Light cleaning - remove only obvious noise, preserve meaningful content."""
        lines = content.split("\n")
        cleaned_lines = []

        for line in lines:
            stripped = line.strip()

            # Skip empty lines at the start
            if not stripped and not cleaned_lines:
                continue

            # Skip pure JSON noise
            if ContentNormalizer.is_json_noise(stripped):
                continue

            cleaned_lines.append(line)

        # Join and clean up excessive blank lines
        result = "\n".join(cleaned_lines)
        result = re.sub(r"\n{3,}", "\n\n", result)

        return result.strip()

    @staticmethod
    def detect_content_type(content: str, raw_type: str) -> ContentType:
        """Detect the actual content type based on content analysis."""
        content_lower = content.lower()

        # Explicit type mappings
        if raw_type == "tool":
            if "calling" in content_lower or "executing" in content_lower:
                return "tool_start"
            elif "completed" in content_lower or "finished" in content_lower:
                return "tool_complete"
            elif "failed" in content_lower or "error" in content_lower:
                return "tool_failed"
            elif "registered" in content_lower or "connected" in content_lower:
                return "tool_info"
            return "tool_info"

        if raw_type == "status":
            return "status"

        if raw_type == "presentation":
            return "presentation"

        if raw_type == "thinking":
            return "thinking"

        # Auto-detect from content
        if "[INJECTION]" in content or "injection" in raw_type:
            return "injection"

        if "[REMINDER]" in content or "reminder" in raw_type:
            return "reminder"

        # Check if it looks like a tool event
        tool_meta = ContentNormalizer.detect_tool_event(content)
        if tool_meta:
            if tool_meta.event == "start":
                return "tool_start"
            elif tool_meta.event == "complete":
                return "tool_complete"
            elif tool_meta.event == "failed":
                return "tool_failed"
            elif tool_meta.event == "info":
                return "tool_info"

        return "text"

    @classmethod
    def normalize(cls, content: str, raw_type: str = "") -> NormalizedContent:
        """Normalize content for display.

        This is the main entry point. It:
        1. Strips backend prefixes and emojis
        2. Detects the actual content type
        3. Extracts metadata (for tools)
        4. Flags coordination content for grouping
        5. Applies minimal cleaning

        Args:
            content: Raw content from orchestrator
            raw_type: The content_type provided by orchestrator

        Returns:
            NormalizedContent with all processing applied
        """
        # Strip prefixes
        cleaned = cls.strip_prefixes(content)

        # Detect actual type
        content_type = cls.detect_content_type(content, raw_type)

        # Extract tool metadata if applicable
        tool_metadata = None
        if content_type.startswith("tool_"):
            tool_metadata = cls.detect_tool_event(content)

        # Check if this is coordination content (for grouping, not filtering)
        is_coordination = cls.is_coordination_content(content)

        # Determine if should display
        should_display = True

        # Only filter pure JSON noise
        if cls.is_json_noise(content):
            should_display = False

        # Apply light cleaning
        if should_display:
            cleaned = cls.clean_content(cleaned)

        # Filter if cleaned content is empty
        if not cleaned.strip():
            should_display = False

        return NormalizedContent(
            content_type=content_type,
            cleaned_content=cleaned,
            original=content,
            tool_metadata=tool_metadata,
            should_display=should_display,
            is_coordination=is_coordination,
        )
