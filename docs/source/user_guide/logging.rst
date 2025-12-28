Logging & Debugging
===================

MassGen provides comprehensive logging to help you understand agent coordination, debug issues, and review decision-making processes.

Logging Directory Structure
----------------------------

All logs are stored in the ``.massgen/massgen_logs/`` directory with timestamped subdirectories:

.. code-block:: text

   .massgen/
   └── massgen_logs/
       └── log_YYYYMMDD_HHMMSS/           # Timestamped log directory
           ├── agent_a/                    # Agent-specific coordination logs
           │   └── YYYYMMDD_HHMMSS_NNNNNN/ # Timestamped coordination steps
           │       ├── answer.txt          # Agent's answer at this step
           │       ├── context.txt         # Context available to agent
           │       └── workspace/          # Agent workspace (if filesystem tools used)
           ├── agent_b/                    # Second agent's logs
           │   └── ...
           ├── agent_outputs/              # Consolidated output files
           │   ├── agent_a.txt             # Complete output from agent_a
           │   ├── agent_b.txt             # Complete output from agent_b
           │   ├── final_presentation_agent_X.txt  # Winning agent's final answer
           │   ├── final_presentation_agent_X_latest.txt  # Symlink to latest
           │   └── system_status.txt       # System status and metadata
           ├── final/                      # Final presentation phase
           │   └── agent_X/                # Winning agent's final work
           │       ├── answer.txt          # Final answer
           │       └── context.txt         # Final context
           ├── coordination_events.json    # Structured coordination events
           ├── coordination_table.txt      # Human-readable coordination table
           ├── vote.json                   # Final vote tallies and consensus data
           ├── massgen.log                 # Complete debug log (or massgen_debug.log in debug mode)
           ├── snapshot_mappings.json      # Workspace snapshot metadata
           └── execution_metadata.yaml     # Query, config, and execution details

.. note::
   When agents use filesystem tools, each coordination step will also contain a ``workspace/`` directory showing the files the agent created or modified during that step.

Per-Attempt Logging (Orchestration Restart)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When **orchestration restart** is enabled, each restart attempt gets its own isolated directory:

.. code-block:: text

   .massgen/massgen_logs/log_YYYYMMDD_HHMMSS/
   ├── attempt_1/          # First attempt (complete log structure)
   ├── attempt_2/          # Second attempt after restart
   ├── attempt_3/          # Third attempt if needed
   └── final/              # Copy of accepted result

For multi-turn: ``turn_1/attempt_1/``, ``turn_1/attempt_2/``, ``turn_1/final/``

.. seealso::
   :doc:`sessions/orchestration_restart` - Learn about automatic quality checks and restart workflows

Log Files Explained
-------------------

Agent Coordination Logs
~~~~~~~~~~~~~~~~~~~~~~~~

**Location**: ``agent_<id>/YYYYMMDD_HHMMSS_NNNNNN/``

Each coordination step gets a timestamped directory containing:

* ``answer.txt`` - The agent's answer/proposal at this step
* ``context.txt`` - What answers/context the agent could see (recent answers from other agents)

**Use cases:**

* Review what each agent proposed during coordination
* Understand how agents' thinking evolved as they saw other agents' work
* Debug why specific decisions were made

Consolidated Agent Outputs
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Location**: ``agent_outputs/``

Contains merged outputs from all coordination rounds:

* ``agent_<id>.txt`` - Complete output history for each agent
* ``final_presentation_agent_<id>.txt`` - Winning agent's final presentation
* ``final_presentation_agent_<id>_latest.txt`` - Symlink to latest (for automation)
* ``system_status.txt`` - System metadata and status

Final Presentation
~~~~~~~~~~~~~~~~~~

**Location**: ``final/agent_<id>/``

The winning agent's final answer after coordination:

* ``answer.txt`` - Complete final answer
* ``context.txt`` - Final context used for presentation

Coordination Events
~~~~~~~~~~~~~~~~~~~

**Location**: ``coordination_events.json``

Structured JSON log of all coordination events:

