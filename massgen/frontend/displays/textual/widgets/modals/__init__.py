# -*- coding: utf-8 -*-
"""
Extracted modal components for the MassGen TUI.

All modals inherit from BaseModal for consistent behavior.
Modals are organized by function:
- browser_modals: AnswerBrowserModal, TimelineModal, BrowserTabsModal, WorkspaceBrowserModal
- status_modals: SystemStatusModal, MCPStatusModal, CostBreakdownModal, MetricsModal
- coordination_modals: VoteResultsModal, OrchestratorEventsModal, CoordinationTableModal, AgentSelectorModal
- content_modals: TextContentModal, TurnDetailModal, ConversationHistoryModal, ContextModal
- input_modals: BroadcastPromptModal, StructuredBroadcastPromptModal
- shortcuts_modal: KeyboardShortcutsModal
- workspace_modals: FileInspectionModal
- agent_output_modal: AgentOutputModal
"""

from .agent_output_modal import AgentOutputModal
from .browser_modals import (
    AnswerBrowserModal,
    BrowserTabsModal,
    TimelineModal,
    WorkspaceBrowserModal,
)
from .content_modals import (
    ContextModal,
    ConversationHistoryModal,
    TextContentModal,
    TurnDetailModal,
)
from .coordination_modals import (
    AgentSelectorModal,
    CoordinationTableModal,
    OrchestratorEventsModal,
    VoteResultsModal,
)
from .input_modals import BroadcastPromptModal, StructuredBroadcastPromptModal
from .shortcuts_modal import KeyboardShortcutsModal
from .status_modals import (
    CostBreakdownModal,
    MCPStatusModal,
    MetricsModal,
    SystemStatusModal,
)
from .workspace_modals import FileInspectionModal

__all__ = [
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
