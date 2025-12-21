from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ResolvedModel:
    raw_model: str
    config_path: Optional[str] = None
    override_model: Optional[str] = None


def resolve_model(raw_model: str, *, default_config: Optional[str], default_model: Optional[str]) -> ResolvedModel:
    """
    Minimal model routing:
    - massgen/path:<path> -> config_path=<path>
    - massgen/model:<model> -> override_model=<model>
    - otherwise:
        - if default_config is set -> use it (and optionally override_model with raw_model if default_model is not set)
        - else treat raw_model as override_model (single-agent quick override)
    """
    if raw_model.startswith("massgen/path:"):
        return ResolvedModel(raw_model=raw_model, config_path=raw_model[len("massgen/path:") :].strip() or None)
    if raw_model.startswith("massgen/model:"):
        return ResolvedModel(raw_model=raw_model, config_path=default_config, override_model=raw_model[len("massgen/model:") :].strip() or None)

    # Generic model strings
    if default_config:
        if default_model:
            return ResolvedModel(raw_model=raw_model, config_path=default_config, override_model=None)
        return ResolvedModel(raw_model=raw_model, config_path=default_config, override_model=raw_model)

    return ResolvedModel(raw_model=raw_model, config_path=None, override_model=raw_model or None)


