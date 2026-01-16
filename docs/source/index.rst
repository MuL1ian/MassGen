=================================================
MassGen: Multi-Agent Scaling System for GenAI
=================================================

.. raw:: html

   <img src="_static/images/logo.png" width="360" alt="MassGen Logo" class="theme-image-light">
   <img src="_static/images/logo-dark.png" width="360" alt="MassGen Logo" class="theme-image-dark">

.. raw:: html

   <p align="center">
     <a href="https://pypi.org/project/massgen/">
       <img src="https://img.shields.io/pypi/v/massgen?style=flat-square&logo=pypi&logoColor=white&label=PyPI&color=3775A9" alt="PyPI">
     </a>
     <a href="https://github.com/Leezekun/MassGen">
       <img src="https://img.shields.io/github/stars/Leezekun/MassGen?style=flat-square&logo=github&color=181717&logoColor=white" alt="GitHub Stars">
     </a>
     <a href="https://www.python.org/downloads/">
       <img src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+">
     </a>
     <a href="https://github.com/Leezekun/MassGen/blob/main/LICENSE">
       <img src="https://img.shields.io/badge/license-Apache%202.0-green?style=flat-square" alt="License">
     </a>
   </p>

   <p align="center">
     <a href="https://x.massgen.ai">
       <img src="https://img.shields.io/badge/FOLLOW%20ON%20X-000000?style=for-the-badge&logo=x&logoColor=white" alt="Follow on X">
     </a>
     <a href="https://www.linkedin.com/company/massgen-ai">
       <img src="https://img.shields.io/badge/FOLLOW%20ON%20LINKEDIN-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white" alt="Follow on LinkedIn">
     </a>
     <a href="https://discord.massgen.ai">
       <img src="https://img.shields.io/badge/JOIN%20OUR%20DISCORD-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Join our Discord">
     </a>
   </p>

|

.. raw:: html

   <a href="https://www.youtube.com/watch?v=Dp2oldJJImw" style="display: block; text-align: center;">
     <img src="_static/images/readme.gif" width="800" alt="MassGen Demo - Multi-agent collaboration in action" class="theme-image-light">
     <img src="_static/images/readme.gif" width="800" alt="MassGen Demo - Multi-agent collaboration in action" class="theme-image-dark">
   </a>

What is MassGen?
----------------

MassGen is a cutting-edge multi-agent system that leverages the power of collaborative AI to solve complex tasks. It assigns a task to multiple AI agents who work in parallel, observe each other's progress, and refine their approaches to converge on the best solution to deliver a comprehensive and high-quality result.

**How It Works:**

* **Work in Parallel** - Multiple agents tackle the problem simultaneously, each bringing unique capabilities
* **See Recent Answers** - At each step, agents view the most recent answers from other agents
* **Decide Next Action** - Each agent chooses to provide a new answer or vote for an existing answer
* **Share Workspaces** - When agents provide answers, their workspace is captured so others can review their work
* **Natural Consensus** - Coordination continues until all agents vote, then the agent with most votes presents the final answer

Think of it as a "parallel study group" for AI - inspired by advanced systems like **xAI's Grok Heavy** and **Google DeepMind's Gemini Deep Think**. Agents learn from each other to produce better results than any single agent could achieve alone.


How Does MassGen Compare?
-------------------------

**MassGen vs LLM Council:** While LLM Council follows a fixed 3-stage pipeline, MassGen agents autonomously decide to contribute new answers or vote for others, reaching consensus organically. Plus, MassGen agents can use tools, execute code, and read/write files in your codebase — backed by active development with regular releases. :doc:`See full comparison → <reference/comparisons>`


Quick Start
-----------

.. tabs::

   .. tab:: CLI

      .. code-block:: bash

         pip install uv        # if needed
         uv venv && source .venv/bin/activate
         uv pip install massgen
         uv run massgen        # Setup wizard, then ask your first question

      Rich terminal UI with real-time streaming, multi-turn conversations, and YAML configuration.

   .. tab:: WebUI

      .. code-block:: bash

         pip install uv        # if needed
         uv venv && source .venv/bin/activate
         uv pip install massgen
         uv run massgen --web  # Open http://localhost:8000

      Browser-based UI with real-time agent streaming, vote visualization, and workspace browsing.

   .. tab:: LiteLLM

      .. code-block:: python

         from dotenv import load_dotenv
         load_dotenv()  # Load OPENROUTER_API_KEY from .env

         import litellm
         from massgen import register_with_litellm

         register_with_litellm()
         response = litellm.completion(
             model="massgen/build",
             messages=[{"role": "user", "content": "Your question"}],
             optional_params={"models": ["openrouter/openai/gpt-5", "openrouter/anthropic/claude-sonnet-4.5"]}
         )
         print(response.choices[0].message.content)

      Standard OpenAI-compatible interface for seamless integration with existing applications.

