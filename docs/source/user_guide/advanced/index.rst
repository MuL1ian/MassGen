Advanced Features
=================

This section covers advanced MassGen capabilities for power users, including multi-agent coordination, multimodal processing, and specialized automation features.

Overview
--------

Advanced features in MassGen:

* **Agent diversity** - Configure multiple agents with different models and behaviors
* **Agent communication** - Enable agents to ask each other questions
* **Task planning** - Structured task breakdown and execution
* **Subagents** - Spawn parallel child processes for independent tasks
* **Planning mode** - Safe execution with human approval
* **Multimodal support** - Image, audio, and video understanding
* **Computer use** - Browser and desktop automation
* **Terminal evaluation** - Record and evaluate terminal sessions

Guides in This Section
----------------------

.. grid:: 2
   :gutter: 3

   .. grid-item-card:: 🎭 Agent Diversity

      Configure diverse agent teams

      * Different models per agent
      * Varied system prompts
      * Specialization strategies
      * Voting and consensus

      :doc:`Read the Diversity guide → <diversity>`

   .. grid-item-card:: 💬 Agent Communication

      Enable inter-agent messaging

      * ask_others tool
      * Agent collaboration patterns
      * Information sharing
      * Coordination strategies

      :doc:`Read the Agent Communication guide → <agent_communication>`

   .. grid-item-card:: 📋 Task Planning

      Structured task execution

      * Task breakdown
      * Planning strategies
      * Execution tracking
      * Complex workflows

      :doc:`Read the Task Planning guide → <agent_task_planning>`

   .. grid-item-card:: 🔀 Subagents

      Parallel child processes

      * Independent workspaces
      * Concurrent execution
      * Context file sharing
      * Result aggregation

      :doc:`Read the Subagents guide → <subagents>`

   .. grid-item-card:: ✅ Planning Mode

      Safe execution with approval

      * Human-in-the-loop
      * Plan review
      * Action confirmation
      * Rollback support

      :doc:`Read the Planning Mode guide → <planning_mode>`

   .. grid-item-card:: 🖼️ Multimodal

      Image, audio, video support

      * Image understanding
      * Audio transcription
      * Video analysis
      * Multi-format input

      :doc:`Read the Multimodal guide → <multimodal>`

   .. grid-item-card:: 🖥️ Computer Use

      Browser and desktop automation

      * Gemini Computer Use
      * Claude Computer Use
      * Browser automation
      * Visual feedback

      :doc:`Read the Computer Use guide → <computer_use>`

   .. grid-item-card:: 📺 Terminal Evaluation

      Record and evaluate sessions

      * VHS recording
      * Session playback
      * Evaluation metrics
      * Demonstration creation

      :doc:`Read the Terminal Evaluation guide → <terminal_evaluation>`

Related Documentation
---------------------

* :doc:`../concepts` - Core MassGen concepts
* :doc:`../backends` - Backend capabilities
* :doc:`../tools/index` - Tools and capabilities
* :doc:`../integration/index` - Integration options

.. toctree::
   :maxdepth: 1
   :hidden:

   diversity
   agent_communication
   agent_task_planning
   subagents
   planning_mode
   multimodal
   computer_use
   terminal_evaluation
