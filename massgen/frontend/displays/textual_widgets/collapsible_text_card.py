# -*- coding: utf-8 -*-
"""
Collapsible Text Card Widget for MassGen TUI.

Provides a clickable collapsible card for displaying long reasoning or content text.
Shows the last N chunks when collapsed with "(+N chunks above)" indicator at top,
matching the streaming UX where newest content is visible.
"""

import re
from typing import List, Optional

from rich.text import Text
from textual.events import Click
from textual.widgets import Static

# Patterns to filter out from content
FILTER_PATTERNS = [
    r"🧠\s*\[Reasoning Started\]",
    r"🧠\s*\[Reasoning Complete\]",
    r"\[Reasoning Started\]",
    r"\[Reasoning Complete\]",
    r"🔄\s*Vote for \[.*?\] ignored.*",  # Internal vote status messages
]
FILTER_REGEX = re.compile("|".join(FILTER_PATTERNS), re.IGNORECASE)


class CollapsibleTextCard(Static):
    """Collapsible card for reasoning or content text.

    Shows last N chunks when collapsed with "(+N chunks above)" indicator at top.
    Click to expand/collapse. Pattern matches ToolBatchCard's "show newest" UX.

    Uses border-left styling matching ToolCallCard. All indentation is handled
    via CSS padding-left so wrapped lines align correctly.

    Attributes:
        content: The full text content.
        label: Label shown in header ("Thinking" or "Content").
    """

    # Separator between chunks for visual clarity
    CHUNK_SEPARATOR = "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"

    # Chunks visible when collapsed - shows the tail (newest content)
    COLLAPSED_CHUNK_COUNT = 3

    can_focus = True

    @staticmethod
    def _clean_content(content: str) -> str:
        """Remove reasoning markers from content, preserve spacing."""
        return FILTER_REGEX.sub("", content)

    def __init__(
        self,
        content: str,
        label: str = "Thinking",
        *,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """Initialize the collapsible text card.

        Args:
            content: The full text content to display.
            label: Label for the card ("Thinking" or "Content").
            id: Optional DOM ID.
            classes: Optional CSS classes.
        """
        super().__init__(id=id, classes=classes)
        self._content = self._clean_content(content)
        self._label = label
        self._expanded = False
        self._chunks: List[str] = [self._content] if self._content else []
        # Add label-based class for CSS targeting (e.g., label-thinking, label-content)
        self.add_class(f"label-{label.lower()}")
        # Appearance animation state
        self.add_class("appearing")

    def on_mount(self) -> None:
        """Complete appearance animation after mounting."""
        self.set_timer(0.3, self._complete_appearance)

    def _complete_appearance(self) -> None:
        """Complete the appearance animation by transitioning to appeared state."""
        self.remove_class("appearing")
        self.add_class("appeared")

    def render(self) -> Text:
        """Render the card content."""
        return self._build_content()

    def _render_chunk(self, text: Text, chunk: str) -> None:
        """Render a single chunk of content.

        No manual indentation - CSS padding-left handles alignment for all lines
        including wrapped ones.
        """
        for line in chunk.split("\n"):
            if line:  # Skip completely empty lines
                text.append(f"\n{line}", style="dim #9ca3af")

    def _build_content(self) -> Text:
        """Build the Rich Text content for display."""
        text = Text()

        # Expand indicator and label (on first line)
        indicator = "▾" if self._expanded else "▸"
        text.append(f"{indicator} ", style="dim")
        text.append(f"[{self._label}]", style="dim italic #8b949e")

        total_chunks = len(self._chunks)

        if total_chunks == 0:
            return text

        # Only show separators for Thinking/Reasoning, not Content
        show_separators = self._label.lower() in ("thinking", "reasoning")

        if self._expanded:
            # Show all chunks
            for i, chunk in enumerate(self._chunks):
                self._render_chunk(text, chunk)
                # Add separator or blank line between chunks (not after last)
                if i < total_chunks - 1:
                    if show_separators:
                        text.append(f"\n{self.CHUNK_SEPARATOR}", style="dim #484f58")
                    else:
                        # Blank line between content chunks for readability
                        text.append("\n")
        else:
            # Show "(+N chunks above)" at TOP if truncated
            if total_chunks > self.COLLAPSED_CHUNK_COUNT:
                hidden = total_chunks - self.COLLAPSED_CHUNK_COUNT
                text.append(f"\n(+{hidden} chunks above)", style="dim italic #6e7681")

            # Show LAST N chunks (tail) - newest content visible
            visible_chunks = self._chunks[-self.COLLAPSED_CHUNK_COUNT :]
            for i, chunk in enumerate(visible_chunks):
                # Add separator or blank line before chunk (except first visible)
                if i > 0:
                    if show_separators:
                        text.append(f"\n{self.CHUNK_SEPARATOR}", style="dim #484f58")
                    else:
                        # Blank line between content chunks for readability
                        text.append("\n")
                self._render_chunk(text, chunk)

        return text

    def on_click(self, event: Click) -> None:
        """Handle click - toggle expansion."""
        self._expanded = not self._expanded
        if self._expanded:
            self.add_class("expanded")
        else:
            self.remove_class("expanded")
        self.refresh()

    @property
    def is_expanded(self) -> bool:
        """Check if the card is expanded."""
        return self._expanded

    @property
    def label(self) -> str:
        """Get the card label."""
        return self._label

    @property
    def content(self) -> str:
        """Get the full content."""
        return self._content

    @property
    def chunk_count(self) -> int:
        """Get the total number of chunks."""
        return len(self._chunks)

    def append_content(self, new_content: str) -> None:
        """Append additional content as a new chunk.

        Used for batching consecutive reasoning statements into one card.
        Each append creates a new chunk, separated visually.

        Args:
            new_content: Text to append as a new chunk.
        """
        # Clean and validate content
        cleaned = self._clean_content(new_content)
        if not cleaned:
            return

        # Add as new chunk
        self._chunks.append(cleaned)
        self._content += "\n" + self.CHUNK_SEPARATOR + "\n" + cleaned
        self.refresh()
