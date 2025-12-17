# -*- coding: utf-8 -*-
"""
System Prompt Section Architecture

This module implements a class-based architecture for building structured,
prioritized system prompts. Each section encapsulates specific instructions
with explicit priority levels, enabling better attention management and
maintainability.

Design Document: docs/dev_notes/system_prompt_architecture_redesign.md
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional


class Priority(IntEnum):
    """
    Explicit priority levels for system prompt sections.

    Lower numbers = higher priority (appear earlier in final prompt).
    Based on research showing critical instructions should appear at top
    or bottom of prompts for maximum attention.

    References:
        - Lakera AI Prompt Engineering Guide 2025
        - Anthropic Claude 4 Best Practices
        - "Position is Power" research (arXiv:2505.21091v2)
    """

    CRITICAL = 1  # Agent identity, MassGen primitives (vote/new_answer), core behaviors
    HIGH = 5  # Skills, memory, filesystem workspace - essential context
    MEDIUM = 10  # Operational guidance, task planning
    LOW = 15  # Task-specific context
    AUXILIARY = 20  # Optional guidance, best practices


@dataclass
class SystemPromptSection(ABC):
    """
    Base class for all system prompt sections.

    Each section encapsulates a specific set of instructions with explicit
    priority, optional XML structure, and support for hierarchical subsections.

    Attributes:
        title: Human-readable section title (for debugging/logging)
        priority: Priority level determining render order
        xml_tag: Optional XML tag name for wrapping content
        enabled: Whether this section should be included
        subsections: Optional list of child sections for hierarchy

    Example:
        >>> class CustomSection(SystemPromptSection):
        ...     def build_content(self) -> str:
        ...         return "Custom instructions here"
        >>>
        >>> section = CustomSection(
        ...     title="Custom",
        ...     priority=Priority.MEDIUM,
        ...     xml_tag="custom"
        ... )
        >>> print(section.render())
        <custom priority="medium">
        Custom instructions here
        </custom>
    """

    title: str
    priority: Priority
    xml_tag: Optional[str] = None
    enabled: bool = True
    subsections: List["SystemPromptSection"] = field(default_factory=list)

    @abstractmethod
    def build_content(self) -> str:
        """
        Build the actual content for this section.

        Subclasses must implement this to provide their specific instructions.

        Returns:
            String content for this section (without XML wrapping)
        """

    def render(self) -> str:
        """
        Render the complete section with XML structure if specified.

        Automatically handles:
        - XML tag wrapping with priority attributes
        - Recursive rendering of subsections
        - Skipping if disabled

        Returns:
            Formatted section string ready for inclusion in system prompt
        """
        if not self.enabled:
            return ""

        # Build main content
        content = self.build_content()

        # Render and append subsections if present
        if self.subsections:
            enabled_subsections = [s for s in self.subsections if s.enabled]
            if enabled_subsections:
                sorted_subsections = sorted(
                    enabled_subsections,
                    key=lambda s: s.priority,
                )
                subsection_content = "\n\n".join(s.render() for s in sorted_subsections)
                content = f"{content}\n\n{subsection_content}"

        # Wrap in XML if tag specified
        if self.xml_tag:
            # Handle both Priority enum and raw integers
            if isinstance(self.priority, Priority):
                priority_name = self.priority.name.lower()
            else:
                # Map integer priorities to names
                priority_map = {1: "critical", 2: "critical", 3: "critical", 4: "critical", 5: "high", 10: "medium", 15: "low", 20: "auxiliary"}
                priority_name = priority_map.get(self.priority, "medium")
            return f'<{self.xml_tag} priority="{priority_name}">\n{content}\n</{self.xml_tag}>'

        return content


class AgentIdentitySection(SystemPromptSection):
    """
    Agent's core identity: role, expertise, personality.

    This section ALWAYS comes first (Priority 1) to establish
    WHO the agent is before any operational instructions.
    Skips rendering if empty.

    Args:
        agent_message: The agent's custom system message from
                      agent.get_configurable_system_message()
    """

    def __init__(self, agent_message: str):
        super().__init__(
            title="Agent Identity",
            priority=1,  # First, before massgen_coordination(2) and core_behaviors(3)
            xml_tag="agent_identity",
        )
        self.agent_message = agent_message

    def build_content(self) -> str:
        return self.agent_message

    def render(self) -> str:
        """Skip rendering if agent message is empty."""
        if not self.agent_message or not self.agent_message.strip():
            return ""
        return super().render()


class CoreBehaviorsSection(SystemPromptSection):
    """
    Core behavioral principles for Claude agents.

    Includes critical guidance on:
    - Default to action vs suggestion
    - Parallel tool calling
    - File cleanup

    Based on Anthropic Claude 4 best practices.
    Priority 4 puts this after agent_identity(1), massgen_coordination(2), and skills(3).
    """

    def __init__(self):
        super().__init__(
            title="Core Behaviors",
            priority=4,  # After agent_identity(1), massgen_coordination(2), skills(3)
            xml_tag="core_behaviors",
        )

    def build_content(self) -> str:
        return """## Core Behavioral Principles

**Default to Action:**
By default, implement changes rather than only suggesting them. If the user's intent is unclear,
infer the most useful likely action and proceed, using tools to discover any missing details instead
of guessing. Try to infer the user's intent about whether a tool call (e.g., file edit or read) is
intended or not, and act accordingly.

**Parallel Tool Calling:**
If you intend to call multiple tools and there are no dependencies between the tool calls, make all
of the independent tool calls in parallel. Prioritize calling tools simultaneously whenever the
actions can be done in parallel rather than sequentially. For example, when reading 3 files, run 3
tool calls in parallel to read all 3 files into context at the same time. Maximize use of parallel
tool calls where possible to increase speed and efficiency. However, if some tool calls depend on
previous calls to inform dependent values like the parameters, do NOT call these tools in parallel
and instead call them sequentially. Never use placeholders or guess missing parameters in tool calls."""


class SkillsSection(SystemPromptSection):
    """
    Available skills that agents can invoke.

    CRITICAL priority (3) ensures skills appear before general behaviors.
    Skills define fundamental capabilities that must be known before task execution.

    Args:
        skills: List of all skills (both builtin and project) with name, description, location
    """

    def __init__(self, skills: List[Dict[str, Any]]):
        super().__init__(
            title="Available Skills",
            priority=3,  # After agent_identity(1) and massgen_coordination(2), before core_behaviors(4)
            xml_tag="skills",
        )
        self.skills = skills

    def build_content(self) -> str:
        """Build skills in XML format with full descriptions."""
        content_parts = []

        # Header
        content_parts.append("## Available Skills")
        content_parts.append("")
        content_parts.append("<!-- SKILLS_TABLE_START -->")

        # Usage instructions
        content_parts.append("<usage>")
        content_parts.append("When users ask you to perform tasks, check if any of the available skills below can help complete the task more effectively.")
        content_parts.append("")
        content_parts.append("How to use skills:")
        content_parts.append('- Invoke: execute_command("openskills read <skill-name>")')
        content_parts.append("- The skill content will load with detailed instructions")
        content_parts.append("- Base directory provided in output for resolving bundled resources")
        content_parts.append("")
        content_parts.append("Usage notes:")
        content_parts.append("- Only use skills listed in <available_skills> below")
        content_parts.append("- Do not invoke a skill that is already loaded in your context")
        content_parts.append("</usage>")
        content_parts.append("")

        # Skills list (project skills only - builtin skills are auto-loaded elsewhere)
        content_parts.append("<available_skills>")

        # Add project skills only
        for skill in self.skills:
            name = skill.get("name", "Unknown")
            description = skill.get("description", "No description")
            location = skill.get("location", "project")

            content_parts.append("")
            content_parts.append("<skill>")
            content_parts.append(f"<name>{name}</name>")
            content_parts.append(f"<description>{description}</description>")
            content_parts.append(f"<location>{location}</location>")
            content_parts.append("</skill>")

        content_parts.append("")
        content_parts.append("</available_skills>")
        content_parts.append("<!-- SKILLS_TABLE_END -->")

        return "\n".join(content_parts)


class FileSearchSection(SystemPromptSection):
    """
    Lightweight file search guidance for ripgrep and ast-grep.

    This provides essential usage patterns for the pre-installed search tools.
    For comprehensive guidance, agents can invoke: execute_command("openskills read file-search")

    MEDIUM priority - useful but not critical for all tasks.
    """

    def __init__(self):
        super().__init__(
            title="File Search Tools",
            priority=Priority.MEDIUM,
            xml_tag="file_search_tools",
        )

    def build_content(self) -> str:
        """Build concise file search guidance."""
        return """## File Search Tools

