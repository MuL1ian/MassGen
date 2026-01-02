# Proactive (Agent-Driven) Compression Design

## Status: FUTURE / NOT IMPLEMENTED

This document captures the design for a **proactive** approach to context compression where the agent participates in summarizing its own context before truncation. This is currently **not reliably implementable** due to limitations in LLM provider APIs.

## The Problem

### Current Limitation

From `massgen/backend/_context_errors.py`:

> "Since most LLM providers only report token usage AFTER a request completes, we cannot proactively prevent context overflow. Instead, we catch errors and compress."

### Why Agent-Driven Compression Can't Work Reliably Today

1. **Token counts are only available after API calls complete**
   - We use `_last_call_input_tokens` from the *previous* turn
   - But context grows during tool execution *within* a turn
   - Reasoning tokens are hidden by many providers and cannot be counted as we go, so we are oblivious to the real token count until the end
   - By the time the next API call happens, we may already exceed the limit

2. **Token estimation is unreliable**
   - Different providers use different tokenizers (~7.5% variance observed with Gemini)
   - Tool definitions add tokens that are hard to estimate
   - Multimodal content (images) has unpredictable token costs

3. **Input caching and hidden reasoning make new API calls suboptimal**
   - One API call streaming many tool calls along the way will cache inputs resulting in many cost savings.
   - Not all information from an API call is provided to the backend, e.g., reasoning is hidden for OpenAI. So if streaming is ended and a new call is made, that call will not have the full context.

### Current Solution: Reactive Compression

We implemented reactive compression instead (see `context_compression_design.md`):
1. Catch context length errors from the API
2. Summarize older messages
3. Truncate if needed
4. Retry with compressed context

This works reliably because we handle the error **after** it happens rather than trying to predict it.

---

## Future Vision: True Proactive Compression

For agent-driven compression to work reliably, we would need:

### Option 1: Pre-flight Token Counting from Providers

If providers offered a "dry run" endpoint that returns token count without executing:

```python
# Hypothetical API
token_count = await client.messages.count_tokens(messages=messages, tools=tools)
if token_count > context_window * 0.9:
    # Trigger compression before the actual call
    pass
```

### Option 2: Streaming Token Counts

If providers streamed token usage incrementally during tool execution:

```python
async for chunk in stream:
    if chunk.type == "token_usage":
        if chunk.cumulative_tokens > threshold:
            # Pause and compress mid-stream
            pass
```

### Option 3: Client-Side Accurate Tokenization

If we had access to exact tokenizers for each provider:

```python
# Hypothetical - provider-specific tokenizers
from anthropic.tokenizer import count_tokens as claude_count
from openai.tokenizer import count_tokens as openai_count

# Pre-flight check with exact count
tokens = claude_count(messages, tools)
```

---

## Archived Implementation

The following code was developed for agent-driven compression but is not being shipped because it cannot work reliably given current API limitations.

### AgentDrivenCompressor Class

This class was designed to coordinate agent-driven compression with filesystem memory:

