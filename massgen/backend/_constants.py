# -*- coding: utf-8 -*-
"""Centralized constants for backend operations.

This module defines common constants used across different backend implementations,
including provider-specific defaults and configuration values.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# =============================================================================
# OPENROUTER CONSTANTS
# =============================================================================

# Default search engine for OpenRouter web search plugin
# Options: "exa" (default, AI-native search) or "native" (traditional search)
OPENROUTER_DEFAULT_WEB_ENGINE = "exa"

# Default maximum number of search results to return (OpenRouter default is 5)
OPENROUTER_DEFAULT_WEB_MAX_RESULTS = 5

# Valid engine options for OpenRouter web search
OPENROUTER_VALID_WEB_ENGINES = {"exa", "native"}

# Valid search context size options for OpenRouter web search
OPENROUTER_VALID_SEARCH_CONTEXT_SIZES = {"low", "medium", "high"}


def configure_openrouter_extra_body(
    api_params: Dict[str, Any],
    all_params: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Configure extra_body for OpenRouter API requests.

    Handles cost tracking and web search plugin configuration with validation.

    Args:
        api_params: API parameters dict (modified in place)
        all_params: All configuration parameters

    Returns:
        The extra_body dict if OpenRouter detected, None otherwise

    Raises:
        ValueError: If engine is invalid or max_results is not a positive integer
    """
    base_url = all_params.get("base_url", "")
    if "openrouter.ai" not in base_url.lower():
        return None

    extra_body = api_params.get("extra_body", {})
    if not isinstance(extra_body, dict):
        extra_body = {}

    # Enable cost tracking in usage response
    extra_body["usage"] = {"include": True}

    # Enable web search via plugins array
    if all_params.get("enable_web_search", False):
        # Validate engine parameter
        engine = all_params.get("engine", OPENROUTER_DEFAULT_WEB_ENGINE)
        if engine not in OPENROUTER_VALID_WEB_ENGINES:
            raise ValueError(
                f"Invalid OpenRouter web search engine: '{engine}'. " f"Must be one of: {OPENROUTER_VALID_WEB_ENGINES}",
            )

        # Validate max_results parameter
        max_results = all_params.get("max_results", OPENROUTER_DEFAULT_WEB_MAX_RESULTS)
        if not isinstance(max_results, int) or max_results < 1:
            raise ValueError(
                f"OpenRouter max_results must be a positive integer, got: {max_results}",
            )

        web_plugin = {
            "id": "web",
            "engine": engine,
            "max_results": max_results,
        }

        # Add optional search_prompt if provided
        search_prompt = all_params.get("search_prompt")
        if search_prompt:
            web_plugin["search_prompt"] = search_prompt

        if "plugins" not in extra_body:
            extra_body["plugins"] = []
        extra_body["plugins"].append(web_plugin)

        # Add web_search_options for search_context_size if provided
        search_context_size = all_params.get("search_context_size")
        if search_context_size:
            if search_context_size not in OPENROUTER_VALID_SEARCH_CONTEXT_SIZES:
                raise ValueError(
                    f"Invalid OpenRouter search_context_size: '{search_context_size}'. " f"Must be one of: {OPENROUTER_VALID_SEARCH_CONTEXT_SIZES}",
                )
            extra_body["web_search_options"] = {"search_context_size": search_context_size}

        logger.info(f"[OpenRouter] Web search plugin enabled: {web_plugin}")

    api_params["extra_body"] = extra_body
    return extra_body