You have access to fast search tools for code exploration:

**ripgrep (rg)** - Fast text/regex search:
```bash
# Search with file type filtering
rg "pattern" --type py --type js

# Common flags: -i (case-insensitive), -w (whole words), -l (files only), -C N (context lines)
rg "function.*login" --type js src/
```

**ast-grep (sg)** - Structural code search:
```bash
# Find code patterns by syntax
sg --pattern 'function $NAME($$$) { $$$ }' --lang js

# Metavariables: $VAR (single node), $$$ (zero or more nodes)
sg --pattern 'class $NAME { $$$ }' --lang python
```

**Key principles:**
- Start narrow: Specify file types (--type py) and directories (src/)
- Count first: Use `rg "pattern" --count` to check result volume before full search
- Limit output: Pipe to `head -N` if results are large
- Use rg for text, sg for code structure

For detailed guidance including targeting strategies and examples, invoke: `execute_command("openskills read file-search")`"""


class CodeBasedToolsSection(SystemPromptSection):
    """
    Guidance for code-based tool access (CodeAct paradigm).

    When enabled, MCP tools are presented as Python code in the filesystem.
    Agents discover tools by exploring servers/, read docstrings, and call via imports.

    MEDIUM priority - important for tool discovery and usage.

    Args:
        workspace_path: Path to agent's workspace
        shared_tools_path: Optional path to shared tools directory
        mcp_servers: List of MCP server configurations (for fetching descriptions)
    """

    def __init__(
        self,
        workspace_path: str,
        shared_tools_path: str = None,
        mcp_servers: List[Dict[str, Any]] = None,
    ):
        super().__init__(
            title="Code-Based Tools",
            priority=Priority.MEDIUM,
            xml_tag="code_based_tools",
        )
        self.workspace_path = workspace_path
        self.shared_tools_path = shared_tools_path
        self.mcp_servers = mcp_servers or []
        # Use shared tools path if available, otherwise workspace
        self.tools_location = shared_tools_path if shared_tools_path else workspace_path

    def build_content(self) -> str:
        """Build code-based tools guidance."""
        location_note = ""
        if self.shared_tools_path:
            location_note = f"\n\n**Note**: Tools are in a shared read-only location (`{self.shared_tools_path}`) accessible to all agents."

        # Read ExecutionResult class definition for custom tools
        import re
        from pathlib import Path

        result_file = Path(__file__).parent / "tool" / "_result.py"
        try:
            execution_result_code = result_file.read_text()
        except Exception:
            execution_result_code = "# ExecutionResult definition not available"

        # Discover custom tools by reading TOOL.md files
        custom_tools_list = ""
        custom_tools_path = Path(self.tools_location) / "custom_tools"
        if custom_tools_path.exists():
            tool_descriptions = []
            for tool_md in custom_tools_path.glob("*/TOOL.md"):
                try:
                    content = tool_md.read_text()
                    # Extract description from YAML frontmatter
                    match = re.search(r"^description:\s*(.+)$", content, re.MULTILINE)
                    if match:
                        tool_name = tool_md.parent.name
                        description = match.group(1).strip()
                        tool_descriptions.append(f"- **{tool_name}**: {description}")
                except Exception:
                    continue

            if tool_descriptions:
                custom_tools_list = "\n\n**Available Custom Tools:**\n" + "\n".join(tool_descriptions)

        # Fetch MCP server descriptions from registry
        mcp_servers_list = ""
        if self.mcp_servers:
            try:
                from massgen.mcp_tools.registry_client import (
                    get_mcp_server_descriptions,
                )

                mcp_descriptions = get_mcp_server_descriptions(self.mcp_servers)
                if mcp_descriptions:
                    mcp_items = [f"- **{name}**: {desc}" for name, desc in mcp_descriptions.items()]
                    mcp_servers_list = "\n\n**Available MCP Servers:**\n" + "\n".join(mcp_items)
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning(f"Failed to fetch MCP descriptions: {e}")
                # Fall back to just showing server names
                server_names = [s.get("name", "unknown") for s in self.mcp_servers]
                if server_names:
                    mcp_servers_list = "\n\n**Available MCP Servers:** " + ", ".join(server_names)

        return f"""## Available Tools (Code-Based Access)

Tools are available as **Python code** in your workspace filesystem. Discover and call them like regular Python modules (e.g., use normal search tools such as `rg` or `sg`){location_note}

**Directory Structure:**
```
{self.tools_location}/
├── servers/              # MCP tool wrappers (auto-generated, read-only)
│   ├── __init__.py      # Package marker (import from here)
│   ├── weather/
│   │   ├── __init__.py  # Exports: get_forecast, get_current
│   │   ├── get_forecast.py
│   │   └── get_current.py
│   └── github/
│       ├── __init__.py  # Exports: create_issue
│       └── create_issue.py
└── custom_tools/         # Full Python implementations (read-only)
    └── [user-provided tools]

Your workspace/
└── utils/               # CREATE THIS - for your scripts (workflows, async, filtering)
    └── [write your own scripts here as needed]
```{mcp_servers_list}{custom_tools_list}

**Important:** All tools and servers listed here are already configured and ready to use. If a tool requires API keys, they are already available - we only show tools you can actually use.

**Note:** Skills provide guidance and workflows, while tools provide actual functionality. They complement each other - for
example, a skill might guide you through a process that requires using specific tools to complete it.

While it's not always necessary to use additional tools, there are some cases where they are required (e.g., multimodal
content generation and understanding, as by default agents only handle text). In other cases, using tools can help you
complete tasks more efficiently.

**Tool Discovery (Efficient Patterns):**

Custom tools (listed above) - read TOOL.md for details:
```bash
head -n 80 custom_tools/<tool_name>/TOOL.md
```

MCP servers - extract function docstrings:
```bash
# List servers and functions
ls servers/ && ls servers/<server_name>/

# Get function docstring (first 25 lines)
head -n 25 servers/<server_name>/<function>.py

# Extract all function signatures with ast-grep
sg --pattern 'def $FUNC($$$):' --lang python servers/<server_name>/
```

Search patterns:
```bash
# Search custom tools by capability
rg 'tasks:' custom_tools/*/TOOL.md -A 3 | rg -i '<keyword>'

# Search MCP server functions by name/keyword
rg -i '<keyword>' servers/ -l
```

**Usage Pattern:**
```python
# Import MCP tools from servers/
from servers.weather import get_forecast
from servers.github import create_issue

# Import custom tools - use module path from TOOL.md entry_points
# Simple tool: from custom_tools.{{file}} import {{function}}
from custom_tools.string_utils import reverse_string

# Tool in subdirectory: from custom_tools.{{dir}}.{{file}} import {{function}}
# Example from TOOL.md: entry_points[0] = {{file: "_multimodal_tools/text_to_image_generation.py", function: "text_to_image_generation"}}
from custom_tools._multimodal_tools.text_to_image_generation import text_to_image_generation

# Use the tools
weather = get_forecast("San Francisco", days=3)
reversed_text = reverse_string("hello")
image = await text_to_image_generation(prompt="sunset", output_path="sunset.png")
```

**Important:**
- Subdirectories under `custom_tools/` don't auto-import tools. Always import directly from the `.py` file using the path from TOOL.md.
- **CRITICAL**: When running Python scripts that import from `servers/` or `custom_tools/`, always specify `work_dir="{self.workspace_path}"` in your
  execute_command call. The symlinks to these directories only exist in your main workspace, not in temporary snapshot directories.

**Custom Tools Return Type:**

Custom tools MUST return `ExecutionResult`. Here's the definition from `massgen/tool/_result.py`:

```python
{execution_result_code}
```

**Creating Workflows (utils/):**
Write scripts in `utils/` to combine multiple tools:

```python
# utils/daily_weather_report.py
from servers.weather import get_forecast, get_current

def generate_report(city: str) -> str:
    current = get_current(city)
    forecast = get_forecast(city, days=3)

    report = f"Current: {{current['temp']}}°F\\n"
    report += f"Forecast: {{forecast['summary']}}"
    return report

# Run directly
if __name__ == "__main__":
    print(generate_report("San Francisco"))
```

Then execute: `python utils/daily_weather_report.py`

**Advanced Patterns:**
- **Async operations**: Use `asyncio` to call multiple tools in parallel
- **Data filtering**: Process large datasets in utils/ before returning (reduce tokens)
- **Error handling**: Add try/except in utils/ for robust workflows
- **Tool composition**: Chain multiple tools together in single script

