# -*- coding: utf-8 -*-
"""
Shared compression utilities for all backends.

Provides a simple message compression function that can be used by any backend
when context length is exceeded.
"""

import asyncio
import json
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import httpx

from ..logger_config import get_log_session_dir, logger

if TYPE_CHECKING:
    from .base import BackendBase

# Conversation summarization prompts
#
# Uses a 3-message structure to clearly separate the conversation being summarized
# from the summarization instructions:
# 1. System: Brief instructions for summarization format
# 2. User: The conversation content (provided as a separate message)
# 3. User: Request to summarize it
#
# This prevents the model from confusing instructions in the conversation content
# with the summarization task itself.
SUMMARIZER_SYSTEM_PROMPT = """You summarize conversations. Include:
1. User Request: What was asked for
2. Work Done: Files read, tools used, code written
3. Key Details: File paths, code snippets, technical findings
4. Current State: Where things stand
5. Pending: Remaining work

Be thorough but concise. This summary replaces the original messages."""

# Conversation content - provided as separate message
SUMMARIZER_CONVERSATION_PROMPT = """Here is the conversation to summarize:

{conversation}"""

# Final request - triggers the summary
SUMMARIZER_REQUEST_PROMPT = """Summarize the conversation above."""


async def compress_messages_for_recovery(
    messages: List[Dict[str, Any]],
    backend: "BackendBase",
    target_ratio: float = 0.2,
    buffer_content: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Compress messages for context error recovery.

    This function is backend-agnostic and uses the provided backend
    to make the summarization call. If compression is not sufficient
    (e.g., initial input exceeds context), it will also truncate
    message content to fit within the context window.

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

    except (httpx.HTTPStatusError, httpx.TimeoutException, asyncio.TimeoutError) as e:
        # Expected network/API errors - fallback to truncation is appropriate
        logger.warning(
            f"[CompressionUtils] Summarization failed due to API/network error: {e}. " "Using simple truncation.",
        )
        summary = "[Previous conversation content was truncated due to API error during compression. " "Some context may be incomplete.]"

    except Exception as e:
        # Unexpected error - log with full stack trace for debugging
        logger.error(
            f"[CompressionUtils] Unexpected error during summarization: {e}. " "Using simple truncation.",
            exc_info=True,
        )
        summary = "[Previous conversation content was truncated due to context limits]"

    # Build result: system → user message → summary → any additional recent messages
    # Order matters! Putting summary AFTER user message means the model sees it as
    # the latest context and will build on it rather than re-doing the work.
    result = []

    # Preserve system message if present (never compressed)
    if system_message:
        result.append(system_message)

    # Add recent messages (typically contains the user request)
    result.extend(recent_messages)

    # Add summary as assistant message LAST - this is the most recent context
    # the model sees, so it should continue from here rather than start fresh
    # Strip trailing whitespace to avoid Claude API error about trailing whitespace
    result.append(
        {
            "role": "assistant",
            "content": f"[Previous conversation summary]\n{summary.strip()}",
        },
    )

    logger.info(
        f"[CompressionUtils] Compressed {len(messages)} messages to {len(result)} messages",
    )

    # Check if result still exceeds context and apply truncation if needed
    result = _ensure_fits_context(result, backend)

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


def _estimate_messages_tokens(messages: List[Dict[str, Any]]) -> int:
    """Estimate total tokens in a message list."""
    calc = _get_token_calculator()
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += calc.estimate_tokens(content)
        elif isinstance(content, list):
            # Handle multimodal content
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    total += calc.estimate_tokens(item["text"])
    return total


def _ensure_fits_context(
    messages: List[Dict[str, Any]],
    backend: "BackendBase",
) -> List[Dict[str, Any]]:
    """Ensure messages fit within context window by truncating if needed.

    If the total message tokens exceed the context window, this function
    finds the largest message and truncates its content to fit.

    Args:
        messages: The messages to check/truncate
        backend: The backend (used to get context window size)

    Returns:
        Messages that fit within context window
    """
    context_window, context_source = _get_context_window_for_backend(backend)
    calc = _get_token_calculator()

    # Reserve space for output and safety margin
    # Use 10% variance buffer for tokenizer differences between tiktoken and model-specific tokenizers
    OUTPUT_RESERVE = 4096
    TOKENIZER_VARIANCE_BUFFER = int(context_window * 0.10)
    max_input_tokens = context_window - OUTPUT_RESERVE - TOKENIZER_VARIANCE_BUFFER

    # Estimate current tokens
    current_tokens = _estimate_messages_tokens(messages)

    if current_tokens <= max_input_tokens:
        logger.debug(
            f"[CompressionUtils] Messages fit within context: {current_tokens:,} <= {max_input_tokens:,}",
        )
        return messages

    # Messages exceed context - need to truncate
    logger.warning(
        f"[CompressionUtils] Messages still exceed context after compression: " f"{current_tokens:,} > {max_input_tokens:,} tokens. Truncating content...",
    )

    # Find the largest message (by content tokens)
    largest_idx = -1
    largest_tokens = 0
    for i, msg in enumerate(messages):
        content = msg.get("content", "")
        if isinstance(content, str):
            tokens = calc.estimate_tokens(content)
            if tokens > largest_tokens:
                largest_tokens = tokens
                largest_idx = i

    if largest_idx == -1:
        logger.warning("[CompressionUtils] No truncatable content found")
        return messages

    # Calculate how much to reduce
    excess = current_tokens - max_input_tokens
    target_tokens = largest_tokens - excess - 500  # Extra safety

    if target_tokens < 1000:
        # If we'd need to truncate too much, just keep a minimal amount
        target_tokens = 1000
        logger.warning(
            f"[CompressionUtils] Truncating heavily - target only {target_tokens} tokens",
        )

    # Truncate the largest message
    result = []
    for i, msg in enumerate(messages):
        if i == largest_idx:
            content = msg.get("content", "")
            if isinstance(content, str):
                truncated_content = _truncate_to_token_budget(content, target_tokens)
                result.append({**msg, "content": truncated_content})
                logger.info(
                    f"[CompressionUtils] Truncated message {i} from {largest_tokens:,} to ~{target_tokens:,} tokens",
                )
            else:
                result.append(msg)
        else:
            result.append(msg)

    # Verify final size
    final_tokens = _estimate_messages_tokens(result)
    logger.info(
        f"[CompressionUtils] After truncation: {final_tokens:,} tokens " f"(context: {context_window:,}, source: {context_source})",
    )

    return result


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
    conversation_prompt_tokens = calc.estimate_tokens(SUMMARIZER_CONVERSATION_PROMPT)
    request_tokens = calc.estimate_tokens(SUMMARIZER_REQUEST_PROMPT)

    # Max tokens for conversation: context - system - prompts - output - safety_margin
    # Use 10% safety margin for tokenizer variance between tiktoken and model-specific tokenizers
    TOKENIZER_VARIANCE_BUFFER = int(context_window * 0.10)
    max_conversation_tokens = context_window - system_tokens - conversation_prompt_tokens - request_tokens - SUMMARY_OUTPUT_TOKENS - TOKENIZER_VARIANCE_BUFFER

    # Truncate conversation_text to fit within budget
    conversation_text = _truncate_to_token_budget(conversation_text, max_conversation_tokens)

    # Use 3-message structure to clearly separate conversation from summarization request
    summarizer_messages = [
        {"role": "system", "content": SUMMARIZER_SYSTEM_PROMPT},
        {"role": "user", "content": SUMMARIZER_CONVERSATION_PROMPT.format(conversation=conversation_text)},
        {"role": "user", "content": SUMMARIZER_REQUEST_PROMPT},
    ]

    # Use the backend's stream_with_tools() - works uniformly for all backends
    # Pass _compression_retry=True to prevent recursive compression attempts
    # Collect content chunks into final response
    # Filter out mcp_status chunks (connection messages, tool registration, etc.)
    content_parts = []
    async for chunk in backend.stream_with_tools(summarizer_messages, tools=[], _compression_retry=True):
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
            # Only save message count, not the full messages (input file has the originals)
            data["compressed_message_count"] = len(compressed_result)

        if summary is not None:
            data["summary"] = summary
            data["summary_length_chars"] = len(summary)

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

        logger.debug(f"[CompressionUtils] Saved compression debug data: {filepath}")

    except Exception as e:
        logger.warning(
            f"[CompressionUtils] Failed to save compression debug: {e}",
            exc_info=True,
        )
