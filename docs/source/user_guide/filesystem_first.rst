==========================
Filesystem-First Mode
==========================

.. note::
   **Status**: Experimental (v0.2.0+)

   Filesystem-first mode is a revolutionary new paradigm that enables agents to discover tools from the filesystem
   rather than having all tools injected into context. This reduces context usage by **98%** and allows attaching
   **100+ MCP servers** without context pollution.

Overview
========

Traditional tool injection loads all available tools into the agent's context window, which:

- Consumes significant tokens (~150K for comprehensive tool definitions)
- Limits the number of MCP servers you can attach (5-10 before context overflow)
- Requires manually predicting which tools agents will need
- Pollutes context with irrelevant tools

Filesystem-first mode solves all these problems by representing tools as **files in the filesystem** that agents discover using CLI primitives like ripgrep and ast-grep.

Key Benefits
============

Context Efficiency
------------------

- **98% reduction**: From ~150K tokens to ~3K tokens for tool definitions
- Only essential tools (filesystem + code execution) remain in context
- All other tools discovered on-demand from filesystem

Unlimited Scalability
---------------------

- **100+ MCP servers**: Attach unlimited servers with zero context cost
- **Progressive disclosure**: Load only tools needed for each task
- **Universal workspace**: One config works for any task

Code Composition
----------------

- **Write scripts**: Compose tools with native Python code
- **Control flow**: Use loops, conditionals, error handling
- **Reusable workflows**: Save successful patterns as skills

Unified Architecture
--------------------

- **MCP tools** → files in ``servers/``
- **Custom tools** → files in ``tools/``
- **Skills** → reusable workflows in ``skills/``
- **Memory** → persistent storage in ``memory/``
- All discoverable with same search primitives

Quick Start
===========

Prerequisites
-------------

Filesystem-first mode **requires** Docker-based code execution:

1. **Docker installed** (Engine 28.0.0+)

   .. code-block:: bash

      docker --version

2. **Build MassGen Docker image**

   .. code-block:: bash

      cd massgen/docker
      bash build.sh

3. **Verify search tools** (ripgrep + ast-grep)

   .. code-block:: bash

      docker run --rm massgen/mcp-runtime:latest rg --version
      docker run --rm massgen/mcp-runtime:latest ast-grep --version

Basic Configuration
-------------------

Create a config file with ``execution_mode: "filesystem_first"``:

.. code-block:: yaml

   # config.yaml
   massgen:
     execution_mode: "filesystem_first"

     # Minimal in-context tools (only essentials)
     in_context_tools:
       filesystem:
         - read_file
         - write_file
         - list_directory
       command_execution:
         - execute_command  # Code execution MCP server tool

     # Attach as many MCP servers as you want!
     available_mcp_servers:
       - google-drive
       - github
       - slack
       - postgres
       # ... unlimited!

   agents:
     - id: "agent"
       backend:
         type: "openai"
         model: "gpt-4o"
         enable_mcp_command_line: true  # Required
         command_line_execution_mode: "docker"  # Required

Run MassGen:

.. code-block:: bash

   massgen --config config.yaml "Your question here"

How It Works
============

Workspace Structure
-------------------

When filesystem-first mode is enabled, MassGen creates this structure:

.. code-block:: text

   /massgen_workspace/                    # Shared workspace
   ├── servers/                           # MCP tools (SHARED, read-only)
   │   ├── google-drive/
   │   │   ├── getDocument.py
   │   │   ├── searchFiles.py
   │   │   └── __init__.py
   │   ├── github/
   │   │   ├── createIssue.py
   │   │   └── __init__.py
   │   └── ...
   ├── tools/                             # Custom tools (SHARED, read-only)
   │   ├── web/
   │   │   ├── playwright_navigate.py
   │   │   └── screenshot.py
   │   └── multimodal/
   │       └── vision_understanding.py
   ├── skills/                            # Reusable workflows
   │   ├── community/                     # Shared skills
   │   │   └── webapp-testing/
   │   │       └── SKILL.md
   │   └── agent_a/                       # Per-agent skills
   │       └── my-workflow/
   │           └── SKILL.md
   └── agents/                            # Per-agent directories
       ├── agent_a/
       │   ├── workspace/  -> temp_workspaces/agent_a/
       │   ├── memory/                    # Persistent memory
       │   └── tasks/
       └── agent_b/
           └── ...

