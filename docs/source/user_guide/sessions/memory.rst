Memory and Context Management
==============================

MassGen's memory system enables agents to maintain knowledge across conversations, handle long context windows gracefully, and share insights across multi-turn sessions. The system automatically manages context compression, semantic memory retrieval, and cross-agent knowledge sharing.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
--------

The memory system consists of two complementary components:

**ConversationMemory (Short-term)**
   Fast in-memory storage for recent messages. Maintains verbatim conversation history for the current context window.

**PersistentMemory (Long-term)**
   Vector database storage (via `mem0 <https://mem0.ai>`_) with semantic search. Extracts and stores key facts that persist across sessions and can be retrieved when relevant.

Key Features
~~~~~~~~~~~~

- **Automatic Context Compression**: When approaching token limits, old messages are removed while remaining accessible via semantic search
- **Semantic Retrieval**: Retrieve relevant facts from past conversations based on current context
- **Cross-Agent Memory Sharing**: Agents access previous winning agents' knowledge from past turns
- **Session Management**: Memories isolated by session for clean separation of different tasks
- **Turn-Aware Filtering**: Prevents temporal leakage by filtering memories by turn number

Quick Start
-----------

Prerequisites
~~~~~~~~~~~~~

For multi-agent setups, start the Qdrant vector database server:

.. code-block:: bash

   # Start Qdrant (required for persistent memory)
   docker-compose -f docker-compose.qdrant.yml up -d

   # Verify it's running
   curl http://localhost:6333/health

   # (Optional) View Qdrant dashboard
   open http://localhost:6333/dashboard

Basic Configuration
~~~~~~~~~~~~~~~~~~~

Add memory configuration to your YAML config:

.. code-block:: yaml

   memory:
     enabled: true

     conversation_memory:
       enabled: true  # Short-term tracking

     persistent_memory:
       enabled: true  # Long-term storage

       # LLM for fact extraction (uses mem0's native providers)
       llm:
         provider: "openai"
         model: "gpt-4.1-nano-2025-04-14"

       # Embeddings for vector search
       embedding:
         provider: "openai"
         model: "text-embedding-3-small"

       # Qdrant configuration
       qdrant:
         mode: "server"  # Use "local" for single-agent only
         host: "localhost"
         port: 6333

     # Context compression settings
     compression:
       trigger_threshold: 0.75  # Compress at 75% usage
       target_ratio: 0.40       # Keep 40% after compression

     # Retrieval settings
     retrieval:
       limit: 5              # Facts to retrieve
       exclude_recent: true  # Only retrieve after compression

     # Recording settings (v0.1.9+)
     recording:
       record_all_tool_calls: false  # Set true to capture ALL MCP tools
       record_reasoning: false       # Set true to capture thinking separately

Run with Memory
~~~~~~~~~~~~~~~

.. code-block:: bash

   # Interactive mode with memory
   massgen --config @examples/memory/gpt5mini_gemini_context_window_management.yaml

   # Single question with memory
   massgen \
     --config @examples/memory/gpt5mini_gemini_context_window_management.yaml \
     "Analyze the MassGen codebase and create an architecture document"

How It Works
------------

Custom Fact Extraction
~~~~~~~~~~~~~~~~~~~~~~~

MassGen uses custom prompts designed to extract high-quality, domain-focused memories. The goal is to filter facts to be:

**Self-Contained and Specific**:
   Facts should be understandable 6 months later without the original conversation

**Focused on Domain Knowledge**:
   - ✅ Concrete data points with context ("OpenAI revenue reached $12B annualized")
   - ✅ Insights with explanations ("Narrative depth valued in creative writing because...")
   - ✅ Capabilities with use cases ("MassGen v0.1.1 supports Python tools via YAML")
   - ✅ Domain expertise with details ("Binet's formula uses golden ratio phi=(1+√5)/2")
   - ✅ Specific recommendations with WHAT, WHEN, WHY

**Tool Usage Patterns** (v0.1.9+):
   - ✅ Tool sequences that work ("For code analysis, directory_tree → read_file → grep provides systematic understanding")
   - ✅ Problem-solving approaches ("Breaking large tasks into focused searches yields better results than broad queries")
   - ✅ What worked/failed with reasoning ("Sequential exploration prevents getting lost in implementation details")

**Excluded for Quality**:
   - ❌ Agent comparisons ("Agent 1's response is better")
   - ❌ Voting details ("The reason for voting...")
   - ❌ Meta-instructions ("Response should start with...")
   - ❌ Generic advice without specifics ("Providing templates improves docs")
   - ❌ Usage statistics without insight ("Used grep 5 times")

**Implementation**: ``massgen/memory/_fact_extraction_prompts.py::MASSGEN_UNIVERSAL_FACT_EXTRACTION_PROMPT``

Memory Flow
~~~~~~~~~~~

**Every Turn**:

1. User message added to conversation_memory (verbatim)
2. Agent responds with reasoning and answer
3. Response recorded to:

   - **ConversationMemory**: Full message for immediate context
   - **PersistentMemory**: mem0's LLM extracts key facts and stores in vector DB

4. Context window checked:

   - **Below threshold**: Continue normally
   - **Above threshold**: Compress old messages, enable retrieval

**What Gets Recorded** (Default):

