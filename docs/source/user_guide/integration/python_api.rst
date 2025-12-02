=============================
Programmatic API Guide
=============================

This guide shows how to use MassGen programmatically from Python code, including direct Python API usage and LiteLLM integration.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
========

MassGen provides multiple ways to integrate into your Python applications:

1. **Direct Python API** - Use ``massgen.run()`` for simple programmatic access
2. **LiteLLM Integration** - Use MassGen as a LiteLLM custom provider
3. **CLI with --output-file** - Save results directly to a file for batch processing

Quick Start
===========

LiteLLM Integration (Recommended)
---------------------------------

.. note::
   Token counting and pricing are not yet supported in the LiteLLM integration.
   The ``usage`` field in responses will show zeros. This feature is planned for a future release.

Copy-paste ready example for using MassGen with LiteLLM:

.. code-block:: python

   from dotenv import load_dotenv
   load_dotenv()  # Load API keys from .env file

   import litellm
   from massgen import register_with_litellm

   # Register MassGen as a provider (call once at startup)
   register_with_litellm()

   # Run multi-agent with different models (slash format: backend/model)
   response = litellm.completion(
       model="massgen/build",
       messages=[{"role": "user", "content": "What is machine learning?"}],
       optional_params={
           "models": [
               "openrouter/openai/gpt-5.1",
               "openrouter/google/gemini-3-pro-preview",
               "openrouter/x-ai/grok-4.1-fast",
           ],
       }
   )

   # Get the final answer (standard LiteLLM response)
   print("=== FINAL ANSWER ===")
   print(response.choices[0].message.content)

   # Access MassGen metadata
   metadata = response._hidden_params

   # Print all agent answers
   print("\n=== ALL ANSWERS ===")
   for answer in metadata.get("massgen_answers", []):
       print(f"\n[{answer['agent_id']}] ({answer['label']})")
       print(answer["content"][:200] + "..." if len(answer["content"] or "") > 200 else answer["content"])

   # Print vote results
   print("\n=== VOTING ===")
   vote_results = metadata.get("massgen_vote_results")
   if vote_results:
       print(f"Winner: {vote_results['winner']}")
       print(f"Votes: {vote_results['vote_counts']}")
       for voted_for, voters in vote_results.get("voter_details", {}).items():
           for v in voters:
               print(f"  {v['voter']} -> {voted_for}: {v['reason']}")

   # Log paths for detailed inspection
   print("\n=== LOG PATHS ===")
   print(f"Log directory: {metadata.get('massgen_log_directory')}")
   print(f"Final answer: {metadata.get('massgen_final_answer_path')}")

Direct Python API
-----------------

For async workflows or more control:

.. code-block:: python

   import asyncio
   import massgen

   # Single agent mode
   result = asyncio.run(massgen.run(
       query="What is machine learning?",
       model="gpt-4o-mini"
   ))
   print(result["final_answer"])

   # Multi-agent mode with config
   result = asyncio.run(massgen.run(
       query="Compare renewable energy sources",
       config="@examples/basic_multi"
   ))
   print(result["final_answer"])

   # Access coordination metadata (multi-agent only)
   print(f"Winner: {result.get('selected_agent')}")
   for answer in result.get("answers", []):
       print(f"[{answer['agent_id']}]: {answer['content'][:100]}...")


Python API Reference
====================

massgen.run()
-------------

The main async function for running MassGen programmatically.

.. code-block:: python

   async def run(
       query: str,
       config: str = None,
       model: str = None,
       enable_logging: bool = False,
       output_file: str = None,
       **kwargs,
   ) -> dict

**Parameters:**

- ``query`` (str): The question or task for the agent(s)
- ``config`` (str, optional): Config file path or ``@examples/NAME``
- ``model`` (str, optional): Quick single-agent mode with model name
- ``enable_logging`` (bool): Enable logging and return ``log_directory`` in result
- ``output_file`` (str, optional): Write final answer to this file path
- ``**kwargs``: Additional configuration options (e.g., ``system_message``, ``base_url``)