From the agent's perspective (via symlinks):

.. code-block:: text

   /workspace/                            # Agent's working directory
   ├── servers/ -> /massgen_workspace/servers/
   ├── tools/ -> /massgen_workspace/tools/
   ├── skills/ -> /massgen_workspace/skills/
   ├── memory/ -> /massgen_workspace/agents/agent_a/memory/
   └── ... (your project files)

Tool Discovery Workflow
-----------------------

Here's how an agent discovers and uses tools:

**Example Task**: "Analyze Q4 sales and send summary to #sales"

**1. Discover relevant tools using ripgrep:**

.. code-block:: python

   import subprocess

   # Find sales-related tools
   result = subprocess.run(
       ["rg", "sales|revenue|crm", "servers/", "-i", "-l"],
       capture_output=True, text=True
   )
   # Output:
   # servers/salesforce/query_records.py
   # servers/stripe/list_charges.py

   # Find messaging tools
   result = subprocess.run(
       ["rg", "slack|message", "servers/", "-i", "-l"],
       capture_output=True, text=True
   )
   # Output:
   # servers/slack/post_message.py

**2. Read tool definitions:**

.. code-block:: python

   with open("servers/salesforce/query_records.py") as f:
       print(f.read())  # See full tool documentation

**3. Write code using discovered tools:**

.. code-block:: python

   from servers.salesforce import query_records
   from servers.slack import post_message

   # Fetch Q4 sales data
   data = await query_records(
       query="SELECT Amount FROM Opportunity WHERE CloseDate >= 2024-10-01"
   )

   # Analyze
   total = sum(record["Amount"] for record in data)
   summary = f"Q4 Revenue: ${total:,.2f}"

   # Send to Slack
   await post_message(channel="#sales", text=summary)

**Result**: Task completed using only 2 tools (out of 200+ available) with ~3K token context!

Configuration Reference
=======================

Global Settings
---------------

Add a ``massgen:`` section to your config:

.. code-block:: yaml

   massgen:
     # Enable filesystem-first mode (default: "context_based")
     execution_mode: "filesystem_first"

     # Tools that remain in context (minimal set)
     in_context_tools:
       filesystem: [read_file, write_file, list_directory, create_directory]
       code_execution: [execute_python, execute_bash]

     # All other MCP servers (exposed as files, NOT in context)
     available_mcp_servers:
       - google-drive
       - github
       - slack
       # ... add as many as you want!

     # Custom tools (exposed as files, NOT in context)
     available_custom_tools:
       - web.playwright_navigate
       - multimodal.vision_understanding
       # ... all custom tools

     # Code execution configuration (REQUIRED)
     code_execution:
       enabled: true
       mode: "docker"  # Strongly recommended

     # Search tools (for tool discovery)
     search_tools:
       enable_ripgrep: true
       enable_ast_grep: true
       enable_semtools: false  # Optional (future)

In-Context Tools
----------------

These tools remain in the agent's context for immediate access:

**Essential Filesystem** (required for tool discovery):

- ``read_file`` - Read tool definitions and source code
- ``write_file`` - Save generated code
- ``list_directory`` - Discover available tools
- ``create_directory`` - Organize workspace
- ``move_file`` - Manage files
- ``get_file_info`` - Check file metadata

**Command Execution** (required for filesystem-first):

- ``execute_command`` - Run shell commands (ripgrep, ast-grep, Python, etc.)

**Total context cost**: ~3-4K tokens (vs. ~150K for all tools)

Available MCP Servers
---------------------

List all MCP servers you want to make available. Agents will discover them on-demand:

.. code-block:: yaml

   massgen:
     available_mcp_servers:
       # Productivity
       - google-drive
       - gmail
       - google-calendar
       - notion
       - slack

       # Development
       - github
       - gitlab
       - linear

       # Databases
       - postgres
       - mongodb

       # ... add unlimited servers!

**No context cost** - All servers exposed as files, zero tokens in context.

Agent Configuration
-------------------

Agents must have code execution enabled:

.. code-block:: yaml

   agents:
     - id: "universal_agent"
       backend:
         type: "openai"
         model: "gpt-4o"
         enable_mcp_command_line: true  # Required
         command_line_execution_mode: "docker"  # Required
         command_line_docker_image: "massgen/mcp-runtime:latest"

Tool Discovery
==============

Agents use standard CLI tools to discover relevant tools:

Ripgrep (Fast Text Search)
---------------------------

Find tools by keyword:

.. code-block:: bash

   # Find all tools related to "document"
   rg "document" servers/ tools/ -i -l

   # Find tools with specific capabilities
   rg "screenshot|image|visual" tools/ -i -l

AST-grep (Structural Search)
-----------------------------

Find tools by code structure:

.. code-block:: bash

   # Find all async functions
   ast-grep --pattern 'async def $FUNC($$$)' servers/

   # Find tools that return specific types
   ast-grep --pattern 'def $FUNC($$$) -> Dict' servers/

Directory Listing
-----------------

Browse available servers and tools:

.. code-block:: python

   import os

   # List all MCP servers
   servers = os.listdir("servers/")
   print(f"Available: {servers}")

   # List tools in a server
   tools = os.listdir("servers/google-drive/")

Skills System
=============

Skills are reusable workflows saved in SKILL.md format (compatible with Anthropic Skills specification).

Creating Skills
---------------

Agents can save successful workflows:

.. code-block:: python

   from _massgen_runtime import save_skill

   save_skill(
       name="webapp-testing",
       description="Test web applications with Playwright",
       instructions="""
   # Web Application Testing Skill

   ## Instructions
   1. Navigate to URL using playwright_navigate
   2. Take screenshots
   3. Check console for errors

   ## Example
   ```python
   from tools.web import playwright_navigate
   result = await playwright_navigate(url="https://example.com", screenshot=True)
   ```
       """,
       community=True  # Share with all agents
   )

Skills are saved as directories with SKILL.md:

.. code-block:: text

   skills/community/webapp-testing/
   ├── SKILL.md                  # Instructions
   ├── references/               # Optional documentation
   ├── scripts/                  # Optional helper scripts
   └── assets/                   # Optional templates/config

Using Skills
------------

Discover and use skills via filesystem:

.. code-block:: python

   # Discover skills
   import os
   skills = os.listdir("skills/community/")

   # Read a skill
   with open("skills/community/webapp-testing/SKILL.md") as f:
       instructions = f.read()

   # Or use helper
   from _massgen_runtime import read_skill
   skill = read_skill("webapp-testing")
   print(skill["instructions"])

Listing Skills
--------------

.. code-block:: python

   from _massgen_runtime import list_skills

   skills = list_skills()

   print("My skills:")
   for skill in skills["own"]:
       print(f"  - {skill['name']}: {skill['description']}")

   print("\nCommunity skills:")
   for skill in skills["community"]:
       print(f"  - {skill['name']}: {skill['description']}")

Memory System
=============

Each agent has a persistent ``memory/`` directory for storing and retrieving information.

Memory Directory Structure
---------------------------

.. code-block:: text

   memory/                          # Agent's memory (symlinked)
   ├── core_memories.json           # Long-term facts
   ├── task_history.json            # Previous tasks and outcomes
   ├── learned_patterns.md          # Patterns the agent has learned
   └── preferences.yaml             # User preferences

Using Memory
------------

Agents interact with memory using standard file operations:

**Writing Memory:**

