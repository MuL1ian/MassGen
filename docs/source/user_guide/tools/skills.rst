.. _user_guide_skills:

==========================
Skills System
==========================

The Skills System extends agent capabilities with specialized knowledge and workflows using `openskills <https://github.com/numman-ali/openskills>`_. Skills are modular, self-contained packages that provide domain-specific guidance and tools.

Overview
========

Skills transform agents from general-purpose to specialized agents with:

* **Domain Knowledge**: Specialized expertise (e.g., PDF manipulation, spreadsheet analysis)
* **Workflow Guidance**: Step-by-step procedures for complex tasks
* **Tool Integration**: Pre-configured toolchains for specific domains
* **Filesystem-Based**: Transparent, version-controllable approach

When enabled, agents can invoke skills via bash commands to access domain-specific guidance.

.. note::
   Skills complement MCP tools but work via filesystem instead of MCP protocol. This provides better transparency and allows skills to be version-controlled.

.. important::
   **Model Recommendations**: Skills work best with frontier models (Claude Sonnet/Opus, GPT-5). Smaller models like gpt-5-mini and gpt-5-nano may not reliably recognize when to invoke skills or may skip skill invocation in favor of attempting tasks directly.

Installation
============

Install openskills and Anthropic's skills collection:

.. code-block:: bash

   # Install openskills CLI
   npm install -g openskills

   # Install Anthropic's skills collection
   openskills install anthropics/skills --universal -y

This creates ``.agent/skills/`` directory with all available skills.

.. note::
   Skills work with both Docker mode (``command_line_execution_mode: "docker"``) and local mode (``command_line_execution_mode: "local"``).

   - **Docker mode**: Skills and dependencies (ripgrep, ast-grep) are pre-installed in the container
   - **Local mode**: You need to install dependencies manually (``brew install ripgrep ast-grep`` on macOS)

Configuration
=============

Basic Configuration
-------------------

Enable skills in your YAML config:

.. code-block:: yaml

   agents:
     Agent1:
       backend_name: "Anthropic"
       backend_params:
         model: "claude-sonnet-4"
         # REQUIRED: Skills need command line access
         enable_mcp_command_line: true
         command_line_execution_mode: "docker"  # or "local"

   orchestrator:
     coordination:
       # Enable skills system
       use_skills: true

       # Optional: Skills directory (default: .agent/skills)
       skills_directory: ".agent/skills"

.. important::
   **Skills require command line execution** (``enable_mcp_command_line: true``) to be enabled for at least one agent.

With Task Planning
------------------

Combine skills with task planning (filesystem mode):

.. code-block:: yaml

   orchestrator:
     coordination:
       use_skills: true
       enable_agent_task_planning: true
       task_planning_filesystem_mode: true  # Save tasks to tasks/ directory

This creates a ``tasks/`` directory in the agent workspace:

.. code-block:: text

   agent_workspace/
     └── tasks/
         └── plan.json        # Task planning state

With Memory System
------------------

Combine skills with filesystem-based memory:

.. code-block:: yaml

   orchestrator:
     coordination:
       use_skills: true
       enable_memory_filesystem_mode: true

This creates a two-tier memory structure:

.. code-block:: text

   agent_workspace/
     └── memory/
         ├── short_term/      # Auto-injected into system prompts
         └── long_term/       # Load on-demand via MCP tools

With Previous Session Skills
-----------------------------

Enable discovery of evolving skills from previous MassGen sessions:

.. code-block:: yaml

   orchestrator:
     coordination:
       use_skills: true
       load_previous_session_skills: true  # Discover skills from past sessions

When enabled, MassGen scans ``.massgen/massgen_logs/`` for evolving skills (``SKILL.md`` files) created by agents in previous sessions. These skills appear in the system prompt with ``<location>previous_session</location>``.

**Path structure scanned:**

.. code-block:: text

   .massgen/massgen_logs/
     └── log_YYYYMMDD_HHMMSS/
         └── turn_N/
             └── attempt_N/
                 └── final/
                     └── agent_X/
                         └── workspace/
                             └── tasks/
                                 └── evolving_skill/
                                     └── SKILL.md  # Discovered as previous_session skill

Complete Setup (All Features)
------------------------------

