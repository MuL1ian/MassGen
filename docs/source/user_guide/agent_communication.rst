Agent Communication
===================

MassGen supports collaborative problem-solving through agent-to-agent communication
and optional human participation. This enables agents to coordinate, ask for help,
and work together more effectively during complex tasks.

Overview
--------

The communication system allows agents to:

- Ask questions to other agents using the ``ask_others()`` tool
- Request input, suggestions, or help during coordination
- Coordinate on shared resources or dependencies
- Optionally include the human user in discussions

Communication is handled through a **broadcast channel** that:

1. Delivers questions to all other agents (inject-then-continue pattern)
2. Collects responses asynchronously
3. Returns responses to the requesting agent
4. Optionally prompts the human user for input

Communication Modes
-------------------

There are three broadcast modes:

**Disabled (default)**
   Broadcasting is completely disabled. Agents work independently.

   .. code-block:: yaml

      orchestrator:
        coordination:
          broadcast: false

**Agent-to-agent**
   Agents can communicate with each other. Questions are broadcast to all other
   agents who can respond.

   .. code-block:: yaml

      orchestrator:
        coordination:
          broadcast: "agents"

**Human-only**
   Agents can ask questions directly to the human user. Other agents are NOT
   prompted - only the human responds. This is useful when you want human
   guidance without agent cross-talk.

   .. code-block:: yaml

      orchestrator:
        coordination:
          broadcast: "human"

Basic Usage
-----------

The ``ask_others()`` tool waits for all responses before returning:

.. code-block:: python

   # Agent calls ask_others()
   result = ask_others("Should I use OAuth2 or JWT for authentication?")

   # Tool blocks and waits for responses
   # Returns: {
   #   "status": "complete",
   #   "responses": [
   #     {"responder_id": "agent_b", "content": "Use OAuth2...", "is_human": False},
   #     {"responder_id": "agent_c", "content": "I agree...", "is_human": False}
   #   ]
   # }

   # Agent can now use responses
   for response in result["responses"]:
       print(f"{response['responder_id']}: {response['content']}")

Configuration Options
---------------------

All broadcast settings are in the orchestrator's coordination config:

.. code-block:: yaml

   orchestrator:
     coordination:
       # Broadcast mode: false (disabled) | "agents" | "human"
       broadcast: "agents"

       # Maximum time to wait for responses (seconds)
       broadcast_timeout: 300

       # Maximum active broadcasts per agent
       max_broadcasts_per_agent: 10

       # How frequently agents use ask_others() (optional)
       # Options: "low" | "medium" | "high"
       broadcast_sensitivity: "medium"

Complete Configuration Examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Agent-to-Agent Communication**

.. code-block:: yaml

   # massgen/configs/broadcast/test_broadcast_agents.yaml
   agents:
     - id: agent_a
       backend:
         type: openai
         model: gpt-5
         cwd: workspace1
         enable_mcp_command_line: true
         command_line_execution_mode: docker

     - id: agent_b
       backend:
         type: gemini
         model: gemini-3-pro-preview
         cwd: workspace2
         enable_mcp_command_line: true
         command_line_execution_mode: docker

   orchestrator:
     snapshot_storage: snapshots
     agent_temporary_workspace: temp_workspaces

     coordination:
       broadcast: "agents"  # Enable agent-to-agent communication
       broadcast_sensitivity: "high"  # Agents use ask_others() frequently
       broadcast_timeout: 300
       max_broadcasts_per_agent: 10

**Human-in-the-Loop Communication**

.. code-block:: yaml

   # massgen/configs/broadcast/test_broadcast_human.yaml
   agents:
     - id: agent_a
       backend:
         type: openai
         model: gpt-5
         cwd: workspace1
         enable_mcp_command_line: true
         command_line_execution_mode: docker

     - id: agent_b
       backend:
         type: gemini
         model: gemini-3-pro-preview
         cwd: workspace2
         enable_mcp_command_line: true
         command_line_execution_mode: docker

   orchestrator:
     snapshot_storage: snapshots
     agent_temporary_workspace: temp_workspaces

     coordination:
       broadcast: "human"  # Human will be prompted for responses
       broadcast_sensitivity: "high"
       broadcast_timeout: 60  # Shorter timeout for interactive sessions
       max_broadcasts_per_agent: 5

Human Participation
-------------------

When ``broadcast: "human"`` is enabled, the human user is the sole responder.
Other agents are NOT prompted - only the human answers questions:

.. code-block:: yaml

   orchestrator:
     coordination:
       broadcast: "human"

**What happens:**

