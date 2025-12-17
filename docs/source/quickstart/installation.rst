============
Installation
============

Prerequisites
=============

MassGen requires **Python 3.11 or higher**.

.. code-block:: bash

   python --version  # Should be 3.11+

Quick Install
=============

.. tabs::

   .. tab:: CLI

      .. code-block:: bash

         pip install uv                          # if needed
         uv venv && source .venv/bin/activate
         uv pip install massgen

   .. tab:: LiteLLM Integration

      .. code-block:: bash

         pip install uv                          # if needed
         uv venv && source .venv/bin/activate
         uv pip install massgen litellm python-dotenv

      Then in Python:

      .. code-block:: python

         from dotenv import load_dotenv
         load_dotenv()  # Load OPENROUTER_API_KEY from .env

         import litellm
         from massgen import register_with_litellm

         register_with_litellm()

         response = litellm.completion(
             model="massgen/build",
             messages=[{"role": "user", "content": "Hello!"}],
             optional_params={"models": ["openrouter/openai/gpt-5"]}
         )
         print(response.choices[0].message.content)

For programmatic Python usage, see the :doc:`../user_guide/integration/python_api`.

First Run Setup
===============

On first run, MassGen guides you through setup. Choose your preferred interface:

.. tabs::

   .. tab:: WebUI (Recommended)

      .. code-block:: bash

         uv run massgen --web

      The browser-based setup wizard will:

      1. **Configure API keys** - Enter keys for OpenAI, Anthropic, Google, etc.
      2. **Setup Docker** (optional) - For isolated code execution
      3. **Review Skills** - See available agent capabilities
      4. **Create your agent team** - Quickstart wizard for configuration

      This is the easiest way to get started - everything in one visual interface.

   .. tab:: CLI

      .. code-block:: bash

         uv run massgen

      The terminal wizard will:

      1. **Configure API keys** (OpenRouter recommended, or individual providers)
      2. **Create your agent team** (choose from templates or examples)
      3. **Launch interactive mode** immediately

Your configuration is saved to ``~/.config/massgen/config.yaml``.

API Keys
--------
API keys can be configured through webui or cli setup. However, they can also be setup through the terminal:

**OpenRouter (recommended):** Single API key for all models

.. code-block:: bash

   export OPENROUTER_API_KEY=sk-or-v1-...

**Or use individual providers:** OpenAI, Anthropic, Google Gemini, xAI (Grok), Azure OpenAI, Groq, Together AI, Fireworks, Cerebras

**Manual setup** (optional - wizard handles this):

.. code-block:: bash

   # Create .env file
   mkdir -p ~/.config/massgen
   echo "OPENROUTER_API_KEY=sk-or-v1-..." >> ~/.config/massgen/.env

Re-run Setup
------------

Re-configure anytime:

.. code-block:: bash

   uv run massgen --web         # WebUI setup page (visit /setup)
   uv run massgen --init        # CLI full configuration wizard
   uv run massgen --setup       # CLI just API keys
   uv run massgen --quickstart  # CLI quick 3-agent setup

Verify Installation
===================

.. code-block:: bash

   # Check CLI is available
   uv run massgen --help

   # List example configurations
   uv run massgen --list-examples

   # Run multi-agent collaboration
   uv run massgen --config @examples/basic/multi/three_agents_default "What is machine learning?"

Optional: Docker & Skills
=========================

For advanced features like isolated code execution:

.. code-block:: bash

   # Install Docker images
   uv run massgen --setup-docker

   # Install skills (semantic search, web scraping)
   uv run massgen --setup-skills

These are optional - basic MassGen works without them.

Development Installation
========================

For contributors or source code access:

.. code-block:: bash

   git clone https://github.com/Leezekun/MassGen.git
   cd MassGen
   pip install -e .

   # Or with full dev setup (Unix/macOS)
   ./scripts/init.sh

Next Steps
==========

.. grid:: 2
   :gutter: 3

   .. grid-item-card:: ▶️ Run MassGen

      See all usage modes

      :doc:`running-massgen`

   .. grid-item-card:: ⚙️ Configuration

      Create custom agent teams

      :doc:`configuration`

   .. grid-item-card:: 📚 Examples

      Ready-to-use configs

      :doc:`../examples/basic_examples`

   .. grid-item-card:: 🐍 Python API

      Programmatic integration

      :doc:`../user_guide/integration/python_api`

Troubleshooting
===============

**Python version error:**

.. code-block:: bash

   python --version  # Need 3.11+
   pip install --upgrade massgen

**API key not found:**

Check ``~/.config/massgen/.env`` exists with correct keys, or re-run ``massgen --init``.

**Setup wizard not appearing:**

Run ``massgen --init`` to manually trigger it.

For more help: `GitHub Issues <https://github.com/Leezekun/MassGen/issues>`_
