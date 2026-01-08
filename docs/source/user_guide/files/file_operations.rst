File Operations & Workspace Management
=======================================

MassGen provides comprehensive file system support, enabling agents to read, write, and manipulate files in organized, isolated workspaces.

Quick Start
-----------

**Single agent with file operations:**

.. code-block:: bash

   # Run from your project directory
   cd /path/to/your-project
   uv run massgen "Create a Python web scraper and save results to CSV"

**Or with explicit config:**

.. code-block:: bash

   massgen \
     --config @examples/tools/filesystem/claude_code_single.yaml \
     "Create a Python web scraper and save results to CSV"

**Multi-agent file collaboration:**

.. code-block:: bash

   massgen \
     --config @examples/tools/filesystem/claude_code_context_sharing.yaml \
     "Generate a comprehensive project report with charts and analysis"

.. warning::

   **Model Selection for Filesystem Operations**

   We **do not recommend** using weaker models like GPT-4o or GPT-4.1 for filesystem operations. These models do not handle file operations reliably and may produce unexpected behavior.

   **Recommended models:**

   * Claude Sonnet 4/4.5
   * GPT-5
   * Gemini 2.5 Pro
   * Grok 4
   * Other frontier models with strong tool-calling capabilities

   Weaker models may struggle with complex file operations, error handling, and workspace management.

Inline Context Paths with @syntax
---------------------------------

MassGen supports ``@path`` syntax in prompts to include files and directories as context paths dynamically, without modifying your YAML config.

**Basic Syntax:**

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Syntax
     - Effect
   * - ``@path/to/file``
     - Add file as read-only context
   * - ``@path/to/file:w``
     - Add file as write context
   * - ``@path/to/dir/``
     - Add directory as read-only context
   * - ``@path/to/dir/:w``
     - Add directory as write context
   * - ``\@literal``
     - Escaped @ (not parsed as reference)

**Examples:**

.. code-block:: bash

   # Review a specific file (read-only)
   massgen "Review @src/main.py for security issues"

   # Refactor a file (write access)
   massgen "Refactor @src/config.py:w to use dataclasses"

   # Use one file as reference, modify another
   massgen "Use @docs/spec.md as reference to update @src/impl.py:w"

   # Multiple files
   massgen "Compare @src/old.py with @src/new.py and create a migration guide"

   # Directory access
   massgen "Review all files in @src/components/ for consistency"

**Features:**

* **Path Validation**: Paths are validated before execution - you'll get a clear error if a path doesn't exist
* **Home Directory Expansion**: Use ``~`` for home directory (e.g., ``@~/projects/myapp``)
* **Relative Paths**: Paths are resolved relative to your current working directory
* **Smart Suggestions**: If you reference 3+ files from the same directory, MassGen suggests using the parent directory instead
* **Permission Merging**: ``@`` paths are merged with any ``context_paths`` in your YAML config

**Interactive Mode with Tab Completion:**

In interactive mode, MassGen provides inline file path completion when you type ``@``. Press **Tab** to see file suggestions:

.. code-block:: text

   👤 User: Review @src/ma<Tab>
                   ┌──────────────────┐
                   │ src/main.py      │  ← Press Tab to autocomplete
                   │ src/manager.py   │
                   │ src/makefile     │
                   └──────────────────┘

When you submit a prompt with ``@`` paths, MassGen will automatically update agent permissions:

.. code-block:: text

   👤 User: Review @src/utils.py for bugs

   📂 Context paths from prompt:
      📖 /path/to/src/utils.py (read)
      🔄 Updating agents with new context paths...
      ✅ Agents updated with new context paths

   🔄 Processing...

**Path Accumulation Across Turns:**

Context paths from ``@`` syntax accumulate across turns in a session. If you reference ``@src/main.py`` in turn 1, you can still discuss it in turn 5 without re-specifying the path:

.. code-block:: text

   Turn 1: "Review @src/main.py"
   → Agent can access: src/main.py

   Turn 2: "Now check @tests/test_main.py too"
   → Agent can access: src/main.py, tests/test_main.py (both!)

   Turn 3: "Fix the bug we discussed"
   → Agent can still access: src/main.py, tests/test_main.py

**Permission Upgrade:**

If you reference the same path with different permissions, the higher permission (write) takes precedence:

.. code-block:: text

   Turn 1: @src/main.py      → read access
   Turn 2: @src/main.py:w    → upgraded to write access!

**Programmatic API:**

For the Python API, ``@`` parsing is opt-in:

.. code-block:: python

   import massgen

   # Opt-in to @path parsing
   result = await massgen.run(
       query="Review @src/main.py for issues",
       model="claude-sonnet-4",
       parse_at_references=True,  # Enable @path parsing
   )

   # Or manually parse and handle paths
   from massgen.path_handling import parse_prompt_for_context

   parsed = parse_prompt_for_context("Review @src/main.py")
   print(parsed.context_paths)  # [{'path': '/abs/path/to/src/main.py', 'permission': 'read'}]
   print(parsed.cleaned_prompt)  # "Review"

Configuration
-------------

Basic Workspace Setup
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   agents:
     - id: "file-agent"
       backend:
         type: "claude_code"        # Backend with file support
         model: "claude-sonnet-4"   # Your model choice
         cwd: "workspace"           # Isolated workspace for file operations

   orchestrator:
     snapshot_storage: "snapshots"                 # Shared snapshots directory
     agent_temporary_workspace: "temp_workspaces"  # Temporary workspace management

Multi-Agent Workspace Isolation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each agent gets its own isolated workspace:

.. code-block:: yaml

   agents:
     - id: "analyzer"
       backend:
         type: "claude_code"
         cwd: "workspace1"      # Agent-specific workspace

     - id: "reviewer"
       backend:
         type: "gemini"
         cwd: "workspace2"      # Separate workspace

This ensures agents don't interfere with each other's files during coordination.

Configuration Parameters
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Parameter
     - Required
     - Description
   * - ``cwd``
     - Yes
     - Working directory for file operations (agent-specific workspace)
   * - ``snapshot_storage``
     - Yes
     - Directory for workspace snapshots (shared between agents)
   * - ``agent_temporary_workspace``
     - Yes
     - Parent directory for temporary workspaces
   * - ``exclude_file_operation_mcps``
     - No
     - Exclude file operation MCP tools. Agents use command-line tools instead. (default: false)

Minimal MCP Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~

When ``exclude_file_operation_mcps: true``, MassGen excludes redundant file operation MCP tools and relies on command-line tools instead:

.. code-block:: yaml

   agents:
     - id: "efficient_agent"
       backend:
         type: "gemini"
         model: "gemini-2.5-flash"
         cwd: "workspace"
         exclude_file_operation_mcps: true  # Use command-line tools
         enable_mcp_command_line: true      # Enable command execution

**What gets excluded:**

* Filesystem MCP read operations (``read_file``, ``list_directory``, ``grep_search``)
* File operation tools from Workspace Tools MCP (``copy_file``, ``delete_file``, ``compare_files``)

**What is kept:**

* File write operations (``write_file``, ``edit_file``) - Provides clean file creation without shell escaping issues
* Command execution tools (``execute_command``, background shell management)
* Media generation tools (image/audio generation, if enabled)
* Planning tools (task management abstractions)

**Agents use standard command-line tools for excluded operations:**

* ``cat``, ``head``, ``tail`` instead of ``read_file``
* ``ls``, ``find`` instead of ``list_directory``
* ``grep``, ``rg`` instead of ``grep_search``
* ``cp`` instead of ``copy_file``
* ``rm`` instead of ``delete_file``
* ``diff`` instead of ``compare_files``

.. note::

   This configuration reduces MCP tool overhead while maintaining full functionality through command-line tools. Recommended for models that are proficient with shell commands.

Available File Operations
-------------------------

Claude Code Backend
~~~~~~~~~~~~~~~~~~~

Claude Code has built-in file operation tools:

* **Read** - Read file contents
* **Write** - Create or overwrite files
* **Edit** - Make targeted edits to existing files
* **Bash** - Execute shell commands (including file operations)
* **Grep** - Search file contents with regex
* **Glob** - Find files matching patterns

**Additional Claude Code Tools:**

* **Task** - Launch specialized agents for complex tasks
* **ExitPlanMode** - Exit planning mode (when enabled)
* **NotebookEdit** - Edit Jupyter notebook cells
* **WebFetch** - Fetch and process web content
* **TodoWrite** - Manage task lists
* **WebSearch** - Search the web
* **BashOutput** - Retrieve background shell output
* **KillShell** - Terminate background shells
* **SlashCommand** - Execute custom slash commands

.. seealso::
   For complete Claude Code tools documentation and usage examples, see the `Claude Code Documentation <https://docs.claude.com/en/docs/claude-code>`_

**Example:**

.. code-block:: bash

   massgen \
     --backend claude_code \
     --model sonnet \
     "Create a Python project with src/, tests/, and docs/ directories"

MCP Filesystem Server
~~~~~~~~~~~~~~~~~~~~~

All backends can use the MCP Filesystem Server for file operations:

.. code-block:: yaml

   agents:
     - id: "gemini_agent"
       backend:
         type: "gemini"
         model: "gemini-2.5-flash"