.. code-block:: json

   {
     "event_id": "E42",
     "timestamp": "2025-10-08T01:40:29",
     "agent_id": "agent_a",
     "event_type": "vote",
     "data": {
       "vote_for": "agent_b.2",
       "reason": "More comprehensive approach..."
     }
   }

**Event types:**

* ``started_streaming`` - Agent begins thinking
* ``new_answer`` - Agent provides labeled answer
* ``vote`` - Agent votes for an answer
* ``restart`` - Agent requests restart
* ``restart_completed`` - Agent finishes restart
* ``final_answer`` - Winner provides final response

Vote Summary
~~~~~~~~~~~~

**Location**: ``vote.json``

Final vote tallies and consensus information:

.. code-block:: json

   {
     "votes": {
       "agent_a": {
         "voted_for": "agent_b",
         "reason": "More comprehensive analysis"
       },
       "agent_b": {
         "voted_for": "agent_b",
         "reason": "Best captures key insights"
       }
     },
     "winner": "agent_b",
     "consensus_reached": true
   }

**Use cases:**

* Understand final consensus decision
* Review voting patterns across agents
* Analyze decision-making rationale

Main Debug Log
~~~~~~~~~~~~~~

**Location**: ``massgen.log``

Complete debug log with all system operations:

* Backend API calls and responses
* Tool usage and results
* Coordination state transitions
* Error messages and stack traces

Enable with ``--debug`` flag for verbose logging.

Execution Metadata
~~~~~~~~~~~~~~~~~~

**Location**: ``execution_metadata.yaml``

This file captures the complete execution context for reproducibility:

.. code-block:: yaml

   query: "Your original question"
   timestamp: "2025-10-13T14:30:22"
   config_path: "/path/to/config.yaml"
   config:
     agents:
       - id: "agent1"
         backend:
           type: "gemini"
           model: "gemini-2.5-flash"
       # ... full config
   cli_args:
     config: "/path/to/config.yaml"
     question: "Your original question"
     debug: false
     # ... all CLI arguments
   git:
     commit: "a1b2c3d4e5f6..."
     branch: "main"
   python_version: "3.13.0"
   massgen_version: "0.0.33"
   working_directory: "/path/to/project"

**Contents:**

* ``query`` - The user's original query/prompt
* ``timestamp`` - When the execution started (ISO 8601 format)
* ``config_path`` - Path or description of config used
* ``config`` - Complete configuration (full YAML/JSON content)
* ``cli_args`` - All command-line arguments passed to massgen
* ``git`` - Git repository info (commit hash, branch) if in a git repo
* ``python_version`` - Python interpreter version
* ``massgen_version`` - MassGen package version
* ``working_directory`` - Current working directory

**Use cases:**

* **Reproduce the exact same run** - All information needed to recreate execution
* **Debug configuration issues** - Full config and CLI args captured
* **Share execution details** - Send metadata file to team members
* **Create test cases** - Convert real runs into regression tests
* **Track experiments** - Git commit ensures you know which code version was used
* **Environment debugging** - Python version and working directory help diagnose environment issues

**Multi-turn sessions:**

For interactive multi-turn mode, each turn gets its own ``execution_metadata.yaml`` with additional fields:

.. code-block:: yaml

   # ... standard fields above ...
   cli_args:
     mode: "interactive"
     turn: 3
     session_id: "session_20251013_143022"

Coordination Table
------------------

The **coordination table** (``coordination_table.txt``) is a human-readable visualization of the entire multi-agent coordination process.

Structure
~~~~~~~~~

.. code-block:: text

   +-------------------------------------------------------------------+
   |   Event  |           Agent 1           |           Agent 2           |
   |----------+-----------------------------+-----------------------------+
   |   USER   | Original user question                                     |
   |==========+=============================+=============================+
   |     E1   |     📋 Context: []          |      ⏳ (waiting)            |
   |          |  💭 Started streaming       |                             |
   |----------+-----------------------------+-----------------------------+
   |     E2   |     🔄 (streaming)          |   ✨ NEW ANSWER: agent2.1   |
   |          |                             |👁️  Preview: Summary...      |
   |----------+-----------------------------+-----------------------------+

**Key sections:**