1. Agent calls ``ask_others("Question here")``
2. Human sees notification in terminal (other agents are NOT notified):

   .. code-block:: text

      ======================================================================
      📢 BROADCAST FROM AGENT_A
      ======================================================================

      Should I use OAuth2 or JWT for authentication?

      ──────────────────────────────────────────────────────────────────────
      Options:
        • Type your response and press Enter
        • Press Enter alone to skip
        • You have 300 seconds to respond
      ======================================================================
      Your response (or Enter to skip):

3. Human can:
   - Type response and press Enter
   - Press Enter to skip (no response)
   - Wait for timeout (no response)

4. Human's response is returned to the requesting agent

Human Q&A Context Injection
~~~~~~~~~~~~~~~~~~~~~~~~~~~

When multiple agents run in parallel, they may ask similar questions to the human.
MassGen prevents redundant prompts through **serialization** and **Q&A history reuse**.

**Serialization:**

In human mode, ``ask_others()`` calls are serialized - only one agent can prompt the
human at a time. If Agent B calls ``ask_others()`` while Agent A is waiting for a
response, Agent B waits until Agent A's request completes.

**Q&A History Reuse:**

Once a human has answered any question, subsequent ``ask_others()`` calls return
the existing Q&A history **without prompting the human again**:

.. code-block:: json

   {
     "status": "deferred",
     "responses": [],
     "human_qa_history": [
       {"question": "What color theme?", "answer": "Dark mode"}
     ],
     "human_qa_note": "The human has already answered questions this session. Review the history above..."
   }

The agent receives the existing Q&A history to check if their question was already
answered. If the existing Q&A answers their question, they can use it directly.
If their question needs different information, they can call ``ask_others()`` again
with a more specific question (which will prompt the human for new input).

**How it works:**

1. Agent A calls ``ask_others("What color theme?")`` → acquires lock → prompts human
2. Agent B calls ``ask_others("What style?")`` → waits for lock...
3. Human answers "Dark mode" → Q&A stored → Agent A gets response → lock released
4. Agent B acquires lock → sees Q&A history exists → returns "deferred" with Q&A (NO prompt!)
5. Agent B uses existing Q&A or asks a different question

**Key points:**

- Human is only prompted **once** - subsequent calls return existing Q&A
- ``ask_others()`` calls are serialized (one at a time) in human mode
- Q&A history persists across all turns within a session
- Agents can call ``ask_others()`` again with a different question if needed
- **Note:** Q&A history reuse only applies to ``broadcast: "human"`` mode, not agent-to-agent communication

Examples
--------

Example 1: Coordinating on Shared Resources
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Agent A is about to modify shared code
   result = ask_others(
       "I'm about to refactor the authentication module to use OAuth2. "
       "Any concerns or conflicts with your current work?"
   )

   # Check responses
   for response in result["responses"]:
       if "concern" in response["content"].lower():
           # Address concerns before proceeding
           print(f"⚠️  {response['responder_id']} has concerns: {response['content']}")

Example 2: Getting Help When Stuck
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Agent is stuck on a bug
   result = ask_others(
       "I'm seeing a weird authentication error: 'Token signature invalid'. "
       "I've verified the secret key is correct. Any ideas what might cause this?"
   )

   # Review suggestions
   for response in result["responses"]:
       print(f"💡 Suggestion from {response['responder_id']}: {response['content']}")

Example 3: Hitting a Blocker
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Agent hits a blocker and needs human input
   result = ask_others(
       "The Google Maps API requires authentication and I don't have credentials. "
       "Should I use a free alternative like OpenStreetMap, or do you have API keys I should use?"
   )

   # Use human's guidance to proceed
   for response in result["responses"]:
       print(f"Guidance: {response['content']}")

Example 4: Multiple Viable Approaches
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Agent needs help choosing between approaches
   result = ask_others(
       "I can implement the data visualization using either Chart.js (simpler, lighter) "
       "or D3.js (more powerful, steeper learning curve). "
       "Which would you prefer given your needs?"
   )

   # Implement based on preference
   for response in result["responses"]:
       print(f"Decision: {response['content']}")

Example 5: Human Participation (Design Preferences)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With ``broadcast: "human"`` enabled:

.. code-block:: python

   # Agent asks for human preferences on design decisions
   result = ask_others(
       "For the portfolio website, would you prefer: "
       "(A) a single-page design with smooth scrolling, or "
       "(B) multiple pages with navigation? "
       "Also, should I include a contact form or just list your email?"
   )

   # In human mode, only the human responds
   for response in result["responses"]:
       print(f"👤 Human: {response['content']}")

