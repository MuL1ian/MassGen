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
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


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


class GPT5GuidanceSection(SystemPromptSection):
    """
    GPT-5.x specific guidance for solution persistence and tool preambles.

    Encourages autonomous, end-to-end task completion and structured tool
    usage narration based on OpenAI's GPT-5 prompting guides.

    Only included when the model is GPT-5.x (gpt-5, gpt-5.1, gpt-5.2, etc.)
    Priority 4 places this alongside CoreBehaviorsSection.

    References:
        - https://cookbook.openai.com/examples/gpt-5/gpt-5-1_prompting_guide#encouraging-complete-solutions
        - https://cookbook.openai.com/examples/gpt-5/gpt-5_prompting_guide#tool-preambles
    """

    def __init__(self):
        super().__init__(
            title="GPT-5 Guidance",
            priority=4,  # Same priority as CoreBehaviorsSection
            xml_tag=None,  # Uses internal XML tags for each subsection
        )

    def build_content(self) -> str:
        return (
            "<solution_persistence>\n"
            "- Treat yourself as an autonomous senior pair-programmer: once the user gives a direction, "
            "proactively gather context, plan, implement, test, and refine without waiting for additional "
            "prompts at each step.\n"
            "- Persist until the task is fully handled end-to-end within the current turn whenever feasible: "
            "do not stop at analysis or partial fixes; carry changes through implementation, verification, "
            "and a clear explanation of outcomes unless the user explicitly pauses or redirects you.\n"
            "- Be extremely biased for action. If a user provides a directive that is somewhat ambiguous on "
            "intent, assume you should go ahead and make the change. If the user asks a question like "
            '"should we do x?" and your answer is "yes", you should also go ahead and perform the action. '
            "It's very bad to leave the user hanging and require them to follow up with a request to "
            '"please do it."\n'
            "</solution_persistence>\n\n"
            "<tool_preambles>\n"
            "- As you execute your file edit(s) and other tool calls, narrate each step succinctly and "
            "sequentially, marking progress clearly.\n"
            "- CRITICAL: If your task requires creating or modifying files, you MUST use file tools to "
            "actually write them to the filesystem. Do NOT just output file contents in the new_answer "
            "text using markdown - the files will not exist unless you call the appropriate writing and "
            "editing tools.\n"
            "</tool_preambles>"
        )


class GrokGuidanceSection(SystemPromptSection):
    """
    Grok-specific guidance for file content encoding.

    Addresses a known issue where Grok models (particularly Grok 4.1) HTML-escape
    file content when writing SVG, XML, HTML, or other files containing angle
    brackets. This results in corrupted files with &lt; instead of <, etc.

    Only included when the model is Grok (grok-*).
    Priority 4 places this alongside CoreBehaviorsSection.
    """

    def __init__(self):
        super().__init__(
            title="Grok Guidance",
            priority=4,  # Same priority as CoreBehaviorsSection
            xml_tag=None,  # Uses internal XML tags
        )

    def build_content(self) -> str:
        return (
            "<file_content_encoding>\n"
            "CRITICAL: When writing file content, pass the content EXACTLY as it should appear in the file. "
            "Do NOT HTML-escape or XML-escape the content.\n"
            '- Write literal characters: use < not &lt;, use > not &gt;, use " not &quot;, use & not &amp;\n'
            "- The file writing tool expects raw content, not escaped content. Escaping will corrupt the file.\n"
            "</file_content_encoding>"
        )


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
        content_parts.append("- Invoke: run the command `openskills read <skill-name>`")
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
    For comprehensive guidance, agents can run: `openskills read file-search`

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