.. code-block:: text

   ✅ User messages
   ✅ Final answer text (accumulated from content chunks)
   ✅ Workflow tools (new_answer, vote) with full arguments

   ❌ System messages (orchestrator prompts - filtered out)
   ❌ MCP tool calls (unless record_all_tool_calls: true)
   ❌ Reasoning chunks (unless record_reasoning: true)

**Configurable Recording** (v0.1.9+):

You can now control what gets recorded to memory via YAML configuration:

.. code-block:: yaml

   memory:
     recording:
       record_all_tool_calls: false  # Set to true to capture ALL MCP tools
       record_reasoning: false       # Set to true to capture thinking separately

See :ref:`recording-configuration` below for details.

Context Compression
~~~~~~~~~~~~~~~~~~~

MassGen uses **reactive compression** for context window management. This is due to
a fundamental limitation of most LLM APIs.

**Why Reactive?**

Most LLM providers (OpenAI, Anthropic, Google) only report token usage *after* a
request completes. There is no mid-stream token counting or pre-flight validation API.
This means MassGen cannot proactively prevent context overflow—it can only react when
the provider returns a context length error.

**How It Works**

1. MassGen sends the conversation to the LLM
2. If the context is too long, the provider returns an error
3. MassGen catches the error and generates a summary of the work done so far
4. The summarized conversation is retried automatically (single retry to prevent loops)

**After compression**, the message structure looks like:

.. code-block:: text

   Before Error:
   [system] → [user 1] → [assistant 1] → ... → [user 20] → [assistant 20] ← ERROR

   After Compression:
   [system] → [user request] → [summary as assistant message]
   ↑           ↑                ↑
   System      User's original  Summary of ALL work done so far
   preserved   request          (most recent context - model continues from here)

**Key Design: User → Summary Ordering**

The summary is placed *after* the user message as an assistant message. This ordering
is critical for preventing redundant work:

- The model sees its own summary as the most recent context
- It naturally continues from the summary rather than starting fresh
- File reads, analysis, and other completed work are preserved in the summary

**What Gets Summarized**

The compression system captures everything in the streaming buffer, including:

- Tool calls and their results (file reads, directory listings, etc.)
- Reasoning and analysis performed
- Partial answers and work in progress
- Any content that was streaming when the context limit was hit

This ensures the model doesn't re-read files or redo analysis after compression.

**Configuration**

.. code-block:: yaml

   coordination:
     compression_target_ratio: 0.20  # Preserve 20% of messages, summarize 80%

The ``compression_target_ratio`` controls how aggressively to compress when the
context limit is exceeded:

- **0.20** (default): Preserve ~20% of messages verbatim, summarize the rest
- **0.30**: More conservative, preserve ~30% of messages
- **0.10**: More aggressive, preserve only ~10% of messages

.. note::

   Compression is **reactive** - it only triggers when the provider returns a context
   length error. MassGen cannot predict when context will exceed the limit because
   token counts are only available after each LLM call completes.

**Best Practices**

- For very long tasks, consider breaking into multiple sessions
- Use ``clear_history=True`` when starting unrelated topics
- Critical information should be in recent messages or system prompt
- Lower ``compression_target_ratio`` for more aggressive compression (preserves less)

**Future Improvements**

Some providers may add better token tracking in the future:

- Pre-flight token counting APIs
- Streaming token usage updates
- Local models with tiktoken-based estimation

Memory Retrieval
~~~~~~~~~~~~~~~~

Retrieval happens when:

- ✅ **After compression**: Retrieve facts from compressed messages
- ✅ **On restart/reset**: Restore recent context
- ❌ **Before compression**: Skip (all context already in conversation_memory)

Retrieval process:

1. **Search own agent's memories** (all turns, current session)
2. **Search previous winners' memories** (filtered by turn - see below)
3. **Format and inject** as system message before processing

.. code-block:: text

   Retrieved memories injected as:

   ┌─────────────────────────────────────┐
   │ Relevant memories:                   │
   │ • User asked about backend system    │
   │ • Agent analyzed 5 backend files     │
   │ • [From agent_b Turn 1] Explained    │
   │   stateful vs stateless backends     │
   └─────────────────────────────────────┘
   ↓
   [user msg 15] → [agent response 15] → ...

Use Cases
---------

Scenario 1: Long Analysis Tasks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Use case**: Analyzing a large codebase that requires reading 50+ files

**Without memory**:
   Context fills up after ~15 files, agent loses track of earlier analysis

**With memory**:
   - Agent reads files 1-15, context compresses
   - Files 16-30: Agent retrieves relevant facts from 1-15
   - Maintains complete understanding throughout analysis

**Configuration**:

.. code-block:: yaml

   memory:
     enabled: true
     compression:
       trigger_threshold: 0.75  # Compress when 75% full
       target_ratio: 0.40        # Keep 40% of recent context

**Example**:

.. code-block:: bash

   massgen --config @examples/memory/gpt5mini_gemini_context_window_management.yaml \
     "Analyze the entire MassGen codebase and create comprehensive documentation"

Scenario 2: Multi-Turn Sessions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Use case**: Interactive development across multiple sessions

**Without memory**:
   Each turn starts fresh, agents forget previous turns' insights

**With memory**:
   - Turn 1: Agent A wins, explains backend architecture
   - Turn 2: Agent B retrieves Agent A's Turn 1 insights
   - Turn 3: Agent A sees both own past work + Agent B's Turn 2 insights

**How winner memory sharing works**:

.. code-block:: text

   Turn 1: agent_a wins → Memories tagged {"agent_id": "agent_a", "turn": 1}
   Turn 2:
     agent_b retrieves:
       ✅ Own memories (all turns)
       ✅ agent_a's Turn 1 memories (previous winner)
       ❌ agent_a's Turn 2 memories (not yet complete)

   Turn 3:
     agent_a retrieves:
       ✅ Own memories (Turns 1, 2)
       ✅ agent_b's Turn 2 memories (previous winner)

**Configuration**:

Session ID automatically generated for interactive mode: ``session_20251028_143000``

Memories are isolated per session unless you specify a custom session name.

Scenario 3: Orchestrator Restarts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Use case**: Agent needs to restart due to errors or new answers from other agents

**Without memory**:
   Partial work lost, agent starts from scratch

**With memory**:
   - Before restart: Current conversation recorded to persistent_memory
   - On restart: Relevant facts retrieved to restore context
   - Agent continues seamlessly with knowledge of prior attempts

**Example flow**:

.. code-block:: text

   Agent A working on task...
   📝 Read 5 files, analyzed architecture
   🔄 Other agent submits better answer → Restart triggered
   💾 Recording 10 messages before reset
   🔄 Retrieving memories after reset...
   💭 Retrieved: "Analyzed backend/base.py", "Found adapter pattern", ...
   ✅ Agent continues with restored context

Configuration Reference
-----------------------

Complete Configuration
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   memory:
     # Global enable/disable
     enabled: true

     # Short-term conversation tracking
     conversation_memory:
       enabled: true

     # Long-term knowledge storage
     persistent_memory:
       enabled: true
       on_disk: true  # Persist across restarts

       # Session isolation (optional)
       # session_name: "my_project_analysis"  # Specific session
       # session_name: null                   # Cross-session memory

       # LLM for fact extraction
       llm:
         provider: "openai"
         model: "gpt-4.1-nano-2025-04-14"  # Fast, cheap for memory ops
         # api_key: "sk-..."  # Optional - reads from OPENAI_API_KEY env var

       # Embeddings for vector search
       embedding:
         provider: "openai"
         model: "text-embedding-3-small"
         # api_key: "sk-..."  # Optional - reads from OPENAI_API_KEY env var

       # Vector store (Qdrant)
       qdrant:
         mode: "server"      # "server" or "local"
         host: "localhost"   # Server mode only
         port: 6333          # Server mode only
         # path: ".massgen/qdrant"  # Local mode only

     # Context window compression
     compression:
       trigger_threshold: 0.75  # Compress at 75% context usage
       target_ratio: 0.40       # Target 40% after compression

     # Memory retrieval
     retrieval:
       limit: 5              # Max facts per agent
       exclude_recent: true  # Skip retrieval before compression

     # Memory recording (v0.1.9+)
     recording:
       record_all_tool_calls: false  # Record ALL MCP tools (not just workflow)
       record_reasoning: false       # Record reasoning chunks separately

Configuration Options
~~~~~~~~~~~~~~~~~~~~~

Memory Toggle
^^^^^^^^^^^^^

.. code-block:: yaml

   memory:
     enabled: false  # Disable entire memory system

Conversation Memory
^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

   conversation_memory:
     enabled: true  # Almost always true - needed for context management

Persistent Memory
^^^^^^^^^^^^^^^^^

**LLM Configuration** (for fact extraction):

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Provider
     - Configuration
   * - OpenAI
     - ``provider: "openai"``, ``model: "gpt-4.1-nano-2025-04-14"`` or ``"gpt-4o-mini"``
   * - Anthropic
     - ``provider: "anthropic"``, ``model: "claude-3-5-haiku-20241022"``
   * - Groq
     - ``provider: "groq"``, ``model: "llama-3.1-8b-instant"``

**Embedding Configuration** (for vector search):

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Provider
     - Configuration
   * - OpenAI
     - ``provider: "openai"``, ``model: "text-embedding-3-small"`` (1536 dims)
   * - Together
     - ``provider: "together"``, ``model: "togethercomputer/m2-bert-80M-8k-retrieval"``
   * - Azure OpenAI
     - ``provider: "azure_openai"``, ``model: "text-embedding-ada-002"``

**Qdrant Configuration**:

.. code-block:: yaml

   # Server mode (RECOMMENDED for multi-agent)
   qdrant:
     mode: "server"
     host: "localhost"
     port: 6333

   # Local mode (single agent only)
   qdrant:
     mode: "local"
     path: ".massgen/qdrant"

.. warning::
   Local file-based Qdrant does NOT support concurrent access. For multi-agent setups, always use server mode.

Session Management
^^^^^^^^^^^^^^^^^^

**Automatic sessions**:

All sessions are automatically created and tracked in the registry:

- **Interactive mode**: ``session_20251028_143000`` (shared across all turns in that session)
- **Single question**: ``session_20251028_143001`` (each run gets its own tracked session)

**Custom sessions**:

.. code-block:: yaml

   persistent_memory:
     session_name: "my_project_analysis"  # Continue specific session

**Cross-session memory** (search across all sessions):

.. code-block:: yaml

   persistent_memory:
     session_name: null  # or omit the field

Loading Previous Sessions
^^^^^^^^^^^^^^^^^^^^^^^^^^

MassGen automatically tracks all memory sessions in a registry (``~/.massgen/sessions.json``). You can list and load previous sessions to continue conversations with their memory context intact.

**List available sessions**:

.. code-block:: bash

   massgen --list-sessions

