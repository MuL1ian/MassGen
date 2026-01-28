# -*- coding: utf-8 -*-
"""
Shared plan execution setup logic for CLI and TUI.

This module provides reusable functions for preparing plan execution,
ensuring both CLI (--execute-plan) and TUI execute mode use the same logic.
"""

import copy
import json
import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from .plan_storage import PlanSession

logger = logging.getLogger(__name__)


# Plan execution guidance injected into agent system messages
PLAN_EXECUTION_GUIDANCE = """
## Plan Execution Mode

You are executing a pre-approved task plan. The plan has been AUTO-LOADED into `tasks/plan.json`.

### Getting Started - Plan is Ready

Your task plan is already loaded. Use MCP planning tools to track progress:

1. **See all tasks**: `get_task_plan()` - view full plan with current status
2. **See ready tasks**: `get_ready_tasks()` - tasks with dependencies satisfied
3. **Start a task**: `update_task_status("T001", "in_progress")`
4. **Complete a task**: `update_task_status("T001", "completed", "How you completed it")`

Supporting docs from planning phase are in `planning_docs/` for reference.

### CRITICAL: Verification Workflow

**Do NOT just write code and mark tasks complete. You MUST verify your work actually runs.**

#### Task Status Flow
- `pending` → `in_progress` → `completed` → `verified`
- **completed**: Implementation is done (code written)
- **verified**: Task has been tested and confirmed working

#### How to Use Verification
1. Mark task `completed` when implementation is done
2. At logical checkpoints, verify groups of completed tasks together
3. Mark tasks `verified` after verification passes

#### Verification Checkpoints (when to verify)
Tasks have `verification_group` labels (e.g., "foundation", "frontend_ui", "api"). Verify when:

1. **After completing all tasks in a verification_group** - e.g., after all "foundation" tasks, run `npm run dev`
2. **After major milestones** - e.g., project setup, feature completion
3. **Before declaring work complete** - Run full build (`npm run build`)

Use `get_task_plan()` to see tasks grouped by `verification_group` under `verification_groups`.

#### Verification Commands
Tasks have `verification_method` in metadata - USE IT:
```
update_task_status("F001", "completed", "Created Next.js project")
# ... complete more foundation tasks ...
# Verify the group:
# npm run dev → works!
update_task_status("F001", "verified", "Dev server runs on localhost:3000")
```

**A task should NOT be marked `verified` if:**
- The code doesn't compile/build
- The dev server crashes on startup
- The feature doesn't render or function as described

Fix issues before marking as verified.

### Evaluating CURRENT_ANSWERS

When you see other agents' work, you'll receive **progress stats** showing task completion.
These are INFORMATIONAL only - they help you understand where others are, but task count alone
doesn't determine quality.

**Focus on Deliverable Quality** (the end product matters most):
- Does the deliverable work? (website loads, app runs, API responds)
- Does it meet the original requirements from the planning docs?
- Is the user-facing quality good? (UI looks right, features work as expected)

**Progress stats are context, not judgment**:
- An agent with fewer tasks completed might have better quality work
- An agent with all tasks done might have rushed and produced poor quality
- Use progress info to understand scope, but evaluate the actual deliverable

**Only vote when work is TRULY COMPLETE and HIGH QUALITY**:
- All planned tasks should be done (or have documented reasons for deviation)
- The deliverable must be functional and meet quality expectations
- Don't vote for partial implementations, even if task count looks good

### Adopting Another Agent's Work

If you see a CURRENT_ANSWER that's excellent and you want to build on it:
1. Their plan progress is in their `tasks/plan.json`
2. To adopt: copy their plan.json content into YOUR `tasks/plan.json` via `create_task_plan(tasks=[...])`
3. Then continue from where they left off

If no agent is fully complete with quality work, continue your own implementation rather than voting for incomplete work.
"""


