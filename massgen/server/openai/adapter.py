# -*- coding: utf-8 -*-
from __future__ import annotations

import time
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from massgen.backend.base import StreamChunk
from massgen.tool.workflow_toolkits.base import WORKFLOW_TOOL_NAMES


def _extract_tool_name(tool_call: Dict[str, Any]) -> str:
    fn = tool_call.get("function") or {}
    return fn.get("name") or ""


def _normalize_tool_call(tool_call: Dict[str, Any], idx: int) -> Dict[str, Any]:
    """
    Ensure a tool call matches OpenAI chat.completions shape:
    {"id","type":"function","function":{"name","arguments":<string>}}
    """
    tc = dict(tool_call)
    tc.setdefault("id", f"call_{idx}")
    tc.setdefault("type", "function")
    fn = dict(tc.get("function") or {})
    fn.setdefault("name", "")

    args = fn.get("arguments", {})
    # OpenAI commonly represents arguments as a string; tolerate dicts from MassGen.
    if not isinstance(args, str):
        try:
            import json

            args = json.dumps(args, separators=(",", ":"), ensure_ascii=False)
        except Exception:
            args = "{}"
    fn["arguments"] = args
    tc["function"] = fn
    return tc


def filter_external_tool_calls(tool_calls: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    if not tool_calls:
        return []
    filtered: List[Dict[str, Any]] = []
    for idx, tc in enumerate(tool_calls):
        name = _extract_tool_name(tc)
        if name in WORKFLOW_TOOL_NAMES:
            continue
        filtered.append(_normalize_tool_call(tc, idx))
    return filtered


def _is_trace_content(chunk: StreamChunk) -> bool:
    """Identify content chunks that are coordination traces (orchestrator/system)."""
    source = getattr(chunk, "source", None)
    return source is None or str(source) in {"orchestrator", "system"}


def build_chat_completion_response(
    *,
    content: str,
    tool_calls: List[Dict[str, Any]],
    model: str,
    finish_reason: str,
    created: Optional[int] = None,
    response_id: Optional[str] = None,
    reasoning_content: Optional[str] = None,
) -> Dict[str, Any]:
    created = created or int(time.time())
    response_id = response_id or f"chatcmpl_{uuid.uuid4().hex}"

    message: Dict[str, Any] = {"role": "assistant"}
    if content:
        message["content"] = content
    else:
        message["content"] = ""  # keep shape stable
    if tool_calls:
        message["tool_calls"] = tool_calls
    if reasoning_content:
        message["reasoning_content"] = reasoning_content

    return {
        "id": response_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": finish_reason,
            },
        ],
    }


def _format_trace_chunk(chunk: StreamChunk) -> Optional[str]:
    """Format a non-content chunk into a trace string for reasoning_content."""
    t = str(chunk.type)
    parts: List[str] = []

    # Include source/agent info if available
    source = getattr(chunk, "source", None) or "system"

    if t == "reasoning" and chunk.content:
        parts.append(f"[{source}] {chunk.content}")
    elif t == "reasoning_done":
        text = getattr(chunk, "reasoning_text", None)
        if text:
            parts.append(f"[{source}] {text}")
    elif t == "agent_status":
        status = getattr(chunk, "agent_status", None) or getattr(chunk, "content", None)
        if status:
            parts.append(f"[{source}] Status: {status}")
    elif t == "status":
        status = getattr(chunk, "content", None)
        if status:
            parts.append(f"[system] {status}")
    elif t == "vote_result":
        vote = getattr(chunk, "vote_result", None) or getattr(chunk, "content", None)
        if vote:
            parts.append(f"[orchestrator] Vote: {vote}")
    elif t == "coordination":
        coord = getattr(chunk, "content", None)
        if coord:
            parts.append(f"[orchestrator] {coord}")
    elif t not in ("content", "tool_calls", "error", "done"):
        # Catch-all for any other chunk types
        text = getattr(chunk, "content", None) or getattr(chunk, "text", None)
        if text:
            parts.append(f"[{source}:{t}] {text}")

    return "\n".join(parts) if parts else None