**Returns:**

A dictionary containing:

.. code-block:: python

   {
       "final_answer": str,        # The generated answer
       "config_used": str,         # Path to config or "single-agent:<model>"
       "session_id": str,          # Session ID for continuation

       # Log directory pointers (multi-agent mode):
       "log_directory": str,       # Root log directory (e.g., .massgen/massgen_logs/log_XXX)
       "final_answer_path": str,   # Path to final/ directory

       # Coordination metadata (multi-agent mode only, uses anonymous agent_a, agent_b names):
       "selected_agent": str,      # Anonymous ID of the winning agent (e.g., "agent_a")
       "vote_results": dict,       # Voting details with anonymous IDs (see below)
       "answers": list,            # List of answers with labels and paths (see below)
       "agent_mapping": dict,      # Maps anonymous IDs to real agent IDs
   }

The ``answers`` list contains entries for each answer submitted (agent IDs are anonymized):

.. code-block:: python

   [
       {
           "label": "agent1.1",       # Answer label in answerX.Y format
           "agent_id": "agent_a",     # Anonymized agent ID
           "answer_path": "/path/to/.../turn_1/attempt_1/agent_a/20251130_XXX/",
           "content": "The answer text...",
       },
       {
           "label": "agent2.1",
           "agent_id": "agent_b",
           "answer_path": "/path/to/.../turn_1/attempt_1/agent_b/20251130_XXX/",
           "content": "Another answer...",
       },
   ]

The ``agent_mapping`` dict maps anonymous names back to real agent IDs:

.. code-block:: python

   {
       "agent_a": "openrouter-fast1",
       "agent_b": "openrouter-fast2",
   }

The ``vote_results`` dict contains (with anonymized agent IDs):

.. code-block:: python

   {
       "vote_counts": {"agent_a": 2, "agent_b": 1},  # Votes per agent
       "voter_details": {                            # Who voted and why
           "agent_a": [
               {"voter": "agent_b", "reason": "More comprehensive answer"},
               {"voter": "agent_c", "reason": "Better structure"}
           ]
       },
       "winner": "agent_a",      # Winning agent (anonymous ID)
       "is_tie": False,          # Whether there was a tie
       "total_votes": 3,         # Total votes cast
       "agents_with_answers": 2, # Agents that submitted answers
       "agents_voted": 3,        # Agents that voted
   }

**Examples:**

.. code-block:: python

   import asyncio
   import massgen

   # Single agent with specific model
   result = asyncio.run(massgen.run(
       query="Explain quantum computing",
       model="claude-sonnet-4-20250514"
   ))

   # Multi-agent with example config
   result = asyncio.run(massgen.run(
       query="Design a REST API",
       config="@examples/basic_multi"
   ))

   # With logging enabled
   result = asyncio.run(massgen.run(
       query="Your question",
       config="@examples/basic_multi",
       enable_logging=True
   ))
   print(f"Logs at: {result['log_directory']}")

   # Save output to file
   result = asyncio.run(massgen.run(
       query="Your question",
       model="gpt-4o-mini",
       output_file="/tmp/answer.txt"
   ))


massgen.build_config()
----------------------

Build a MassGen configuration dict programmatically, similar to ``--quickstart``:

.. code-block:: python

   def build_config(
       num_agents: int = None,
       backend: str = None,
       model: str = None,
       models: list = None,
       backends: list = None,
       use_docker: bool = False,
       context_path: str = None,
   ) -> dict

**Parameters:**

- ``num_agents`` (int, optional): Number of agents (1-10). Auto-detected from models/backends if not specified.
- ``backend`` (str, optional): Backend provider for all agents - 'openai', 'anthropic', 'gemini', 'grok'
- ``model`` (str, optional): Model name for all agents (e.g., 'gpt-4o-mini')
- ``models`` (list, optional): List of model names, one per agent (e.g., ['gpt-4o', 'claude-sonnet-4-20250514'])
- ``backends`` (list, optional): List of backends, one per agent (e.g., ['openai', 'anthropic'])
- ``use_docker`` (bool): Enable Docker execution mode (default: False)
- ``context_path`` (str, optional): Path to add as context for file operations

