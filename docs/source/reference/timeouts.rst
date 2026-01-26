Timeout Configuration
=====================

MassGen provides timeout configuration to control how long coordination and agent operations can run before being terminated. This prevents runaway processes and ensures predictable execution times.

Quick Reference
---------------

**Default Timeouts**:

* **Orchestrator**: 1800 seconds (30 minutes)
* **Per-Round**: Disabled by default in YAML configs; enabled in ``--quickstart`` (10 min initial, 5 min subsequent)
* **Grace Period**: 120 seconds (time after soft timeout before hard block)

**CLI Override**:

.. code-block:: bash

   uv run python -m massgen.cli \
     --orchestrator-timeout 600 \
     --config config.yaml \
     "Your question"

**Config File**:

.. code-block:: yaml

   timeout_settings:
     orchestrator_timeout_seconds: 1800
     initial_round_timeout_seconds: 600      # 10 min for first answer
     subsequent_round_timeout_seconds: 180   # 3 min for voting rounds
     round_timeout_grace_seconds: 120        # Grace period before hard block

Timeout Types
-------------

MassGen has two levels of timeout control:

1. **Orchestrator Timeout**: Overall session limit (kills entire coordination)
2. **Per-Round Timeout**: Individual round limits (prompts agents to submit)

Orchestrator Timeout
~~~~~~~~~~~~~~~~~~~~

Controls the maximum time for multi-agent coordination:

* **Covers**: Entire coordination process (all rounds of voting and consensus)
* **Default**: 1800 seconds (30 minutes)
* **When it triggers**: Coordination exceeds the time limit
* **What happens**: Coordination terminates gracefully, current state is saved

.. code-block:: yaml

   timeout_settings:
     orchestrator_timeout_seconds: 600  # 10 minutes

Per-Round Timeout
~~~~~~~~~~~~~~~~~

Controls the maximum time for individual agent rounds. This prevents agents from getting stuck in analysis loops (e.g., repeatedly analyzing the same image with inconsistent results).

* **Covers**: Single round of agent work (initial answer or voting)
* **Default**: Needs to be added in YAML configs; ``--quickstart`` enables with 600s/300s/120s
* **When it triggers**: Agent exceeds time limit for current round
* **What happens**: Two-phase timeout (soft warning, then hard block)

**Configuration Options**:

.. code-block:: yaml

   timeout_settings:
     initial_round_timeout_seconds: 600    # Soft timeout for round 0 (initial answer)
     subsequent_round_timeout_seconds: 180 # Soft timeout for rounds 1+ (voting)
     round_timeout_grace_seconds: 120      # Grace period before hard block

**Two-Phase Timeout Behavior**:

1. **Soft Timeout**: When reached, a friendly warning message is injected telling the agent to wrap up and submit. The agent can still finish final touches to make their work presentable.

2. **Hard Timeout**: After the grace period expires (soft timeout + ``round_timeout_grace_seconds``), non-terminal tool calls are blocked. Only ``vote`` and ``new_answer`` tools are allowed.

**Timeline Example** (initial round with 600s timeout + 120s grace):

.. code-block:: text

   0-600s:   Agent works normally
   600s:     Soft timeout - friendly warning message injected
   600-720s: Grace period - agent can finish final touches
   720s+:    Hard timeout - non-terminal tools blocked, only vote/new_answer allowed

**Soft Timeout Message** (from ``RoundTimeoutPostHook``):

.. code-block:: text

   ============================================================
   ⏰ ROUND TIME LIMIT APPROACHING - PLEASE WRAP UP
   ============================================================

   You have exceeded the soft time limit for this initial answer round (605s / 600s).

   Please wrap up your current work and submit soon:
   1. `new_answer` - Submit your current best answer (can be a work-in-progress)
   2. `vote` - Vote for an existing answer if one is satisfactory

   You may finish any final touches to make your work presentable, but please
   submit within the next 120 seconds. After that, tool calls
   will be blocked and you'll need to submit immediately.

   The next coordination round will allow further iteration if needed.
   ============================================================

**Why Use Per-Round Timeouts**:

* **Prevent stuck agents**: Agents can get caught in loops (e.g., repeatedly calling vision tools on the same image)
* **Predictable costs**: Cap spending on individual rounds
* **Fairer coordination**: Ensure all agents get timely turns
* **Different phases, different needs**: Initial answers need more time than voting rounds

**Smart Injection Skipping**:

