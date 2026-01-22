# -*- coding: utf-8 -*-
"""Workspace-related modals: File browser and file inspection."""

from pathlib import Path
from typing import TYPE_CHECKING, Optional

try:
    from textual.app import ComposeResult
    from textual.containers import Container, Horizontal
    from textual.widgets import Button, DirectoryTree, Label, TextArea

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False

from ..modal_base import BaseModal

if TYPE_CHECKING:
    from massgen.frontend.displays.textual_terminal_display import (
        TextualApp,
        TextualTerminalDisplay,
    )


class WorkspaceFilesModal(BaseModal):
    """Modal to display workspace files and open workspace directory."""

    def __init__(self, display: "TextualTerminalDisplay", app: "TextualApp"):
        super().__init__()
        self.coordination_display = display
        self.app_ref = app
        self.workspace_path = self._get_workspace_path()

    def _get_workspace_path(self) -> Optional[Path]:
        """Get the workspace directory path."""
        orchestrator = getattr(self.coordination_display, "orchestrator", None)
        if not orchestrator:
            return None
        workspace_dir = getattr(orchestrator, "workspace_dir", None)
        if workspace_dir:
            return Path(workspace_dir)
        return None

    def compose(self) -> ComposeResult:
        with Container(id="workspace_container"):
            yield Label("📁 Workspace Files", id="workspace_header")
            yield TextArea(self._build_file_list(), id="workspace_content", read_only=True)
            with Horizontal(id="workspace_buttons"):
                yield Button("Open Workspace", id="open_workspace_button")
                yield Button("Close (ESC)", id="close_workspace_button")

    def _build_file_list(self) -> str:
        """Build a list of files in the workspace."""
        if not self.workspace_path or not self.workspace_path.exists():
            return "No workspace directory available."

        lines = [f"Workspace: {self.workspace_path}", ""]

        try:
            files = list(self.workspace_path.rglob("*"))
            files = [f for f in files if f.is_file()]

            if not files:
                lines.append("No files in workspace.")
            else:
                lines.append(f"Files ({len(files)} total):")
                lines.append("-" * 50)

                # Show first 20 files
                for f in sorted(files)[:20]:
                    rel_path = f.relative_to(self.workspace_path)
                    size = f.stat().st_size
                    size_str = self._format_size(size)
                    lines.append(f"  {rel_path} ({size_str})")

                if len(files) > 20:
                    lines.append(f"  ... and {len(files) - 20} more files")

        except Exception as e:
            lines.append(f"Error reading workspace: {e}")

        return "\n".join(lines)

    def _format_size(self, size: int) -> str:
        """Format file size in human-readable form."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}" if unit != "B" else f"{size} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "open_workspace_button":
            self._open_workspace()
        elif event.button.id == "close_workspace_button":
            self.dismiss()

    def _open_workspace(self) -> None:
        """Open the workspace directory in the system file browser."""
        import platform
        import subprocess

        if not self.workspace_path or not self.workspace_path.exists():
            self.app_ref.notify("No workspace directory available", severity="warning")
            return

        try:
            system = platform.system()
            if system == "Darwin":  # macOS
                subprocess.run(["open", str(self.workspace_path)])
            elif system == "Windows":
                subprocess.run(["explorer", str(self.workspace_path)])
            else:  # Linux
                subprocess.run(["xdg-open", str(self.workspace_path)])
            self.app_ref.notify(f"Opened: {self.workspace_path}", severity="information")
        except Exception as e:
            self.app_ref.notify(f"Error opening workspace: {e}", severity="error")


class FileInspectionModal(BaseModal):
    """Modal for inspecting files in the workspace with tree view and preview."""

    def __init__(self, workspace_path: Path, app: "TextualApp"):
        super().__init__()
        self.workspace_path = workspace_path
        self.app_ref = app
        self.selected_file: Optional[Path] = None

    def compose(self) -> ComposeResult:
        with Container(id="file_inspection_container"):
            yield Label("📁 File Inspection", id="file_inspection_header")
            with Horizontal(id="file_inspection_content"):
                # Left panel: Directory tree
                with Container(id="file_tree_panel"):
                    yield Label("Workspace Files:", id="tree_label")
                    if self.workspace_path and self.workspace_path.exists():
                        yield DirectoryTree(str(self.workspace_path), id="workspace_tree")
                    else:
                        yield Label("No workspace available", id="no_workspace_label")
                # Right panel: File preview
                with Container(id="file_preview_panel"):
                    yield Label("File Preview:", id="preview_label")
                    yield TextArea("Select a file to preview", id="file_preview", read_only=True)
            with Horizontal(id="file_inspection_buttons"):
                yield Button("Open in Editor", id="open_editor_button")
                yield Button("Close (ESC)", id="close_inspection_button")

    def on_directory_tree_file_selected(self, event) -> None:
        """Handle file selection in the tree."""
        self.selected_file = Path(event.path)
        self._update_preview()

    def _update_preview(self) -> None:
        """Update the file preview panel."""
        preview = self.query_one("#file_preview", TextArea)

        if not self.selected_file or not self.selected_file.exists():
            preview.load_text("Select a file to preview")
            return

        if self.selected_file.is_dir():
            preview.load_text(f"Directory: {self.selected_file.name}\n\nSelect a file to view its contents.")
            return

        # Check file size - limit preview to reasonable size
        try:
            file_size = self.selected_file.stat().st_size
            if file_size > 100000:  # 100KB limit
                preview.load_text(f"File too large to preview ({file_size:,} bytes)\n\nUse 'Open in Editor' to view.")
                return

            # Try to read as text
            content = self.selected_file.read_text(encoding="utf-8", errors="replace")
            # Limit lines for preview
            lines = content.split("\n")
            if len(lines) > 200:
                content = "\n".join(lines[:200]) + f"\n\n... ({len(lines) - 200} more lines)"
            preview.load_text(content)
        except Exception as e:
            preview.load_text(f"Cannot preview file: {e}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "open_editor_button":
            self._open_in_editor()
        elif event.button.id == "close_inspection_button":
            self.dismiss()

    def _open_in_editor(self) -> None:
        """Open the selected file in the system editor."""
        import platform
        import subprocess

        if not self.selected_file or not self.selected_file.exists():
            self.app_ref.notify("No file selected", severity="warning")
            return

        if self.selected_file.is_dir():
            self.app_ref.notify("Cannot open directory in editor", severity="warning")
            return

        try:
            system = platform.system()
            if system == "Darwin":  # macOS
                subprocess.run(["open", str(self.selected_file)])
            elif system == "Windows":
                subprocess.run(["start", str(self.selected_file)], shell=True)
            else:  # Linux
                subprocess.run(["xdg-open", str(self.selected_file)])
            self.app_ref.notify(f"Opened: {self.selected_file.name}", severity="information")
        except Exception as e:
            self.app_ref.notify(f"Error opening file: {e}", severity="error")