.. code-block:: python

   import json

   # Read existing memories
   with open("memory/core_memories.json") as f:
       memories = json.load(f)

   # Add new memory
   memories["user_preferences"] = {"theme": "dark", "language": "python"}

   # Save
   with open("memory/core_memories.json", "w") as f:
       json.dump(memories, f, indent=2)

**Searching Memory:**

.. code-block:: python

   import subprocess

   # Find all memories about a topic
   result = subprocess.run(
       ["rg", "database optimization", "memory/", "-i"],
       capture_output=True, text=True
   )
   print(result.stdout)

**Accessing Memory Path:**

.. code-block:: python

   from _massgen_runtime import get_memory_path

   memory_dir = get_memory_path()
   print(f"My memory is at: {memory_dir}")

Advanced Features
=================

Custom In-Context Tools
-----------------------

You can customize which tools stay in context:

.. code-block:: yaml

   massgen:
     execution_mode: "filesystem_first"

     in_context_tools:
       # Minimal set (maximum context savings)
       filesystem: [read_file, write_file, list_directory]
       code_execution: [execute_python]

     # OR: Add domain-specific essentials
     in_context_tools:
       filesystem: "*"  # All filesystem tools
       code_execution: "*"
       web: [playwright_navigate]  # If web-focused agent

Resource Limits
---------------

Configure Docker resource limits:

.. code-block:: yaml

   agents:
     - backend:
         enable_mcp_command_line: true
         command_line_execution_mode: "docker"
         command_line_docker_memory_limit: "2g"
         command_line_docker_cpu_limit: 4.0
         command_line_docker_network_mode: "bridge"

Network Access
--------------

Control network access for security:

.. code-block:: yaml

   agents:
     - backend:
         command_line_docker_network_mode: "none"    # No network
         # OR
         command_line_docker_network_mode: "bridge"  # Internet access
         # OR
         command_line_docker_network_mode: "host"    # Full host network

Examples
========

Example 1: Universal Workspace
-------------------------------

A single config that works for ANY task:

.. code-block:: yaml

   # universal_workspace.yaml
   massgen:
     execution_mode: "filesystem_first"

     in_context_tools:
       filesystem: [read_file, write_file, list_directory]
       code_execution: [execute_python, execute_bash]

     # Attach EVERY MCP you own
     available_mcp_servers:
       # Productivity (12 servers)
       - google-drive
       - gmail
       - notion
       - slack
       # ... more

       # Development (15 servers)
       - github
       - gitlab
       - linear
       # ... more

       # Databases (8 servers)
       - postgres
       - mongodb
       # ... more

       # Total: 50+ servers, zero context cost!

   agents:
     - id: "universal_agent"
       backend:
         type: "openai"
         model: "gpt-4o"
         enable_mcp_command_line: true
         command_line_execution_mode: "docker"

**Usage**: This single config adapts to any task. Agent discovers and uses only the 2-3 tools needed.

Example 2: Web Development
---------------------------

.. code-block:: yaml

   massgen:
     execution_mode: "filesystem_first"

     available_mcp_servers:
       - github       # Version control
       - vercel       # Deployment
       - postgres     # Database

     available_custom_tools:
       - web.playwright_navigate
       - web.screenshot
       - multimodal.vision_understanding

   agents:
     - id: "web_dev_agent"
       backend:
         type: "openai"
         model: "gpt-4o"
         enable_mcp_command_line: true
         command_line_execution_mode: "docker"

Example 3: Data Analysis
-------------------------

.. code-block:: yaml

   massgen:
     execution_mode: "filesystem_first"

     available_mcp_servers:
       - postgres
       - mongodb
       - salesforce
       - stripe
       - slack        # For reporting

   agents:
     - id: "data_analyst"
       backend:
         type: "openai"
         model: "gpt-4o"
         enable_mcp_command_line: true
         command_line_execution_mode: "docker"

Runtime Functions
=================

Agents have access to these runtime functions:

MCP Tools
---------

.. code-block:: python

   from _massgen_runtime import call_mcp_tool

   result = await call_mcp_tool(
       server="google-drive",
       tool="getDocument",
       arguments={"documentId": "abc123"}
   )