When a new answer arrives from another agent, MassGen normally injects it mid-stream so the current agent can consider it. However, if the agent is close to their soft timeout, injection is skipped and the agent restarts instead. This ensures agents have enough time to properly consider new answers rather than being forced to submit immediately after seeing them.

The threshold is ``round_timeout_grace_seconds`` - if remaining time before soft timeout is less than the grace period, injection is skipped.

.. code-block:: text

   [Orchestrator] Skipping mid-stream injection for agent_a - only 45s until soft timeout (need 120s to think)

Subagent Round Timeouts
~~~~~~~~~~~~~~~~~~~~~~~

Subagents can use per-round timeouts too. Configure them under ``orchestrator.coordination.subagent_round_timeouts``.
If omitted, subagents inherit the parent ``timeout_settings`` values.

.. code-block:: yaml

   orchestrator:
     coordination:
       enable_subagents: true
       subagent_round_timeouts:
         initial_round_timeout_seconds: 300
         subsequent_round_timeout_seconds: 120
         round_timeout_grace_seconds: 60

Configuration Methods

---------------------

Method 1: CLI Flag (Highest Priority)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Override timeout for a single run:

.. code-block:: bash

   # Short timeout for simple task
   uv run python -m massgen.cli \
     --orchestrator-timeout 300 \
     --config config.yaml \
     "What are LLM agents?"

   # Longer timeout for complex research
   uv run python -m massgen.cli \
     --orchestrator-timeout 3600 \
     --config config.yaml \
     "Conduct comprehensive market analysis with 5 agents"

Method 2: Configuration File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set timeout in your YAML configuration:

.. code-block:: yaml

   # Basic configuration with custom timeout
   agents:
     - id: "agent1"
       backend:
         type: "gemini"
         model: "gemini-2.5-flash"

   timeout_settings:
     orchestrator_timeout_seconds: 900  # 15 minutes

   ui:
     display_type: "rich_terminal"

Method 3: Default (No Configuration)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If not specified, MassGen uses the default 30-minute timeout:

.. code-block:: yaml

   # This configuration will use default 1800s timeout
   agents:
     - id: "agent1"
       backend:
         type: "openai"
         model: "gpt-4o"

Timeout Behavior
----------------

What Happens When Timeout Occurs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When the orchestrator timeout is reached:

1. **Current coordination round completes** (not interrupted mid-operation)
2. **Partial results saved** (current state is preserved)
3. **Error message displayed** indicating timeout
4. **Graceful shutdown** (agents cleanup properly)

.. code-block:: text

   🔄 Round 5 of coordination...
   ⏰ Orchestrator timeout reached (1800 seconds)
   💾 Saving current state...
   ❌ Coordination incomplete - timeout exceeded

**Important**: The system attempts graceful termination. Individual agent operations may still complete if they're in progress.

Successful Completion Before Timeout
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If coordination completes normally:

.. code-block:: text

   ✅ Coordination complete!
   ⏱️  Total time: 245 seconds (well under 1800s limit)

Choosing the Right Timeout
---------------------------

Simple Tasks (5-10 minutes)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Recommended**: 300-600 seconds

.. code-block:: yaml

   timeout_settings:
     orchestrator_timeout_seconds: 600

**Examples**:

* Quick research questions
* Single-agent tasks
* Fast LLM models (GPT-4o-mini, Gemini Flash)
* Tasks with 2-3 agents

.. code-block:: bash

   uv run python -m massgen.cli \
     --orchestrator-timeout 600 \
     --model gemini-2.5-flash \
     "What are the key features of Python 3.12?"

Standard Tasks (15-30 minutes)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Recommended**: 900-1800 seconds (default)

.. code-block:: yaml

   timeout_settings:
     orchestrator_timeout_seconds: 1800  # Default

**Examples**:

* Multi-agent coordination (3-5 agents)
* Tasks with external API calls (MCP tools)
* Code generation with file operations
* Research with web search

.. code-block:: bash

   uv run python -m massgen.cli \
     --config multi_agent_config.yaml \
     "Analyze market trends and create a report"

Complex Tasks (30-60 minutes)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Recommended**: 1800-3600 seconds

.. code-block:: yaml

   timeout_settings:
     orchestrator_timeout_seconds: 3600  # 1 hour

**Examples**:

* Large-scale code refactoring
* Comprehensive research with many sources
* Tasks involving multiple API calls
* 5+ agents coordination
* Planning mode with extensive discussion

.. code-block:: bash

   uv run python -m massgen.cli \
     --orchestrator-timeout 3600 \
     --config five_agents_research.yaml \
     "Conduct a complete competitive analysis of the AI market"

