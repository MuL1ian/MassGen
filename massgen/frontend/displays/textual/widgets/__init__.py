# -*- coding: utf-8 -*-
"""
Textual widgets for the MassGen TUI.

This module exports all widgets including:
- Modal base classes (BaseModal, BaseDataModal)
- Extracted modal components organized by function
- Re-exports from the existing textual_widgets directory for backwards compatibility
"""

# Base modal classes
from .modal_base import MODAL_BASE_CSS, BaseDataModal, BaseModal

# Extracted modals - organized by function
from .modals import (  # Browser modals; Status modals; Coordination modals; Content modals; Input modals; Shortcuts modal; Workspace modals; Agent output modal
    AgentOutputModal,
    AgentSelectorModal,
    AnswerBrowserModal,
    BroadcastPromptModal,
    BrowserTabsModal,
    ContextModal,
    ConversationHistoryModal,
    CoordinationTableModal,
    CostBreakdownModal,
    FileInspectionModal,
    KeyboardShortcutsModal,
    MCPStatusModal,
    MetricsModal,
    OrchestratorEventsModal,
    StructuredBroadcastPromptModal,
    SystemStatusModal,
    TextContentModal,
    TimelineModal,
    TurnDetailModal,
    VoteResultsModal,
    WorkspaceBrowserModal,
)

__all__ = [
    # Base classes
    "BaseModal",
    "BaseDataModal",
    "MODAL_BASE_CSS",
    # Browser modals
    "AnswerBrowserModal",
    "BrowserTabsModal",
    "TimelineModal",
    "WorkspaceBrowserModal",
    # Status modals
    "CostBreakdownModal",
    "MCPStatusModal",
    "MetricsModal",
    "SystemStatusModal",
    # Coordination modals
    "AgentSelectorModal",
    "CoordinationTableModal",
    "OrchestratorEventsModal",
    "VoteResultsModal",
    # Content modals
    "ContextModal",
    "ConversationHistoryModal",
    "TextContentModal",
    "TurnDetailModal",
    # Input modals
    "BroadcastPromptModal",
    "StructuredBroadcastPromptModal",
    # Shortcuts modal
    "KeyboardShortcutsModal",
    # Workspace modals
    "FileInspectionModal",
    # Agent output modal
    "AgentOutputModal",
]
