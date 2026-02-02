# -*- coding: utf-8 -*-
"""File explorer side panel for the final answer card.

Shows workspace file changes (new/modified) in a tree with click-to-preview.
Falls back to scanning the workspace directory when no explicit context_paths are provided.
"""

from pathlib import Path
from typing import Dict, List, Optional

from textual.containers import Vertical
from textual.widgets import Static, Tree


class FileExplorerPanel(Vertical):
    """Side panel showing workspace file changes with click-to-preview.

    Displays a tree of new/modified files and a preview pane for the selected file.
    When context_paths is empty, scans workspace_path for all files instead.
    """

    DEFAULT_CSS = """
    FileExplorerPanel {
        width: 35%;
        border-left: solid #45475a;
        display: none;
        height: 1fr;
        overflow-y: auto;
    }

    FileExplorerPanel.visible {
        display: block;
    }

    FileExplorerPanel #file_tree_header {
        color: #58a6ff;
        text-style: bold;
        padding: 0 1;
        height: 1;
    }

    FileExplorerPanel #file_tree {
        height: auto;
        max-height: 50%;
        min-height: 5;
        padding: 0 1;
    }

    FileExplorerPanel #file_preview_header {
        color: #8b949e;
        padding: 0 1;
        height: 1;
        border-top: solid #45475a;
    }

    FileExplorerPanel #file_preview {
        height: 1fr;
        min-height: 5;
        padding: 0 1;
        color: #e6e6e6;
        overflow-y: auto;
    }
    """

    def __init__(
        self,
        context_paths: Optional[Dict[str, List[str]]] = None,
        workspace_path: Optional[str] = None,
        id: Optional[str] = None,
    ) -> None:
        super().__init__(id=id or "file_explorer_panel")
        self.context_paths = context_paths or {}
        self.workspace_path = workspace_path
        self._all_paths: Dict[str, str] = {}  # display path -> status ("new"/"modified"/"workspace")
        self._path_lookup: Dict[str, str] = {}  # display path -> absolute path

        # Populate from explicit context_paths first
        for path in self.context_paths.get("new", []):
            self._add_path(path, "new")
        for path in self.context_paths.get("modified", []):
            self._add_path(path, "modified")

        # If no context_paths but workspace exists, scan it
        if not self._all_paths and self.workspace_path:
            self._scan_workspace()

    def _add_path(self, display_path: str, status: str, absolute_path: Optional[str] = None) -> None:
        """Track a path for display and lookup."""
        self._all_paths[display_path] = status
        self._path_lookup[display_path] = absolute_path or display_path

    def _clear_workspace_entries(self) -> None:
        """Remove previously scanned workspace entries to allow refresh."""
        to_remove = [p for p, status in self._all_paths.items() if status == "workspace"]
        for display_path in to_remove:
            self._all_paths.pop(display_path, None)
            self._path_lookup.pop(display_path, None)

    # Directories to skip when scanning workspace
    _SKIP_DIRS = frozenset(
        {
            ".git",
            ".env",
            ".massgen",
            "massgen_logs",
            "node_modules",
            "__pycache__",
            ".venv",
            "venv",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".tox",
            ".nox",
            ".cache",
            ".next",
            ".nuxt",
            "dist",
            "build",
            "target",
            ".pnpm",
            ".pnpm-store",
            "vendor",
        },
    )
    _MAX_DEPTH = 3
    _MAX_FILES = 50

    def _scan_workspace(self) -> None:
        """Scan workspace directory and populate _all_paths with found files."""
        ws = Path(self.workspace_path)
        if not ws.exists() or not ws.is_dir():
            return
        self._clear_workspace_entries()
        try:
            added = 0
            truncated = False
            for f in sorted(ws.rglob("*")):
                if added >= self._MAX_FILES:
                    truncated = True
                    break
                # Skip filtered directories
                if any(part in self._SKIP_DIRS for part in f.relative_to(ws).parts):
                    continue
                # Enforce depth limit
                rel = f.relative_to(ws)
                if len(rel.parts) > self._MAX_DEPTH:
                    continue
                if f.is_file():
                    display_path = str(rel)
                    self._add_path(display_path, "workspace", absolute_path=str(f))
                    added += 1
            if truncated:
                self._add_path("... (more files)", "workspace", absolute_path="")
        except Exception:
            pass

    def has_files(self) -> bool:
        """Return True if there are any files to display."""
        return bool(self._all_paths)

    def compose(self):
        from textual.widgets import Label

        has_context = bool(self.context_paths.get("new") or self.context_paths.get("modified"))
        header_text = "📂 Workspace Changes" if has_context else "📂 Workspace"
        yield Label(header_text, id="file_tree_header")

        tree: Tree[str] = Tree("files", id="file_tree")
        tree.root.expand()
        tree.show_root = False

        # Build directory structure
        dirs: Dict[str, any] = {}
        for display_path, status in sorted(self._all_paths.items()):
            parts = Path(display_path).parts
            # Add directory nodes
            current = tree.root
            for i, part in enumerate(parts[:-1]):
                key = "/".join(parts[: i + 1])
                if key not in dirs:
                    node = current.add(f"▾ {part}/", data=None)
                    node.expand()
                    dirs[key] = node
                current = dirs[key]

            # Add file leaf with status icon
            if status == "new":
                icon = "✚"
            elif status == "modified":
                icon = "✎"
            else:
                icon = "·"
            filename = parts[-1] if parts else display_path
            data_path = self._path_lookup.get(display_path, display_path)
            current.add_leaf(f"{icon} {filename}", data=data_path)

        yield tree
        yield Label("", id="file_preview_header")
        yield Static("Select a file to preview", id="file_preview")

    def rebuild_tree(self) -> None:
        """Rebuild the tree widget in-place from current _all_paths."""
        try:
            tree = self.query_one("#file_tree", Tree)
        except Exception:
            return
        tree.clear()
        dirs: Dict[str, any] = {}
        for display_path, status in sorted(self._all_paths.items()):
            parts = Path(display_path).parts
            current = tree.root
            for i, part in enumerate(parts[:-1]):
                key = "/".join(parts[: i + 1])
                if key not in dirs:
                    node = current.add(f"▾ {part}/", data=None)
                    node.expand()
                    dirs[key] = node
                current = dirs[key]
            if status == "new":
                icon = "✚"
            elif status == "modified":
                icon = "✎"
            else:
                icon = "·"
            filename = parts[-1] if parts else display_path
            data_path = self._path_lookup.get(display_path, display_path)
            current.add_leaf(f"{icon} {filename}", data=data_path)
        tree.root.expand()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Load preview when a file is clicked."""
        from textual.widgets import Label

        filepath = event.node.data
        if not filepath:
            return

        try:
            preview_header = self.query_one("#file_preview_header", Label)
            preview_widget = self.query_one("#file_preview", Static)

            p = Path(filepath)
            preview_header.update(f"── {p.name} ──")

            if p.exists() and p.is_file():
                try:
                    content = p.read_text(errors="replace")
                    # Limit to first 100 lines
                    lines = content.splitlines()[:100]
                    if len(content.splitlines()) > 100:
                        lines.append(f"\n... ({len(content.splitlines()) - 100} more lines)")
                    preview_widget.update("\n".join(lines))
                except Exception:
                    preview_widget.update(f"(unable to read {filepath})")
            else:
                preview_widget.update(f"(file not found: {filepath})")
        except Exception:
            pass
