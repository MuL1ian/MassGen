---
name: extraframework-agents
description: Integration tools for external agent frameworks (LangGraph, AG2, AgentScope, etc.)
category: agent-integration
requires_api_keys: [OPENAI_API_KEY]
tasks:
  - "Run LangGraph state graph workflows as MassGen tools"
  - "Execute AG2 (AutoGen) multi-agent conversations"
  - "Use AgentScope agents within MassGen"
  - "Leverage OpenAI Assistants API"
  - "Integrate SmolagentHF workflows"
  - "Demonstrate framework interoperability"
keywords: [langgraph, autogen, ag2, agentscope, openai-assistants, smolagent, framework-integration, multi-agent, interoperability]
---

# Extra-Framework Agents

Integration layer for wrapping external agent frameworks (LangGraph, AG2, AgentScope, OpenAI Assistants, SmolagentHF) as MassGen custom tools.

## Purpose

Demonstrate framework interoperability by:
- Running other agent frameworks within MassGen
- Leveraging specialized capabilities from different frameworks
- Creating hybrid multi-framework solutions
- Using best tool for each task regardless of framework
- Showing how to wrap external agent systems as tools

**Key insight:** Any agent framework can be wrapped as a MassGen tool, enabling you to mix and match approaches.

## When to Use This Tool

**Use extra-framework agents when:**
- Need specific capabilities from another framework
- Want to leverage existing agent implementations
- Comparing different framework approaches
- Building hybrid multi-framework systems
- Demonstrating interoperability patterns

**Do NOT use for:**
- Simple tasks (use native MassGen tools)
- Production critical paths (adds complexity)
- Performance-sensitive operations (adds overhead)

## Available Frameworks

### LangGraph Integration

#### `run_langgraph_lesson_planner_agent(messages: List[Dict], api_key: str) -> AsyncGenerator`

Runs a LangGraph state graph workflow for lesson planning.

**Example:**
```python
from massgen.tool._extraframework_agents import langgraph_lesson_planner_tool

messages = [{"role": "user", "content": "Create a 4th grade science lesson on photosynthesis"}]
result = await langgraph_lesson_planner_tool.run_langgraph_lesson_planner_tool(
    messages=messages,
    api_key=os.getenv("OPENAI_API_KEY")
)
# Returns: Structured lesson plan from LangGraph workflow
```

**LangGraph features:**
- State graph architecture
- Multiple specialized nodes (curriculum, planner, reviewer)
- Structured workflow with checkpoints
- Message-based state management

**Use when:**
- Need complex multi-step workflows with state
- Want structured agent pipelines
- Require workflow visualization

### AG2 (AutoGen) Integration

#### `run_ag2_lesson_planner_agent(messages: List[Dict], api_key: str) -> AsyncGenerator`

Runs AG2 multi-agent conversation for lesson planning.

**Example:**
```python
from massgen.tool._extraframework_agents import ag2_lesson_planner_tool

messages = [{"role": "user", "content": "Create a history lesson on the Civil War"}]
result = await ag2_lesson_planner_tool.run_ag2_lesson_planner_tool(
    messages=messages,
    api_key=os.getenv("OPENAI_API_KEY")
)
# Returns: Lesson plan from AG2 agent collaboration
```

**AG2 features:**
- Multi-agent conversations
- Agent-to-agent communication
- Consensus building
- AutoGen compatibility

**Use when:**
- Need multiple agents collaborating
- Want conversational agent interactions
- Require debate/review patterns

### AgentScope Integration

#### `run_agentscope_lesson_planner_agent(messages: List[Dict], api_key: str) -> AsyncGenerator`

Runs AgentScope workflow for lesson planning.

**Example:**
```python
from massgen.tool._extraframework_agents import agentscope_lesson_planner_tool

messages = [{"role": "user", "content": "Create a math lesson on fractions"}]
result = await agentscope_lesson_planner_tool.run_agentscope_lesson_planner_tool(
    messages=messages,
    api_key=os.getenv("OPENAI_API_KEY")
)
# Returns: Lesson plan from AgentScope
```

**AgentScope features:**
- Pipeline-based workflows
- Message passing between agents
- Flexible agent composition

**Use when:**
- Need simple pipeline architectures
- Want lightweight agent composition
- Require message-based coordination

### OpenAI Assistants Integration

#### `run_openai_assistant_lesson_planner_agent(messages: List[Dict], api_key: str) -> AsyncGenerator`

Uses OpenAI Assistants API for lesson planning.

**Example:**
```python
from massgen.tool._extraframework_agents import openai_assistant_lesson_planner_tool

messages = [{"role": "user", "content": "Create an art lesson on impressionism"}]
result = await openai_assistant_lesson_planner_tool.run_openai_assistant_lesson_planner_tool(
    messages=messages,
    api_key=os.getenv("OPENAI_API_KEY")
)
# Returns: Lesson plan from OpenAI Assistant
```

**OpenAI Assistants features:**
- Hosted assistant instances
- Built-in tools (code interpreter, retrieval)
- Thread-based conversations
- Persistent state

**Use when:**
- Want hosted assistant capabilities
- Need built-in OpenAI tools
- Require persistent conversation threads

### SmolagentHF Integration

#### `run_smolagent_lesson_planner_agent(messages: List[Dict], api_key: str) -> AsyncGenerator`

Uses Hugging Face's Smolagent for lesson planning.