**Key Principles:**
1. **Batch discovery operations**: Combine `ls`, `rg`, `sg` in single `execute_command()` calls
2. **Search then extract**: Use `rg -l` to find candidates, then `head`/`sg` for targeted reads
3. **Minimize context**: Extract only signatures/docstrings with `sg` or `head -n 25` (not full `cat`)
4. **Import only needed tools**: Don't import everything upfront (reduces context)
5. **Create utils/ for complex workflows**: Combine tools, add async, filter data

**Example - Async Multi-Tool Call:**
```python
# utils/parallel_weather.py
import asyncio
from servers.weather import get_forecast

async def get_forecasts(cities: list) -> dict:
    tasks = [get_forecast(city) for city in cities]
    results = await asyncio.gather(*tasks)
    return dict(zip(cities, results))

# Get weather for 5 cities in parallel
cities = ["SF", "NYC", "LA", "Chicago", "Boston"]
forecasts = asyncio.run(get_forecasts(cities))
```

**Example - Data Filtering:**
```python
# utils/top_leads.py
from servers.salesforce import get_records

def get_qualified_leads(limit: int = 50) -> list:
    # Fetch 10k records from Salesforce
    all_records = get_records(object="Lead", limit=10000)

    # Filter in execution environment (not sent to LLM context)
    qualified = [r for r in all_records if r["score"] > 80]

    # Return only top N (massive context reduction)
    return sorted(qualified, key=lambda x: x["score"], reverse=True)[:limit]
```