Example output:

.. code-block:: text

   Available Memory Sessions:
   ============================================================

   Session ID: session_20251028_143000
     Status:  completed
     Started: 2025-10-28 14:30:00
     Model:   gpt-4o-mini
     Config:  memory_config.yaml

   Session ID: session_20251027_091500
     Status:  completed
     Started: 2025-10-27 09:15:00
     Model:   gpt-4o
     Description: Codebase analysis project
     Config:  research_config.yaml

   ============================================================
   To load a session, use: massgen --session-id <SESSION_ID> "Your question"

**Load session via CLI**:

.. code-block:: bash

   # Continue previous session
   massgen --session-id session_20251028_143000 "What did we discuss about the backend?"

   # Interactive mode with previous session
   massgen --session-id session_20251028_143000 --config my_config.yaml

**Load session via YAML config**:

.. code-block:: yaml

   # Add to your config file
   session_id: "session_20251028_143000"

   memory:
     enabled: true
     persistent_memory:
       enabled: true
       # ... rest of memory config

**Priority order**: CLI argument (``--session-id``) > YAML config (``session_id:``) > Auto-generated

**Benefits**:

- Continue conversations across multiple CLI runs
- Access memory from previous analysis sessions
- Build on previous agents' knowledge without re-analysis
- Maintain context for long-running research projects

**Note**: All sessions (both interactive and single-question modes) are tracked in the registry and can be continued later

Compression Settings
^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

   compression:
     trigger_threshold: 0.75  # Not reliably enforceable - see note below
     target_ratio: 0.20        # Preserve 20% of messages after compression

.. note::

   **Reactive Compression Limitation**: The ``trigger_threshold`` cannot be proactively
   enforced because token counts are only available after each LLM call completes. MassGen
   uses reactive compression—catching context length errors from the provider and
   summarizing automatically. Only ``target_ratio`` is reliably enforced.

Example configurations:

- **Aggressive compression**: ``target_ratio: 0.10`` (preserve only 10%)
- **Moderate** (default): ``target_ratio: 0.20`` (preserve 20%)
- **Conservative**: ``target_ratio: 0.40`` (preserve 40%)

Retrieval Settings
^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

   retrieval:
     limit: 5              # Max facts per agent (default: 5)
     exclude_recent: true  # Smart retrieval (default: true)

- **More context**: Increase ``limit`` to 10-20 (uses more tokens)
- **Always retrieve**: Set ``exclude_recent: false`` (may duplicate recent context)

.. _recording-configuration:

Recording Settings (v0.1.9+)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**New in v0.1.9**: Control what gets recorded to memory for better observability and learning.

.. code-block:: yaml

   memory:
     recording:
       record_all_tool_calls: false  # Record ALL MCP tools (not just workflow)
       record_reasoning: false       # Record reasoning chunks separately

**record_all_tool_calls** (default: ``false``):

:``false``: Only workflow tools (``new_answer``, ``vote``) are recorded
:``true``: ALL MCP tools are captured (``list_directory``, ``read_file``, ``write_file``, etc.)

**When to enable**:
- Learning tool usage patterns across sessions
- Debugging which tools agents use most
- Understanding tool sequences (e.g., "directory_tree → read_file → grep")
- Maximum observability during development

**Example with ALL tools enabled**:

.. code-block:: text

   [Tool Usage]
   [Tool Call: mcp__filesystem__directory_tree]
   Arguments: {"path": "/Users/.../massgen"}
   Result: [directory structure with 50+ files...]

   [Tool Call: mcp__filesystem__read_text_file]
   Arguments: {"path": ".../orchestrator.py"}
   Result: [full file contents...]

   [Tool Call: new_answer]
   Arguments: {"content": "Architecture analysis complete..."}
   Result: Answer submitted

**record_reasoning** (default: ``false``):

:``false``: Reasoning mixed with final answer in main response
:``true``: Reasoning chunks saved separately with ``[Reasoning]`` prefix

**When to enable**:
- Debugging agent decision-making
- Learning problem-solving approaches
- Capturing strategic thinking separate from final output

**Example with reasoning enabled**:

.. code-block:: text

   [Reasoning]
   I should analyze the file structure first before diving into specific implementations.
   This will help me build a mental model of the codebase organization.

   [Reasoning Summary]
   Decided to use directory_tree followed by selective file reads for systematic analysis.

   Final answer: The codebase follows a modular architecture...

**Performance Impact**:

- **With both disabled** (default): ~1-2 KB per recording, concise memory
- **With both enabled**: ~10-50 KB per recording, maximum detail
- **mem0 extraction cost**: Same LLM calls regardless (extracts from whatever is sent)

**Recommendation**:
- **Development**: Enable both for debugging
- **Production**: Keep disabled for concise, focused memory

Monitoring and Debugging
-------------------------

Context Window Logs
~~~~~~~~~~~~~~~~~~~

MassGen uses **buffer-based context tracking** to accurately monitor token usage. The conversation buffer captures ALL content including tool calls, tool results, injections, and reasoning—not just turn-level messages.

**Token Tracking Priority**:

1. **Official API counts** (at stream end): Most accurate for cost/pricing
2. **Buffer estimation** (fallback): Captures all content provided by API

Monitor context usage in real-time:

.. code-block:: text

   # Using official API token counts (most accurate)
   📊 Context Window (Turn 5): 45,000 / 128,000 tokens (35%) [API actual]

   # Using buffer estimation (fallback, assuming API provides all content)
   📊 Context Buffer (Turn 5): 45,000 / 128,000 tokens (35%) [buffer]