Custom Tools
------------

.. code-block:: python

   from _massgen_runtime import call_custom_tool

   result = await call_custom_tool(
       tool_name="web.playwright_navigate",
       url="https://example.com",
       screenshot=True
   )

Skills
------

.. code-block:: python

   from _massgen_runtime import (
       save_skill,      # Save workflow as skill
       read_skill,      # Read skill instructions
       list_skills,     # List available skills
       delete_skill,    # Remove skill
       get_skill_resource,  # Access bundled resources
   )

Context
-------

.. code-block:: python

   from _massgen_runtime import (
       get_agent_id,     # Get current agent ID
       get_memory_path,  # Get agent's memory directory
   )

Comparison: Context-Based vs Filesystem-First
==============================================

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Aspect
     - Context-Based
     - Filesystem-First
   * - Max MCP servers
     - 5-10 (limited)
     - **100+** (unlimited)
   * - Context cost
     - ~150K tokens
     - **~3K tokens** (98% reduction)
   * - Tool discovery
     - Manual config
     - **Automatic** (ripgrep/ast-grep)
   * - Tool composition
     - Chain tool calls
     - **Write code** (loops, conditionals)
   * - Config management
     - Different per task
     - **One universal config**
   * - Skills
     - Not available
     - **Reusable workflows**
   * - Memory
     - Dedicated API
     - **Filesystem** (unified)
   * - Scalability
     - Limited by context
     - **Unlimited**

Troubleshooting
===============

"execution_mode: 'filesystem_first' requires code execution"
------------------------------------------------------------

**Cause**: Code execution not enabled in agent backend.

**Solution**: Enable Docker-based code execution:

.. code-block:: yaml

   agents:
     - backend:
         enable_mcp_command_line: true
         command_line_execution_mode: "docker"

"Search tool 'ripgrep' is NOT available"
----------------------------------------

**Cause**: Docker image doesn't include ripgrep.

**Solution**: Rebuild Docker image (includes ripgrep by default):

.. code-block:: bash

   cd massgen/docker
   bash build.sh

"Tools not found in filesystem"
--------------------------------

**Cause**: Workspace not initialized or MCP clients not connected.

**Solution**: Check logs for initialization messages. Ensure MCP servers are configured correctly.

"Cannot import from servers/"
------------------------------

**Cause**: Symlinks not created or Python path not set.

**Solution**:

1. Verify symlinks exist:

   .. code-block:: bash

      ls -la temp_workspaces/your_agent_id/

2. Ensure code execution runs from workspace directory

Best Practices
==============

1. **Use filesystem-first for complex multi-tool tasks**

   - Ideal when you need many MCP integrations
   - Great for tasks where tool needs are unpredictable

2. **Create one universal workspace config**

   - Attach all MCP servers you own
   - Reuse for different tasks
   - Let agents discover what they need

3. **Save successful workflows as skills**

   - When a complex task succeeds, save it
   - Share useful skills to community
   - Build a library of proven workflows

4. **Use Docker mode for security**

   - Isolated execution environment
   - Resource limits prevent abuse
   - Network controls

5. **Leverage search tools effectively**

   - Use ripgrep for keyword search
   - Use ast-grep for structural patterns
   - Combine both for precise discovery

See Also
========

- :doc:`tools/code_execution` - Code execution setup
- :doc:`tools/mcp_integration` - MCP server configuration
- :doc:`tools/custom_tools` - Custom tool development
- **Design Doc**: ``docs/dev_notes/filesystem_tool_discovery_design.md``
- **Example Configs**: ``massgen/configs/examples/filesystem_first_*.yaml``

References
==========

- `Anthropic: Code Execution with MCP <https://www.anthropic.com/engineering/code-execution-with-mcp>`_
- `Apple: CodeAct <https://machinelearning.apple.com/research/codeact>`_
- `Anthropic Skills <https://github.com/anthropics/skills>`_