For full coordination capabilities:

.. code-block:: yaml

   orchestrator:
     coordination:
       use_skills: true
       enable_agent_task_planning: true
       task_planning_filesystem_mode: true
       enable_memory_filesystem_mode: true
       load_previous_session_skills: true  # Optional: load skills from previous sessions

This creates:

.. code-block:: text

   agent_workspace/
     ├── memory/
     │   ├── short_term/
     │   └── long_term/
     └── tasks/
         └── plan.json

Built-in Skills
===============

MassGen includes built-in skills bundled in ``massgen/skills/``:

**Code Search & Understanding:**

* ``file-search`` - Fast text and structural code search (ripgrep/ast-grep)
* ``serena`` - Symbol-level code understanding using LSP
* ``semtools`` - Semantic search using embeddings

**Workflow & Skills (Code Mode):**

* ``evolving-skill-creator`` - Central planning mechanism for code-based workflows. Creates structured workflow plans that inventory MCP servers, custom tools, skills, and capture learnings for reuse in future sessions

**Meta-Development (MassGen develops MassGen):**

* ``massgen-config-creator`` - Config creation guidance and best practices
* ``massgen-develops-massgen`` - Self-development workflows (automation + visual evaluation)
* ``massgen-release-documenter`` - Release documentation process
* ``model-registry-maintainer`` - Model registry maintenance

All skills are invoked the same way using ``openskills read <skill-name>``.

.. note::
   **Lightweight Guidance**: When command execution is enabled, agents automatically receive lightweight file search guidance (~30 lines) in their system prompt. For comprehensive documentation, invoke: ``openskills read file-search``

File Search
-----------

Fast text and structural code search using ripgrep and ast-grep.

**Lightweight Guidance (Always Available):**

When command execution is enabled, agents automatically see basic usage:

.. code-block:: bash

   # Text search with ripgrep
   rg "pattern" --type py --type js

   # Structural search with ast-grep
   sg --pattern 'function $NAME($$$) { $$$ }' --lang js

**Full Skill Content:**

.. code-block:: bash

   # Load comprehensive 280-line guide with targeting strategies
   openskills read file-search

**Best for:**

* Finding code patterns
* Analyzing codebases
* Refactoring workflows
* Fast keyword searches

Serena
------

Symbol-level code understanding using Language Server Protocol (LSP). Provides IDE-like capabilities for finding symbols, tracking references, and making precise code edits.

**Prerequisites:**

.. code-block:: bash

   # Use uvx to run serena on-demand (no permanent installation)
   uvx --from git+https://github.com/oraios/serena serena --help

   # Works in both Docker mode (uv pre-installed) and local mode
   # For local mode, install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh

**Invocation:**

.. code-block:: bash

   # Load serena skill guidance
   openskills read serena

**Core Capabilities:**

* **find_symbol**: Locate class, function, or variable definitions
* **find_referencing_symbols**: Find all locations where a symbol is used
* **insert_after_symbol**: Make precise code insertions at symbol level

**Usage:**

.. code-block:: bash

   # Read skill guidance
   openskills read serena

   # Find symbol definitions (after reading skill)
   serena find_symbol --name 'UserService' --type class

   # Find all references
   serena find_referencing_symbols --name 'authenticate'

   # Insert code at symbol location
   serena insert_after_symbol --name 'MyClass' --type class --code '...'

**Best for:**

* Understanding symbol relationships and dependencies
* Impact analysis before refactoring
* Precise code insertions at symbol level
* Tracking all usages of functions/classes
* Working with large, complex codebases

**Supported Languages:**

Python, JavaScript, TypeScript, Rust, Go, Java, C/C++, C#, Ruby, PHP, and 20+ more languages through LSP.

Semtools Skill
--------------

Semantic search using embedding-based similarity matching. Find code by meaning, not just keywords.

**Prerequisites:**

.. code-block:: bash

   # Install via npm (recommended)
   npm install -g @llamaindex/semtools

   # Or via cargo
   cargo install semtools

   # Optional: For document parsing (PDF, DOCX, PPTX)
   export LLAMA_CLOUD_API_KEY="your-key"

**Invocation:**

.. code-block:: bash

   # Load semtools skill guidance
   openskills read semtools