This approach provides context reduction compared to loading all tool schemas upfront."""


class MemorySection(SystemPromptSection):
    """
    Memory system instructions for context retention across conversations.

    HIGH priority ensures memory usage is prominent and agents use it
    proactively rather than only when explicitly prompted.

    Args:
        memory_config: Dictionary containing memory system configuration
                      including short-term and long-term memory content
    """

    def __init__(self, memory_config: Dict[str, Any]):
        super().__init__(
            title="Memory System",
            priority=Priority.HIGH,
            xml_tag="memory",
        )
        self.memory_config = memory_config

    def build_content(self) -> str:
        """Build memory system instructions."""
        content_parts = []

        # Header - concise overview
        content_parts.append(
            "## Decision Documentation System\n\n"
            "Document decisions and learnings to **optimize future work** and **prevent repeated mistakes**. "
            "This isn't just memory - it's about capturing **why** decisions were made, **what worked/failed**, "
            "and **what would help similar tasks succeed**.\n",
        )

        # Memory tiers - clarified with usage guidance
        content_parts.append(
            "### Storage Tiers\n\n"
            "**short_term** (auto-loaded every turn):\n"
            "- User preferences and workflow patterns\n"
            "- Quick reference info needed frequently\n"
            "- Current task context and findings\n"
            "- Small, tactical observations (<100 lines)\n"
            "- Examples: user_prefs.md, current_findings.md\n\n"
            "**long_term** (load manually when needed):\n"
            "- Detailed post-mortems and analyses\n"
            "- Comprehensive skill effectiveness reports\n"
            "- Complex lessons with context (>100 lines)\n"
            "- Knowledge that's useful but not needed every turn\n"
            "- Examples: detailed_analysis.md, comprehensive_guide.md\n\n"
            "**Rule of thumb**: If it's small and useful every turn → short_term. "
            "If it's detailed and situationally useful → long_term.\n",
        )

        # Show existing short-term memories (full content)
        short_term = self.memory_config.get("short_term", {})
        if short_term:
            content_parts.append("\n### Current Short-Term Memories\n")
            short_term_content = short_term.get("content", "")
            if short_term_content:
                content_parts.append(short_term_content)
            else:
                content_parts.append("*No short-term memories yet*")

        # Show existing long-term memories (summaries only)
        long_term = self.memory_config.get("long_term", [])
        if long_term:
            content_parts.append("\n### Available Long-Term Memories\n")
            content_parts.append("<available_long_term_memories>")
            for memory in long_term:
                mem_id = memory.get("id", "N/A")
                summary = memory.get("summary", "No summary")
                created = memory.get("created_at", "Unknown")
                content_parts.append("")
                content_parts.append("<memory>")
                content_parts.append(f"<id>{mem_id}</id>")
                content_parts.append(f"<summary>{summary}</summary>")
                content_parts.append(f"<created>{created}</created>")
                content_parts.append("</memory>")
            content_parts.append("")
            content_parts.append("</available_long_term_memories>")

        # Show current memories from temp workspaces (all agents' current work)
        temp_workspace_memories = self.memory_config.get("temp_workspace_memories", [])
        if temp_workspace_memories:
            content_parts.append("\n### Current Agent Memories (For Comparison)\n")
            content_parts.append(
                "These are the current memories from all agents working on this task. " "Review to compare approaches and avoid duplicating work.\n",
            )

            for agent_mem in temp_workspace_memories:
                agent_label = agent_mem.get("agent_label", "unknown")
                memories = agent_mem.get("memories", {})

                content_parts.append(f"\n**{agent_label}:**")

                # Show short_term memories (full content)
                if memories.get("short_term"):
                    content_parts.append("\n*short_term:*")
                    for mem_name, mem_data in memories["short_term"].items():
                        content = mem_data.get("content", mem_data) if isinstance(mem_data, dict) else mem_data
                        content_parts.append(f"- `{mem_name}.md`")
                        content_parts.append(f"  ```\n  {content.strip()}\n  ```")

                # Show long_term memories (name + description only)
                if memories.get("long_term"):
                    content_parts.append("\n*long_term:*")
                    for mem_name, mem_data in memories["long_term"].items():
                        if isinstance(mem_data, dict):
                            description = mem_data.get("description", "No description")
                            content_parts.append(f"- `{mem_name}.md`: {description}")
                        else:
                            # Fallback if not parsed
                            content_parts.append(f"- `{mem_name}.md`")

                if not memories.get("short_term") and not memories.get("long_term"):
                    content_parts.append("  *No memories*")

        # Show archived memories (deduplicated historical context)
        archived = self.memory_config.get("archived_memories", {})
        if archived and (archived.get("short_term") or archived.get("long_term")):
            content_parts.append("\n### Archived Memories (Historical - Deduplicated)\n")
            content_parts.append(
                "These are historical memories from previous answers. Duplicate names have been resolved " "(showing only the most recent version of each memory). This is read-only context.\n",
            )

            # Show short_term archived memories (full content)
            if archived.get("short_term"):
                content_parts.append("\n**Short-term (full content):**")
                for mem_name, mem_data in archived["short_term"].items():
                    content = mem_data.get("content", "")
                    content_parts.append(f"\n- `{mem_name}.md`")
                    content_parts.append(f"  ```\n  {content.strip()}\n  ```")

            # Show long_term archived memories (name + description only)
            if archived.get("long_term"):
                content_parts.append("\n**Long-term (summaries only):**")
                for mem_name, mem_data in archived["long_term"].items():
                    content = mem_data.get("content", "")
                    # Try to extract description from YAML frontmatter
                    description = "No description"
                    if "description:" in content:
                        try:
                            # Simple extraction of description line
                            for line in content.split("\n"):
                                if line.strip().startswith("description:"):
                                    description = line.split("description:", 1)[1].strip()
                                    break
                        except Exception:
                            pass
                    content_parts.append(f"- `{mem_name}.md`: {description}")

        # File operations - simple and direct
        content_parts.append(
            "\n### Saving Memories\n\n"
            "Save memories by writing markdown files to the memory directory:\n"
            "- **Short-term** → `memory/short_term/{name}.md` (auto-loaded every turn)\n"
            "- **Long-term** → `memory/long_term/{name}.md` (load manually when needed)\n\n"
            "**File Format (REQUIRED YAML Frontmatter):**\n"
            "```markdown\n"
            "---\n"
            "name: skill_effectiveness\n"
            "description: Tracking which skills and tools work well for different task types\n"
            "created: 2025-11-23T20:00:00\n"
            "updated: 2025-11-23T20:00:00\n"
            "---\n\n"
            "## Your Content Here\n"
            "Document your findings...\n"
            "```\n\n"
            "**Important:** You are stateless - you don't have a persistent identity across restarts. "
            "When you call `new_answer`, your workspace is cleared and archived. The system shows you:\n"
            "1. Current memories from all agents (for comparing approaches)\n"
            "2. Historical archived memories (deduplicated - newest version of each name)\n\n"
            "If the same memory name appears multiple times, only the most recent version is shown.\n",
        )

        # Task completion reminders
        content_parts.append(
            "\n### Automatic Reminders\n\n"
            "When you complete high-priority tasks, tool responses will include reminders to document decisions. "
            "These help you optimize future work by capturing what worked, what didn't, and why.\n",
        )

        # When to document - with clear tier guidance
        content_parts.append(
            "\n### What to Document\n\n"
            "**SHORT-TERM (use for most things):**\n\n"
            "**User Preferences** → memory/short_term/user_prefs.md\n"
            "- What does the user value (speed vs quality, iteration vs one-shot, etc.)?\n"
            "- Coding style, naming conventions, workflow preferences\n"
            "- Example: 'User prefers iterative refinement with visual feedback'\n\n"
            "**Quick Observations** → memory/short_term/quick_notes.md\n"
            "- Tactical findings from current work\n"
            "- What worked/failed in this specific task\n"
            "- Tool tips and gotchas discovered\n"
            "- Example: 'create_directory fails on nested paths - create parent first'\n\n"
            "**Current Context** → memory/short_term/task_context.md\n"
            "- Key findings about the current task\n"
            "- Important decisions made\n"
            "- State of work in progress\n\n"
            "**LONG-TERM (only if detailed/comprehensive):**\n\n"
            "**Comprehensive Skill Analysis** → memory/long_term/skill_effectiveness.md\n"
            "- Detailed comparison of multiple skills/approaches\n"
            "- Cross-task patterns (>3 examples)\n"
            "- Only save if you have substantial evidence (100+ lines)\n\n"
            "**Detailed Post-Mortems** → memory/long_term/approach_patterns.md\n"
            "- In-depth analysis of complex approaches\n"
            "- Multi-step strategies with rationale\n"
            "- Only for significant architectural decisions\n\n"
            "**Note**: Most observations should go in **short_term**. Reserve long_term for truly "
            "detailed analyses that would clutter the auto-loaded context.\n",
        )

        # Examples - emphasize short-term for most uses
        content_parts.append(
            "\n### Examples\n\n"
            "```python\n"
            "# SHORT-TERM: Quick tactical observation (PREFERRED for most things)\n"
            "write_file(\n"
            '    "memory/short_term/quick_notes.md",\n'
            '    "---\\n"\n'
            '    "name: quick_notes\\n"\n'
            '    "description: Tactical observations from current work\\n"\n'
            '    "created: 2025-11-23T20:00:00\\n"\n'
            '    "updated: 2025-11-23T20:00:00\\n"\n'
            '    "---\\n\\n"\n'
            '    "## Web Development\\n"\n'
            '    "- create_directory fails on nested paths - create parent first\\n"\n'
            '    "- CSS variables work well for theming\\n"\n'
            '    "- Always test with `printf` for CLI stdin validation"\n'
            ")\n\n"
            "# SHORT-TERM: User preferences\n"
            "write_file(\n"
            '    "memory/short_term/user_prefs.md",\n'
            '    "---\\n"\n'
            '    "name: user_prefs\\n"\n'
            '    "description: User workflow and style preferences\\n"\n'
            '    "created: 2025-11-23T20:00:00\\n"\n'
            '    "updated: 2025-11-23T20:00:00\\n"\n'
            '    "---\\n\\n"\n'
            '    "## Preferences\\n"\n'
            '    "- Prefers clean, minimal code\\n"\n'
            '    "- Wants explanations with examples"\n'
            ")\n\n"
            "# LONG-TERM: Only for detailed analysis (>100 lines)\n"
            "write_file(\n"
            '    "memory/long_term/comprehensive_analysis.md",\n'
            '    "---\\n"\n'
            '    "name: comprehensive_analysis\\n"\n'
            '    "description: Detailed multi-task skill effectiveness analysis\\n"\n'
            '    "created: 2025-11-23T20:00:00\\n"\n'
            '    "updated: 2025-11-23T20:00:00\\n"\n'
            '    "---\\n\\n"\n'
            '    "[100+ lines of detailed analysis comparing approaches across multiple tasks...]"\n'
            ")\n"
            "```\n",
        )

        return "\n".join(content_parts)


class WorkspaceStructureSection(SystemPromptSection):
    """
    Critical workspace paths and structure information.

    This subsection of FilesystemSection contains the MUST-KNOW information
    about where files are located and how the workspace is organized.

    Args:
        workspace_path: Path to the agent's workspace directory
        context_paths: List of paths containing important context
    """

    def __init__(self, workspace_path: str, context_paths: List[str]):
        super().__init__(
            title="Workspace Structure",
            priority=Priority.HIGH,
            xml_tag="workspace_structure",
        )
        self.workspace_path = workspace_path
        self.context_paths = context_paths

    def build_content(self) -> str:
        """Build workspace structure documentation."""
        content_parts = []

        content_parts.append("## Workspace Paths\n")
        content_parts.append(f"**Workspace directory**: `{self.workspace_path}`")
        content_parts.append(
            "\nThis is your primary working directory where you should create " "and manage files for this task.\n",
        )

        if self.context_paths:
            content_parts.append("**Context paths**:")
            for path in self.context_paths:
                content_parts.append(f"- `{path}`")
            content_parts.append(
                "\nThese paths contain important context for your task. " "Review them before starting work.",
            )

        return "\n".join(content_parts)


class CommandExecutionSection(SystemPromptSection):
    """
    Command execution environment and instructions.

    Documents the execution environment (Docker vs native), available packages,
    and any restrictions.

    NOTE: Package list is manually maintained and should match massgen/docker/Dockerfile.
    TODO: Consider auto-generating this from the Dockerfile for accuracy.

    Args:
        docker_mode: Whether commands execute in Docker containers
        enable_sudo: Whether sudo is available in Docker containers
    """

    def __init__(self, docker_mode: bool = False, enable_sudo: bool = False):
        super().__init__(
            title="Command Execution",
            priority=Priority.MEDIUM,
            xml_tag="command_execution",
        )
        self.docker_mode = docker_mode
        self.enable_sudo = enable_sudo

    def build_content(self) -> str:
        parts = ["## Command Execution"]
        parts.append("You can run command line commands using the `execute_command` tool.")
        parts.append("**Efficiency**: Batch multiple commands in one call using `&&` (e.g., `ls servers/ && ls custom_tools/`)\n")

        if self.docker_mode:
            parts.append("**IMPORTANT: Docker Execution Environment**")
            parts.append("- You are running in a Linux Docker container (Debian-based)")
            parts.append("- Base image: Python 3.11-slim with Node.js 20.x LTS")
            parts.append(
                "- Pre-installed packages:\n"
                "  - System: git, curl, build-essential, ripgrep, gh (GitHub CLI)\n"
                "  - Python: pytest, requests, numpy, pandas, ast-grep-cli\n"
                "  - Node: npm, openskills (global)",
            )
            parts.append("- Use `apt-get` for system packages (NOT brew, dnf, yum, etc.)")

            if self.enable_sudo:
                parts.append(
                    "- **Sudo is available**: You can install packages with " "`sudo apt-get install <package>`",
                )
                parts.append("- Example: `sudo apt-get update && sudo apt-get install -y ffmpeg`")
            else:
                parts.append("- Sudo is NOT available - use pip/npm for user-level packages only")
                parts.append(
                    "- For system packages, ask the user to rebuild the Docker image with " "needed packages",
                )

            parts.append("")

        return "\n".join(parts)


class FilesystemOperationsSection(SystemPromptSection):
    """
    Filesystem tool usage instructions.

    Documents how to use filesystem tools for creating answers, managing
    files, and coordinating with other agents.

    Args:
        main_workspace: Path to agent's main workspace
        temp_workspace: Path to shared reference workspace
        context_paths: List of context paths with permissions
        previous_turns: List of previous turn metadata
        workspace_prepopulated: Whether workspace is pre-populated
        agent_answers: Dict of agent answers to show workspace structure
        enable_command_execution: Whether command line execution is enabled
    """

    def __init__(
        self,
        main_workspace: Optional[str] = None,
        temp_workspace: Optional[str] = None,
        context_paths: Optional[List[Dict[str, str]]] = None,
        previous_turns: Optional[List[Dict[str, Any]]] = None,
        workspace_prepopulated: bool = False,
        agent_answers: Optional[Dict[str, str]] = None,
        enable_command_execution: bool = False,
    ):
        super().__init__(
            title="Filesystem Operations",
            priority=Priority.MEDIUM,
            xml_tag="filesystem_operations",
        )
        self.main_workspace = main_workspace
        self.temp_workspace = temp_workspace
        self.context_paths = context_paths or []
        self.previous_turns = previous_turns or []
        self.workspace_prepopulated = workspace_prepopulated
        self.agent_answers = agent_answers
        self.enable_command_execution = enable_command_execution

    def build_content(self) -> str:
        parts = ["## Filesystem Access"]

        # Explain workspace behavior
        parts.append(
            "Your working directory is set to your workspace, so all relative paths in your file "
            "operations will be resolved from there. This ensures each agent works in isolation "
            "while having access to shared references. Only include in your workspace files that "
            "should be used in your answer.\n",
        )

        if self.main_workspace:
            workspace_note = f"**Your Workspace**: `{self.main_workspace}` - Write actual files here using " "file tools. All your file operations will be relative to this directory."
            if self.workspace_prepopulated:
                workspace_note += (
                    " **Note**: Your workspace already contains a writable copy of the previous "
                    "turn's results - you can modify or build upon these files. The original "
                    "unmodified version is also available as a read-only context path if you need "
                    "to reference what was originally there."
                )
            parts.append(workspace_note)

        if self.temp_workspace:
            # Build workspace tree structure
            workspace_tree = f"**Shared Reference**: `{self.temp_workspace}` - Contains previous answers from " "all agents (read/execute-only)\n"

            # Add agent subdirectories in tree format
            if self.agent_answers:
                agent_mapping = {}
                for i, agent_id in enumerate(sorted(self.agent_answers.keys()), 1):
                    agent_mapping[agent_id] = f"agent{i}"

                workspace_tree += "   Available agent workspaces:\n"
                agent_items = list(agent_mapping.items())
                for idx, (agent_id, anon_id) in enumerate(agent_items):
                    is_last = idx == len(agent_items) - 1
                    prefix = "   └── " if is_last else "   ├── "
                    workspace_tree += f"{prefix}{self.temp_workspace}/{anon_id}/\n"

            workspace_tree += (
                "   **Building on Others' Work:**\n"
                "   - **Inspect First**: Examine files before copying to understand what you're "
                "working with.\n"
                "   - **Selective Copying**: Only copy specific files you'll actually modify or "
                "use, not entire directories wholesale.\n"
                "   - **Merging Approaches**: If combining work from multiple agents, consider "
                "merging complementary parts (e.g., agent1's data model + agent2's API layer) "
                "rather than picking one entire solution.\n"
                "   - **Attribution**: Be explicit in your answer about what you built on (e.g., "
                "'Extended agent1's parser.py to handle edge cases').\n"
                "   - **Verify Files**: Not all workspaces may have matching answers in CURRENT "
                "ANSWERS section (restart scenarios). Check actual files in Shared Reference.\n"
            )
            parts.append(workspace_tree)

        if self.context_paths:
            has_target = any(p.get("will_be_writable", False) for p in self.context_paths)
            has_readonly_context = any(not p.get("will_be_writable", False) and p.get("permission") == "read" for p in self.context_paths)

            if has_target:
                parts.append(
                    "\n**Important Context**: If the user asks about improving, fixing, debugging, "
                    "or understanding an existing code/project (e.g., 'Why is this code not "
                    "working?', 'Fix this bug', 'Add feature X'), they are referring to the Target "
                    "Path below. First READ the existing files from that path to understand what's "
                    "there, then make your changes based on that codebase. Final deliverables must "
                    "end up there.\n",
                )
            elif has_readonly_context:
                parts.append(
                    "\n**Important Context**: If the user asks about debugging or understanding an "
                    "existing code/project (e.g., 'Why is this code not working?', 'Explain this "
                    "bug'), they are referring to (one of) the Context Path(s) below. Read then "
                    "provide analysis/explanation based on that codebase - you cannot modify it "
                    "directly.\n",
                )

            for path_config in self.context_paths:
                path = path_config.get("path", "")
                permission = path_config.get("permission", "read")
                will_be_writable = path_config.get("will_be_writable", False)
                if path:
                    if permission == "read" and will_be_writable:
                        parts.append(
                            f"**Target Path**: `{path}` (read-only now, write access later) - This "
                            "is where your changes will be delivered. Work in your workspace first, "
                            f"then the final presenter will place or update files DIRECTLY into "
                            f"`{path}` using the FULL ABSOLUTE PATH.",
                        )
                    elif permission == "write":
                        parts.append(
                            f"**Target Path**: `{path}` (write access) - This is where your changes "
                            "must be delivered. First, ensure you place your answer in your "
                            f"workspace, then copy/write files DIRECTLY into `{path}` using FULL "
                            f"ABSOLUTE PATH (not relative paths). Files must go directly into the "
                            f"target path itself (e.g., `{path}/file.txt`), NOT into a `.massgen/` "
                            "subdirectory within it.",
                        )
                    else:
                        parts.append(
                            f"**Context Path**: `{path}` (read-only) - Use FULL ABSOLUTE PATH when " "reading.",
                        )

        # Add note about multi-turn conversations
        if self.previous_turns:
            parts.append(
                "\n**Note**: This is a multi-turn conversation. Each User/Assistant exchange in "
                "the conversation history represents one turn. The workspace from each turn is "
                "available as a read-only context path listed above (e.g., turn 1's workspace is "
                "at the path ending in `/turn_1/workspace`).",
            )

        # Add task handling priority
        parts.append(
            "\n**Task Handling Priority**: When responding to user requests, follow this priority "
            "order:\n"
            "1. **Use MCP Tools First**: If you have specialized MCP tools available, call them "
            "DIRECTLY to complete the task\n"
            "   - Save any outputs/artifacts from MCP tools to your workspace\n"
            "2. **Write Code If Needed**: If MCP tools cannot complete the task, write and execute "
            "code\n"
            "3. **Create Other Files**: Create configs, documents, or other deliverables as "
            "needed\n"
            "4. **Text Response Otherwise**: If no tools or files are needed, provide a direct "
            "text answer\n\n"
            "**Important**: Do NOT ask the user for clarification or additional input. Make "
            "reasonable assumptions and proceed with sensible defaults. You will not receive user "
            "feedback, so complete the task autonomously based on the original request.\n",
        )

        # Add new answer guidance
        new_answer_guidance = "\n**New Answer**: When calling `new_answer`:\n"
        if self.enable_command_execution:
            new_answer_guidance += "- If you executed commands (e.g., running tests), explain the results in your " "answer (what passed, what failed, what the output shows)\n"
        new_answer_guidance += "- If you created files, list your cwd and file paths (but do NOT paste full file " "contents)\n"
        new_answer_guidance += "- If providing a text response, include your analysis/explanation in the `content` " "field\n"
        parts.append(new_answer_guidance)

        return "\n".join(parts)


class FilesystemBestPracticesSection(SystemPromptSection):
    """
    Optional filesystem best practices and tips.

    Lower priority guidance about workspace cleanup, comparison tools, and evaluation.

    Args:
        enable_code_based_tools: Whether code-based tools mode is enabled
    """

    def __init__(self, enable_code_based_tools: bool = False):
        super().__init__(
            title="Filesystem Best Practices",
            priority=Priority.AUXILIARY,
            xml_tag="filesystem_best_practices",
        )
        self.enable_code_based_tools = enable_code_based_tools

    def build_content(self) -> str:
        parts = []

        # Workspace management guidance
        parts.append(
            "**Workspace Management**: \n"
            "- **Selective Copying**: When building on other agents' work, only copy the specific "
            "files you need to modify or use. Do not copy entire workspaces wholesale. Be explicit "
            "about what you're building on (e.g., 'Using agent1's parser.py with "
            "modifications').\n"
            "- **Never Copy Gitignored Files**: Do NOT copy files/directories that are typically "
            "gitignored: `node_modules/`, `__pycache__/`, `.git/`, `venv/`, `env/`, `.env`, "
            "`dist/`, `build/`, `*.pyc`, `.cache/`, etc. These files are regenerated by running "
            "`npm install`, `pip install`, or build commands. Copying them breaks symlinks and "
            "causes errors. Instead, include proper dependency files (`package.json`, "
            "`requirements.txt`) and let users reinstall.\n"
            "- **Cleanup**: Remove any temporary files, intermediate artifacts, test scripts, or "
            "unused files copied from another agent before submitting `new_answer`. Your workspace "
            "should contain only the files that are part of your final deliverable. For example, "
            "if you created `test_output.txt` for debugging or `old_version.py` before "
            "refactoring, delete them.\n"
            "- **Organization**: Keep files logically organized. If you're combining work from "
            "multiple agents, structure the result clearly.\n",
        )

        # Comparison tools (conditional on mode)
        if self.enable_code_based_tools:
            parts.append(
                "**Comparison Tools**: Use directory and file comparison operations to understand "
                "differences between workspaces or versions. These read-only operations help you "
                "understand what changed, build upon existing work effectively, or verify solutions "
                "before voting.\n",
            )
        else:
            parts.append(
                "**Comparison Tools**: Use directory and file comparison tools to see differences "
                "between workspaces or versions. These read-only tools help you understand what "
                "changed, build upon existing work effectively, or verify solutions before voting.\n",
            )

        # Evaluation guidance - emphasize outcome-based evaluation
        parts.append(
            "**Evaluation**: When evaluating agents' answers, assess both implementation and results:\n"
            "- **For code quality**: Verify key files or substantially different implementations in "
            "their workspaces (via Shared Reference)\n"
            "- **For functionality**: Evaluate outcomes by running tests, checking visualizations, "
            "validating outputs, or testing the deliverables\n"
            "- **Focus verification**: Prioritize critical functionality and substantial differences "
            "rather than exhaustively reviewing every file\n"
            "- **Don't rely solely on answer text**: Ensure the actual work matches their claims\n",
        )

        return "\n".join(parts)


class FilesystemSection(SystemPromptSection):
    """
    Parent section for all filesystem-related instructions.

    Breaks the monolithic filesystem instructions into three prioritized
    subsections:
    1. Workspace structure (HIGH) - Must-know paths
    2. Operations (MEDIUM) - Tool usage
    3. Best practices (AUXILIARY) - Optional guidance

    Args:
        workspace_path: Path to agent's workspace
        context_paths: List of context paths
        main_workspace: Path to agent's main workspace
        temp_workspace: Path to shared reference workspace
        previous_turns: List of previous turn metadata
        workspace_prepopulated: Whether workspace is pre-populated
        agent_answers: Dict of agent answers to show workspace structure
        enable_command_execution: Whether command line execution is enabled
        docker_mode: Whether commands execute in Docker containers
        enable_sudo: Whether sudo is available in Docker containers
        enable_code_based_tools: Whether code-based tools mode is enabled
    """

    def __init__(
        self,
        workspace_path: str,
        context_paths: List[str],
        main_workspace: Optional[str] = None,
        temp_workspace: Optional[str] = None,
        context_paths_detailed: Optional[List[Dict[str, str]]] = None,
        previous_turns: Optional[List[Dict[str, Any]]] = None,
        workspace_prepopulated: bool = False,
        agent_answers: Optional[Dict[str, str]] = None,
        enable_command_execution: bool = False,
        docker_mode: bool = False,
        enable_sudo: bool = False,
        enable_code_based_tools: bool = False,
    ):
        super().__init__(
            title="Filesystem & Workspace",
            priority=Priority.HIGH,
            xml_tag="filesystem",
        )

        # Create subsections with appropriate priorities
        self.subsections = [
            WorkspaceStructureSection(workspace_path, context_paths),
            FilesystemOperationsSection(
                main_workspace=main_workspace,
                temp_workspace=temp_workspace,
                context_paths=context_paths_detailed,
                previous_turns=previous_turns,
                workspace_prepopulated=workspace_prepopulated,
                agent_answers=agent_answers,
                enable_command_execution=enable_command_execution,
            ),
            FilesystemBestPracticesSection(enable_code_based_tools=enable_code_based_tools),
        ]

        # Add command execution section if enabled
        if enable_command_execution:
            self.subsections.append(
                CommandExecutionSection(docker_mode=docker_mode, enable_sudo=enable_sudo),
            )

    def build_content(self) -> str:
        """Brief intro - subsections contain the details."""
        return "# Filesystem Instructions\n\n" "You have access to a filesystem-based workspace for managing your work " "and coordinating with other agents."


class TaskPlanningSection(SystemPromptSection):
    """
    Task planning guidance for complex multi-step tasks.

    Provides comprehensive instructions on when and how to use task planning
    tools for organizing multi-step work.

    Args:
        filesystem_mode: If True, includes guidance about filesystem-based task storage
    """

    def __init__(self, filesystem_mode: bool = False):
        super().__init__(
            title="Task Planning",
            priority=Priority.MEDIUM,
            xml_tag="task_planning",
        )
        self.filesystem_mode = filesystem_mode

    def build_content(self) -> str:
        base_guidance = """
