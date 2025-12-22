=========================
Python API & LiteLLM
=========================

MassGen provides two ways to integrate into your Python applications:

1. **LiteLLM Integration** (Recommended) - OpenAI-compatible interface, works with 100+ providers
2. **Direct Python API** - Async-first API with ``massgen.run()`` and ``massgen.build_config()``

.. note::
   **For Contributors:** Looking for internal API documentation? See :doc:`../api/index` for developer API reference of classes and modules.

.. contents:: On This Page
   :local:
   :depth: 2

LiteLLM Integration
===================

The easiest way to use MassGen programmatically. Works with existing LiteLLM-based code.

Quick Start
-----------

.. code-block:: python

   from dotenv import load_dotenv
   load_dotenv()  # Load API keys from .env

   import litellm
   from massgen import register_with_litellm

   # Register MassGen as a provider (call once at startup)
   register_with_litellm()

   # Multi-agent with different models
   response = litellm.completion(
       model="massgen/build",
       messages=[{"role": "user", "content": "What is machine learning?"}],
       optional_params={
           "models": ["openai/gpt-5", "anthropic/claude-sonnet-4-5-20250929"],
       }
   )
   print(response.choices[0].message.content)

Model String Format
-------------------

- ``massgen/build`` - Build config dynamically from ``optional_params`` (most flexible)
- ``massgen/<example-name>`` - Use built-in example config
- ``massgen/model:<model-name>`` - Quick single-agent mode
- ``massgen/path:<config-path>`` - Explicit config file path

Optional Parameters
-------------------

Pass MassGen-specific options via ``optional_params``:

+----------------------+------------------+----------------------------------------------------+
| Parameter            | Type             | Description                                        |
+======================+==================+====================================================+
| ``models``           | list[str]        | List of models for multi-agent                     |
|                      |                  | (e.g., ``["gpt-5", "claude-sonnet-4-5-20250929"]``)|
+----------------------+------------------+----------------------------------------------------+
| ``model``            | str              | Single model name for all agents                   |
+----------------------+------------------+----------------------------------------------------+
| ``num_agents``       | int              | Number of agents when using single model           |
+----------------------+------------------+----------------------------------------------------+
| ``enable_filesystem``| bool             | Enable filesystem/MCP tools (default: True)        |
+----------------------+------------------+----------------------------------------------------+
| ``context_paths``    | list             | Paths with permissions for file operations         |
+----------------------+------------------+----------------------------------------------------+
| ``use_docker``       | bool             | Enable Docker execution mode (default: False)      |
+----------------------+------------------+----------------------------------------------------+
| ``enable_logging``   | bool             | Enable logging and return log directory            |
+----------------------+------------------+----------------------------------------------------+
| ``output_file``      | str              | Write final answer to this file path               |
+----------------------+------------------+----------------------------------------------------+

Examples
--------

.. code-block:: python

   # Multi-agent with filesystem access
   response = litellm.completion(
       model="massgen/build",
       messages=[{"role": "user", "content": "Read the config and summarize"}],
       optional_params={
           "model": "gpt-5",
           "context_paths": [
               {"path": "/path/to/project", "permission": "read"},
               {"path": "/path/to/output", "permission": "write"},
           ],
       }
   )

   # Lightweight mode (no filesystem, faster for simple queries)
   response = litellm.completion(
       model="massgen/build",
       messages=[{"role": "user", "content": "What is 2+2?"}],
       optional_params={
           "model": "gpt-5-nano",
           "enable_filesystem": False,
       }
   )

   # Access coordination metadata
   metadata = response._hidden_params
   print(f"Winner: {metadata.get('massgen_selected_agent')}")
   print(f"Votes: {metadata.get('massgen_vote_results', {}).get('vote_counts')}")

For complete LiteLLM examples, see :doc:`../user_guide/integration/python_api`.

Direct Python API
=================

For async workflows or more control, use ``massgen.run()`` directly.

.. code-block:: python

   import asyncio
   import massgen

   async def main():
       # Single agent with filesystem support (default)
       result = await massgen.run(
           query="What is machine learning?",
           model="gpt-5"
       )
       print(result['final_answer'])

       # Multi-agent mode
       result = await massgen.run(
           query="Compare approaches",
           models=["gpt-5", "claude-sonnet-4-5-20250929"]
       )
       print(result['final_answer'])

       # Lightweight mode (no filesystem)
       result = await massgen.run(
           query="What is 2+2?",
           model="gpt-5-nano",
           enable_filesystem=False
       )
       print(result['final_answer'])

   asyncio.run(main())