def prepare_plan_execution_config(
    config: Dict[str, Any],
    plan_session: "PlanSession",
) -> Dict[str, Any]:
    """
    Prepare config for plan execution (used by both CLI and TUI).

    Modifies config to:
    1. Add frozen plan as read-only context path
    2. Enable planning MCP tools for task tracking
    3. Inject plan execution guidance into agents' system messages

    Args:
        config: Full config dict to modify
        plan_session: PlanSession with frozen plan

    Returns:
        Modified config dict ready for orchestrator
    """
    exec_config = copy.deepcopy(config)

    # Set up context paths
    orchestrator_cfg = exec_config.setdefault("orchestrator", {})
    context_paths = orchestrator_cfg.setdefault("context_paths", [])

    # Restore context paths from planning phase (if stored in metadata)
    try:
        metadata = plan_session.load_metadata()
        if metadata.context_paths:
            context_paths.extend(metadata.context_paths)
            logger.info(
                f"[PlanExecution] Restored {len(metadata.context_paths)} context paths from planning phase",
            )
    except Exception as e:
        logger.warning(f"[PlanExecution] Could not load context paths from metadata: {e}")

    # Add frozen plan as read-only context
    context_paths.append(
        {
            "path": str(plan_session.frozen_dir),
            "permission": "read",
        },
    )

    # Enable planning MCP tools for task tracking
    coordination_cfg = orchestrator_cfg.setdefault("coordination", {})
    coordination_cfg["enable_agent_task_planning"] = True
    coordination_cfg["task_planning_filesystem_mode"] = True

    # Inject plan execution guidance into agents' system messages
    if "agents" in exec_config:
        for agent_cfg in exec_config["agents"]:
            existing_msg = agent_cfg.get("system_message", "")
            agent_cfg["system_message"] = existing_msg + PLAN_EXECUTION_GUIDANCE
    elif "agent" in exec_config:
        agent_cfg = exec_config["agent"]
        existing_msg = agent_cfg.get("system_message", "")
        agent_cfg["system_message"] = existing_msg + PLAN_EXECUTION_GUIDANCE

    return exec_config


def setup_agent_workspaces_for_execution(
    agents: Dict[str, Any],
    plan_session: "PlanSession",
) -> int:
    """
    Copy plan and supporting docs to each agent's workspace.

    Called after agents are created but before orchestrator runs.
    This ensures agents have immediate access to the plan.

    Args:
        agents: Dictionary mapping agent_id to agent instance
        plan_session: PlanSession with frozen plan

    Returns:
        Number of tasks in the plan (0 if plan not found)
    """
    frozen_plan_file = plan_session.frozen_dir / "plan.json"
    if not frozen_plan_file.exists():
        logger.warning(f"[PlanExecution] Frozen plan not found at {frozen_plan_file}")
        return 0

    try:
        plan_data = json.loads(frozen_plan_file.read_text())
    except json.JSONDecodeError as e:
        logger.error(f"[PlanExecution] Failed to parse frozen plan: {e}")
        return 0

    plan_tasks = plan_data.get("tasks", [])
    task_count = len(plan_tasks)

    for agent_id, agent in agents.items():
        if hasattr(agent.backend, "filesystem_manager") and agent.backend.filesystem_manager:
            agent_workspace = Path(agent.backend.filesystem_manager.cwd)

            # Copy supporting docs (*.md files) to planning_docs/ for reference
            planning_docs_dest = agent_workspace / "planning_docs"
            planning_docs_dest.mkdir(exist_ok=True)
            for doc in plan_session.frozen_dir.glob("*.md"):
                shutil.copy2(doc, planning_docs_dest / doc.name)
                logger.info(f"[PlanExecution] Copied {doc.name} to {agent_id}'s planning_docs/")

            # Copy plan.json directly to tasks/plan.json so agents can read it immediately
            # Write full plan_data to preserve top-level metadata (agent_id, timestamps, subagents)
            if plan_tasks:
                tasks_dir = agent_workspace / "tasks"
                tasks_dir.mkdir(exist_ok=True)
                plan_file = tasks_dir / "plan.json"
                plan_file.write_text(json.dumps(plan_data, indent=2))
                logger.info(
                    f"[PlanExecution] Copied plan.json to {agent_id}'s tasks/plan.json ({task_count} tasks)",
                )

    return task_count


def build_execution_prompt(question: str) -> str:
    """
    Build the execution prompt that guides agents through plan-based work.

    Args:
        question: The original user question/task

    Returns:
        Formatted execution prompt with plan context
    """
    return f"""# PLAN EXECUTION MODE

Your task plan has been AUTO-LOADED into `tasks/plan.json`. Start executing!

## Your Task
{question}

## Getting Started

1. **Check ready tasks**: Use `get_ready_tasks()` to see what to work on first
2. **Track progress**: Use `update_task_status(task_id, status, completion_notes)` as you work
3. **Execute all tasks**: Implement everything in the plan
4. **Evaluate others**: See system prompt for how to assess CURRENT_ANSWERS

## Reference Materials
- `planning_docs/` - supporting docs from planning phase (user stories, design, etc.)
- Frozen plan available via context path for validation

Begin execution now."""
