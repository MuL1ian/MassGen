# -*- coding: utf-8 -*-
"""Streaming buffer mixin for compression recovery.

This module provides a mixin class that adds streaming buffer functionality
to LLM backends. The buffer tracks accumulated content during streaming so
it can be included in compression summaries when context limits are exceeded.
"""
import json
from typing import Any, Dict, List, Optional


class StreamingBufferMixin:
    """Mixin providing streaming buffer for compression recovery.

    Tracks accumulated content during streaming so it can be included
    in compression summaries when context limits are exceeded. The buffer
    captures:
    - Streaming text content (deltas)
    - Tool call requests (name + arguments)
    - Tool execution results
    - Tool errors
    - Reasoning/thinking content

    Usage:
        class MyBackend(StreamingBufferMixin, CustomToolAndMCPBackend):
            pass

    Note:
        The mixin should be listed BEFORE the main parent class in the
        inheritance list for correct Method Resolution Order (MRO).
    """

    _streaming_buffer: str = ""
    _in_reasoning_block: bool = False

    def __init__(self, *args, **kwargs):
        """Initialize streaming buffer.

        Uses cooperative multiple inheritance - calls super().__init__()
        to ensure proper MRO chain.
        """
        super().__init__(*args, **kwargs)
        self._streaming_buffer = ""
        self._in_reasoning_block = False

    def _clear_streaming_buffer(
        self,
        *,
        _compression_retry: bool = False,
        **kwargs,
    ) -> None:
        """Clear the streaming buffer.

        Respects the _compression_retry flag - does NOT clear if this is
        a retry after compression (to preserve accumulated context).

        Args:
            _compression_retry: If True, preserve buffer (retry after compression)
            **kwargs: Additional keyword arguments (ignored, for compatibility)
        """
        if not _compression_retry:
            self._streaming_buffer = ""
            self._in_reasoning_block = False

    def _append_to_streaming_buffer(self, content: str) -> None:
        """Append content to the streaming buffer.

        Args:
            content: Text content to append (typically streaming deltas)
        """
        if content:
            self._in_reasoning_block = False  # End reasoning block when regular content comes
            self._streaming_buffer += content

    def _append_tool_call_to_buffer(
        self,
        tool_calls: List[Dict[str, Any]],
    ) -> None:
        """Append tool call requests to the streaming buffer.

        Records the tool calls made by the LLM before execution.

        Args:
            tool_calls: List of tool call dictionaries with name, arguments, etc.
        """
        if not tool_calls:
            return

        for call in tool_calls:
            # Handle both flat format {"name": "...", "arguments": ...}
            # and nested format {"function": {"name": "...", "arguments": ...}}
            if "function" in call and isinstance(call["function"], dict):
                name = call["function"].get("name", "unknown")
                args = call["function"].get("arguments", {})
            else:
                name = call.get("name", "unknown")
                args = call.get("arguments", {})

            # Format arguments - handle both string and dict
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except (json.JSONDecodeError, TypeError):
                    pass  # Keep as string

            # Compact JSON for arguments
            if isinstance(args, dict):
                args_str = json.dumps(args, separators=(",", ":"))
            else:
                args_str = str(args)

            self._in_reasoning_block = False  # End reasoning block when tool call comes
            self._streaming_buffer += f"\n\n[Tool Call: {name}({args_str})]"

    def _append_tool_to_buffer(
        self,
        tool_name: str,
        result_text: str,
        is_error: bool = False,
    ) -> None:
        """Append a tool result to the streaming buffer with consistent formatting.

        Args:
            tool_name: Name of the tool that was executed
            result_text: The result text or error message
            is_error: Whether this is an error result
        """
        self._in_reasoning_block = False  # End reasoning block when tool result comes
        prefix = "Tool Error" if is_error else "Tool"
        self._streaming_buffer += f"\n\n[{prefix}: {tool_name}]\n{result_text}"

    def _append_reasoning_to_buffer(self, reasoning_text: str) -> None:
        """Append reasoning/thinking content to the streaming buffer.

        Args:
            reasoning_text: Reasoning or thinking text from the model
        """
        if reasoning_text:
            # Only add header if this is start of reasoning block
            if not self._in_reasoning_block:
                if self._streaming_buffer and not self._streaming_buffer.endswith("\n"):
                    self._streaming_buffer += "\n"
                self._streaming_buffer += "\n[Reasoning]\n"
                self._in_reasoning_block = True
            self._streaming_buffer += reasoning_text

    def _get_streaming_buffer(self) -> Optional[str]:
        """Get buffer content for compression, or None if empty.

        Returns:
            Buffer content string or None if empty
        """
        return self._streaming_buffer if self._streaming_buffer else None
