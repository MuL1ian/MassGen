===============================
Increasing Diversity in MassGen
===============================

Why Diversity Matters
=====================

In multi-agent systems, diversity drives better outcomes. When agents approach problems from different angles, they explore solution spaces more thoroughly, catch errors, and generate richer insights.

MassGen provides several mechanisms to increase diversity across agent teams:

1. **Answer Novelty Requirements** - Prevent agents from rephrasing existing answers
2. **Question Paraphrasing (DSPy)** - Give each agent a linguistically different question variant
3. **Persona Generation** - Automatically assign different perspectives or solution approaches to agents

.. contents:: Table of Contents
   :local:
   :depth: 2

Answer Novelty Requirements
============================

The ``answer_novelty_requirement`` setting ensures agents produce meaningfully different answers rather than just rephrasing existing solutions.

Configuration
-------------

Set under ``orchestrator`` in your config:

.. code-block:: yaml

   orchestrator:
     answer_novelty_requirement: "balanced"  # lenient|balanced|strict

Options
-------

.. list-table::
   :header-rows: 1
   :widths: 15 20 65

   * - Setting
     - Overlap Threshold
     - Description
   * - ``lenient``
     - No checks
     - No similarity checks (fastest, allows rephrasing)
   * - ``balanced``
     - >70% token overlap
     - Default. Rejects answers that are too similar, requires meaningful differences
   * - ``strict``
     - >50% token overlap
     - Only accepts substantially different solutions, prevents minor variations

How It Works
------------

When an agent provides a new answer, MassGen compares token overlap with existing answers:

* **Passes check**: Answer is novel enough, accepted
* **Fails check**: Agent receives error message explaining their answer is too similar and should use a fundamentally different approach or vote instead

Example
-------

.. code-block:: yaml

   orchestrator:
     voting_sensitivity: "balanced"
     max_new_answers_per_agent: 2
     answer_novelty_requirement: "balanced"  # Enforce meaningful differences

This prevents agents from making cosmetic changes and forces them to explore genuinely different approaches.

Question Paraphrasing with DSPy
================================

DSPy integration provides **intelligent question paraphrasing** - each agent receives a semantically equivalent but differently worded version of your question, encouraging diverse interpretations.

Quick Start
-----------

**1. Install DSPy:**

.. code-block:: bash

   pip install 'dspy>=2.4.0'

**2. Configure in your YAML:**

.. code-block:: yaml

   orchestrator:
     dspy:
       enabled: true
       backend:
         type: "gemini"
         model: "gemini-3-flash-preview"
       num_variants: 3
       strategy: "balanced"

**3. Run MassGen:**

.. code-block:: bash

   massgen --config my_config.yaml "Explain quantum computing"

You'll see: ``✅ DSPy question paraphrasing enabled (strategy=balanced, variants=3)``

Configuration Reference
-----------------------

Main Settings
~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Parameter
     - Type
     - Default
     - Description
   * - ``enabled``
     - boolean
     - ``false``
     - Enable DSPy paraphrasing
   * - ``backend``
     - object
     - \-
     - LLM config for paraphrase generation (required)
   * - ``num_variants``
     - integer
     - ``3``
     - Number of paraphrase variants (1-10 recommended)
   * - ``strategy``
     - string
     - ``balanced``
     - ``balanced`` | ``diverse`` | ``conservative`` | ``adaptive``
   * - ``cache_enabled``
     - boolean
     - ``true``
     - Cache paraphrases for repeated questions
   * - ``semantic_threshold``
     - float
     - ``0.85``
     - Validation strictness (0.0-1.0)
   * - ``validate_semantics``
     - boolean
     - ``true``
     - Verify paraphrases ask for same information

Backend Configuration
~~~~~~~~~~~~~~~~~~~~~

Under ``orchestrator.dspy.backend``:

.. code-block:: yaml

   backend:
     type: "gemini"              # openai|anthropic|gemini|lmstudio|vllm|cerebras
     model: "gemini-3-flash-preview"   # Required
     api_key: "..."              # Optional (uses env var if omitted)
     temperature: 0.7            # Optional (overrides strategy temps)
     max_tokens: 150             # Optional

