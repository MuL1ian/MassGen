Subagents
=========

Subagents enable agents to spawn independent child processes for parallel task execution. Each subagent runs in its own isolated workspace, allowing complex workflows to be broken into concurrent, independent pieces.

Quick Start
-----------

**Enable subagents and run a parallel task:**

.. code-block:: bash

   massgen \
     --config @massgen/configs/features/subagent_demo.yaml \
     "Build a web app with frontend, backend, and documentation"

The agent can spawn subagents to work on frontend, backend, and docs simultaneously.

What are Subagents?
-------------------

Subagents are independent MassGen processes spawned by a parent agent to handle parallelizable work:

.. code-block:: text

   Parent Agent
   ├── spawn_subagents([
   │     {task: "Build frontend", subagent_id: "frontend"},
   │     {task: "Build backend", subagent_id: "backend"},
   │     {task: "Write docs", subagent_id: "docs"}
   │   ])
   │
   ├─→ Subagent: frontend (isolated workspace)
   ├─→ Subagent: backend (isolated workspace)
   └─→ Subagent: docs (isolated workspace)

   ← All complete → Parent continues with results

Key characteristics:

* **Process isolation**: Each subagent is a separate MassGen subprocess
* **Independent workspaces**: No interference between subagents
* **Parallel execution**: All subagents run concurrently
* **Automatic inheritance**: Subagents use the same model/backend as parent by default
* **Result aggregation**: Parent receives structured results with workspace paths

When to Use Subagents
---------------------

Use subagents when you have:

* **Independent parallel tasks**: Research topic A while researching topic B
* **Large deliverables**: Break a website into frontend, backend, assets
* **Context isolation**: Keep each task's files separate and organized
* **Time-consuming work**: Run multiple long tasks simultaneously

Do NOT use subagents for:

* **Sequential dependencies**: Task B needs output from Task A
* **Simple tasks**: Overhead isn't worth it for quick operations
* **Shared state requirements**: Tasks that need to coordinate in real-time

Configuration
-------------

Basic Configuration
~~~~~~~~~~~~~~~~~~~

Enable subagents in your YAML config:

.. code-block:: yaml

   orchestrator:
     enable_subagents: true
     subagent_default_timeout: 300  # 5 minutes per subagent
     subagent_max_concurrent: 3     # Max 3 subagents at once

Full Example
~~~~~~~~~~~~

.. code-block:: yaml

   agents:
     - id: "orchestrator_agent"
       backend:
         type: "openai"
         model: "gpt-4o"
         cwd: "workspace"
         enable_mcp_command_line: true
       system_message: |
         You are a task orchestrator. For complex tasks with independent
         parts, use spawn_subagents to parallelize the work.

   orchestrator:
     enable_subagents: true
     subagent_default_timeout: 300
     subagent_max_concurrent: 3
     enable_agent_task_planning: true  # Recommended for complex orchestration

   ui:
     display_type: "rich_terminal"
     logging_enabled: true

Custom Subagent Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, subagents inherit all parent agent configurations. To customize:

.. code-block:: yaml

   orchestrator:
     enable_subagents: true
     subagent_orchestrator:
       enabled: true
       agents:
         - id: "subagent_worker"
           backend:
             type: "openai"
             model: "gpt-4o-mini"  # Use cheaper model for subagents
         - id: "subagent_worker_2"
           backend:
             type: "gemini"
             model: "gemini-2.0-flash"

How Agents Use Subagents
------------------------

When subagents are enabled, agents have access to the ``spawn_subagents`` tool:

.. code-block:: json

   {
     "tool": "spawn_subagents",
     "arguments": {
       "tasks": [
         {
           "task": "Research Bob Dylan's biography and write to bio.md",
           "subagent_id": "biography"
         },
         {
           "task": "Create discography table in discography.md",
           "subagent_id": "discography"
         },
         {
           "task": "List 20 famous songs with years in songs.md",
           "subagent_id": "songs"
         }
       ],
       "context": "Building a Bob Dylan tribute website with biography, discography, and songs pages"
     }
   }

Critical Rules
~~~~~~~~~~~~~~