**Returns:**

A complete configuration dict ready to use with ``run()``.

**Examples:**

.. code-block:: python

   import asyncio
   import massgen

   # Same model for all agents
   config = massgen.build_config(num_agents=3, model="gpt-5")
   result = asyncio.run(massgen.run(query="Your question", config_dict=config))

   # Different models per agent (auto-detects backends)
   config = massgen.build_config(
       models=["gpt-5", "claude-sonnet-4-5-20250929", "gemini-3-pro-preview"]
   )
   result = asyncio.run(massgen.run(query="Compare approaches", config_dict=config))

   # Explicit backends and models with Docker
   config = massgen.build_config(
       backends=["openai", "anthropic"],
       models=["gpt-5", "claude-sonnet-4-5-20250929"],
       use_docker=True
   )

**Generated Config Structure:**

When you call ``build_config()``, it generates a complete YAML-equivalent config. Here's what the default produces:

.. code-block:: yaml

   # build_config() with defaults (2 agents, gpt-5, local mode)
   agents:
     - id: openai-gpt5-1
       backend:
         type: openai
         model: gpt-5
         cwd: workspace1
         exclude_file_operation_mcps: false  # MCP file ops enabled
     - id: openai-gpt5-2
       backend:
         type: openai
         model: gpt-5
         cwd: workspace2
         exclude_file_operation_mcps: false

   orchestrator:
     snapshot_storage: snapshots
     agent_temporary_workspace: temp_workspaces
     max_new_answers_per_agent: 5
     coordination:
       max_orchestration_restarts: 2
       enable_agent_task_planning: true
       task_planning_filesystem_mode: true
       enable_memory_filesystem_mode: true

   timeout_settings:
     orchestrator_timeout_seconds: 1800

With ``use_docker=True``, the config includes Docker execution settings:

.. code-block:: yaml

   # build_config(models=["groq/llama-3.3-70b"], use_docker=True)
   agents:
     - id: groq-70b1
       backend:
         type: groq
         model: llama-3.3-70b
         base_url: https://api.groq.com/openai/v1  # Auto-filled!
         cwd: workspace1
         enable_code_based_tools: true
         command_line_execution_mode: docker
         command_line_docker_image: ghcr.io/massgen/mcp-runtime-sudo:latest
         # ... additional Docker settings

   orchestrator:
     coordination:
       use_skills: true
       skills_directory: .agent/skills
       # ... additional orchestration settings


LiteLLM Integration
===================

MassGen integrates with `LiteLLM <https://docs.litellm.ai/>`_, allowing you to use it alongside 100+ other LLM providers with a unified interface.

Installation
------------

LiteLLM is an optional dependency. Install it with:

.. code-block:: bash

   pip install massgen[litellm]
   # or
   pip install litellm

Registration
------------

Before using MassGen with LiteLLM, register it as a provider:

.. code-block:: python

   from massgen import register_with_litellm

   # Call once at startup
   register_with_litellm()

Model String Format
-------------------

MassGen uses a special model string format:

- ``massgen/<example-name>`` - Use built-in example config
- ``massgen/model:<model-name>`` - Quick single-agent mode
- ``massgen/path:<config-path>`` - Explicit config file path
- ``massgen/build`` - Build config dynamically from ``optional_params``

**Examples:**

.. code-block:: python

   import litellm
   from massgen import register_with_litellm

   register_with_litellm()

   # Built-in example config
   response = litellm.completion(
       model="massgen/basic_multi",
       messages=[{"role": "user", "content": "Your question"}]
   )

   # Quick single-agent mode
   response = litellm.completion(
       model="massgen/model:gpt-4o-mini",
       messages=[{"role": "user", "content": "What is 2+2?"}]
   )

   # Explicit config path
   response = litellm.completion(
       model="massgen/path:/path/to/my_config.yaml",
       messages=[{"role": "user", "content": "Your question"}]
   )

