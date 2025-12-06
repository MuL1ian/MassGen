File Operations
===============

MassGen provides comprehensive file system capabilities that enable agents to read, write, and manage files safely within defined boundaries. This section covers all aspects of file operations in MassGen.

.. tip::

   For quick file operation examples, see :doc:`../../quickstart/running-massgen`.

Overview
--------

MassGen's file system features include:

* **Workspace isolation** - Agents operate within defined directories
* **Protected paths** - Prevent modification of sensitive files
* **Project integration** - Work with existing codebases safely
* **Memory filesystem** - Combine file ops with session memory
* **Snapshot management** - Track and restore file states

Guides in This Section
----------------------

.. grid:: 2
   :gutter: 3

   .. grid-item-card:: 📁 File Operations

      Core file system capabilities

      * Read, write, edit files
      * Workspace configuration
      * File snapshots and restoration
      * Safety and isolation

      :doc:`Read the File Operations guide → <file_operations>`

   .. grid-item-card:: 📂 Project Integration

      Work with existing projects

      * Context paths configuration
      * Codebase exploration
      * Safe project modification
      * Multi-directory access

      :doc:`Read the Project Integration guide → <project_integration>`

   .. grid-item-card:: 🔒 Protected Paths

      Secure file access

      * Protect sensitive files
      * Read-only paths
      * Path exclusion patterns
      * Security best practices

      :doc:`Read the Protected Paths guide → <protected_paths>`

   .. grid-item-card:: 💾 Memory Filesystem Mode

      Combine files with session memory

      * Persistent file context
      * Memory-based file tracking
      * Multi-session file operations
      * Advanced workflows

      :doc:`Read the Memory Filesystem guide → <memory_filesystem_mode>`

Related Documentation
---------------------

* :doc:`../tools/index` - Tools that work with files
* :doc:`../tools/code_execution` - Execute code that creates files
* :doc:`../sessions/memory` - Session memory management
* :doc:`../../reference/yaml_schema` - YAML configuration reference

.. toctree::
   :maxdepth: 1
   :hidden:

   file_operations
   project_integration
   protected_paths
   memory_filesystem_mode