**MCP Filesystem Operations:**

* ``read_file`` - Read file contents
* ``write_file`` - Write or create files
* ``create_directory`` - Create directories
* ``list_directory`` - List directory contents
* ``delete_file`` - Delete files (with safety checks)
* ``move_file`` - Move or rename files

.. seealso::
   For complete MCP Filesystem Server documentation and additional operations, see the `official MCP Filesystem Server <https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem>`_

MassGen Workspace Tools
~~~~~~~~~~~~~~~~~~~~~~~

MassGen provides additional workspace management tools via the Workspace Tools MCP Server:

.. code-block:: yaml

   agents:
     - id: "advanced_agent"
       backend:
         type: "claude"
         model: "claude-sonnet-4"
         mcp_servers:
           - name: "workspace_tools"
             type: "stdio"
             command: "uv"
             args: ["run", "python", "-m", "massgen.filesystem_manager._workspace_tools_server"]

**File Operations:**

* ``copy_file`` - Copy single file/directory from any accessible path to workspace
* ``copy_files_batch`` - Copy multiple files with pattern matching and exclusions
* ``delete_file`` - Delete single file/directory from workspace
* ``delete_files_batch`` - Delete multiple files with pattern matching

**Directory Analysis:**

* ``compare_directories`` - Compare two directories and show differences
* ``compare_files`` - Compare two text files and show unified diff

**Image Generation** (requires OpenAI API key):

* ``generate_and_store_image_with_input_images`` - Create variations of existing images using gpt-4.1
* ``generate_and_store_image_no_input_images`` - Generate new images from text prompts using gpt-4.1

**Example - Workspace cleanup with batch operations:**

.. code-block:: text

   You: Copy all Python files from the previous turn's output
   [Agent uses copy_files_batch with include_patterns: ["*.py"]]

   You: Delete all temporary files
   [Agent uses delete_files_batch with include_patterns: ["*.tmp", "*.temp"]]

   You: Compare my workspace with the reference implementation
   [Agent uses compare_directories to show differences]

Workspace Management
--------------------

Workspace Isolation
~~~~~~~~~~~~~~~~~~~

Each agent's ``cwd`` is fully isolated:

* Agents can freely read/write within their workspace
* No risk of conflicting file operations
* Clean separation of work products

**Directory structure:**

.. code-block:: text

   .massgen/
   └── workspaces/
       ├── workspace1/     # Agent 1's isolated workspace
       │   ├── file1.py
       │   └── output.txt
       └── workspace2/     # Agent 2's isolated workspace
           ├── analysis.md
           └── data.csv

Snapshot Storage
~~~~~~~~~~~~~~~~

Workspace snapshots enable context sharing between agents:

* Winning agent's workspace is saved as snapshot
* Future coordination rounds can access previous results
* Enables building on past work

**How it works:**

1. Agent completes initial answer → Workspace snapshotted
2. Coordination phase → Agents can reference snapshot
3. Final agent selected → Can build on snapshot content

Temporary Workspaces
~~~~~~~~~~~~~~~~~~~~

Previous turn results available via temporary workspaces:

* Multi-turn sessions preserve context
* Agents can access files from earlier turns
* Organized by turn number

.. code-block:: text

   .massgen/
   └── temp_workspaces/
       ├── turn_1/
       │   └── agent1/
       │       └── previous_output.txt
       └── turn_2/
           └── agent2/
               └── refined_output.txt

File Operation Safety
---------------------

Read-Before-Delete Enforcement
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

MassGen prevents accidental file deletion with ``FileOperationTracker``:

**Safety Rules:**

1. Agents **must read a file before deleting it**
2. Exception: Agent-created files can be deleted without reading
3. Directory deletion requires validation
4. Clear error messages when operations blocked

**Example:**

.. code-block:: python

   # This will FAIL - file not read first
   Agent: Delete config.json
   Error: Cannot delete config.json - file has not been read

   # This will SUCCEED - file read first
   Agent: Read config.json
   Agent: Delete config.json
   Success: File deleted

Created File Exemption
~~~~~~~~~~~~~~~~~~~~~~

Files created by an agent can be freely deleted:

.. code-block:: python

   Agent: Write new_file.txt "content"
   Agent: Delete new_file.txt  # Allowed - agent created it

This allows agents to clean up their own temporary files.

PathPermissionManager
~~~~~~~~~~~~~~~~~~~~~

Integrated operation tracking:

* ``track_read_operation()`` - Records file reads
* ``track_write_operation()`` - Records file writes
* ``track_delete_operation()`` - Validates and records deletions
* Enhanced delete validation for files and batch operations

Protected Paths
~~~~~~~~~~~~~~~

