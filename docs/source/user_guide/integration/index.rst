Integration & Automation
========================

This section covers how to integrate MassGen into your applications and automate workflows. MassGen offers multiple integration paths for different use cases.

Choosing Your Integration
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Method
     - Best For
     - Key Features
   * - **Python API**
     - Application integration, automation scripts
     - Async-first, full control, direct access
   * - **LiteLLM**
     - Existing LiteLLM users, LangChain integration
     - OpenAI-compatible, drop-in replacement
   * - **Automation Mode**
     - Background execution, CI/CD pipelines
     - Headless, non-interactive, scriptable

Guides in This Section
----------------------

.. grid:: 3
   :gutter: 3

   .. grid-item-card:: 🐍 Python API

      Direct Python integration

      * ``massgen.run()`` async API
      * ``massgen.build_config()`` programmatic config
      * LiteLLM provider registration
      * Full control over execution

      :doc:`Read the Python API guide → <python_api>`

   .. grid-item-card:: 🤖 Automation

      Headless execution

      * Background execution
      * CI/CD integration
      * Status file monitoring
      * Non-interactive mode

      :doc:`Read the Automation guide → <automation>`

   .. grid-item-card:: 🔗 Framework Interoperability

      External frameworks

      * AG2 framework integration
      * LangChain compatibility
      * Custom backends
      * External tools

      :doc:`Read the Interoperability guide → <general_interoperability>`

Quick Examples
--------------

.. tabs::

   .. tab:: Python API

      .. code-block:: python

         import asyncio
         import massgen

         async def main():
             result = await massgen.run(
                 query="Analyze this problem",
                 models=["gpt-5", "claude-sonnet-4-5-20250929"]
             )
             print(result["final_answer"])

         asyncio.run(main())

   .. tab:: LiteLLM

      .. code-block:: python

         import litellm
         from massgen import register_with_litellm

         register_with_litellm()

         response = litellm.completion(
             model="massgen/build",
             messages=[{"role": "user", "content": "Your question"}],
             optional_params={"models": ["openai/gpt-5", "anthropic/claude-sonnet-4-5-20250929"]}
         )
         print(response.choices[0].message.content)

   .. tab:: Automation CLI

      .. code-block:: bash

         # Run in automation mode (headless)
         massgen --automation --model gpt-5 "Your question"

         # Monitor with status file
         massgen --automation --status-file status.json "Your query"

Related Documentation
---------------------

* :doc:`../../quickstart/running-massgen` - Getting started
* :doc:`../../reference/python_api` - API reference
* :doc:`../../reference/cli` - CLI reference
* :doc:`../tools/index` - Available tools

.. toctree::
   :maxdepth: 1
   :hidden:

   python_api
   automation
   general_interoperability
