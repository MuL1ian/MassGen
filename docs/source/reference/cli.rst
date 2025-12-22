CLI Reference
=============

MassGen Command Line Interface reference.

Basic Usage
-----------

.. code-block:: bash

   massgen [OPTIONS] ["<your question>"]

**Default Behavior (No Arguments):**

When running ``massgen`` with no arguments, configs are auto-discovered with this priority:

1. ``.massgen/config.yaml`` (project-level config in current directory)
2. ``~/.config/massgen/config.yaml`` (global default config)
3. Launch setup wizard if no config found

**First-Time Setup:**

The wizard consists of two steps:

1. **API Key Setup** (if no cloud provider keys detected)

   * Prompts for OpenAI, Anthropic, Google, or other cloud provider API keys
   * Saves to ``~/.config/massgen/.env``
   * Skipped if keys already exist

2. **Configuration Setup**

   * Option to browse ready-to-use configs/examples
   * Option to build from templates (Simple Q&A, Research, Code & Files, etc.)
   * Asks "Save as default?" when browsing existing configs
   * Launches directly into interactive mode

**After Setup:**

* **No arguments** → Starts multi-turn conversation mode if default config chosen
* **With question** → Runs single query using default config

CLI Parameters
--------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Parameter
     - Description
   * - ``--config PATH``
     - Path to YAML configuration file with agent definitions, model parameters, backend parameters and UI settings
   * - ``--select``
     - Interactively select from available configurations (user configs, project configs, current directory, package examples). Uses hierarchical navigation: category → config
   * - ``--backend TYPE``
     - Backend type for quick setup without config file. Options: ``claude``, ``claude_code``, ``gemini``, ``grok``, ``openai``, ``azure_openai``, ``zai``
   * - ``--model NAME``
     - Model name for quick setup (e.g., ``gemini-2.5-flash``, ``gpt-5-nano``). Mutually exclusive with ``--config``
   * - ``--system-message TEXT``
     - System prompt for the agent in quick setup mode. Omitted if ``--config`` is provided
   * - ``--no-display``
     - Disable real-time streaming UI coordination display (fallback to simple text output)
   * - ``--no-logs``
     - Disable real-time logging
   * - ``--debug``
     - Enable debug mode with verbose logging. Debug logs saved to ``agent_outputs/log_{time}/massgen_debug.log``
   * - ``--session-id ID``
     - Load memory from a previous session by ID (e.g., ``session_20251028_143000``). Allows continuing conversations with memory context from prior runs. Use with ``--list-sessions`` to find available sessions
   * - ``--list-sessions``
     - List all available memory sessions with their metadata (session IDs, timestamps, models, status). Sessions are automatically tracked in ``~/.massgen/sessions.json``
   * - ``--web``
     - Start the WebUI server instead of the terminal UI. Opens a browser-based interface with real-time agent streaming, vote visualization, and workspace browsing
   * - ``--web-host HOST``
     - Host address for the WebUI server (default: ``127.0.0.1``). Use ``0.0.0.0`` to allow external connections
   * - ``--web-port PORT``
     - Port for the WebUI server (default: ``8000``)
   * - ``--no-browser``
     - Don't auto-open browser when using ``--web`` with a question. Useful for automation or when running on servers
   * - ``--output-file PATH``
     - Write final answer to specified file path. Works in any mode (automation, interactive, etc.). Useful for capturing agent responses in scripts or pipelines
   * - ``"<your question>"``
     - Optional single-question input. If omitted, MassGen enters interactive chat mode

Examples
--------

Default Configuration Mode
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # First time: Launch setup wizard
   massgen

   # After setup: Start interactive conversation
   massgen

   # Run single query with default config
   massgen "What is machine learning?"

Interactive Config Selection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Browse and select from available configurations
   massgen --select

   # After selection, optionally provide a question
   massgen --select "Your question here"

   # The selector shows configs from:
   # - User configs: ~/.config/massgen/agents/
   # - Project configs: .massgen/*.yaml
   # - Current directory: *.yaml
   # - Package examples: Built-in example configs

