# -*- coding: utf-8 -*-
"""Skill management modals for Textual TUI."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from textual.app import ComposeResult
    from textual.containers import Container, Horizontal, VerticalScroll
    from textual.widgets import Button, Checkbox, Label, Static

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False

from ..modal_base import BaseModal


class SkillsModal(BaseModal):
    """Modal for viewing and toggling available skills for the current session."""

    def __init__(
        self,
        *,
        default_skills: List[Dict[str, Any]],
        created_skills: List[Dict[str, Any]],
        enabled_skill_names: Optional[List[str]],
    ) -> None:
        super().__init__()
        self._default_skills = default_skills
        self._created_skills = created_skills
        self._enabled_skill_names = enabled_skill_names
        self._checkbox_to_name: Dict[str, str] = {}

    def _is_enabled(self, name: str) -> bool:
        """Return whether a skill should render as enabled."""
        if self._enabled_skill_names is None:
            return True
        enabled = {s.lower() for s in self._enabled_skill_names}
        return name.lower() in enabled

    def compose(self) -> ComposeResult:
        total = len(self._default_skills) + len(self._created_skills)
        with Container(id="skills_modal_container"):
            yield Label("🧩 Skills Manager", id="skills_modal_header")
            yield Label(
                f"{total} skill(s) discovered • Session-only toggles",
                id="skills_modal_summary",
            )

            with VerticalScroll(id="skills_modal_scroll"):
                yield Label("Default Skills", classes="modal-section-header")
                if self._default_skills:
                    for idx, skill in enumerate(self._default_skills):
                        name = skill.get("name", f"default-{idx}")
                        desc = skill.get("description", "")
                        checkbox_id = f"skill_default_{idx}"
                        self._checkbox_to_name[checkbox_id] = name
                        yield Checkbox(name, value=self._is_enabled(name), id=checkbox_id)
                        if desc:
                            yield Static(f"[dim]{desc}[/]", markup=True, classes="modal-list-item")
                else:
                    yield Static("[dim]No default skills found[/]", markup=True, classes="modal-list-item")

                yield Label("Created Skills", classes="modal-section-header")
                if self._created_skills:
                    for idx, skill in enumerate(self._created_skills):
                        name = skill.get("name", f"created-{idx}")
                        desc = skill.get("description", "")
                        location = skill.get("location", "created")
                        checkbox_id = f"skill_created_{idx}"
                        self._checkbox_to_name[checkbox_id] = name
                        yield Checkbox(
                            f"{name} [{location}]",
                            value=self._is_enabled(name),
                            id=checkbox_id,
                        )
                        if desc:
                            yield Static(f"[dim]{desc}[/]", markup=True, classes="modal-list-item")
                else:
                    yield Static("[dim]No created skills found[/]", markup=True, classes="modal-list-item")

            with Horizontal(id="skills_modal_actions"):
                yield Button("Enable All", id="enable_all_skills_btn")
                yield Button("Disable All", id="disable_all_skills_btn")
                yield Button("Apply", id="apply_skills_btn", variant="primary")
                yield Button("Cancel", id="skills_cancel_button")

    def _set_all_checkboxes(self, value: bool) -> None:
        """Set all skill checkboxes to the given value."""
        for checkbox_id in self._checkbox_to_name:
            try:
                cb = self.query_one(f"#{checkbox_id}", Checkbox)
                cb.value = value
            except Exception:
                continue

    def _collect_enabled_names(self) -> List[str]:
        """Collect selected skill names from checkbox state."""
        selected: List[str] = []
        for checkbox_id, name in self._checkbox_to_name.items():
            try:
                cb = self.query_one(f"#{checkbox_id}", Checkbox)
                if cb.value:
                    selected.append(name)
            except Exception:
                continue
        return selected

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "enable_all_skills_btn":
            self._set_all_checkboxes(True)
            return
        if event.button.id == "disable_all_skills_btn":
            self._set_all_checkboxes(False)
            return
        if event.button.id == "apply_skills_btn":
            self.dismiss(self._collect_enabled_names())
            event.stop()
            return
        if event.button.id == "skills_cancel_button":
            self.dismiss(None)
            event.stop()
            return
