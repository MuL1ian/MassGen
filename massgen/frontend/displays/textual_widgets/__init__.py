# -*- coding: utf-8 -*-
"""
Textual widgets for the MassGen TUI.

This module provides reusable Textual widgets for the production TUI interface.
"""

from .background_tasks_modal import BackgroundTasksModal
from .content_sections import (
    CompletionFooter,
    ReasoningSection,
    ResponseSection,
    RestartBanner,
    StatusBadge,
    ThinkingSection,
    TimelineSection,
    ToolSection,
)
from .injection_card import InjectionSubCard
from .multi_line_input import MultiLineInput
from .path_suggestion import PathSuggestion, PathSuggestionDropdown
from .tab_bar import AgentTab, AgentTabBar, AgentTabChanged
from .task_plan_card import TaskPlanCard
from .task_plan_modal import TaskPlanModal
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
    # Task plan card and modal
    "TaskPlanCard",
    "TaskPlanModal",
    # Background tasks modal
    "BackgroundTasksModal",
    # Injection sub-card
    "InjectionSubCard",
    # Content sections
    "ToolSection",
    "TimelineSection",
    "ThinkingSection",
    "ReasoningSection",
    "ResponseSection",
    "StatusBadge",
    "CompletionFooter",
    "RestartBanner",
    # Input widgets
    "MultiLineInput",
    # Path autocomplete
    "PathSuggestion",
    "PathSuggestionDropdown",
]