**Example:**
```python
from massgen.tool._extraframework_agents import smolagent_lesson_planner_tool

messages = [{"role": "user", "content": "Create a coding lesson on Python loops"}]
result = await smolagent_lesson_planner_tool.run_smolagent_lesson_planner_tool(
    messages=messages,
    api_key=os.getenv("OPENAI_API_KEY")
)
# Returns: Lesson plan from Smolagent
```

**Smolagent features:**
- Lightweight agent framework
- HuggingFace ecosystem integration
- Simple tool usage patterns

**Use when:**
- Need HuggingFace model integration
- Want lightweight agent framework
- Require simple tool-using agents

## Common Pattern: Lesson Planning

All examples implement a **lesson planner** to demonstrate:
- How each framework approaches the same problem
- Comparative architecture patterns
- Interoperability across frameworks

**Lesson planner workflow:**
1. Analyze topic and grade level
2. Identify curriculum standards
3. Create lesson structure
4. Add activities and assessments
5. Review and refine plan

Each framework implements this differently, showing their unique strengths.

## Configuration

### Prerequisites

**Install required frameworks:**
```bash
# LangGraph
pip install langgraph langchain-openai

# AG2 (AutoGen)
pip install ag2

# AgentScope
pip install agentscope

# OpenAI Assistants (included in openai package)
pip install openai

# Smolagent
pip install smolagent
```

**Set API key:**
```bash
export OPENAI_API_KEY="your-api-key"
```

### YAML Config

Enable extra-framework agents in your config:

```yaml
custom_tools_path: "massgen/tool/_extraframework_agents"

# Or specify individual tools
tools:
  - name: run_langgraph_lesson_planner_tool
  - name: run_ag2_lesson_planner_tool
```

## Integration Pattern

**How to wrap any framework as a MassGen tool:**

1. **Define async generator function:**
```python
async def run_framework_agent(
    messages: List[Dict[str, Any]],
    api_key: str,
) -> AsyncGenerator[Dict[str, Any], None]:
    # Extract user prompt from messages
    user_prompt = extract_prompt(messages)

    # Run framework-specific logic
    result = await framework.run(user_prompt)

    # Yield progress updates
    yield {"type": "log", "content": "Processing..."}

    # Yield final result
    yield {"type": "output", "content": result}
```

2. **Wrap as MassGen tool:**
```python
from massgen.tool import context_params
from massgen.tool._result import ExecutionResult, TextContent

@context_params(["messages", "api_key"])
async def framework_tool(
    messages: List[Dict],
    api_key: str,
) -> ExecutionResult:
    outputs = []
    async for chunk in run_framework_agent(messages, api_key):
        if chunk["type"] == "output":
            outputs.append(chunk["content"])

    return ExecutionResult(
        output_blocks=[TextContent(data="\n".join(outputs))]
    )
```

3. **Use in MassGen:**
```yaml
tools:
  - name: framework_tool
```

## Comparison of Frameworks

| Framework | Strengths | Best For |
|-----------|-----------|----------|
| **LangGraph** | State graphs, visualization | Complex workflows, pipelines |
| **AG2** | Multi-agent, conversations | Collaboration, debate |
| **AgentScope** | Lightweight, flexible | Simple pipelines, message passing |
| **OpenAI Assistants** | Hosted, built-in tools | Quick prototypes, persistence |
| **Smolagent** | HF integration, simple | HF models, lightweight tasks |

## Limitations

- **Dependency bloat**: Each framework adds dependencies
- **Version conflicts**: Frameworks may have conflicting dependencies
- **Performance overhead**: Extra layer of abstraction
- **Complexity**: Harder to debug multi-framework systems
- **Learning curve**: Must understand multiple frameworks
- **API costs**: Running multiple agents increases costs

## Best Practices

**1. Use native tools when possible:**
```python
# Prefer native MassGen tools for simple tasks
# Use extra-framework agents for specialized capabilities
```

**2. Isolate framework dependencies:**
```python
# Optional imports to avoid loading all frameworks
try:
    from langgraph import StateGraph
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
```

**3. Consistent message format:**
```python
# Standardize messages across frameworks
messages = [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
]
```

**4. Error handling:**
```python
try:
    result = await run_framework_agent(messages, api_key)
except Exception as e:
    return ExecutionResult(
        output_blocks=[TextContent(data=f"Framework error: {e}")]
    )
```

**5. Document framework choice:**
```python
# Explain why using specific framework
"""
Using LangGraph for this task because:
- Need complex state management
- Benefit from graph visualization
- Require checkpointing
"""
```

## Common Use Cases

1. **Compare approaches**: Run same task through multiple frameworks
2. **Best-of-breed**: Use best framework for each sub-task
3. **Migration testing**: Compare results when migrating frameworks
4. **Specialized capabilities**: Access unique framework features
5. **Research**: Study different agent architectures

## Example: Multi-Framework Workflow

```python
# Use different framework for each step

# Step 1: LangGraph for complex planning
plan = await run_langgraph_lesson_planner_tool(messages, api_key)

# Step 2: AG2 for collaborative review
review = await run_ag2_lesson_planner_tool(
    [{"role": "user", "content": f"Review this plan: {plan}"}],
    api_key
)

# Step 3: Native MassGen tool for final formatting
formatted = await format_document(review)
```

This demonstrates true framework interoperability: choosing the best tool for each job.
