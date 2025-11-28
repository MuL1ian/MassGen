Agent Communication
===================

MassGen supports collaborative problem-solving through agent-to-agent communication
and optional human participation. This enables agents to coordinate, ask for help,
and work together more effectively during complex tasks.

.. note::
   This feature is part of the Agent Planning & Coordination system (Phase 2).
   Requires MassGen v0.1.11 or later.

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

Blocking Mode (Default)
~~~~~~~~~~~~~~~~~~~~~~~

In blocking mode, ``ask_others()`` waits for all responses before returning:

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

Polling Mode
~~~~~~~~~~~~

In polling mode, ``ask_others()`` returns immediately and agents check status later:

.. code-block:: yaml

   orchestrator:
     coordination:
       broadcast: "agents"
       broadcast_wait_by_default: false

.. code-block:: python

   # Agent asks question without waiting
   result = ask_others("Should I use OAuth2 or JWT?", wait=False)
   request_id = result["request_id"]

   # Continue with other work
   # ... do other tasks ...

   # Check if responses are ready
   status = check_broadcast_status(request_id)
   if status["status"] == "complete":
       responses = get_broadcast_responses(request_id)
       # Process responses

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

       # Default behavior: true (blocking) | false (polling)
       broadcast_wait_by_default: true

       # Response mode: "inline" | "background"
       broadcast_response_mode: "inline"

       # Maximum active broadcasts per agent
       max_broadcasts_per_agent: 10

Response Modes
--------------

Inline Mode (default)
~~~~~~~~~~~~~~~~~~~~~

When agents receive broadcast questions, the question is injected into their current
conversation context. They respond naturally as part of their ongoing work.

**Pros:** Agent has full context, can reference their current work
**Cons:** Slightly interrupts the agent's current train of thought

.. code-block:: yaml

   orchestrator:
     coordination:
       broadcast_response_mode: "inline"

Background Mode
~~~~~~~~~~~~~~~

When agents receive broadcast questions, a separate LLM call is made with a snapshot
of their recent context to generate a response.

**Pros:** Main task flow is not interrupted
**Cons:** Response based on context snapshot, not live state

.. code-block:: yaml

   orchestrator:
     coordination:
       broadcast_response_mode: "background"

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

The agent receives the existing Q&A and can decide whether to use it or call
``ask_others()`` again with a more specific question if needed.

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

Best Practices
--------------

When to Use ask_others()
~~~~~~~~~~~~~~~~~~~~~~~~

**Good use cases:**

- "I'm about to refactor the User model. Any concerns or suggestions?"
- "Does anyone know which OAuth library we decided to use?"
- "I'm stuck on this authentication bug. Ideas?"
- "Should I use approach A or approach B for this feature?"

**Avoid overuse:**

- Don't broadcast for status updates ("I'm starting work")
- Don't broadcast for trivial questions that you can answer yourself
- Don't broadcast too frequently (use the 10 broadcast limit wisely)

Writing Good Questions
~~~~~~~~~~~~~~~~~~~~~~

Be **specific and actionable**:

✅ Good: "I'm about to add a new field to the User table. Any schema concerns?"
❌ Bad: "What do you think?"

✅ Good: "Should I use Redis or Memcached for session storage? Our requirements are X, Y, Z."
❌ Bad: "Which cache should I use?"

Responding to Broadcasts
~~~~~~~~~~~~~~~~~~~~~~~~~

When you receive a broadcast question from another agent:

- Provide helpful, concise responses
- Reference your current work if relevant
- Be collaborative and constructive
- Then continue with your original task

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

Example 3: Polling Mode for Long-Running Work
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Agent delegates research and continues working
   result = ask_others(
       "Can someone research OAuth2 provider options (Google, GitHub, Auth0)? "
       "I need feature comparison and pricing.",
       wait=False
   )
   request_id = result["request_id"]

   # Continue with other work
   # ... implement database models ...
   # ... write tests ...

   # Check if research is ready
   status = check_broadcast_status(request_id)
   if status["status"] == "complete":
       research = get_broadcast_responses(request_id)
       # Use research results

Example 4: Human Participation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With ``broadcast: "human"`` enabled:

.. code-block:: python

   # Agent asks for human input (only human responds, not other agents)
   result = ask_others(
       "I've identified two approaches for implementing this feature. "
       "Approach A is faster but less flexible. Approach B is more robust "
       "but takes longer. Which should I prioritize?"
   )

   # In human mode, only the human responds
   for response in result["responses"]:
       print(f"👤 Human: {response['content']}")

Example 5: Using Human Q&A History (Deferred Response)
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
6. Requesting agent gets responses (immediately if blocking, via polling if not)

This pattern ensures agents aren't abruptly interrupted mid-task.

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

MCP Tools
~~~~~~~~~

Three MCP tools are injected when broadcasts are enabled:

``ask_others(question: str, wait: Optional[bool] = None)``
   Ask question to other agents. Returns responses (blocking) or request_id (polling).

``check_broadcast_status(request_id: str)``
   Check if broadcast is complete and how many responses collected.

``get_broadcast_responses(request_id: str)``
   Get all responses for a broadcast request.

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
