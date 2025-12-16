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

# System prompt for the compression summarizer
SUMMARIZER_SYSTEM_PROMPT = """You are a conversation summarizer. Your task is to create a concise summary of a conversation that preserves:
1. The main task or goal
2. Key decisions and progress made
3. Important information discovered (file contents, tool outputs, etc.)
4. Any pending work or next steps

Be concise but complete. The summary will replace the original messages, so include anything essential for continuing the task."""

SUMMARIZER_USER_PROMPT = """Please summarize the following conversation. Focus on preserving information needed to continue the task.

<conversation>
{conversation}
</conversation>

Provide a structured summary with sections for:
- Task/Goal
- Progress Made
- Key Information
- Next Steps (if any)"""


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

    # Calculate how many messages to preserve
    total_messages = len(messages)
    preserve_count = max(1, int(total_messages * target_ratio))

    # Determine which messages to compress vs preserve
    if preserve_count < total_messages:
        messages_to_compress = messages[:-preserve_count]
        recent_messages = messages[-preserve_count:]
    else:
        messages_to_compress = messages[:-1]
        recent_messages = messages[-1:]

    # If there's nothing to compress, return original
    if not messages_to_compress:
        logger.warning("[CompressionUtils] No messages to compress, returning original")
        return messages

    # Build context for summarization
    summary_context = _format_messages_for_summary(messages_to_compress)
    if buffer_content:
        summary_context += f"\n\n[Partial response when context limit hit]\n{buffer_content}"

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

    # Preserve system message if present
    if messages and messages[0].get("role") == "system":
        result.append(messages[0])

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


async def _generate_summary(backend: "BackendBase", conversation_text: str) -> str:
    """Generate a summary using the backend's API.

    Args:
        backend: The backend to use for the API call
        conversation_text: Formatted conversation text to summarize

    Returns:
        Summary text
    """
    summarizer_messages = [
        {"role": "system", "content": SUMMARIZER_SYSTEM_PROMPT},
        {"role": "user", "content": SUMMARIZER_USER_PROMPT.format(conversation=conversation_text)},
    ]

    # Use the backend's client to make a simple completion call
    # This works for any backend that has a chat completions-compatible client
    client = backend._client
    model = backend.config.get("model", "gpt-4o-mini")

    # Try chat completions first (works for most backends)
    if hasattr(client, "chat") and hasattr(client.chat, "completions"):
        response = await client.chat.completions.create(
            model=model,
            messages=summarizer_messages,
            max_tokens=2000,
            temperature=0.3,
        )
        return response.choices[0].message.content

    # Try responses API (for OpenAI Response API backend)
    elif hasattr(client, "responses"):
        response = await client.responses.create(
            model=model,
            input=summarizer_messages,
        )
        return response.output_text or "[Summary generation failed]"

    else:
        raise ValueError(f"Backend {type(backend)} does not have a compatible client for summarization")


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