1. **Header** - Event symbols, status symbols, and terminology
2. **Event log** - Chronological coordination events
3. **Summary** - Final statistics per agent
4. **Totals** - Overall coordination metrics

Event Symbols
~~~~~~~~~~~~~

**Actions:**

* 💭 Started streaming - Agent begins thinking/processing
* ✨ NEW ANSWER - Agent provides a labeled answer
* 🗳️ VOTE - Agent votes for an answer
* 💭 Reason - Reasoning behind the vote
* 👁️ Preview - Content of the answer
* 🔁 RESTART TRIGGERED - Agent requests to restart
* ✅ RESTART COMPLETED - Agent finishes restart
* 🎯 FINAL ANSWER - Winner provides final response
* 🏆 Winner selected - System announces winner

**Status:**

* 💭 (streaming) - Currently thinking/processing
* ⏳ (waiting) - Idle, waiting for turn
* ✅ (answered) - Has provided an answer
* ✅ (voted) - Has cast a vote
* ✅ (completed) - Task completed
* 🎯 (final answer given) - Winner completed final answer

Answer Labels
~~~~~~~~~~~~~

Each answer gets a unique identifier:

**Format**: ``agent{N}.{attempt}``

* ``N`` = Agent number (1, 2, 3...)
* ``attempt`` = New answer number (1, 2, 3...)

**Examples:**

* ``agent1.1`` = Agent 1's first answer
* ``agent2.1`` = Agent 2's first answer
* ``agent1.2`` = Agent 1's second answer (after restart)
* ``agent1.final`` = Agent 1's final answer (if winner)

Coordination Flow
~~~~~~~~~~~~~~~~~

The table shows how agents coordinate:

1. **Agents see recent answers** - Each agent can view the most recent answers from other agents
2. **Decide next action** - Each agent chooses to either:

   * Provide a new/refined answer
   * Vote for an existing answer they think is best

3. **All agents vote** - Coordination continues until all agents have voted
4. **Final presentation** - The agent with the most votes delivers the final answer

**Example interpretation:**

.. code-block:: text

   E7: Agent 1 provides answer agent1.1
   E13: Agent 1 votes for agent1.1 (self-vote)
   E19: Agent 2 votes for agent1.1 (consensus!)
   E39: Agent 1 selected as winner
   E39: Agent 1 provides final answer

**What agents see:**

During coordination, agents see snapshots of each other's work through workspace snapshots and answer context. This allows agents to build on insights, catch errors, and converge on the best solution.

Summary Statistics
~~~~~~~~~~~~~~~~~~

At the bottom of the coordination table:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Metric
     - Description
   * - **Answers**
     - Number of distinct answers provided
   * - **Votes**
     - Number of votes cast
   * - **Restarts**
     - Number of times agent restarted (cleared memory)
   * - **Status**
     - Final completion status

Accessing Logs
--------------

Log Analysis Commands
~~~~~~~~~~~~~~~~~~~~~

MassGen provides the ``massgen logs`` command for quick log analysis without manual file navigation.

**Summary of most recent run:**

.. code-block:: bash

   massgen logs

   # Example output:
   # ╭──────────────────────────── MassGen Run Summary ─────────────────────────────╮
   # │ Create a website about Bob Dylan                                             │
   # │                                                                               │
   # │ Winner: agent_a | Agents: 1 | Duration: 7.2m | Cost: $0.54                   │
   # ╰───────────────────────────────────────────────────────────────────────────────╯
   #
   # Tokens: Input: 6,035,629 | Output: 21,279 | Reasoning: 7,104
   #
   # Rounds (5): answer: 1 | vote: 1 | presentation: 2 | post_evaluation: 1
   #   Errors: 0 | Timeouts: 0
   #
   # ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━┳━━━━━━┓
   # ┃ Tool                                      ┃ Calls ┃  Time ┃  Avg ┃ Fail ┃
   # ┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━╇━━━━━━┩
   # │ mcp__command_line__execute_command        │    47 │  4.4s │ 94ms │      │
   # │ mcp__planning__update_task_status         │    13 │ 228ms │ 18ms │      │
   # └───────────────────────────────────────────┴───────┴───────┴──────┴──────┘

