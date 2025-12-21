import json
from typing import AsyncIterator

from fastapi.testclient import TestClient

from massgen.backend.base import StreamChunk
from massgen.server.app import create_app
from massgen.server.openai.model_router import ResolvedModel


class FakeEngine:
    async def stream_chat(self, req, resolved: ResolvedModel, *, request_id: str) -> AsyncIterator[StreamChunk]:
        _ = (req, resolved, request_id)
        yield StreamChunk(type="content", content="Hello")
        yield StreamChunk(type="content", content=" world")
        yield StreamChunk(type="done")


def _iter_sse_data_lines(resp):
    for line in resp.iter_lines():
        if not line:
            continue
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        assert line.startswith("data: ")
        yield line[len("data: ") :]


def test_chat_completions_non_stream():
    app = create_app(engine=FakeEngine())
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
    assert data["object"] == "chat.completion"
    assert data["choices"][0]["message"]["role"] == "assistant"
    assert data["choices"][0]["message"]["content"] == "Hello world"
    assert data["choices"][0]["finish_reason"] == "stop"


def test_chat_completions_streaming():
    app = create_app(engine=FakeEngine())
    client = TestClient(app)
    with client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "massgen",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        },
    ) as resp:
        assert resp.status_code == 200
        got = ""
        saw_done = False
        for data_line in _iter_sse_data_lines(resp):
            if data_line == "[DONE]":
                saw_done = True
                break
            payload = json.loads(data_line)
            delta = payload["choices"][0]["delta"]
            got += delta.get("content", "") or ""
        assert saw_done is True
        assert got == "Hello world"


