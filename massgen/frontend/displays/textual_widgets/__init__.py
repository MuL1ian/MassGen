# -*- coding: utf-8 -*-
"""
Textual widgets for the MassGen TUI.

This module provides reusable Textual widgets for the production TUI interface.
"""

from .background_tasks_modal import BackgroundTasksModal
from .content_sections import (
    CompletionFooter,
    FinalPresentationCard,
    ReasoningSection,
    ResponseSection,
    RestartBanner,
    StatusBadge,
    ThinkingSection,
    TimelineSection,
    ToolSection,
)
from .injection_card import InjectionSubCard
from .mode_bar import ModeBar, ModeChanged, ModeToggle, OverrideRequested
from .multi_line_input import MultiLineInput
from .path_suggestion import PathSuggestion, PathSuggestionDropdown
from .plan_approval_modal import PlanApprovalModal, PlanApprovalResult
from .quickstart_wizard import QuickstartWizard
from .setup_wizard import SetupWizard
from .subagent_card import SubagentCard
from .subagent_modal import SubagentModal
from .tab_bar import AgentTab, AgentTabBar, AgentTabChanged
from .task_plan_card import TaskPlanCard
from .task_plan_modal import TaskPlanModal
from .tool_card import ToolCallCard, format_tool_display_name, get_tool_category
from .tool_detail_modal import ToolDetailModal
from .wizard_base import (
    StepComponent,
    WizardCompleted,
    WizardModal,
    WizardState,
    WizardStep,
)

__all__ = [
    # Mode bar
    "ModeBar",
    "ModeToggle",
    "ModeChanged",
    "OverrideRequested",
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
    # Plan approval modal
    "PlanApprovalModal",
    "PlanApprovalResult",
    # Subagent card and modal
    "SubagentCard",
    "SubagentModal",
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
    "FinalPresentationCard",
    # Input widgets
    "MultiLineInput",
    # Path autocomplete
    "PathSuggestion",
    "PathSuggestionDropdown",
    # Wizard framework
    "WizardModal",
    "WizardState",
    "WizardStep",
    "WizardCompleted",
    "StepComponent",
    "SetupWizard",
    "QuickstartWizard",
]
