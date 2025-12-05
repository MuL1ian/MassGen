Sessions & Memory
=================

MassGen provides robust session management and memory capabilities for interactive, multi-turn conversations with AI agents. This section covers how to maintain context, manage sessions, and work with persistent memory.

Overview
--------

Session features in MassGen:

* **Multi-turn mode** - Interactive conversations with persistent context
* **Memory management** - Long-term context preservation across sessions
* **Session restart** - Resume and continue previous sessions
* **Graceful cancellation** - Save partial progress when interrupting
* **Context windows** - Efficient handling of conversation history

Guides in This Section
----------------------

.. grid:: 3
   :gutter: 3

   .. grid-item-card:: 💬 Multi-Turn Mode

      Interactive conversations

      * Start interactive sessions
      * Conversation management
      * Session commands
      * Real-time agent responses

      :doc:`Read the Multi-Turn Mode guide → <multi_turn_mode>`

   .. grid-item-card:: 🧠 Memory

      Context preservation

      * Session memory
      * Memory archiving
      * Context management
      * Memory configuration

      :doc:`Read the Memory guide → <memory>`

   .. grid-item-card:: 🔄 Session Restart

      Resume previous sessions

      * Restart capabilities
      * Session recovery
      * State restoration
      * Continuation patterns

      :doc:`Read the Session Restart guide → <orchestration_restart>`

   .. grid-item-card:: ⏹️ Graceful Cancellation

      Save progress on interrupt

      * Ctrl+C handling
      * Partial progress saving
      * Resume cancelled sessions
      * Review partial answers

      :doc:`Read the Graceful Cancellation guide → <graceful_cancellation>`

Quick Start
-----------

Start an interactive multi-turn session:

.. tabs::

   .. tab:: CLI

      .. code-block:: bash

         # Start interactive mode
         massgen

         # Or with a specific config
         massgen --config @examples/basic/multi/three_agents_default

   .. tab:: Python API

      .. code-block:: python

         import asyncio
         import massgen

         # Multi-turn requires CLI for now
         # Use single queries for programmatic access
         result = await massgen.run(
             query="First question...",
             model="gpt-5"
         )

Related Documentation
---------------------

* :doc:`../files/memory_filesystem_mode` - Combine memory with file operations
* :doc:`../integration/automation` - Automated execution modes
* :doc:`../../quickstart/running-massgen` - Getting started with sessions
* :doc:`../../reference/cli` - CLI reference

.. toctree::
   :maxdepth: 1
   :hidden:

   multi_turn_mode
   memory
   orchestration_restart
   graceful_cancellation
