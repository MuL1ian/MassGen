# -*- coding: utf-8 -*-
"""
Textual TUI components for MassGen.

This package contains all Textual-based TUI components:
- widgets/: UI widgets including modals, cards, and input components
- themes/: TCSS theme files (dark, light, midnight, professional)

The main TextualTerminalDisplay class is still in the parent directory
(textual_terminal_display.py) but imports modals from this package.
"""

# Re-export widgets for convenience
from .widgets import (  # Base classes; Browser modals; Status modals; Coordination modals; Content modals; Input modals; Shortcuts modal; Workspace modals; Agent output modal
    MODAL_BASE_CSS,
    AgentOutputModal,
    AgentSelectorModal,
    AnswerBrowserModal,
    BaseDataModal,
    BaseModal,
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