1. **Tasks run in PARALLEL**: All tasks start simultaneously. Do NOT create tasks where one depends on another's output.

2. **Context is REQUIRED**: Subagents need project context to understand their work.

3. **Maximum tasks per call**: Limited by ``subagent_max_concurrent`` (default 3).

4. **No nesting**: Subagents cannot spawn their own subagents.

5. **Read-only context files**: Use ``context_files`` to share files, but subagents can only read them.

Result Structure
~~~~~~~~~~~~~~~~

The ``spawn_subagents`` tool returns:

.. code-block:: json

   {
     "success": true,
     "results": [
       {
         "subagent_id": "biography",
         "status": "completed",
         "success": true,
         "answer": "Created bio.md with comprehensive biography...",
         "workspace": "/path/to/subagents/biography/workspace",
         "execution_time_seconds": 45.2,
         "token_usage": {"input_tokens": 5000, "output_tokens": 2000}
       },
       {
         "subagent_id": "discography",
         "status": "completed",
         "success": true,
         "answer": "Created discography.md with album table...",
         "workspace": "/path/to/subagents/discography/workspace",
         "execution_time_seconds": 38.7
       }
     ],
     "summary": {
       "total": 3,
       "completed": 3,
       "failed": 0,
       "timeout": 0
     }
   }

Sharing Files with Subagents
----------------------------

Pass files to subagents using ``context_files``:

.. code-block:: json

   {
     "tasks": [
       {
         "task": "Refactor the utils module",
         "subagent_id": "refactor",
         "context_files": [
           "/path/to/project/utils.py",
           "/path/to/project/config.py"
         ]
       }
     ],
     "context": "Improving code quality in the utils module"
   }

.. warning::

   Context files are **read-only**. Subagents cannot modify files passed via ``context_files``. If you need the parent to use subagent output, copy files from the subagent's workspace after completion.

Handling Timeouts
-----------------

When a subagent times out, check its workspace for partial work:

.. code-block:: text

   Subagent "frontend" timed out after 300 seconds.

   Workspace: /path/to/subagents/frontend/workspace

   Check this directory for any files the subagent created
   before timing out. You can complete the remaining work yourself.

The parent agent can:

1. Read files from the timed-out subagent's workspace
2. Complete the remaining work
3. Or retry with adjusted parameters

Logging and Debugging
---------------------

Subagent logs are organized in the main session's log directory:

.. code-block:: text

   .massgen/massgen_logs/log_YYYYMMDD_HHMMSS/
   └── turn_1/
       └── attempt_1/
           ├── subagents/
           │   ├── biography/
           │   │   ├── status.json          # Progress and token usage
           │   │   ├── conversation.json    # Subagent conversation
           │   │   └── subprocess_logs.json # Path to full subprocess logs
           │   ├── discography/
           │   │   └── ...
           │   └── songs/
           │       └── ...
           ├── metrics_summary.json         # Includes subagent costs
           └── status.json

The ``status.json`` for each subagent contains:

.. code-block:: json

   {
     "subagent_id": "biography",
     "status": "completed",
     "task": "Research Bob Dylan's biography...",
     "started_at": "2025-01-15T10:30:00",
     "completed_at": "2025-01-15T10:30:45",
     "token_usage": {
       "input_tokens": 5000,
       "output_tokens": 2000,
       "estimated_cost": 0.015
     },
     "answer": "Created bio.md with comprehensive biography..."
   }

Cost Tracking
-------------

Subagent costs are automatically aggregated in the parent's metrics:

.. code-block:: json

   {
     "totals": {
       "estimated_cost": 0.083,
       "agent_cost": 0.046,
       "subagent_cost": 0.037
     },
     "subagents": {
       "total_subagents": 3,
       "total_input_tokens": 15000,
       "total_output_tokens": 6000,
       "total_estimated_cost": 0.037
     }
   }

Best Practices
--------------

1. **Design for independence**: Each subagent task should be completable without other subagents' output.

2. **Provide clear context**: The ``context`` parameter helps subagents understand the bigger picture.