# Task Planning and Management

You have access to task planning tools to organize complex work.

**IMPORTANT WORKFLOW - Plan Before Executing:**

When working on multi-step tasks:
1. **Think first** - Understand the requirements (some initial research/analysis is fine)
2. **Create your task plan EARLY** - Use `create_task_plan()` BEFORE executing file operations or major
   actions
3. **Execute tasks** - Work through your plan systematically
4. **Update as you go** - Use `add_task()` to capture new requirements you discover

**DO NOT:**
- ❌ Jump straight into creating files without planning first
- ❌ Start executing complex work without a clear task breakdown
- ❌ Ignore the planning tools for multi-step work

**DO:**
- ✅ Create a task plan early, even if it's just 3-4 high-level tasks
- ✅ Refine your plan as you learn more (tasks can be added/edited/deleted)
- ✅ Brief initial analysis is OK before planning (e.g., reading docs, checking existing code)

**When to create a task plan:**
- Multi-step tasks with dependencies (most common)
- Multiple files or components to create
- Complex features requiring coordination
- Work that needs to be tracked or broken down
- Any task where you'd benefit from a checklist

**Skip task planning ONLY for:**
- Trivial single-step tasks
- Simple questions/analysis with no execution
- Quick one-off operations

**Tools available:**
- `create_task_plan(tasks)` - Create a plan with tasks and dependencies
- `get_ready_tasks()` - Get tasks ready to start (dependencies satisfied)
- `get_blocked_tasks()` - See what's waiting on dependencies
- `update_task_status(task_id, status)` - Mark progress (pending/in_progress/completed)
- `add_task(description, depends_on, priority)` - Add new tasks (priority: low/medium/high)
- `get_task_plan()` - View your complete task plan
- `edit_task(task_id, description)` - Update task descriptions
- `delete_task(task_id)` - Remove tasks no longer needed

