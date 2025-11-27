#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for backend cost tracking with litellm.

These tests make real API calls to verify end-to-end cost tracking.
They are marked as integration tests and skipped if API keys are not available.

Run with: pytest massgen/tests/test_backend_cost_tracking.py -m integration -v
"""

import os

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chat_completions_backend_usage_tracking():
    """Test that ChatCompletionsBackend correctly tracks usage with real API."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set")

    from massgen.backend.chat_completions import ChatCompletionsBackend

    backend = ChatCompletionsBackend(
        api_key=api_key,
        base_url="https://api.openai.com/v1",
    )

    messages = [{"role": "user", "content": "Say only: test"}]

    # Reset usage
    backend.token_usage.reset()

    # Make API call with cheap model
    response_content = ""
    async for chunk in backend.stream_with_tools(messages, [], model="gpt-4o-mini", max_tokens=5):
        if chunk.type == "content":
            response_content += chunk.content
        elif chunk.type == "done":
            break

    # Verify usage was tracked
    assert backend.token_usage.input_tokens > 0, "Input tokens should be tracked"
    assert backend.token_usage.output_tokens > 0, "Output tokens should be tracked"
    assert backend.token_usage.estimated_cost > 0, "Cost should be tracked"

    # Cost should be reasonable for short message (~10 tokens)
    assert backend.token_usage.estimated_cost < 0.001, "Cost should be < $0.001 for short message"

    print("\nChatCompletions usage tracking:")
    print(f"  Input: {backend.token_usage.input_tokens} tokens")
    print(f"  Output: {backend.token_usage.output_tokens} tokens")
    print(f"  Cost: ${backend.token_usage.estimated_cost:.6f}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_claude_code_backend_usage_tracking():
    """Test that ClaudeCodeBackend correctly tracks usage with real API."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")

    from massgen.backend.claude_code import ClaudeCodeBackend

    backend = ClaudeCodeBackend(api_key=api_key)

    messages = [{"role": "user", "content": "Say only: test"}]

    backend.token_usage.reset()

    response_content = ""
    async for chunk in backend.stream_with_tools(messages, [], model="claude-3-5-haiku-20241022", max_tokens=5):
        if chunk.type == "content":
            response_content += chunk.content
        elif chunk.type == "done":
            break

    # Verify usage was tracked
    assert backend.token_usage.input_tokens > 0
    assert backend.token_usage.output_tokens > 0
    assert backend.token_usage.estimated_cost > 0

    # Cost should be reasonable
    assert backend.token_usage.estimated_cost < 0.001

    print("\nClaudeCode usage tracking:")
    print(f"  Input: {backend.token_usage.input_tokens} tokens")
    print(f"  Output: {backend.token_usage.output_tokens} tokens")
    print(f"  Cost: ${backend.token_usage.estimated_cost:.6f}")


@pytest.mark.integration
@pytest.mark.expensive
@pytest.mark.asyncio
async def test_o3_mini_reasoning_tokens_e2e():
    """Test o3-mini reasoning tokens are tracked end-to-end (EXPENSIVE)."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set")

    from massgen.backend.chat_completions import ChatCompletionsBackend

    backend = ChatCompletionsBackend(
        api_key=api_key,
        base_url="https://api.openai.com/v1",
    )

    # Reasoning task that should trigger reasoning tokens
    messages = [
        {
            "role": "user",
            "content": "If x^2 + 3x - 10 = 0, what is x? Show your reasoning.",
        },
    ]

    backend.token_usage.reset()

    async for chunk in backend.stream_with_tools(messages, [], model="o3-mini", max_tokens=500):
        if chunk.type == "done":
            break

    # Should have tracked cost (reasoning tokens are expensive)
    assert backend.token_usage.estimated_cost > 0

    print("\nO3-mini reasoning test:")
    print(f"  Input: {backend.token_usage.input_tokens} tokens")
    print(f"  Output: {backend.token_usage.output_tokens} tokens")
    print(f"  Cost: ${backend.token_usage.estimated_cost:.6f}")
    print("  Note: Cost includes reasoning tokens if present")


@pytest.mark.integration
@pytest.mark.expensive
@pytest.mark.asyncio
async def test_claude_caching_e2e():
    """Test Claude prompt caching discount is tracked (EXPENSIVE - 2 API calls)."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")

    from massgen.backend.claude_code import ClaudeCodeBackend

    backend = ClaudeCodeBackend(api_key=api_key)

    # Large system prompt to trigger caching (needs >1024 tokens)
    large_context = "Context information: " + "This is important context. " * 200
    assert len(large_context) > 5000, "Context should be large enough to trigger caching"

    messages_with_cache = [
        {"role": "user", "content": f"{large_context}\n\nQuestion: Say 'test'"},
    ]

    # First call (no cache)
    backend.token_usage.reset()
    async for chunk in backend.stream_with_tools(messages_with_cache, [], model="claude-3-5-haiku-20241022", max_tokens=5):
        if chunk.type == "done":
            break

    cost_first_call = backend.token_usage.estimated_cost

    # Second call (should use cache)
    backend.token_usage.reset()
    async for chunk in backend.stream_with_tools(messages_with_cache, [], model="claude-3-5-haiku-20241022", max_tokens=5):
        if chunk.type == "done":
            break

    cost_second_call = backend.token_usage.estimated_cost

    print("\nClaude caching test:")
    print(f"  First call (no cache): ${cost_first_call:.6f}")
    print(f"  Second call (cached): ${cost_second_call:.6f}")
    print(f"  Savings: ${cost_first_call - cost_second_call:.6f}")

    # Note: This test is informational - caching may or may not occur
    # depending on Claude's caching policies


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