API Reference
=============

massgen.run()
-------------

.. code-block:: python

   async def run(
       query: str,
       config: str = None,
       model: str = None,
       models: list = None,
       num_agents: int = None,
       use_docker: bool = False,
       enable_filesystem: bool = True,
       enable_logging: bool = False,
       output_file: str = None,
       **kwargs
   ) -> dict

**Parameters:**

- ``query`` (str): The question or task for the agent(s)
- ``config`` (str, optional): Config file path or ``@examples/NAME``
- ``model`` (str, optional): Model name for agents
- ``models`` (list, optional): List of models for multi-agent mode
- ``num_agents`` (int, optional): Number of agents when using single model
- ``use_docker`` (bool): Enable Docker execution (default: False)
- ``enable_filesystem`` (bool): Enable filesystem/MCP tools (default: True)
- ``enable_logging`` (bool): Enable logging (default: False)
- ``output_file`` (str, optional): Write final answer to file
- ``context_paths`` (list, optional): Paths with permissions for file operations

**Returns:**

.. code-block:: python

   {
       'final_answer': str,        # The generated answer
       'config_used': str,         # Config path or description
       'session_id': str,          # Session ID
       'selected_agent': str,      # Winner (multi-agent)
       'vote_results': dict,       # Voting details
       'answers': list,            # All agent answers
   }

Usage Patterns
==============

Single Agent Mode
-----------------

For simple queries with a single agent:

.. code-block:: python

   import asyncio
   import massgen

   async def single_agent_query():
       result = await massgen.run(
           query="What are the benefits of renewable energy?",
           model="gpt-5-mini"
       )
       return result['final_answer']

   answer = asyncio.run(single_agent_query())
   print(answer)

**Supported Models:**

- OpenAI: ``gpt-5``, ``gpt-5-mini``, ``gpt-5-nano``, ``gpt-4o``, ``o1``
- Anthropic: ``claude-sonnet-4``, ``claude-opus-4``
- Google: ``gemini-2.5-flash``, ``gemini-2.5-pro``, ``gemini-2.0-flash``
- xAI: ``grok-4``, ``grok-4-fast-reasoning``

See :doc:`supported_models` for the complete list.

Multi-Agent with Configuration
-------------------------------

For complex queries requiring multiple agents:

.. code-block:: python

   import asyncio
   import massgen

   async def multi_agent_research():
       result = await massgen.run(
           query="Compare renewable energy sources with analysis",
           config="@examples/research_team"
       )
       return result

   result = asyncio.run(multi_agent_research())
   print(result['final_answer'])
   print(f"Config: {result['config_used']}")

**Built-in Example Configurations:**

Use the ``@examples/`` prefix to access built-in configurations:

- ``@examples/basic/single/single_gpt5nano`` - Single agent configuration
- ``@examples/basic/multi/three_agents_default`` - Three-agent basic setup
- ``@examples/research_team`` - Research-focused agents with web search
- ``@examples/coding_team`` - Code generation with multiple agents

List all available examples:

.. code-block:: bash

   massgen --list-examples

Default Configuration
---------------------

Use your default configuration (from the setup wizard):

.. code-block:: python

   import asyncio
   import massgen

   async def use_default_config():
       # No config or model specified - uses ~/.config/massgen/config.yaml
       result = await massgen.run(
           query="Analyze the impact of AI on healthcare"
       )
       return result['final_answer']

   answer = asyncio.run(use_default_config())
   print(answer)

Custom Configuration Files
---------------------------

Use your own YAML configuration files:

.. code-block:: python

   import asyncio
   import massgen

   async def custom_config():
       result = await massgen.run(
           query="Your question",
           config="./my-agents.yaml"  # Relative path
       )
       return result

   # Or absolute path
   async def custom_config_abs():
       result = await massgen.run(
           query="Your question",
           config="/path/to/my-agents.yaml"
       )
       return result

Named Configurations
--------------------

Use named configurations from ``~/.config/massgen/agents/``:

.. code-block:: python

   import asyncio
   import massgen

   async def named_config():
       # Looks for ~/.config/massgen/agents/research-team.yaml
       result = await massgen.run(
           query="Research question",
           config="research-team"  # No .yaml extension needed
       )
       return result

   answer = asyncio.run(named_config())
   print(answer)

Advanced Usage
==============