**Core Capabilities:**

* **Semantic Search**: Find code by meaning, not exact keywords
* **Workspace Management**: Cache embeddings for fast repeated searches
* **Document Parsing**: Convert PDFs, DOCX, PPTX to searchable text (optional)

**Usage:**

.. code-block:: bash

   # Read skill guidance
   openskills read semtools

   # Semantic search by concept (after reading skill)
   search "authentication logic" src/

   # Search with more results
   search "error handling" --top-k 10 --n-lines 5

   # Create workspace for large codebases
   workspace use my-project
   export SEMTOOLS_WORKSPACE=my-project

   # Parse documents (requires API key)
   parse research_papers/*.pdf

**Best for:**

* Finding code when you know the concept but not the keywords
* Discovering semantically similar implementations
* Searching across different terminology/languages
* Document analysis and research
* Exploratory code discovery

**Note:**

* Semantic search works **locally** without API keys
* Document parsing (PDF/DOCX) requires LlamaIndex Cloud API key
* Embeddings are computed locally using model2vec

Meta-Development Skills
------------------------

MassGen includes four skills that enable agents to develop and improve MassGen itself. These skills provide structured workflows and best practices for common development tasks.

MassGen Config Creator
~~~~~~~~~~~~~~~~~~~~~~

Guides agents in creating properly structured YAML configuration files.

**Invocation:**

.. code-block:: bash

   openskills read massgen-config-creator

**Key Features:**

* Enforces "read existing configs first, never invent properties" rule
* References authoritative documentation (``docs/source/development/writing_configs.rst``)
* Property placement reference (backend-level vs orchestrator-level)
* File naming and location conventions
* Common pattern templates (single agent, multi-agent, with filesystem)

**Use Cases:**

* Creating example configs for new features
* Writing configs for case studies
* Building reusable multi-agent workflows
* Testing backend/tool integrations

**Example:**

.. code-block:: bash

   # Agent uses skill to create a config
   openskills read massgen-config-creator
   # Follows guidance to create properly structured config

MassGen Develops MassGen
~~~~~~~~~~~~~~~~~~~~~~~~~

Guides agents in using MassGen to develop itself through two distinct workflows.

**Invocation:**

.. code-block:: bash

   openskills read massgen-develops-massgen

**Workflow 1: Automation Mode** (Functional Testing)

* Run MassGen in ``--automation`` mode for clean, parseable output
* Monitor progress via ``status.json`` file
* Parse log directory and results programmatically
* Create background monitoring tasks (token usage, errors, progress, coordination)
* Test backend functionality, coordination logic, agent responses

**Workflow 2: Visual Evaluation** (UX Testing)

* Pre-test with ``--automation`` to validate config (REQUIRED)
* Record rich terminal display with VHS (without ``--automation``)
* Analyze videos with ``understand_video`` tool
* Evaluate terminal UX: clarity, layout, status indicators, user experience

**Additional Guidance:**

* Model selection guidelines (prefer recent mid-tier models)
* Config generation patterns
* Docker considerations (automatic detection and mode switching)
* Timing expectations and monitoring best practices

**Use Cases:**

* Testing new features programmatically
* Evaluating terminal UI/UX quality
* Creating case study demos with recordings
* Running experiments with MassGen configs

MassGen Release Documenter
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Guides agents through the complete release documentation workflow.

**Invocation:**

.. code-block:: bash

   openskills read massgen-release-documenter

**Documentation Order (CRITICAL):**

1. CHANGELOG.md (START HERE)
2. Sphinx Documentation (docs/source/)
3. Config Documentation (massgen/configs/README.md)
4. Case Studies (docs/source/examples/case_studies/)
5. README.md
6. README_PYPI.md (auto-synced via pre-commit)
7. Roadmap (ROADMAP.md)

**Key Features:**

* Phase-by-phase release checklist
* Commit message templates
* PR creation workflow
* Tag release instructions
* Validation checklist
* Backend update guidance (config_builder.py, capabilities.py)

**Use Cases:**

* Preparing documentation for new releases
* Updating CHANGELOG.md
* Writing case studies
* Following release checklist process

**References:** Primary source of truth is ``docs/dev_notes/release_checklist.md``

Model Registry Maintainer
~~~~~~~~~~~~~~~~~~~~~~~~~~

Guides agents in maintaining MassGen's model and backend registry.

**Invocation:**

.. code-block:: bash

   openskills read model-registry-maintainer

**Two Files to Maintain:**

1. ``massgen/backend/capabilities.py`` - Models, capabilities, release dates
2. ``massgen/token_manager/token_manager.py`` - Pricing, context windows

**Pricing Resolution Order:**

1. LiteLLM database (500+ models, fetched on-demand, cached 1 hour)
2. Hardcoded PROVIDER_PRICING (fallback only)
3. Pattern matching heuristics

**Information Gathered for New Models:**

* Release date (format: "YYYY-MM")
* Context window and max output tokens
* Pricing (input/output per 1K tokens)
* Capabilities (web search, code execution, vision, etc.)
* Exact API identifier

**Programmatic Updates:**

* LiteLLM pricing database integration
* OpenRouter API for real-time data
* Provider-specific API guidance
* Automation script template

**Current Coverage:**

* OpenAI: GPT-5 family, GPT-4.1 family, o4-mini
* Claude: Sonnet 4.5, Haiku 4.5, Opus 4.1
* Gemini: 3-pro-preview, 2.5-pro, 2.5-flash
* Grok: 4.1 family, 4 family, 3 family

**Use Cases:**

* Adding new models from providers
* Updating model pricing
* Maintaining context window information
* Keeping registry current with provider releases

Choosing Between Search Tools
------------------------------

MassGen provides three complementary search approaches:

+------------------+----------------------+------------------------+---------------------------+
| Tool             | Search Type          | Best For               | Example                   |
+==================+======================+========================+===========================+
| **file-search**  | Text/Syntax          | Exact keywords,        | Find "LoginService" class |
| (ripgrep/ast-grep)|                     | code patterns          |                           |
+------------------+----------------------+------------------------+---------------------------+
| **serena**       | Symbols/References   | Finding definitions,   | Track all uses of         |
|                  |                      | tracking usage         | authenticate()            |
+------------------+----------------------+------------------------+---------------------------+
| **semtools**     | Semantic/Meaning     | Concept discovery,     | Find "rate limiting"      |
|                  |                      | similar code           | implementations           |
+------------------+----------------------+------------------------+---------------------------+

**Search Strategy:**

1. **Concept Discovery**: Use semtools to find relevant areas
2. **Symbol Tracking**: Use serena to track precise definitions and references
3. **Text Search**: Use file-search (ripgrep) for exact keyword follow-up

**Example Workflow:**

.. code-block:: bash

   # 1. Discover authentication-related code semantically
   search "user authentication" src/

   # 2. Find exact class definition
   uvx --from git+https://github.com/oraios/serena serena find_symbol --name 'AuthService' --type class

   # 3. Track all references
   uvx --from git+https://github.com/oraios/serena serena find_referencing_symbols --name 'AuthService'

   # 4. Search for specific patterns
   rg "AuthService\(" --type py src/

External Skills
===============

Anthropic Skills Collection
----------------------------

When you install ``anthropics/skills``, you get access to:

* **pdf**: PDF manipulation toolkit
* **xlsx**: Spreadsheet creation and analysis
* **pptx**: PowerPoint presentation generation
* **docx**: Word document processing
* **skill-creator**: Guide for creating custom skills
* **And more...**

Using External Skills
---------------------

1. **Discover available skills:**

   Agents see skills listed in their system prompt automatically.

2. **Invoke a skill:**

   .. code-block:: bash

      openskills read pdf

   This loads the PDF skill's guidance and instructions.

3. **Follow skill guidance:**

   The skill content provides step-by-step instructions, examples, and best practices.

Evolving Skills (Code Mode)
---------------------------

Evolving skills are the **central planning mechanism** for code-based workflows. When agents enable ``auto_discover_custom_tools: true`` (code mode), they create evolving skills that:

1. **Structure Task Planning**: Enhanced task planning with explicit workflow documentation
2. **Discover Available Tools**: Structured sections for MCP servers, custom tools, and other skills
3. **Create Reusable Scripts**: Python tools that persist for future use
4. **Capture Learnings**: What worked, what didn't, and tips for iteration

**Why Use Evolving Skills:**

Rather than ad-hoc task execution, evolving skills provide a structured approach where agents:

- **Plan before executing**: Document the workflow upfront
- **Inventory available resources**: Explicitly list MCP servers, custom tools, and skills to use
- **Build reusable tools**: Create Python scripts that become part of the skill
- **Learn and improve**: Capture learnings for the skill to improve over iterations

**Creating Evolving Skills:**

Invoke the built-in ``evolving-skill-creator`` skill:

.. code-block:: bash

   openskills read evolving-skill-creator

**Directory Structure:**

.. code-block:: text

   tasks/evolving_skill/
   ├── SKILL.md              # Workflow plan with structured sections
   └── scripts/              # Python tools created during execution
       ├── scrape_data.py
       └── generate_output.py

**Key Sections in SKILL.md:**

.. code-block:: markdown

   ---
   name: artist-website-builder  # Descriptive, reusable name
   description: Build static biographical websites for artists
   ---

   # Artist Website Builder

   ## Workflow
   Detailed numbered steps...

   ## Tools to Create
   Python scripts to build (documented BEFORE writing):
   - scripts/fetch_data.py: Purpose, inputs, outputs, dependencies

   ## Tools to Use
   Available resources discovered in the workspace:
   - servers/context7: Documentation fetching
   - custom_tools/image_optimizer: Asset compression

   ## Skills
   Other skills that can help:
   - web-scraping-patterns: Crawling approach guidance

   ## Packages
   Dependencies to install:
   - crawl4ai, jinja2

   ## Learnings
   (Updated after execution)

**Important:** The ``SKILL.md`` must have proper YAML frontmatter with ``name`` and ``description`` fields for the skill to be discoverable in future sessions. Use descriptive names like ``artist-website-builder``, not instance-specific names like ``bob-dylan-project``.

**Loading in Future Sessions:**

Enable ``load_previous_session_skills: true`` to automatically discover evolving skills from previous sessions. This allows agents to build on previous work and reuse tools/workflows. See :ref:`With Previous Session Skills <user_guide_skills>`.

Creating Custom Skills
----------------------

Follow the ``skill-creator`` skill guidance:

.. code-block:: bash

   openskills read skill-creator

Or create manually:

1. Create skill directory:

   .. code-block:: bash

      mkdir .agent/skills/my-skill

2. Create ``SKILL.md`` with YAML frontmatter:

   .. code-block:: markdown

      ---
      name: my-skill
      description: Brief description of what this skill does
      ---

      # My Skill

      Detailed guidance and instructions...

3. Skill is automatically discovered when ``use_skills: true``

How Skills Work
===============

Discovery
---------

When ``use_skills: true``:

1. MassGen scans ``.agent/skills/`` (external) and ``massgen/skills/`` (built-in)
2. Parses ``SKILL.md`` files for metadata
3. Builds skills table in agent system prompt

Skills Table
------------

Agents see available skills in their system prompt:

.. code-block:: xml

   <skills_system priority="1">

   ## Available Skills

   <available_skills>

   <skill>
   <name>pdf</name>
   <description>PDF manipulation toolkit...</description>
   <location>project</location>
   </skill>

   <skill>
   <name>file-search</name>
   <description>Fast text and structural code search...</description>
   <location>builtin</location>
   </skill>

   </available_skills>

   </skills_system>

Invocation
----------

Agents invoke skills using bash:

.. code-block:: bash

   openskills read <skill-name>

This loads the skill's full content and guidance.

Best Practices
==============

When to Use Skills
------------------

**Use skills when:**

* Task requires domain-specific knowledge
* Workflow is complex and benefits from guidance
* Want transparency (filesystem > MCP state)
* Multiple agents need to coordinate

**Don't use skills when:**

* Simple, one-off tasks
* MCP tools are sufficient
* Command line execution not available

Skill Selection
---------------

1. **Check available skills** in the system prompt first
2. **Read skill content** before using
3. **Follow skill guidance** - they provide best practices
4. **Don't mix approaches** - if using a skill, follow its patterns

Memory Management
-----------------

1. **Be selective** - only save important information
2. **Use clear names** - descriptive filenames
3. **Structured data** - JSON for data, Markdown for docs
4. **Clean up** - remove outdated memories

File Searching
--------------

1. **Start broad** - simple patterns first
2. **Add filters** - use file type and directory filters
3. **Use context** - ``-C`` flag shows surrounding code
4. **Combine tools** - ripgrep for text, ast-grep for structure

Troubleshooting
===============

Skills Not Found
----------------

**Error:** ``Skills directory is empty or doesn't exist``

**Solution:**

.. code-block:: bash

   # Local users: Install openskills
   npm install -g openskills
   openskills install anthropics/skills --universal -y

   # Docker users: Skills should be pre-installed
   # If missing, rebuild Docker image

Command Execution Required
---------------------------

**Error:** ``Skills require command line execution``

**Solution:**

Add to agent config:

.. code-block:: yaml

   agents:
     Agent1:
       backend_params:
         enable_mcp_command_line: true
         command_line_execution_mode: "docker"  # or "local"

Skill Not Appearing
-------------------

**Problem:** Installed skill not showing in skills table

**Solutions:**

1. Check skills directory path in config
2. Verify ``SKILL.md`` has YAML frontmatter
3. Check file permissions
4. Try ``openskills list`` to see installed skills

Performance Considerations
==========================

Skill Discovery Cost
--------------------

* Skills are scanned once at orchestration startup
* Minimal overhead for small skill collections
* For 50+ skills, consider using specific skills directory

System Prompt Size
------------------

* Skills table adds to system prompt length
* ~100 tokens per skill in the table
* Full skill content loaded on-demand via ``openskills read``

Integration with Other Features
================================

With Filesystem
---------------

Skills work seamlessly with filesystem features:

* ``memory/`` for skill-specific memory
* ``temp_workspaces/`` for viewing other agents' skill usage
* File tools for creating/reading skill outputs

With MCP Tools
--------------

Skills complement MCP tools:

* Use MCP tools for direct actions
* Use skills for guidance and workflows
* Skills can invoke MCP tools via instructions

With Multi-Turn
---------------

Skills persist across turns:

* Memories saved in ``memory/`` available in next turn
* Skill outputs visible in ``temp_workspaces/``

Example Workflows
=================

Complex Refactoring
-------------------

.. code-block:: yaml

   # Config: Enable skills with task planning and memory
   coordination:
     use_skills: true
     enable_agent_task_planning: true
     task_planning_filesystem_mode: true
     enable_memory_filesystem_mode: true

**Agent workflow:**

1. Use ``file-search`` skill to find all usages
2. Store decisions in ``memory/`` for context
3. Execute refactoring in agent workspace

Multi-Agent Collaboration
--------------------------

.. code-block:: yaml

   # Config: Skills with memory for cross-agent sharing
   coordination:
     use_skills: true
     enable_memory_filesystem_mode: true

**Agent collaboration:**

1. Agent 1: Research using external skills, save findings to ``memory/short_term/``
2. Agent 2: Read Agent 1's memories from shared reference path (typically ``temp_workspaces/agent1/memory/``)
3. Agent 2: Build upon findings using same skills

.. note::
   The shared reference path is configurable via ``agent_temporary_workspace`` in the orchestrator config. The default is ``temp_workspaces/`` but can be any directory name. Agents see the actual path in their system prompt under "Shared Reference".

See Also
========

* :ref:`user_guide_agent_task_planning` - Task planning without skills
* :ref:`user_guide_custom_tools` - Creating custom MCP tools
* :ref:`user_guide_code_execution` - Command line execution setup
* :ref:`user_guide_file_operations` - Filesystem operations

Examples
========

* ``massgen/configs/skills/skills_basic.yaml`` - Basic skills usage
* ``massgen/configs/skills/skills_semantic_search.yaml`` - Semantic search with serena and semtools
* ``massgen/configs/skills/test_semantic_skills.yaml`` - Test configuration for semantic skills
* ``massgen/configs/skills/skills_with_task_planning.yaml`` - With task planning
* ``massgen/configs/skills/skills_organized_workspace.yaml`` - Organized workspace structure
* ``massgen/configs/skills/skills_with_previous_sessions.yaml`` - Load evolving skills from previous sessions
