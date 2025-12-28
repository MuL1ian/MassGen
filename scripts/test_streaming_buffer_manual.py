#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manual test script to inspect streaming buffer content.

This script:
1. Creates a backend instance
2. Streams a response with tool usage
3. Prints the accumulated buffer content

Usage:
    uv run python scripts/test_streaming_buffer_manual.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_response_backend():
    """Test ResponseBackend buffer accumulation."""
    print("=" * 80)
    print("Testing ResponseBackend Streaming Buffer")
    print("=" * 80 + "\n")

    from massgen.backend.response import ResponseBackend

    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set, skipping ResponseBackend test")
        return

    backend = ResponseBackend(api_key=os.getenv("OPENAI_API_KEY"))

    messages = [
        {"role": "user", "content": "What is 2+2? Think through it step by step."},
    ]

    print("Streaming response...")
    print("-" * 40)

    async for chunk in backend.stream_with_tools(messages, [], model="gpt-5-nano"):
        if chunk.type == "content":
            print(chunk.content, end="", flush=True)
        elif chunk.type == "reasoning":
            print(f"[REASONING] {chunk.content}", end="", flush=True)
        elif chunk.type == "done":
            break

    print("\n" + "-" * 40)
    print("\nBuffer Content:")
    print("=" * 40)
    buffer = backend._get_streaming_buffer()
    if buffer:
        print(buffer)
    else:
        print("(empty)")
    print("=" * 40)


async def test_chat_completions_backend():
    """Test ChatCompletionsBackend buffer accumulation."""
    print("\n" + "=" * 80)
    print("Testing ChatCompletionsBackend Streaming Buffer")
    print("=" * 80 + "\n")

    from massgen.backend.chat_completions import ChatCompletionsBackend

    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set, skipping ChatCompletionsBackend test")
        return

    backend = ChatCompletionsBackend(api_key=os.getenv("OPENAI_API_KEY"))

    # Use a tool to see tool call tracking
    tools = [
        {
            "type": "function",
            "name": "get_weather",
            "description": "Get weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"},
                },
                "required": ["location"],
            },
        },
    ]

    messages = [
        {"role": "user", "content": "What's the weather in Tokyo?"},
    ]

    print("Streaming response with tool...")
    print("-" * 40)

    async for chunk in backend.stream_with_tools(messages, tools, model="gpt-5-nano"):
        if chunk.type == "content":
            print(chunk.content, end="", flush=True)
        elif chunk.type == "tool_calls":
            print(f"\n[TOOL CALLS] {chunk.tool_calls}")
        elif chunk.type == "done":
            break

    print("\n" + "-" * 40)
    print("\nBuffer Content:")
    print("=" * 40)
    buffer = backend._get_streaming_buffer()
    if buffer:
        print(buffer)
    else:
        print("(empty)")
    print("=" * 40)


async def test_claude_backend():
    """Test ClaudeBackend buffer accumulation."""
    print("\n" + "=" * 80)
    print("Testing ClaudeBackend Streaming Buffer")
    print("=" * 80 + "\n")

    from massgen.backend.claude import ClaudeBackend

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set, skipping ClaudeBackend test")
        return

    backend = ClaudeBackend(api_key=os.getenv("ANTHROPIC_API_KEY"))

    messages = [
        {"role": "user", "content": "What is 2+2? Be brief."},
    ]

    print("Streaming response...")
    print("-" * 40)

    async for chunk in backend.stream_with_tools(messages, [], model="claude-haiku-4-5-20251001"):
        if chunk.type == "content":
            print(chunk.content, end="", flush=True)
        elif chunk.type == "done":
            break

    print("\n" + "-" * 40)
    print("\nBuffer Content:")
    print("=" * 40)
    buffer = backend._get_streaming_buffer()
    if buffer:
        print(buffer)
    else:
        print("(empty)")
    print("=" * 40)


async def test_buffer_directly():
    """Test buffer methods directly without API calls."""
    print("\n" + "=" * 80)
    print("Testing Buffer Methods Directly (No API)")
    print("=" * 80 + "\n")

    from massgen.backend._streaming_buffer_mixin import StreamingBufferMixin

    class MockBackend(StreamingBufferMixin):
        def __init__(self):
            super().__init__()

    backend = MockBackend()

    # Simulate a realistic streaming sequence
    print("Simulating streaming sequence...")

    # Reasoning
    backend._append_reasoning_to_buffer("Let me think about this problem...")
    backend._append_reasoning_to_buffer(" I need to analyze the request carefully.")

    # Regular content
    backend._append_to_streaming_buffer("I'll help you with that. ")

    # Tool call
    backend._append_tool_call_to_buffer(
        [
            {"name": "read_file", "arguments": {"path": "/src/main.py"}},
        ],
    )

    # Tool result
    backend._append_tool_to_buffer("read_file", "def main():\n    print('hello world')")

    # More content
    backend._append_to_streaming_buffer("The file contains a simple main function.")

    # Tool error
    backend._append_tool_call_to_buffer(
        [
            {"name": "write_file", "arguments": {"path": "/etc/passwd", "content": "test"}},
        ],
    )
    backend._append_tool_to_buffer("write_file", "Permission denied", is_error=True)

    # Final content
    backend._append_to_streaming_buffer(" Let me try a different approach.")

    print("\nBuffer Content:")
    print("=" * 60)
    buffer = backend._get_streaming_buffer()
    print(buffer)
    print("=" * 60)
    print(f"\nTotal buffer size: {len(buffer)} characters")


async def main():
    """Run all tests."""
    # Always run the direct test (no API needed)
    await test_buffer_directly()

    # Run API tests if keys are available
    if os.getenv("OPENAI_API_KEY"):
        await test_response_backend()
        await test_chat_completions_backend()
    else:
        print("\nSkipping OpenAI tests (OPENAI_API_KEY not set)")

    if os.getenv("ANTHROPIC_API_KEY"):
        await test_claude_backend()
    else:
        print("\nSkipping Claude tests (ANTHROPIC_API_KEY not set)")

    print("\n" + "=" * 80)
    print("All tests complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