**Available subcommands:**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Command
     - Description
   * - ``massgen logs`` or ``massgen logs summary``
     - Display run summary with tokens, rounds, and top tools
   * - ``massgen logs tools``
     - Full tool breakdown table sorted by execution time
   * - ``massgen logs tools --sort calls``
     - Sort tools by call count instead of time
   * - ``massgen logs list``
     - List recent runs with timestamps, costs, and questions
   * - ``massgen logs list --limit 20``
     - Show more runs (default: 10)
   * - ``massgen logs open``
     - Open log directory in system file manager (Finder/Explorer)

**Common options:**

.. code-block:: bash

   # Analyze a specific log directory
   massgen logs --log-dir .massgen/massgen_logs/log_20251218_134125_867383/turn_1/attempt_1

   # Output raw JSON for scripting
   massgen logs summary --json

**Tool breakdown example:**

.. code-block:: bash

   massgen logs tools

   # ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━┳━━━━━━┓
   # ┃ Tool                                      ┃ Calls ┃  Time ┃  Avg ┃ Fail ┃
   # ┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━╇━━━━━━┩
   # │ mcp__command_line__execute_command        │    47 │  4.4s │ 94ms │      │
   # │ mcp__planning__update_task_status         │    13 │ 228ms │ 18ms │      │
   # │ mcp__filesystem__write_file               │     7 │ 181ms │ 26ms │      │
   # │ mcp__planning__create_task_plan           │     2 │  36ms │ 18ms │      │
   # ├───────────────────────────────────────────┼───────┼───────┼──────┼──────┤
   # │ TOTAL                                     │    69 │  4.8s │      │      │
   # └───────────────────────────────────────────┴───────┴───────┴──────┴──────┘

**List recent runs:**

.. code-block:: bash

   massgen logs list --limit 5

   # ┏━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
   # ┃ # ┃ Timestamp        ┃ Duration ┃  Cost ┃ Question                           ┃
   # ┡━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
   # │ 1 │ 2025-12-18 13:41 │     7.2m │ $0.54 │ Create a website about Bob Dylan   │
   # │ 2 │ 2025-12-17 23:01 │    16.2m │ $1.23 │ Build a REST API...                │
   # │ 3 │ 2025-12-17 22:30 │     3.1m │ $0.12 │ Explain quantum computing...       │
   # └───┴──────────────────┴──────────┴───────┴────────────────────────────────────┘

During Execution
~~~~~~~~~~~~~~~~

**Press 'r' key** during execution to view real-time coordination table in your terminal.

After Execution
~~~~~~~~~~~~~~~

**Find latest log directory:**

.. code-block:: bash

   # Using massgen logs open (recommended)
   massgen logs open

   # Or manually
   ls -t .massgen/massgen_logs/ | head -1

**View coordination table:**

.. code-block:: bash

   cat .massgen/massgen_logs/log_20251008_013641/coordination_table.txt

**View specific agent output:**

.. code-block:: bash

   cat .massgen/massgen_logs/log_20251008_013641/agent_outputs/agent_a.txt

**View final answer:**

.. code-block:: bash

   cat .massgen/massgen_logs/log_20251008_013641/agent_outputs/final_presentation_*_latest.txt

Debug Mode
----------

Enable detailed logging with the ``--debug`` flag:

.. code-block:: bash

   uv run python -m massgen.cli \
     --debug \
     --config your_config.yaml \
     "Your question"

**What debug mode logs:**

* ✅ Full API request/response bodies
* ✅ Tool call arguments and results
* ✅ Coordination state transitions
* ✅ File operation details
* ✅ MCP server communication
* ✅ Error stack traces

**Debug log location**: ``.massgen/massgen_logs/log_YYYYMMDD_HHMMSS/massgen_debug.log``

Common Debugging Scenarios
---------------------------

Agent Not Converging
~~~~~~~~~~~~~~~~~~~~

**Check**: ``coordination_table.txt``

Look for:

* Agents changing votes frequently
* New answers in every round
* No clear vote majority

**Solution**: Review agent answers to understand disagreement points.

