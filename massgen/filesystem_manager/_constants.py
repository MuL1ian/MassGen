# -*- coding: utf-8 -*-
"""Centralized constants for filesystem operations.

This module defines common patterns for directories and files that should be
excluded from various operations like logging, sharing, and path permissions.
"""

# =============================================================================
# DIRECTORY PATTERNS TO SKIP/EXCLUDE
# =============================================================================

# Large dependency/cache directories that should be skipped in logging and listing
# These directories can contain thousands of files and slow down operations
SKIP_DIRS_FOR_LOGGING = frozenset(
    {
        # Package managers / dependencies
        "node_modules",
        ".pnpm",
        "vendor",  # PHP, Go
        "pkg",  # Go
        "target",  # Rust
        # Python
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".nox",
        "*.egg-info",
        # Build outputs
        "dist",
        "build",
        ".next",
        ".nuxt",
        ".parcel-cache",
        # Caches
        ".cache",
        ".coverage",
    },
)

# Directories that are critical/sensitive and should be protected from agent access
# Agents should not read/write to these directories
CRITICAL_DIRS = frozenset(
    {
        ".git",
        ".env",
        ".massgen",
        "massgen_logs",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
    },
)

# Directories excluded from path permissions by default
# Subset of critical dirs that permission manager should block
DEFAULT_EXCLUDED_DIRS = frozenset(
    {
        ".massgen",
        ".env",
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".DS_Store",
        "massgen_logs",
    },
)

# Directories to exclude when uploading to gist/sharing
# These are often huge and not useful for sharing session data
SHARE_EXCLUDE_DIRS = frozenset(
    {
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        ".venv",
        ".git",
        "workspace",  # Agent workspace directories (often huge)
    },
)

# =============================================================================
# FILE PATTERNS TO IGNORE
# =============================================================================

# File patterns to ignore in file operation tracking
PATTERNS_TO_IGNORE_FOR_TRACKING = [
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".coverage",
    "*.egg-info",
    ".tox",
    ".nox",
    "node_modules",
    ".next",
    ".nuxt",
    "dist",
    "build",
    ".DS_Store",
    "Thumbs.db",
    "*.log",
    "*.swp",
    "*.swo",
    "*~",
    "*.pyc",  # Python compiled bytecode files
    "*.pyo",  # Python optimized bytecode files
]

# File extensions to exclude when sharing (binary/large files)
SHARE_EXCLUDE_EXTENSIONS = frozenset(
    {
        ".pyc",
        ".pyo",
        ".so",
        ".bin",
        ".safetensors",
        ".log.zip",
        ".db",
        ".sqlite",
        ".sqlite3",
    },
)

# =============================================================================
# BINARY FILE EXTENSIONS
# =============================================================================

# Binary file extensions that should not be read by text-based tools
BINARY_FILE_EXTENSIONS = frozenset(
    {
        # Images
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".ico",
        ".svg",
        ".webp",
        ".tiff",
        ".tif",
        # Audio
        ".mp3",
        ".wav",
        ".ogg",
        ".flac",
        ".aac",
        ".m4a",
        ".wma",
        # Video
        ".mp4",
        ".avi",
        ".mkv",
        ".mov",
        ".wmv",
        ".flv",
        ".webm",
        ".m4v",
        ".mpg",
        ".mpeg",
        # Archives
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".xz",
        ".7z",
        ".rar",
        # Executables and object files
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".o",
        ".a",
        ".class",
        ".jar",
        # Documents (binary formats)
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        # Data
        ".bin",
        ".dat",
        ".db",
        ".sqlite",
        ".sqlite3",
        # Python compiled
        ".pyc",
        ".pyo",
        ".pyd",
        # Other
        ".wasm",
        ".safetensors",
        ".onnx",
        ".pb",
        ".h5",
        ".hdf5",
    },
)

# =============================================================================
# WORKSPACE FILE EXTENSIONS (for sharing)
# =============================================================================

# File extensions to include from workspace when sharing (small text files)
WORKSPACE_INCLUDE_EXTENSIONS = frozenset(
    {
        ".txt",
        ".md",
        ".json",
        ".yaml",
        ".yml",
        ".py",
        ".js",
        ".ts",
        ".html",
        ".css",
        ".sh",
        ".toml",
        ".cfg",
        ".ini",
        ".xml",
    },
)

# =============================================================================
# SIZE LIMITS
# =============================================================================

# Maximum file size for sharing (10MB)
MAX_FILE_SIZE_FOR_SHARING = 10_000_000

# Maximum total size for sharing (90MB, leaving buffer from 100MB gist limit)
MAX_TOTAL_SIZE_FOR_SHARING = 90_000_000

# Maximum number of files for sharing (290, leaving buffer from 300 gist limit)
MAX_FILES_FOR_SHARING = 290

# Maximum items to log in workspace listings
MAX_LOG_ITEMS = 50

# Maximum directory depth for workspace logging
MAX_LOG_DEPTH = 3

# =============================================================================
# FRAMEWORK MCP SERVERS
# =============================================================================

# MCP servers that are part of MassGen's framework and should NOT be converted
# to code-based tools (discoverable in servers/ directory). These are either:
# - Automatically available built-in tools
# - Handled specially by the framework
# - Injected conditionally based on config flags
#
# Note: Server names may have agent-specific suffixes (e.g., "planning_agent_a"),
# so matching should check for prefix matches like server_name.startswith(f"{mcp}_")
FRAMEWORK_MCPS = frozenset(
    {
        "command_line",  # Command execution (execute_command tool)
        "workspace_tools",  # Workspace operations (file ops, media generation)
        "filesystem",  # Filesystem operations (read/write/edit files)
        "planning",  # Task planning MCP
        "memory",  # Memory management MCP
        "subagent",  # Subagent spawning (built-in when enabled)
    },
)
