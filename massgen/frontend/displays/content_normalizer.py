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
    "tool_args",
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

# Patterns for stripping backend prefixes (applied at start of content)
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

# Patterns for stripping markers that can appear anywhere in content (not just start)
GLOBAL_STRIP_PATTERNS = [
    # Full injection block with === delimiters and content (multiline)
    # Matches: ===...===\n⚠️IMPORTANT: NEW ANSWER...\n===...===\n[UPDATE:...]...(until double newline or end)
    (
        r"={10,}\s*\n\s*⚠️?\s*IMPORTANT:\s*NEW ANSWER[^\n]*\n\s*={10,}\s*\n" r"(?:\[UPDATE:[^\]]*\][^\n]*\n(?:.*?\n)*?(?=\n\n|\Z))?",
        "",
    ),
    # Simpler injection block pattern (just the header and delimiter lines)
    (r"={10,}\s*\n\s*⚠️?\s*IMPORTANT:[^\n]*\n\s*={10,}\s*\n?", ""),
    # [UPDATE: ...] blocks that appear after injection headers
    (r"\[UPDATE:\s*[^\]]*\](?:\s*\([^)]*\))?:?\s*\n?", ""),
    # [INJECTION] marker with optional preceding backslash/whitespace
    (r"\\?\s*\[INJECTION\]\s*", " "),
    # [REMINDER] marker anywhere
    (r"\\?\s*\[REMINDER\]\s*", " "),
    # [MCP Tool] and [Custom Tool] labels from backend tool execution (with optional preceding emoji)
    (r"\\?\s*[🔧✅]?\s*\[(MCP|Custom) Tool\]\s*", " "),
    # MCP: prefix anywhere (with optional preceding backslash)
    (r"\\?\s*MCP:\s*🐢?\s*", " "),
    # "Results for Calling mcp__tool_name:" prefix - strip verbose MCP result prefix
    (r"Results for Calling \S+:\s*", ""),
    # "mcp__tool_name completed" suffix - strip verbose MCP completion suffix
    (r"\s*✅?\s*mcp__\S+\s+completed\s*", ""),
]

COMPILED_GLOBAL_STRIP_PATTERNS = [(re.compile(p, re.DOTALL | re.MULTILINE), r) for p, r in GLOBAL_STRIP_PATTERNS]

# Compiled regex patterns for performance
COMPILED_STRIP_PATTERNS = [(re.compile(p), r) for p, r in STRIP_PATTERNS]