Dynamic Config Building
-----------------------

Use ``massgen/build`` to create multi-agent configurations on-the-fly.

**Slash Format (Recommended)** - Explicitly specify backend and model:

.. code-block:: python

   import litellm
   from massgen import register_with_litellm

   register_with_litellm()

   # Slash format: "backend/model" - explicit and clear
   response = litellm.completion(
       model="massgen/build",
       messages=[{"role": "user", "content": "Compare approaches"}],
       optional_params={
           "models": ["openai/gpt-5", "groq/llama-3.3-70b", "cerebras/llama-3.3-70b"],
       }
   )

   # Mixed: auto-detect + explicit
   response = litellm.completion(
       model="massgen/build",
       messages=[{"role": "user", "content": "Your question"}],
       optional_params={
           "models": ["gpt-5", "groq/llama-3.3-70b-versatile"],  # gpt-5 auto-detects to openai
       }
   )

   # Same model for multiple agents
   response = litellm.completion(
       model="massgen/build",
       messages=[{"role": "user", "content": "Your question"}],
       optional_params={
           "model": "groq/llama-3.3-70b",
           "num_agents": 3,
       }
   )

**Supported Backends:** ``openai``, ``claude``, ``gemini``, ``grok``, ``groq``, ``cerebras``, ``together``, ``fireworks``, ``openrouter``, and more.

.. tip::
   Use slash format for providers like Groq, Cerebras, Together, etc. where model names
   don't clearly indicate the backend.

Async Usage
-----------

LiteLLM also supports async:

.. code-block:: python

   import asyncio
   import litellm
   from massgen import register_with_litellm

   register_with_litellm()

   async def main():
       response = await litellm.acompletion(
           model="massgen/basic_multi",
           messages=[{"role": "user", "content": "Your question"}]
       )
       print(response.choices[0].message.content)

   asyncio.run(main())

Optional Parameters
-------------------

Pass MassGen-specific options via ``optional_params``:

.. code-block:: python

   response = litellm.completion(
       model="massgen/basic_multi",
       messages=[{"role": "user", "content": "Your question"}],
       optional_params={
           "enable_logging": True,
           "output_file": "/tmp/answer.txt"
       }
   )

**Available Parameters:**

+------------------+------------------+----------------------------------------------------+
| Parameter        | Type             | Description                                        |
+==================+==================+====================================================+
| ``models``       | list[str]        | List of model names for multi-agent mode           |
|                  |                  | (e.g., ``["gpt-4o", "claude-sonnet-4-20250514"]``) |
+------------------+------------------+----------------------------------------------------+
| ``model``        | str              | Single model name for all agents                   |
+------------------+------------------+----------------------------------------------------+
| ``num_agents``   | int              | Number of agents when using single model           |
+------------------+------------------+----------------------------------------------------+
| ``use_docker``   | bool             | Enable Docker execution mode (default: False)      |
+------------------+------------------+----------------------------------------------------+
| ``context_path`` | str              | Path to add as context for file operations         |
+------------------+------------------+----------------------------------------------------+
| ``enable_logging``| bool            | Enable logging and return log directory            |
+------------------+------------------+----------------------------------------------------+
| ``output_file``  | str              | Write final answer to this file path               |
+------------------+------------------+----------------------------------------------------+

.. note::
   When using ``massgen/build``, either ``models`` (list) or ``model`` (single) should be provided.
   If using ``model``, you can also specify ``num_agents`` to control how many agents use that model.

.. tip::
   For more advanced configurations (custom system prompts, MCP tools, specific orchestration settings, etc.),
   create a YAML config file and use ``massgen/path:/path/to/config.yaml`` instead. See
   :doc:`../../reference/yaml_schema` for the full configuration schema.

Accessing Coordination Metadata
-------------------------------

MassGen stores coordination metadata in the response's ``_hidden_params`` attribute.
This follows LiteLLM's convention for provider-specific metadata:

.. code-block:: python

   import litellm
   from massgen import register_with_litellm

   register_with_litellm()

   response = litellm.completion(
       model="massgen/build",
       messages=[{"role": "user", "content": "Compare AI approaches"}],
       optional_params={
           "models": ["openai/gpt-5", "anthropic/claude-sonnet-4-5-20250929"],
       }
   )

   # Access the final answer (standard LiteLLM)
   print(response.choices[0].message.content)

   # Access MassGen coordination metadata
   metadata = response._hidden_params

   # Basic metadata
   print(f"Config used: {metadata['massgen_config_used']}")
   print(f"Session ID: {metadata['massgen_session_id']}")

   # Log directory pointers
   print(f"Log directory: {metadata['massgen_log_directory']}")
   print(f"Final answer path: {metadata['massgen_final_answer_path']}")

   # Coordination metadata (multi-agent mode)
   print(f"Selected agent: {metadata['massgen_selected_agent']}")

   # Voting details
   vote_results = metadata['massgen_vote_results']
   if vote_results:
       print(f"Winner: {vote_results['winner']}")
       print(f"Vote counts: {vote_results['vote_counts']}")
       print(f"Was tie: {vote_results['is_tie']}")

       # See why each agent voted
       for agent_id, voters in vote_results['voter_details'].items():
           for vote in voters:
               print(f"  {vote['voter']} voted for {agent_id}: {vote['reason']}")

   # All answers with labels and log paths
   answers = metadata['massgen_answers']
   if answers:
       for answer in answers:
           print(f"[{answer['label']}] {answer['agent_id']}")
           print(f"  Path: {answer['answer_path']}")
           print(f"  Content: {answer['content'][:100]}...")

**Available Metadata Fields:**

+-------------------------------+------------------+--------------------------------------------------+
| Field                         | Type             | Description                                      |
+===============================+==================+==================================================+
| ``massgen_config_used``       | str              | Config path or description                       |
+-------------------------------+------------------+--------------------------------------------------+
| ``massgen_session_id``        | str              | Session ID for the run                           |
+-------------------------------+------------------+--------------------------------------------------+
| ``massgen_log_directory``     | str or None      | Root log directory path                          |
+-------------------------------+------------------+--------------------------------------------------+
| ``massgen_final_answer_path`` | str or None      | Path to final/ directory with winning answer     |
+-------------------------------+------------------+--------------------------------------------------+
| ``massgen_selected_agent``    | str or None      | Anonymous ID of winning agent (e.g., "agent_a")  |
+-------------------------------+------------------+--------------------------------------------------+
| ``massgen_vote_results``      | dict or None     | Voting details with anonymous agent IDs          |
+-------------------------------+------------------+--------------------------------------------------+
| ``massgen_answers``           | list or None     | Answers with label, anonymous agent_id, path     |
+-------------------------------+------------------+--------------------------------------------------+
| ``massgen_agent_mapping``     | dict or None     | Maps anonymous IDs to real agent IDs             |
+-------------------------------+------------------+--------------------------------------------------+

Each entry in ``massgen_answers`` contains:

- ``label``: Answer label in answerX.Y format (e.g., "agent1.1", "agent2.1")
- ``agent_id``: Anonymous agent ID (e.g., "agent_a", "agent_b")
- ``answer_path``: Full filesystem path to the answer snapshot in logs
- ``content``: The answer text

Use ``massgen_agent_mapping`` to look up the real agent ID if needed:

.. code-block:: python

   mapping = metadata['massgen_agent_mapping']
   real_id = mapping['agent_a']  # e.g., "openrouter-fast1"

.. note::
   Coordination metadata fields (``selected_agent``, ``vote_results``, etc.) are only populated
   in multi-agent mode. In single-agent mode, these fields will be ``None``.

Advanced: Accessing Log Files
-----------------------------

Read answer files directly from the log directory:

