# -*- coding: utf-8 -*-
"""Layout regression tests for the bottom input/mode bar area."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from massgen.frontend.displays import textual_terminal_display as textual_display_module
from massgen.frontend.displays.textual_terminal_display import TextualTerminalDisplay
from massgen.frontend.displays.textual_widgets.mode_bar import ModeToggle


def _widget_text(widget: object) -> str:
    """Extract visible text from a Textual widget."""
    return str(widget.render())


def _strip_text(line: object) -> str:
    """Extract plain text from a Textual Strip-like render line."""
    segments = getattr(line, "segments", None) or getattr(line, "_segments", None)
    if not segments:
        return str(line)
    return "".join(getattr(segment, "text", "") for segment in segments)


def test_mode_toggle_compact_labels_do_not_keep_wide_padding() -> None:
    """Compact mode should avoid wide fixed padding to preserve horizontal space."""
    toggle = ModeToggle(
        mode_type="plan",
        initial_state="normal",
        states=["normal", "plan", "execute", "analysis"],
    )
    toggle.set_compact(True)

    rendered = str(toggle.render())
    assert "Norm" in rendered
    assert "Norm   " not in rendered


def test_mode_toggle_compact_analysis_label_is_anly() -> None:
    """Compact analysis label should use a short neutral token."""
    toggle = ModeToggle(
        mode_type="plan",
        initial_state="analysis",
        states=["normal", "plan", "execute", "analysis"],
    )
    toggle.set_compact(True)

    rendered = str(toggle.render())
    assert "Anly" in rendered
    assert "Analyze" not in rendered


def test_mode_toggle_persona_off_label_is_neutral() -> None:
    """Persona toggle should avoid explicit OFF text; inactive state is shown via styling."""
    compact_toggle = ModeToggle(
        mode_type="personas",
        initial_state="off",
        states=["off", "on"],
    )
    compact_toggle.set_compact(True)
    compact_rendered = str(compact_toggle.render())
    assert "Persona Off" not in compact_rendered
    assert "Persona" in compact_rendered

    full_toggle = ModeToggle(
        mode_type="personas",
        initial_state="off",
        states=["off", "on"],
    )
    full_toggle.set_compact(False)
    full_rendered = str(full_toggle.render())
    assert "Personas OFF" not in full_rendered
    assert "Personas" in full_rendered


@pytest.mark.asyncio
async def test_mode_bar_stays_within_input_header_at_narrow_width(monkeypatch, tmp_path: Path) -> None:
    """Mode bar should stay in bounds while keeping primary toggle labels visible."""
    monkeypatch.setattr(textual_display_module, "get_event_emitter", lambda: None)
    monkeypatch.setattr(
        textual_display_module,
        "get_user_settings",
        lambda: SimpleNamespace(theme="dark", vim_mode=True),
    )

    display = TextualTerminalDisplay(
        ["agent_a", "agent_b", "agent_c"],
        agent_models={
            "agent_a": "gpt-5.3-codex",
            "agent_b": "claude-opus-4-6",
            "agent_c": "gemini-3-flash-preview",
        },
        keyboard_interactive_mode=False,
        output_dir=tmp_path,
        theme="dark",
    )
    app = textual_display_module.TextualApp(
        display=display,
        question="Welcome! Type your question below...",
        buffers=display._buffers,
        buffer_lock=display._buffer_lock,
        buffer_flush_interval=display.buffer_flush_interval,
    )
    display._app = app

    async with app.run_test(headless=True, size=(90, 24)) as pilot:
        await pilot.pause()

        # Max out mode-bar content to mimic the reported overlap case.
        app._update_vim_indicator(False)  # insert mode -> input hint visible
        assert app._mode_bar is not None
        app._mode_bar.set_plan_mode("analysis")
        app._mode_bar.set_coordination_mode("decomposition")
        app._mode_bar.set_skills_available(True)
        await pilot.pause()

        mode_bar = app.query_one("#mode_bar")
        input_header = app.query_one("#input_header")

        mode_left = mode_bar.region.x
        mode_right = mode_left + mode_bar.region.width
        header_left = input_header.region.x
        header_right = header_left + input_header.region.width

        assert mode_left >= header_left
        assert mode_right <= header_right
        assert mode_bar.region.height >= 2

        # Primary run-mode toggles should remain visible, not clipped to icon-only.
        for toggle_id in ("#plan_toggle", "#agent_toggle", "#refinement_toggle", "#coordination_toggle"):
            toggle = app.query_one(toggle_id)
            assert toggle.region.width > 0
            assert toggle.region.height > 0
            assert toggle.region.x + toggle.region.width <= mode_right

        assert any(token in _widget_text(app.query_one("#plan_toggle")) for token in ("Anly", "Analyze"))
        assert "Decomp" in _widget_text(app.query_one("#coordination_toggle"))

        # Row layout may remain single-line if controls fit after responsive compaction.
        row_primary = app.query_one("#mode_row_primary")
        row_secondary = app.query_one("#mode_row_secondary")
        assert row_secondary.region.y >= row_primary.region.y

        # Meta panel should move below mode controls on narrow layouts.
        input_modes_row = app.query_one("#input_modes_row")
        input_meta_panel = app.query_one("#input_meta_panel")
        assert "meta-stacked" in input_modes_row.classes
        assert input_meta_panel.region.y > mode_bar.region.y

        vim_indicator = app.query_one("#vim_indicator")
        input_hint = app.query_one("#input_hint")
        assert "Insert" in _widget_text(vim_indicator)
        assert "Ctrl+P" in _widget_text(input_hint)
        assert input_hint.region.y > mode_bar.region.y


@pytest.mark.asyncio
async def test_analysis_mode_stacks_meta_panel_at_standard_narrow_width(monkeypatch, tmp_path: Path) -> None:
    """Analysis mode should prioritize run controls and stack right-side meta hints earlier."""
    monkeypatch.setattr(textual_display_module, "get_event_emitter", lambda: None)
    monkeypatch.setattr(
        textual_display_module,
        "get_user_settings",
        lambda: SimpleNamespace(theme="dark", vim_mode=True),
    )

    display = TextualTerminalDisplay(
        ["agent_a", "agent_b", "agent_c"],
        agent_models={
            "agent_a": "gpt-5.3-codex",
            "agent_b": "claude-opus-4-6",
            "agent_c": "gemini-3-flash-preview",
        },
        keyboard_interactive_mode=False,
        output_dir=tmp_path,
        theme="dark",
    )
    app = textual_display_module.TextualApp(
        display=display,
        question="Welcome! Type your question below...",
        buffers=display._buffers,
        buffer_lock=display._buffer_lock,
        buffer_flush_interval=display.buffer_flush_interval,
    )
    display._app = app

    async with app.run_test(headless=True, size=(150, 24)) as pilot:
        await pilot.pause()
        app._update_vim_indicator(False)
        assert app._mode_bar is not None
        app._mode_state.plan_mode = "analysis"
        app._mode_bar.set_plan_mode("analysis")
        app._refresh_input_modes_row_layout()
        await pilot.pause()

        input_modes_row = app.query_one("#input_modes_row")
        input_meta_panel = app.query_one("#input_meta_panel")
        mode_bar = app.query_one("#mode_bar")

        assert "meta-stacked" in input_modes_row.classes
        assert input_meta_panel.region.y > mode_bar.region.y
        assert any(token in _widget_text(app.query_one("#plan_toggle")) for token in ("Anly", "Analyze", "Analyzing"))


@pytest.mark.asyncio
async def test_mode_bar_does_not_render_skills_button(monkeypatch, tmp_path: Path) -> None:
    """Skills manager should no longer appear as a mode-bar control."""
    monkeypatch.setattr(textual_display_module, "get_event_emitter", lambda: None)
    monkeypatch.setattr(
        textual_display_module,
        "get_user_settings",
        lambda: SimpleNamespace(theme="dark", vim_mode=False),
    )

    display = TextualTerminalDisplay(
        ["agent_a"],
        agent_models={"agent_a": "gpt-5.3-codex"},
        keyboard_interactive_mode=False,
        output_dir=tmp_path,
        theme="dark",
    )
    app = textual_display_module.TextualApp(
        display=display,
        question="Welcome! Type your question below...",
        buffers=display._buffers,
        buffer_lock=display._buffer_lock,
        buffer_flush_interval=display.buffer_flush_interval,
    )
    display._app = app

    async with app.run_test(headless=True, size=(120, 24)) as pilot:
        await pilot.pause()
        assert len(app.query("#skills_btn")) == 0


@pytest.mark.asyncio
async def test_mode_bar_uses_single_row_when_space_is_available(monkeypatch, tmp_path: Path) -> None:
    """Wide terminals should keep mode controls on a single row."""
    monkeypatch.setattr(textual_display_module, "get_event_emitter", lambda: None)
    monkeypatch.setattr(
        textual_display_module,
        "get_user_settings",
        lambda: SimpleNamespace(theme="dark", vim_mode=False),
    )

    display = TextualTerminalDisplay(
        ["agent_a", "agent_b", "agent_c"],
        agent_models={
            "agent_a": "gpt-5.3-codex",
            "agent_b": "claude-opus-4-6",
            "agent_c": "gemini-3-flash-preview",
        },
        keyboard_interactive_mode=False,
        output_dir=tmp_path,
        theme="dark",
    )
    app = textual_display_module.TextualApp(
        display=display,
        question="Welcome! Type your question below...",
        buffers=display._buffers,
        buffer_lock=display._buffer_lock,
        buffer_flush_interval=display.buffer_flush_interval,
    )
    display._app = app

    async with app.run_test(headless=True, size=(170, 28)) as pilot:
        await pilot.pause()
        assert app._mode_bar is not None
        app._mode_bar.set_skills_available(True)
        await pilot.pause()

        row_primary = app.query_one("#mode_row_primary")
        row_secondary = app.query_one("#mode_row_secondary")
        assert row_secondary.region.y == row_primary.region.y

        # Plan label should remain visible in wider states when toggled.
        app._mode_bar.set_plan_mode("plan")
        await pilot.pause()
        assert any(token in _widget_text(app.query_one("#plan_toggle")) for token in ("Planning", "Plan"))

        app._mode_bar.set_plan_mode("execute")
        await pilot.pause()
        assert any(token in _widget_text(app.query_one("#plan_toggle")) for token in ("Executing", "Exec"))

        app._mode_bar.set_plan_mode("analysis")
        await pilot.pause()
        assert any(token in _widget_text(app.query_one("#plan_toggle")) for token in ("Analyzing", "Analyze", "Anly"))


@pytest.mark.asyncio
async def test_single_agent_mode_disables_decomposition(monkeypatch, tmp_path: Path) -> None:
    """Single-agent mode should force parallel coordination and disable decomposition toggle."""
    monkeypatch.setattr(textual_display_module, "get_event_emitter", lambda: None)
    monkeypatch.setattr(
        textual_display_module,
        "get_user_settings",
        lambda: SimpleNamespace(theme="dark", vim_mode=False),
    )

    display = TextualTerminalDisplay(
        ["agent_a", "agent_b", "agent_c"],
        agent_models={
            "agent_a": "gpt-5.3-codex",
            "agent_b": "claude-opus-4-6",
            "agent_c": "gemini-3-flash-preview",
        },
        keyboard_interactive_mode=False,
        output_dir=tmp_path,
        theme="dark",
    )
    app = textual_display_module.TextualApp(
        display=display,
        question="Welcome! Type your question below...",
        buffers=display._buffers,
        buffer_lock=display._buffer_lock,
        buffer_flush_interval=display.buffer_flush_interval,
    )
    display._app = app

    async with app.run_test(headless=True, size=(120, 26)) as pilot:
        await pilot.pause()
        assert app._mode_bar is not None

        # Multi-agent mode can use decomposition.
        app._handle_coordination_mode_change("decomposition")
        await pilot.pause()
        assert app._mode_state.coordination_mode == "decomposition"
        assert app._mode_bar.get_coordination_mode() == "decomposition"

        # Switching to single-agent mode forces coordination back to parallel.
        app._handle_agent_mode_change("single")
        await pilot.pause()
        coordination_toggle = app.query_one("#coordination_toggle")
        assert app._mode_state.coordination_mode == "parallel"
        assert app._mode_bar.get_coordination_mode() == "parallel"
        assert "disabled" in coordination_toggle.classes

        # Attempting decomposition while single-agent should be rejected.
        app._handle_coordination_mode_change("decomposition")
        await pilot.pause()
        assert app._mode_state.coordination_mode == "parallel"
        assert app._mode_bar.get_coordination_mode() == "parallel"

        # Returning to multi-agent mode re-enables the coordination toggle.
        app._handle_agent_mode_change("multi")
        await pilot.pause()
        assert "disabled" not in coordination_toggle.classes


@pytest.mark.asyncio
async def test_welcome_screen_reflows_for_narrow_terminals(monkeypatch, tmp_path: Path) -> None:
    """Welcome screen should use compact content while keeping right-panel hints readable."""
    monkeypatch.setattr(textual_display_module, "get_event_emitter", lambda: None)
    monkeypatch.setattr(
        textual_display_module,
        "get_user_settings",
        lambda: SimpleNamespace(theme="dark", vim_mode=False),
    )

    display = TextualTerminalDisplay(
        ["agent_a", "agent_b", "agent_c"],
        agent_models={
            "agent_a": "gpt-5.3-codex",
            "agent_b": "claude-opus-4-6",
            "agent_c": "gemini-3-flash-preview",
        },
        keyboard_interactive_mode=False,
        output_dir=tmp_path,
        theme="dark",
    )
    app = textual_display_module.TextualApp(
        display=display,
        question="Welcome! Type your question below...",
        buffers=display._buffers,
        buffer_lock=display._buffer_lock,
        buffer_flush_interval=display.buffer_flush_interval,
    )
    display._app = app

    async with app.run_test(headless=True, size=(70, 24)) as pilot:
        await pilot.pause()

        logo_text = _widget_text(app.query_one("#welcome_logo"))
        agents_text = _widget_text(app.query_one("#welcome_agents"))
        input_hint_text = _widget_text(app.query_one("#input_hint"))
        vim_indicator = app.query_one("#vim_indicator")
        input_header = app.query_one("#input_header")
        input_hint = app.query_one("#input_hint")

        assert logo_text.strip() == "MASSGEN"
        assert "agent_a" in agents_text
        assert "openai/gpt-5.3-codex" in agents_text
        assert "anthropic/claude-opus-4-6" in agents_text
        assert "google/gemini-3-flash-preview" in agents_text
        assert "Ctrl+P" in input_hint_text
        assert "CWD" in input_hint_text
        assert Path.cwd().name in input_hint_text
        assert len(input_hint_text) <= 42
        assert input_header.region.y <= vim_indicator.region.y < input_header.region.y + input_header.region.height
        assert input_header.region.y <= input_hint.region.y < input_header.region.y + input_header.region.height
        assert input_hint.region.y > vim_indicator.region.y


@pytest.mark.asyncio
async def test_welcome_screen_uses_left_aligned_agent_model_rows(monkeypatch, tmp_path: Path) -> None:
    """Wide welcome layout should render agent/model lines in left-aligned rows."""
    monkeypatch.setattr(textual_display_module, "get_event_emitter", lambda: None)
    monkeypatch.setattr(
        textual_display_module,
        "get_user_settings",
        lambda: SimpleNamespace(theme="dark", vim_mode=False),
    )

    display = TextualTerminalDisplay(
        ["agent_a", "agent_b", "agent_c"],
        agent_models={
            "agent_a": "gpt-5.3-codex",
            "agent_b": "claude-opus-4-6",
            "agent_c": "gemini-3-flash-preview",
        },
        keyboard_interactive_mode=False,
        output_dir=tmp_path,
        theme="dark",
    )
    app = textual_display_module.TextualApp(
        display=display,
        question="Welcome! Type your question below...",
        buffers=display._buffers,
        buffer_lock=display._buffer_lock,
        buffer_flush_interval=display.buffer_flush_interval,
    )
    display._app = app

    async with app.run_test(headless=True, size=(120, 26)) as pilot:
        await pilot.pause()
        agents_widget = app.query_one("#welcome_agents")
        agents_text = _widget_text(app.query_one("#welcome_agents"))
        model_rows = [line for line in agents_text.splitlines() if " - " in line and "/" in line]
        assert len(model_rows) == 3
        assert all(line.startswith("agent_") for line in model_rows)
        assert all(" - " in line for line in model_rows)
        assert agents_widget.region.x > 0


@pytest.mark.asyncio
async def test_context_hint_persists_after_first_prompt(monkeypatch, tmp_path: Path) -> None:
    """CWD/context hint should remain visible in the input meta panel after welcome is dismissed."""
    monkeypatch.setattr(textual_display_module, "get_event_emitter", lambda: None)
    monkeypatch.setattr(
        textual_display_module,
        "get_user_settings",
        lambda: SimpleNamespace(theme="dark", vim_mode=False),
    )

    display = TextualTerminalDisplay(
        ["agent_a"],
        agent_models={"agent_a": "gpt-5.3-codex"},
        keyboard_interactive_mode=False,
        output_dir=tmp_path,
        theme="dark",
    )
    app = textual_display_module.TextualApp(
        display=display,
        question="Welcome! Type your question below...",
        buffers=display._buffers,
        buffer_lock=display._buffer_lock,
        buffer_flush_interval=display.buffer_flush_interval,
    )
    display._app = app

    async with app.run_test(headless=True, size=(100, 24)) as pilot:
        await pilot.pause()
        input_hint = app.query_one("#input_hint")
        assert "Ctrl+P" in _widget_text(input_hint)
        assert "CWD" in _widget_text(input_hint)
        assert Path.cwd().name in _widget_text(input_hint)

        app._dismiss_welcome()
        await pilot.pause()
        assert "hidden" not in input_hint.classes
        assert "Ctrl+P" in _widget_text(input_hint)
        assert "CWD" in _widget_text(input_hint)


@pytest.mark.asyncio
async def test_input_bar_shows_placeholder_shadow_text(monkeypatch, tmp_path: Path) -> None:
    """Empty input should still show guidance text in-place."""
    monkeypatch.setattr(textual_display_module, "get_event_emitter", lambda: None)
    monkeypatch.setattr(
        textual_display_module,
        "get_user_settings",
        lambda: SimpleNamespace(theme="dark", vim_mode=False),
    )

    display = TextualTerminalDisplay(
        ["agent_a"],
        agent_models={"agent_a": "gpt-5.3-codex"},
        keyboard_interactive_mode=False,
        output_dir=tmp_path,
        theme="dark",
    )
    app = textual_display_module.TextualApp(
        display=display,
        question="Welcome! Type your question below...",
        buffers=display._buffers,
        buffer_lock=display._buffer_lock,
        buffer_flush_interval=display.buffer_flush_interval,
    )
    display._app = app

    async with app.run_test(headless=True, size=(100, 24)) as pilot:
        await pilot.pause()
        question_input = app.query_one("#question_input")
        assert question_input.text == ""
        placeholder_line = _strip_text(question_input.render_line(0))
        assert "Enter to submit" in placeholder_line


@pytest.mark.asyncio
async def test_ctrl_p_toggle_emits_full_cwd_toast(monkeypatch, tmp_path: Path) -> None:
    """Ctrl+P should emit a toast that includes full CWD and new context mode."""
    monkeypatch.setattr(textual_display_module, "get_event_emitter", lambda: None)
    monkeypatch.setattr(
        textual_display_module,
        "get_user_settings",
        lambda: SimpleNamespace(theme="dark", vim_mode=False),
    )

    display = TextualTerminalDisplay(
        ["agent_a"],
        agent_models={"agent_a": "gpt-5.3-codex"},
        keyboard_interactive_mode=False,
        output_dir=tmp_path,
        theme="dark",
    )
    app = textual_display_module.TextualApp(
        display=display,
        question="Welcome! Type your question below...",
        buffers=display._buffers,
        buffer_lock=display._buffer_lock,
        buffer_flush_interval=display.buffer_flush_interval,
    )
    display._app = app

    toasts: list[str] = []

    def _capture_toast(message: str, **_: object) -> None:
        toasts.append(message)

    async with app.run_test(headless=True, size=(100, 24)) as pilot:
        await pilot.pause()
        app.notify = _capture_toast  # type: ignore[assignment]
        app._toggle_cwd_auto_include()  # off -> read
        await pilot.pause()

        assert toasts
        assert "Ctrl+P: CWD context read-only" in toasts[-1]
        assert str(Path.cwd()) in toasts[-1]


@pytest.mark.asyncio
async def test_ctrl_p_hint_uses_short_mode_tokens(monkeypatch, tmp_path: Path) -> None:
    """Right-side CWD hint should use short mode tokens (ro/rw) to preserve space."""
    monkeypatch.setattr(textual_display_module, "get_event_emitter", lambda: None)
    monkeypatch.setattr(
        textual_display_module,
        "get_user_settings",
        lambda: SimpleNamespace(theme="dark", vim_mode=False),
    )

    display = TextualTerminalDisplay(
        ["agent_a"],
        agent_models={"agent_a": "gpt-5.3-codex"},
        keyboard_interactive_mode=False,
        output_dir=tmp_path,
        theme="dark",
    )
    app = textual_display_module.TextualApp(
        display=display,
        question="Welcome! Type your question below...",
        buffers=display._buffers,
        buffer_lock=display._buffer_lock,
        buffer_flush_interval=display.buffer_flush_interval,
    )
    display._app = app

    async with app.run_test(headless=True, size=(110, 24)) as pilot:
        await pilot.pause()
        input_hint = app.query_one("#input_hint")

        app._toggle_cwd_auto_include()  # off -> read
        await pilot.pause()
        hint_text = _widget_text(input_hint)
        assert "CWD ro" in hint_text
        assert "read-only" not in hint_text

        app._toggle_cwd_auto_include()  # read -> write
        await pilot.pause()
        hint_text = _widget_text(input_hint)
        assert "CWD rw" in hint_text
        assert "read+write" not in hint_text
