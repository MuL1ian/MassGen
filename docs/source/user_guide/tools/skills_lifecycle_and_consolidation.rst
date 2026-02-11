.. _user_guide_skills_lifecycle_and_consolidation:

Skills Lifecycle and Consolidation
==================================

This document captures:

1. What is already implemented for skills UX/runtime behavior.
2. The proposed lifecycle model for updating and consolidating skills to avoid duplication.
3. Tool exposure policy for the ``skills`` MCP wrapper.

Current Implementation (Shipped in This Branch)
================================================

Global Skills Entry in TUI
--------------------------

Skills management is available from a dedicated ``Skills`` button in the mode bar when skills are discoverable.
The analysis-only "Manage Skills" button was removed from analysis settings.

Skills Modal Organization
-------------------------

The modal now groups skills by source:

* ``builtin`` (MassGen bundled skills)
* ``project`` (``.agent/skills`` in current project)
* ``user`` (``~/.agent/skills``)
* ``previous_session`` (evolving skills discovered from logs)

The modal includes:

* Source/custom/evolving labeling for each skill.
* ``Include evolving skills from previous sessions`` toggle.
* ``Enable All``, ``Disable All``, and ``Enable Custom`` quick actions.

Runtime Behavior
----------------

* ``include_previous_session_skills`` is stored in TUI analysis state and forwarded at runtime.
* Analysis mode now supports ``skill_lifecycle_mode`` with:

  * ``create_or_update`` (default): update best matching existing skill, otherwise create.
  * ``create_new``: always create a new skill directory.
  * ``consolidate``: apply update/create and then merge overlapping project skills.

* Local skills setup now supports including previous-session evolving skills in merged local skills directories.
* Skill scanning now returns richer metadata (for example: ``source_path``, ``is_custom``, ``is_evolving``, ``origin``) and deduplicates by skill name.
* Analysis skill-creation instructions now explicitly request provenance metadata:

  * ``massgen_origin``
  * ``evolving: true``

* Post-analysis harvesting now applies lifecycle-aware upsert logic (create/update/consolidate) rather than copy-only behavior.

Skills MCP Wrapper Tool
-----------------------

A ``skills`` tool is available in the workspace tools server:

* ``skills(action="list")`` returns grouped skill metadata.
* ``skills(action="read", skill_name="...")`` reads a skill by:

  1. Trying ``openskills read`` first.
  2. Falling back to direct ``SKILL.md`` reads when needed.

This enables skill usage in local execution contexts where direct CLI invocation may not be reliable.

Remaining Gaps
==============

Without lifecycle controls, evolving skill creation can cause:

* Duplicate domain skills (for example, multiple poem-writing variants).
* Drift and fragmentation across similar skills.
* Overly large, noisy "all skills" inventories.

Lifecycle Model (Implemented + Tuning)
======================================

Default
-------

``create_or_update`` is the default behavior in analysis mode.

Behavior:

1. Discover existing skills first.
2. Match the new candidate against existing skills using semantic similarity (name + description + content).
3. If match confidence is high, update the existing skill instead of creating a new one.
4. If confidence is low, create a new skill.

Other Modes
-----------

* ``create_new``: Always create a new skill (explicit opt-in).
* ``consolidate``: Merge overlapping skills and keep canonical versions.

Consolidation Guardrails
------------------------

* Keep canonical skill IDs/directories stable where possible.
* Record provenance for merged skills (for example ``merged_from`` list).
* Prefer staged writes + explicit approval over silent direct merges.

Analysis UX
-----------

Analysis options now include a dedicated skill lifecycle selector in the popover:

* ``Create or Update (recommended)``
* ``Create New Only``
* ``Consolidate Similar Skills``

Recommended Write Policy
------------------------

For normal coordination runs, avoid broad write access by all agents to canonical skills.

Preferred policy:

1. Only final/presenter agent can propose skill changes.
2. Write to staging first.
3. Require explicit apply/approve step for canonical ``.agent/skills`` updates.

Tool Exposure Policy
====================

Requirement for the ``skills`` MCP wrapper tool:

* Expose it only when CLI-native skill workflows are not active.
* Do not expose it when backend type is ``codex``.
* Do not expose it when backend type is ``claude_code``.
* Treat this as a hard gating rule to avoid overlapping skill systems.

Rationale:

* Those backends already have native skill patterns.
* Avoid duplicated/conflicting skill invocation paths.

Implementation note:

* Backend/tool gating is now enforced in two layers:

  * MCP config excludes ``skills`` and sets a disable env flag.
  * Workspace tools server honors the env flag and does not register ``skills`` at all.

Candidate Config Surface (Proposed)
===================================

.. code-block:: yaml

   orchestrator:
     coordination:
       use_skills: true

       # Existing:
       load_previous_session_skills: false

       # Proposed:
       skill_lifecycle_mode: "create_or_update"   # create_new | create_or_update | consolidate
       enable_skill_consolidation_in_analysis: false
       skill_write_policy: "final_agent_staging"  # none | final_agent_staging | final_agent_direct
       max_previous_session_skills: 10
       previous_session_skill_sort: "recency"     # recency | relevance

Decision Checklist Before Implementation
========================================

1. Should ``create_or_update`` be the default globally, or only in analysis mode?
2. Should consolidation ever run automatically, or always require explicit toggle?
3. Should superseded skills be archived automatically or only suggested?
4. Should canonical updates require approval in all modes, or only when multiple agents are writing?
