# -*- coding: utf-8 -*-
"""
Multi-line input widget for the MassGen TUI.

Provides a TextArea-based input that supports multi-line text entry.
Enter submits, Shift+Enter or Ctrl+J inserts a new line.
Optional vim mode for vim-style editing.
Supports @ path autocomplete integration.
"""

from typing import Optional, Tuple

from textual import events
from textual.binding import Binding
from textual.message import Message
from textual.widgets import TextArea


class MultiLineInput(TextArea):
    """A multi-line input widget that submits on Enter.

    This widget extends TextArea to provide a multi-line input experience.
    Users can:
    - Submit with Enter (matches standard convention)
    - Insert new lines with Shift+Enter or Ctrl+J
    - Use standard TextArea navigation and editing
    - Toggle vim mode with Escape (enter normal mode) / i (enter insert mode)

    Vim mode supports:
    - h/j/k/l for cursor movement
    - w/b for word movement
    - 0/$ for line start/end
    - x to delete character
    - dd to delete line
    - i/a/A/o/O to enter insert mode
    - Escape to return to normal mode

    Attributes:
        placeholder: Text shown when the input is empty.
        vim_mode: Whether vim mode is enabled.
    """

    BINDINGS = [
        Binding("enter", "submit", "Submit", priority=True),
        Binding("shift+enter", "newline", "New Line", priority=True),
        Binding("ctrl+j", "newline", "New Line", show=False),
    ]

    class Submitted(Message, bubble=True):
        """Message sent when the user submits the input with Enter.

        Attributes:
            value: The text content that was submitted.
            input: The MultiLineInput widget that sent the message.
        """

        def __init__(self, input: "MultiLineInput", value: str) -> None:
            super().__init__()
            self.value = value
            self.input = input

    class VimModeChanged(Message, bubble=True):
        """Message sent when vim mode changes."""

        def __init__(self, input: "MultiLineInput", vim_normal: bool) -> None:
            super().__init__()
            self.input = input
            self.vim_normal = vim_normal

    class AtPrefixChanged(Message, bubble=True):
        """Message sent when @ prefix changes (for autocomplete)."""

        def __init__(self, input: "MultiLineInput", prefix: str, at_position: int) -> None:
            super().__init__()
            self.input = input
            self.prefix = prefix  # Path prefix after @
            self.at_position = at_position  # Character position of @

    class AtDismissed(Message, bubble=True):
        """Message sent when @ autocomplete should be dismissed."""

        def __init__(self, input: "MultiLineInput") -> None:
            super().__init__()
            self.input = input

    class TabPressedWithAutocomplete(Message, bubble=True):
        """Message sent when Tab is pressed while autocomplete is active."""

        def __init__(self, input: "MultiLineInput") -> None:
            super().__init__()
            self.input = input

    def __init__(
        self,
        placeholder: str = "",
        id: str | None = None,
        classes: str | None = None,
        vim_mode: bool = False,
    ) -> None:
        """Initialize the multi-line input.

        Args:
            placeholder: Text to show when empty (stored but not displayed by default TextArea).
            id: Widget ID.
            classes: CSS classes.
            vim_mode: Whether to enable vim-style editing.
        """
        super().__init__(
            id=id,
            classes=classes,
            soft_wrap=True,
            show_line_numbers=False,
            tab_behavior="indent",
        )
        self._placeholder = placeholder
        self._show_placeholder = True
        self._vim_mode = vim_mode
        self._vim_normal = False  # Start in insert mode even if vim_mode is True

        # Vim pending command state (for two-key commands like dd, cc, dw, cw)
        self._vim_pending_cmd: Optional[str] = None
        # Vim pending motion (for three-key commands like dt<char>, cf<char>)
        self._vim_pending_motion: Optional[str] = None

        # @ autocomplete state
        self._at_position: Optional[int] = None  # Character position of @ in text
        self._autocomplete_active = False  # Whether autocomplete dropdown is showing

    @property
    def vim_mode(self) -> bool:
        """Whether vim mode is enabled."""
        return self._vim_mode

    @vim_mode.setter
    def vim_mode(self, value: bool) -> None:
        """Enable or disable vim mode."""
        self._vim_mode = value
        if not value:
            self._vim_normal = False
            self.remove_class("vim-normal")

    @property
    def vim_normal(self) -> bool:
        """Whether currently in vim normal mode (vs insert mode)."""
        return self._vim_mode and self._vim_normal

    @property
    def text(self) -> str:
        """Get the current text content."""
        return self.document.text

    @text.setter
    def text(self, value: str) -> None:
        """Set the text content."""
        self.load_text(value)
        self._show_placeholder = not value

    def clear(self) -> None:
        """Clear the input text."""
        self.load_text("")
        self._show_placeholder = True

    def action_submit(self) -> None:
        """Submit the current text when Enter is pressed."""
        # In vim normal mode, Enter doesn't submit
        if self.vim_normal:
            self.action_cursor_down()
            return
        text = self.text.strip()
        if text:
            self.post_message(self.Submitted(self, text))

    def action_newline(self) -> None:
        """Insert a newline when Shift+Enter or Ctrl+J is pressed."""
        if self.vim_normal:
            return
        self.insert("\n")

    def _enter_normal_mode(self) -> None:
        """Enter vim normal mode."""
        if not self._vim_mode:
            return
        self._vim_normal = True
        self.add_class("vim-normal")
        self.post_message(self.VimModeChanged(self, True))

    def _enter_insert_mode(self, after: bool = False) -> None:
        """Enter vim insert mode.

        Args:
            after: If True, move cursor one position right (like 'a' command).
        """
        self._vim_normal = False
        self.remove_class("vim-normal")
        if after and self.cursor_location[1] < len(self.document.get_line(self.cursor_location[0])):
            self.action_cursor_right()
        self.post_message(self.VimModeChanged(self, False))

    def on_key(self, event: events.Key) -> None:
        """Handle key events for vim mode and autocomplete."""
        # When autocomplete is active, intercept Tab to prevent focus change
        if self._autocomplete_active and event.key == "tab":
            # Post a message that the app can handle for selection
            self.post_message(self.TabPressedWithAutocomplete(self))
            event.prevent_default()
            event.stop()
            return

        if not self._vim_mode:
            # Vim mode disabled - don't intercept any keys
            return

        # In insert mode, only Escape switches to normal mode
        if not self._vim_normal:
            if event.key == "escape":
                self._enter_normal_mode()
                event.prevent_default()
                event.stop()
            return

        # In normal mode, handle vim keys
        event.prevent_default()
        event.stop()

        key = event.key

        # Handle pending three-key commands (dt<char>, cf<char>, etc.)
        if self._vim_pending_motion:
            self._handle_vim_pending_motion(key)
            return

        # Handle pending two-key commands (d, c, g)
        if self._vim_pending_cmd:
            self._handle_vim_pending_command(key)
            return

        # Mode switching
        if key == "i":
            self._enter_insert_mode()
        elif key == "a":
            self._enter_insert_mode(after=True)
        elif key == "A":  # Append at end of line
            self.action_cursor_line_end()
            self._enter_insert_mode()
        elif key == "o":  # Open line below
            self.action_cursor_line_end()
            self.insert("\n")
            self._enter_insert_mode()
        elif key == "O":  # Open line above
            self.action_cursor_line_start()
            self.insert("\n")
            self.action_cursor_up()
            self._enter_insert_mode()

        # Movement
        elif key == "h":
            self.action_cursor_left()
        elif key == "j":
            self.action_cursor_down()
        elif key == "k":
            self.action_cursor_up()
        elif key == "l":
            self.action_cursor_right()
        elif key == "w":
            self.action_cursor_word_right()
        elif key == "b":
            self.action_cursor_word_left()
        elif key == "0":
            self.action_cursor_line_start()
        elif key in ("$", "end"):
            self.action_cursor_line_end()
        elif key == "g":
            # Wait for second key (gg = go to start)
            self._vim_pending_cmd = "g"
        elif key == "G":
            # G - go to end
            last_line = self.document.line_count - 1
            self.move_cursor((last_line, len(self.document.get_line(last_line))))

        # Character motions (standalone) - f/t/F/T
        elif key == "f":
            # f<char> - move to next occurrence of char
            self._vim_pending_motion = "f"
        elif key == "F":
            # F<char> - move to previous occurrence of char
            self._vim_pending_motion = "F"
        elif key == "t":
            # t<char> - move to before next occurrence of char
            self._vim_pending_motion = "t"
        elif key == "T":
            # T<char> - move to after previous occurrence of char
            self._vim_pending_motion = "T"

        # Editing - delete commands
        elif key == "x":
            # Delete character under cursor
            self.action_delete_right()
        elif key == "X":
            # Delete character before cursor
            self.action_delete_left()
        elif key == "d":
            # Wait for second key (dd = delete line, dw = delete word, d$ = delete to end)
            self._vim_pending_cmd = "d"
        elif key == "D":
            # Delete from cursor to end of line
            self._delete_to_end_of_line()

        # Editing - change commands (delete and enter insert mode)
        elif key == "c":
            # Wait for second key (cc = change line, cw = change word, c$ = change to end)
            self._vim_pending_cmd = "c"
        elif key == "C":
            # Change from cursor to end of line
            self._change_to_end_of_line()
        elif key == "s":
            # Substitute character (delete char and enter insert)
            self.action_delete_right()
            self._enter_insert_mode()
        elif key == "S":
            # Substitute line (same as cc)
            self._change_current_line()

        # Undo/redo
        elif key == "u":
            self.action_undo()
        elif key == "escape":
            # Cancel any pending command
            self._vim_pending_cmd = None
            self._vim_pending_motion = None

        # Submit in normal mode with Enter handled by action_submit

    def _handle_vim_pending_command(self, key: str) -> None:
        """Handle the second key of a two-key vim command.

        Args:
            key: The second key pressed after d, c, or g.
        """
        pending = self._vim_pending_cmd
        self._vim_pending_cmd = None  # Clear pending state

        if pending == "d":
            # Delete commands
            if key == "d":
                # dd - delete current line
                self._delete_current_line()
            elif key == "w":
                # dw - delete word
                self._delete_word()
            elif key in ("$", "end"):
                # d$ - delete to end of line
                self._delete_to_end_of_line()
            elif key == "0":
                # d0 - delete to start of line
                self._delete_to_start_of_line()
            elif key in ("t", "f", "T", "F"):
                # dt<char>, df<char>, dT<char>, dF<char> - wait for third key
                self._vim_pending_motion = f"d{key}"
            # Other motions cancel the command

        elif pending == "c":
            # Change commands (delete and enter insert)
            if key == "c":
                # cc - change current line
                self._change_current_line()
            elif key == "w":
                # cw - change word
                self._change_word()
            elif key in ("$", "end"):
                # c$ - change to end of line
                self._change_to_end_of_line()
            elif key == "0":
                # c0 - change to start of line
                self._change_to_start_of_line()
            elif key in ("t", "f", "T", "F"):
                # ct<char>, cf<char>, cT<char>, cF<char> - wait for third key
                self._vim_pending_motion = f"c{key}"
            # Other motions cancel the command

        elif pending == "g":
            # Go commands
            if key == "g":
                # gg - go to start of document
                self.move_cursor((0, 0))
            # Other motions cancel the command

    def _handle_vim_pending_motion(self, char: str) -> None:
        """Handle the target character for f/t/F/T motions.

        Args:
            char: The target character to find.
        """
        motion = self._vim_pending_motion
        self._vim_pending_motion = None  # Clear pending state

        if not char or len(char) != 1:
            return  # Invalid character, cancel

        # Parse the motion (e.g., "f", "dt", "cf")
        if motion in ("f", "t", "F", "T"):
            # Standalone motion - just move cursor
            self._execute_char_motion(motion, char)
        elif motion and len(motion) == 2:
            # Combined with d or c (e.g., "dt", "cf")
            action = motion[0]  # 'd' or 'c'
            motion_type = motion[1]  # 'f', 't', 'F', or 'T'

            # Find target position
            target_col = self._find_char_position(motion_type, char)
            if target_col is not None:
                if action == "d":
                    self._delete_to_position(motion_type, target_col)
                elif action == "c":
                    self._delete_to_position(motion_type, target_col)
                    self._enter_insert_mode()

    def _execute_char_motion(self, motion: str, char: str) -> None:
        """Execute a standalone f/t/F/T motion.

        Args:
            motion: One of 'f', 't', 'F', 'T'.
            char: The target character.
        """
        target_col = self._find_char_position(motion, char)
        if target_col is not None:
            row, _ = self.cursor_location
            self.move_cursor((row, target_col))

    def _find_char_position(self, motion: str, char: str) -> Optional[int]:
        """Find the column position for a character motion.

        Args:
            motion: One of 'f', 't', 'F', 'T'.
            char: The target character.

        Returns:
            The target column, or None if not found.
        """
        row, col = self.cursor_location
        line = self.document.get_line(row)

        if motion in ("f", "t"):
            # Search forward
            try:
                idx = line.index(char, col + 1)
                if motion == "t":
                    idx -= 1  # Stop before the character
                return idx
            except ValueError:
                return None
        else:
            # Search backward (F, T)
            try:
                # Search in the substring before cursor
                idx = line.rindex(char, 0, col)
                if motion == "T":
                    idx += 1  # Stop after the character
                return idx
            except ValueError:
                return None

    def _delete_to_position(self, motion: str, target_col: int) -> None:
        """Delete from cursor to target position.

        Args:
            motion: The motion type ('f', 't', 'F', 'T').
            target_col: The target column.
        """
        row, col = self.cursor_location
        lines = self.text.split("\n")

        if row >= len(lines):
            return

        line = lines[row]

        if motion in ("f", "t"):
            # Delete forward (include target for 'f', exclude for 't' already handled)
            end = target_col + 1 if motion == "f" else target_col + 1
            lines[row] = line[:col] + line[end:]
        else:
            # Delete backward
            start = target_col if motion == "F" else target_col
            lines[row] = line[:start] + line[col:]
            col = start  # Move cursor to deletion point

        new_text = "\n".join(lines)
        self.load_text(new_text)
        self.move_cursor((row, col if motion in ("F", "T") else col))

    def _delete_current_line(self) -> None:
        """Delete the current line (vim dd command)."""
        row, _ = self.cursor_location
        line_count = self.document.line_count

        if line_count == 1:
            # Only one line, just clear it
            self.load_text("")
        else:
            lines = self.text.split("\n")
            del lines[row]
            new_text = "\n".join(lines)
            self.load_text(new_text)
            # Move cursor to valid position
            new_row = min(row, len(lines) - 1)
            self.move_cursor((new_row, 0))

    def _delete_to_end_of_line(self) -> None:
        """Delete from cursor to end of line (vim D command)."""
        row, col = self.cursor_location
        lines = self.text.split("\n")

        if row < len(lines):
            # Keep text before cursor, remove text after
            lines[row] = lines[row][:col]
            new_text = "\n".join(lines)
            self.load_text(new_text)
            self.move_cursor((row, col))

    def _change_current_line(self) -> None:
        """Delete line content and enter insert mode (vim cc/S command)."""
        row, _ = self.cursor_location
        lines = self.text.split("\n")

        if row < len(lines):
            # Clear the line but keep it
            lines[row] = ""
            new_text = "\n".join(lines)
            self.load_text(new_text)
            self.move_cursor((row, 0))

        self._enter_insert_mode()

    def _change_to_end_of_line(self) -> None:
        """Delete from cursor to end of line and enter insert mode (vim C command)."""
        self._delete_to_end_of_line()
        self._enter_insert_mode()

    def _delete_to_start_of_line(self) -> None:
        """Delete from cursor to start of line (vim d0 command)."""
        row, col = self.cursor_location
        lines = self.text.split("\n")

        if row < len(lines) and col > 0:
            # Keep text after cursor, remove text before
            lines[row] = lines[row][col:]
            new_text = "\n".join(lines)
            self.load_text(new_text)
            self.move_cursor((row, 0))

    def _change_to_start_of_line(self) -> None:
        """Delete from cursor to start of line and enter insert mode (vim c0 command)."""
        self._delete_to_start_of_line()
        self._enter_insert_mode()

    def _delete_word(self) -> None:
        """Delete from cursor to end of word (vim dw command)."""
        # Get current position
        row, col = self.cursor_location
        lines = self.text.split("\n")

        if row >= len(lines):
            return

        line = lines[row]

        # Find end of current word or whitespace
        end_col = col
        in_word = col < len(line) and not line[col].isspace()

        if in_word:
            # Delete to end of word
            while end_col < len(line) and not line[end_col].isspace():
                end_col += 1
        else:
            # Delete whitespace
            while end_col < len(line) and line[end_col].isspace():
                end_col += 1

        # Delete the characters
        lines[row] = line[:col] + line[end_col:]
        new_text = "\n".join(lines)
        self.load_text(new_text)
        self.move_cursor((row, col))

    def _change_word(self) -> None:
        """Delete from cursor to end of word and enter insert mode (vim cw command)."""
        self._delete_word()
        self._enter_insert_mode()

    def on_focus(self) -> None:
        """Handle focus - hide placeholder."""
        self._show_placeholder = False

    def on_blur(self) -> None:
        """Handle blur - show placeholder if empty."""
        if not self.text.strip():
            self._show_placeholder = True

    # =========================================================================
    # @ Autocomplete Support
    # =========================================================================

    @property
    def autocomplete_active(self) -> bool:
        """Whether @ autocomplete is currently active."""
        return self._autocomplete_active

    @autocomplete_active.setter
    def autocomplete_active(self, value: bool) -> None:
        """Set autocomplete active state."""
        self._autocomplete_active = value
        if not value:
            self._at_position = None

    def _find_at_position(self) -> Optional[Tuple[int, str]]:
        """Find the @ position and prefix for autocomplete.

        Returns:
            Tuple of (at_position, prefix) or None if no valid @ trigger.
        """
        text = self.text
        cursor_pos = self._get_cursor_offset()

        # Only consider text before cursor
        text_before_cursor = text[:cursor_pos]

        # Find the last @ that starts a path reference
        pos = len(text_before_cursor) - 1
        while pos >= 0:
            if text_before_cursor[pos] == "@":
                # Check if escaped
                if pos > 0 and text_before_cursor[pos - 1] == "\\":
                    pos -= 1
                    continue

                # Check if it's likely part of an email
                if self._is_email_context(text_before_cursor, pos):
                    pos -= 1
                    continue

                # Valid @ - extract prefix
                prefix = text_before_cursor[pos + 1 :]

                # Don't trigger if there's a space (path is complete)
                if " " in prefix:
                    return None

                # Don't trigger if already has :w suffix
                if prefix.endswith(":w"):
                    return None

                return (pos, prefix)

            # Stop if we hit whitespace before finding @
            if text_before_cursor[pos] == " ":
                break

            pos -= 1

        return None

    def _is_email_context(self, text: str, at_pos: int) -> bool:
        """Check if @ at position is likely part of an email address."""
        if at_pos == 0:
            return False

        before = text[at_pos - 1]
        if not (before.isalnum() or before in "._-"):
            return False

        after = text[at_pos + 1 :] if at_pos + 1 < len(text) else ""
        if not after:
            return False

        # If there's a dot and no path separator, likely an email
        if "." in after:
            first_dot = after.index(".")
            first_part = after[:first_dot]
            if "/" not in first_part and first_part.replace("-", "").isalnum():
                return True

        return False

    def _get_cursor_offset(self) -> int:
        """Get the cursor position as a character offset in the full text."""
        row, col = self.cursor_location
        lines = self.text.split("\n")

        offset = col
        for i in range(row):
            offset += len(lines[i]) + 1  # +1 for newline

        return offset

    def _check_at_trigger(self) -> None:
        """Check if @ autocomplete should be triggered and notify."""
        # Guard against being called before __init__ completes
        if not hasattr(self, "_autocomplete_active"):
            return

        result = self._find_at_position()
        # DEBUG: Log the result
        with open("/tmp/at_debug.log", "a") as f:
            f.write(f"[DEBUG MLI] _check_at_trigger: result={result}\n")

        if result:
            at_pos, prefix = result
            self._at_position = at_pos
            with open("/tmp/at_debug.log", "a") as f:
                f.write(f"[DEBUG MLI] Posting AtPrefixChanged: prefix={repr(prefix)}\n")
            self.post_message(self.AtPrefixChanged(self, prefix, at_pos))
        elif self._autocomplete_active:
            self._at_position = None
            self.post_message(self.AtDismissed(self))

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Handle text changes to detect @ triggers."""
        # DEBUG: Log that this handler was called
        with open("/tmp/at_debug.log", "a") as f:
            f.write(f"[DEBUG MLI] on_text_area_changed called, text={repr(self.text[:50] if self.text else '')}\n")
        self._check_at_trigger()

    def insert_completion(self, path: str, with_write: bool = False) -> None:
        """Insert a completed path at the @ position.

        Args:
            path: The full path to insert.
            with_write: Whether to add :w suffix.
        """
        if self._at_position is None:
            return

        text = self.text
        cursor_pos = self._get_cursor_offset()

        # Find end of current @ reference
        at_end = cursor_pos
        for i in range(self._at_position + 1, len(text)):
            if text[i] in (" ", "\n"):
                at_end = i
                break
            at_end = i + 1

        # Build new text
        before = text[: self._at_position]
        after = text[at_end:]
        suffix = ":w" if with_write else ""
        new_reference = f"@{path}{suffix}"

        new_text = before + new_reference + after
        new_cursor_pos = len(before) + len(new_reference)

        # Update text and cursor
        self.load_text(new_text)

        # Convert offset to row, col
        lines = new_text.split("\n")
        offset = 0
        for row, line in enumerate(lines):
            if offset + len(line) >= new_cursor_pos:
                col = new_cursor_pos - offset
                self.move_cursor((row, col))
                break
            offset += len(line) + 1

        # Reset autocomplete state
        self._at_position = None
        self._autocomplete_active = False

    def update_at_prefix(self, new_prefix: str) -> None:
        """Update the @ prefix when browsing directories.

        Args:
            new_prefix: The new path prefix (e.g., after selecting a directory).
        """
        if self._at_position is None:
            return

        text = self.text
        cursor_pos = self._get_cursor_offset()

        # Find end of current @ reference
        at_end = cursor_pos

        # Build new text
        before = text[: self._at_position]
        after = text[at_end:]
        new_text = before + f"@{new_prefix}" + after
        new_cursor_pos = len(before) + 1 + len(new_prefix)

        # Update text
        self.load_text(new_text)

        # Move cursor
        lines = new_text.split("\n")
        offset = 0
        for row, line in enumerate(lines):
            if offset + len(line) >= new_cursor_pos:
                col = new_cursor_pos - offset
                self.move_cursor((row, col))
                break
            offset += len(line) + 1

        # Update at position and trigger new autocomplete
        self._check_at_trigger()
