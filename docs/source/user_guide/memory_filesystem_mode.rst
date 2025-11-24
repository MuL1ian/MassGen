Memory Filesystem Mode
======================

.. warning::
   **This feature is currently in development and experimental.** Multi-turn persistence and some advanced features may not work as expected. For production use, see :doc:`memory` for the stable persistent memory system with Qdrant.

MassGen's filesystem-based memory mode provides a simple, transparent two-tier memory system for agents. Memories are automatically saved to the filesystem, visible across agents, and can be managed using MCP tools.

.. note::

   This is different from the :doc:`memory` system. Filesystem mode is designed for transparent, file-based memory storage suitable for coordination and cross-agent visibility, while persistent memory uses vector databases for semantic retrieval across sessions.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
--------

The filesystem memory mode introduces a **two-tier hierarchy** inspired by `Letta's context hierarchy <https://docs.letta.com/guides/agents/context-hierarchy>`_:

**Short-term Memory** (Tier 1)
   Always injected into all agents' system prompts. Use for tactical observations, user preferences, and quick reference information needed frequently. These are small (<100 lines), immediately useful notes. Auto-loaded every turn.

**Long-term Memory** (Tier 2)
   Summary (name + description only) shown in system prompt, full content loaded on-demand via ``load_memory()``. Use for detailed analyses, comprehensive reports, and information that's useful but not needed every turn (>100 lines). Manual load when needed.

Key Features
~~~~~~~~~~~~

- **Filesystem Transparency**: All memories stored as Markdown files in agent workspaces
- **Cross-Agent Visibility**: All agents see all memories from all agents
- **Memory Archiving**: Memories automatically preserved when agents restart (``new_answer``)
- **Stateless Agents**: Agents see aggregated context from current state + historical archives
- **Smart Deduplication**: Historical archives show only latest version of each memory
- **Automatic Injection**: Short-term memories always in-context, no action needed
- **Two-Tier Design**: Balance between immediate availability and context window efficiency
- **MCP Tools**: Create, update, remove, and load memories programmatically

Quick Start
-----------

Enable in Configuration
~~~~~~~~~~~~~~~~~~~~~~~

Add to your YAML config:

.. code-block:: yaml

   orchestrator:
     coordination:
       enable_memory_filesystem_mode: true

   agents:
     - id: "agent_a"
       backend:
         cwd: "workspace1"  # Required for filesystem mode

Basic Usage
~~~~~~~~~~~

**Creating a short-term memory** (always in-context):

.. code-block:: python

   # Create a memory that will be auto-injected into all agents' prompts
   create_memory(
       name="user_preferences",
       description="User's coding style preferences",
       content="# Preferences\n- Uses tabs over spaces\n- Prefers functional programming\n- Avoids global state",
       tier="short_term"
   )

**Creating a long-term memory** (load on-demand):

.. code-block:: python

   # Create a reference memory that won't be auto-injected
   create_memory(
       name="project_history",
       description="Project background and architectural decisions",
       content="# Project History\n## Initial Setup (2024-01)...",
       tier="long_term"
   )

**Loading a long-term memory**:

.. code-block:: python

   # When you need access to long-term memory content
   result = load_memory(name="project_history")
   print(result["content"])

Architecture
------------

Directory Structure
~~~~~~~~~~~~~~~~~~~

Memories are stored in multiple locations for different purposes:

**Agent Workspaces** (Current work):

.. code-block:: text

   workspace1/
     memory/
       short_term/
         quick_notes.md
         user_prefs.md
       long_term/
         comprehensive_analysis.md

   workspace2/
     memory/
       short_term/
         task_context.md

**Temp Workspaces** (For cross-agent visibility):

.. code-block:: text

   .massgen/temp_workspaces/
     agent1/
       memory/
         short_term/
           quick_notes.md
     agent2/
       memory/
         short_term/
           task_context.md

**Archived Memories** (Historical persistence):

.. code-block:: text

   .massgen/sessions/session_20251123_210304/
     archived_memories/
       agent_a_answer_0/
         short_term/
           quick_notes.md
         long_term/
           skill_effectiveness.md
       agent_a_answer_1/
         short_term/
           quick_notes.md  # Updated version
       agent_b_answer_0/
         short_term/
           task_context.md
     turn_1/
       workspace/
       answer.txt

File Format
~~~~~~~~~~~

All memories **MUST** use **Markdown with YAML frontmatter**:

.. code-block:: markdown

   ---
   name: quick_notes
   description: Tactical observations from current work
   created: 2025-11-23T20:00:00
   updated: 2025-11-23T20:00:00
   ---

   ## Web Development
   - CSS variables work well for theming
   - create_directory fails on nested paths - create parent first

**Required YAML fields:**

- ``name``: Memory filename (without .md extension)
- ``description``: Brief summary for display in long-term memory lists
- ``created``: ISO timestamp when memory was created
- ``updated``: ISO timestamp of last update

**Optional fields:**

- ``tier``: "short_term" or "long_term" (inferred from directory if missing)
- ``agent_id``: Which agent created it (auto-populated by MCP tools)

System Prompt Injection
~~~~~~~~~~~~~~~~~~~~~~~~

Memory injection happens **automatically on every turn**. The orchestrator reads all memory files from all agents' workspaces and includes them in each agent's system prompt.

Injection Flow
^^^^^^^^^^^^^^

**1. Agent Creates Memory:**

When an agent calls ``create_memory()``, the Memory MCP server saves to filesystem:

.. code-block:: text

   workspace1/memory/short_term/decisions.md

**2. Orchestrator Reads All Memories (Every Turn):**

On every turn, before sending messages to agents, the orchestrator:

- Scans **all agents' workspaces**: ``workspace1/memory/``, ``workspace2/memory/``, etc.
- Reads all ``short_term/*.md`` and ``long_term/*.md`` files
- Parses YAML frontmatter + content from each file
- Groups into two lists: short-term and long-term memories

**3. Formats Into System Message:**

The orchestrator generates a memory section and appends it to each agent's system prompt:

.. code-block:: text

   system_message = base_system_message
                  + planning_guidance
                  + memory_message       ← Injected here
                  + skills_message

**4. All Agents See All Memories:**

Every agent receives the same memory section in their system prompt, containing:

- **Short-term**: Full content from ALL agents (with source labels)
- **Long-term**: Summary table from ALL agents

**Cross-Agent Visibility:**

- When Agent A creates a memory, Agent B sees it in their **next system message**
- Memories are re-read from filesystem on **every turn** (no caching)
- Updates are immediately visible to all agents
- Each memory shows which agent created it: ``[Agent: agent_a]``

System Prompt Format
^^^^^^^^^^^^^^^^^^^^

Agents see memories from two sources in their system prompts:

**1. Current Agent Memories** (from temp workspaces):

.. code-block:: text

   ### Current Agent Memories (For Comparison)

   **agent1:**
   *short_term:*
   - `quick_notes.md`
     ```
     - CSS variables work well for theming
     - create_directory needs parent to exist first
     ```

   *long_term:*
   - `comprehensive_analysis.md`: Detailed skill effectiveness analysis

   **agent2:**
   *short_term:*
   - `task_context.md`
     ```
     Key findings about current task...
     ```

**2. Archived Memories** (deduplicated historical context):

.. code-block:: text

   ### Archived Memories (Historical - Deduplicated)

   **Short-term (full content):**

   - `quick_notes.md` (from Agent A Answer 1)
     ```
     - CSS variables work well
     - Always test responsiveness
     ```

   **Long-term (summaries only):**
   - `skill_effectiveness.md`: Tracking skills and tools (from Agent A Answer 2)
   - `approach_patterns.md`: Strategy analysis (from Agent B Answer 0)

**Key Differences:**

- **Current**: Shows ALL memories from all agents (no deduplication) for comparison
- **Archived**: Shows deduplicated memories (newest version only) from previous answers
- **Short-term**: Full content always shown
- **Long-term**: Only name + description shown (load with ``load_memory()`` to see full content)

**Important Notes:**

- **Stateless agents**: Agents have no persistent identity across ``new_answer`` calls
- **Deduplication**: If same memory name appears multiple times in archives, only newest shown
- **Automatic archiving**: Memories saved to ``.massgen/sessions/{session_id}/archived_memories/`` before workspace clearing
- **Fresh reads**: Memory is always read from filesystem on every turn, never cached

MCP Tools Reference
-------------------

create_memory
~~~~~~~~~~~~~

Create a new memory in short-term or long-term storage.

.. code-block:: python

   create_memory(
       name: str,              # Unique identifier (filesystem-safe)
       description: str,       # Short summary for tables/overviews
       content: str,           # Full content (markdown supported)
       tier: str = "short_term"  # "short_term" or "long_term"
   ) -> Dict[str, Any]

**Parameters**:

- ``name``: Unique identifier for the memory. Must be filesystem-safe (no special characters).
- ``description``: Brief summary shown in tables and headers (1-2 sentences).
- ``content``: Full memory content. Markdown formatting supported.
- ``tier``: Either ``"short_term"`` (auto-inject) or ``"long_term"`` (load on-demand).

**Returns**:

.. code-block:: python

   {
       "success": True,
       "operation": "create_memory",
       "memory": {
           "name": "user_preferences",
           "description": "...",
           "content": "...",
           "tier": "short_term",
           "agent_id": "agent_a",
           "created": "2025-01-12T10:30:00Z",
           "updated": "2025-01-12T10:30:00Z"
       }
   }

**Example**:

.. code-block:: python

   result = create_memory(
       name="api_credentials",
       description="API keys and authentication details",
       content="API Key: sk-...\nEndpoint: https://api.example.com",
       tier="short_term"
   )

update_memory
~~~~~~~~~~~~~

Update existing memory content and/or description.

.. code-block:: python

   update_memory(
       name: str,                    # Name of memory to update
       content: str,                 # New content
       description: Optional[str] = None  # Optional new description
   ) -> Dict[str, Any]

**Example**:

.. code-block:: python

   update_memory(
       name="user_preferences",
       content="# Updated Preferences\n- Now uses spaces (changed from tabs)",
       description="Updated user coding preferences"
   )

remove_memory
~~~~~~~~~~~~~

Delete a memory from storage.

.. code-block:: python

   remove_memory(name: str) -> Dict[str, Any]

**Example**:

.. code-block:: python

   remove_memory(name="old_preferences")

load_memory
~~~~~~~~~~~

Load a long-term memory into context. Returns full content for injection.

.. code-block:: python

   load_memory(name: str) -> Dict[str, Any]

**Returns**:

.. code-block:: python

   {
       "success": True,
       "operation": "load_memory",
       "memory": {...},
       "content": "# Full memory content here..."
   }

**Example**:

.. code-block:: python

   result = load_memory(name="project_history")
   print(result["content"])  # Access full content

Best Practices
--------------

Choosing Between Tiers
~~~~~~~~~~~~~~~~~~~~~~~

**Use Short-term** (PREFERRED for most things) when:

- Small, tactical observations (<100 lines)
- Needed frequently across turns
- Quick reference information
- User preferences and workflow patterns
- Tool tips and gotchas discovered
- Examples: ``quick_notes.md``, ``user_prefs.md``, ``task_context.md``

**Use Long-term** (only for detailed content) when:

- Comprehensive, detailed analysis (>100 lines)
- Multi-task patterns with substantial evidence
- Detailed post-mortems and architectural decisions
- Content that would clutter auto-loaded context
- Examples: ``comprehensive_analysis.md``, ``detailed_post_mortem.md``

**Rule of thumb**: If it's small and useful every turn → short_term. If it's detailed and situationally useful → long_term. Most observations should be short-term.

Memory Organization
~~~~~~~~~~~~~~~~~~~

**Use clear, descriptive names**:

.. code-block:: python

   # Good
   create_memory(name="user_email_preferences", ...)

   # Bad
   create_memory(name="prefs", ...)

**Keep short-term memories concise**:

.. code-block:: python

   # Good - focused and brief
   create_memory(
       name="user_style",
       content="- Tabs over spaces\n- Functional style\n- No globals",
       tier="short_term"
   )

   # Bad - too verbose for short-term
   create_memory(
       name="user_style",
       content="[100 lines of detailed style guide]",
       tier="short_term"  # Should be long_term!
   )

**Use meaningful descriptions**:

.. code-block:: python

   # Good
   description="User's Python coding style preferences and conventions"

   # Bad
   description="Preferences"

Cross-Agent Coordination
~~~~~~~~~~~~~~~~~~~~~~~~

All agents see all memories with source attribution:

.. code-block:: python

   # Agent A creates a memory
   create_memory(
       name="research_findings",
       description="Literature review on neural architectures",
       content="[Research notes]",
       tier="long_term"
   )

   # Agent B sees it in their system prompt and can load it
   result = load_memory(name="research_findings")
   # Result includes agent_id to track origin

**Tips**:

- Use descriptive names to help other agents find relevant memories
- Include agent context in descriptions when appropriate
- Respect read/write patterns (each agent owns their memories)

Memory Lifecycle Management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Clean up outdated memories**:

.. code-block:: python

   # When a memory is no longer needed
   remove_memory(name="temporary_analysis")

**Update instead of creating duplicates**:

.. code-block:: python

   # Check if memory exists, then update
   try:
       result = load_memory(name="user_prefs")
       update_memory(name="user_prefs", content="[new content]")
   except:
       create_memory(name="user_prefs", ...)

Context Window Management
~~~~~~~~~~~~~~~~~~~~~~~~~

**Monitor short-term usage**:

Short-term memories consume context window tokens. Recommended limits:

- **Individual memory size**: <1000 tokens
- **Total short-term memories**: <10 memories
- **Total short-term tokens**: <10,000 tokens

**Promote/demote as needed**:

.. code-block:: python

   # If short-term gets too large, move less critical items to long-term
   # (Manual process - load content, delete from short, recreate in long)

   result = load_memory(name="detailed_notes")
   content = result["content"]
   remove_memory(name="detailed_notes")
   create_memory(
       name="detailed_notes",
       description="Archived detailed notes",
       content=content,
       tier="long_term"
   )

Use Cases
---------

Multi-Turn Conversations
~~~~~~~~~~~~~~~~~~~~~~~~

Persist context across conversation turns:

.. code-block:: python

   # Turn 1: Agent A saves findings
   create_memory(
       name="analysis_turn1",
       description="Initial codebase analysis findings",
       content="# Findings\n- Found 3 API endpoints\n- Auth uses JWT",
       tier="long_term"
   )

   # Turn 2: Agent B references previous work
   prev_analysis = load_memory(name="analysis_turn1")
   # Continue from where Agent A left off

User Preferences Tracking
~~~~~~~~~~~~~~~~~~~~~~~~~~

Store and maintain user preferences:

.. code-block:: python

   create_memory(
       name="user_preferences",
       description="User's project preferences and constraints",
       content="""
       # User Preferences
       - Language: Python 3.11+
       - Framework: FastAPI
       - Testing: pytest with coverage >80%
       - Documentation: Google-style docstrings
       """,
       tier="short_term"  # Always available
   )

Project Context Management
~~~~~~~~~~~~~~~~~~~~~~~~~~

Maintain project background and decisions:

.. code-block:: python

   create_memory(
       name="project_context",
       description="Project overview and architectural decisions",
       content="""
       # Project Context

       ## Overview
       Building a multi-agent orchestration framework for AI coordination.

       ## Key Decisions
       - Using MCP for tool integration
       - Filesystem-first for transparency
       - Two-tier memory hierarchy

       ## Current Sprint
       - Implementing memory filesystem mode
       - Target: v0.2.0 release
       """,
       tier="long_term"  # Load when needed
   )

Troubleshooting
---------------

Memories Not Appearing
~~~~~~~~~~~~~~~~~~~~~~

**Check configuration**:

.. code-block:: yaml

   orchestrator:
     coordination:
       enable_memory_filesystem_mode: true  # Must be true

   agents:
     - id: "agent_a"
       backend:
         cwd: "workspace1"  # Must have workspace path

**Verify workspace path**:

.. code-block:: bash

   # Check if memory directory exists
   ls workspace1/memory/

   # Should see: short_term/ long_term/

**Check logs**:

.. code-block:: bash

   # Look for memory MCP injection logs
   grep "Injecting memory tools" logs/massgen.log
   grep "enable_memory_filesystem_mode" logs/massgen.log

Memory Not Loading
~~~~~~~~~~~~~~~~~~

**Verify memory exists**:

.. code-block:: bash

   # Check filesystem
   ls workspace1/memory/short_term/
   ls workspace1/memory/long_term/

   # Read memory file
   cat workspace1/memory/long_term/project_history.md

**Check frontmatter format**:

Memory files must start with ``---`` and have valid YAML:

.. code-block:: markdown

   ---
   name: my_memory
   description: My memory description
   tier: long_term
   agent_id: agent_a
   created: 2025-01-12T10:30:00Z
   updated: 2025-01-12T10:30:00Z
   ---

   Content here...

Performance Considerations
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Short-term memory adds to every request**:

- Each short-term memory adds ~100-1000 tokens per agent
- With 3 agents × 5 short-term memories = potential 1,500-15,000 tokens
- Monitor context usage and move to long-term if needed

**Long-term memory loads on-demand**:

- Only costs tokens when explicitly loaded
- Can have unlimited long-term memories
- Load time is negligible (filesystem read)

Comparison with Other Memory Systems
-------------------------------------

Filesystem Mode vs. Persistent Memory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Feature
     - Filesystem Mode
     - Persistent Memory (Qdrant)
   * - Storage
     - Markdown files in workspace
     - Vector database (Qdrant)
   * - Retrieval
     - Manual load or auto-inject
     - Semantic search
   * - Persistence
     - Per-session (workspace)
     - Cross-session (database)
   * - Setup
     - Config flag only
     - Requires Qdrant server
   * - Use Case
     - Transparent, file-based coordination
     - Long-term semantic memory
   * - Cross-Agent
     - Full visibility (same orchestration)
     - Shared collection
   * - Scale
     - Small-medium (<100 memories)
     - Large (unlimited)

**When to use each**:

- **Filesystem Mode**: Current session coordination, transparent memory, file-based workflows
- **Persistent Memory**: Multi-session learning, semantic retrieval, large knowledge bases

Filesystem Mode vs. Skills System
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Feature
     - Filesystem Mode
     - Skills System
   * - Purpose
     - Runtime memory/context
     - Pre-defined knowledge/tools
   * - Modification
     - Dynamic (create/update/delete)
     - Static (loaded at start)
   * - Format
     - Markdown with frontmatter
     - Markdown with frontmatter
   * - Injection
     - Two-tier (auto + manual)
     - Auto-inject or load
   * - Agent Creation
     - Yes (via MCP tools)
     - No (external files)

**Complementary use**:

- Skills: Pre-existing knowledge (how to use tools, workflows)
- Memory: Runtime discoveries (user prefs, findings, decisions)

Memory Archiving & Persistence
--------------------------------

When agents call ``new_answer`` to restart with a fresh workspace, their memories are automatically archived.

How It Works
~~~~~~~~~~~~

1. **Before clearing workspace**: Memories copied to ``.massgen/sessions/{session_id}/archived_memories/{agent_id}_answer_{n}/``
2. **Workspace cleared**: Agent gets fresh workspace
3. **Memories preserved**: Historical archives persist permanently in sessions/ directory
4. **System prompt updated**: Next agent sees archived memories (deduplicated) + current memories

Deduplication Strategy
~~~~~~~~~~~~~~~~~~~~~~

**Current Agent Memories** (from temp workspaces):
   - Shows ALL memories from ALL agents
   - NO deduplication (need all for comparison)
   - Used for evaluating competing answers

**Archived Memories** (from sessions/):
   - Shows deduplicated historical memories
   - For duplicate names: keeps only newest version (by file timestamp)
   - Reduces noise from repeated memory names across answers

**Example**:

.. code-block:: text

   Archives before deduplication:
   - agent_a_answer_0/quick_notes.md (timestamp: 100)
   - agent_a_answer_1/quick_notes.md (timestamp: 200) ← SHOWN
   - agent_b_answer_0/quick_notes.md (timestamp: 150)

   System prompt shows only: agent_a_answer_1/quick_notes.md (most recent)

Stateless Architecture
~~~~~~~~~~~~~~~~~~~~~~~

Agents are **stateless** - they have no persistent identity across ``new_answer`` calls. Each agent sees:

1. All current memories from all agents' workspaces (for comparing approaches)
2. Deduplicated historical memories from archives (for context)

This design ensures agents see complete context without confusion about "my previous work" vs "other agents' work".

Known Limitations
-----------------

This feature is experimental. Key limitations:

1. **No Semantic Search**: Retrieval by exact name only. No similarity search or automatic relevance ranking.

2. **Token Management**: No automatic enforcement of memory size limits. Keep short-term memories small (<100 lines).

3. **Archive Growth**: Archives accumulate over time. Consider periodic cleanup of old session directories.

4. **No Conflict Resolution**: If multiple agents update same memory name, deduplication keeps newest by timestamp (last write wins).

Related Documentation
---------------------

- :doc:`memory` - Persistent memory with Qdrant (different system)
- :doc:`agent_task_planning` - Task planning MCP (similar filesystem pattern)
- :doc:`skills` - Skills system (similar injection pattern)
- `Letta Context Hierarchy <https://docs.letta.com/guides/agents/context-hierarchy>`_ - Inspiration for tier design
