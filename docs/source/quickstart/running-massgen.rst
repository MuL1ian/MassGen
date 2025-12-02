Running MassGen
===============

This guide shows you how to run MassGen using different modes and configurations.

Choosing Your Mode
------------------

MassGen offers two primary ways to run multi-agent workflows:

.. list-table::
   :header-rows: 1
   :widths: 15 35 50

   * - Mode
     - Best For
     - Key Features
   * - **CLI**
     - Interactive exploration, quick experiments
     - Rich terminal UI, YAML configs, real-time visualization
   * - **LiteLLM**
     - Application integration, LangChain, existing LiteLLM users
     - Standard OpenAI interface, drop-in replacement

For advanced programmatic control, see the :doc:`../user_guide/integration/python_api` (async-first, headless execution).

Quick Start Examples
--------------------

.. tabs::

   .. tab:: CLI

      .. code-block:: bash

         # Multi-agent collaboration (recommended)
         uv run massgen --config @examples/basic/multi/three_agents_default "Analyze renewable energy"

         # Interactive mode (multi-turn)
         uv run massgen

   .. tab:: LiteLLM

      .. code-block:: python

         from dotenv import load_dotenv
         load_dotenv()  # Load OPENROUTER_API_KEY from .env

         import litellm
         from massgen import register_with_litellm

         register_with_litellm()

         # Multi-agent with multiple models (using OpenRouter)
         response = litellm.completion(
             model="massgen/build",
             messages=[{"role": "user", "content": "Analyze renewable energy"}],
             optional_params={"models": ["openrouter/openai/gpt-5", "openrouter/anthropic/claude-sonnet-4.5"]}
         )
         print(response.choices[0].message.content)

CLI Usage
---------

Basic Command Structure
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   uv run massgen [OPTIONS] ["<your question>"]

For the complete list of CLI options, see :doc:`../reference/cli`.

Multi-Agent Collaboration
~~~~~~~~~~~~~~~~~~~~~~~~~

MassGen is designed for multi-agent collaboration - multiple agents working together on complex tasks:

.. code-block:: bash

   # Three agents collaborate
   uv run massgen --config @examples/basic/multi/three_agents_default "Analyze the pros and cons of renewable energy"

The agents work in parallel, share observations, vote for solutions, and converge on the best answer.

Interactive Multi-Turn Mode
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Start without a question to enter interactive chat mode:

.. code-block:: bash

   # Interactive with multi-agent team
   uv run massgen --config @examples/basic/multi/three_agents_default

Features:

* Conversation context preserved across turns
* Session history saved in ``.massgen/sessions/``
* Real-time agent coordination visualization

See :doc:`../user_guide/sessions/multi_turn_mode` for the complete guide.

.. note::

   For programmatic Python access with async support and full control, see the :doc:`../user_guide/integration/python_api`.

LiteLLM Integration
-------------------

MassGen integrates with LiteLLM for a familiar OpenAI-compatible interface. Use OpenRouter to access multiple models with a single API key.

Setup
~~~~~

.. code-block:: python

   from dotenv import load_dotenv
   load_dotenv()  # Load OPENROUTER_API_KEY from .env

   import litellm
   from massgen import register_with_litellm

   # Register once at startup
   register_with_litellm()

Model String Formats
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Dynamic multi-agent with OpenRouter (recommended - single API key)
   response = litellm.completion(
       model="massgen/build",
       messages=[{"role": "user", "content": "Your question"}],
       optional_params={"models": ["openrouter/openai/gpt-5", "openrouter/anthropic/claude-sonnet-4.5"]}
   )
   print(response.choices[0].message.content)

   # Use example config
   response = litellm.completion(
       model="massgen/basic_multi",
       messages=[{"role": "user", "content": "Your question"}]
   )
   print(response.choices[0].message.content)

Access MassGen Metadata
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # MassGen-specific metadata
   metadata = response._hidden_params
   print(metadata.get("massgen_vote_results"))
   print(metadata.get("massgen_answers"))

See :doc:`../user_guide/integration/python_api` for complete LiteLLM documentation.

Adding Tools
------------

MCP Integration
~~~~~~~~~~~~~~~

Add external tools via Model Context Protocol:

.. tabs::

   .. tab:: CLI

      .. code-block:: bash

         uv run massgen --config @examples/tools/mcp/gpt5_nano_mcp_example.yaml \
           "What's the weather in New York?"

   .. tab:: YAML Config

      .. code-block:: yaml

         agents:
           - id: "agent_with_tools"
             backend:
               type: "openai"
               model: "openrouter/openai/gpt-5"
             mcp_servers:
               - command: "npx"
                 args: ["-y", "@modelcontextprotocol/server-weather"]

See :doc:`../user_guide/tools/mcp_integration` for details.

File Operations
~~~~~~~~~~~~~~~

Agents can work with files in isolated workspaces:

.. tabs::

   .. tab:: CLI

      .. code-block:: bash

         uv run massgen --config @examples/tools/filesystem/claude_code_single.yaml \
           "Create a Python web scraper and save results to CSV"

   .. tab:: YAML Config

      .. code-block:: yaml

         orchestrator:
           file_system:
             enabled: true
             use_docker: false

See :doc:`../user_guide/files/file_operations` for details.

Configuration Paths
-------------------

MassGen supports multiple ways to specify configurations:

.. code-block:: bash

   # Built-in examples (works from any directory)
   uv run massgen --config @examples/basic/multi/three_agents_default "Question"

   # List all examples
   uv run massgen --list-examples

   # Custom file (relative or absolute path)
   uv run massgen --config ./my-config.yaml "Question"

   # User config directory
   uv run massgen --config my-saved-config "Question"
   # Looks for ~/.config/massgen/agents/my-saved-config.yaml

Viewing Results
---------------

By default, MassGen shows a rich terminal UI. Control the display:

.. code-block:: bash

   # Disable UI (quiet mode)
   uv run massgen --no-display --config config.yaml "Question"

   # Enable debug logging
   uv run massgen --debug --config config.yaml "Question"

Next Steps
----------

.. grid:: 2
   :gutter: 3

   .. grid-item-card:: ⚙️ Configuration

      Create custom agent teams

      :doc:`configuration`

   .. grid-item-card:: 📚 Core Concepts

      Understand multi-agent coordination

      :doc:`../user_guide/concepts`

   .. grid-item-card:: 🐍 Python API

      Full programmatic control

      :doc:`../user_guide/integration/python_api`

   .. grid-item-card:: 🔌 Tools & MCP

      Add capabilities to agents

      :doc:`../user_guide/tools/index`
