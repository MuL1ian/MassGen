Code-Based Tools
================

MassGen supports code-based tool access following the **CodeAct paradigm**. Instead of passing tool schemas to the model, MCP tools are presented as Python code in the workspace filesystem. Agents discover tools by reading files, import them like normal Python modules, and execute them via command-line.

This approach provides significant benefits:

* **98% context reduction** - Load only needed tools instead of all schemas upfront (Anthropic research)
* **Transparent tool access** - Agents read source code and docstrings to understand tools
* **Native composition** - Combine multiple tools naturally using standard Python
* **Async-friendly workflows** - Write async scripts for parallel tool execution
* **Smart data filtering** - Process large datasets before returning to LLM

.. note::

   **Quick Setup Summary:**

   1. Enable ``enable_code_based_tools: true`` in your config
   2. Add ``enable_mcp_command_line: true`` for execution
   3. Optionally add ``exclude_file_operation_mcps: true`` to reduce redundancy
   4. Your MCP servers become Python code in ``workspace/servers/``

Quick Start: Try It Now
------------------------

MassGen includes a working example you can try immediately:

.. code-block:: bash

   # Code-based tools with weather MCP
   massgen \
     --config massgen/configs/tools/filesystem/code_based/example_code_based_tools.yaml \
     "What's the weather forecast for San Francisco and New York?"

The agent will:

1. Explore ``workspace/servers/`` to discover available tools
2. Read tool documentation from Python files
3. Import and use the weather tools
4. Optionally create workflows in ``workspace/utils/`` for complex operations

How It Works
------------

When ``enable_code_based_tools: true`` is set, MassGen:

1. **Connects to your MCP servers** (weather, GitHub, etc.)
2. **Extracts tool schemas** from each connected server
3. **Generates Python wrapper code** for each tool
4. **Writes code to workspace** in an organized structure:

.. code-block:: text

   workspace/
   ├── servers/              # Auto-generated MCP wrappers
   │   ├── __init__.py      # Tool registry (list_tools, load, describe)
   │   ├── weather/
   │   │   ├── __init__.py
   │   │   ├── get_forecast.py
   │   │   └── get_current.py
   │   └── github/
   │       └── create_issue.py
   ├── custom_tools/         # Your custom Python tools (optional)
   ├── utils/               # Agent-created scripts (workflows, async, filtering)
   └── .mcp/                # Hidden MCP client (protocol handler)
       ├── client.py
       └── servers.json

**Directory purposes:**

