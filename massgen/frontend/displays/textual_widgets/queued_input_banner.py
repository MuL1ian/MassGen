# -*- coding: utf-8 -*-
"""
Queued Input Banner Widget for MassGen TUI.

Shows a banner above the input bar when human input has been queued
for injection during agent execution.
"""

from typing import List, Optional

from rich.text import Text
from textual.widgets import Static


class QueuedInputBanner(Static):
    """Banner showing queued human input pending injection.

    Displayed above the input bar when the user types input while
    agents are executing. Shows a preview of queued messages and
    indicates they will be injected after the next tool call.
    """

    # CSS moved to base.tcss for theme support
    DEFAULT_CSS = ""

    def __init__(
        self,
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """Initialize the queued input banner.

        Args:
            id: Optional widget ID.
            classes: Optional CSS classes.
        """
        super().__init__(id=id, classes=classes)
        self._queued_messages: List[str] = []

    def add_message(self, text: str) -> None:
        """Add a queued message and show/update the banner.

        Args:
            text: The queued human input text to add
        """
        self._queued_messages.append(text)
        self._rebuild()
        self.add_class("visible")

    def set_text(self, text: str) -> None:
        """Set a single queued message (replaces all). For backwards compatibility.

        Args:
            text: The queued human input text to display
        """
        self._queued_messages = [text]
        self._rebuild()
        self.add_class("visible")

    def clear(self) -> None:
        """Clear all messages and hide the banner."""
        self._queued_messages.clear()
        self.remove_class("visible")

    def _rebuild(self) -> None:
        """Rebuild the banner content."""
        if not self._queued_messages:
            self.update("")
            return

        content = Text()
        count = len(self._queued_messages)

        if count == 1:
            # Single message - show preview
            display_text = self._queued_messages[0]
            if len(display_text) > 50:
                display_text = display_text[:47] + "..."

            content.append("📝 ", style="bold yellow")
            content.append("Queued: ", style="bold")
            content.append(f'"{display_text}"', style="italic")
            content.append(" (injecting to all agents)", style="dim")
        else:
            # Multiple messages - show count and latest
            latest = self._queued_messages[-1]
            if len(latest) > 40:
                latest = latest[:37] + "..."

            content.append("📝 ", style="bold yellow")
            content.append(f"{count} messages queued", style="bold")
            content.append(f' (latest: "{latest}")', style="italic dim")

        self.update(content)