Agent Errors
~~~~~~~~~~~~

**Check**: ``massgen.log`` for error messages

**Search for**:

.. code-block:: bash

   grep -i "error" .massgen/massgen_logs/log_*/massgen.log
   grep -i "exception" .massgen/massgen_logs/log_*/massgen.log

Tool Failures
~~~~~~~~~~~~~

**Check**: ``agent_outputs/agent_<id>.txt``

Look for tool call failures and error messages.

**Also check**: ``massgen.log`` for detailed tool execution logs

Understanding Agent Decisions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Review coordination rounds:**

1. Open ``coordination_table.txt``
2. Find the round where decision changed
3. Check ``agent_<id>/YYYYMMDD_HHMMSS_NNNNNN/context.txt`` to see what the agent could see
4. Check ``agent_<id>/YYYYMMDD_HHMMSS_NNNNNN/answer.txt`` for the agent's reasoning

Performance Analysis
~~~~~~~~~~~~~~~~~~~~

**Check summary statistics** in ``coordination_table.txt``:

* High restart count = Agents changing approach frequently
* Low vote count = Quick consensus
* Many answers = Iterative refinement

Log Retention
-------------

Logs are stored indefinitely by default.

**Clean old logs manually:**

.. code-block:: bash

   # Remove logs older than 7 days
   find .massgen/massgen_logs/ -type d -name "log_*" -mtime +7 -exec rm -rf {} +

**Disk space check:**

.. code-block:: bash

   du -sh .massgen/massgen_logs/

Best Practices
--------------

1. **Review coordination table first** - Best overview of what happened
2. **Use debug mode for troubleshooting** - Full details when needed
3. **Archive important logs** - Move successful runs to separate directory
4. **Check final presentation** - Verify winning agent's work quality
5. **Monitor log size** - Clean old logs periodically

Integration with CI/CD
----------------------

**Automated log parsing:**

.. code-block:: python

   import json

   # Parse coordination events
   with open(".massgen/massgen_logs/log_latest/coordination_events.json") as f:
       events = json.load(f)

   # Extract final answer
   with open(".massgen/massgen_logs/log_latest/agent_outputs/final_presentation_*_latest.txt") as f:
       final_answer = f.read()

**Exit status:**

MassGen exits with status 0 on success, non-zero on failure.

.. code-block:: bash

   uv run python -m massgen.cli --config config.yaml "Question" && echo "Success"

Sharing Sessions
----------------

MassGen allows you to share session logs via GitHub Gist for easy collaboration and review.

Prerequisites
~~~~~~~~~~~~~

Sharing requires the **GitHub CLI (gh)** to be installed and authenticated:

1. **Install GitHub CLI**:

   - macOS: ``brew install gh``
   - Windows: ``winget install --id GitHub.cli``
   - Linux: See https://cli.github.com/

2. **Authenticate with GitHub**:

   .. code-block:: bash

      gh auth login

   Follow the prompts to authenticate. This is required for creating gists.

Sharing a Session
~~~~~~~~~~~~~~~~~

Use the ``massgen export`` command to share a session:

.. code-block:: bash

   # Share the most recent session
   massgen export

   # Share a specific session by log directory name
   massgen export log_20251218_134125_867383

   # Share a specific session by full path
   massgen export /path/to/.massgen/massgen_logs/log_20251218_134125_867383

**Output:**

.. code-block:: text

   Sharing session from: /path/to/.massgen/massgen_logs/log_20251218_134125/turn_1/attempt_1
   Collecting files...
   Uploading 45 files (1,234,567 bytes)...

   Share URL: https://massgen.github.io/MassGen-Viewer/?gist=abc123def456

   Anyone with this link can view the session (no login required).

The share URL opens the **MassGen Viewer**, a web-based session viewer that displays:

- Session summary (question, winner, cost, duration)
- Agent activity and coordination timeline
- Answers and votes with full content
- Tool usage breakdown
- Configuration used

**What gets uploaded:**

- Metrics and status files
- Coordination events and votes
- Agent answers (intermediate and final)
- Execution metadata (with API keys redacted)
- Small workspace files (code, text, configs)

**What is excluded:**