Paraphrasing Strategies
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Strategy
     - Temperature Pattern
     - Best For
   * - ``balanced``
     - [0.5, 0.6, 0.7]
     - General use (default)
   * - ``diverse``
     - [0.3, 0.6, 0.9]
     - Maximum linguistic variation
   * - ``conservative``
     - [0.3, 0.4, 0.5]
     - Technical/scientific accuracy
   * - ``adaptive``
     - [0.3, 0.5, 0.7, 0.9]
     - Mixed question types

How It Works
------------

1. **Generate**: DSPy creates N paraphrased variants of your question
2. **Validate**: Each variant is checked for semantic equivalence and quality
3. **Assign**: Paraphrases are distributed round-robin to agents
4. **Process**: Each agent receives both original and paraphrased version
5. **Fallback**: If generation fails, agents receive original question (coordination continues)

Example Workflow
~~~~~~~~~~~~~~~~

.. code-block:: text

   Original: "Explain quantum computing"

   Agent 1 receives: "Can you explain what quantum computing is?"
   Agent 2 receives: "What is quantum computing and how does it work?"
   Agent 3 receives: "Please describe quantum computing principles"

Each agent interprets the question slightly differently, leading to more diverse initial answers.

Configuration Examples
----------------------

Cost-Optimized
~~~~~~~~~~~~~~

.. code-block:: yaml

   orchestrator:
     dspy:
       enabled: true
       backend:
         type: "openai"
         model: "gpt-4o-mini"      # Cheaper model
         max_tokens: 100
       num_variants: 2              # Fewer variants
       strategy: "conservative"
       use_chain_of_thought: false
       cache_enabled: true

High-Quality
~~~~~~~~~~~~

.. code-block:: yaml

   orchestrator:
     dspy:
       enabled: true
       backend:
         type: "openai"
         model: "gpt-4o"
       num_variants: 4
       strategy: "diverse"          # Maximum variation
       use_chain_of_thought: true   # Better reasoning (higher cost)
       semantic_threshold: 0.90     # Stricter validation

Local LLM
~~~~~~~~~

.. code-block:: yaml

   orchestrator:
     dspy:
       enabled: true
       backend:
         type: "lmstudio"
         model: "your-local-model"
         base_url: "http://localhost:1234/v1"
       num_variants: 3
       strategy: "balanced"

Troubleshooting
---------------

**Installation Issues**

.. code-block:: bash

   pip install 'dspy>=2.4.0'
   pip show dspy  # Verify version

**API Key Issues**

Set environment variables:

.. code-block:: bash

   export OPENAI_API_KEY="sk-..."
   export ANTHROPIC_API_KEY="sk-ant-..."
   export GOOGLE_API_KEY="..."

**Generation Failures**

If DSPy fails, the system falls back to original question - coordination continues normally. Check:

1. Backend connectivity and model availability
2. API key validity and credits
3. Logs for detailed error messages

**Low Quality Paraphrases**

Try:

* ``strategy: "diverse"`` for more variation
* ``semantic_threshold: 0.90`` for stricter validation
* ``use_chain_of_thought: true`` for better reasoning
* ``temperature_range: [0.5, 1.0]`` for custom temperature control

.. seealso::
   **Detailed Implementation Guide**: See ``massgen/backend/docs/DSPY_IMPLEMENTATION_GUIDE.md`` for comprehensive technical documentation including temperature scheduling formulas, validation mechanisms, and debugging.

Persona Generation
==================

The persona generator automatically assigns different perspectives or approaches to each agent, encouraging diverse solutions without manual configuration.

Quick Start
-----------

Enable persona generation in your config:

.. code-block:: yaml

   orchestrator:
     coordination:
       persona_generator:
         enabled: true
         diversity_mode: "perspective"  # or "implementation"

Configuration Reference
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Parameter
     - Type
     - Default
     - Description
   * - ``enabled``
     - boolean
     - ``false``
     - Enable automatic persona generation
   * - ``diversity_mode``
     - string
     - ``perspective``
     - Type of diversity to encourage (see below)
   * - ``persist_across_turns``
     - boolean
     - ``false``
     - If true, reuse personas across turns. If false (default), generate fresh personas each turn.
   * - ``backend``
     - object
     - (inherited)
     - Optional LLM config for persona generation

Diversity Modes
~~~~~~~~~~~~~~~