async def accumulate_stream_to_response(
    stream: AsyncIterator[StreamChunk],
    *,
    model: str,
) -> Tuple[Dict[str, Any], str]:
    content_parts: List[str] = []
    reasoning_parts: List[str] = []
    tool_calls: List[Dict[str, Any]] = []
    finish_reason = "stop"
    usage: Optional[Dict[str, Any]] = None
    tool_calls_received = False

    async for chunk in stream:
        t = str(chunk.type)
        if t == "usage":
            usage = getattr(chunk, "usage", None) or getattr(chunk, "content", None)
            continue

        if tool_calls_received and t not in ("done", "usage"):
            # After tool calls, only usage/done metadata should arrive.
            continue

        if t == "content" and chunk.content:
            if _is_trace_content(chunk):
                reasoning_parts.append(f"[{getattr(chunk, 'source', 'system') or 'system'}] {chunk.content}")
            else:
                content_parts.append(chunk.content)
        elif t == "tool_calls":
            tool_calls = filter_external_tool_calls(getattr(chunk, "tool_calls", None))
            if tool_calls:
                finish_reason = "tool_calls"
                tool_calls_received = True
        elif t == "error":
            finish_reason = "stop"
            content_parts.append(getattr(chunk, "error", "") or "Error")
        elif t == "done":
            break
        else:
            # Collect all other chunks as reasoning traces
            trace = _format_trace_chunk(chunk)
            if trace:
                reasoning_parts.append(trace)

    content = "".join(content_parts)
    reasoning_content = "\n".join(reasoning_parts) if reasoning_parts else None
    resp = build_chat_completion_response(
        content=content,
        tool_calls=tool_calls,
        model=model,
        finish_reason=finish_reason,
        reasoning_content=reasoning_content,
    )
    if usage:
        resp["usage"] = usage
    return resp, finish_reason


def make_sse_chunk(
    *,
    response_id: str,
    model: str,
    delta: Dict[str, Any],
    finish_reason: Optional[str] = None,
    created: Optional[int] = None,
    usage: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    created = created or int(time.time())
    payload: Dict[str, Any] = {
        "id": response_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": delta,
                "finish_reason": finish_reason,
            },
        ],
    }
    if usage is not None:
        payload["usage"] = usage
    return payload


async def stream_to_sse_frames(
    stream: AsyncIterator[StreamChunk],
    *,
    model: str,
    response_id: str,
) -> AsyncIterator[Dict[str, Any]]:
    """
    Convert StreamChunks into OpenAI-compatible SSE frame payload dicts.

    For maximum client compatibility, we buffer all chunks first, then:
    1. Emit role frame
    2. Emit reasoning_content (all traces) in one chunk
    3. Stream content chunks
    4. Emit tool_calls if any
    5. Emit finish frame
    """
    # Buffer all chunks first
    content_chunks: List[str] = []
    reasoning_parts: List[str] = []
    tool_calls: List[Dict[str, Any]] = []
    error_content: Optional[str] = None
    usage_data: Optional[Dict[str, Any]] = None

    async for chunk in stream:
        t = str(chunk.type)
        if t == "usage":
            usage_data = getattr(chunk, "usage", None) or getattr(chunk, "content", None)
            continue
        if t == "content" and chunk.content:
            if _is_trace_content(chunk):
                reasoning_parts.append(f"[{getattr(chunk, 'source', 'system') or 'system'}] {chunk.content}")
            else:
                content_chunks.append(chunk.content)
        elif t == "tool_calls":
            tool_calls = filter_external_tool_calls(getattr(chunk, "tool_calls", None))
            if tool_calls:
                pass
        elif t == "error":
            error_content = getattr(chunk, "error", None) or "Error"
        elif t == "done":
            break
        else:
            # Collect all other chunks as reasoning traces
            trace = _format_trace_chunk(chunk)
            if trace:
                reasoning_parts.append(trace)

    # Initial role frame (matches OpenAI behavior)
    yield make_sse_chunk(
        response_id=response_id,
        model=model,
        delta={"role": "assistant"},
        finish_reason=None,
    )

    # Emit reasoning_content first if present
    if reasoning_parts:
        reasoning_content = "\n".join(reasoning_parts)
        yield make_sse_chunk(
            response_id=response_id,
            model=model,
            delta={"reasoning_content": reasoning_content},
            finish_reason=None,
        )

    # Stream content
    for content_part in content_chunks:
        yield make_sse_chunk(
            response_id=response_id,
            model=model,
            delta={"content": content_part},
            finish_reason=None,
        )

    # Handle error content
    if error_content:
        yield make_sse_chunk(
            response_id=response_id,
            model=model,
            delta={"content": error_content},
            finish_reason="stop",
            usage=usage_data,
        )
        return

    # Emit tool_calls if any
    if tool_calls:
        delta_tool_calls = []
        for i, tc in enumerate(tool_calls):
            delta_tool_calls.append(
                {
                    "index": i,
                    "id": tc.get("id"),
                    "type": "function",
                    "function": {
                        "name": (tc.get("function") or {}).get("name"),
                        "arguments": (tc.get("function") or {}).get("arguments"),
                    },
                },
            )
        yield make_sse_chunk(
            response_id=response_id,
            model=model,
            delta={"tool_calls": delta_tool_calls},
            finish_reason=None,
        )
        yield make_sse_chunk(
            response_id=response_id,
            model=model,
            delta={},
            finish_reason="tool_calls",
            usage=usage_data,
        )
        return

    # Normal stop
    yield make_sse_chunk(
        response_id=response_id,
        model=model,
        delta={},
        finish_reason="stop",
        usage=usage_data,
    )
