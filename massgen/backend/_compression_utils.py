# -*- coding: utf-8 -*-
"""
Shared compression utilities for all backends.

Provides a simple message compression function that can be used by any backend
when context length is exceeded.
"""

import json
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..logger_config import get_log_session_dir, logger

if TYPE_CHECKING:
    from .base import BackendBase

# Conversation summarization prompt adapted from Claude Code's compaction system
# Source: https://github.com/Piebald-AI/claude-code-system-prompts
# File: system-prompts/agent-prompt-conversation-summarization.md
#
# Key adaptations for MassGen:
# - Removed <analysis> tags to minimize output tokens (we're token-constrained)
# - Kept structured sections for comprehensive context preservation
# - Added tool execution focus (MassGen is heavily tool-based)
SUMMARIZER_SYSTEM_PROMPT = """Your task is to create a detailed summary of the conversation so far, paying close attention to the user's explicit requests and your previous actions.
This summary should be thorough in capturing technical details, code patterns, and architectural decisions that would be essential for continuing development work without losing context.

Your summary should include the following sections:

1. Primary Request and Intent: Capture all of the user's explicit requests and intents in detail.

2. Key Technical Concepts: List all important technical concepts, technologies, and frameworks discussed.

3. Files and Code Sections: Enumerate specific files and code sections examined, modified, or created.
   Include full code snippets where applicable and include a summary of why each file read or edit is important.

4. Tool Execution Results: Summarize key outputs from tool calls (file reads, command executions, API responses). Include specific data that would be lost without the original context.

5. Errors and Fixes: List all errors encountered and how they were fixed. Pay special attention to specific user feedback received.

6. Problem Solving: Document problems solved and any ongoing troubleshooting efforts.

7. Pending Tasks: Outline any pending tasks that have explicitly been requested.

8. Current Work: Describe in detail precisely what was being worked on immediately before this summary,
   paying special attention to the most recent messages. Include file names and code snippets where applicable.

9. Optional Next Step: List the next step to take that is related to the most recent work.
   IMPORTANT: ensure this step is DIRECTLY in line with the user's most recent explicit requests.
   If the last task was concluded, only list next steps if they are explicitly in line with the user's request.

Be thorough but concise. This summary will replace the original messages, so include everything essential for continuing the work seamlessly."""

SUMMARIZER_USER_PROMPT = """Please provide a detailed summary of the conversation below, following the structure specified in your instructions.

<conversation>
{conversation}
</conversation>

Create your summary now, ensuring precision and thoroughness. Focus especially on preserving:
- Exact file paths and code changes
- Specific tool outputs and their implications
- User feedback and course corrections
- The precise state of work when this summary was created"""