:doc:`quickstart/installation` · :doc:`quickstart/running-massgen` · :doc:`quickstart/configuration`

Key Features
------------

.. grid:: 2
   :gutter: 3

   .. grid-item-card:: 🤝 Cross-Model Synergy

      Use Claude, Gemini, GPT, Grok together - each agent can use a different model.

   .. grid-item-card:: ⚡ Parallel Coordination

      Multiple agents work simultaneously with voting and consensus detection.

   .. grid-item-card:: 🛠️ Tools & MCP

      Model Context Protocol for web search, code execution, file operations, and custom tools.

   .. grid-item-card:: 🐍 Python & LiteLLM

      Full async Python API and LiteLLM integration for seamless application embedding.

   .. grid-item-card:: 📊 Live Visualization

      Real-time terminal display showing agents' working processes and coordination.

   .. grid-item-card:: 💬 Multi-Turn Sessions

      Interactive conversations with context preservation across turns.

   .. grid-item-card:: 🔗 Framework Interoperability

      Integrate external frameworks (AG2, LangGraph, AgentScope, OpenAI, SmolAgent) as tools.

   .. grid-item-card:: 📁 Project Integration

      Work directly with your codebase using context paths with granular read/write permissions.

Recent Releases
---------------

**v0.1.39 (January 16, 2026)** - Plan and Execute Workflow

Complete plan-then-execute workflow with ``--plan-and-execute`` for autonomous planning and execution, ``--execute-plan`` to run existing plans. Task verification workflow with ``verified`` status and verification groups for batch validation. Plan storage system in ``.massgen/plans/`` with frozen snapshots and execution tracking. Response API function call message sanitization fixes.

**v0.1.38 (January 15, 2026)** - Task Planning Mode & Two-Tier Workspace

Create structured plans with ``--plan`` flag and ``--plan-depth`` (shallow/medium/deep) for future workflows (plan-only, no auto-execution). Git-backed two-tier workspace separates scratch exploration from final deliverables. Automatic ``CLAUDE.md`` and ``AGENTS.md`` discovery for project context. Batch image analysis with ``read_media`` tool. Reliability fixes: circuit breaker for infinite loops, timeout race conditions, MCP tool restoration.

**v0.1.37 (January 12, 2026)** - Execution Traces & Thinking Mode Improvements

Full execution history preserved as searchable ``execution_trace.md`` files alongside agent snapshots. Agents can read trace files to recover detailed history after context compression. Claude Code and Gemini thinking mode streaming buffer integration. Standardized agent labeling across all backends.

:doc:`Full changelog → <changelog>`

Supported Models
----------------

**Claude** (Anthropic) · **Gemini** (Google) · **GPT** (OpenAI) · **Grok** (xAI) · **Azure OpenAI** · **Groq** · **Together** · **LM Studio** · :doc:`and more... <reference/supported_models>`

Documentation
-------------

.. grid:: 3
   :gutter: 2

   .. grid-item-card:: 🚀 Getting Started

      * :doc:`quickstart/installation`
      * :doc:`quickstart/running-massgen`
      * :doc:`quickstart/configuration`

   .. grid-item-card:: 📖 User Guide

      * :doc:`user_guide/concepts`
      * :doc:`user_guide/webui`
      * :doc:`user_guide/tools/index`
      * :doc:`user_guide/integration/index`

   .. grid-item-card:: 📚 Reference

      * :doc:`reference/cli`
      * :doc:`reference/python_api`
      * :doc:`reference/yaml_schema`
      * :doc:`examples/basic_examples`

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Getting Started

   quickstart/installation
   quickstart/running-massgen
   quickstart/configuration

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: User Guide

   user_guide/concepts
   user_guide/task_planning
   user_guide/backends
   user_guide/webui
   user_guide/tools/index
   user_guide/files/index
   user_guide/sessions/index
   user_guide/integration/index
   user_guide/advanced/index
   user_guide/validating_configs
   user_guide/logging

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Reference

   reference/python_api
   reference/cli
   reference/yaml_schema
   reference/mcp_server_registry
   reference/configuration_examples
   reference/timeouts
   reference/supported_models
   reference/comparisons
   glossary

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Examples

   examples/case_studies
   examples/basic_examples
   examples/advanced_patterns
   examples/available_configs

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Development

   development/contributing
   development/writing_configs
   development/architecture
   development/roadmap
   changelog
   api/index
