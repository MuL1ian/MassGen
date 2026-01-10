# -*- coding: utf-8 -*-
"""
Textual widgets for the MassGen TUI.

This module provides reusable Textual widgets for the production TUI interface.
"""

from .content_sections import (
    CompletionFooter,
    ReasoningSection,
    ResponseSection,
    StatusBadge,
    ThinkingSection,
    TimelineSection,
    ToolSection,
)
from .tab_bar import AgentTab, AgentTabBar, AgentTabChanged
from .tool_card import ToolCallCard, format_tool_display_name, get_tool_category
from .tool_detail_modal import ToolDetailModal

__all__ = [
    # Tab bar
    "AgentTab",
    "AgentTabBar",
    "AgentTabChanged",
    # Tool cards and modal
    "ToolCallCard",
    "ToolDetailModal",
    "get_tool_category",
    "format_tool_display_name",
    # Content sections
    "ToolSection",
    "TimelineSection",
    "ThinkingSection",
    "ReasoningSection",
    "ResponseSection",
    "StatusBadge",
    "CompletionFooter",
]
