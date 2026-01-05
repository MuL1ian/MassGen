HTTP Server (OpenAI-Compatible API)
====================================

Run MassGen as an OpenAI-compatible HTTP server for seamless integration with existing tools, proxies, and clients.

Quick Start
-----------

**Step 1: Create a config file** (``config.yaml``)

.. code-block:: yaml

   agents:
     - id: research-agent
       backend:
         type: openai
         model: gpt-4o

     - id: analysis-agent
       backend:
         type: gemini
         model: gemini-2.5-flash

**Step 2: Start the server**

.. code-block:: bash

   massgen serve --config config.yaml

   # Server starts on http://localhost:4000

**Step 3: Connect with any OpenAI client**

.. code-block:: python

   from openai import OpenAI

   client = OpenAI(
       base_url="http://localhost:4000/v1",
       api_key="not-needed"  # Local server doesn't require auth
   )

   response = client.chat.completions.create(
       model="massgen",
       messages=[{"role": "user", "content": "Analyze renewable energy trends"}],
   )

   # Final answer
   print(response.choices[0].message.content)

**cURL alternative:**

.. code-block:: bash

   curl http://localhost:4000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model":"massgen","messages":[{"role":"user","content":"Hello!"}]}'

Endpoints
---------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Endpoint
     - Description
   * - ``GET /health``
     - Health check (returns ``{"status": "ok"}``)
   * - ``POST /v1/chat/completions``
     - Chat completions endpoint

Response Format
---------------

The server returns OpenAI-compatible responses with MassGen metadata:

.. code-block:: json

   {
     "id": "chatcmpl-req_abc123",
     "object": "chat.completion",
     "created": 1704067200,
     "model": "massgen",
     "choices": [{
       "index": 0,
       "message": {
         "role": "assistant",
         "content": "The final coordinated answer from the agent team."
       },
       "finish_reason": "stop"
     }],
     "usage": {
       "prompt_tokens": 0,
       "completion_tokens": 0,
       "total_tokens": 0
     },
     "massgen_metadata": {
       "session_id": "api_session_20260104_213901",
       "config_used": "/path/to/config.yaml",
       "log_directory": ".massgen/massgen_logs/log_20260104_213901_326713",
       "final_answer_path": ".massgen/massgen_logs/log_20260104_213901_326713/turn_1/final",
       "selected_agent": "agent_a",
       "vote_results": {
         "vote_counts": {"agent_a": 2, "agent_b": 1},
         "winner": "agent_a",
         "is_tie": false
       },
       "answers": [
         {"label": "answer1.1", "agent_id": "agent_a", "content": "..."},
         {"label": "answer2.1", "agent_id": "agent_b", "content": "..."}
       ],
       "agent_mapping": {"agent1": "agent_a", "agent2": "agent_b"}
     }
   }

The ``massgen_metadata`` field contains the same information returned by ``massgen.run()``:

* ``session_id`` - Unique session identifier
* ``config_used`` - Path to the config file used
* ``log_directory`` - Root log directory for this session
* ``final_answer_path`` - Path to the final answer directory
* ``selected_agent`` - ID of the winning agent
* ``vote_results`` - Voting details (counts, winner, tie status)
* ``answers`` - All submitted answers with labels and content
* ``agent_mapping`` - Mapping from anonymous names to agent IDs

Config Selection
----------------

Use the ``model`` parameter to select which config to use:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Model String
     - Description
   * - ``massgen``
     - Use the server's default config (from ``--config`` or auto-discovered)
   * - ``massgen/basic_multi``
     - Use a built-in example config (e.g., ``@examples/basic_multi``)
   * - ``massgen/path:/path/to/config.yaml``
     - Use a specific config file path

CLI Options
-----------

.. code-block:: bash

   massgen serve [OPTIONS]

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Option
     - Description
   * - ``--config PATH``
     - Path to YAML configuration file (supports ``@examples/`` syntax)
   * - ``--host HOST``
     - Bind address (default: ``0.0.0.0``)
   * - ``--port PORT``
     - Port number (default: ``4000``)
   * - ``--reload``
     - Enable auto-reload (development only)

If no ``--config`` is provided, the server auto-discovers configs in order:

1. ``.massgen/config.yaml`` (project-level)
2. ``~/.config/massgen/config.yaml`` (user-level)

Environment Variables
---------------------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Variable
     - Description
   * - ``MASSGEN_SERVER_HOST``
     - Bind address (default: ``0.0.0.0``)
   * - ``MASSGEN_SERVER_PORT``
     - Port (default: ``4000``)
   * - ``MASSGEN_SERVER_DEFAULT_CONFIG``
     - Default config file path

Full Feature Parity
-------------------

The HTTP server uses ``massgen.run()`` internally, providing **identical behavior** to CLI, WebUI, and LiteLLM modes:

* **Logging** - Creates logs in ``.massgen/massgen_logs/``
* **Metrics** - Saves ``metrics_summary.json`` and ``execution_metadata.yaml``
* **Session Management** - Full session tracking with coordination history
* **Agent Outputs** - Saves individual agent outputs to ``agent_outputs/``

This means you can use ``massgen logs`` to view server session logs, and all debugging/analysis tools work the same way.

Streaming Support
-----------------

.. note::

   Streaming (``stream: true``) is not yet supported. Set ``stream: false`` in requests.
   Streaming support is planned for a future release.

Use Cases
---------

The HTTP server is ideal for:

* **API Gateways** - Route MassGen through existing infrastructure
* **Proxies** - Use tools like LiteLLM Proxy or other OpenAI-compatible routers
* **External Applications** - Any app that speaks the OpenAI API format
* **Language-Agnostic Integration** - Use from any language with HTTP support

See Also
--------

* :doc:`/quickstart/running-massgen` - Quick start with all modes
* :doc:`/reference/cli` - Full CLI reference
* :doc:`python_api` - Direct Python API (same return values as HTTP server)
