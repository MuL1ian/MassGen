# -*- coding: utf-8 -*-
from __future__ import annotations

import copy
import uuid
from typing import Any, AsyncGenerator, AsyncIterator, Dict, Optional, Protocol

from massgen.agent_config import AgentConfig
from massgen.backend.base import StreamChunk
from massgen.cli import create_agents_from_config, load_config_file
from massgen.orchestrator import Orchestrator

from .openai.model_router import ResolvedModel
from .openai.schema import ChatCompletionRequest


class Engine(Protocol):
    async def stream_chat(
        self,
        req: ChatCompletionRequest,
        resolved: ResolvedModel,
        *,
        request_id: str,
    ) -> AsyncIterator[StreamChunk]:
        ...


class MassGenEngine:
    """
    Default engine that reuses MassGen's existing orchestrator + StreamChunk streaming.

    This is intentionally conservative: it supports loading a config file and streaming
    orchestrator output. Tests inject a FakeEngine instead.
    """

    def __init__(
        self,
        *,
        default_config: Optional[str] = None,
        default_model: Optional[str] = None,
        enable_rate_limit: bool = False,
    ):
        self._default_config = default_config
        self._default_model = default_model
        self._enable_rate_limit = enable_rate_limit

    def _load_config(self, resolved: ResolvedModel) -> Dict[str, Any]:
        config_path = resolved.config_path or self._default_config
        if not config_path:
            # Extremely minimal fallback: build a 1-agent quick config is out-of-scope here.
            # Fail clearly so operators can set MASSGEN_SERVER_DEFAULT_CONFIG.
            raise ValueError("No config provided. Set MASSGEN_SERVER_DEFAULT_CONFIG or use model='massgen/path:<path>'.")
        return load_config_file(config_path)

    def _apply_model_override(self, config: Dict[str, Any], override_model: Optional[str]) -> Dict[str, Any]:
        if not override_model:
            return config
        cfg = copy.deepcopy(config)
        if "agent" in cfg:
            cfg["agent"].setdefault("backend", {})
            cfg["agent"]["backend"]["model"] = override_model
        if "agents" in cfg and isinstance(cfg["agents"], list):
            for agent in cfg["agents"]:
                if isinstance(agent, dict):
                    agent.setdefault("backend", {})
                    agent["backend"]["model"] = override_model
        return cfg

    async def stream_chat(
        self,
        req: ChatCompletionRequest,
        resolved: ResolvedModel,
        *,
        request_id: str,
    ) -> AsyncGenerator[StreamChunk, None]:
        config = self._load_config(resolved)
        override_model = resolved.override_model or self._default_model
        config = self._apply_model_override(config, override_model)

        orchestrator_cfg = config.get("orchestrator", {}) if isinstance(config, dict) else {}
        agents = create_agents_from_config(
            config,
            orchestrator_cfg if isinstance(orchestrator_cfg, dict) else None,
            enable_rate_limit=self._enable_rate_limit,
            config_path=resolved.config_path or self._default_config,
        )

        # Construct a minimal AgentConfig for orchestrator behavior.
        # We keep most defaults; orchestration behavior is controlled by the YAML agent configs.
        orch_config = AgentConfig.create_openai_config()
        orch = Orchestrator(
            agents=agents,
            config=orch_config,
            session_id=f"server_{uuid.uuid4().hex[:8]}",
            enable_rate_limit=self._enable_rate_limit,
            trace_classification="strict",
        )

        # Preserve OpenAI-style tool messages in req.messages (Orchestrator will be updated to retain role=tool).
        async for chunk in orch.chat(req.messages, tools=req.tools):
            # Attach a source if missing (useful for adapter filtering)
            if chunk.source is None:
                chunk.source = "orchestrator"
            yield chunk