**perspective** (default)
   Agents receive different *values and priorities* for the same problem. Each agent optimizes
   for different qualities (e.g., simplicity vs robustness, user experience vs maintainability).

   Example personas:

   * "Prioritize long-term maintainability and clean architecture over quick solutions"
   * "Optimize for the end user's experience - make it intuitive and delightful"

**implementation**
   Agents receive different *solution types or interpretations*. Each agent explores a
   fundamentally different kind of solution to the problem.

   Example personas:

   * "Explore a minimalist, single-page approach focusing on essential content"
   * "Consider a rich, interactive experience with dynamic elements"

**Future: combined**
   A mixed mode combining both perspective and implementation diversity is planned for future releases.

Phase-Based Adaptation
----------------------

Persona injection adapts based on the coordination phase:

**Exploration Phase** (no answers seen yet)
   Agents receive their full perspective to encourage diverse initial solutions.

**Convergence Phase** (after seeing other answers)
   Perspectives are softened to encourage objective evaluation across all approaches.
   Agents are reminded to evaluate ALL solutions on merit rather than defending their original perspective.

This prevents personas from blocking convergence after restarts - agents naturally shift from
"generate diverse ideas" to "find the best solution across all ideas."

How It Works
------------

1. **Generate**: Before agents start, the system generates complementary perspectives
2. **Assign**: Each agent receives a unique persona as part of their system message
3. **Adapt**: Persona text adjusts based on whether the agent has seen other solutions
4. **Preserve**: User-specified system prompts are preserved; personas are prepended

Example Configuration
---------------------

Full configuration with all options:

.. code-block:: yaml

   orchestrator:
     coordination:
       persona_generator:
         enabled: true
         diversity_mode: "perspective"
         backend:
           type: "gemini"
           model: "gemini-3-flash-preview"

With implementation diversity:

.. code-block:: yaml

   orchestrator:
     coordination:
       persona_generator:
         enabled: true
         diversity_mode: "implementation"

Combining Diversity Methods
============================

For maximum diversity, combine multiple techniques:

.. code-block:: yaml

   orchestrator:
     # Enforce different solutions
     answer_novelty_requirement: "balanced"
     max_new_answers_per_agent: 2

     # Linguistic diversity via DSPy
     dspy:
       enabled: true
       backend:
         type: "gemini"
         model: "gemini-3-flash-preview"
       num_variants: 3
       strategy: "diverse"

     # Conceptual diversity via personas
     coordination:
       persona_generator:
         enabled: true
         diversity_mode: "perspective"

This configuration ensures:

1. Each agent receives a different question phrasing (DSPy)
2. Each agent has a different perspective/priority (persona generator)
3. Agents must provide meaningfully different answers (novelty requirement)
4. Limited attempts encourage quality over iteration (max_new_answers)

When to Use What
================

**Answer Novelty Requirement**

* ✅ Always recommended for multi-agent setups
* ✅ Prevents wasted cycles on superficial changes
* Use ``balanced`` by default, ``strict`` for critical tasks

**DSPy Question Paraphrasing**

* ✅ Complex queries benefiting from multiple interpretations
* ✅ Multi-agent systems seeking diverse perspectives
* ❌ Skip for single-agent or simple factual queries (adds overhead)

**Persona Generation**

* ✅ Multi-agent systems where conceptual diversity matters
* ✅ Creative tasks benefiting from different approaches or interpretations
* ✅ Use ``perspective`` mode for different values/priorities
* ✅ Use ``implementation`` mode for different solution types
* ❌ Skip for single-agent setups (no benefit)

Summary
=======

MassGen's diversity framework includes:

**Current Features:**

1. **Answer Novelty Requirements** - Prevents rephrasing, enforces meaningful differences
2. **DSPy Question Paraphrasing** - Linguistic diversity through intelligent paraphrasing
3. **Persona Generation** - Conceptual diversity through automatically assigned perspectives

   * ``perspective`` mode: Different values and priorities
   * ``implementation`` mode: Different solution types and interpretations
   * Phase-based adaptation: Strong perspectives for exploration, softened for convergence

**Future Features:**

4. **Combined Diversity Mode** - Mix perspective and implementation diversity in a single run

Use these techniques individually or combined to maximize the quality and breadth of multi-agent coordination.

**Next Steps:**

* :doc:`../../reference/yaml_schema` - Complete configuration reference
* :doc:`../backends` - Backend capabilities matrix
* :doc:`../../examples/basic_examples` - Working examples
