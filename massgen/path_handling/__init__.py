# -*- coding: utf-8 -*-
"""Path handling module for @filename syntax in MassGen prompts.

This module provides:
- AtPathCompleter: Prompt completion for @path references
- parse_prompt_for_context: Extract context paths from prompts
- ParsedPrompt: Dataclass for parsed prompt results
"""

from massgen.path_handling.path_completer import AtPathCompleter
from massgen.path_handling.prompt_parser import (
    ParsedPrompt,
    PromptParserError,
    parse_prompt_for_context,
)

__all__ = [
    "AtPathCompleter",
    "ParsedPrompt",
    "PromptParserError",
    "parse_prompt_for_context",
]