Protected paths allow you to make specific files or directories **read-only** within writable context paths, preventing agents from modifying or deleting critical reference files while allowing them to edit other files.

**Use Case**: You want agents to modify some files in a directory but keep certain reference files, configurations, or templates untouched.

**Configuration Example:**

.. code-block:: yaml

   orchestrator:
     snapshot_storage: "snapshots"
     agent_temporary_workspace: "temp_workspaces"

     context_paths:
       - path: "/path/to/project"
         permission: "write"
         protected_paths:
           - "config.json"      # Read-only
           - "template.html"    # Read-only
           - "tests/fixtures/"  # Entire directory read-only

**What Agents Can Do:**

* ✅ **Read** protected files for reference
* ✅ **Write/Edit** non-protected files in the same directory
* ❌ **Modify or Delete** protected files

**Common Use Cases:**

1. **Protect Reference Files**: Keep test fixtures unchanged while agents modify code
2. **Protect Configuration**: Allow code changes but prevent config modifications
3. **Protect Templates**: Let agents generate content without modifying templates
4. **Protect Documentation Structure**: Allow content updates but preserve organization

For complete protected paths documentation including examples, troubleshooting, and best practices, see the **Protected Paths** section in :doc:`project_integration`.

Security Considerations
-----------------------

.. warning::

   **Agents can autonomously read, write, modify, and delete files** within their permitted directories.

Before running MassGen with filesystem access:

* ✅ Only grant access to directories you're comfortable with agents modifying
* ✅ Use permission system to restrict write access where needed
* ✅ Use protected paths for critical files within writable directories
* ✅ Test in an isolated directory first
* ✅ Back up important files before granting write access
* ✅ Review ``context_paths`` configuration carefully

The agents will execute file operations **without additional confirmation** once permissions are granted.

File Access Control
~~~~~~~~~~~~~~~~~~~

Use MCP server configurations to restrict access:

.. code-block:: yaml

   # Filesystem operations handled via cwd parameter
   # No need to add filesystem MCP server manually

Workspace Organization
----------------------

Clean Project Structure
~~~~~~~~~~~~~~~~~~~~~~~

All MassGen state organized under ``.massgen/``:

.. code-block:: text

   your-project/
   ├── .massgen/                    # All MassGen state
   │   ├── sessions/                # Multi-turn conversation history
   │   ├── workspaces/              # Agent working directories
   │   ├── snapshots/               # Workspace snapshots
   │   └── temp_workspaces/         # Previous turn results
   ├── src/                         # Your project files
   └── docs/                        # Your documentation

**Benefits:**

* Clean projects - all MassGen files in one place
* Easy ``.gitignore`` - just add ``.massgen/``
* Portable - delete ``.massgen/`` without affecting project
* Multi-turn sessions preserved

Configuration Auto-Organization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

MassGen automatically organizes under ``.massgen/``:

.. code-block:: yaml

   orchestrator:
     snapshot_storage: "snapshots"         # → .massgen/snapshots/
     agent_temporary_workspace: "temp"     # → .massgen/temp/

   agents:
     - backend:
         cwd: "workspace1"                 # → .massgen/workspaces/workspace1/

Example: Multi-Agent Document Processing
-----------------------------------------

.. code-block:: yaml

   agents:
     - id: "analyzer"
       backend:
         type: "gemini"
         model: "gemini-2.5-flash"
         cwd: "analyzer_workspace"

     - id: "writer"
       backend:
         type: "claude_code"
         cwd: "writer_workspace"

   orchestrator:
     snapshot_storage: "snapshots"
     agent_temporary_workspace: "temp"

**Usage:**

.. code-block:: bash

   massgen \
     --config document_processing.yaml \
     "Analyze data.csv and create a comprehensive report with visualizations"

**What happens:**

1. **Analyzer** reads data.csv, creates analysis in its workspace
2. **Writer** sees analyzer's snapshot, creates report with charts
3. Final output in winner's workspace, snapshot saved for future reference

Advanced Topics
---------------

The sections above cover basic file operations and workspace management. For advanced features, see:

* :doc:`project_integration` - Work with your existing codebase using context paths with file-level and directory-level access control, plus protected paths for fine-grained permission control
* :doc:`../tools/code_execution` - Execute bash commands and scripts with MCP-based code execution, supporting both local and Docker isolation modes

Next Steps
----------

* :doc:`../tools/code_execution` - Execute commands and scripts with local or Docker isolation
* :doc:`../tools/mcp_integration` - Additional MCP tools beyond filesystem
* :doc:`../sessions/multi_turn_mode` - File operations across multiple conversation turns
* :doc:`../../quickstart/running-massgen` - More examples