Quick Single Agent
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Fastest way to test - no config file
   massgen --model claude-3-5-sonnet-latest "What is machine learning?"
   massgen --model gemini-2.5-flash "Explain quantum computing"

With Specific Backend
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   massgen \
     --backend gemini \
     --model gemini-2.5-flash \
     "What are the latest developments in AI?"

Multi-Agent with Config
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Recommended: Use YAML config for multi-agent
   massgen \
     --config @examples/basic/multi/three_agents_default.yaml \
     "Analyze the pros and cons of renewable energy"

Interactive Mode
~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Omit question to enter interactive chat mode
   massgen --model gemini-2.5-flash

   # Multi-agent interactive
   massgen \
     --config @examples/basic/multi/three_agents_default.yaml

Debug Mode
~~~~~~~~~~

.. code-block:: bash

   massgen \
     --debug \
     --config @examples/basic/multi/three_agents_default.yaml \
     "Your question here"

Disable UI
~~~~~~~~~~

.. code-block:: bash

   # Simple text output instead of rich terminal UI
   massgen \
     --no-display \
     --config config.yaml \
     "Question"

Session Management
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # List available memory sessions
   massgen --list-sessions

   # Load session from previous run
   massgen --session-id session_20251028_143000 \
     "What did we discuss about the backend architecture?"

   # Interactive mode with previous session
   massgen --session-id session_20251028_143000 \
     --config my_config.yaml

   # Session can also be specified in YAML config
   # Add to your config.yaml:
   #   session_id: "session_20251028_143000"

WebUI Mode
~~~~~~~~~~

.. code-block:: bash

   # Start WebUI on default localhost:8000
   massgen --web

   # Custom host and port (for external access)
   massgen --web --web-host 0.0.0.0 --web-port 3000

   # With a specific config
   massgen --web --config @examples/basic/multi/three_agents_default

   # Combine with debug mode
   massgen --web --debug --config my_config.yaml

Output to File
~~~~~~~~~~~~~~

.. code-block:: bash

   # Save agent response to a file
   massgen --output-file results.txt "Summarize the key points of machine learning"

   # With config and output file
   massgen --config my_config.yaml --output-file report.md "Generate a project report"


Additional Commands
-------------------

Log Analysis (``massgen logs``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Analyze and browse session logs without manual file navigation.

.. code-block:: bash

   # Summary of most recent run
   massgen logs

   # Full tool breakdown
   massgen logs tools

   # List recent runs
   massgen logs list

   # Open log directory in file manager
   massgen logs open

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Subcommand
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
     - Open log directory in system file manager

**Options:**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Option
     - Description
   * - ``--log-dir PATH``
     - Analyze a specific log directory instead of the most recent
   * - ``--json``
     - Output raw JSON for scripting

Share Session (``massgen export``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Share a session via GitHub Gist for easy collaboration.

.. code-block:: bash

   # Share the most recent session
   massgen export

   # Share a specific session
   massgen export log_20251218_134125_867383

**Prerequisites:** Requires GitHub CLI (``gh``) to be installed and authenticated.

.. code-block:: bash

   # Install gh (macOS)
   brew install gh

   # Authenticate
   gh auth login

**Output:**

.. code-block:: text

   Sharing session from: .massgen/massgen_logs/log_20251218_134125/turn_1/attempt_1
   Collecting files...
   Uploading 45 files (1,234,567 bytes)...

   Share URL: https://massgen.github.io/MassGen-Viewer/?gist=abc123def456

   Anyone with this link can view the session (no login required).

The URL opens the MassGen Viewer with the session's coordination timeline, answers, votes, and tool usage.

Manage Shared Sessions (``massgen shares``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

List and manage your shared sessions.

.. code-block:: bash

   # List your shared sessions
   massgen shares list

   # Delete a shared session
   massgen shares delete <gist_id>

See Also
--------

* :doc:`../quickstart/running-massgen` - Detailed usage examples
* :doc:`yaml_schema` - YAML configuration reference
* :doc:`supported_models` - Available models and backends
* :doc:`../user_guide/logging` - Complete logging and debugging guide