When compression triggers:

.. code-block:: text

   ⚠️  Context Buffer (Turn 11): 96,000 / 128,000 tokens (75%) [buffer] - Approaching limit!
   🔄 Attempting compression (96,000 → 51,200 tokens)
   📦 Context compressed: Removed 15 messages (44,800 tokens).
      Kept 8 recent messages (51,200 tokens).

**Why Buffer-Based Tracking?**

The conversation buffer is the true source of context sent to agents. Unlike message-based tracking, it includes:

- Tool calls and their arguments
- Tool results (can be very large)
- Injections from other agents
- Pending content not yet flushed
- Reasoning/thinking content (may not be available, depending on the API)

This provides accurate context usage even mid-stream, before official API counts are available.

Memory Operations
~~~~~~~~~~~~~~~~~

**Recording**:

.. code-block:: text

   🔍 [_mem0_add] Recording to mem0 (agent=agent_a, session=session_123, turn=1)
      messages: 2 message(s)
      assistant: [Reasoning] I analyzed the backend files...
      assistant: The backend system consists of...
   ✅ mem0 extracted 5 fact(s), 2 relation(s)

**Retrieval**:

.. code-block:: text

   🔄 Retrieving memories after reset for agent_a (restoring recent context + 1 winner(s))...
   🔍 [retrieve] Searching memories (agent=agent_a, limit=5, winners=1)
      Previous winners: [{'agent_id': 'agent_b', 'turn': 1}]
      🔎 Searching own memories (agent_a)...
         → Found 3 memory/memories
      🔎 Searching 1 previous winner(s)...
         → Searching agent_b (turn 1)...
            Found 2 memory/memories
   ✅ Total: 5 memories retrieved
      [1] User asked about MassGen architecture
      [2] [From agent_b Turn 1] Explained the adapter pattern

Debug Files (v0.1.9+)
~~~~~~~~~~~~~~~~~~~~~

**New in v0.1.9**: Memory debug mode saves complete message→fact mappings when using the ``--debug`` flag.

**Enable debug mode**:

.. code-block:: bash

   massgen --debug --config your_config.yaml "Your question"

**Debug files saved to**:

.. code-block:: text

   .massgen/massgen_logs/log_{timestamp}/attempt_{N}/memory_debug/
   └── {agent_id}/
       ├── turn_1_20251029_200335.json
       ├── turn_2_20251029_200438.json
       └── turn_3_20251029_200557.json

**File structure**:

.. code-block:: json

   {
     "timestamp": "2025-10-29T20:03:35.123456",
     "agent_id": "test_agent",
     "session_id": "temp_20251029_200122",
     "turn": 1,
     "metadata": {
       "tools_used": ["mcp__filesystem__directory_tree", "read_text_file"],
       "has_tools": true,
       "message_count": 1
     },
     "messages_sent": [
       {
         "role": "assistant",
         "content": "[Tool Usage]\n[Tool Call: directory_tree]\nArguments: {...}\nResult: ..."
       }
     ],
     "facts_extracted": [
       {
         "id": "abc123",
         "memory": "For analyzing Python codebases, directory_tree → read_file sequence...",
         "event": "ADD"
       }
     ],
     "extraction_count": 10
   }

**Use cases**:

- **Verify tool capture**: Check if MCP tools appear in ``messages_sent``
- **Tune prompts**: Compare input vs. extracted facts to improve extraction quality
- **Debug 0 facts**: See what content was sent when extraction fails
- **Monitor quality**: Review if facts are actionable or generic

Testing Memory Setup
~~~~~~~~~~~~~~~~~~~~

Verify your memory configuration:

.. code-block:: bash

   # Run test script
   uv run python scripts/test_memory_setup.py

Expected output:

.. code-block:: text

   🧪 MEMORY SYSTEM TEST SUITE

   ============================================================
   TEST 1: Environment Variables
   ============================================================
   ✅ OPENAI_API_KEY found (starts with: sk-proj...)

   ============================================================
   TEST 2: OpenAI Embedding API
   ============================================================
   ✅ Embedding successful!
      Vector dimensions: 1536

   ============================================================
   TEST 3: mem0 LLM API (gpt-4.1-nano)
   ============================================================
   ✅ LLM call successful!

   ============================================================
   TEST 4: Qdrant Connection
   ============================================================
   ✅ Qdrant server connected!

   ============================================================
   TEST 5: Full Memory Integration
   ============================================================
   ✅ PersistentMemory created!
   ✅ Messages recorded!

Advanced Usage
--------------

Per-Agent Memory Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Override memory settings for specific agents:

.. code-block:: yaml

   memory:
     # Global defaults
     retrieval:
       limit: 5

   agents:
     - id: "researcher"
       memory:
         retrieval:
           limit: 20  # This agent gets more context

     - id: "writer"
       memory:
         retrieval:
           limit: 3   # This agent gets less

Different Embedding Providers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Using Together AI** (cost-effective):

.. code-block:: yaml

   persistent_memory:
     embedding:
       provider: "together"
       model: "togethercomputer/m2-bert-80M-8k-retrieval"
       # Reads TOGETHER_API_KEY from environment

**Using Azure OpenAI**:

.. code-block:: yaml

   persistent_memory:
     llm:
       provider: "azure_openai"
       model: "gpt-4o-mini"
       api_key: "${AZURE_OPENAI_API_KEY}"
     embedding:
       provider: "azure_openai"
       model: "text-embedding-ada-002"

Session Continuation
~~~~~~~~~~~~~~~~~~~~

**Continue a previous session**:

.. code-block:: yaml

   persistent_memory:
     session_name: "codebase_analysis_oct2025"

All agents will access memories from this session across multiple CLI runs.

**Cross-session knowledge**:

.. code-block:: yaml

   persistent_memory:
     session_name: null  # Search across ALL sessions

Useful for:
- Building knowledge base across projects
- Learning from past conversations
- Avoiding repeating analysis

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Qdrant Connection Error**

.. code-block:: text

   ⚠️  Failed to create shared Qdrant client: Storage folder .massgen/qdrant
   is already accessed by another instance

**Solution**:

1. Check if Qdrant server is running:

   .. code-block:: bash

      docker-compose -f docker-compose.qdrant.yml ps

2. Remove stale lock files:

   .. code-block:: bash

      ./scripts/cleanup_qdrant_lock.sh
      # Or manually:
      rm .massgen/qdrant/.lock

3. Use server mode for multi-agent:

   .. code-block:: yaml

      qdrant:
        mode: "server"

**API Key Not Found**

.. code-block:: text

   ⚠️  OPENAI_API_KEY not found in environment - embedding will fail!

**Solution**:

Create ``.env`` file in project root:

.. code-block:: bash

   OPENAI_API_KEY=sk-proj-...
   ANTHROPIC_API_KEY=sk-ant-...  # If using Anthropic

**No Memories Retrieved**

.. code-block:: text

   🔄 Retrieving memories after reset...
   ℹ️  No relevant memories found

**This is normal if**:
- First turn (no memories yet)
- Query doesn't match stored memories semantically
- mem0 hasn't processed messages yet (async extraction)