- Large files (>10MB)
- Debug logs (``massgen.log``)
- Binary files and caches
- Sensitive data (API keys are automatically redacted)

Managing Shared Sessions
~~~~~~~~~~~~~~~~~~~~~~~~

**List your shared sessions:**

.. code-block:: bash

   massgen shares list

**Delete a shared session:**

.. code-block:: bash

   massgen shares delete <gist_id>

Authentication Errors
~~~~~~~~~~~~~~~~~~~~~

If you see authentication errors when sharing:

.. code-block:: text

   Error: Not authenticated with GitHub.
   Run 'gh auth login' to enable sharing.

**Solution:** Run ``gh auth login`` and complete the authentication flow.

If the GitHub CLI is not installed:

.. code-block:: text

   Error: GitHub CLI (gh) not found.
   Install it from https://cli.github.com/

**Solution:** Install the GitHub CLI for your platform.

Logfire Observability
---------------------

MassGen supports `Logfire <https://logfire.pydantic.dev/docs/>`_ for advanced structured tracing and observability. When enabled, Logfire provides:

* **Automatic LLM instrumentation** - Traces all OpenAI and Anthropic API calls with request/response details
* **Tool execution tracing** - Spans for MCP tool calls with timing and success/failure metrics
* **Coordination events** - Structured logs for agent coordination, voting, and winner selection
* **Token usage metrics** - Detailed tracking of input/output/reasoning/cached tokens
* **Integrated with loguru** - All existing log messages flow through Logfire when enabled

Enabling Logfire
~~~~~~~~~~~~~~~~

**Via CLI flag (recommended):**

.. code-block:: bash

   massgen --logfire --config your_config.yaml "Your question"

**Via environment variable:**

.. code-block:: bash

   export MASSGEN_LOGFIRE_ENABLED=true
   massgen --config your_config.yaml "Your question"

Setting Up Logfire
~~~~~~~~~~~~~~~~~~

1. **Create a Logfire account** at https://logfire.pydantic.dev/

2. **Get your token:**

   .. code-block:: bash

      # Install logfire CLI
      pip install logfire

      # Authenticate
      logfire auth login

   This creates ``~/.logfire/credentials.json`` with your token.

3. **Alternatively, set the token directly:**

   .. code-block:: bash

      export LOGFIRE_TOKEN=your_token_here

4. **Run MassGen with Logfire enabled:**

   .. code-block:: bash

      massgen --logfire --config your_config.yaml "Your question"

What Gets Traced
~~~~~~~~~~~~~~~~

When Logfire is enabled, MassGen automatically traces:

**LLM API Calls:**

* All requests to OpenAI-compatible APIs (GPT-4, etc.)
* All requests to Anthropic Claude API
* All requests to Google GenAI (Gemini) API
* Request parameters, response content, and timing
* Token usage breakdown

.. note::
   For Gemini tracing, set ``OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true``
   to capture full prompts and completions. Without this, content appears as ``<elided>``.

**Tool Executions:**

* MCP server tool calls with full input/output
* Custom tools (like ``read_media``, ``write_file``, etc.)
* Agent attribution via ``massgen.agent_id`` span attribute
* Execution time in milliseconds
* Success/failure status
* Error messages when tools fail

**Coordination Events:**

* ``coordination_started`` - When agent coordination begins
* ``winner_selected`` - When voting completes and a winner is chosen
* Vote counts and participating agents

**Example Logfire Dashboard View:**