* ``servers/`` - Auto-generated wrappers for MCP tools (read-only for agents)
* ``custom_tools/`` - Full Python implementations you provide (optional)
* ``utils/`` - Agent workspace for creating workflows and scripts
* ``.mcp/`` - Hidden infrastructure (agents don't see this)

Configuration
-------------

Basic Setup
~~~~~~~~~~~

.. code-block:: yaml

   agents:
     - id: "my_agent"
       backend:
         type: "gemini"
         model: "gemini-2.5-flash"
         cwd: "workspace"

         # Enable code-based tools
         enable_code_based_tools: true
         enable_mcp_command_line: true      # Required for execution
         exclude_file_operation_mcps: true  # Recommended (use CLI for files)

         # Your MCP servers (will be converted to Python code)
         mcp_servers:
           - name: "weather"
             type: "stdio"
             command: "npx"
             args: ["-y", "@modelcontextprotocol/server-weather"]

With Custom Tools
~~~~~~~~~~~~~~~~~

If you have existing Python tools you want visible in the workspace:

.. code-block:: yaml

   backend:
     enable_code_based_tools: true
     custom_tools_path: "path/to/your/custom_tools"  # Copied to workspace/custom_tools/

     mcp_servers:
       - name: "weather"
         # ... MCP config

Your custom tools directory will be copied into ``workspace/custom_tools/`` where agents can read and use them.

Agent Usage Patterns
--------------------

1. Tool Discovery
~~~~~~~~~~~~~~~~~

Agents can discover tools in two ways:

**Via tool registry:**

.. code-block:: python

   # List all available tools
   import servers
   tools = servers.list_tools()
   # ['weather.get_forecast', 'weather.get_current', 'github.create_issue']

   # Read documentation
   print(servers.describe('weather.get_forecast'))

**Via filesystem exploration:**

.. code-block:: bash

   # Explore what's available
   ls servers/
   ls servers/weather/
   cat servers/weather/get_forecast.py  # Read source code and docstrings

2. Direct Tool Usage
~~~~~~~~~~~~~~~~~~~~

Once discovered, agents import and use tools:

.. code-block:: python

   # Import tool
   from servers.weather import get_forecast

   # Call it
   forecast = get_forecast("San Francisco", days=3)
   print(forecast)

3. Creating Workflows (utils/)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Agents can write sophisticated scripts in ``utils/`` to compose multiple tools:

.. code-block:: python

   # utils/daily_weather_report.py
   from servers.weather import get_forecast, get_current

   def generate_report(city: str) -> str:
       """Generate a daily weather report for a city."""
       current = get_current(city)
       forecast = get_forecast(city, days=3)

       report = f"Current: {current['temp']}°F\n"
       report += f"3-day forecast: {forecast['summary']}"
       return report

   if __name__ == "__main__":
       print(generate_report("San Francisco"))

Then execute:

.. code-block:: bash

   python utils/daily_weather_report.py

4. Async Operations
~~~~~~~~~~~~~~~~~~~

For parallel tool calls, agents can use asyncio:

.. code-block:: python

   # utils/parallel_forecasts.py
   import asyncio
   from servers.weather import get_forecast

   async def get_forecasts(cities: list) -> dict:
       """Get forecasts for multiple cities in parallel."""
       tasks = [get_forecast(city) for city in cities]
       results = await asyncio.gather(*tasks)
       return dict(zip(cities, results))

   cities = ["San Francisco", "New York", "Los Angeles", "Chicago"]
   forecasts = asyncio.run(get_forecasts(cities))
   print(forecasts)

5. Data Filtering
~~~~~~~~~~~~~~~~~

Process large datasets in the execution environment before returning to the LLM:

.. code-block:: python

   # utils/qualified_leads.py
   from servers.salesforce import get_records

   def get_top_leads(limit: int = 50) -> list:
       """Get top qualified leads (filters 10k → 50 records)."""
       # Fetch large dataset
       all_records = get_records(object="Lead", limit=10000)

       # Filter in execution environment (not sent to LLM)
       qualified = [r for r in all_records if r["score"] > 80]

       # Return only top N (massive context reduction)
       return sorted(qualified, key=lambda x: x["score"], reverse=True)[:limit]

   # Agent only sees top 50, not all 10k records
   top_leads = get_top_leads()

Generated Code Example
----------------------

MassGen generates clean, documented Python wrappers. Here's an example:

**``servers/weather/get_forecast.py``:**

.. code-block:: python

   """
   get_forecast - MCP tool wrapper

   Auto-generated wrapper for the 'get_forecast' tool from the 'weather' MCP server.
   This wrapper handles MCP protocol communication transparently.
   """

   from typing import Any, Dict, Optional
   import sys
   import os
   from pathlib import Path

   # Add .mcp to path for MCP client
   _mcp_path = Path(__file__).parent.parent.parent / '.mcp'
   if str(_mcp_path) not in sys.path:
       sys.path.insert(0, str(_mcp_path))

   from client import call_mcp_tool


   def get_forecast(location: str, days: Optional[int] = 5) -> Any:
       """Get weather forecast for a location.

       Args:
           location (str): City name or coordinates
           days (int, optional): Number of days (default: 5, max: 10)

       Returns:
           Any: Tool execution result from MCP server
       """
       return call_mcp_tool(
           server="weather",
           tool="get_forecast",
           arguments={
               "location": location,
               "days": days
           }
       )


   if __name__ == "__main__":
       # CLI usage for testing
       import json

       if len(sys.argv) > 1:
           result = get_forecast(sys.argv[1])
       else:
           print("Usage: python get_forecast.py <location>")
           print(f"\nDocumentation:\n{get_forecast.__doc__}")
           sys.exit(1)

       print(json.dumps(result, indent=2))

Agents can read this file to understand the tool's interface, then import and use it.

Benefits
--------

Context Reduction
~~~~~~~~~~~~~~~~~

**Without code-based tools:**

* All tool schemas loaded upfront into model context
* 10 MCP tools × 200 tokens each = 2,000 tokens before any task
* Wasted context on unused tools

**With code-based tools:**

* Only tool names visible initially (``ls servers/``)
* Agent reads only needed tools
* 98% reduction in tool-related context (Anthropic research)

Transparency
~~~~~~~~~~~~

Agents can:

* Read source code to understand tool behavior
* See parameter types and defaults
* Read docstrings and examples
* Understand error handling

This is impossible with opaque tool schemas.

Composability
~~~~~~~~~~~~~

Standard Python enables natural tool composition:

.. code-block:: python

   # utils/weather_email.py
   from servers.weather import get_forecast
   from servers.gmail import send_email

   async def send_weather_alert(city: str, recipient: str):
       """Send weather forecast via email."""
       forecast = get_forecast(city, days=7)

       if forecast['max_temp'] > 100:
           await send_email(
               to=recipient,
               subject=f"Heat Alert: {city}",
               body=f"High temperature expected: {forecast['max_temp']}°F"
           )

Async Performance
~~~~~~~~~~~~~~~~~

Native async support enables parallel tool calls:

.. code-block:: python

   # Sequential: 3 seconds total
   forecast1 = get_forecast("SF")      # 1s
   forecast2 = get_forecast("NYC")     # 1s
   forecast3 = get_forecast("LA")      # 1s

   # Parallel: 1 second total
   results = await asyncio.gather(
       get_forecast("SF"),
       get_forecast("NYC"),
       get_forecast("LA")
   )  # All execute concurrently

Data Filtering Privacy
~~~~~~~~~~~~~~~~~~~~~~

Process sensitive data in execution environment:

.. code-block:: python

   # Fetch 10k customer records
   customers = get_records("Customer", limit=10000)

   # Filter to relevant subset (in execution env, not sent to LLM)
   active_customers = [c for c in customers if c["status"] == "active"]

   # Only return summary statistics
   return {
       "total": len(customers),
       "active": len(active_customers),
       "conversion_rate": len(active_customers) / len(customers)
   }

The LLM never sees the raw customer data.

Important Notes
---------------

Built-in MCPs Stay as MCPs
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Only **user-added MCP servers** are converted to code. Built-in framework MCPs remain as protocol tools:

* ``command_line`` - Command execution (bash is implicitly available)
* ``workspace_tools`` - File operations, media generation
* ``filesystem`` - Filesystem operations
* ``planning`` - Task planning MCP
* ``memory`` - Memory management MCP

These are abstracted at the protocol level and not visible in the filesystem. For example, you can run bash commands directly without needing an ``execute_command`` function - it's automatically available.

Non-blocking Code Generation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If code generation fails, MCP setup continues normally. The agent falls back to protocol-based tool access.

Command-line Execution Required
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Code-based tools require command-line execution capability:

.. code-block:: yaml

   backend:
     enable_mcp_command_line: true  # Required

Without this, agents cannot execute Python scripts.

Recommended: Exclude File Operation MCPs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Since agents have command-line access, file operations can use standard tools (``cat``, ``ls``, etc.):

.. code-block:: yaml

   backend:
     exclude_file_operation_mcps: true  # Use CLI for file operations

This reduces tool overhead and simplifies the environment.

Complete Example Config
------------------------

.. code-block:: yaml

   agents:
     - id: "research_agent"
       backend:
         type: "gemini"
         model: "gemini-2.5-flash"
         cwd: "research_workspace"

         # Code-based tools configuration
         enable_code_based_tools: true
         enable_mcp_command_line: true
         exclude_file_operation_mcps: true

         # Optional: Your custom tools
         custom_tools_path: "my_tools/"

         # MCP servers (converted to Python code)
         mcp_servers:
           - name: "weather"
             type: "stdio"
             command: "npx"
             args: ["-y", "@modelcontextprotocol/server-weather"]

           - name: "github"
             type: "stdio"
             command: "npx"
             args: ["-y", "@modelcontextprotocol/server-github"]
             env:
               GITHUB_TOKEN: "${GITHUB_TOKEN}"

       system_message: |
         You are a research assistant with access to weather and GitHub tools.
         Tools are available as Python modules in the workspace.

         Discover tools:
         - ls servers/
         - cat servers/weather/get_forecast.py

         Use tools:
         - from servers.weather import get_forecast
         - Create workflows in utils/ for complex tasks

   ui:
     display_type: "rich_terminal"

References
----------

This implementation is based on recent research and production systems:

* **CodeAct** (Apple Research) - Shows 20% higher success rate using code as action space
  https://machinelearning.apple.com/research/codeact

* **Cloudflare Code Mode** - TypeScript API approach for tool access
  https://blog.cloudflare.com/code-mode/

* **Anthropic MCP Code Execution** - Demonstrates 98% context reduction
  https://www.anthropic.com/engineering/code-execution-with-mcp

See Also
--------

* :doc:`custom_tools` - Creating custom Python tools
* :doc:`mcp_integration` - MCP server setup and configuration
* :doc:`code_execution` - Command-line execution modes
* :doc:`file_operations` - File operation configuration