**Check**:
1. Verify recording succeeded: Look for ``✅ mem0 extracted X fact(s)`` in logs
2. Browse Qdrant collections: http://localhost:6333/dashboard
3. Check debug files: ``.massgen/.../memory_debug/*.json``

**0 Facts Extracted**

.. code-block:: text

   ✅ mem0 extracted 0 fact(s), 0 relation(s)
   ⚠️  mem0 extracted 0 facts (check fact extraction prompt or content quality)

**Common causes**:
1. **Content too short**: Less than 10 chars or empty messages
2. **Weak extraction model**: gpt-4o-mini may fail on complex content
3. **Generic content**: No extractable facts (e.g., voting messages)
4. **JSON parsing error**: Model hit token limit mid-response

**Solutions**:
1. Use stronger model: Change ``llm.model`` to ``"gpt-4o"``
2. Enable debug mode: ``--debug`` to inspect ``messages_sent``
3. Check content length in logs: ``Combined content length: X chars``
4. Enable ``record_all_tool_calls: true`` to provide more context

**PointStruct Validation Errors**

.. code-block:: text

   Error: 6 validation errors for PointStruct
   vector.list[float] Input should be a valid list [type=list_type, input_value=None]

**Cause**: Embedding API returned ``None`` instead of valid vector

**Common reasons**:
1. **Empty content**: Message with no text sent to embedding API
2. **API failure**: Rate limit, timeout, or invalid API key
3. **Malformed input**: Special characters or encoding issues

**Solution**: This is now automatically prevented by content validation (messages < 10 chars filtered out). If still occurring, check API key and embedding provider status.

**JSON Parsing Errors from mem0**

.. code-block:: text

   Invalid JSON response: Unterminated string starting at: line 108 column 7

**Cause**: mem0's extraction LLM hit token limit mid-response, didn't close JSON string

**Solution**: Use stronger extraction model (gpt-4o) or reduce content length

Cleaning Up
~~~~~~~~~~~

**Stop Qdrant**:

.. code-block:: bash

   docker-compose -f docker-compose.qdrant.yml down

**Clear all memories**:

.. code-block:: bash

   # Remove Qdrant storage (WARNING: deletes all memories!)
   rm -rf .massgen/qdrant_storage

**Clear session data**:

.. code-block:: bash

   # Remove specific session
   rm -rf .massgen/memory_test_sessions/session_20251028_143000

   # Or all sessions
   rm -rf .massgen/memory_test_sessions

.. _design-decisions:

Design Decisions
----------------

.. raw:: html

   <details>
   <summary><strong>Why These Architecture Choices?</strong> (Click to expand)</summary>

Why mem0's Native LLMs/Embedders?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Decision**: Use mem0's built-in providers (OpenAI, Anthropic, etc.) instead of wrapping MassGen backends

**Rationale**:

- **Simpler**: No adapter layer, direct integration
- **No async issues**: mem0's adapters are sync, wrapping async MassGen backends caused event loop conflicts
- **Optimized**: mem0's default (gpt-4.1-nano) is optimized for memory operations
- **Flexible**: Support for many providers without custom code

**Trade-off**: Requires separate API keys (can't reuse agent's backend). But memory operations are cheap (~1-2 cents/session).

Why MCP Tools Are Optional in Memory (v0.1.9+)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Default**: MCP tool calls (read_file, list_directory, etc.) are **not** recorded

**Rationale**:

1. **Implementation details**: HOW the work was done, not WHAT was learned
2. **Redundant**: The final answer usually captures insights from reading those files
3. **Noise**: 50+ file reads can overwhelm mem0's extraction, making it harder to extract semantic facts
4. **Focus on outcomes**: Agent's conclusions more valuable than execution trace
5. **Token efficiency**: Keeps memory concise and focused

**Example (default mode)**:

.. code-block:: text

   Recorded to memory:
   ✅ Final answer: "The backend uses an adapter pattern in base.py that enables provider abstraction"

   Not recorded:
   ❌ [Tool: read_file] path=/foo/base.py
   ❌ [Tool: read_file] path=/foo/openai.py
   ❌ [Tool: read_file] path=/foo/claude.py

**When to Enable** (``record_all_tool_calls: true``):

- **Learning tool patterns**: Understand which tool sequences work best
- **Debugging**: See exactly what agent explored
- **Pattern analysis**: Extract insights like "directory_tree before read_file is more effective"
- **Development**: Maximum observability during testing

**Example (all tools mode)**:

.. code-block:: text

   Recorded to memory:
   ✅ [Tool Call: mcp__filesystem__directory_tree]
      Arguments: {"path": "/massgen"}
      Result: [50+ files and directories...]
   ✅ [Tool Call: mcp__filesystem__read_text_file]
      Arguments: {"path": "/massgen/base.py"}
      Result: [full file contents...]
   ✅ Final answer: "The backend uses an adapter pattern..."

mem0's LLM can then extract: "For analyzing codebases, using directory_tree first followed by reading key files provides systematic understanding"

**If you just need execution history** (not learning patterns): Check orchestrator logs or agent workspace snapshots instead.

Why Record Reasoning?
~~~~~~~~~~~~~~~~~~~~~

**Decision**: Include full reasoning chains and summaries in memory

**Rationale**:

- **Context for decisions**: Final answer is meaningless without the reasoning
- **Better fact extraction**: mem0's LLM can extract richer facts from reasoning
- **Debugging**: Understand WHY agent made certain choices
- **Learning**: Future turns benefit from understanding past reasoning

**Example memory facts extracted**:

- Without reasoning: "Agent said backend uses adapters"
- With reasoning: "Agent analyzed base.py first, then compared 5 implementations, concluded adapters enable provider abstraction"

Why Filter System Messages?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Decision**: Exclude ``role: "system"`` messages from memory

**Rationale**:

- **Orchestrator noise**: System messages contain coordination prompts like "You are evaluating answers from multiple agents..."
- **Not conversation content**: System prompts are framework instructions, not user/agent dialogue
- **Bloat**: Can be 5-10KB per message, mostly boilerplate
- **Focus on semantics**: User questions and agent answers are what matter for memory

Why Smart Retrieval (exclude_recent)?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Decision**: Default ``exclude_recent: true`` - only retrieve after compression

**Rationale**:

- **Before compression**: All context already in conversation_memory sent to LLM
- **Retrieval would duplicate**: Waste tokens on information already present
- **After compression**: Old messages removed, retrieval fills the gap
- **On restart**: Always retrieve to restore context

**Token efficiency**:

- Without exclude_recent: ~500 extra tokens per turn (duplicated context)
- With exclude_recent: ~100 tokens only when needed (after compression)

Context Compression Thresholds
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Decision**: Default 75% trigger, 40% target

**Rationale**:

- **75% trigger**: Provides buffer before hitting limit (avoid truncation)
- **40% target**: Balances context retention vs. token budget
- **Room for retrieval**: Retrieved facts + recent context fit comfortably
- **Headroom for response**: LLM has space to generate long responses

**Alternative configurations**:

- **Long analysis tasks**: Lower threshold (50%) to compress more aggressively
- **Short conversations**: Higher threshold (90%) to compress rarely

Why Qdrant Server for Multi-Agent?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Decision**: Require Qdrant server mode (Docker) for multi-agent setups

**Rationale**:

- **Concurrent access**: File-based Qdrant locks on first access
- **Performance**: Server mode handles parallel searches better
- **Robustness**: No stale lock files from crashed processes
- **Scalability**: Can scale to many agents

**Trade-off**: Requires Docker. But setup is one command: ``docker-compose up -d``

Why Separate Memories Per Agent?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Decision**: Each agent has isolated memories, filtered by ``agent_id``

**Rationale**:

- **Specialization**: Different agents can build different knowledge bases
- **Controlled sharing**: Only share via turn-aware winner mechanism
- **Scalability**: Single Qdrant database, filtered by metadata
- **Privacy**: Agent-specific knowledge stays private until winning

**Alternative considered**: Shared memory pool for all agents. Rejected because:
- Information overload: Agent sees irrelevant memories from other agents
- Loss of specialization: Can't maintain agent-specific expertise
- Temporal issues: Agent sees work-in-progress from concurrent agents

Why Turn-Aware Memory Filtering?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Decision**: Filter previous winners' memories by ``{"turn": 1}`` metadata

**Rationale**:

**Prevents temporal leakage**:

.. code-block:: text

   Turn 2 (concurrent):
   - agent_a working... (incomplete)
   - agent_b working... (incomplete)

   Without filtering:
   - agent_a could see agent_b's Turn 2 work-in-progress ❌
   - Leads to confusion, inconsistent state

   With filtering:
   - agent_a only sees agent_b's Turn 1 (complete, winner) ✅
   - Clean separation of concurrent work

**Implementation**: Memories tagged with ``{"turn": N}`` on recording, filtered on retrieval.

.. raw:: html

   </details>

API Reference
-------------

For programmatic usage, see the memory module docstrings:

- ``massgen.memory.PersistentMemory`` - Persistent memory API
- ``massgen.memory.ConversationMemory`` - Conversation memory API
- ``massgen.memory._context_monitor`` - Context monitoring utilities

  - ``log_context_usage_from_buffer(buffer, turn_number)`` - Buffer-based tracking (recommended)
  - ``log_context_usage_from_tokens(tokens, turn_number)`` - Official API token counts
  - ``log_context_usage(messages, turn_number)`` - Legacy message-based tracking

- ``massgen.conversation_buffer.AgentConversationBuffer`` - Conversation buffer

  - ``estimate_tokens(calculator)`` - Get total token count including pending content
  - ``get_token_stats(calculator)`` - Get breakdown by entry type (user, assistant, tool_call, etc.)

Examples
--------

See complete examples in:

- ``massgen/configs/memory/gpt5mini_gemini_context_window_management.yaml``
- ``massgen/configs/memory/gpt5mini_high_reasoning_gemini.yaml``

Future Improvements
-------------------

.. note::
   The memory system is production-ready but has several planned enhancements.

Planned Features
~~~~~~~~~~~~~~~~

**1. Proactive Streaming Interruption** *(Partially Implemented)*

**Implemented**: Buffer-based token tracking captures ALL content during streaming:

.. code-block:: text

   [Agent streaming response...]
   → [Buffer tracks: tool calls, results, reasoning, content]
   → [Pre-processing: 📊 Context Buffer: 45K / 128K tokens [buffer]]
   → [Post-processing: 📊 Context Window: 45K / 128K tokens [API actual]]
   → [Compress if needed]

**Remaining**: Proactive interruption when approaching budget

**Planned**: Inject warning to agent mid-stream when approaching limit

.. code-block:: text

   [Agent streaming...]
   → [Buffer counter: 95K / 128K budget]
   → [Agent sees: "⚠️ Approaching token limit, wrap up"]
   → [Agent concludes early]

**2. Memory Analytics Dashboard**

**Planned**: Visualize memory quality and tool usage patterns

.. code-block:: text

   Memory Analytics Dashboard
   ===========================

   Facts Extracted: 245 (last 7 days)
   Tool Patterns Learned: 12

   Top Tool Sequences:
   1. directory_tree → read_file → grep (85% success)
   2. list_directory → read_file (92% success)

   Fact Quality:
   - Actionable: 78%
   - Generic: 15%
   - Redundant: 7%

**3. Smart Tool Result Summarization**

**Planned**: Automatically summarize large MCP tool results before recording

.. code-block:: yaml

   memory:
     recording:
       record_all_tool_calls: true
       summarize_large_results: true  # Auto-summarize results > 5KB
       summary_model: "gpt-4o-mini"   # Model for summarization

**Benefit**: Capture tool usage patterns without overwhelming mem0's extraction LLM with 50KB directory trees

**4. Memory Summarization on Compression** *(Implemented)*

Compression now generates a comprehensive summary of all work done:

.. code-block:: text

   Compression Flow:
   1. Context limit error detected
   2. Generate summary of buffer content (tool calls, results, analysis)
   3. Rebuild context: [system] → [user request] → [summary]
   4. Summary placed LAST so model continues from it (not restart)

The user→summary ordering prevents models from re-reading files or redoing analysis
that was already completed before compression.

Known Limitations
~~~~~~~~~~~~~~~~~

**Token Counting During Streaming** *(Improved in v0.1.25+)*

Buffer-based tracking now provides context estimates during streaming:

- ✅ **Before processing**: Buffer estimation shows current context size
- ✅ **After response**: Official API counts used when available
- ✅ **Accurate tracking**: Includes tool calls, results, injections, reasoning
- ❌ Can't stop mid-response if too large (proactive interruption planned)
- ❌ No real-time budget warnings to agent yet
- ❌ Reasoning not provided by APIs so buffer can be inaccurate

**Workaround**: Set conservative compression thresholds (50-60%) to leave headroom.

**Extraction Quality Depends on Model**

The quality of extracted facts varies significantly by model:

- **gpt-4.1-nano / gpt-4o-mini**: Fast, cheap, but may produce generic facts or JSON parsing errors on complex content
- **gpt-4o / gpt-4-turbo**: Slower, more expensive, but extracts specific, actionable insights

**Recommendation**: Use gpt-4o-mini for development, gpt-4o for production if fact quality matters.

**MCP Tools Recording is Opt-In**

By default, MCP tool calls (read_file, list_directory) are excluded to keep memory concise.

**To enable**: Set ``memory.recording.record_all_tool_calls: true``

**Trade-off**: More data for pattern learning vs. potential information overload for mem0's extraction LLM.

**Session-Level Memory Isolation**

Memories are isolated per session. To access knowledge from previous sessions, either:
- Set ``session_name: null`` (search all sessions)
- Explicitly continue a session with ``session_name: "my_session"``

**Local Qdrant Single-Agent Only**

File-based Qdrant (``mode: "local"``) does NOT support concurrent access.

**For multi-agent**: Always use ``mode: "server"`` with Docker.

Next Steps
----------

- :doc:`multi_turn_mode` - Interactive multi-turn conversations
- :doc:`orchestration_restart` - Graceful restart handling
- :doc:`../logging` - Understanding MassGen's logging system