.. code-block:: python

   from pathlib import Path

   metadata = response._hidden_params
   log_dir = metadata.get("massgen_log_directory")

   # List log contents
   if log_dir:
       for item in Path(log_dir).iterdir():
           print(f"  {item.name}")

   # Read specific answer files
   for answer in metadata.get("massgen_answers", []):
       if answer.get("answer_path"):
           answer_file = Path(answer["answer_path"]) / "answer.txt"
           if answer_file.exists():
               print(f"{answer['agent_id']}: {answer_file.read_text()[:100]}...")

Advanced: Export to JSON
------------------------

Save structured results for pipelines:

.. code-block:: python

   import json

   metadata = response._hidden_params
   results = {
       "final_answer": response.choices[0].message.content,
       "winner": metadata.get("massgen_selected_agent"),
       "vote_counts": metadata.get("massgen_vote_results", {}).get("vote_counts"),
       "answers": [
           {"agent": a["agent_id"], "label": a["label"], "content": a["content"]}
           for a in metadata.get("massgen_answers", [])
       ],
   }

   with open("massgen_results.json", "w") as f:
       json.dump(results, f, indent=2)


CLI --output-file Flag
======================

For batch processing and automation, use the ``--output-file`` flag to save the final answer directly to a file:

.. code-block:: bash

   # Save answer to specific file
   massgen --config my_config.yaml --output-file /tmp/answer.txt "Your question"

   # Works with automation mode
   massgen --automation --config my_config.yaml --output-file /tmp/answer.txt "Your question"

   # Output includes OUTPUT_FILE path for easy parsing
   # OUTPUT_FILE: /tmp/answer.txt

This is especially useful for:

- Batch processing multiple questions
- Integration with shell scripts
- LLM agents that need to retrieve answers programmatically

**Example batch script:**

.. code-block:: bash

   #!/bin/bash
   questions=("Question 1" "Question 2" "Question 3")

   for i in "${!questions[@]}"; do
       massgen --automation --config config.yaml \
           --output-file "/tmp/answer_${i}.txt" \
           "${questions[$i]}"
   done

   # Results are in /tmp/answer_0.txt, /tmp/answer_1.txt, etc.


Integration Patterns
====================

Evaluation Workflows
--------------------

Use MassGen in your evaluation pipelines:

.. code-block:: python

   import asyncio
   import massgen
   from pathlib import Path

   async def evaluate_questions(questions: list, config: str) -> list:
       """Run MassGen on a list of questions and collect results."""
       results = []
       for q in questions:
           result = await massgen.run(
               query=q,
               config=config,
               enable_logging=True
           )
           results.append({
               "question": q,
               "answer": result["final_answer"],
               "log_dir": result.get("log_directory")
           })
       return results

   # Run evaluation
   questions = [
       "What is machine learning?",
       "Explain neural networks",
       "Compare supervised and unsupervised learning"
   ]

   results = asyncio.run(evaluate_questions(
       questions,
       config="@examples/basic_multi"
   ))

   for r in results:
       print(f"Q: {r['question']}")
       print(f"A: {r['answer'][:200]}...")
       print()

LangChain Integration
---------------------

Use MassGen as a LangChain LLM via LiteLLM:

.. code-block:: python

   from langchain_community.chat_models import ChatLiteLLM
   from massgen import register_with_litellm

   register_with_litellm()

   llm = ChatLiteLLM(model="massgen/basic_multi")
   response = llm.invoke("Compare different AI architectures")
   print(response.content)


Checking LiteLLM Availability
=============================

Check if LiteLLM is available before using:

.. code-block:: python

   from massgen import LITELLM_AVAILABLE, register_with_litellm

   if LITELLM_AVAILABLE:
       register_with_litellm()
       # Use LiteLLM integration
   else:
       print("LiteLLM not installed. Install with: pip install massgen[litellm]")
       # Fall back to direct API


Next Steps
==========

- **See** :doc:`automation` for LLM agent automation guide
- **Read** :doc:`../../reference/cli` for all CLI options
- **Check** :doc:`../../reference/yaml_schema` for configuration details
- **Browse** :doc:`../../examples/basic_examples` for working examples
