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

   # Non-streaming request
   response = client.chat.completions.create(
       model="massgen",
       messages=[{"role": "user", "content": "Analyze renewable energy trends"}],
       stream=False
   )

   # Final answer
   print(response.choices[0].message.content)

   # Coordination traces (optional)
   if hasattr(response.choices[0].message, "reasoning_content"):
       print(response.choices[0].message.reasoning_content)

**cURL alternative:**

.. code-block:: bash

   curl http://localhost:4000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model":"massgen","messages":[{"role":"user","content":"Hello!"}]}'

Streaming Example
-----------------

.. code-block:: python

   from openai import OpenAI

   client = OpenAI(
       base_url="http://localhost:4000/v1",
       api_key="not-needed"
   )

   stream = client.chat.completions.create(
       model="massgen",
       messages=[{"role": "user", "content": "What is 25 * 4?"}],
       stream=True
   )

   for chunk in stream:
       delta = chunk.choices[0].delta

       # Coordination traces come first (optional)
       if hasattr(delta, "reasoning_content") and delta.reasoning_content:
           print(f"[TRACE] {delta.reasoning_content}")

       # Final answer content
       if delta.content:
           print(delta.content, end="", flush=True)

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
     - Chat completions (supports ``stream: true`` for SSE)

Response Format
---------------

The server returns OpenAI-compatible responses with an additional ``reasoning_content`` field:

.. code-block:: json

   {
     "choices": [{
       "message": {
         "role": "assistant",
         "content": "The final coordinated answer from the agent team.",
         "reasoning_content": "[agent_1] Analyzing...\n[agent_2] Voting...\n[orchestrator] Selected agent_1"
       },
       "finish_reason": "stop"
     }]
   }

* ``content`` - The final synthesized answer (what you show to users)
* ``reasoning_content`` - Internal coordination traces (optional, for debugging)

Config-as-Authority
-------------------

When running with ``--config``, the server operates in "Config-as-Authority" mode:

* The ``model`` parameter in client requests is **ignored by default**
* The server uses the agent team defined in your YAML configuration
* To force a model override, use ``model="massgen/model:<model_id>"``

This ensures your carefully tuned multi-agent configuration is respected regardless of what the client sends.

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
     - Path to YAML configuration file
   * - ``--host HOST``
     - Bind address (default: ``0.0.0.0``)
   * - ``--port PORT``
     - Port number (default: ``4000``)
   * - ``--default-model MODEL``
     - Default model to use if no config is provided

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
   * - ``MASSGEN_SERVER_DEFAULT_MODEL``
     - Default model override

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
* :doc:`python_api` - Direct Python API for more control
