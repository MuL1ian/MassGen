# -*- coding: utf-8 -*-
"""Regression coverage for ChatCompletionsBackend provider wiring."""

import pytest

from massgen.backend import ChatCompletionsBackend


def test_openai_backend_defaults():
    """Default backend should use generic provider settings."""
    backend = ChatCompletionsBackend()
    assert backend.get_provider_name() == "ChatCompletion"
    assert "base_url" not in backend.config
    assert backend.estimate_tokens("Hello world, how are you doing today?") > 0
    assert backend.calculate_cost(1000, 500, "gpt-4o-mini") >= 0


def test_together_ai_backend():
    """Provider should be inferred from Together base URL."""
    backend = ChatCompletionsBackend(
        base_url="https://api.together.xyz/v1",
        api_key="test-key",
    )
    assert backend.get_provider_name() == "Together AI"
    assert backend.config["base_url"] == "https://api.together.xyz/v1"
    assert backend.calculate_cost(1000, 500, "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo") >= 0


def test_cerebras_backend():
    """Provider should be inferred from Cerebras base URL."""
    backend = ChatCompletionsBackend(
        base_url="https://api.cerebras.ai/v1",
        api_key="test-key",
    )
    assert backend.get_provider_name() == "Cerebras AI"
    assert backend.config["base_url"] == "https://api.cerebras.ai/v1"


@pytest.mark.skip(reason="Backend API drift: convert_tools_to_chat_completions_format method was removed from ChatCompletionsBackend")
def test_tool_conversion():
    """Tool conversion now lives in api_params_handler, not this backend class."""
