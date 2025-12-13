# -*- coding: utf-8 -*-
"""
AgentConversationBuffer - Single source of truth for agent conversation state.

This module provides a unified conversation buffer that captures ALL streaming
content during agent coordination, replacing the fragmented approach of multiple
separate storage mechanisms.

See docs/dev_notes/conversation_buffer_design.md for architecture details.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class EntryType(Enum):
    """Types of entries in the conversation buffer."""

    USER = "user"  # User/orchestrator messages
    ASSISTANT = "assistant"  # Agent responses
    SYSTEM = "system"  # System messages
    TOOL_CALL = "tool_call"  # Tool invocation
    TOOL_RESULT = "tool_result"  # Tool execution result
    INJECTION = "injection"  # Injected updates from other agents
    REASONING = "reasoning"  # Agent thinking/reasoning content


@dataclass
class ConversationEntry:
    """
    Single entry in the conversation buffer.

    Attributes:
        timestamp: Unix timestamp when entry was created
        entry_type: Type of entry (user, assistant, tool_call, etc.)
        content: The actual content of the entry
        metadata: Additional context (tool_name, attempt, round, etc.)
    """

    timestamp: float
    entry_type: EntryType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize entry to dict."""
        return {
            "timestamp": self.timestamp,
            "entry_type": self.entry_type.value,
            "content": self.content,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationEntry":
        """Deserialize entry from dict."""
        return cls(
            timestamp=data["timestamp"],
            entry_type=EntryType(data["entry_type"]),
            content=data["content"],
            metadata=data.get("metadata", {}),
        )


class AgentConversationBuffer:
    """
    Unified conversation buffer that captures ALL streaming content.

    This class serves as the single source of truth for agent conversation state,
    capturing everything that happens during streaming:
    - Content chunks (accumulated text)
    - Reasoning/thinking content
    - Tool calls (MCP, custom, workflow)
    - Tool results
    - Injected updates from other agents
    - System context

    This replaces the fragmented approach where content was split across:
    - conversation_history (incomplete, missing streamed content)
    - conversation_memory (separate system, not used for injection)
    - assistant_response (temporary accumulator, lost after streaming)

    Usage:
        buffer = AgentConversationBuffer(agent_id="agent_a")

        # During streaming:
        buffer.add_content("I'll analyze this...")
        buffer.add_tool_call("read_file", {"path": "foo.py"}, call_id="call_123")
        buffer.add_tool_result("read_file", "call_123", "file contents...")
        buffer.add_reasoning("Let me think about this...")

        # When turn completes:
        buffer.flush_turn()

        # For injection:
        buffer.inject_update({"agent_b": "Here's my answer..."})

        # Build LLM messages:
        messages = buffer.to_messages()

        # Persistence:
        buffer.save(Path("buffer.json"))
        buffer = AgentConversationBuffer.load(Path("buffer.json"))
    """

    def __init__(self, agent_id: str):
        """
        Initialize conversation buffer for an agent.

        Args:
            agent_id: Unique identifier for the agent
        """
        self.agent_id = agent_id
        self.entries: List[ConversationEntry] = []

        # Coordination tracking
        self.current_attempt = 0
        self.current_round = 0

        # Streaming accumulators (flushed on turn complete)
        self._pending_content = ""
        self._pending_reasoning = ""
        self._pending_tool_calls: List[Dict[str, Any]] = []

        # Track injection points for debugging
        self._injection_timestamps: List[float] = []

    # ─────────────────────────────────────────────────────────────────────
    # Recording during streaming
    # ─────────────────────────────────────────────────────────────────────

    def set_coordination_context(self, attempt: int, round_num: int) -> None:
        """
        Set current coordination context for metadata.

        Args:
            attempt: Current attempt number
            round_num: Current round number
        """
        self.current_attempt = attempt
        self.current_round = round_num

    def add_system_message(self, content: str) -> None:
        """
        Add system message to buffer.

        Args:
            content: System message content
        """
        self.entries.append(
            ConversationEntry(
                timestamp=time.time(),
                entry_type=EntryType.SYSTEM,
                content=content,
                metadata=self._base_metadata(),
            ),
        )

    def add_user_message(self, content: str) -> None:
        """
        Add user/orchestrator message to buffer.

        Args:
            content: User message content
        """
        self.entries.append(
            ConversationEntry(
                timestamp=time.time(),
                entry_type=EntryType.USER,
                content=content,
                metadata=self._base_metadata(),
            ),
        )

    def add_content(self, content: str) -> None:
        """
        Accumulate streaming content.

        Content is accumulated until flush_turn() is called, then
        stored as a single assistant entry.

        Args:
            content: Content chunk to accumulate
        """
        self._pending_content += content

    def add_reasoning(self, content: str) -> None:
        """
        Accumulate reasoning/thinking content.

        Args:
            content: Reasoning content chunk
        """
        self._pending_reasoning += content

    def add_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        call_id: Optional[str] = None,
    ) -> None:
        """
        Record a tool call.

        Args:
            tool_name: Name of the tool being called
            args: Arguments passed to the tool
            call_id: Optional unique identifier for the call
        """
        self._pending_tool_calls.append(
            {
                "name": tool_name,
                "arguments": args,
                "call_id": call_id,
                "result": None,
                "timestamp": time.time(),
            },
        )

    def add_tool_result(
        self,
        tool_name: str,
        call_id: Optional[str],
        result: str,
    ) -> None:
        """
        Record tool result, matching to previous call if possible.

        Args:
            tool_name: Name of the tool
            call_id: Call ID to match (if available)
            result: Result from tool execution
        """
        # Try to find matching call and update result
        for call in reversed(self._pending_tool_calls):
            if call["name"] == tool_name:
                if call_id is None or call.get("call_id") == call_id:
                    if call["result"] is None:  # Don't overwrite existing result
                        call["result"] = result
                        return

        # No matching call found, add standalone result entry
        self._pending_tool_calls.append(
            {
                "name": tool_name,
                "call_id": call_id,
                "arguments": {},
                "result": result,
                "timestamp": time.time(),
            },
        )

    def flush_turn(self) -> None:
        """
        Flush accumulated content into entries.

        Called when agent turn completes (on "done" chunk). This converts
        all pending accumulators into permanent entries.
        """
        now = time.time()
        base_meta = self._base_metadata()

        # Add reasoning if present
        if self._pending_reasoning.strip():
            self.entries.append(
                ConversationEntry(
                    timestamp=now,
                    entry_type=EntryType.REASONING,
                    content=self._pending_reasoning.strip(),
                    metadata=base_meta,
                ),
            )

        # Add tool calls and results
        for call in self._pending_tool_calls:
            # Add tool call entry
            self.entries.append(
                ConversationEntry(
                    timestamp=call["timestamp"],
                    entry_type=EntryType.TOOL_CALL,
                    content=json.dumps(call.get("arguments", {}), default=str),
                    metadata={
                        **base_meta,
                        "tool_name": call["name"],
                        "call_id": call.get("call_id"),
                    },
                ),
            )

            # Add tool result entry if present
            if call.get("result"):
                self.entries.append(
                    ConversationEntry(
                        timestamp=call["timestamp"] + 0.001,
                        entry_type=EntryType.TOOL_RESULT,
                        content=str(call["result"]),
                        metadata={
                            **base_meta,
                            "tool_name": call["name"],
                            "call_id": call.get("call_id"),
                        },
                    ),
                )

        # Add main content
        if self._pending_content.strip():
            self.entries.append(
                ConversationEntry(
                    timestamp=now,
                    entry_type=EntryType.ASSISTANT,
                    content=self._pending_content.strip(),
                    metadata=base_meta,
                ),
            )

        # Clear accumulators
        self._pending_content = ""
        self._pending_reasoning = ""
        self._pending_tool_calls = []

    def _base_metadata(self) -> Dict[str, Any]:
        """Get base metadata for entries."""
        return {
            "attempt": self.current_attempt,
            "round": self.current_round,
            "agent_id": self.agent_id,
        }

    # ─────────────────────────────────────────────────────────────────────
    # Injection support
    # ─────────────────────────────────────────────────────────────────────

    def inject_update(
        self,
        new_answers: Dict[str, str],
        anonymize: bool = True,
    ) -> None:
        """
        Inject update from other agents into buffer.

        This is the canonical injection point - modifies the buffer directly
        with new answers from other agents.

        Args:
            new_answers: Dict mapping agent_id to their answer content
            anonymize: If True, use anonymous labels (agent1, agent2) instead of IDs
        """
        if not new_answers:
            return

        now = time.time()
        update_content = self._format_injection_message(new_answers, anonymize)

        self.entries.append(
            ConversationEntry(
                timestamp=now,
                entry_type=EntryType.INJECTION,
                content=update_content,
                metadata={
                    **self._base_metadata(),
                    "source_agents": list(new_answers.keys()),
                    "answer_count": len(new_answers),
                },
            ),
        )

        self._injection_timestamps.append(now)

    def _format_injection_message(
        self,
        new_answers: Dict[str, str],
        anonymize: bool = True,
    ) -> str:
        """
        Format the injection message content.

        Args:
            new_answers: Dict mapping agent_id to answer content
            anonymize: If True, use anonymous labels

        Returns:
            Formatted injection message string
        """
        parts = [
            "UPDATE: While you were working, new answers were provided.",
            "",
            "<NEW_ANSWERS>",
        ]

        for i, (agent_id, answer) in enumerate(sorted(new_answers.items()), 1):
            label = f"agent{i}" if anonymize else agent_id
            parts.append(f"<{label}>")
            parts.append(answer)
            parts.append(f"</{label}>")
            parts.append("")

        parts.append("</NEW_ANSWERS>")
        parts.append("")
        parts.append("You can now:")
        parts.append("1. Continue your current approach if you think it's better or different")
        parts.append("2. Build upon or refine the new answers")
        parts.append("3. Vote for an existing answer if you agree with it")
        parts.append("")
        parts.append("Proceed with your decision.")

        return "\n".join(parts)

    def get_last_injection_timestamp(self) -> Optional[float]:
        """Get timestamp of most recent injection, if any."""
        return self._injection_timestamps[-1] if self._injection_timestamps else None

    def get_entries_since_injection(self) -> List[ConversationEntry]:
        """Get all entries since the last injection."""
        last_injection = self.get_last_injection_timestamp()
        if last_injection is None:
            return self.entries.copy()
        return [e for e in self.entries if e.timestamp > last_injection]

    # ─────────────────────────────────────────────────────────────────────
    # Building LLM messages
    # ─────────────────────────────────────────────────────────────────────

    def to_messages(
        self,
        include_reasoning: bool = False,
        include_tool_details: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Convert buffer to LLM message format.

        This produces the message list that gets sent to the LLM API.

        Args:
            include_reasoning: If True, include reasoning entries
            include_tool_details: If True, include tool call/result entries

        Returns:
            List of message dicts in LLM format
        """
        messages = []

        for entry in self.entries:
            if entry.entry_type == EntryType.SYSTEM:
                messages.append({"role": "system", "content": entry.content})

            elif entry.entry_type == EntryType.USER:
                messages.append({"role": "user", "content": entry.content})

            elif entry.entry_type == EntryType.ASSISTANT:
                messages.append({"role": "assistant", "content": entry.content})

            elif entry.entry_type == EntryType.REASONING:
                if include_reasoning:
                    messages.append(
                        {
                            "role": "assistant",
                            "content": f"[Reasoning]\n{entry.content}",
                        },
                    )

            elif entry.entry_type == EntryType.TOOL_CALL:
                if include_tool_details:
                    tool_name = entry.metadata.get("tool_name", "unknown")
                    messages.append(
                        {
                            "role": "assistant",
                            "content": f"[Tool Call: {tool_name}]\n{entry.content}",
                            "tool_calls": [
                                {
                                    "id": entry.metadata.get("call_id", ""),
                                    "type": "function",
                                    "function": {
                                        "name": tool_name,
                                        "arguments": entry.content,
                                    },
                                },
                            ],
                        },
                    )

            elif entry.entry_type == EntryType.TOOL_RESULT:
                if include_tool_details:
                    messages.append(
                        {
                            "role": "tool",
                            "content": entry.content,
                            "tool_call_id": entry.metadata.get("call_id", ""),
                        },
                    )

            elif entry.entry_type == EntryType.INJECTION:
                # Injection appears as user message from orchestrator
                messages.append({"role": "user", "content": entry.content})

        return messages

    def to_simple_messages(self) -> List[Dict[str, str]]:
        """
        Convert buffer to simple message format (role + content only).

        Useful for backends that don't support tool message format.

        Returns:
            List of simple message dicts
        """
        messages = []

        for entry in self.entries:
            if entry.entry_type in (EntryType.SYSTEM, EntryType.USER, EntryType.INJECTION):
                role = "system" if entry.entry_type == EntryType.SYSTEM else "user"
                messages.append({"role": role, "content": entry.content})

            elif entry.entry_type in (EntryType.ASSISTANT, EntryType.REASONING):
                messages.append({"role": "assistant", "content": entry.content})

            elif entry.entry_type == EntryType.TOOL_CALL:
                tool_name = entry.metadata.get("tool_name", "unknown")
                messages.append(
                    {
                        "role": "assistant",
                        "content": f"[Using tool: {tool_name}]\nArguments: {entry.content}",
                    },
                )

            elif entry.entry_type == EntryType.TOOL_RESULT:
                tool_name = entry.metadata.get("tool_name", "unknown")
                messages.append(
                    {
                        "role": "user",  # Tool results as user message in simple format
                        "content": f"[Result from {tool_name}]: {entry.content}",
                    },
                )

        return messages

    # ─────────────────────────────────────────────────────────────────────
    # Query methods
    # ─────────────────────────────────────────────────────────────────────

    def get_entries_since(self, timestamp: float) -> List[ConversationEntry]:
        """Get all entries since a given timestamp."""
        return [e for e in self.entries if e.timestamp > timestamp]

    def get_entries_by_type(self, entry_type: EntryType) -> List[ConversationEntry]:
        """Get all entries of a specific type."""
        return [e for e in self.entries if e.entry_type == entry_type]

    def get_tool_calls(self) -> List[ConversationEntry]:
        """Get all tool call entries."""
        return self.get_entries_by_type(EntryType.TOOL_CALL)

    def get_assistant_content(self) -> str:
        """Get concatenated assistant content."""
        entries = self.get_entries_by_type(EntryType.ASSISTANT)
        return "\n\n".join(e.content for e in entries)

    def entry_count(self) -> int:
        """Get total number of entries."""
        return len(self.entries)

    def has_pending_content(self) -> bool:
        """Check if there's unflushed pending content."""
        return bool(
            self._pending_content.strip() or self._pending_reasoning.strip() or self._pending_tool_calls,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Persistence
    # ─────────────────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize buffer to dict.

        Returns:
            Dict representation of the buffer
        """
        return {
            "agent_id": self.agent_id,
            "current_attempt": self.current_attempt,
            "current_round": self.current_round,
            "entries": [e.to_dict() for e in self.entries],
            "injection_timestamps": self._injection_timestamps,
            # Note: pending content is NOT serialized (should be flushed first)
        }

    def save(self, path: Path) -> None:
        """
        Save buffer to file.

        Args:
            path: Path to save to
        """
        # Warn if there's unflushed content
        if self.has_pending_content():
            import logging

            logging.warning(
                f"Saving buffer with unflushed content for agent {self.agent_id}. " "Call flush_turn() first to ensure all content is captured.",
            )

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, default=str))

    @classmethod
    def load(cls, path: Path) -> "AgentConversationBuffer":
        """
        Load buffer from file.

        Args:
            path: Path to load from

        Returns:
            Loaded AgentConversationBuffer instance
        """
        data = json.loads(path.read_text())

        buffer = cls(data["agent_id"])
        buffer.current_attempt = data.get("current_attempt", 0)
        buffer.current_round = data.get("current_round", 0)
        buffer.entries = [ConversationEntry.from_dict(e) for e in data.get("entries", [])]
        buffer._injection_timestamps = data.get("injection_timestamps", [])

        return buffer

    def clear(self) -> None:
        """Clear all entries and pending content."""
        self.entries.clear()
        self._pending_content = ""
        self._pending_reasoning = ""
        self._pending_tool_calls = []
        self._injection_timestamps = []
        self.current_attempt = 0
        self.current_round = 0

    def save_to_text_file(self, path: Path) -> None:
        """
        Save buffer to grep-friendly text file.

        Each entry is formatted as a single line:
        [HH:MM:SS.ms] [TYPE] content...

        This format is optimized for grep/search rather than cat.

        Args:
            path: Path to save to (typically buffer.txt)
        """

        path.parent.mkdir(parents=True, exist_ok=True)

        # Flush any pending content first
        if self.has_pending_content():
            self.flush_turn()

        lines = []
        for entry in self.entries:
            lines.append(self._format_entry_line(entry))

        path.write_text("\n".join(lines))

    def _format_entry_line(self, entry: "ConversationEntry") -> str:
        """
        Format entry as single grep-friendly line.

        Args:
            entry: The conversation entry to format

        Returns:
            Formatted line string
        """
        from datetime import datetime

        ts = datetime.fromtimestamp(entry.timestamp).strftime("%H:%M:%S.%f")[:-3]
        entry_type = entry.entry_type.value.upper()

        # Add tool name for tool entries
        if entry.entry_type in (EntryType.TOOL_CALL, EntryType.TOOL_RESULT):
            tool_name = entry.metadata.get("tool_name", "unknown")
            entry_type = f"{entry_type}:{tool_name}"

        # Replace newlines with spaces for grep-friendly single-line format
        content = entry.content.replace("\n", " ").replace("\r", "")

        return f"[{ts}] [{entry_type}] {content}"

    # ─────────────────────────────────────────────────────────────────────
    # String representation
    # ─────────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"AgentConversationBuffer(" f"agent_id={self.agent_id!r}, " f"entries={len(self.entries)}, " f"attempt={self.current_attempt}, " f"round={self.current_round})"

    def __len__(self) -> int:
        return len(self.entries)