**Reading Tool Responses:**
Tool responses may include important reminders and guidance (e.g., when completing high-priority tasks,
you'll receive reminders to save learnings to memory). Always read tool response messages carefully.

**Recommended workflow:**
```python
# 1. Create plan FIRST (before major execution)
plan = create_task_plan([
    {"id": "research", "description": "Research OAuth providers"},
    {"id": "design", "description": "Design auth flow", "depends_on": ["research"]},
    {"id": "implement", "description": "Implement endpoints", "depends_on": ["design"]}
])

# 2. Work through tasks systematically
update_task_status("research", "in_progress")
# ... do research work ...
update_task_status("research", "completed")

# 3. Add tasks as you discover new requirements
add_task("Write integration tests", depends_on=["implement"])

# 4. Continue working
ready = get_ready_tasks()  # ["design"]
update_task_status("design", "in_progress")
```

**Dependency formats:**
```python
# By index (0-based)
create_task_plan([
    "Task 1",
    {"description": "Task 2", "depends_on": [0]}  # Depends on Task 1
])

# By ID (recommended for clarity)
create_task_plan([
    {"id": "auth", "description": "Setup auth"},
    {"id": "api", "description": "Build API", "depends_on": ["auth"]}
])
```

**IMPORTANT - Including Task Plan in Your Answer:**
If you created a task plan, include a summary at the end of your `new_answer` showing:
1. Each task name
2. Completion status (✓ or ✗)
3. Brief description of what you did

Example format:
```
[Your main answer content here]

---
**Task Execution Summary:**
✓ Research OAuth providers - Analyzed OAuth 2.0 spec and compared providers
✓ Design auth flow - Created flow diagram with PKCE and token refresh
✓ Implement endpoints - Built /auth/login, /auth/callback, /auth/refresh
✓ Write tests - Added integration tests for auth flow

Status: 4/4 tasks completed
```

This helps other agents understand your approach and makes voting more specific."""

        if self.filesystem_mode:
            filesystem_guidance = """

**Filesystem Mode Enabled:**
Your task plans are automatically saved to `tasks/plan.json` in your workspace. You can write notes
or comments in `tasks/notes.md` or other files in the `tasks/` directory.

*NOTE*: You will also have access to other agents' task plans in the shared reference."""
            return base_guidance + filesystem_guidance

        return base_guidance


class EvaluationSection(SystemPromptSection):
    """
    MassGen evaluation and coordination mechanics.

    Priority 2 places this after agent_identity(1) but before core_behaviors(3).
    This defines the fundamental MassGen primitives that the agent needs to understand:
    vote tool, new_answer tool, and coordination mechanics.

    Args:
        voting_sensitivity: Controls evaluation strictness ('lenient', 'balanced', 'strict')
        answer_novelty_requirement: Controls novelty requirements ('lenient', 'balanced', 'strict')
    """

    def __init__(
        self,
        voting_sensitivity: str = "lenient",
        answer_novelty_requirement: str = "lenient",
    ):
        super().__init__(
            title="MassGen Coordination",
            priority=2,  # After agent_identity(1), before core_behaviors(3)
            xml_tag="massgen_coordination",
        )
        self.voting_sensitivity = voting_sensitivity
        self.answer_novelty_requirement = answer_novelty_requirement

    def build_content(self) -> str:
        import time

        # Determine evaluation criteria based on voting sensitivity
        if self.voting_sensitivity == "strict":
            evaluation_section = """Does the best CURRENT ANSWER address the ORIGINAL MESSAGE exceptionally well? Consider:
- Is it comprehensive, addressing ALL aspects and edge cases?
- Is it technically accurate and well-reasoned?
- Does it provide clear explanations and proper justification?
- Is it complete with no significant gaps or weaknesses?
- Could it serve as a reference-quality solution?

Only use the `vote` tool if the best answer meets high standards of excellence."""
        elif self.voting_sensitivity == "balanced":
            evaluation_section = """Does the best CURRENT ANSWER address the ORIGINAL MESSAGE well? Consider:
- Is it comprehensive, accurate, and complete?
- Could it be meaningfully improved, refined, or expanded?
- Are there weaknesses, gaps, or better approaches?

Only use the `vote` tool if the best answer is strong and complete."""
        else:
            # Default to lenient (including explicit "lenient" or any other value)
            evaluation_section = """Does the best CURRENT ANSWER address the ORIGINAL MESSAGE well?

If YES, use the `vote` tool to record your vote and skip the `new_answer` tool."""

        # Add novelty requirement instructions if not lenient
        novelty_section = ""
        if self.answer_novelty_requirement == "balanced":
            novelty_section = """
IMPORTANT: If you provide a new answer, it must be meaningfully different from existing answers.
- Don't just rephrase or reword existing solutions
- Introduce new insights, approaches, or tools
- Make substantive improvements, not cosmetic changes"""
        elif self.answer_novelty_requirement == "strict":
            novelty_section = """
CRITICAL: New answers must be SUBSTANTIALLY different from existing answers.
- Use a fundamentally different approach or methodology
- Employ different tools or techniques
- Provide significantly more depth or novel perspectives
- If you cannot provide a truly novel solution, vote instead"""

        return f"""You are evaluating answers from multiple agents for final response to a message.
Different agents may have different builtin tools and capabilities.
{evaluation_section}
Otherwise, digest existing answers, combine their strengths, and do additional work to address their weaknesses,
then use the `new_answer` tool to record a better answer to the ORIGINAL MESSAGE.{novelty_section}
Make sure you actually call `vote` or `new_answer` (in tool call format).

*Note*: The CURRENT TIME is **{time.strftime("%Y-%m-%d %H:%M:%S")}**."""


class PostEvaluationSection(SystemPromptSection):
    """
    Post-evaluation phase instructions.

    After final presentation, the winning agent evaluates its own answer
    and decides whether to submit or restart with improvements.

    MEDIUM priority as this is phase-specific operational guidance.
    """

    def __init__(self):
        super().__init__(
            title="Post-Presentation Evaluation",
            priority=Priority.MEDIUM,
            xml_tag="post_evaluation",
        )

    def build_content(self) -> str:
        return """## Post-Presentation Evaluation

You have just presented a final answer to the user. Now you must evaluate whether your answer fully addresses the original task.

**Your Task:**
Review the final answer that was presented and determine if it completely and accurately addresses the original task requirements.

**Available Tools:**
You have access to the same filesystem and MCP tools that were available during presentation. Use these tools to:
- Verify that claimed files actually exist in the workspace
- Check file contents to confirm they match what was described
- Validate any technical claims or implementations

**Decision:**
You must call ONE of these tools:

1. **submit(confirmed=True)** - Use this when:
   - The answer fully addresses ALL parts of the original task
   - All claims in the answer are accurate and verified
   - The work is complete and ready for the user

2. **restart_orchestration(reason, instructions)** - Use this when:
   - The answer is incomplete (missing required elements)
   - The answer contains errors or inaccuracies
   - Important aspects of the task were not addressed

   Provide:
   - **reason**: Clear explanation of what's wrong (e.g., "The task required descriptions of two Beatles, but only John Lennon was described")
   - **instructions**: Detailed, actionable guidance for the next attempt (e.g.,
     "Provide two descriptions (John Lennon AND Paul McCartney). Each should include:
     birth year, role in band, notable songs, impact on music. Use 4-6 sentences per person.")

**Important Notes:**
- Be honest and thorough in your evaluation
- You are evaluating your own work with a fresh perspective
- If you find problems, restarting with clear instructions will lead to a better result
- The restart process gives you another opportunity to get it right
"""


class PlanningModeSection(SystemPromptSection):
    """
    Planning mode instructions (conditional).

    Only included when planning mode is enabled. Instructs agent to
    think through approach before executing.

    Args:
        planning_mode_instruction: The planning mode instruction text
    """

    def __init__(self, planning_mode_instruction: str):
        super().__init__(
            title="Planning Mode",
            priority=Priority.MEDIUM,
            xml_tag="planning_mode",
        )
        self.planning_mode_instruction = planning_mode_instruction

    def build_content(self) -> str:
        return self.planning_mode_instruction


class BroadcastCommunicationSection(SystemPromptSection):
    """
    Agent-to-agent communication capabilities via broadcast tools.

    Provides instructions for using ask_others() tool for collaborative
    problem-solving between agents, with configurable sensitivity levels.

    This section appears at HIGH priority to provide coordination guidance
    after critical context but before auxiliary best practices.

    Args:
        broadcast_mode: Communication mode - "agents" (agent-to-agent only)
                       or "human" (agents can ask agents + human)
        wait_by_default: Whether ask_others() blocks by default (True)
                        or returns immediately for polling (False)
        sensitivity: How frequently to use ask_others():
                    - "low": Only for critical decisions/when blocked
                    - "medium": For significant decisions and design choices (default)
                    - "high": Frequently - whenever considering options

    Example:
        >>> section = BroadcastCommunicationSection(
        ...     broadcast_mode="agents",
        ...     wait_by_default=True,
        ...     sensitivity="medium"
        ... )
        >>> print(section.render())
    """

    def __init__(
        self,
        broadcast_mode: str,
        wait_by_default: bool = True,
        sensitivity: str = "medium",
        human_qa_history: List[Dict[str, Any]] = None,
    ):
        super().__init__(
            title="Broadcast Communication",
            priority=Priority.HIGH,  # Elevated from MEDIUM for stronger emphasis
            xml_tag="broadcast_communication",
        )
        self.broadcast_mode = broadcast_mode
        self.wait_by_default = wait_by_default
        self.sensitivity = sensitivity
        self.human_qa_history = human_qa_history or []

    def build_content(self) -> str:
        """Build broadcast communication instructions."""
        lines = [
            "## Agent Communication",
            "",
            "**CRITICAL TOOL: ask_others()**",
            "",
        ]

        if self.broadcast_mode == "human":
            lines.append("You MUST use the `ask_others()` tool to ask questions to the human user.")
        else:
            lines.append("You MUST use the `ask_others()` tool to collaborate with other agents.")

        lines.append("")

        # Add sensitivity-specific guidance
        if self.sensitivity == "high":
            lines.append("**Collaboration frequency: HIGH - You MUST use ask_others() frequently whenever you're considering options, proposing approaches, or making decisions.**")
        elif self.sensitivity == "low":
            lines.append("**Collaboration frequency: LOW - You MUST use ask_others() when blocked or for critical architectural decisions.**")
        else:  # medium
            lines.append("**Collaboration frequency: MEDIUM - You MUST use ask_others() for significant decisions, design choices, or when confirmation would be valuable.**")

        lines.extend(
            [
                "",
                "**When you MUST use ask_others():**",
                '- **User explicitly requests collaboration**: If prompt says "ask_others for..." then CALL THE TOOL immediately',
                "- **Before key decisions**: Architecture, framework, approach choices",
                "- **When you need specific information**: Include context about YOUR project so others can help",
                "- **Before significant implementation**: Describe your current setup and ask for input",
                "",
                "**When NOT to use ask_others():**",
                "- For rhetorical questions or obvious answers",
                "- Repeatedly on the same topic (one broadcast per decision)",
                "- For trivial implementation details",
                "",
                "**Timing:**",
                '- **User says "ask_others"**: Call tool immediately',
                "- **Before deciding**: Ask first, then provide answer with responses",
                "- **For feedback**: Provide answer first, then ask for feedback",
                "",
                "**IMPORTANT: Include responses in your answer:**",
                "When you receive responses from ask_others(), INCLUDE them in your new_answer():",
                '- Example: "I asked about framework. Response: Use Vue. Based on this, I will..."',
                "- Check your answer before asking again - reuse documented responses",
                "",
                "**How it works:**",
            ],
        )

        if self.wait_by_default:
            if self.broadcast_mode == "human":
                lines.extend(
                    [
                        "- Call `ask_others(question)` with your question",
                        "- The tool blocks and waits for the human's response",
                        "- Returns the human's response when ready",
                        "- You can then continue with your task",
                    ],
                )
            else:
                lines.extend(
                    [
                        "- Call `ask_others(question)` with your question",
                        "- The tool blocks and waits for responses from other agents",
                        "- Returns all responses immediately when ready",
                        "- You can then continue with your task",
                    ],
                )
        else:
            lines.extend(
                [
                    "- Call `ask_others(question, wait=False)` to send question without waiting",
                    "- Continue working on other tasks",
                    "- Later, check status with `check_broadcast_status(request_id)`",
                    "- Get responses with `get_broadcast_responses(request_id)` when ready",
                ],
            )

        lines.extend(
            [
                "",
                "**Best practices:**",
                "- Be specific and actionable in your questions",
                "- Use when you genuinely need coordination or input",
                "- Actually CALL THE TOOL (don't just mention it in your answer text)",
                "- Respond helpfully when others ask you questions",
                "",
                "**Examples of good questions (include ALL relevant context - other agents cannot see your workspace):**",
                '- "I\'m building an e-commerce site with Next.js. The client wants product pages to be SEO-friendly. Should I use SSR, SSG, or ISR for the product catalog?"',
                "- \"I need to add a 'last_login' field to track user sessions. The User model currently has id, email, password_hash, created_at. Any concerns with adding this timestamp field?\"",
                '- "Setting up OAuth for a Node.js/Express API. The project uses Passport.js. Should I add Google OAuth with passport-google-oauth20, or is there a better approach?"',
                '- "I\'m refactoring authentication in a Django app that currently uses session-based auth. Considering switching to JWT for mobile API support. What are the tradeoffs?"',
                '- "Building a real-time dashboard that needs to handle 1000+ concurrent users. Using React frontend with WebSocket. Should I use Socket.io or native WebSocket API?"',
            ],
        )

        if self.broadcast_mode == "human":
            lines.extend(
                [
                    "",
                    "**Note:** In human mode, only the human responds to your questions (other agents are not notified).",
                ],
            )

        # Inject human Q&A history if available (human mode only)
        if self.human_qa_history and self.broadcast_mode == "human":
            lines.extend(
                [
                    "",
                    "**Human has already answered these questions this turn:**",
                ],
            )
            for i, qa in enumerate(self.human_qa_history, 1):
                lines.append(f"- Q{i}: {qa['question']}")
                lines.append(f"  A{i}: {qa['answer']}")
            lines.extend(
                [
                    "",
                    "Check if your question is already answered above before calling ask_others().",
                ],
            )

        return "\n".join(lines)


class EvolvingSkillsSection(SystemPromptSection):
    """
    Guidance on evolving skills - detailed workflow plans.

    Includes the full evolving-skill-creator content directly in the system prompt
    so agents don't need to read it separately.
    """

    def __init__(self):
        super().__init__(
            title="Evolving Skills",
            priority=6,  # After core_behaviors(4), task_planning(5)
            xml_tag="evolving_skills",
        )

    def build_content(self) -> str:
        return """## Evolving Skills

**REQUIRED**: Before starting work on any task, you MUST create an evolving skill - a detailed workflow plan.

### What is an Evolving Skill?

An evolving skill is a workflow plan that:
1. Documents specific steps to accomplish a goal
2. Lists Python scripts you'll create as reusable tools
3. Captures learnings after execution for future improvement

Unlike static skills, evolving skills are refined through use.

### Directory Structure

```
tasks/evolving_skill/
├── SKILL.md              # Your workflow plan
└── scripts/              # Python tools you create during execution
    ├── scrape_data.py
    └── generate_output.py
```

### SKILL.md Format

```yaml
---
name: task-name-here
description: What this workflow does and when to use it
---
# Task Name

## Overview
Brief description of the problem this skill solves.

## Workflow
Detailed numbered steps:
1. First step - be specific
2. Second step - include commands/tools to use
3. ...

## Tools to Create
Python scripts you'll write. Document BEFORE writing them:

### scripts/example_tool.py
- **Purpose**: What it does
- **Inputs**: What it takes (args, files, etc.)
- **Outputs**: What it produces
- **Dependencies**: Required packages

## Tools to Use
(Discover what's available, list ones you'll use)
- servers/name: MCP server tools
- custom_tools/name: Python tool implementations

## Skills
- skill_name: how it will help

## Packages
- package_name (pip install package_name)

## Expected Outputs
- Files this workflow produces
- Formats and locations

## Learnings
(Add after execution)

### What Worked Well
- ...

### What Didn't Work
- ...

### Tips for Future Use
- ...
```

### Tools to Create Section

This is key. When your workflow involves writing Python scripts, document them upfront:

```markdown
## Tools to Create

### scripts/fetch_artist_data.py
- **Purpose**: Crawl Wikipedia and extract artist biographical data
- **Inputs**: artist_name (str), output_path (str)
- **Outputs**: JSON file with structured bio data
- **Dependencies**: crawl4ai, json

### scripts/build_site.py
- **Purpose**: Generate static HTML from artist data
- **Inputs**: data_path (str), theme (str), output_dir (str)
- **Outputs**: Complete website in output_dir/
- **Dependencies**: jinja2
```

After execution, the actual scripts live in `scripts/` and can be reused.

### Required Steps

1. **BEFORE starting work**: Create `tasks/evolving_skill/SKILL.md` with your workflow plan
2. **During execution**: Follow your plan, create scripts as documented
3. **AFTER completing work**: Update SKILL.md with Learnings section

### Key Principles

1. **Be specific** - Workflow steps should be actionable, not vague
2. **Document tools upfront** - Plan scripts before writing them
3. **Update with learnings** - The skill improves through use
4. **Keep scripts reusable** - Design tools to work in similar future tasks"""


class SystemPromptBuilder:
    """
    Builder for assembling system prompts from sections.

    Automatically handles:
    - Priority-based sorting
    - XML structure wrapping
    - Conditional section inclusion (via enabled flag)
    - Hierarchical subsection rendering

    Example:
        >>> builder = SystemPromptBuilder()
        >>> builder.add_section(AgentIdentitySection("You are..."))
        >>> builder.add_section(SkillsSection(skills=[...]))
        >>> system_prompt = builder.build()
    """

    def __init__(self):
        self.sections: List[SystemPromptSection] = []

    def add_section(self, section: SystemPromptSection) -> "SystemPromptBuilder":
        """
        Add a section to the builder.

        Args:
            section: SystemPromptSection instance to add

        Returns:
            Self for method chaining (builder pattern)
        """
        self.sections.append(section)
        return self

    def build(self) -> str:
        """
        Assemble the final system prompt.

        Process:
        1. Filter to enabled sections only
        2. Sort by priority (lower number = earlier in prompt)
        3. Render each section (with XML if specified)
        4. Join with blank lines
        5. Wrap in root <system_prompt> XML tag

        Returns:
            Complete system prompt string ready for use
        """
        # Filter to enabled sections only
        enabled_sections = [s for s in self.sections if s.enabled]

        # Sort by priority (CRITICAL=1 comes before LOW=15)
        sorted_sections = sorted(enabled_sections, key=lambda s: s.priority)

        # Render each section
        rendered_sections = [s.render() for s in sorted_sections]

        # Join with blank lines
        content = "\n\n".join(rendered_sections)

        # Wrap in root tag
        return f"<system_prompt>\n\n{content}\n\n</system_prompt>"
