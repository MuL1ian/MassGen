# Change: Add Task Planning Mode CLI (`--plan`)

## Why

Users want to leverage MassGen's multi-agent coordination purely for task planning. Per Anthropic's research on effective harnesses for long-running agents, comprehensive feature lists (200+ features with descriptions and pass/fail status) dramatically improve agent outcomes. This feature enables:

1. **Standalone planning tool**: `uv run massgen --plan "task"` outputs structured feature lists
2. **Interactive planning**: Agents ask user clarifying questions via `ask_others` (like Claude Code's AskUserQuestion)
3. **Scalable depth**: `--plan-depth` controls granularity from 5-10 tasks (shallow) to 100-200+ (deep)

Reference: [MAS-151](https://linear.app/massgen-ai/issue/MAS-151/feature-introduce-scaling-through-task-planning)

## What Changes

### CLI
- Add `--plan` flag for task planning mode
- Add `--plan-depth shallow|medium|deep` to control plan granularity

### Configuration
- Auto-add current working directory to `context_paths` (so agents can explore codebase)
- Auto-set `broadcast="user"` (route `ask_others` to user for clarifications)
- New `plan_depth` field in CoordinationConfig

### User Prompt
- Prepend task planning instructions to user's question (not system prompt)
- Depth-specific guidance on number of features/tasks to generate
- Emphasis on interactive questioning with user

### Output
- Primary artifact: `feature_list.json` with structured features
- Supporting docs: Agent-determined based on task complexity

**NOT affected:**
- No tool blocking (unlike existing `enable_planning_mode`)
- No new coordination phases
- Normal execution - winning agent writes plan files

## Impact

- Affected specs: New `task-planning` capability
- Affected code:
  - `massgen/cli.py` - CLI arguments and prompt construction
  - `massgen/agent_config.py` - CoordinationConfig.plan_depth field
  - `massgen/config_validator.py` - Validate plan_depth values
