# -*- coding: utf-8 -*-
"""Snapshot prototypes for final-answer lock UI options.

These tests intentionally exercise multiple visual concepts in separate style
files so we can compare lock-mode UX before selecting one to integrate.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Static

from massgen.frontend.displays.textual_widgets.content_sections import (
    FinalPresentationCard,
    TimelineSection,
)

_OPTION_DIR = Path(__file__).resolve().parents[2] / "frontend" / "displays" / "textual_themes" / "prototypes" / "final_lock"


def _configure_snapshot_terminal_environment(monkeypatch) -> None:  # noqa: ANN001 - pytest fixture type
    """Pin terminal color behavior so snapshots stay deterministic."""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.setenv("COLORTERM", "truecolor")


def _seed_final_card_shell(timeline: TimelineSection, option_class: str) -> None:
    timeline.add_separator("Round 4", round_number=4)
    timeline.add_widget(Static("intermediate output", id="middle_card"), round_number=4)

    final_card = FinalPresentationCard(
        agent_id="agent_a",
        vote_results={
            "vote_counts": {"A2.3": 2, "B2.1": 1},
            "winner": "A2.3",
            "is_tie": False,
        },
        context_paths={
            "new": [
                "tasks/evolving_skill/SKILL.md",
                "tasks/checklist_gap_report.md",
            ],
            "modified": ["docs/notes/final_lock.md"],
        },
        id="final_presentation_card",
    )
    final_card.add_class(option_class)
    timeline.add_widget(final_card, round_number=4)


async def _settle_snapshot(pilot) -> None:  # noqa: ANN001 - fixture-provided type
    """Settle timers before capture."""
    app = pilot.app
    timeline = app.query_one(TimelineSection)
    final_card = app.query_one("#final_presentation_card", FinalPresentationCard)
    if not timeline.is_answer_locked:
        final_card.append_chunk(
            "Created `POEM.md` in workspace with an 11-stanza free verse poem.\n\n"
            "## Highlights\n"
            "- Original metaphors\n"
            "- Concrete domestic imagery\n"
            "- Strong narrative arc\n\n"
            "The output is ready for handoff.",
        )
        final_card.complete()
        final_card.set_locked_mode(True)
        final_card.refresh(layout=True)
        timeline.lock_to_final_answer("final_presentation_card")

    for card in app.query(FinalPresentationCard):
        try:
            card._flush_stream_buffer()
            card._sync_locked_render_mode()
        except Exception:
            pass
    for timer in list(getattr(app, "_timers", [])):
        try:
            timer.stop()
        except Exception:
            pass
    await pilot.pause()


class _FinalLockSignalStripApp(App):
    CSS_PATH = str(_OPTION_DIR / "option_signal_strip.tcss")

    def compose(self) -> ComposeResult:
        yield TimelineSection(id="timeline")

    def on_mount(self) -> None:
        _seed_final_card_shell(self.query_one(TimelineSection), "option-signal-strip")


class _FinalLockEditorialSplitApp(App):
    CSS_PATH = str(_OPTION_DIR / "option_editorial_split.tcss")

    def compose(self) -> ComposeResult:
        yield TimelineSection(id="timeline")

    def on_mount(self) -> None:
        _seed_final_card_shell(self.query_one(TimelineSection), "option-editorial-split")


class _FinalLockCommandDeckApp(App):
    CSS_PATH = str(_OPTION_DIR / "option_command_deck.tcss")

    def compose(self) -> ComposeResult:
        yield TimelineSection(id="timeline")

    def on_mount(self) -> None:
        _seed_final_card_shell(self.query_one(TimelineSection), "option-command-deck")


class _FinalLockZenFocusApp(App):
    CSS_PATH = str(_OPTION_DIR / "option_zen_focus.tcss")

    def compose(self) -> ComposeResult:
        yield TimelineSection(id="timeline")

    def on_mount(self) -> None:
        _seed_final_card_shell(self.query_one(TimelineSection), "option-zen-focus")


class _FinalLockCompactStackApp(App):
    CSS_PATH = str(_OPTION_DIR / "option_compact_stack.tcss")

    def compose(self) -> ComposeResult:
        yield TimelineSection(id="timeline")

    def on_mount(self) -> None:
        _seed_final_card_shell(self.query_one(TimelineSection), "option-compact-stack")


class _FinalLockTimelineNativeProApp(App):
    CSS_PATH = str(_OPTION_DIR / "option_timeline_native_pro.tcss")

    def compose(self) -> ComposeResult:
        yield TimelineSection(id="timeline")

    def on_mount(self) -> None:
        _seed_final_card_shell(self.query_one(TimelineSection), "option-timeline-native-pro")


class _FinalLockEvidenceDockedProApp(App):
    CSS_PATH = str(_OPTION_DIR / "option_evidence_docked_pro.tcss")

    def compose(self) -> ComposeResult:
        yield TimelineSection(id="timeline")

    def on_mount(self) -> None:
        _seed_final_card_shell(self.query_one(TimelineSection), "option-evidence-docked-pro")


class _FinalLockBriefingPanelProApp(App):
    CSS_PATH = str(_OPTION_DIR / "option_briefing_panel_pro.tcss")

    def compose(self) -> ComposeResult:
        yield TimelineSection(id="timeline")

    def on_mount(self) -> None:
        _seed_final_card_shell(self.query_one(TimelineSection), "option-briefing-panel-pro")


def test_final_lock_option_signal_strip(snap_compare, monkeypatch) -> None:  # noqa: ANN001 - pytest fixture type
    _configure_snapshot_terminal_environment(monkeypatch)
    assert snap_compare(
        _FinalLockSignalStripApp(),
        terminal_size=(150, 40),
        run_before=_settle_snapshot,
    )


def test_final_lock_option_editorial_split(snap_compare, monkeypatch) -> None:  # noqa: ANN001 - pytest fixture type
    _configure_snapshot_terminal_environment(monkeypatch)
    assert snap_compare(
        _FinalLockEditorialSplitApp(),
        terminal_size=(150, 40),
        run_before=_settle_snapshot,
    )


def test_final_lock_option_command_deck(snap_compare, monkeypatch) -> None:  # noqa: ANN001 - pytest fixture type
    _configure_snapshot_terminal_environment(monkeypatch)
    assert snap_compare(
        _FinalLockCommandDeckApp(),
        terminal_size=(150, 40),
        run_before=_settle_snapshot,
    )


def test_final_lock_option_zen_focus(snap_compare, monkeypatch) -> None:  # noqa: ANN001 - pytest fixture type
    _configure_snapshot_terminal_environment(monkeypatch)
    assert snap_compare(
        _FinalLockZenFocusApp(),
        terminal_size=(150, 40),
        run_before=_settle_snapshot,
    )


def test_final_lock_option_compact_stack(snap_compare, monkeypatch) -> None:  # noqa: ANN001 - pytest fixture type
    _configure_snapshot_terminal_environment(monkeypatch)
    assert snap_compare(
        _FinalLockCompactStackApp(),
        terminal_size=(150, 40),
        run_before=_settle_snapshot,
    )


def test_final_lock_option_timeline_native_pro(snap_compare, monkeypatch) -> None:  # noqa: ANN001 - pytest fixture type
    _configure_snapshot_terminal_environment(monkeypatch)
    assert snap_compare(
        _FinalLockTimelineNativeProApp(),
        terminal_size=(150, 40),
        run_before=_settle_snapshot,
    )


def test_final_lock_option_evidence_docked_pro(snap_compare, monkeypatch) -> None:  # noqa: ANN001 - pytest fixture type
    _configure_snapshot_terminal_environment(monkeypatch)
    assert snap_compare(
        _FinalLockEvidenceDockedProApp(),
        terminal_size=(150, 40),
        run_before=_settle_snapshot,
    )


def test_final_lock_option_briefing_panel_pro(snap_compare, monkeypatch) -> None:  # noqa: ANN001 - pytest fixture type
    _configure_snapshot_terminal_environment(monkeypatch)
    assert snap_compare(
        _FinalLockBriefingPanelProApp(),
        terminal_size=(150, 40),
        run_before=_settle_snapshot,
    )
