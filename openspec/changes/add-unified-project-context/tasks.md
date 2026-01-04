# Tasks: Add Unified Task Context

## 1. Core Infrastructure

- [x] 1.1 Create `massgen/context/task_context.py` with `load_task_context()` function
- [x] 1.2 Add `task_context: Optional[str]` to ExecutionContext in `base_with_custom_tool_and_mcp.py`
- [x] 1.3 Load task context in `stream_with_tools()` and pass to ExecutionContext

## 2. System Prompt Integration

- [x] 2.1 Add CONTEXT.md creation instructions to `system_message_builder.py`
- [x] 2.2 Include template and examples for what to put in CONTEXT.md

## 3. Multimodal Tools - Understanding

- [x] 3.1 Update `read_media.py` to add `task_context` to @context_params
- [x] 3.2 Update `understand_image.py` to inject context into OpenAI API call
- [x] 3.3 Update `understand_audio.py` to inject context into API calls
- [x] 3.4 Update `understand_video.py` to inject context into all backend API calls
- [x] 3.5 Update `understand_file.py` to inject context into API call

## 4. Multimodal Tools - Generation

- [x] 4.1 Update `generate_media.py` to add `task_context` to @context_params
- [x] 4.2 Context injection handled in `generate_media.py` (not individual backends)
- [N/A] 4.3 `generation/_video.py` - uses prompt from GenerationConfig (context injected upstream)
- [N/A] 4.4 `generation/_audio.py` - uses prompt from GenerationConfig (context injected upstream)

## 5. Subagent Integration

- [x] 5.1 Update `_copy_context_files()` to auto-copy CONTEXT.md if it exists
- [x] 5.2 Update `_build_subagent_system_prompt()` to include context from CONTEXT.md
- [x] 5.3 Subagents are read-only (receive copied CONTEXT.md, cannot create/modify)
- [x] 5.4 Add `warning` field to SubagentResult for context truncation visibility
- [x] 5.5 Propagate context warning to all SubagentResult creation paths (success, error, timeout)

## 6. Configuration

- [N/A] 6.1 `task_context` is loaded at runtime from workspace, not passed as config
- [N/A] 6.2 No config param exclusion needed (not a YAML config param)

## 7. Testing

- [ ] 7.1 Add unit tests for `load_task_context()` function
- [ ] 7.2 Test context injection in understand_image
- [ ] 7.3 Test subagent CONTEXT.md auto-copy
