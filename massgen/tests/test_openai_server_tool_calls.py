# -*- coding: utf-8 -*-
import json
from typing import AsyncIterator

from fastapi.testclient import TestClient

from massgen.backend.base import StreamChunk
from massgen.server.app import create_app
from massgen.server.openai.model_router import ResolvedModel
from massgen.tool.workflow_toolkits.base import WORKFLOW_TOOL_NAMES


class FakeToolCallEngine:
    def __init__(self, *, tool_name: str):
        self._tool_name = tool_name

    async def stream_chat(self, req, resolved: ResolvedModel, *, request_id: str) -> AsyncIterator[StreamChunk]:
        _ = (req, resolved, request_id)
        yield StreamChunk(
            type="tool_calls",
            tool_calls=[
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": self._tool_name, "arguments": {"x": 1}},
                },
            ],
        )
        yield StreamChunk(type="done")


def _iter_sse_data_lines(resp):
    for line in resp.iter_lines():
        if not line:
            continue
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        assert line.startswith("data: ")
        yield line[len("data: ") :]


def test_tool_calls_non_stream_finish_reason_tool_calls():
    app = create_app(engine=FakeToolCallEngine(tool_name="client_tool"))
    client = TestClient(app)
    resp = client.post(
        "/v1/chat/completions",
        json={
            "model": "massgen",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": False,
            "tools": [
                {
                    "type": "function",
                    "function": {"name": "client_tool", "description": "x", "parameters": {"type": "object"}},
                },
            ],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["choices"][0]["finish_reason"] == "tool_calls"
    msg = data["choices"][0]["message"]
    assert msg["role"] == "assistant"
    assert msg["tool_calls"][0]["function"]["name"] == "client_tool"


def test_tool_calls_streaming():
    app = create_app(engine=FakeToolCallEngine(tool_name="client_tool"))
    client = TestClient(app)
    with client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "massgen",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
            "tools": [
                {
                    "type": "function",
                    "function": {"name": "client_tool", "description": "x", "parameters": {"type": "object"}},
                },
            ],
        },
    ) as resp:
        assert resp.status_code == 200
        saw_tool_calls = False
        saw_finish = False
        saw_done = False
        for data_line in _iter_sse_data_lines(resp):
            if data_line == "[DONE]":
                saw_done = True
                break
            payload = json.loads(data_line)
            choice = payload["choices"][0]
            delta = choice["delta"]
            if "tool_calls" in delta:
                saw_tool_calls = True
            if choice.get("finish_reason") == "tool_calls":
                saw_finish = True
        assert saw_tool_calls is True
        assert saw_finish is True
        assert saw_done is True


def test_internal_workflow_tools_not_surfaced():
    internal_name = next(iter(WORKFLOW_TOOL_NAMES))
    app = create_app(engine=FakeToolCallEngine(tool_name=internal_name))
    client = TestClient(app)
    resp = client.post(
        "/v1/chat/completions",
        json={
            "model": "massgen",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": False,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    # Tool call should be filtered; default to stop with empty content.
    assert data["choices"][0]["finish_reason"] == "stop"
    assert data["choices"][0]["message"]["tool_calls"] if "tool_calls" in data["choices"][0]["message"] else [] == []


def test_tool_name_collision_rejected():
    internal_name = next(iter(WORKFLOW_TOOL_NAMES))
    app = create_app(engine=FakeToolCallEngine(tool_name="client_tool"))
    client = TestClient(app)
    resp = client.post(
        "/v1/chat/completions",
        json={
            "model": "massgen",
            "messages": [{"role": "user", "content": "hi"}],
            "tools": [{"type": "function", "function": {"name": internal_name, "parameters": {"type": "object"}}}],
        },
    )
    assert resp.status_code == 400
