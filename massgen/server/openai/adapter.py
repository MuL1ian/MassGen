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


def build_chat_completion_response(
    *,
    content: str,
    tool_calls: List[Dict[str, Any]],
    model: str,
    finish_reason: str,
    created: Optional[int] = None,
    response_id: Optional[str] = None,
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


async def accumulate_stream_to_response(
    stream: AsyncIterator[StreamChunk],
    *,
    model: str,
) -> Tuple[Dict[str, Any], str]:
    content_parts: List[str] = []
    tool_calls: List[Dict[str, Any]] = []
    finish_reason = "stop"

    async for chunk in stream:
        t = str(chunk.type)
        if t == "content" and chunk.content:
            content_parts.append(chunk.content)
        elif t == "tool_calls":
            tool_calls = filter_external_tool_calls(getattr(chunk, "tool_calls", None))
            if tool_calls:
                finish_reason = "tool_calls"
        elif t == "error":
            finish_reason = "stop"
            content_parts.append(getattr(chunk, "error", "") or "Error")
        elif t == "done":
            break
        else:
            # Drop non-OpenAI chunks by default (status, debug, etc.)
            continue

        if finish_reason == "tool_calls":
            # In OpenAI semantics, a tool call ends the turn.
            break

    content = "".join(content_parts)
    resp = build_chat_completion_response(
        content=content,
        tool_calls=tool_calls,
        model=model,
        finish_reason=finish_reason,
    )
    return resp, finish_reason


def make_sse_chunk(
    *,
    response_id: str,
    model: str,
    delta: Dict[str, Any],
    finish_reason: Optional[str] = None,
    created: Optional[int] = None,
) -> Dict[str, Any]:
    created = created or int(time.time())
    return {
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


async def stream_to_sse_frames(
    stream: AsyncIterator[StreamChunk],
    *,
    model: str,
    response_id: str,
) -> AsyncIterator[Dict[str, Any]]:
    """
    Convert StreamChunks into OpenAI-compatible SSE frame payload dicts.
    """
    # Initial role frame (matches OpenAI behavior)
    yield make_sse_chunk(
        response_id=response_id,
        model=model,
        delta={"role": "assistant"},
        finish_reason=None,
    )

    tool_calls: List[Dict[str, Any]] = []
    async for chunk in stream:
        t = str(chunk.type)
        if t == "content" and chunk.content:
            yield make_sse_chunk(
                response_id=response_id,
                model=model,
                delta={"content": chunk.content},
                finish_reason=None,
            )
        elif t == "tool_calls":
            tool_calls = filter_external_tool_calls(getattr(chunk, "tool_calls", None))
            if tool_calls:
                # Emit as delta.tool_calls (single-shot; no incremental args streaming)
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
                # Then final chunk with finish_reason=tool_calls
                yield make_sse_chunk(
                    response_id=response_id,
                    model=model,
                    delta={},
                    finish_reason="tool_calls",
                )
                return
        elif t == "error":
            # Surface as content and stop
            err = getattr(chunk, "error", None) or "Error"
            yield make_sse_chunk(
                response_id=response_id,
                model=model,
                delta={"content": err},
                finish_reason="stop",
            )
            return
        elif t == "done":
            break
        else:
            continue

    # Normal stop
    yield make_sse_chunk(
        response_id=response_id,
        model=model,
        delta={},
        finish_reason="stop",
    )


