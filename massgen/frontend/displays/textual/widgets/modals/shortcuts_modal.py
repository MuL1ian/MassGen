# -*- coding: utf-8 -*-
"""Keyboard shortcuts help modal."""


try:
    from textual.app import ComposeResult
    from textual.containers import Container, Horizontal
    from textual.widgets import Button, Label, Static

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False

from ..modal_base import BaseModal


class KeyboardShortcutsModal(BaseModal):
    """Modal showing commands available during coordination."""

    def compose(self) -> ComposeResult:
        with Container(id="shortcuts_modal_container"):
            yield Label("📖  Commands & Shortcuts", id="shortcuts_modal_header")
            yield Label("Press Esc to unfocus input, then use single keys", id="shortcuts_hint")
            # Two-column layout for wide terminals
            with Horizontal(id="shortcuts_columns"):
                # Left column - Quick keys and navigation
                with Container(id="shortcuts_col_left", classes="shortcuts-column"):
                    yield Static(
                        "[bold cyan]Quick Keys[/] [dim](when not typing)[/]\n"
                        "  [yellow]q[/]        Cancel/stop execution\n"
                        "  [yellow]w[/]        Workspace browser\n"
                        "  [yellow]v[/]        Vote results\n"
                        "  [yellow]a[/]        Answer browser\n"
                        "  [yellow]t[/]        Timeline\n"
                        "  [yellow]h[/]        Conversation history\n"
                        "  [yellow]c[/]        Cost breakdown\n"
                        "  [yellow]m[/]        MCP status / metrics\n"
                        "  [yellow]s[/]        System status\n"
                        "  [yellow]o[/]        Agent output (full)\n"
                        "  [yellow]?[/]        This help\n"
                        "  [yellow]1-9[/]      Switch to agent N\n"
                        "\n"
                        "[bold cyan]Focus[/]\n"
                        "  [yellow]Esc[/]      Unfocus input\n"
                        "  [yellow]i[/] or [yellow]/[/]  Focus input",
                        markup=True,
                    )
                # Right column - Input and commands
                with Container(id="shortcuts_col_right", classes="shortcuts-column"):
                    yield Static(
                        "[bold cyan]Input[/]\n"
                        "  [yellow]Enter[/]       Submit question\n"
                        "  [yellow]Shift+Enter[/] New line\n"
                        "  [yellow]Ctrl+P[/]      File access (off→read→write)\n"
                        "  [yellow]Tab[/]         Next agent\n"
                        "  [yellow]Shift+Tab[/]   Cycle plan mode (normal→plan→execute)\n"
                        "\n"
                        "[bold cyan]Quit[/]\n"
                        "  [yellow]Ctrl+C[/]      Exit MassGen\n"
                        "  [yellow]q[/]           Cancel current turn\n"
                        "\n"
                        "[bold cyan]Slash Commands[/]\n"
                        "  [yellow]/history[/]    Conversation history\n"
                        "  [yellow]/context[/]    Manage context paths\n"
                        "  [yellow]/vim[/]        Toggle vim mode\n"
                        "\n"
                        "[bold cyan]Tips[/]\n"
                        "  [dim]Click tool cards for details[/]\n"
                        "  [dim]Type /help for more commands[/]",
                        markup=True,
                    )
            yield Button("Close (ESC)", id="close_shortcuts_button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close_shortcuts_button":
            self.dismiss()