Long-Running Tasks (60+ minutes)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Recommended**: 3600+ seconds

.. code-block:: yaml

   timeout_settings:
     orchestrator_timeout_seconds: 7200  # 2 hours

.. warning::

   Very long timeouts can lead to expensive API costs. Consider breaking down the task or using checkpoints.

**Examples**:

* Full codebase analysis
* Large-scale data processing
* Multi-stage project generation
* Complex multi-turn conversations

Examples by Task Type
----------------------

Example 1: Quick Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~

**Task**: Simple question, single agent

.. code-block:: bash

   uv run python -m massgen.cli \
     --orchestrator-timeout 300 \
     --backend openai \
     --model gpt-4o-mini \
     "Explain quantum entanglement in simple terms"

**Reasoning**: Single agent with fast model, expected completion in 1-2 minutes, 5-minute timeout gives buffer.

Example 2: Multi-Agent Research
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Task**: Three agents researching and comparing approaches

.. code-block:: yaml

   agents:
     - id: "researcher1"
       backend: {type: "gemini", model: "gemini-2.5-flash"}
     - id: "researcher2"
       backend: {type: "openai", model: "gpt-4o"}
     - id: "researcher3"
       backend: {type: "claude", model: "claude-sonnet-4"}

   timeout_settings:
     orchestrator_timeout_seconds: 1200  # 20 minutes

**Reasoning**: Multiple rounds of coordination expected, web search enabled, 20 minutes allows for thorough research and discussion.

Example 3: Code Generation with Files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Task**: Generate project structure with multiple files

.. code-block:: yaml

   agents:
     - id: "architect"
       backend: {type: "claude_code", cwd: "workspace"}
     - id: "reviewer"
       backend: {type: "gemini", model: "gemini-2.5-flash"}

   orchestrator:
     coordination:
       enable_planning_mode: true

   timeout_settings:
     orchestrator_timeout_seconds: 1800  # 30 minutes

**Reasoning**: Planning mode discussion + file creation, default 30 minutes is appropriate.

Example 4: MCP Tool Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Task**: Use multiple MCP tools with planning mode

.. code-block:: yaml

   agents:
     - id: "agent1"
       backend:
         type: "openai"
         model: "gpt-5-nano"
         mcp_servers:
           - {name: "weather", ...}
           - {name: "search", ...}

   orchestrator:
     coordination:
       enable_planning_mode: true

   timeout_settings:
     orchestrator_timeout_seconds: 2400  # 40 minutes

**Reasoning**: MCP tools may have API latency, planning mode adds coordination time, 40 minutes provides safety margin.

Troubleshooting
---------------

Timeouts Occurring Too Frequently
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptoms**:

* Tasks consistently hitting timeout
* Coordination incomplete messages
* Partial results only

**Solutions**:

1. **Increase timeout**:

   .. code-block:: yaml

      timeout_settings:
        orchestrator_timeout_seconds: 3600  # Double the default

2. **Reduce agent count**: Fewer agents = faster coordination

3. **Simplify task**: Break complex tasks into smaller subtasks

4. **Use faster models**: Consider GPT-4o-mini or Gemini Flash instead of larger models

5. **Disable planning mode** if not needed:

   .. code-block:: yaml

      orchestrator:
        coordination:
          enable_planning_mode: false

6. **Check for stuck agents**: Review debug logs for agents not responding

7. **Enable per-round timeouts**: Force agents to submit after a time limit:

   .. code-block:: yaml

      timeout_settings:
        initial_round_timeout_seconds: 600
        subsequent_round_timeout_seconds: 180

Tasks Completing Too Quickly
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptoms**:

* Coordination ends in seconds
* Agents immediately voting without discussion
* Short timeout may be unnecessarily limiting deeper analysis

**Solutions**:

* This is generally not a problem - fast completion is good!
* If you want more thorough discussion, adjust system messages to encourage analysis

Per-Round Timeout Issues
~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptoms**:

* Soft timeout message appears but agent keeps working
* Hard timeout blocks tools unexpectedly
* Agent submits incomplete work

**Solutions**:

1. **Increase grace period** if agents need more time to finish:

   .. code-block:: yaml

      timeout_settings:
        round_timeout_grace_seconds: 180  # 3 minutes instead of 2

2. **Increase initial timeout** for complex tasks:

   .. code-block:: yaml

      timeout_settings:
        initial_round_timeout_seconds: 900  # 15 minutes