Example 6: Clarifying Requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Agent needs clarification on vague requirements
   result = ask_others(
       "You mentioned 'professional styling' for the landing page. "
       "Do you want a corporate/minimalist look, or something more colorful/creative? "
       "Any specific colors or brand guidelines to follow?"
   )

   # Use clarified requirements
   for response in result["responses"]:
       print(f"Requirements: {response['content']}")

Example 7: Using Human Q&A History (Deferred Response)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When Q&A history exists, ``ask_others()`` returns immediately with status
"deferred" instead of prompting the human again:

.. code-block:: python

   # Agent B calls ask_others (Agent A already asked the human earlier)
   result = ask_others("What database should we use?")

   # Check if we got a deferred response (Q&A history exists)
   if result["status"] == "deferred":
       print("Human was NOT prompted - using existing Q&A history:")
       for qa in result["human_qa_history"]:
           print(f"  Q: {qa['question']}")
           print(f"  A: {qa['answer']}")

       # Use existing answers or call ask_others with a different question
       # if more specific information is needed

   elif result["status"] == "complete":
       # This was the first ask_others call - human was prompted
       for response in result["responses"]:
           print(f"Human: {response['content']}")

Technical Details
-----------------

Inject-then-Continue Pattern (Agent Mode)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When an agent calls ``ask_others()`` in **agent mode** (``broadcast: "agents"``):

1. Broadcast created with unique ``request_id``
2. Question injected into all other agents' queues
3. Each agent checks queue at turn boundaries (not a hard interrupt)
4. Agent responds, then continues with original task
5. Responses collected asynchronously
6. Requesting agent receives all responses when complete

This pattern ensures agents aren't abruptly interrupted mid-task.

**Important Limitation: Fresh Context for Agent Responses**

When an agent receives a broadcast question from another agent, it responds using a
**separate, fresh LLM call** with NO conversation history. This means:

- The responding agent sees ONLY the broadcast question
- It does NOT have access to its own conversation history
- It does NOT have access to the requesting agent's context
- Only the ``respond_to_broadcast`` tool is available (no MCP tools, no ``ask_others``)

**Why this design:**

- Keeps responses focused and concise
- Prevents agents from accessing MCP tools or asking new questions during broadcast response
- Avoids interference between the agent's main task and broadcast responses
- Simpler implementation and debugging

**Future enhancement:**

A future version may add "context-aware" broadcast mode where responding agents can access
their conversation history. For now, agents should provide self-contained questions that
don't require the responder to know about prior context.

**Example:**

.. code-block:: python

   # ❌ Bad - requires context
   ask_others("What do you think about this approach?")  # What approach?

   # ✅ Good - self-contained
   ask_others(
       "I'm considering using React with TypeScript for the frontend. "
       "Do you see any issues with this choice?"
   )

Serialized Human Mode
~~~~~~~~~~~~~~~~~~~~~

When an agent calls ``ask_others()`` in **human mode** (``broadcast: "human"``):

1. Agent acquires the ``ask_others`` lock (waits if another agent holds it)
2. If Q&A history exists → returns "deferred" with history (no human prompt)
3. If no Q&A history → prompts human and waits for response
4. Response stored in Q&A history
5. Lock released, next waiting agent proceeds

This ensures:

- Human sees only **one prompt at a time**
- Subsequent agents get existing Q&A without re-prompting
- Q&A history persists across all turns in the session

Broadcast Tools
~~~~~~~~~~~~~~~

Built-in tools automatically available when broadcasts are enabled:

``ask_others(question: str)``
   Ask question to other agents or human. Waits for and returns all responses.

``respond_to_broadcast(answer: str)``
   (Agent mode only) Respond to a broadcast question from another agent.

These are built-in workflow tools, not MCP servers.

Rate Limiting
~~~~~~~~~~~~~

Each agent can have at most ``max_broadcasts_per_agent`` active broadcasts
(default: 10). This prevents agents from spamming broadcasts.

Troubleshooting
---------------

**Broadcasts not working**
   - Check that ``broadcast`` is set to ``"agents"`` or ``"human"`` (not ``false``)
   - Verify all agents are initialized and have ``_orchestrator`` reference
   - Check logs for MCP tool injection messages

**Human prompts not appearing**
   - Ensure ``broadcast: "human"`` is set (not just ``"agents"``)
   - Check that ``coordination_ui`` is initialized
   - Verify timeout hasn't expired

**Timeouts occurring**
   - Increase ``broadcast_timeout`` if agents need more time to respond
   - Check agent logs to see if they're receiving broadcasts
   - Verify agents aren't stuck or errored

See Also
--------

- :doc:`agent_task_planning` - Task planning system for organizing work
- :doc:`../reference/yaml_schema` - Complete YAML configuration reference