Async/Await Patterns
--------------------

Since MassGen is async-native, you can integrate it into async applications:

.. code-block:: python

   import asyncio
   import massgen

   async def process_multiple_queries():
       # Run multiple queries concurrently
       queries = [
           "What is AI?",
           "Explain machine learning",
           "Define neural networks"
       ]

       tasks = [
           massgen.run(query=q, model="gpt-5-mini")
           for q in queries
       ]

       results = await asyncio.gather(*tasks)

       for query, result in zip(queries, results):
           print(f"Q: {query}")
           print(f"A: {result['final_answer']}\n")

   asyncio.run(process_multiple_queries())

Integration with FastAPI
------------------------

MassGen works seamlessly with FastAPI:

.. code-block:: python

   from fastapi import FastAPI
   import massgen

   app = FastAPI()

   @app.post("/query")
   async def handle_query(question: str, model: str = "gpt-5-mini"):
       result = await massgen.run(
           query=question,
           model=model
       )
       return {
           "question": question,
           "answer": result['final_answer'],
           "config": result['config_used']
       }

   # Run with: uvicorn myapp:app

Integration with Jupyter Notebooks
-----------------------------------

MassGen works great in Jupyter notebooks:

.. code-block:: python

   # In a Jupyter cell
   import massgen

   # Jupyter handles the event loop for you
   result = await massgen.run(
       query="Explain photosynthesis",
       model="gemini-2.5-flash"
   )

   print(result['final_answer'])

   # Or create an explicit async cell
   async def research_query():
       return await massgen.run(
           query="Compare programming paradigms",
           config="@examples/research_team"
       )

   result = await research_query()
   print(result['final_answer'])

Error Handling
--------------

Handle errors gracefully:

.. code-block:: python

   import asyncio
   import massgen

   async def safe_query():
       try:
           result = await massgen.run(
               query="Your question",
               model="gpt-5-mini"
           )
           return result['final_answer']

       except ValueError as e:
           print(f"Configuration error: {e}")
           # E.g., config not found, no API key

       except Exception as e:
           print(f"Unexpected error: {e}")
           return None

   answer = asyncio.run(safe_query())

Common Errors
=============

No Configuration Found
----------------------

.. code-block:: python

   ValueError: No config specified and no default config found.
   Run `massgen --init` to create a default configuration.

**Solution:** Run the setup wizard to create a default config:

.. code-block:: bash

   massgen --init

Or specify a config explicitly:

.. code-block:: python

   result = await massgen.run(query="...", config="@examples/basic/multi/three_agents_default")

API Key Not Found
-----------------

If you see API key errors, ensure your keys are configured:

1. Set environment variables:

   .. code-block:: bash

      export OPENAI_API_KEY="sk-..."
      export ANTHROPIC_API_KEY="sk-ant-..."

2. Or create ``~/.config/massgen/.env``:

   .. code-block:: bash

      OPENAI_API_KEY=sk-...
      ANTHROPIC_API_KEY=sk-ant-...

Config Not Found
----------------

.. code-block:: python

   ConfigurationError: Configuration file not found: my-config

**Solution:** Check the config path exists, or use ``@examples/`` for built-in configs.

Best Practices
==============

1. **Use Async/Await Properly**

   .. code-block:: python

      # Good
      result = await massgen.run(query="...")

      # Bad (won't work)
      result = massgen.run(query="...")  # Missing await

2. **Handle Errors**

   Always wrap API calls in try/except blocks for production code.

3. **Reuse Configurations**

   Create named configurations for common use cases:

   .. code-block:: python

      # Save to ~/.config/massgen/agents/research.yaml
      # Then reuse:
      result = await massgen.run(query="...", config="research")

4. **Use Single-Agent Mode for Simple Queries**

   For straightforward questions, single-agent mode is faster:

   .. code-block:: python

      result = await massgen.run(
          query="Quick question",
          model="gpt-5-mini"  # Fast and cheap
      )

5. **Use Multi-Agent Mode for Complex Analysis**

   For research, comparison, or analysis:

   .. code-block:: python

      result = await massgen.run(
          query="Compare X and Y",
          config="@examples/research_team"
      )

See Also
========

- :doc:`../quickstart/installation` - Installation and setup
- :doc:`../quickstart/configuration` - Configuration file format
- :doc:`cli` - Command-line interface reference
- :doc:`supported_models` - Supported models and backends
- :doc:`yaml_schema` - YAML configuration schema
