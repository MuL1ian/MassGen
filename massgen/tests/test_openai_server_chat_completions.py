# -*- coding: utf-8 -*-
import json
from typing import AsyncIterator

from fastapi.testclient import TestClient

from massgen.backend.base import StreamChunk
from massgen.server.app import create_app
from massgen.server.openai.model_router import ResolvedModel


class FakeEngine:
    async def stream_chat(self, req, resolved: ResolvedModel, *, request_id: str) -> AsyncIterator[StreamChunk]:
        _ = (req, resolved, request_id)
        yield StreamChunk(type="content", content="Hello", source="agent_1")
        yield StreamChunk(type="content", content=" world", source="agent_1")
        yield StreamChunk(
            type="usage",
            usage={"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
            source="orchestrator",
        )
        yield StreamChunk(type="done")


class FakeEngineWithReasoning:
    """Engine that produces reasoning/trace chunks before final content."""

    async def stream_chat(self, req, resolved: ResolvedModel, *, request_id: str) -> AsyncIterator[StreamChunk]:
        _ = (req, resolved, request_id)
        # Emit trace chunks (should go to reasoning_content)
        yield StreamChunk(type="status", content="Starting coordination...", source="system")
        yield StreamChunk(type="reasoning", content="Agent thinking...", source="agent_1")
        yield StreamChunk(type="agent_status", content="Generating answer", source="agent_1")
        # Final content
        yield StreamChunk(type="content", content="The answer is 42.", source="agent_1")
        yield StreamChunk(
            type="usage",
            usage={"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
            source="orchestrator",
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
    assert data["usage"] == {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14}


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
        last_payload = None
        for data_line in _iter_sse_data_lines(resp):
            if data_line == "[DONE]":
                saw_done = True
                break
            payload = json.loads(data_line)
            last_payload = payload
            delta = payload["choices"][0]["delta"]
            got += delta.get("content", "") or ""
        assert saw_done is True
        assert got == "Hello world"
        assert last_payload is not None
        assert last_payload.get("usage") == {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14}


def test_chat_completions_reasoning_content_non_stream():
    """Test that non-content chunks are collected into reasoning_content."""
    app = create_app(engine=FakeEngineWithReasoning())
    client = TestClient(app)
    resp = client.post(
        "/v1/chat/completions",
        json={
            "model": "massgen",
            "messages": [{"role": "user", "content": "What is the meaning of life?"}],
            "stream": False,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    message = data["choices"][0]["message"]

    # Final content should only contain the answer
    assert message["content"] == "The answer is 42."

    # reasoning_content should contain traces
    assert "reasoning_content" in message
    reasoning = message["reasoning_content"]
    assert "Starting coordination" in reasoning
    assert "Agent thinking" in reasoning
    assert "Generating answer" in reasoning
    assert data["usage"] == {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14}


def test_chat_completions_reasoning_content_streaming():
    """Test that reasoning_content is emitted before content in streaming."""
    app = create_app(engine=FakeEngineWithReasoning())
    client = TestClient(app)
    with client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "massgen",
            "messages": [{"role": "user", "content": "What is the meaning of life?"}],
            "stream": True,
        },
    ) as resp:
        assert resp.status_code == 200
        content = ""
        reasoning = ""
        saw_reasoning_first = False
        first_non_role_chunk = True
        last_payload = None

        for data_line in _iter_sse_data_lines(resp):
            if data_line == "[DONE]":
                break
            payload = json.loads(data_line)
            last_payload = payload
            delta = payload["choices"][0]["delta"]

            # Check if reasoning comes before content
            if "reasoning_content" in delta:
                reasoning = delta["reasoning_content"]
                if first_non_role_chunk:
                    saw_reasoning_first = True
                first_non_role_chunk = False
            if "content" in delta:
                content += delta["content"]
                first_non_role_chunk = False

        # Verify reasoning was emitted first and contains traces
        assert saw_reasoning_first, "reasoning_content should be emitted before content"
        assert "Starting coordination" in reasoning
        assert "Agent thinking" in reasoning

        # Verify final content
        assert content == "The answer is 42."
        assert last_payload is not None
        assert last_payload.get("usage") == {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14}