3. **Use meaningful IDs**: ``subagent_id`` values appear in logs and help with debugging.

4. **Set appropriate timeouts**: Complex tasks may need longer than the default 5 minutes.

5. **Check workspaces on failure**: Subagent workspaces persist even on timeout/error.

6. **Start small**: Test with 2-3 subagents before scaling up.

Example Workflows
-----------------

Website Builder
~~~~~~~~~~~~~~~

.. code-block:: text

   Task: "Build a Bob Dylan tribute website"

   Parent agent spawns:
   ├── "research" subagent → Creates bio.md, timeline.md, quotes.md
   ├── "frontend" subagent → Creates HTML templates, CSS, JS
   └── "assets" subagent → Creates image metadata, placeholders

   Parent then:
   1. Copies files from each workspace
   2. Integrates content into templates
   3. Delivers final website

Documentation Generator
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   Task: "Generate API documentation for all modules"

   Parent agent spawns:
   ├── "auth_docs" subagent → Documents auth module
   ├── "db_docs" subagent → Documents database module
   └── "api_docs" subagent → Documents API endpoints

   Parent then:
   1. Collects all generated docs
   2. Creates index and cross-references
   3. Builds final documentation site

Docker Support
--------------

Subagents fully support Docker execution mode. When the parent agent is configured to run commands in Docker, subagents automatically inherit all Docker settings:

.. code-block:: yaml

   agents:
     - id: "orchestrator_agent"
       backend:
         type: "gemini"
         model: "gemini-2.0-flash"
         cwd: "workspace"
         enable_mcp_command_line: true
         command_line_execution_mode: docker
         command_line_docker_image: ghcr.io/massgen/mcp-runtime-sudo:latest
         command_line_docker_network_mode: bridge
         command_line_docker_enable_sudo: true
         enable_code_based_tools: true
         auto_discover_custom_tools: true

   orchestrator:
     coordination:
       enable_subagents: true

With this configuration:

* Subagents inherit Docker settings (image, network mode, sudo, credentials)
* Subagents inherit code-based tools settings
* Each subagent's ``execute_command`` calls run in isolated Docker containers

**Architecture:**

.. code-block:: text

   Host Machine
   └── MassGen parent process (runs on host)
        ├── execute_command → Docker container
        └── spawn_subagents → subprocess on host
             └── MassGen subagent process (runs on host)
                  └── execute_command → Docker container

.. important::

   **Limitation**: MassGen itself must run on the host, not inside Docker. The subagent system spawns new MassGen processes as subprocesses, which requires host access. Docker mode only applies to command execution (``execute_command`` tool), not to the MassGen orchestration layer.

   This means:

   * ✅ Running ``massgen`` on your host with ``command_line_execution_mode: docker`` works
   * ✅ Subagents will also run their commands in Docker
   * ❌ Running the entire MassGen process inside Docker with subagents enabled is not supported

Troubleshooting
---------------

Subagent Not Spawning
~~~~~~~~~~~~~~~~~~~~~

**Problem**: ``spawn_subagents`` tool not available.

**Solution**: Ensure ``enable_subagents: true`` is set in orchestrator config.

All Subagents Timing Out
~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: Subagents consistently hit timeout.

**Solutions**:

1. Increase timeout: ``subagent_default_timeout: 600``
2. Simplify tasks: Break into smaller pieces
3. Check model: Some models are slower than others

Subagent Can't Access Files
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: Subagent reports file not found.

**Solutions**:

1. Use absolute paths in ``context_files``
2. Verify file exists before spawning
3. Remember: context files are read-only

Parent Can't Find Subagent Output
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: Parent agent can't locate subagent's created files.

**Solutions**:

1. Check the ``workspace`` path in the result
2. Instruct subagents to list created files in their answer
3. Use ``copy_files_batch`` tool to copy from subagent workspace

Related Documentation
---------------------

* :doc:`agent_task_planning` - Plan tasks before spawning subagents
* :doc:`planning_mode` - Coordinate before executing
* :doc:`../tools/index` - Tools available to agents
* :doc:`../../reference/yaml_schema` - Complete configuration reference