async def compress_messages_for_recovery(
    messages: List[Dict[str, Any]],
    backend: "BackendBase",
    target_ratio: float = 0.2,
    buffer_content: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Compress messages for context error recovery.

    This function is backend-agnostic and uses the provided backend
    to make the summarization call.

    Args:
        messages: The messages that caused the context length error
        backend: The backend to use for summarization (uses same provider)
        target_ratio: What fraction of messages to preserve (default 0.2 = 20%)
        buffer_content: Optional partial response content from streaming buffer

    Returns:
        Compressed message list ready for retry
    """
    logger.info(
        f"[CompressionUtils] Compressing {len(messages)} messages " f"with target_ratio={target_ratio}",
    )

    # Separate system message from other messages - system should NEVER be compressed
    system_message = None
    conversation_messages = messages
    if messages and messages[0].get("role") == "system":
        system_message = messages[0]
        conversation_messages = messages[1:]

    # If only system message or nothing to compress, return original
    if not conversation_messages:
        logger.warning("[CompressionUtils] No conversation messages to compress, returning original")
        return messages

    # Calculate how many conversation messages to preserve (excluding system)
    total_conversation = len(conversation_messages)
    preserve_count = max(1, int(total_conversation * target_ratio))

    # Determine which messages to compress vs preserve
    if preserve_count < total_conversation:
        messages_to_compress = conversation_messages[:-preserve_count]
        recent_messages = conversation_messages[-preserve_count:]
    else:
        messages_to_compress = conversation_messages[:-1]
        recent_messages = conversation_messages[-1:]

    # If there's nothing to compress from messages BUT we have buffer content,
    # we can still generate a summary from the buffer (which contains tool results)
    if not messages_to_compress and not buffer_content:
        logger.warning("[CompressionUtils] No messages or buffer content to compress, returning original")
        return messages

    # If we have no messages to compress but DO have buffer content,
    # summarize the buffer content alone (e.g., massive tool results on first turn)
    if not messages_to_compress and buffer_content:
        logger.info("[CompressionUtils] No messages to compress but buffer has content - summarizing buffer only")

    # Build context for summarization
    # Include both message content and buffer content (tool results, etc.)
    summary_context = ""
    if messages_to_compress:
        summary_context = _format_messages_for_summary(messages_to_compress)
    if buffer_content:
        if summary_context:
            summary_context += f"\n\n[Tool execution results and streaming content]\n{buffer_content}"
        else:
            # Buffer-only case: summarize just the tool results
            summary_context = f"[Tool execution results]\n{buffer_content}"

    # Save debug data
    _save_compression_debug(
        original_messages=messages,
        messages_to_compress=messages_to_compress,
        recent_messages=recent_messages,
        buffer_content=buffer_content,
        summary_context=summary_context,
        suffix="_input",
    )

    # Generate summary using the same backend
    try:
        summary = await _generate_summary(backend, summary_context)
        logger.info(f"[CompressionUtils] Generated summary: {len(summary)} chars")

    except Exception as e:
        logger.error(f"[CompressionUtils] Summarization failed: {e}. Using simple truncation.")
        summary = "[Previous conversation content was truncated due to context limits]"

    # Build result: system (if exists) + summary + recent messages
    result = []

    # Preserve system message if present (never compressed)
    if system_message:
        result.append(system_message)

    # Add summary as assistant message
    result.append(
        {
            "role": "assistant",
            "content": f"[Previous conversation summary]\n{summary}",
        },
    )

    # Add recent messages
    result.extend(recent_messages)

    logger.info(
        f"[CompressionUtils] Compressed {len(messages)} messages to {len(result)} messages",
    )

    # Save result debug data
    _save_compression_debug(
        compressed_result=result,
        summary=summary,
        suffix="_result",
    )

    return result


def _get_token_calculator():
    """Get or create a TokenCostCalculator instance for token estimation."""
    from ..token_manager import TokenCostCalculator

    # Use a module-level cache to avoid repeated initialization
    if not hasattr(_get_token_calculator, "_instance"):
        _get_token_calculator._instance = TokenCostCalculator()
    return _get_token_calculator._instance


def _truncate_to_token_budget(text: str, max_tokens: int) -> str:
    """Truncate text to fit within a token budget using tiktoken.

    Args:
        text: The text to truncate
        max_tokens: Maximum number of tokens allowed

    Returns:
        Truncated text that fits within the token budget
    """
    calc = _get_token_calculator()
    current_tokens = calc.estimate_tokens(text)

    if current_tokens <= max_tokens:
        return text

    # Binary search for the right truncation point
    # Start with a rough estimate based on ratio
    ratio = max_tokens / current_tokens
    end_pos = int(len(text) * ratio * 0.9)  # Start conservative

    # Refine with binary search
    low, high = 0, len(text)
    best_pos = end_pos

    for _ in range(10):  # Max 10 iterations
        mid = (low + high) // 2
        truncated = text[:mid]
        tokens = calc.estimate_tokens(truncated)

        if tokens <= max_tokens:
            best_pos = mid
            low = mid + 1
        else:
            high = mid - 1

    truncated_text = text[:best_pos]
    logger.info(
        f"[CompressionUtils] Truncated from {current_tokens} to ~{calc.estimate_tokens(truncated_text)} tokens",
    )
    return truncated_text + "\n\n[... truncated to fit context ...]"


def _get_context_window_for_backend(backend: "BackendBase") -> tuple[int, str]:
    """Get the context window size for a backend.

    Tries in order:
    1. Backend's _context_window_size attribute (set by mid-stream compression check)
    2. TokenCostCalculator model pricing (from LiteLLM or hardcoded)
    3. Default fallback of 128k

    Args:
        backend: The backend to get context window for

    Returns:
        Tuple of (context_window_size, source_description)
    """
    # 1. Check if backend has context window set (from set_compression_check)
    backend_context = getattr(backend, "_context_window_size", None)
    if backend_context and backend_context > 0:
        return backend_context, "backend._context_window_size"

    # 2. Try to look up from token calculator using provider/model
    calc = _get_token_calculator()
    provider = backend.get_provider_name() if hasattr(backend, "get_provider_name") else None
    model = None
    if hasattr(backend, "config") and isinstance(backend.config, dict):
        model = backend.config.get("model")

    if provider and model:
        pricing = calc.get_model_pricing(provider, model)
        if pricing and pricing.context_window and pricing.context_window > 0:
            return pricing.context_window, f"TokenCostCalculator({provider}/{model})"

    # 3. Default fallback
    return 128000, "default_fallback"


async def _generate_summary(backend: "BackendBase", conversation_text: str) -> str:
    """Generate a summary using the backend's streaming API.

    Uses the backend's own stream_with_tools() method which handles all
    backend-specific differences uniformly.

    Args:
        backend: The backend to use for the API call
        conversation_text: Formatted conversation text to summarize

    Returns:
        Summary text
    """
    # Fixed output token budget for the summary
    SUMMARY_OUTPUT_TOKENS = 4096

    # Get context window size from backend with source tracking
    context_window, context_source = _get_context_window_for_backend(backend)
    logger.info(
        f"[CompressionUtils] Using context_window={context_window:,} tokens (source: {context_source})",
    )

    # Calculate token budget for conversation content
    calc = _get_token_calculator()
    system_tokens = calc.estimate_tokens(SUMMARIZER_SYSTEM_PROMPT)
    prompt_template_tokens = calc.estimate_tokens(SUMMARIZER_USER_PROMPT)

    # Max tokens for conversation: context - system - prompt_template - output - safety_margin
    max_conversation_tokens = context_window - system_tokens - prompt_template_tokens - SUMMARY_OUTPUT_TOKENS - 500

    # Truncate conversation_text to fit within budget
    conversation_text = _truncate_to_token_budget(conversation_text, max_conversation_tokens)

    summarizer_messages = [
        {"role": "system", "content": SUMMARIZER_SYSTEM_PROMPT},
        {"role": "user", "content": SUMMARIZER_USER_PROMPT.format(conversation=conversation_text)},
    ]

    # Use the backend's stream_with_tools() - works uniformly for all backends
    # Collect content chunks into final response
    # Filter out mcp_status chunks (connection messages, tool registration, etc.)
    content_parts = []
    async for chunk in backend.stream_with_tools(summarizer_messages, tools=[]):
        if chunk.content and chunk.type != "mcp_status":
            content_parts.append(chunk.content)

    return "".join(content_parts)


def _format_messages_for_summary(messages: List[Dict[str, Any]]) -> str:
    """Format messages into a readable string for summarization."""
    parts = []

    for msg in messages:
        role = msg.get("role", msg.get("type", "unknown"))
        content = msg.get("content", msg.get("output", ""))

        # Handle different message types
        if msg.get("type") == "function_call":
            name = msg.get("name", "unknown")
            args = msg.get("arguments", "{}")
            parts.append(f"[Tool Call: {name}]\nArguments: {args}")
        elif msg.get("type") == "function_call_output":
            output = msg.get("output", "")
            parts.append(f"[Tool Result]\n{output}")
        elif isinstance(content, str):
            parts.append(f"[{role}]\n{content}")
        elif isinstance(content, list):
            # Handle multimodal content
            text_parts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    text_parts.append(item["text"])
            text = "\n".join(text_parts)
            parts.append(f"[{role}]\n{text}")

    return "\n\n---\n\n".join(parts)


def _save_compression_debug(
    original_messages: Optional[List[Dict[str, Any]]] = None,
    messages_to_compress: Optional[List[Dict[str, Any]]] = None,
    recent_messages: Optional[List[Dict[str, Any]]] = None,
    buffer_content: Optional[str] = None,
    summary_context: Optional[str] = None,
    compressed_result: Optional[List[Dict[str, Any]]] = None,
    summary: Optional[str] = None,
    suffix: str = "",
) -> None:
    """Save compression debug data to the log directory."""
    try:
        log_dir = get_log_session_dir()
        if not log_dir:
            return

        compression_dir = log_dir / "compression_debug"
        compression_dir.mkdir(parents=True, exist_ok=True)

        timestamp = int(time.time() * 1000)
        filename = f"compression_{timestamp}{suffix}.json"
        filepath = compression_dir / filename

        data = {"timestamp": timestamp}

        if original_messages is not None:
            data["original_messages"] = original_messages
            data["original_message_count"] = len(original_messages)

        if messages_to_compress is not None:
            data["messages_to_compress"] = messages_to_compress
            data["messages_to_compress_count"] = len(messages_to_compress)

        if recent_messages is not None:
            data["recent_messages"] = recent_messages
            data["recent_messages_count"] = len(recent_messages)

        if buffer_content is not None:
            data["buffer_content"] = buffer_content

        if summary_context is not None:
            data["summary_context"] = summary_context

        if compressed_result is not None:
            data["compressed_result"] = compressed_result
            data["compressed_message_count"] = len(compressed_result)

        if summary is not None:
            data["summary"] = summary

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

        logger.debug(f"[CompressionUtils] Saved compression debug data: {filepath}")

    except Exception as e:
        logger.warning(f"[CompressionUtils] Failed to save compression debug: {e}")