# Patterns for detecting tool events
# NOTE: The first pattern uses negative lookbehind to avoid matching
# "Results for Calling" or "Arguments for Calling" as start events
TOOL_START_PATTERNS = [
    r"(?<!Results for )(?<!Arguments for )Calling (?:tool )?['\"]?([^\s'\"\.]+)['\"]?",
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
    r"Results for Calling ([^\s:]+):\s*(.+)",  # MCP result pattern - capture tool name and result
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

# Workspace/action tool JSON patterns - these are internal structures that
# should be filtered as they'll be shown via proper tool cards instead
WORKSPACE_TOOL_PATTERNS = [
    # Standard JSON patterns
    r'"action_type"\s*:\s*"',  # "action_type": "new_answer"
    r'"answer_data"\s*:\s*\{',  # "answer_data": {
    r'"action"\s*:\s*"new_answer"',  # "action": "new_answer"
    r'"action"\s*:\s*"vote"',  # "action": "vote"
    r'"content"\s*:\s*"[^"]*\\n',  # "content": "...\n (multiline content in JSON)
    # Partial/malformed patterns (content may be concatenated with other text)
    r'action"\s*:\s*"new_answer"',  # action": "new_answer" (without leading quote)
    r'action"\s*:\s*"vote"',  # action": "vote" (without leading quote)
    r'action_type"\s*:\s*"',  # action_type": " (without leading quote)
    r'answer_data"\s*:\s*\{',  # answer_data": { (without leading quote)
    # Vote-specific patterns
    r'"target_agent_id"\s*:\s*"',  # Vote target field
    r'"reason"\s*:\s*"[^"]*vot',  # Vote reason field mentioning vote
    r'target_agent_id"\s*:\s*"',  # target_agent_id": (without leading quote)
    # Workspace tool patterns
    r'workspace\.action"\s*:\s*"',  # workspace.action": pattern
    r'\.action"\s*:\s*"new_answer"',  # .action": "new_answer"
    r'\.action"\s*:\s*"vote"',  # .action": "vote"
    # Structured output patterns (Gemini format)
    r'\{\s*"action_type"\s*:',  # Start of structured JSON block
    r'\{\s*"action"\s*:\s*"(?:new_answer|vote)"',  # {"action": "new_answer" or "vote"
]

COMPILED_WORKSPACE_PATTERNS = [re.compile(p, re.IGNORECASE) for p in WORKSPACE_TOOL_PATTERNS]

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

# Patterns for workspace state content that should be filtered from display
# These are internal messages that leak through from agent responses
WORKSPACE_STATE_PATTERNS = [
    r'^Providing answer:\s*"',  # "Providing answer: "..." at start
    r"Providing answer:\s*[\"']",  # "Providing answer: "..." anywhere in content
    r"^- CWD:\s*",  # "- CWD: /path/..." workspace path
    r"^- File created:\s*",  # "- File created: filename" workspace state
    r"^- File modified:\s*",  # "- File modified: filename" workspace state
    r"^- File deleted:\s*",  # "- File deleted: filename" workspace state
    r'"Answer already provided by \w+',  # Duplicate answer error messages
    r"Provide different answer or vote for existing one",  # Error continuation
    r"'''Providing answer:",  # Triple-quoted providing answer
    r'"""Providing answer:',  # Double triple-quoted providing answer
    r"\*\*File Path",  # File path markers
    r"\*\*Poem Content",  # Poem content markers
    # Fragment JSON patterns (when JSON appears mid-content without proper structure)
    r'"content"\s*:\s*"[^"]*"\s*"vote_data"',  # "content": "...""vote_data" concatenation
    r'"action"\s*:\s*"vote"',  # "action": "vote" anywhere
    r'"agent_id"\s*:\s*"agent\d*"',  # "agent_id": "agent1" anywhere
    r'"target_answer_id"\s*:\s*"',  # "target_answer_id": "..." anywhere
    r'"vote_data"\s*:\s*\{',  # "vote_data": { anywhere
    r'"action_type"\s*:\s*"',  # "action_type": "..." anywhere (this is coordination JSON)
    r'"action_type"\s*:\s*""',  # "action_type": "" malformed
    # Status change messages (internal state updates)
    r"Status changed to completed",  # Agent status change
    r"Status changed to \w+",  # Any status change message
    # Mixed content fragments (text + JSON)
    r"This fully addresses the original message",  # Boilerplate reasoning
    r"no further improvement or additional information is necessary",  # Boilerplate reasoning
]

COMPILED_WORKSPACE_STATE_PATTERNS = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in WORKSPACE_STATE_PATTERNS]

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
    tool_call_id: Optional[str] = None  # Unique ID for this tool call  # For "Registered X tools" messages


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
    tool_call_id: Optional[str] = None  # Unique ID for this tool call  # Flag for coordination content (for grouping)


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
    def strip_injection_markers(content: str) -> str:
        """Strip [INJECTION], [REMINDER], and MCP markers from anywhere in content.

        Unlike strip_prefixes which only works at the start, this removes markers
        that can appear mid-content (e.g., in tool results).
        """
        result = content
        for pattern, replacement in COMPILED_GLOBAL_STRIP_PATTERNS:
            result = pattern.sub(replacement, result)
        # Clean up multiple spaces that may result from substitutions
        result = re.sub(r"  +", " ", result)
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
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                tool_name = match.group(1) if len(match.groups()) >= 1 else "unknown"
                # Extract result if captured (e.g., "Results for Calling tool: result_text")
                result_text = match.group(2).strip() if len(match.groups()) >= 2 else None
                return ToolMetadata(tool_name=tool_name, event="complete", result=result_text)

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
    def is_workspace_tool_json(content: str) -> bool:
        """Check if content is primarily workspace/action tool JSON that should be filtered.

        These are internal coordination structures (action_type, answer_data, etc.)
        that will be shown via proper tool cards instead of raw JSON.

        Only returns True if:
        1. Content starts with { or [ (after stripping whitespace/markdown)
        2. AND contains workspace action patterns

        This prevents filtering mixed content like "Here is my answer: {json}"
        where the reasoning part should be preserved.
        """
        stripped = content.strip()

        # Remove markdown code fence if present
        if stripped.startswith("```"):
            # Find end of first line
            first_newline = stripped.find("\n")
            if first_newline > 0:
                stripped = stripped[first_newline + 1 :]
            # Remove closing fence
            if stripped.rstrip().endswith("```"):
                stripped = stripped.rstrip()[:-3].rstrip()
            stripped = stripped.strip()

        # Only consider it workspace JSON if it starts with JSON structure
        if not (stripped.startswith("{") or stripped.startswith("[")):
            return False

        # Now check for workspace action patterns
        for pattern in COMPILED_WORKSPACE_PATTERNS:
            if pattern.search(content):
                return True
        return False

    @staticmethod
    def is_workspace_state_content(content: str) -> bool:
        """Check if content is workspace state info that should be filtered.

        This includes messages like:
        - "Providing answer: ..."
        - "- CWD: /path/..."
        - "- File created: ..."
        - "Answer already provided by agent_b..."
        - Content with lots of escaped newlines (raw structured output)
        - Content that is primarily JSON field fragments

        These are internal coordination messages that leak through from agent responses.
        """
        for pattern in COMPILED_WORKSPACE_STATE_PATTERNS:
            if pattern.search(content):
                return True

        # Check for content with lots of escaped newlines - sign of raw structured output
        # If content has 3+ escaped \n and mentions workspace-related terms, filter it
        escaped_newlines = content.count("\\n")
        if escaped_newlines >= 3:
            workspace_terms = ["Providing answer", "File Path", "content=", "answer_data"]
            if any(term.lower() in content.lower() for term in workspace_terms):
                return True

        # Check for content that is primarily JSON-like fragments
        # Count JSON-like indicators
        json_indicators = [
            '": "',  # JSON key-value separator
            '": {',  # JSON nested object
            '",',  # JSON string followed by comma
            '"},',  # JSON end object with comma
        ]
        json_score = sum(content.count(ind) for ind in json_indicators)

        # If content has significant JSON-like structure, it's probably coordination JSON
        content_len = len(content)
        if content_len > 0 and json_score >= 2:
            # More aggressive filtering for short content with JSON
            if content_len < 200 or json_score >= 3:
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
            # Check args/results first - they contain "calling" but are different events
            if "arguments for" in content_lower:
                return "tool_args"
            elif "results for" in content_lower:
                return "tool_complete"
            elif "calling" in content_lower or "executing" in content_lower:
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
            elif tool_meta.event == "args":
                return "tool_args"
            elif tool_meta.event == "complete":
                return "tool_complete"
            elif tool_meta.event == "failed":
                return "tool_failed"
            elif tool_meta.event == "info":
                return "tool_info"

        return "text"

    @classmethod
    def normalize(cls, content: str, raw_type: str = "", tool_call_id: Optional[str] = None) -> NormalizedContent:
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
            tool_call_id: Optional unique ID for this tool call

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
            # Pass tool_call_id to metadata
            if tool_metadata and tool_call_id:
                tool_metadata.tool_call_id = tool_call_id

        # Check if this is coordination content (for grouping, not filtering)
        is_coordination = cls.is_coordination_content(content)

        # Determine if should display
        should_display = True

        # Filter pure JSON noise
        if cls.is_json_noise(content):
            should_display = False

        # Filter workspace/action tool JSON (shown via tool cards instead)
        if cls.is_workspace_tool_json(content):
            should_display = False

        # Filter workspace state content (internal messages)
        # BUT: Don't filter tool content - tool args contain JSON that we need to display
        if not content_type.startswith("tool_") and cls.is_workspace_state_content(content):
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
            tool_call_id=tool_call_id,
        )