3. **Check log messages** for timeout events:

   .. code-block:: text

      [RoundTimeoutPostHook] Soft timeout reached for agent_b after 605s
      [RoundTimeoutPreHook] Blocking mcp__filesystem__write_file for agent_b - hard timeout exceeded

4. **Disable per-round timeouts** by omitting the settings (they're disabled by default)

Timeout But No Error Message
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: Timeout occurs but no clear indication in output.

**Solution**: Enable debug logging:

.. code-block:: bash

   uv run python -m massgen.cli \
     --debug \
     --orchestrator-timeout 600 \
     --config config.yaml \
     "Your question"

Check logs in ``agent_outputs/log_{timestamp}/massgen_debug.log``

Best Practices
--------------

1. **Start with defaults**: Use the 30-minute default unless you have specific needs

2. **Adjust based on task complexity**:

   * Simple: 300-600s
   * Standard: 900-1800s
   * Complex: 1800-3600s
   * Very complex: 3600+s

3. **Consider cost implications**: Longer timeouts = potentially higher API costs

4. **Use CLI overrides for testing**: Test with shorter timeouts first

   .. code-block:: bash

      # Test with 5-minute timeout
      uv run python -m massgen.cli --orchestrator-timeout 300 --config test.yaml "test"

      # Then use full timeout for production
      uv run python -m massgen.cli --config prod.yaml "real task"

5. **Monitor actual completion times**: Check logs to see typical durations for your tasks

6. **Set appropriate timeouts per environment**:

   .. code-block:: yaml

      # Development config
      timeout_settings:
        orchestrator_timeout_seconds: 600  # Fast feedback

   .. code-block:: yaml

      # Production config
      timeout_settings:
        orchestrator_timeout_seconds: 3600  # Allow full completion

7. **Document timeout choices**: Add comments explaining timeout rationale

   .. code-block:: yaml

      timeout_settings:
        # 40 minutes: allows for 5 agents, planning mode, and MCP tool latency
        orchestrator_timeout_seconds: 2400

API Cost Considerations
-----------------------

Longer timeouts can lead to higher costs:

**Estimated API Costs by Timeout**:

.. list-table::
   :header-rows: 1
   :widths: 20 20 30 30

   * - Timeout
     - Typical Duration
     - 3-Agent Scenario
     - 5-Agent Scenario
   * - 5 min
     - 2-3 min
     - $0.10-0.50
     - $0.20-0.80
   * - 30 min (default)
     - 5-15 min
     - $0.50-2.00
     - $1.00-4.00
   * - 1 hour
     - 20-40 min
     - $2.00-5.00
     - $4.00-10.00
   * - 2 hours
     - 40-90 min
     - $5.00-15.00
     - $10.00-30.00

.. note::

   These are rough estimates. Actual costs depend on:

   * Models used (GPT-4 vs GPT-4o-mini, etc.)
   * Number of coordination rounds
   * Tool usage (MCP, code execution, web search)
   * Response lengths

**Cost-Saving Tips**:

1. Use shorter timeouts for testing
2. Choose efficient models (GPT-4o-mini, Gemini Flash)
3. Limit agent count for simple tasks
4. Monitor actual usage and adjust timeouts accordingly

Debug and Monitoring
--------------------

Viewing Timeout Information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Enable debug logging to see timeout details:

.. code-block:: bash

   uv run python -m massgen.cli --debug --config config.yaml "question"

Look for timeout-related messages in ``agent_outputs/log_{timestamp}/massgen_debug.log``:

.. code-block:: text

   [INFO] Orchestrator timeout configured: 1800 seconds
   [INFO] Starting coordination...
   [INFO] Round 1 complete (elapsed: 45s / 1800s)
   [INFO] Round 2 complete (elapsed: 128s / 1800s)
   ...

Monitoring Coordination Progress
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the terminal UI, watch for elapsed time indicators:

.. code-block:: text

   ┌─ Coordination Progress ─────────────────┐
   │ Round: 3/∞                              │
   │ Elapsed: 234s / 1800s (13%)             │
   │ Status: In progress                     │
   └──────────────────────────────────────────┘

Related Configuration
---------------------

* :doc:`../user_guide/concepts` - Understanding coordination mechanics
* :doc:`../user_guide/advanced/planning_mode` - Planning mode and coordination time
* :doc:`yaml_schema` - Complete configuration reference
* :doc:`cli` - CLI timeout flags

Next Steps
----------

* Test your configuration with appropriate timeouts
* Monitor actual completion times in your use cases
* Adjust timeouts based on observed patterns
* Consider cost vs. completion trade-offs