.. code-block:: text

   ┌─ coordination.session (45.2s) ──────────────────────────────┐
   │  task: "Build a REST API for user management"              │
   │  num_agents: 3                                              │
   │  agent_ids: agent_a, agent_b, agent_c                      │
   │                                                             │
   │  ├─ llm.call [claude-3-5-sonnet] (3.1s)                   │
   │  │   input_tokens: 1,234                                   │
   │  │   output_tokens: 567                                    │
   │  │                                                         │
   │  ├─ mcp.filesystem.write_file (0.8s)                      │
   │  │   input_chars: 245                                      │
   │  │   output_chars: 12                                      │
   │  │   success: true                                         │
   │  │                                                         │
   │  ├─ [info] Agent answer: agent1.1                         │
   │  │   agent_id: agent_a, iteration: 1, round: 1            │
   │  │                                                         │
   │  ├─ llm.call [gpt-4] (3.5s)                               │
   │  │   input_tokens: 2,456                                   │
   │  │   output_tokens: 823                                    │
   │  │                                                         │
   │  ├─ [info] Agent answer: agent2.1                         │
   │  │   agent_id: agent_b, iteration: 1, round: 1            │
   │  │                                                         │
   │  ├─ [info] Agent vote: agent_a -> agent2.1                │
   │  │   reason: "More comprehensive solution"                │
   │  │                                                         │
   │  ├─ [info] Agent vote: agent_b -> agent2.1                │
   │  │                                                         │
   │  └─ [info] Winner selected: agent2.1                      │
   │      vote_counts: {agent2.1: 2}                           │
   └────────────────────────────────────────────────────────────┘

**What Gets Logged (Meaningful Events Only):**

To reduce noise, MassGen only logs meaningful coordination events:

1. **Session span** (``coordination.session``) - Top-level span for the entire coordination
2. **LLM API calls** - Automatic instrumentation of OpenAI, Anthropic, and Gemini calls
3. **Tool executions** - MCP tool calls with input/output sizes and timing
4. **Agent answers** - When an agent provides a new answer (with label like ``agent1.1``)
5. **Agent votes** - When an agent casts a vote (with reason)
6. **Winner selection** - When voting completes and winner is determined
7. **Final answer** - When the winning agent presents the final response

Note: Individual coordination iterations are tracked internally but not logged to Logfire to avoid cluttering the trace with less useful information.

Tool Execution Attributes
~~~~~~~~~~~~~~~~~~~~~~~~~

All tool execution events include rich attributes for filtering, grouping, and debugging:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Attribute
     - Description
   * - ``agent_id``
     - The ID of the agent executing the tool (e.g., ``agent_a``, ``agent_b``)
   * - ``tool_name``
     - The full tool name (e.g., ``mcp__filesystem__write_file``)
   * - ``tool_type``
     - Tool category: ``mcp`` for MCP tools, ``custom`` for built-in tools
   * - ``success``
     - Boolean indicating whether the tool call succeeded
   * - ``execution_time_ms``
     - Execution time in milliseconds
   * - ``input_chars``
     - Number of characters in the tool input/arguments
   * - ``output_chars``
     - Number of characters in the tool output/result
   * - ``error_message``
     - Error message if the tool call failed (null on success)
   * - ``server_name``
     - MCP server name for MCP tools (e.g., ``filesystem``, ``command_line``)
   * - ``arguments_preview``
     - First 200 characters of tool arguments (for pattern analysis)
   * - ``output_preview``
     - First 200 characters of tool output (for debugging)
   * - ``round_number``
     - Which coordination round the tool was called in (0, 1, 2, ...)
   * - ``round_type``
     - Type of round: ``initial_answer``, ``voting``, ``presentation``

LLM API Call Attributes
~~~~~~~~~~~~~~~~~~~~~~~

All LLM API call spans include these attributes for agent attribution:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Attribute
     - Description
   * - ``massgen.agent_id``
     - The ID of the agent making the call
   * - ``llm.provider``
     - Provider name (``anthropic``, ``openai``, ``gemini``, etc.)
   * - ``llm.model``
     - Model being called (``claude-3-opus``, ``gpt-4o``, etc.)
   * - ``llm.operation``
     - API operation type (typically ``stream``)
   * - ``gen_ai.system``
     - OpenTelemetry semantic convention for provider
   * - ``gen_ai.request.model``
     - OpenTelemetry semantic convention for model

Example Logfire Queries
~~~~~~~~~~~~~~~~~~~~~~~

These attributes enable powerful filtering and analysis in the Logfire dashboard:

**Find slowest tool calls:**

.. code-block:: sql

   SELECT
     attributes->>'tool.name' as tool_name,
     (attributes->>'tool.execution_time_ms')::float as execution_time_ms,
     attributes->>'massgen.agent_id' as agent_id
   FROM records
   WHERE attributes->>'tool.type' = 'mcp'
   ORDER BY (attributes->>'tool.execution_time_ms')::float DESC