```python
class AgentDrivenCompressor:
    """
    Coordinates agent-driven context compression with filesystem memory.

    Instead of algorithmically removing messages, this compressor:
    1. Injects a summarization request into the conversation
    2. Waits for agent to write memories using file writing tools
    3. Detects when agent calls compression_complete MCP tool
    4. Validates that required memory files exist
    5. Falls back to algorithmic compression if agent fails
    6. Performs final truncation after summaries are saved

    States:
        idle: Normal operation, monitoring context usage
        requesting: Injected compression request, waiting for agent
        validating: Agent signaled completion, validating files
    """

    STATE_IDLE = "idle"
    STATE_REQUESTING = "requesting"
    STATE_VALIDATING = "validating"

    def __init__(
        self,
        workspace_path: Optional[Path] = None,
        fallback_compressor: Optional[ContextCompressor] = None,
        max_attempts: int = 2,
        short_term_path: str = "memory/short_term",
        long_term_path: str = "memory/long_term",
        agent_id: Optional[str] = None,
    ):
        self.workspace_path = Path(workspace_path) if workspace_path else None
        self.fallback_compressor = fallback_compressor
        self.max_attempts = max_attempts
        self.short_term_path = short_term_path
        self.long_term_path = long_term_path
        self.agent_id = agent_id or "unknown"

        # State tracking
        self.state = self.STATE_IDLE
        self.current_attempt = 0
        self.pending_usage_info: Optional[Dict[str, Any]] = None

        # Stats
        self.total_agent_compressions = 0
        self.total_fallback_compressions = 0
        self.total_attempts = 0

    def should_request_compression(self, usage_info: Dict[str, Any]) -> bool:
        """Check if compression should be requested based on usage threshold."""
        should_compress = usage_info.get("should_compress", False)
        is_idle = self.state == self.STATE_IDLE
        return should_compress and is_idle

    def build_compression_request(
        self,
        usage_info: Dict[str, Any],
        task_summary: str = "",
    ) -> Dict[str, Any]:
        """Build the compression request message to inject."""
        content = COMPRESSION_REQUEST.format(
            usage_percent=usage_info.get("usage_percent", 0),
            current_tokens=usage_info.get("current_tokens", 0),
            max_tokens=usage_info.get("max_tokens", 0),
        )

        self.state = self.STATE_REQUESTING
        self.pending_usage_info = usage_info
        self.current_attempt += 1

        return {
            "role": "user",
            "content": content,
            "_is_compression_request": True,
        }

    def validate_memory_written(self) -> Tuple[bool, List[str]]:
        """Check if agent wrote the required memories."""
        if not self.workspace_path:
            return True, []

        written_files = []
        current_time = time.time()

        # Check for required recent.md
        short_term_dir = self.workspace_path / self.short_term_path
        recent_file = short_term_dir / "recent.md"

        if recent_file.exists():
            mtime = recent_file.stat().st_mtime
            if current_time - mtime < 60:  # Written in last 60 seconds
                written_files.append(str(recent_file))

        # Also check for any new long-term memories
        long_term_dir = self.workspace_path / self.long_term_path
        if long_term_dir.exists():
            for f in long_term_dir.glob("*.md"):
                if current_time - f.stat().st_mtime < 60:
                    if str(f) not in written_files:
                        written_files.append(str(f))

        success = recent_file.exists()
        return success, written_files

    def on_compression_complete_tool_called(self) -> bool:
        """Called when compression_complete MCP tool is detected."""
        if self.state != self.STATE_REQUESTING:
            return False

        self.state = self.STATE_VALIDATING
        success, files = self.validate_memory_written()

        if success:
            self.total_agent_compressions += 1
            self._reset_state()
            return True
        else:
            if self.current_attempt >= self.max_attempts:
                self.total_fallback_compressions += 1
                self._reset_state()
                return True  # Proceed with fallback
            else:
                self.state = self.STATE_REQUESTING
                return False

    def _reset_state(self) -> None:
        """Reset state machine to idle."""
        self.state = self.STATE_IDLE
        self.current_attempt = 0
        self.pending_usage_info = None
```

### Compression Prompts

Prompts that would be injected to request agent-driven compression:

```python
COMPRESSION_REQUEST = """
[SYSTEM: Context Compression Required]

Your context window is at {usage_percent:.0%} capacity ({current_tokens:,}/{max_tokens:,} tokens).
Before continuing, you MUST save memories and signal completion.

## IMPORTANT: Preserve Task Context

Before writing your summary, read these files to ensure you preserve full context:
1. `tasks/plan.json` - Your current task plan (if exists)
2. `tasks/evolving_skill/SKILL.md` - Your workflow plan (if exists)

## Required Steps:

### 1. Write Short-Term Summary
Write a DETAILED summary to `memory/short_term/recent.md` containing:

```markdown
# Recent Conversation Summary