For detailed guidance including targeting strategies and examples, run: `openskills read file-search`"""


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
                logger.warning(f"Failed to fetch MCP descriptions: {e}")
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
1. **Batch discovery operations**: Combine `ls`, `rg`, `sg` in a single command execution call
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
            "**SHORT-TERM: Quick tactical observation** (PREFERRED for most things)\n"
            "Use the file write tool to save to `memory/short_term/quick_notes.md`:\n"
            "```markdown\n"
            "---\n"
            "name: quick_notes\n"
            "description: Tactical observations from current work\n"
            "created: 2025-11-23T20:00:00\n"
            "updated: 2025-11-23T20:00:00\n"
            "---\n\n"
            "## Web Development\n"
            "- create_directory fails on nested paths - create parent first\n"
            "- CSS variables work well for theming\n"
            "- Always test with `printf` for CLI stdin validation\n"
            "```\n\n"
            "**SHORT-TERM: User preferences**\n"
            "Save to `memory/short_term/user_prefs.md`:\n"
            "```markdown\n"
            "---\n"
            "name: user_prefs\n"
            "description: User workflow and style preferences\n"
            "created: 2025-11-23T20:00:00\n"
            "updated: 2025-11-23T20:00:00\n"
            "---\n\n"
            "## Preferences\n"
            "- Prefers clean, minimal code\n"
            "- Wants explanations with examples\n"
            "```\n\n"
            "**LONG-TERM: Only for detailed analysis** (>100 lines)\n"
            "Save to `memory/long_term/comprehensive_analysis.md`:\n"
            "```markdown\n"
            "---\n"
            "name: comprehensive_analysis\n"
            "description: Detailed multi-task skill effectiveness analysis\n"
            "created: 2025-11-23T20:00:00\n"
            "updated: 2025-11-23T20:00:00\n"
            "---\n\n"
            "[100+ lines of detailed analysis comparing approaches across multiple tasks...]\n"
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
        use_two_tier_workspace: If True, include documentation for scratch/deliverable structure
    """

    def __init__(self, workspace_path: str, context_paths: List[str], use_two_tier_workspace: bool = False):
        super().__init__(
            title="Workspace Structure",
            priority=Priority.HIGH,
            xml_tag="workspace_structure",
        )
        self.workspace_path = workspace_path
        self.context_paths = context_paths
        self.use_two_tier_workspace = use_two_tier_workspace

    def build_content(self) -> str:
        """Build workspace structure documentation."""
        content_parts = []

        content_parts.append("## Workspace Paths\n")
        content_parts.append(f"**Workspace directory**: `{self.workspace_path}`")
        content_parts.append(
            "\nThis is your primary working directory where you should create " "and manage files for this task.\n",
        )

        # Add two-tier workspace documentation if enabled
        if self.use_two_tier_workspace:
            content_parts.append("### Two-Tier Workspace Structure\n")
            content_parts.append("Your workspace has two directories for organizing your work:\n")
            content_parts.append("- **`scratch/`** - Use for working files, experiments, intermediate results, evaluation scripts")
            content_parts.append("- **`deliverable/`** - Use for final outputs you want to showcase to voters\n")
            content_parts.append("**IMPORTANT: Deliverables must be self-contained and complete.**")
            content_parts.append("The `deliverable/` directory should contain everything needed to use your output:")
            content_parts.append("- All required files (not just one component)")
            content_parts.append("- Any dependencies, assets, or supporting files")
            content_parts.append("- A README explaining how to run/use it")
            content_parts.append("Think of `deliverable/` as a standalone package that voters can immediately use without needing files from `scratch/` or anywhere else.\n")
            content_parts.append("To promote files from scratch to deliverable, use standard file operations:")
            content_parts.append("- Copy: Use filesystem tools to copy files")
            content_parts.append("- Move: Use command line `mv` or filesystem move\n")
            content_parts.append("**Note**: Voters will see BOTH directories, so scratch/ helps them understand your process.\n")
            content_parts.append("### Git Version Control\n")
            content_parts.append("Your workspace is version controlled with git. Changes are automatically committed:")
            content_parts.append("- `[INIT]` - When workspace is created")
            content_parts.append("- `[SNAPSHOT]` - Before coordination checkpoints")
            content_parts.append("- `[TASK]` - When you complete a task with completion notes\n")
            content_parts.append("**Tip**: Use `git log --oneline` to see your work history. This can help you:")
            content_parts.append("- Review what you've accomplished")
            content_parts.append("- Find when specific changes were made")
            content_parts.append("- Recover previous versions if needed\n")

        if self.context_paths:
            content_parts.append("**Context paths**:")
            for path in self.context_paths:
                content_parts.append(f"- `{path}`")
            content_parts.append(
                "\nThese paths contain important context for your task. " "Review them before starting work.",
            )

        return "\n".join(content_parts)


