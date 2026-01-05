# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    role: Literal["system", "user", "assistant", "tool"]
    content: Any = None


class ChatCompletionRequest(BaseModel):
    """
    Minimal OpenAI-compatible Chat Completions request model.

    We intentionally accept unknown fields for forward compatibility.
    """

    model_config = ConfigDict(extra="allow")

    model: str = Field(default="massgen")
    messages: List[Dict[str, Any]]
    stream: bool = False

    # Tool calling (OpenAI-style)
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Any] = None
    parallel_tool_calls: Optional[bool] = None