## Task Context
[Brief description of what you're working on]

## Current Task Plan
[Summary of your task plan from tasks/ if applicable]

## Key Progress
- [Decisions made with context and reasoning]
- [Files created/modified with full paths]
- [Important findings with specifics]

## Environment Setup
- [Packages installed: pip install X, npm install Y]
- [Directories created]
- [Any configuration changes]

## Tool Results
- [Key tool calls and their outputs]
- [Function signatures or patterns discovered]
- [Errors encountered and how they were resolved]

## Current State
- [Where you are in the workflow]
- [What has been completed vs what remains]

## Next Steps
- [Specific remaining work with details]
```

**CRITICAL**: The summary must be DETAILED ENOUGH that you can continue work after
context truncation. Vague summaries like "working on website" are NOT acceptable.

### 2. Write Long-Term Memories (if applicable)
Save any information worth preserving across sessions to `memory/long_term/[name].md`

### 3. Signal Completion
After writing memories, call the `compression_complete` tool to signal you're done.
"""

COMPRESSION_FAILED_RETRY = """
[SYSTEM: Compression Incomplete]

The required memory file was not found. Please ensure you:
1. Write the summary to `memory/short_term/recent.md`
2. Call the `compression_complete` tool

Attempt {attempt}/{max_attempts}. If you continue to fail, algorithmic compression will be used.
"""
```

### MCP Tool: compression_complete

```python
def compression_complete() -> Dict[str, Any]:
    """Signal that context compression memory writes are complete.

    Call this AFTER writing short-term and long-term memories using
    file writing tools. The system will validate that the required
    memory files exist and then truncate the conversation history.

    Returns:
        Dictionary confirming compression signal received
    """
    logger.info("Compression complete signal received from agent")

    # Check if recent.md exists (validation)
    recent_exists = False
    if _workspace_path:
        recent_file = Path(_workspace_path) / "memory" / "short_term" / "recent.md"
        if recent_file.exists():
            recent_exists = True
        else:
            logger.warning(f"Warning: {recent_file} not found")

    return {
        "success": True,
        "operation": "compression_complete",
        "message": "Compression acknowledged. Context will be truncated.",
        "recent_memory_exists": recent_exists,
    }
```

### SingleAgent Integration

```python
def set_agent_driven_compressor(
    self,
    workspace_path: str,
    fallback_compressor: Optional[Any] = None,
    max_attempts: int = 2,
    short_term_path: str = "memory/short_term",
    long_term_path: str = "memory/long_term",
    trigger_threshold: float = 0.75,
    target_ratio: float = 0.20,
) -> None:
    """
    Enable agent-driven compression with filesystem memory.

    Args:
        workspace_path: Path to agent workspace
        fallback_compressor: Optional compressor to use if agent fails
        max_attempts: Max retries before fallback
        short_term_path: Relative path for short-term memories
        long_term_path: Relative path for long-term memories
        trigger_threshold: Context usage (0.0-1.0) at which to trigger compression
        target_ratio: Target context percentage after compression
    """
    self.agent_driven_compressor = AgentDrivenCompressor(
        workspace_path=Path(workspace_path),
        fallback_compressor=fallback_compressor or self.context_compressor,
        max_attempts=max_attempts,
        short_term_path=short_term_path,
        long_term_path=long_term_path,
    )

    if self.context_monitor:
        self.context_monitor.trigger_threshold = trigger_threshold
        self.context_monitor.target_ratio = target_ratio
```

### Orchestrator Setup

```python
def _setup_agent_driven_compression(self) -> None:
    """Set up agent-driven compression for all agents with filesystem memory enabled."""

    trigger_threshold = 0.75
    target_ratio = 0.20

    if hasattr(self.config, "coordination_config"):
        coord_config = self.config.coordination_config
        if hasattr(coord_config, "compression_trigger_threshold"):
            trigger_threshold = coord_config.compression_trigger_threshold
        if hasattr(coord_config, "compression_target_ratio"):
            target_ratio = coord_config.compression_target_ratio

    for agent_id, agent in self.agents.items():
        # Get workspace path from filesystem manager
        workspace_path = None
        if hasattr(agent, "backend") and hasattr(agent.backend, "filesystem_manager"):
            if agent.backend.filesystem_manager and agent.backend.filesystem_manager.cwd:
                workspace_path = PathLib(agent.backend.filesystem_manager.cwd)

        if not workspace_path:
            continue

        # Create context monitor if needed
        if not agent.context_monitor:
            agent.context_monitor = ContextWindowMonitor(
                model_name=model_name,
                provider=provider,
                trigger_threshold=trigger_threshold,
                target_ratio=target_ratio,
            )

        # Set up agent-driven compressor
        agent.set_agent_driven_compressor(
            workspace_path=workspace_path,
            fallback_compressor=getattr(agent, "context_compressor", None),
            trigger_threshold=trigger_threshold,
            target_ratio=target_ratio,
        )
```

---

## Configuration (Not Active)

These config options were designed but are not currently functional:

```yaml
coordination:
  enable_memory_filesystem_mode: true  # Would enable agent-driven compression
  compression_trigger_threshold: 0.75  # Trigger at 75% context usage
  compression_target_ratio: 0.20       # Target 20% after compression
  enable_memory_mcp_tools: false       # Enable full memory MCP tools
```

---

## When This Becomes Viable

Revisit this design when:

1. **Anthropic/OpenAI add pre-flight token counting** - "Count tokens without executing"
2. **Streaming APIs report cumulative token usage** - Real-time token tracking
3. **Provider-specific tokenizers become available** - Accurate client-side counting
4. **Context windows become truly unlimited** - Problem goes away entirely

Until then, reactive compression (catching errors and recovering) is the reliable approach.
