# -*- coding: utf-8 -*-
"""Tests for ChangedocSection system prompt.

Tests cover:
- Section inclusion/exclusion based on config flags
- First-round vs subsequent-round prompt content
- Final presenter consolidation instructions
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from massgen.system_message_builder import SystemMessageBuilder
from massgen.system_prompt_sections import ChangedocSection

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent(system_message="You are a helpful assistant."):
    """Minimal agent stub."""
    backend = MagicMock()
    backend.config = {"model": "gpt-4o-mini"}
    backend.filesystem_manager = None
    backend.backend_params = {}
    backend.mcp_servers = []

    agent = MagicMock()
    agent.get_configurable_system_message.return_value = system_message
    agent.backend = backend
    agent.config = None
    return agent


def _make_config(
    planning_mode_instruction="Plan your approach.",
    enable_changedoc=False,
    broadcast=False,
):
    """Minimal config stub."""
    cc = SimpleNamespace(
        skills_directory=".massgen/skills",
        load_previous_session_skills=False,
        enabled_skill_names=None,
        enable_subagents=False,
        planning_mode_instruction=planning_mode_instruction,
        broadcast=broadcast,
        task_planning_filesystem_mode=False,
        enable_changedoc=enable_changedoc,
    )
    return SimpleNamespace(coordination_config=cc)


def _make_message_templates():
    """Minimal message templates stub."""
    mt = MagicMock()
    mt._voting_sensitivity = "medium"
    mt._answer_novelty_requirement = "moderate"
    mt.final_presentation_system_message.return_value = "Present the best answer."
    return mt


def _make_builder(enable_changedoc=False):
    """Create SystemMessageBuilder with stubs."""
    config = _make_config(enable_changedoc=enable_changedoc)
    mt = _make_message_templates()
    agents = {"agent_a": _make_agent()}
    return SystemMessageBuilder(config=config, message_templates=mt, agents=agents)


# ---------------------------------------------------------------------------
# ChangedocSection unit tests
# ---------------------------------------------------------------------------


class TestChangedocSection:
    """Tests for ChangedocSection prompt content."""

    def test_first_round_content(self):
        """First-round prompt instructs creating tasks/changedoc.md."""
        section = ChangedocSection(has_prior_answers=False)
        content = section.build_content()
        assert "tasks/changedoc.md" in content
        assert "create" in content.lower() or "write" in content.lower()

    def test_subsequent_round_content(self):
        """Subsequent-round prompt instructs inheriting and evolving changedoc."""
        section = ChangedocSection(has_prior_answers=True)
        content = section.build_content()
        assert "inherit" in content.lower() or "build on" in content.lower()
        assert "changedoc" in content.lower()

    def test_first_round_has_template(self):
        """First-round prompt includes the changedoc template structure."""
        section = ChangedocSection(has_prior_answers=False)
        content = section.build_content()
        assert "Change Document" in content
        assert "Decision" in content or "DEC-" in content

    def test_section_metadata(self):
        """Section has correct title and XML tag."""
        section = ChangedocSection()
        assert section.title == "Change Document"
        assert section.xml_tag == "changedoc_instructions"


# ---------------------------------------------------------------------------
# SystemMessageBuilder integration tests
# ---------------------------------------------------------------------------


class TestChangedocInBuildCoordinationMessage:
    """Tests for changedoc section appearing in build_coordination_message."""

    def test_included_when_planning_and_changedoc_enabled(self):
        """ChangedocSection appears when planning_mode + enable_changedoc both True."""
        builder = _make_builder(enable_changedoc=True)
        agent = _make_agent()

        msg = builder.build_coordination_message(
            agent=agent,
            agent_id="agent_a",
            answers=None,
            planning_mode_enabled=True,
            use_skills=False,
            enable_memory=False,
            enable_task_planning=False,
            previous_turns=[],
        )

        assert "changedoc" in msg.lower()

    def test_present_even_when_planning_disabled(self):
        """ChangedocSection appears even when planning mode is off."""
        builder = _make_builder(enable_changedoc=True)
        agent = _make_agent()

        msg = builder.build_coordination_message(
            agent=agent,
            agent_id="agent_a",
            answers=None,
            planning_mode_enabled=False,
            use_skills=False,
            enable_memory=False,
            enable_task_planning=False,
            previous_turns=[],
        )

        assert "changedoc" in msg.lower()

    def test_absent_when_changedoc_disabled(self):
        """ChangedocSection absent when enable_changedoc=False."""
        builder = _make_builder(enable_changedoc=False)
        agent = _make_agent()

        msg = builder.build_coordination_message(
            agent=agent,
            agent_id="agent_a",
            answers=None,
            planning_mode_enabled=True,
            use_skills=False,
            enable_memory=False,
            enable_task_planning=False,
            previous_turns=[],
        )

        assert "changedoc_instructions" not in msg

    def test_first_round_when_no_answers(self):
        """Uses first-round instructions when no answers exist."""
        builder = _make_builder(enable_changedoc=True)
        agent = _make_agent()

        msg = builder.build_coordination_message(
            agent=agent,
            agent_id="agent_a",
            answers=None,
            planning_mode_enabled=True,
            use_skills=False,
            enable_memory=False,
            enable_task_planning=False,
            previous_turns=[],
        )

        # First round: should mention creating changedoc
        assert "tasks/changedoc.md" in msg

    def test_subsequent_round_when_answers_exist(self):
        """Uses subsequent-round instructions when answers are present."""
        builder = _make_builder(enable_changedoc=True)
        agent = _make_agent()

        msg = builder.build_coordination_message(
            agent=agent,
            agent_id="agent_a",
            answers={"agent_b": "Some prior answer"},
            planning_mode_enabled=True,
            use_skills=False,
            enable_memory=False,
            enable_task_planning=False,
            previous_turns=[],
        )

        # Subsequent round: should mention inheriting
        assert "inherit" in msg.lower() or "build on" in msg.lower()