class ProjectInstructionsSection(SystemPromptSection):
    """
    Project-specific instructions from CLAUDE.md or AGENTS.md files.

    Automatically discovers and includes project instruction files when they exist
    in context paths. Follows the agents.md standard (https://agents.md/) with
    hierarchical discovery - the closest CLAUDE.md or AGENTS.md to the context
    path wins.

    Priority order:
    1. CLAUDE.md (Claude Code specific)
    2. AGENTS.md (universal standard - 60k+ projects)

    Discovery algorithm:
    - Starts at context path directory
    - Walks UP the directory tree searching for instruction files
    - Returns first CLAUDE.md or AGENTS.md found (closest wins)
    - CLAUDE.md takes precedence over AGENTS.md at same level
    - Stops at filesystem root or after 10 levels (safety limit)

    Args:
        context_paths: List of context path dictionaries (with "path" key)
        workspace_root: Agent workspace root (kept for backwards compatibility, not used for search boundary)
    """

    def __init__(self, context_paths: List[Dict[str, str]], workspace_root: str):
        super().__init__(
            title="Project Instructions",
            priority=Priority.HIGH,  # Important context, but not operational instructions
            xml_tag="project_instructions",
        )
        self.context_paths = context_paths
        self.workspace_root = Path(workspace_root) if workspace_root else Path.cwd()

    def discover_instruction_file(self, context_path: Path) -> Optional[Path]:
        """
        Walk up from context_path searching for CLAUDE.md or AGENTS.md.
        Returns the closest instruction file found.
        CLAUDE.md takes precedence over AGENTS.md at the same level.

        Stops searching when:
        1. An instruction file is found (success)
        2. We reach the filesystem root (no more parents)
        3. We've searched up to a reasonable depth (safety limit)
        """
        current = context_path if context_path.is_dir() else context_path.parent

        # Safety limit: search up to 10 levels max (prevents infinite loops)
        max_depth = 10
        depth = 0

        # Walk up directory hierarchy
        while current and depth < max_depth:
            # Priority 1: CLAUDE.md (Claude-specific)
            claude_md = current / "CLAUDE.md"
            if claude_md.exists() and claude_md.is_file():
                return claude_md

            # Priority 2: AGENTS.md (universal standard)
            agents_md = current / "AGENTS.md"
            if agents_md.exists() and agents_md.is_file():
                return agents_md

            # Stop at filesystem root
            parent = current.parent
            if parent == current:
                break

            current = parent
            depth += 1

        return None

    def build_content(self) -> str:
        """
        Discover and inject CLAUDE.md/AGENTS.md contents from context paths.
        Uses "closest wins" semantics - only one instruction file per context path.
        """
        # Collect discovered instruction files (deduplicate by path)
        discovered_files = {}  # path -> file_path mapping

        for ctx_path in self.context_paths:
            path_str = ctx_path.get("path", "")
            if not path_str:
                continue

            try:
                path = Path(path_str).resolve()

                # Check if path IS an instruction file directly
                if path.name in ["CLAUDE.md", "AGENTS.md"]:
                    if path.exists() and path.is_file():
                        discovered_files[str(path)] = path
                        continue

                # Otherwise, discover from directory hierarchy
                instruction_file = self.discover_instruction_file(path)
                if instruction_file:
                    discovered_files[str(instruction_file)] = instruction_file

            except Exception as e:
                logger.warning(f"Error checking context path {path_str} for instruction files: {e}")

        if not discovered_files:
            return ""  # No instruction files found

        # Read and format contents
        content_parts = []

        for file_path in discovered_files.values():
            try:
                contents = file_path.read_text(encoding="utf-8")
                # Dedent/clean up any leading/trailing whitespace
                contents = contents.strip()

                logger.info(f"[ProjectInstructionsSection] Loaded {file_path.name} ({len(contents)} chars)")
                content_parts.append(f"**From {file_path.name}** (`{file_path}`):")
                content_parts.append(contents)

            except Exception as e:
                logger.warning(f"Could not read instruction file {file_path}: {e}")

        if not content_parts:
            return ""  # Failed to read any files

        # Format with appropriate framing
        # NOTE: We follow Claude in using a softer framing than strict "Follow these instructions"
        # because this context may or may not be relevant to the current task
        header = [
            "The following project instructions were found in your context paths.",
            "",
            "**IMPORTANT**: This context may or may not be relevant to your current task.",
            "Use these instructions as helpful reference material when applicable,",
            "but do not feel obligated to follow guidance that doesn't apply to what you're doing.",
            "",
        ]

        return "\n".join(header + content_parts)


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
        concurrent_tool_execution: Whether tools execute in parallel
    """

    def __init__(self, docker_mode: bool = False, enable_sudo: bool = False, concurrent_tool_execution: bool = False):
        super().__init__(
            title="Command Execution",
            priority=Priority.MEDIUM,
            xml_tag="command_execution",
        )
        self.docker_mode = docker_mode
        self.enable_sudo = enable_sudo
        self.concurrent_tool_execution = concurrent_tool_execution

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

        if self.concurrent_tool_execution:
            parts.append("**PARALLEL TOOL EXECUTION ENABLED**")
            parts.append("- Multiple tool calls in your response will execute SIMULTANEOUSLY, not sequentially")
            parts.append("- Do NOT call dependent tools together in the same response:")
            parts.append("  - BAD: creating a directory + writing a file into it (directory may not exist yet)")
            parts.append("  - BAD: starting a server + curling it in the same response (server not ready)")
            parts.append("- Each tool call should be independent and not rely on another tool's output")
            parts.append("- If you need sequential execution, make separate responses for each step")
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
        agent_mapping: Optional[Dict[str, str]] = None,
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
        self.agent_mapping = agent_mapping  # Optional: from coordination_tracker.get_reverse_agent_mapping()

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
                # Use provided mapping or create from agent_answers keys (legacy behavior)
                if self.agent_mapping:
                    # Filter to only agents with answers, maintain global numbering
                    agent_mapping = {aid: self.agent_mapping[aid] for aid in self.agent_answers.keys() if aid in self.agent_mapping}
                else:
                    agent_mapping = {}
                    for i, agent_id in enumerate(sorted(self.agent_answers.keys()), 1):
                        agent_mapping[agent_id] = f"agent{i}"

                workspace_tree += "   Available agent workspaces:\n"
                # Sort by anon ID to ensure consistent display order
                agent_items = sorted(agent_mapping.items(), key=lambda x: x[1])
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
        use_two_tier_workspace: Whether two-tier workspace (scratch/deliverable) is enabled
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
        use_two_tier_workspace: bool = False,
    ):
        super().__init__(
            title="Filesystem & Workspace",
            priority=Priority.HIGH,
            xml_tag="filesystem",
        )

        # Create subsections with appropriate priorities
        self.subsections = [
            WorkspaceStructureSection(workspace_path, context_paths, use_two_tier_workspace=use_two_tier_workspace),
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
2. **Create your task plan EARLY** - Use the task plan tool BEFORE executing file operations or major
   actions
3. **Execute tasks** - Work through your plan systematically
4. **Update as you go** - Use the **add_task** tool to capture new requirements you discover

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
- **create_task_plan** - Create a plan with tasks and dependencies
- **get_ready_tasks** - Get tasks ready to start (dependencies satisfied)
- **get_blocked_tasks** - See what's waiting on dependencies
- **update_task_status** - Mark progress (pending/in_progress/completed)
- **add_task** - Add new tasks (priority: low/medium/high)
- **get_task_plan** - View your complete task plan
- **edit_task** - Update task descriptions
- **delete_task** - Remove tasks no longer needed

**Reading Tool Responses:**
Tool responses may include important reminders and guidance (e.g., when completing high-priority tasks,
you'll receive reminders to save learnings to memory). Always read tool response messages carefully.

**Recommended workflow:**
1. **Create your task plan** with tasks like:
   - `{"id": "research", "description": "Research OAuth providers"}`
   - `{"id": "design", "description": "Design auth flow", "depends_on": ["research"]}`
   - `{"id": "implement", "description": "Implement endpoints", "depends_on": ["design"]}`
2. **Update task status** as you work: set task_id="research", status="in_progress", then "completed"
3. **Add tasks** as you discover new requirements: description="Write integration tests", depends_on=["implement"]
4. **Check ready tasks** to see what's unblocked next

**Dependency formats:**
Tasks support two dependency styles:
- **By index** (0-based): `{"description": "Task 2", "depends_on": [0]}` — depends on the first task
- **By ID** (recommended): `{"id": "api", "description": "Build API", "depends_on": ["auth"]}` — depends on task with id "auth"

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
        vote_only: If True, agent has reached max answers and can only vote (no new_answer)
    """

    def __init__(
        self,
        voting_sensitivity: str = "lenient",
        answer_novelty_requirement: str = "lenient",
        vote_only: bool = False,
    ):
        super().__init__(
            title="MassGen Coordination",
            priority=2,  # After agent_identity(1), before core_behaviors(3)
            xml_tag="massgen_coordination",
        )
        self.voting_sensitivity = voting_sensitivity
        self.answer_novelty_requirement = answer_novelty_requirement
        self.vote_only = vote_only

    def build_content(self) -> str:
        import time

        # Vote-only mode: agent has exhausted their answer limit
        if self.vote_only:
            return f"""You are evaluating existing solutions to determine the best answer.

You have provided your maximum number of new answers. Now you MUST vote for the best existing answer.

Analyze the existing answers carefully, then call the `vote` tool to select the best one.

Note: All your other tools are still available to help you evaluate answers. The only restriction is that `vote` is your only workflow tool - you cannot submit new answers.

*Note*: The CURRENT TIME is **{time.strftime("%Y-%m-%d %H:%M:%S")}**."""

        # Determine evaluation criteria based on voting sensitivity
        if self.voting_sensitivity == "strict":
            evaluation_section = """Critically examine existing answers for flaws (be skeptical, not charitable),
verify claims by checking actual files/outputs, and consider if you can build on or combine the best elements.

Does the best CURRENT ANSWER address the ORIGINAL MESSAGE exceptionally well? Consider:
- Is it comprehensive, addressing ALL aspects and edge cases?
- Is it technically accurate and well-reasoned?
- Does it provide clear explanations and proper justification?
- Is it complete with no significant gaps or weaknesses?
- Could it serve as a reference-quality solution?

**Before voting, ask: Can I CREATE A BETTER ANSWER by:**
- Combining strengths from multiple answers (e.g., Agent 1's visuals + Agent 2's content)?
- Fixing errors or gaps you identified in the best answer?
- Adding missing elements that would make it more complete?

If YES to any of these, produce a `new_answer` instead of voting.
Only vote if the best answer is truly excellent AND you cannot improve it."""
        elif self.voting_sensitivity == "balanced":
            evaluation_section = """Critically examine existing answers for flaws,
verify claims by checking actual files/outputs, and consider if you can build on or combine approaches.

Does the best CURRENT ANSWER address the ORIGINAL MESSAGE well? Consider:
- Is it comprehensive, accurate, and complete?
- Could it be meaningfully improved, refined, or expanded?
- Are there weaknesses, gaps, or better approaches?

**Before voting, ask: Can I CREATE A BETTER ANSWER by:**
- Combining strengths from multiple answers (e.g., one agent's structure + another's execution)?
- Fixing errors or gaps you identified?
- Adding missing elements?

If YES, produce a `new_answer`. Only vote if you genuinely cannot add meaningful value."""
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


