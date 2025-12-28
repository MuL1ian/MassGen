# -*- coding: utf-8 -*-
"""
Context Window Compression

Provides two compression strategies:
1. ContextCompressor: Algorithmic compression that removes old messages
2. AgentDrivenCompressor: Agent-driven compression with memory writing

The agent-driven approach asks the agent to summarize context to filesystem
memory before truncation, preserving important information.
"""

import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..logger_config import logger
from ..token_manager.token_manager import TokenCostCalculator
from ._compression_prompts import COMPRESSION_FAILED_RETRY, COMPRESSION_REQUEST
from ._conversation import ConversationMemory
from ._persistent import PersistentMemoryBase


class CompressionStats:
    """Statistics about a compression operation."""

    def __init__(
        self,
        messages_removed: int = 0,
        tokens_removed: int = 0,
        messages_kept: int = 0,
        tokens_kept: int = 0,
    ):
        self.messages_removed = messages_removed
        self.tokens_removed = tokens_removed
        self.messages_kept = messages_kept
        self.tokens_kept = tokens_kept


class ContextCompressor:
    """
    Compresses conversation history when context window fills up.

    Strategy:
    - Messages are already recorded to persistent_memory after each turn
    - Compression removes old messages from conversation_memory
    - Recent messages stay in active context
    - Old messages remain accessible via semantic retrieval

    Features:
    - Token-aware compression (not just message count)
    - Preserves system messages
    - Keeps most recent messages
    - Detailed compression logging

    Example:
        >>> compressor = ContextCompressor(
        ...     token_calculator=TokenCostCalculator(),
        ...     conversation_memory=conversation_memory,
        ...     persistent_memory=persistent_memory
        ... )
        >>>
        >>> stats = await compressor.compress_if_needed(
        ...     messages=messages,
        ...     current_tokens=96000,
        ...     target_tokens=51200
        ... )
    """

    def __init__(
        self,
        token_calculator: TokenCostCalculator,
        conversation_memory: ConversationMemory,
        persistent_memory: Optional[PersistentMemoryBase] = None,
        on_compress: Optional[Callable[[CompressionStats], None]] = None,
    ):
        """
        Initialize context compressor.

        Args:
            token_calculator: Calculator for token estimation
            conversation_memory: Conversation memory to compress
            persistent_memory: Optional persistent memory (for logging purposes)
            on_compress: Optional callback called after compression
        """
        self.token_calculator = token_calculator
        self.conversation_memory = conversation_memory
        self.persistent_memory = persistent_memory
        self.on_compress = on_compress

        # Stats tracking
        self.total_compressions = 0
        self.total_messages_removed = 0
        self.total_tokens_removed = 0

    async def compress_if_needed(
        self,
        messages: List[Dict[str, Any]],
        current_tokens: int,
        target_tokens: int,
        should_compress: bool = None,
    ) -> Optional[CompressionStats]:
        """
        Compress messages if needed.

        Args:
            messages: Current conversation messages
            current_tokens: Current token count
            target_tokens: Target token count after compression
            should_compress: Optional explicit compression flag
                           If None, compresses only if current_tokens > target_tokens

        Returns:
            CompressionStats if compression occurred, None otherwise
        """
        # Determine if we need to compress
        if should_compress is None:
            should_compress = current_tokens > target_tokens

        if not should_compress:
            return None

        # Select messages to keep
        messages_to_keep = self._select_messages_to_keep(
            messages=messages,
            target_tokens=target_tokens,
        )

        if len(messages_to_keep) >= len(messages):
            # No compression needed (already under target)
            logger.debug("All messages fit within target, skipping compression")
            return None

        # Calculate stats
        messages_removed = len(messages) - len(messages_to_keep)
        messages_to_remove = [msg for msg in messages if msg not in messages_to_keep]
        tokens_removed = self.token_calculator.estimate_tokens(messages_to_remove)
        tokens_kept = self.token_calculator.estimate_tokens(messages_to_keep)

        # Update conversation memory
        try:
            await self.conversation_memory.clear()
            await self.conversation_memory.add(messages_to_keep)
        except Exception as e:
            logger.error(
                f"Failed to update conversation memory during compression: {e}. " "Memory may be in inconsistent state.",
                exc_info=True,
            )
            # Return None to signal failure - caller should handle gracefully
            # Note: clear() may have succeeded, leaving memory empty
            return None

        # Log compression result
        if self.persistent_memory:
            logger.info(
                f"📦 Context compressed: Removed {messages_removed} old messages "
                f"({tokens_removed:,} tokens) from active context.\n"
                f"   Kept {len(messages_to_keep)} recent messages ({tokens_kept:,} tokens).\n"
                f"   Old messages remain accessible via semantic search.",
            )
        else:
            logger.warning(
                f"⚠️  Context compressed: Removed {messages_removed} old messages "
                f"({tokens_removed:,} tokens) from active context.\n"
                f"   Kept {len(messages_to_keep)} recent messages ({tokens_kept:,} tokens).\n"
                f"   No persistent memory - old messages NOT retrievable.",
            )

        # Update stats
        self.total_compressions += 1
        self.total_messages_removed += messages_removed
        self.total_tokens_removed += tokens_removed

        # Create stats object
        stats = CompressionStats(
            messages_removed=messages_removed,
            tokens_removed=tokens_removed,
            messages_kept=len(messages_to_keep),
            tokens_kept=tokens_kept,
        )

        # Trigger callback if provided
        if self.on_compress:
            self.on_compress(stats)

        return stats

    def _select_messages_to_keep(
        self,
        messages: List[Dict[str, Any]],
        target_tokens: int,
    ) -> List[Dict[str, Any]]:
        """
        Select which messages to keep in active context.

        Strategy:
        1. Always keep system messages at the start
        2. Keep most recent messages that fit in target_tokens
        3. Remove everything in between

        Args:
            messages: All messages in conversation
            target_tokens: Target token budget for kept messages

        Returns:
            List of messages to keep in conversation_memory
        """
        if not messages:
            return []

        # Separate system messages from others
        system_messages = []
        non_system_messages = []

        for msg in messages:
            if msg.get("role") == "system":
                system_messages.append(msg)
            else:
                non_system_messages.append(msg)

        # Start with system messages in kept list
        messages_to_keep = system_messages.copy()
        tokens_so_far = self.token_calculator.estimate_tokens(system_messages)

        # Work backwards from most recent, adding messages until we hit target
        recent_messages_to_keep = []
        for msg in reversed(non_system_messages):
            msg_tokens = self.token_calculator.estimate_tokens([msg])
            if tokens_so_far + msg_tokens <= target_tokens:
                tokens_so_far += msg_tokens
                recent_messages_to_keep.insert(0, msg)  # Maintain order
            else:
                # Hit token limit, stop here
                break

        # Combine: system messages + recent messages
        messages_to_keep.extend(recent_messages_to_keep)

        return messages_to_keep

    def get_stats(self) -> Dict[str, Any]:
        """Get compression statistics."""
        return {
            "total_compressions": self.total_compressions,
            "total_messages_removed": self.total_messages_removed,
            "total_tokens_removed": self.total_tokens_removed,
        }


