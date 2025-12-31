# Context Compression Design

## Overview

MassGen implements reactive context compression to handle situations where the conversation exceeds a model's context window. When a context length error is detected, the system automatically compresses the conversation history and retries the request.

## Supported Backends

Context compression is supported across the following backends:

| Backend | Model | Context Window | Default Fill Ratio | Notes |
|---------|-------|----------------|-------------------|-------|
| OpenAI | gpt-4o-mini | 128k | 95% | Response API backend |
| Claude | claude-haiku-4-5 | 200k | 150% | Messages API, needs higher ratio due to large context |
| Gemini | gemini-2.0-flash | 1M | 95% | Native SDK, ~7.5% tokenizer variance vs tiktoken |
| OpenRouter | openai/gpt-4o-mini | 128k | 95% | ChatCompletions backend |
| Grok | grok-3-mini | 131k | 300% | Handles overflow gracefully, needs high ratio to trigger |

## Architecture

### Flow

1. **Detection**: When a streaming request fails with a context length error, `is_context_length_error()` identifies it
2. **Compression**: `compress_messages_for_recovery()` summarizes older messages while preserving recent ones
3. **Truncation**: If compression isn't sufficient, `_ensure_fits_context()` truncates the largest message
4. **Retry**: The compressed messages are sent with `_compression_retry=True` flag to prevent infinite loops

### Key Components

- `massgen/backend/_compression_utils.py`: Core compression logic
- `massgen/backend/_context_errors.py`: Error detection patterns for each provider
- `massgen/backend/base_with_custom_tool_and_mcp.py`: Compression handling in streaming
- `massgen/backend/gemini.py`: Gemini-specific `_compression_retry` handling
- `massgen/backend/claude.py`: Claude-specific `_compression_retry` handling
- `massgen/api_params_handler/_claude_api_params_handler.py`: Strips trailing whitespace from assistant messages

### Internal Flags

- `_compression_retry`: Passed to `stream_with_tools()` to prevent recursive compression
  - Must be extracted/popped from kwargs before API calls (causes Pydantic errors in Gemini, unknown arg errors in Claude)
  - Gemini stores in `self._compression_retry_flag` instance variable
  - Claude/base pops from kwargs at start of `_stream_without_custom_and_mcp_tools()`

### Tokenizer Variance

Different models use different tokenizers. Testing showed:
- Tiktoken estimates vs Gemini actual: ~7.5% variance
- A 10% safety buffer is applied when calculating truncation limits

### Claude-Specific Handling

Claude API rejects assistant messages ending with trailing whitespace. The Claude API params handler strips trailing whitespace from all assistant message content.

## Testing

### Unit Tests (pytest)

These run without API keys and are part of the normal test suite:

```bash
# Run all compression-related unit tests
uv run pytest massgen/tests/backend/test_compression_utils.py -v
uv run pytest massgen/tests/test_streaming_buffer.py -v

# Run memory compression tests
uv run pytest massgen/tests/memory/test_agent_compression.py -v
uv run pytest massgen/tests/memory/test_simple_compression.py -v
```

| Test File | What it Tests |
|-----------|--------------|
| `massgen/tests/backend/test_compression_utils.py` | Core compression: truncation, formatting, context fitting, error recovery |
| `massgen/tests/test_streaming_buffer.py` | StreamingBufferMixin: buffer clearing, appending, compression retry preservation |
| `massgen/tests/memory/test_agent_compression.py` | Agent-level compression integration |
| `massgen/tests/memory/test_simple_compression.py` | Basic compression scenarios |

### Manual Integration Tests (scripts/)

These require API keys and make real API calls. They are **excluded from pytest** and must be run manually.

#### Compression Backend Test

Tests reactive compression across all supported backends by filling context to trigger errors:

```bash
# Test all backends with per-backend optimal fill ratios
uv run python scripts/test_compression_backends.py

# Test specific backend
uv run python scripts/test_compression_backends.py --backend gemini

# Test with custom fill ratio
uv run python scripts/test_compression_backends.py --backend openai --fill-ratio 1.0

# List available backends with their default fill ratios
uv run python scripts/test_compression_backends.py --list-backends
```

**Required env vars**: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `XAI_API_KEY`

#### Streaming Buffer Reasoning Test

Tests that reasoning/thinking content is captured in the streaming buffer for compression recovery:

```bash
# Test all providers
uv run python scripts/test_streaming_buffer_reasoning.py

# Test specific provider
uv run python scripts/test_streaming_buffer_reasoning.py --provider claude
uv run python scripts/test_streaming_buffer_reasoning.py --provider gemini

# Custom prompt
uv run python scripts/test_streaming_buffer_reasoning.py --prompt "Explain quantum entanglement"
```

**Providers tested**: Claude (extended thinking), Gemini (thinking parts), OpenAI (reasoning summaries), OpenRouter

**Required env vars**: `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`

**Note**: Both scripts make real API calls and cost money.

### Test Results (December 23, 2025)

| Backend | Model | Fill Ratio | Tokens Sent | Result |
|---------|-------|------------|-------------|--------|
| openai | gpt-4o-mini | 95% | 149k | Compression triggered, succeeded |
| gemini | gemini-2.0-flash | 95% | 1.04M | Compression triggered, succeeded |
| openrouter | openai/gpt-4o-mini | 95% | 149k | Compression triggered, succeeded |
| claude | claude-haiku-4-5 | 150% | 298k | Compression triggered, succeeded |
| grok | grok-3-mini | 300% | 447k | Compression triggered, succeeded |

## Configuration

Context compression is enabled by default and cannot be disabled. The compression behavior adapts to each backend's context window size automatically.

## Future Work: Proactive Compression

A proactive "agent-driven" compression approach was designed but not implemented due to API limitations (providers only report token usage after requests complete, making it impossible to reliably prevent context overflow). See `proactive_compression_design.md` for the future vision and archived implementation code.

## Bugs Fixed

1. **Pydantic validation error (Gemini)**: `_compression_retry` was leaking into Gemini's config and causing validation errors. Fixed by extracting it into an instance variable before kwargs merge.

2. **Unknown argument error (Claude)**: `_compression_retry` was being passed to `messages.create()`. Fixed by popping it from kwargs in `_stream_without_custom_and_mcp_tools()`.

3. **Recursive compression**: The summarizer call was triggering compression again. Fixed by passing `_compression_retry=True` to the summarizer.

4. **Trailing whitespace (Claude)**: Claude API rejects assistant messages ending with whitespace. Fixed by stripping in the API params handler.

5. **Tokenizer variance**: Initial 25% buffer was too high. Reduced to 10% based on testing showing ~7.5% actual variance.
