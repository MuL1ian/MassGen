from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from starlette.responses import JSONResponse, StreamingResponse

from massgen.tool.workflow_toolkits.base import WORKFLOW_TOOL_NAMES

from ..engine import Engine, MassGenEngine
from ..settings import ServerSettings
from .adapter import accumulate_stream_to_response, stream_to_sse_frames
from .model_router import resolve_model
from .schema import ChatCompletionRequest
from .sse import SSE_HEADERS, format_done, format_sse


def _extract_client_tool_names(tools: Optional[List[Dict[str, Any]]]) -> List[str]:
    if not tools:
        return []
    names: List[str] = []
    for t in tools:
        if not isinstance(t, dict):
            continue
        fn = t.get("function") if isinstance(t.get("function"), dict) else {}
        name = fn.get("name")
        if isinstance(name, str) and name.strip():
            names.append(name.strip())
    return names


def build_router(*, engine: Optional[Engine] = None, settings: Optional[ServerSettings] = None) -> APIRouter:
    router = APIRouter()
    settings = settings or ServerSettings.from_env()
    engine = engine or MassGenEngine(default_config=settings.default_config, default_model=settings.default_model)

    @router.get("/health")
    async def health() -> Dict[str, Any]:
        import massgen

        return {"status": "ok", "service": "massgen-server", "version": getattr(massgen, "__version__", "unknown")}

    @router.post("/v1/chat/completions")
    async def chat_completions(req: ChatCompletionRequest, request: Request):
        # Guard against collisions with MassGen workflow tools.
        tool_names = _extract_client_tool_names(req.tools)
        collisions = sorted(set(tool_names).intersection(set(WORKFLOW_TOOL_NAMES)))
        if collisions:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Client tool names collide with reserved MassGen workflow tools",
                    "collisions": collisions,
                },
            )

        resolved = resolve_model(
            req.model or "massgen",
            default_config=settings.default_config,
            default_model=settings.default_model,
        )

        request_id = request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex}"
        model_for_response = resolved.override_model or (settings.default_model or req.model or "massgen")

        async def _stream():
            response_id = f"chatcmpl_{uuid.uuid4().hex}"
            stream_it = engine.stream_chat(req, resolved, request_id=request_id)
            async for frame in stream_to_sse_frames(stream_it, model=model_for_response, response_id=response_id):
                yield format_sse(frame)
            yield format_done()

        if req.stream:
            return StreamingResponse(
                _stream(),
                media_type="text/event-stream",
                headers=SSE_HEADERS,
            )

        stream_it = engine.stream_chat(req, resolved, request_id=request_id)
        resp, _finish = await accumulate_stream_to_response(stream_it, model=model_for_response)
        return JSONResponse(resp)

    return router