class AgentDrivenCompressor:
    """
    Coordinates agent-driven context compression with filesystem memory.

    Instead of algorithmically removing messages, this compressor:
    1. Injects a summarization request into the conversation
    2. Waits for agent to write memories using file writing tools
    3. Detects when agent calls compression_complete MCP tool
    4. Validates that required memory files exist
    5. Falls back to algorithmic compression if agent fails
    6. Performs final truncation after summaries are saved

    States:
        idle: Normal operation, monitoring context usage
        requesting: Injected compression request, waiting for agent
        validating: Agent signaled completion, validating files

    Example:
        >>> compressor = AgentDrivenCompressor(
        ...     workspace_path=Path("/workspace"),
        ...     fallback_compressor=context_compressor,
        ... )
        >>> if compressor.should_request_compression(usage_info):
        ...     msg = compressor.build_compression_request(usage_info)
        ...     # Inject msg into conversation
    """

    # Compression states
    STATE_IDLE = "idle"
    STATE_REQUESTING = "requesting"
    STATE_VALIDATING = "validating"

    def __init__(
        self,
        workspace_path: Optional[Path] = None,
        fallback_compressor: Optional[ContextCompressor] = None,
        max_attempts: int = 2,
        short_term_path: str = "memory/short_term",
        long_term_path: str = "memory/long_term",
    ):
        """
        Initialize agent-driven compressor.

        Args:
            workspace_path: Path to agent workspace for memory validation
            fallback_compressor: Algorithmic compressor for fallback
            max_attempts: Max retries before fallback (default 2)
            short_term_path: Relative path for short-term memories
            long_term_path: Relative path for long-term memories
        """
        self.workspace_path = Path(workspace_path) if workspace_path else None
        self.fallback_compressor = fallback_compressor
        self.max_attempts = max_attempts
        self.short_term_path = short_term_path
        self.long_term_path = long_term_path

        # State tracking
        self.state = self.STATE_IDLE
        self.current_attempt = 0
        self.pending_usage_info: Optional[Dict[str, Any]] = None

        # Stats
        self.total_agent_compressions = 0
        self.total_fallback_compressions = 0
        self.total_attempts = 0

    def should_request_compression(self, usage_info: Dict[str, Any]) -> bool:
        """
        Check if compression should be requested.

        Args:
            usage_info: Dict from ContextWindowMonitor.log_context_usage()

        Returns:
            True if compression should be requested
        """
        should_compress = usage_info.get("should_compress", False)
        is_idle = self.state == self.STATE_IDLE
        result = should_compress and is_idle

        logger.debug(
            f"[AgentDrivenCompressor] should_request_compression: "
            f"should_compress={should_compress}, state={self.state}, is_idle={is_idle}, "
            f"usage={usage_info.get('usage_percent', 0)*100:.1f}%, "
            f"threshold={usage_info.get('trigger_threshold', 0)*100:.0f}% -> {result}",
        )

        return result

    def build_compression_request(
        self,
        usage_info: Dict[str, Any],
        task_summary: str = "",
    ) -> Dict[str, Any]:
        """
        Build the compression request message to inject.

        Args:
            usage_info: Context usage info with tokens/percentage
            task_summary: Optional summary of current task

        Returns:
            Message dict to inject into conversation
        """
        content = COMPRESSION_REQUEST.format(
            usage_percent=usage_info.get("usage_percent", 0),
            current_tokens=usage_info.get("current_tokens", 0),
            max_tokens=usage_info.get("max_tokens", 0),
        )

        # Transition to requesting state
        self.state = self.STATE_REQUESTING
        self.pending_usage_info = usage_info
        self.current_attempt += 1
        self.total_attempts += 1

        logger.info(
            f"📝 Requesting agent-driven compression " f"(attempt {self.current_attempt}/{self.max_attempts})",
        )

        return {
            "role": "user",
            "content": content,
            "_is_compression_request": True,  # Internal marker
        }

    def build_retry_request(self) -> Dict[str, Any]:
        """
        Build a retry request if validation failed.

        Returns:
            Message dict to inject into conversation
        """
        self.current_attempt += 1
        self.total_attempts += 1

        content = COMPRESSION_FAILED_RETRY.format(
            attempt=self.current_attempt,
            max_attempts=self.max_attempts,
        )

        logger.warning(
            f"⚠️ Compression validation failed, retrying " f"(attempt {self.current_attempt}/{self.max_attempts})",
        )

        return {
            "role": "user",
            "content": content,
            "_is_compression_request": True,
        }

    def validate_memory_written(self) -> Tuple[bool, List[str]]:
        """
        Check if agent wrote the required memories.

        Returns:
            Tuple of (success, list of written file paths)
        """
        if not self.workspace_path:
            logger.warning("No workspace path configured, skipping validation")
            return True, []  # Can't validate, assume success

        written_files = []
        current_time = time.time()

        # Check for required recent.md
        short_term_dir = self.workspace_path / self.short_term_path
        recent_file = short_term_dir / "recent.md"

        if recent_file.exists():
            # Check if recently modified (within 60 seconds)
            mtime = recent_file.stat().st_mtime
            if current_time - mtime < 60:
                written_files.append(str(recent_file))
                logger.info(f"✅ Found recent memory: {recent_file}")
            else:
                logger.warning("⚠️ recent.md exists but wasn't recently modified")

        # Also check for any new long-term memories
        long_term_dir = self.workspace_path / self.long_term_path
        if long_term_dir.exists():
            for f in long_term_dir.glob("*.md"):
                if current_time - f.stat().st_mtime < 60:
                    if str(f) not in written_files:
                        written_files.append(str(f))
                        logger.info(f"✅ Found long-term memory: {f}")

        success = recent_file.exists()
        return success, written_files

    def on_compression_complete_tool_called(self) -> bool:
        """
        Called when compression_complete MCP tool is detected.

        Returns:
            True if validation passed and truncation should proceed
        """
        if self.state != self.STATE_REQUESTING:
            logger.warning(
                f"compression_complete called in unexpected state: {self.state}",
            )
            return False

        self.state = self.STATE_VALIDATING
        success, files = self.validate_memory_written()

        if success:
            logger.info(f"✅ Agent compression validated. Files: {files}")
            self.total_agent_compressions += 1
            self._reset_state()
            return True
        else:
            # Check if we should retry or fallback
            if self.current_attempt >= self.max_attempts:
                logger.warning(
                    f"⚠️ Agent failed to write memory summary after " f"{self.max_attempts} attempts. Falling back to " f"algorithmic compression (no summary preserved).",
                )
                self.total_fallback_compressions += 1
                self._reset_state()
                return True  # Still proceed with truncation via fallback
            else:
                # Will retry - stay in requesting state
                self.state = self.STATE_REQUESTING
                return False

    def should_use_fallback(self) -> bool:
        """Check if we should use fallback compression."""
        return self.current_attempt >= self.max_attempts

    def _reset_state(self) -> None:
        """Reset state machine to idle."""
        self.state = self.STATE_IDLE
        self.current_attempt = 0
        self.pending_usage_info = None

    def get_stats(self) -> Dict[str, Any]:
        """Get compression statistics."""
        return {
            "total_agent_compressions": self.total_agent_compressions,
            "total_fallback_compressions": self.total_fallback_compressions,
            "total_attempts": self.total_attempts,
            "current_state": self.state,
            "current_attempt": self.current_attempt,
        }