class SubagentSection(SystemPromptSection):
    """
    Subagent delegation guidance for spawning independent agent instances.

    Provides instructions on when and how to use subagents for task delegation,
    parallel execution, and context isolation.

    Args:
        workspace_path: Path to the agent's workspace (for subagent workspace location)
        max_concurrent: Maximum concurrent subagents allowed
    """

    def __init__(self, workspace_path: str, max_concurrent: int = 3):
        super().__init__(
            title="Subagent Delegation",
            priority=Priority.MEDIUM,
            xml_tag="subagent_delegation",
        )
        self.workspace_path = workspace_path
        self.max_concurrent = max_concurrent

    def build_content(self) -> str:
        return f"""
# Subagent Delegation

You can spawn **subagents** to execute tasks with fresh context and isolated workspaces.

## When to Use Subagents

**USING TASK DEPENDENCIES TO IDENTIFY SUBAGENT CANDIDATES:**
When you create a task plan, tasks with the SAME dependencies (or no dependencies) can potentially run in parallel via subagents. Look at your plan:
- Tasks that share dependencies → candidates for parallel subagent execution
- Tasks that depend on each other → must be sequential (do NOT subagent)
- Simple/quick tasks → do yourself (subagent overhead not worth it)

Example task plan analysis:
```
Task A: Research biography (no deps)        ← Can parallelize
Task B: Research discography (no deps)      ← Can parallelize
Task C: Research quotes (no deps)           ← Can parallelize
Task D: Build website (deps: A, B, C)       ← Sequential, do yourself after A/B/C
```
→ Spawn subagents for A, B, C simultaneously. Wait for results. Then do D yourself.

**IDEAL USE CASES:**
- **Research and exploration** - gathering information, searching, analyzing sources
- **Parallel data collection** - multiple independent lookups that can run simultaneously
- Complex subtasks that benefit from fresh context (avoid context pollution)
- Experimental operations you want isolated from your main workspace

**SUBAGENT RELIABILITY:**
Subagents are useful helpers but have limitations:
- They run with simpler configs and may be less capable than you
- Their outputs are **raw materials** - expect to review, refine, and fix their work
- Don't blindly trust subagent results - verify and integrate thoughtfully
- If a subagent produces something broken or incomplete, **you fix it** rather than reporting failure

**AVOID SUBAGENTS FOR:**
- Simple, quick operations you can do directly (overhead not worth it)
- Tasks requiring back-and-forth coordination (high overhead)
- Operations that need to modify your main workspace directly
- Sequential tasks that depend on other task outputs
- High-stakes deliverables that need careful quality control (do these yourself)

## How Subagents Work

1. **Isolated Workspace**: Each subagent gets its own workspace
   - You can READ files from subagent workspaces
   - You CANNOT write directly to subagent workspaces
2. **Fresh Context**: Subagents start with a clean slate (just the task you provide)
3. **Context Files**: Pass `context_files` to give the subagent READ-ONLY access to files
4. **No Nesting**: Subagents cannot spawn their own subagents
5. **No Human Broadcast**: Subagents cannot ask the human or request human input

## Waiting for Subagents (CRITICAL)

**DO NOT submit your answer until ALL subagents have returned results.**

When you spawn subagents:
1. **Wait for the tool to return** - `spawn_subagents` blocks until ALL tasks complete
2. **Do NOT say "I will now run subagents"** and submit an answer - wait for actual results first
3. **Only after receiving results** should you integrate outputs and submit your answer

**BAD**: "I spawned 5 subagents. I will now wait for them and report back." (submitting answer before results)
**GOOD**: Wait for spawn tool to return → read results → integrate → then submit answer with completed work

## Integrating Subagent Results (MANDATORY)

**YOU MUST INTEGRATE SUBAGENT OUTPUTS.** Subagents are helpers - YOU are responsible for the final deliverable.

After subagents complete (or timeout):
1. **Read each subagent's answer** to get the file paths they created
2. **Read those files** from the paths listed in the answer
3. **Write integrated files to YOUR workspace** - combine, merge, and organize the content
4. **If a subagent timed out**: Check its workspace anyway - it may have created partial work you can use. Complete any remaining work yourself.
5. **Your final answer**: Describe the COMPLETED work in your workspace, not what subagents did

**Handling timeouts/failures - YOU MUST CHECK WORKSPACES AND LOGS:**
When a subagent times out or fails, the result includes both `workspace` and `log_path`. You MUST:
1. **Check the workspace** (e.g., `/path/to/subagents/bio/workspace`) for partial work
2. **Check the log_path** (if provided) for debugging info - contains `full_logs/` with conversation history
3. **List files in both directories** to see what was created before failure
4. **Read and use any partial work** - even a half-finished file is better than nothing
5. **Complete the remaining work yourself** - don't just report the timeout

**DO NOT:**
- ❌ Submit answer before subagents finish
- ❌ Say "I will run subagents and report back" as your answer
- ❌ List what subagents produced and ask "what do you want next?"
- ❌ Leave files scattered in subagent workspaces
- ❌ Report subagent failures without completing the work yourself
- ❌ Provide "next steps" menus (A/B/C options) instead of finished work

**DO:**
- ✅ Wait for all subagent results before submitting answer
- ✅ Read subagent output files and write them to YOUR workspace
- ✅ If building a website: create the actual HTML/CSS/content files in your workspace
- ✅ If subagent timed out: check for partial work, use it, complete the rest
- ✅ Final answer: "I created X, Y, Z in my workspace" with the actual files present

## Retrieving Files from Subagents

When a subagent creates files you need:
1. **Check the answer**: The subagent lists relevant file paths in its answer
2. **Read the files**: Read from the paths in the answer
3. **Copy to your workspace**: Save files you need to your workspace

**IMPORTANT**: Only copy files you actually need. Context isolation is a key feature - you don't need every file the subagent created, just the relevant outputs.

## The spawn_subagents Tool

**CRITICAL: Tasks run in PARALLEL (simultaneously), NOT sequentially!**

All subagents start at the same time and cannot see each other's output. Design tasks that are INDEPENDENT:
- ✅ GOOD: "Research biography" + "Research discography" + "Research songs" (independent research)
- ❌ BAD: "Research content" + "Build site using researched content" (task 2 can't access task 1's output!)

**REQUIREMENTS:**
1. **Maximum {self.max_concurrent} tasks per call** - requests for more will error
2. **`CONTEXT.md` in workspace is REQUIRED** - subagents need to know the project/goal
3. **Each task dict must have `"task"` field** (not "description" or "id")

```python
# CORRECT: Independent parallel tasks (each can complete without the others)
spawn_subagents(
    tasks=[
        {{"task": "Research and write Bob Dylan biography to bio.md", "subagent_id": "bio"}},
        {{"task": "Create discography table in discography.md", "subagent_id": "discog"}},
        {{"task": "List 20 famous songs with years in songs.md", "subagent_id": "songs"}}
    ],
    async_=False,  # True if run asynchronously (you check later), False to block until done
    refine=False,  # True to allow subagents to refine their answers (more expensive and slower but better quality)
)

# WRONG - DO NOT DO THIS (task 2 depends on task 1's output):
# spawn_subagents(tasks=[
#     {{"task": "Research all content"}},
#     {{"task": "Build website using the researched content"}}  # CAN'T ACCESS TASK 1!
# ])
```

**async_ parameter:**
- `async_=True`: Spawn in background, continue working, results injected later via broadcast. Use when you can do useful work while waiting or user requests background execution.
- `async_=False` (default): Wait for results before proceeding. Use when you need outputs to complete any other work.

**refine parameter:**
- `refine=True` (default): Multi-round refinement with voting. Higher quality, slower, more expensive. Use for complex analysis.
- `refine=False`: Single-pass execution. Faster, cheaper. Use for simple lookups/lists.

## Available Tools

- `spawn_subagents(tasks, async_?, refine?)` -- Max {self.max_concurrent} parallel tasks.
- `list_subagents()` - List all spawned subagents with status
- `get_subagent_result(subagent_id)` - Get result from a completed subagent
- `check_subagent_status(subagent_id)` - Check status of a subagent

## Result Format

```json
{{
    "success": true,
    "operation": "spawn_subagents",
    "results": [
        {{
            "subagent_id": "research_oauth",
            "status": "completed",  // or "completed_but_timeout", "partial", "timeout", "error"
            "workspace": "{self.workspace_path}/subagents/research_oauth/workspace",
            "answer": "The subagent's answer with file paths...",
            "execution_time_seconds": 45.2,
            "completion_percentage": 100,  // Progress when timeout occurred (0-100)
            "token_usage": {{"input_tokens": 1000, "output_tokens": 500}}
        }}
    ],
    "summary": {{"total": 1, "completed": 1, "failed": 0, "timeout": 0}}
}}
```

**Status values:**
- `completed`: Normal successful completion
- `completed_but_timeout`: Timed out but answer was recovered (use it!)
- `partial`: Some work done, check workspace for partial files
- `timeout`: No recoverable work, but workspace still accessible
- `error`: Failed with error

## Workspace Structure

```
{self.workspace_path}/
├── ... (your files)
└── subagents/
    ├── _registry.json    # Subagent tracking
    ├── sub_abc123/
    │   ├── workspace/    # Subagent's files (READ-ONLY to you)
    │   └── _metadata.json
    └── sub_def456/
        ├── workspace/
        └── _metadata.json
```
"""


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
                        "- Call `ask_others(questions=[...])` with structured questions (PREFERRED)",
                        "- The tool blocks and waits for the human's response",
                        "- Returns the human's selections/responses when ready",
                        "- You can then continue with your task",
                    ],
                )
            else:
                lines.extend(
                    [
                        "- Call `ask_others(questions=[...])` with structured questions (PREFERRED)",
                        "- The tool blocks and waits for responses from other agents",
                        "- Returns all responses immediately when ready",
                        "- You can then continue with your task",
                    ],
                )
        else:
            lines.extend(
                [
                    "- Call `ask_others(questions=[...], wait=False)` to send without waiting",
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
                "- **Limit to 5-7 questions max per call** - too many questions overwhelms the responder",
                "- For each question, **provide 2-5 predefined options** when possible",
                "",
                "**PREFERRED: Use structured questions with the `questions` parameter:**",
                "Structured questions provide a better UX with clear options. Use them for most questions.",
                "",
                "Example - single structured question:",
                "```json",
                "ask_others(questions=[{",
                '  "text": "Which rendering approach should I use for product pages?",',
                '  "options": [',
                '    {"id": "ssr", "label": "SSR", "description": "Server-side rendering"},',
                '    {"id": "ssg", "label": "SSG", "description": "Static site generation"},',
                '    {"id": "isr", "label": "ISR", "description": "Incremental static regeneration"}',
                "  ],",
                '  "multiSelect": false,',
                '  "allowOther": true',
                "}])",
                "```",
                "",
                "Example - multiple questions in one call:",
                "```json",
                "ask_others(questions=[",
                "  {",
                '    "text": "Which frontend framework?",',
                '    "options": [',
                '      {"id": "react", "label": "React"},',
                '      {"id": "vue", "label": "Vue"},',
                '      {"id": "svelte", "label": "Svelte"}',
                "    ]",
                "  },",
                "  {",
                '    "text": "Which databases do you use?",',
                '    "options": [',
                '      {"id": "postgres", "label": "PostgreSQL"},',
                '      {"id": "mysql", "label": "MySQL"},',
                '      {"id": "mongodb", "label": "MongoDB"}',
                "    ],",
                '    "multiSelect": true',
                "  }",
                "])",
                "```",
                "",
                "**FALLBACK: Use simple text for truly open-ended questions:**",
                'Only use `ask_others(question="...")` when predefined options don\'t make sense:',
                '- "What specific challenges have you encountered with this codebase?"',
                '- "Describe your ideal workflow for this feature."',
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

    When plan_context is provided (from tasks/plan.json), adds guidance to
    reference the plan and capture task-specific learnings.
    """

    def __init__(self, plan_context: dict | None = None):
        super().__init__(
            title="Evolving Skills",
            priority=6,  # After core_behaviors(4), task_planning(5)
            xml_tag="evolving_skills",
        )
        self.plan_context = plan_context

    def build_content(self) -> str:
        base_content = """## Evolving Skills

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

## Verification & Improvement
How to verify and iterate on output (output-first approach):
- For code: Run it, fix issues, rerun until working correctly
- For websites: Screenshot and view, adjust layout/styling, re-screenshot until polished
- For files: Open and inspect, refine content, re-check until quality meets bar
- For data: Validate format/values, fix accuracy issues, re-validate until correct

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
3. **BEFORE answering**: Verify outputs work (run code, view visuals, check files)
4. **AFTER completing work**: Update SKILL.md with Learnings section

### Key Principles

1. **Be specific** - Workflow steps should be actionable, not vague
2. **Document tools upfront** - Plan scripts before writing them
3. **Test like a user** - Verify artifacts through interaction, not just observation (click buttons, play games, navigate pages, run with edge cases, etc)
4. **Update with learnings** - The skill improves through use
5. **Keep scripts reusable** - Design tools to work in similar future tasks"""

        # Append plan-specific guidance if plan context is available
        if self.plan_context:
            task_count = len(self.plan_context.get("tasks", []))
            base_content += f"""

### Plan Integration

You have an active task plan with **{task_count} tasks** in `tasks/plan.json`.

When creating your evolving skill:
1. **Reference the plan**: Add `Task plan: tasks/plan.json ({task_count} tasks)` in your Overview section
2. **Focus on learnings**: The plan has task structure - your skill should capture HOW to execute and what you LEARNED
3. **Map insights to tasks**: In your Learnings section, note which task IDs your insights apply to (e.g., "T003: Found that X works better than Y")
4. **Keep minimal**: Don't duplicate the entire plan in your skill - focus on execution details and improvements
"""

        return base_content


class OutputFirstVerificationSection(SystemPromptSection):
    """
    Core principle: verify outcomes and iterate improvements.

    HIGH priority - fundamental operating principle for quality work.
    This is not just about checking if something works (for voting),
    but actively improving outputs through iteration.
    Always included regardless of tools available.
    """

    def __init__(self):
        super().__init__(
            title="Output-First Iteration",
            priority=Priority.HIGH,
            xml_tag="output_first_iteration",
        )

    def build_content(self) -> str:
        return """## Output-First Iteration

**Core Principle: Experience your work exactly as a user would - through dynamic interaction, not just static observation.**

This is an **improvement loop**, not just a verification step:
1. Run/view output → 2. **Interact as a user would** → 3. Identify gaps or issues → 4. Fix and enhance → 5. Re-run and re-interact → 6. Repeat until excellent

### Dynamic Verification: Think Like a User

Static screenshots or a single code run are often not sufficient. Users don't just look at artifacts - they interact with them:

| Artifact Type | Static Check (incomplete) | Dynamic Check (required) |
|--------------|---------------------------|--------------------------|
| Website/App | Screenshot looks good | Click all buttons, navigate all pages, test forms, verify links work |
| Game | Screenshot shows UI | Play the game - test controls, scoring, game over states, restart |
| Interactive tool | Interface renders | Use every feature, test edge cases, verify all interactions |
| Script/Code | No errors on run | Test with various inputs, edge cases, invalid data |
| API | Single call works | Test all endpoints, error states, authentication flows |
| Data pipeline | Output exists | Validate accuracy, test with edge case inputs |

**For any artifact not listed above:** Apply the same principle - ask "How will a user actually USE this?" and test that way.
The goal is always to verify the complete user experience, not just surface appearance.

### The User Experience Test

Before considering any interactive artifact complete, ask:
1. **What will users click/interact with?** → Do it. Does it work?
2. **What will users type/input?** → Try it. Does it respond correctly?
3. **What paths will users take?** → Navigate them all. Any broken routes?
4. **How will users break it?** → Try to break it. Does it handle errors gracefully?

### Why this matters:
- A website screenshot can look perfect while half the links are broken
- A game screenshot shows nothing about whether gameplay works
- An interactive tool may render but crash on first click
- Any artifact may LOOK correct but FAIL when actually used

**The goal is to verify INTERACTION OUTCOMES, not just visual appearance.**

### Apply at every stage:
1. **During development** - short loops: interact, improve, re-interact
2. **Before answering** - full interaction test on the actual output
3. **During evaluation** - judge by interaction results, improve if gaps found

### Iteration examples:
- **Websites**: Visit all pages → click every nav link → found 2 broken links → fix routes → re-test all links → confirm working
- **Games**: Play game → controls unresponsive → fix input handling → replay → confirm smooth gameplay
- **Interactive tools**: Use all features → export fails on large files → add chunking → re-test export → confirm fixed
- **Code**: Run with test inputs → crashes on empty array → add validation → rerun with edge cases → confirm robust

### Finalization:
- Use `new_answer` when you produced work or iterated improvements based on **interaction testing**.
- Use `vote` only when an existing answer already meets the bar after **testing as a user would**."""


class MultimodalToolsSection(SystemPromptSection):
    """
    Guidance for using read_media to verify visual artifacts.

    MEDIUM priority - extends output-first verification to visual content.
    Only included when multimodal tools are enabled.
    """

    def __init__(self):
        super().__init__(
            title="Visual Verification Tools",
            priority=Priority.MEDIUM,
            xml_tag="visual_verification_tools",
        )

    def build_content(self) -> str:
        return """## Visual & Interactive Verification

Use `read_media` for visual analysis, but remember: **interact first, screenshot second.**

### Key Principle
Screenshots verify appearance. Interaction verifies functionality. Do both:
1. **Interact** with the artifact as a user would (click, navigate, play, input)
2. **Screenshot** key states during/after interaction
3. **Analyze** with read_media using **critical prompts**

### CRITICAL: Be Skeptical, Not Charitable
When evaluating your own or others' work, use prompts that look for **flaws**:

**BAD prompts (too charitable):**
- "Does the layout look correct?"
- "Describe this screenshot"

**GOOD prompts (skeptical):**
- "What flaws, issues, or missing elements do you see? Be critical."
- "What would a demanding user complain about?"
- "Does this fully meet the requirements, or are there gaps?"

**Supported formats:**
- Images: png, jpg, jpeg, gif, webp, bmp
- Audio: mp3, wav, m4a, ogg, flac, aac
- Video: mp4, mov, avi, mkv, webm

A beautiful screenshot means nothing if buttons don't work. Test functionality, then verify visuals with a critical eye."""


class TaskContextSection(SystemPromptSection):
    """
    Instructions for creating CONTEXT.md before using multimodal tools or subagents.

    This ensures external API calls (to GPT-4.1, Gemini, etc.) have context about
    what the user is trying to accomplish, preventing hallucinations about
    task-specific terminology.

    MEDIUM priority - included when multimodal tools or subagents are enabled.
    """

    def __init__(self):
        super().__init__(
            title="Task Context",
            priority=Priority.MEDIUM,
            xml_tag="task_context",
        )

    def build_content(self) -> str:
        return """## Task Context for Tools and Subagents

**REQUIRED**: Before spawning subagents or using multimodal tools (read_media, generate_media),
you MUST create a `CONTEXT.md` file in your workspace with task context.

### Why This Matters
External APIs (like GPT-4.1 for image analysis) have no idea what you're working on.
Without context, they will hallucinate - for example, interpreting "MassGen" as
"Massachusetts General Hospital" instead of "multi-agent AI system".

### What to Include in CONTEXT.md
Write a brief file explaining:
- **What we're building/doing** - the core task in 1-2 sentences
- **Key terminology** - project-specific terms that could be misinterpreted
- **Visual/brand details** - style, colors, aesthetic if relevant
- **Any other context** tools or subagents need to understand the task

### Example CONTEXT.md
```markdown
# Task Context

Building a marketing website for MassGen - a multi-agent AI orchestration system
that coordinates parallel AI agents through voting and consensus.

## Key Terms
- MassGen: Multi-agent AI coordination system (NOT Massachusetts General Hospital)
- Agents: Individual AI instances that collaborate
- Voting: Consensus mechanism where agents vote on best solutions

## Visual Style
- Dark theme with terminal aesthetic
- Primary color: indigo (#4F46E5)
- Modern, technical but approachable tone
```

### When to Create It
Create CONTEXT.md **before** your first use of:
- `spawn_subagents` - subagents will inherit this context
- `read_media` - image/audio/video analysis will use this context
- `generate_media` - image/video/audio generation will use this context

The file will be read automatically and injected into external API calls."""


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
