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
from massgen.system_prompt_sections import (
    _CHECKLIST_ITEMS_CHANGEDOC,
    ChangedocSection,
    EvaluationSection,
    _build_changedoc_checklist_analysis,
    _build_checklist_analysis,
)

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


# ---------------------------------------------------------------------------
# Changedoc-anchored evaluation checklist tests
# ---------------------------------------------------------------------------


class TestChangedocChecklist:
    """Tests for changedoc-anchored evaluation checklist items and analysis."""

    def test_changedoc_checklist_items_count(self):
        """_CHECKLIST_ITEMS_CHANGEDOC has exactly 5 items."""
        assert len(_CHECKLIST_ITEMS_CHANGEDOC) == 5

    def test_changedoc_checklist_items_content(self):
        """Changedoc items mention changedoc, rationale, and traceability."""
        joined = " ".join(_CHECKLIST_ITEMS_CHANGEDOC).lower()
        assert "changedoc" in joined
        assert "rationale" in joined
        assert "traceab" in joined  # traceability or traceable

    def test_changedoc_analysis_has_decision_audit(self):
        """_build_changedoc_checklist_analysis() mentions key steps."""
        analysis = _build_changedoc_checklist_analysis()
        assert "Decision Audit" in analysis
        assert "Ideal Decision Set" in analysis
        assert "Gap Analysis" in analysis

    def test_changedoc_analysis_differs_from_generic(self):
        """Changedoc analysis is distinct from the generic analysis."""
        generic = _build_checklist_analysis()
        changedoc = _build_changedoc_checklist_analysis()
        assert generic != changedoc
        # Generic has "Ideal Version", changedoc has "Ideal Decision Set"
        assert "Ideal Version" not in changedoc
        assert "Ideal Decision Set" not in generic

    def test_evaluation_section_uses_changedoc_items(self):
        """EvaluationSection(has_changedoc=True) produces changedoc-aware text."""
        section = EvaluationSection(
            voting_sensitivity="checklist_gated",
            has_changedoc=True,
        )
        content = section.build_content()
        # Should contain changedoc checklist items, not generic ones
        assert "Decision Completeness" in content or "changedoc" in content.lower()
        assert "Decision Audit" in content

    def test_evaluation_section_uses_generic_items(self):
        """EvaluationSection(has_changedoc=False) produces original text."""
        section = EvaluationSection(
            voting_sensitivity="checklist_gated",
            has_changedoc=False,
        )
        content = section.build_content()
        # Should contain generic items, not changedoc-specific analysis
        assert "Ideal Version" in content
        assert "Decision Audit" not in content

    def test_system_message_builder_passes_changedoc_flag(self):
        """Builder derives changedoc flag from config and produces changedoc-aware eval."""
        config = _make_config(enable_changedoc=True)
        mt = _make_message_templates()
        mt._voting_sensitivity = "checklist_gated"
        agents = {"agent_a": _make_agent()}
        builder = SystemMessageBuilder(config=config, message_templates=mt, agents=agents)
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

        # The coordination section should use changedoc analysis
        assert "Decision Audit" in msg

    def test_system_message_builder_generic_when_changedoc_off(self):
        """Builder without changedoc uses generic checklist."""
        config = _make_config(enable_changedoc=False)
        mt = _make_message_templates()
        mt._voting_sensitivity = "checklist_gated"
        agents = {"agent_a": _make_agent()}
        builder = SystemMessageBuilder(config=config, message_templates=mt, agents=agents)
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

        # The coordination section should use generic analysis
        assert "Ideal Version" in msg
        assert "Decision Audit" not in msg
