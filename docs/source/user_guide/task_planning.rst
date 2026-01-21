Task Planning Mode
==================

MassGen's task planning mode enables agents to create structured plans before execution,
separating the "what to build" from the "how to build it" phases.

.. contents:: On This Page
   :local:
   :depth: 2

Overview
--------

Task planning mode provides three workflows:

1. **Planning Only** (``--plan``) - Agents create a structured task plan interactively
2. **Plan and Execute** (``--plan-and-execute``) - Full workflow: create plan, then execute it
3. **Execute Plan** (``--execute-plan``) - Execute an existing plan without re-planning

This separation enables:

* Human review of plans before execution
* Iteration on plans without re-running expensive execution
* Reuse of plans across multiple execution attempts
* Clear accountability for what was planned vs what was built

Quick Start
-----------

**Create a plan:**

.. code-block:: bash

   uv run massgen --config my_agents.yaml --plan "Build a portfolio website with dark mode"

**Create and execute a plan:**

.. code-block:: bash

   uv run massgen --config my_agents.yaml --plan-and-execute "Build a portfolio website"

**Execute an existing plan:**

.. code-block:: bash

   # By plan ID
   uv run massgen --config my_agents.yaml --execute-plan 20260115_173113_836955

   # By path
   uv run massgen --config my_agents.yaml --execute-plan .massgen/plans/plan_20260115_173113_836955

   # Most recent plan
   uv run massgen --config my_agents.yaml --execute-plan latest

Planning Phase
--------------

In planning mode, agents create:

* **Task Plan** (``plan.json``) - Structured list of tasks with dependencies (required)
* **Supporting docs** (optional) - Requirements, design decisions, or other markdown documentation

Plan Depth
^^^^^^^^^^

Control plan granularity with ``--plan-depth``:

.. code-block:: bash

   # Quick overview (5-10 tasks)
   uv run massgen --config my_agents.yaml --plan --plan-depth shallow "Build a blog"

   # Balanced detail (20-50 tasks) - default
   uv run massgen --config my_agents.yaml --plan --plan-depth medium "Build a blog"

   # Comprehensive breakdown (100-200+ tasks)
   uv run massgen --config my_agents.yaml --plan --plan-depth deep "Build a blog"

Broadcast Modes
^^^^^^^^^^^^^^^

Control how agents collaborate during planning:

.. code-block:: bash

   # Agents ask user critical questions (default)
   uv run massgen --config my_agents.yaml --plan --broadcast human "Build a blog"

   # Agents coordinate and clarify with each other
   uv run massgen --config my_agents.yaml --plan --broadcast agents "Build a blog"

   # Fully autonomous - no questions
   uv run massgen --config my_agents.yaml --plan --broadcast false "Build a blog"

.. note::
   In automation mode (``--automation``), ``human`` broadcast automatically switches
   to ``false`` since there's no human to respond.

Task Plan Structure
^^^^^^^^^^^^^^^^^^^

Plans are stored as JSON with this structure:

.. code-block:: json

   {
     "tasks": [
       {
         "id": "F001",
         "description": "Initialize Next.js project with Tailwind CSS",
         "status": "pending",
         "depends_on": [],
         "priority": "high",
         "metadata": {
           "verification": "Dev server runs successfully",
           "verification_method": "Start dev server and verify it loads",
           "verification_group": "foundation"
         }
       },
       {
         "id": "F002",
         "description": "Create responsive navigation component",
         "status": "pending",
         "depends_on": ["F001"],
         "priority": "high",
         "metadata": {
           "verification": "Navigation renders on mobile and desktop",
           "verification_method": "Check responsive rendering at different viewport sizes",
           "verification_group": "components"
         }
       }
     ]
   }

**Task Fields:**

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Required
     - Description
   * - ``id``
     - Yes
     - Unique task identifier (e.g., "F001", "T001")
   * - ``description``
     - Yes
     - What the task accomplishes
   * - ``status``
     - Yes
     - ``pending``, ``in_progress``, ``completed``, ``verified``, or ``blocked``
   * - ``depends_on``
     - Yes
     - Array of task IDs that must complete first
   * - ``priority``
     - No
     - ``high``, ``medium``, or ``low``
   * - ``completed_at``
     - No
     - Timestamp when task was completed (ISO format)
   * - ``verified_at``
     - No
     - Timestamp when task was verified (ISO format)
   * - ``metadata.verification``
     - No
     - How to verify task completion
   * - ``metadata.verification_method``
     - No
     - Specific command or action to verify
   * - ``metadata.verification_group``
     - No
     - Group name for batch verification (e.g., "foundation", "frontend_ui")

Execution Phase
---------------

During execution:

1. The frozen plan (from ``frozen/plan.json``) is loaded and copied to each agent's workspace
2. Agents use MCP planning tools to track progress
3. Agents execute tasks respecting dependencies
4. Agents update task status as they work

MCP Planning Tools
^^^^^^^^^^^^^^^^^^

Agents have access to these tools during execution:

.. code-block:: text

   get_task_plan()                              # View full plan with status
   get_ready_tasks()                            # Tasks with satisfied dependencies
   update_task_status(id, status, notes)        # Mark task progress
   add_task(description, depends_on, priority)  # Add new task if needed
   create_task_plan(tasks)                      # Replace entire plan (adoption)

**Example agent workflow:**

.. code-block:: text

   1. get_ready_tasks() → ["F001"]
   2. update_task_status("F001", "in_progress")
   3. ... execute task ...
   4. update_task_status("F001", "completed", "Created Next.js project")
   5. get_ready_tasks() → ["F002", "F003"]  # Dependencies now satisfied
   6. ... complete more foundation tasks ...
   7. # Verify foundation group: run npm run dev → works!
   8. update_task_status("F001", "verified", "Dev server runs successfully")

**Task Status Flow:**

- ``pending`` → ``in_progress`` → ``completed`` → ``verified``
- **completed**: Implementation is done (code written)
- **verified**: Task has been tested and confirmed working

Agents verify tasks in groups using ``verification_group`` labels, not after every task.

Plan Storage
------------

Plans are stored in ``.massgen/plans/``:

.. code-block:: text

   .massgen/plans/
   └── plan_20260115_173113_836955/
       ├── plan_metadata.json      # Session info, status
       ├── execution_log.jsonl     # Event log
       ├── plan_diff.json          # Changes from original (after execution)
       ├── frozen/                  # Immutable snapshot from planning
       │   ├── plan.json
       │   ├── requirements.md
       │   └── design_decisions.md
       └── workspace/              # Modified plan after execution

**Plan Metadata:**

.. code-block:: json

   {
     "plan_id": "20260115_173113_836955",
     "created_at": "2026-01-15T17:31:13.837534",
     "planning_session_id": "log_20260115_171953_153808",
     "execution_session_id": "log_20260115_195506_513599",
     "status": "completed"
   }

**Status Values:**

* ``planning`` - Plan creation in progress
* ``ready`` - Planning complete, awaiting execution
* ``executing`` - Execution in progress
* ``completed`` - Execution finished
* ``failed`` - Execution failed

Configuration
-------------

Enable planning tools in your config:

.. code-block:: yaml

   orchestrator:
     coordination:
       enable_agent_task_planning: true
       task_planning_filesystem_mode: true

These are **automatically enabled** when using ``--plan``, ``--plan-and-execute``,
or ``--execute-plan`` flags.

Automation Mode
---------------

For CI/CD or programmatic usage:

.. code-block:: bash

   # Plan and execute with automation output
   uv run massgen --automation --config my_agents.yaml \
       --plan-and-execute "Build the feature"

   # Execute existing plan
   uv run massgen --automation --config my_agents.yaml \
       --execute-plan latest

**Automation output includes:**

.. code-block:: text

   LOG_DIR: .massgen/massgen_logs/log_20260115_195506_513599
   PLAN_DIR: .massgen/plans/plan_20260115_173113_836955
   PLAN_ID: 20260115_173113_836955
   STATUS: 0

Best Practices
--------------

**1. Review Plans Before Execution**

.. code-block:: bash

   # Create plan only
   uv run massgen --config my_agents.yaml --plan "Build feature X"

   # Review the plan
   cat .massgen/plans/plan_*/frozen/plan.json

   # Execute when satisfied
   uv run massgen --config my_agents.yaml --execute-plan latest

**2. Use Appropriate Depth**

* ``shallow`` - Quick prototypes, simple features
* ``medium`` - Most projects (default)
* ``deep`` - Complex systems, detailed specifications

**3. Include Verification in Plans**

Good plans include verification methods:

.. code-block:: json

   {
     "id": "F001",
     "description": "Setup project",
     "metadata": {
       "verification": "Project builds without errors",
       "verification_method": "Run build and check for errors"
     }
   }

Agents are instructed to verify at checkpoints:

* After project setup - run dev server, confirm it starts
* After completing a feature group - test the feature works
* Before declaring complete - run full build, fix errors

**4. Iterate on Plans**

If execution reveals issues:

1. Review the plan diff (``--plan-report``)
2. Create a new plan incorporating lessons learned
3. Execute the improved plan

Troubleshooting
---------------

**Plan not found:**

.. code-block:: bash

   # List available plans
   ls .massgen/plans/

   # Use full path if ID doesn't work
   uv run massgen --execute-plan .massgen/plans/plan_20260115_173113_836955

**Agents not following plan:**

Check that planning tools are enabled in your config and that the plan
was properly loaded. Agents should call ``get_task_plan()`` at the start.

**Verification steps not running:**

Agents are instructed to verify at checkpoints (after setup, after feature groups,
before completion), not after every individual task. If verification is still
being skipped, ensure your plan has clear ``verification_method`` fields and
consider adding explicit "verify build" tasks at key milestones.

See Also
--------

* :doc:`concepts` - Core MassGen concepts
* :doc:`logging` - Understanding logs and debugging
* :doc:`../reference/cli` - Complete CLI reference
* :doc:`../examples/advanced_patterns` - Advanced usage patterns
