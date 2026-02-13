# -*- coding: utf-8 -*-
"""
Standalone prototype for the GitDiffReviewModal professional redesign.

Run directly: uv run python massgen/tests/frontend/review_modal_prototype.py

This app mounts the real GitDiffReviewModal with sample data and applies CSS
overrides for the new near-fullscreen, professional design.
"""

from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Static

from massgen.frontend.displays.textual.widgets.modal_base import MODAL_BASE_CSS
from massgen.frontend.displays.textual.widgets.modals.review_modal import (
    GitDiffReviewModal,
)

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_DIFF = """\
diff --git a/src/app.py b/src/app.py
index abc1234..def5678 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1,4 +1,5 @@
 import os
+import sys

 def main():
     pass
@@ -10,3 +11,3 @@ def helper():
-    return False
+    return True
     # end
"""

MULTI_FILE_DIFF = (
    SAMPLE_DIFF
    + """\

diff --git a/new_feature.py b/new_feature.py
new file mode 100644
--- /dev/null
+++ b/new_feature.py
@@ -0,0 +1,8 @@
+\"\"\"New feature module.\"\"\"
+
+
+def process(data):
+    result = []
+    for item in data:
+        result.append(item * 2)
+    return result

diff --git a/utils/helpers.py b/utils/helpers.py
index 999aaa..bbb111 100644
--- a/utils/helpers.py
+++ b/utils/helpers.py
@@ -5,6 +5,10 @@ import json
 def load_config(path):
     with open(path) as f:
         return json.load(f)
+
+
+def save_config(path, data):
+    with open(path, 'w') as f:
+        json.dump(data, f, indent=2)

diff --git a/tests/test_app.py b/tests/test_app.py
index ccc222..ddd333 100644
--- a/tests/test_app.py
+++ b/tests/test_app.py
@@ -1,5 +1,9 @@
 import pytest
+from unittest.mock import patch

 def test_main():
     assert True
+
+def test_helper():
+    assert helper() is True
"""
)


def _make_review_changes():
    return [
        {
            "original_path": "/home/user/project",
            "isolated_path": "/tmp/massgen_worktree",
            "changes": [
                {"status": "M", "path": "src/app.py"},
                {"status": "A", "path": "new_feature.py"},
                {"status": "M", "path": "utils/helpers.py"},
                {"status": "M", "path": "tests/test_app.py"},
                {"status": "D", "path": "deprecated.py"},
            ],
            "diff": MULTI_FILE_DIFF,
        },
    ]


# ---------------------------------------------------------------------------
# Load MassGen theme CSS chain
# ---------------------------------------------------------------------------
_THEMES_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "displays" / "textual_themes"
_PALETTE_CSS = (_THEMES_DIR / "palettes" / "_dark.tcss").read_text()
_BASE_CSS = (_THEMES_DIR / "base.tcss").read_text()

# ---------------------------------------------------------------------------
# CSS overrides for the new professional design
# ---------------------------------------------------------------------------
REDESIGN_CSS = """
/* ===== Review Modal Professional Redesign ===== */

/* Near-fullscreen container */
.review-modal {
    width: 98%;
    max-width: 180;
    height: 96%;
    padding: 0 1;
}

/* Header with surface bg and bottom border */
.review-modal .modal-header {
    background: $bg-surface;
    border-bottom: solid $border-muted;
}

/* Summary with surface bg */
.review-modal .modal-summary {
    background: $bg-surface;
}

/* Instructions: single line, compact */
.review-modal .modal-instructions {
    height: 1;
    max-height: 1;
    overflow: hidden;
    background: $bg-surface;
    border-bottom: solid $border-muted;
}

/* File list panel */
.review-modal .review-file-list {
    background: $bg-surface;
    border-right: solid $border-default;
}

/* File list header with border */
.review-modal .review-file-list-header {
    border-bottom: solid $border-muted;
}

/* Diff panel: no left padding */
.review-modal .review-diff-panel {
    padding-left: 0;
}

/* Diff header: brighter text + border */
.review-modal .review-diff-header {
    color: $fg-secondary;
    border-bottom: solid $border-muted;
}

/* Footer: flush, bordered, surface bg */
.review-modal .modal-footer {
    margin-top: 0;
    border-top: solid $surface-lighten-1;
    background: $bg-surface;
}
"""


class ReviewModalPrototypeApp(App):
    """Prototype app for the redesigned review modal."""

    CSS = _PALETTE_CSS + "\n" + MODAL_BASE_CSS + "\n" + _BASE_CSS + "\n" + REDESIGN_CSS

    def compose(self) -> ComposeResult:
        yield Static("")

    def on_mount(self) -> None:
        modal = GitDiffReviewModal(changes=_make_review_changes())
        self.push_screen(modal)


if __name__ == "__main__":
    app = ReviewModalPrototypeApp()
    app.run()