**Find failed tools with their arguments:**

.. code-block:: sql

   SELECT
     attributes->>'tool.name' as tool_name,
     attributes->>'tool.arguments_preview' as arguments_preview,
     attributes->>'tool.error_message' as error_message,
     attributes->>'massgen.agent_id' as agent_id
   FROM records
   WHERE attributes->>'tool.success' = 'false'

**Tools with large outputs (potential cost drivers):**

.. code-block:: sql

   SELECT
     attributes->>'mcp.server' as server_name,
     attributes->>'tool.name' as tool_name,
     (attributes->>'tool.output_chars')::int as output_chars,
     attributes->>'massgen.agent_id' as agent_id
   FROM records
   WHERE (attributes->>'tool.output_chars')::int > 10000
   ORDER BY (attributes->>'tool.output_chars')::int DESC

**Pattern analysis - which arguments lead to failures:**

.. code-block:: sql

   SELECT
     attributes->>'tool.arguments_preview' as arguments_preview,
     COUNT(*) as fail_count
   FROM records
   WHERE attributes->>'tool.success' = 'false'
   GROUP BY attributes->>'tool.arguments_preview'
   ORDER BY fail_count DESC

**Tool usage by MCP server:**

.. code-block:: sql

   SELECT
     attributes->>'mcp.server' as server_name,
     COUNT(*) as calls,
     AVG((attributes->>'tool.execution_time_ms')::float) as avg_time_ms
   FROM records
   WHERE attributes->>'tool.type' = 'mcp'
   GROUP BY attributes->>'mcp.server'

**LLM calls by agent:**

.. code-block:: sql

   SELECT
     attributes->>'massgen.agent_id' as agent_id,
     attributes->>'llm.model' as model,
     COUNT(*) as calls
   FROM records
   WHERE span_name LIKE 'llm.%'
   GROUP BY attributes->>'massgen.agent_id', attributes->>'llm.model'

**All activity for a specific agent:**

.. code-block:: sql

   SELECT span_name, start_timestamp, duration
   FROM records
   WHERE attributes->>'massgen.agent_id' = 'agent_a'
   ORDER BY start_timestamp

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Variable
     - Description
   * - ``MASSGEN_LOGFIRE_ENABLED``
     - Set to ``true`` to enable Logfire (alternative to ``--logfire`` flag)
   * - ``LOGFIRE_TOKEN``
     - Your Logfire API token (if not using ``logfire auth login``)
   * - ``LOGFIRE_SERVICE_NAME``
     - Override the service name (default: ``massgen``). Read by Logfire library.
   * - ``LOGFIRE_ENVIRONMENT``
     - Set environment tag (e.g., ``production``, ``development``). Read by Logfire library.
   * - ``OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT``
     - Set to ``true`` to capture Gemini prompts/completions (otherwise shows ``<elided>``)

Programmatic Usage
~~~~~~~~~~~~~~~~~~

When using MassGen as a library, you can configure Logfire programmatically:

.. code-block:: python

   from massgen.structured_logging import configure_observability

   # Enable observability with custom settings
   configure_observability(
       enabled=True,
       service_name="my-app",
       environment="production",
   )

   # Now run your orchestrator
   from massgen.orchestrator import Orchestrator
   orchestrator = Orchestrator(config)
   result = await orchestrator.run("Your question")

Graceful Degradation
~~~~~~~~~~~~~~~~~~~~

Logfire integration is designed to be non-intrusive:

* **No Logfire installed?** - Code runs normally without any errors
* **Logfire disabled?** - All logging falls back to standard loguru
* **Network issues?** - Logfire handles connectivity gracefully

This means you can always enable the ``--logfire`` flag without worrying about breaking your workflow - it will simply be ignored if Logfire is not configured.

See Also
--------

* :doc:`sessions/multi_turn_mode` - Session logging for interactive mode
* :doc:`files/file_operations` - Workspace and file operation logs
* :doc:`../reference/cli` - CLI options for logging control
