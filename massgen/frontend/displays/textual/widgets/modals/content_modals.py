# -*- coding: utf-8 -*-
"""Content-related modals: Text, Turn details, Conversation history, Context."""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

try:
    from textual.app import ComposeResult
    from textual.containers import Container, Horizontal, ScrollableContainer
    from textual.widget import Widget
    from textual.widgets import Button, Input, Label, Static, TextArea

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False

from ..modal_base import BaseModal

if TYPE_CHECKING:
    from massgen.frontend.displays.textual_terminal_display import (
        TextualApp,
        TextualTerminalDisplay,
    )


class TextContentModal(BaseModal):
    """Generic modal to display text content from a file or buffer."""

    def __init__(self, title: str, content: str):
        super().__init__()
        self.title = title
        self.content = content

    def compose(self) -> ComposeResult:
        with Container(id="text_content_container"):
            yield Label(self.title, id="text_content_header")
            yield TextArea(self.content, id="text_content_body", read_only=True)
            yield Button("Close (ESC)", id="close_text_content_button")


class TurnDetailModal(BaseModal):
    """Modal showing full details of a conversation turn."""

    def __init__(
        self,
        turn_data: Dict[str, Any],
        agent_color_class: str,
    ):
        super().__init__()
        self._turn_data = turn_data
        self._agent_color_class = agent_color_class

    def compose(self) -> ComposeResult:
        turn = self._turn_data.get("turn", "?")
        question = self._turn_data.get("question", "")
        answer = self._turn_data.get("answer", "")
        agent_id = self._turn_data.get("agent_id", "")
        model = self._turn_data.get("model", "")
        timestamp = self._turn_data.get("timestamp", 0)
        workspace_path = self._turn_data.get("workspace_path")

        # Format timestamp
        time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S") if timestamp else ""
        agent_info = f"{agent_id} ({model})" if model else agent_id

        with Container(id="turn_detail_container", classes=self._agent_color_class):
            # Header with turn info
            yield Label(
                f"[bold cyan]Turn {turn}[/] - {time_str}",
                id="turn_detail_header",
                markup=True,
            )
            yield Label(f"[dim]Winner: {agent_info}[/]", id="turn_detail_agent", markup=True)

            # Question
            yield Label("[bold]Question:[/]", markup=True)
            yield Static(question, id="turn_detail_question")

            # Full answer in scrollable container
            yield Label("[bold]Answer:[/]", markup=True)
            with ScrollableContainer(id="turn_detail_answer_scroll"):
                yield Static(answer, id="turn_detail_answer")

            # Footer buttons
            with Horizontal(id="turn_detail_footer"):
                if workspace_path:
                    yield Button("📂 Open Workspace", id="turn_detail_workspace_button")
                yield Button("Close (ESC)", id="turn_detail_close_button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "turn_detail_close_button":
            self.dismiss()
        elif event.button.id == "turn_detail_workspace_button":
            self._open_workspace_in_explorer()

    def _open_workspace_in_explorer(self) -> None:
        """Open the turn's workspace directory in the system file explorer."""
        import platform
        import subprocess

        workspace_path = self._turn_data.get("workspace_path")
        if not workspace_path:
            self.notify("No workspace available for this turn", severity="warning", timeout=2)
            return

        try:
            system = platform.system()
            if system == "Darwin":  # macOS
                subprocess.run(["open", str(workspace_path)])
            elif system == "Windows":
                subprocess.run(["explorer", str(workspace_path)])
            else:  # Linux
                subprocess.run(["xdg-open", str(workspace_path)])
        except Exception as e:
            self.notify(f"Error opening workspace: {e}", severity="error", timeout=3)


class ConversationHistoryModal(BaseModal):
    """Modal showing conversation history and current prompt."""

    def __init__(
        self,
        conversation_history: List[Dict[str, Any]],
        current_question: str,
        agent_ids: List[str],
    ):
        super().__init__()
        self._history = conversation_history
        self._current_question = current_question
        self._agent_ids = agent_ids

    def compose(self) -> ComposeResult:
        with Container(id="history_container"):
            yield Label("📜 Conversation History", id="history_header")

            # Show current prompt if any
            if self._current_question:
                yield Label(f"[bold]Current:[/] {self._current_question}", id="current_prompt")

            # Scrollable history container
            with ScrollableContainer(id="history_scroll"):
                if self._history:
                    for idx, entry in enumerate(reversed(self._history)):  # Most recent first
                        yield self._create_turn_widget(entry, idx)
                else:
                    yield Label("[dim]No conversation history yet.[/]", id="no_history")

            yield Button("Close (ESC)", id="close_history_button")

    def _get_agent_color_class(self, agent_id: str) -> str:
        """Get the agent color class for an agent ID."""
        if agent_id in self._agent_ids:
            agent_idx = self._agent_ids.index(agent_id) + 1
            return f"agent-color-{((agent_idx - 1) % 8) + 1}"
        return "agent-color-1"

    def _create_turn_widget(self, entry: Dict[str, Any], idx: int) -> Widget:
        """Create a clickable widget for a conversation turn with agent color."""
        turn = entry.get("turn", "?")
        question = entry.get("question", "")
        answer = entry.get("answer", "")
        agent_id = entry.get("agent_id", "")
        model = entry.get("model", "")
        timestamp = entry.get("timestamp", 0)
        workspace_path = entry.get("workspace_path")

        # Format timestamp
        time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S") if timestamp else ""

        # Truncate answer for display
        answer_preview = answer[:200] + "..." if len(answer) > 200 else answer

        agent_info = f"{agent_id} ({model})" if model else agent_id
        agent_color_class = self._get_agent_color_class(agent_id)

        # Build content - workspace indicator if available
        workspace_indicator = " 📂" if workspace_path else ""

        content = f"""[bold cyan]Turn {turn}[/] - {time_str}{workspace_indicator}
[bold]Q:[/] {question}
[dim]Winner: {agent_info}[/]
[bold]A:[/] {answer_preview}
"""
        # Return a container with turn index in ID for click handling
        # The actual_idx is the original index in _history (before reversal)
        actual_idx = len(self._history) - 1 - idx
        return Static(
            content,
            id=f"history_turn_{actual_idx}",
            classes=f"history-turn turn-entry {agent_color_class}",
            markup=True,
        )

    def on_click(self, event) -> None:
        """Handle clicks on turn entries to show full details."""
        # Walk up to find the turn widget
        target = event.widget
        while target and not (hasattr(target, "id") and target.id and target.id.startswith("history_turn_")):
            target = getattr(target, "parent", None)

        if target and target.id:
            try:
                idx = int(target.id.split("_")[-1])
                if 0 <= idx < len(self._history):
                    entry = self._history[idx]
                    agent_id = entry.get("agent_id", "")
                    agent_color_class = self._get_agent_color_class(agent_id)
                    self.app.push_screen(TurnDetailModal(entry, agent_color_class))
            except (ValueError, IndexError):
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "close_history_button":
            self.dismiss()


class ContextModal(BaseModal):
    """Modal for managing context paths."""

    def __init__(self, display: "TextualTerminalDisplay", app: "TextualApp"):
        super().__init__()
        self.coordination_display = display
        self.app_ref = app
        self.current_paths = self._get_current_paths()

    def _get_current_paths(self) -> List[str]:
        """Get current context paths from orchestrator config."""
        orchestrator = getattr(self.coordination_display, "orchestrator", None)
        if not orchestrator:
            return []
        orchestrator_cfg = getattr(orchestrator, "config", {})
        return orchestrator_cfg.get("context_paths", [])

    def compose(self) -> ComposeResult:
        with Container(id="context_container"):
            yield Label("📂 Context Paths", id="context_header")
            yield Label("Current paths that agents can access:", id="context_hint")
            yield TextArea(
                self._format_paths(),
                id="context_current_paths",
                read_only=True,
            )
            yield Label("Add new path:", id="add_path_label")
            yield Input(placeholder="Enter path to add...", id="new_path_input")
            with Horizontal(id="context_buttons"):
                yield Button("Add Path", id="add_path_button")
                yield Button("Close (ESC)", id="close_context_button")

    def _format_paths(self) -> str:
        """Format current paths for display."""
        if not self.current_paths:
            return "No context paths configured."
        return "\n".join(f"  • {path}" for path in self.current_paths)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "add_path_button":
            self._add_path()
        elif event.button.id == "close_context_button":
            self.dismiss()

    def _add_path(self) -> None:
        """Add a new context path."""
        input_widget = self.query_one("#new_path_input", Input)
        new_path = input_widget.value.strip()

        if not new_path:
            self.app_ref.notify("Please enter a path", severity="warning")
            return

        path = Path(new_path).expanduser().resolve()
        if not path.exists():
            self.app_ref.notify(f"Path does not exist: {new_path}", severity="warning")
            return

        if str(path) in self.current_paths:
            self.app_ref.notify("Path already in context", severity="warning")
            return

        self.current_paths.append(str(path))
        self._update_orchestrator_paths()
        input_widget.value = ""

        # Refresh the display
        paths_area = self.query_one("#context_current_paths", TextArea)
        paths_area.load_text(self._format_paths())
        self.app_ref.notify(f"Added: {path}", severity="information")

    def _update_orchestrator_paths(self) -> None:
        """Update the orchestrator config with new paths."""
        orchestrator = getattr(self.coordination_display, "orchestrator", None)
        if orchestrator:
            if hasattr(orchestrator, "config"):
                orchestrator.config["context_paths"] = self.current_paths.copy()
