# Worktrees Module

## Overview

When `write_mode` is enabled, agents work in git worktrees — isolated checkouts of the user's project. Each coordination round, every agent gets a fresh worktree with its own branch. Branches are preserved across rounds for cross-agent visibility, and scratch files are archived for continuity.

## Lifecycle

```
Round 1                          Round 2                         Final Presentation
─────────────────────────────    ──────────────────────────────  ─────────────────────────
agent1: massgen/a1b2c3d4         agent1: massgen/e5f6g7h8        presenter: presenter
agent2: massgen/i9j0k1l2         agent2: massgen/m3n4o5p6          (based on winner's branch)
     │                                │
     ▼                                ▼
cleanup_round()                  cleanup_round()
  ├─ auto-commit changes           ├─ auto-commit changes
  ├─ archive scratch → agent1/     ├─ archive scratch → agent1/
  ├─ remove worktree               ├─ remove worktree
  └─ keep branch                   └─ keep branch
                                                                cleanup_session()
                                                                  └─ delete all branches
```

## Branch Naming

| Context | Branch Name | Example |
|---------|------------|---------|
| Regular rounds | `massgen/{8-char hex}` | `massgen/f028d1c7` |
| Final presentation | `branch_label` param (explicit) | `presenter` |
| No `branch_label` | Random hex suffix | `massgen/a1b2c3d4` |

Branch names are intentionally short and anonymous. They do NOT contain agent IDs, round numbers, or session IDs.

### Why not `agent1`, `agent2` as branch names?

An agent's branch gets deleted when it starts a new round (`previous_branch` mechanism). If agent1's branch were named `agent1` in round 1, then in round 2 that branch gets deleted and recreated — meaning other agents lose the reference mid-session. Short random names avoid this collision.

Instead, the **system prompt** maps other agents' branches to readable labels:

```
Other agents' branches:
- agent1: `massgen/f028d1c7`
- agent2: `massgen/a1b2c3d4`
```

## Scratch Directory

Each worktree gets a `.massgen_scratch/` directory:

- Git-excluded (via `info/exclude` in the **common** git dir)
- For experiments, eval scripts, notes
- Invisible to `git status`, `git diff`, and reviewers

### Scratch Archive

On `cleanup_round()`, scratch files are moved to the workspace:

```
{workspace}/.scratch_archive/
├── agent1/          # From round N (named by archive_label)
│   └── notes.md
└── agent2/
    └── eval.py
```

The `archive_label` parameter on `move_scratch_to_workspace()` controls the directory name. The orchestrator passes the anonymous agent ID (e.g. `agent1`), making archives human-readable.

Without `archive_label`, falls back to the hex suffix from the branch name.

## Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `IsolationContextManager` | `massgen/filesystem_manager/_isolation_context_manager.py` | Creates/manages worktrees, scratch dirs, branch lifecycle |
| `WorktreeManager` | `massgen/infrastructure/` | Low-level GitPython wrapper for worktree operations |
| `WorkspaceStructureSection` | `massgen/system_prompt_sections.py` | System prompt section showing branches and workspace info |

## IsolationContextManager Parameters

| Parameter | Type | Used For |
|-----------|------|----------|
| `session_id` | `str` | Not used in branch names (only for logging) |
| `write_mode` | `str` | `"auto"`, `"worktree"`, `"isolated"`, `"legacy"` |
| `workspace_path` | `str` | Where worktrees are created (`{workspace}/.worktree/`) |
| `previous_branch` | `str` | Branch to delete on init (one-branch-per-agent invariant) |
| `base_commit` | `str` | Starting point for worktree (e.g. winner's branch for final pres) |
| `branch_label` | `str` | Explicit branch name override (e.g. `"presenter"`) |

## System Prompt

The `WorkspaceStructureSection` shows agents:

1. **Their branch**: "Your work is on branch `massgen/f028d1c7`. All changes are auto-committed when your turn ends."
2. **Other agents' branches** (with anonymous labels): `agent1: massgen/abc123`
3. **Scratch archive reminder**: "Check `.scratch_archive/` for experiments from prior rounds."

The prompt does NOT reveal which anonymous ID the agent is — maintaining anonymity. The agent sees its branch name (which is random) but doesn't know it corresponds to any particular agent label.

## Auto-Commit

`cleanup_round()` auto-commits all uncommitted changes before removing the worktree:

```python
# In _auto_commit_worktree():
repo.git.add("-A")
repo.index.commit("[ROUND] Auto-commit")
```

This ensures the branch contains the agent's actual work even after the worktree is gone. Without this, the branch would point at HEAD (empty) and cross-agent visibility would find nothing.

## Orchestrator Integration

### Regular Rounds (`_stream_agent_execution`)

```python
round_isolation_mgr = IsolationContextManager(
    session_id=f"{self.session_id}-{round_suffix}",
    write_mode=write_mode,
    workspace_path=workspace_path,
    previous_branch=previous_branch,
    # No branch_label — uses short random name
)
```

Other branches passed to system prompt as `Dict[str, str]`:
```python
other_agent_branches = {
    agent_mapping.get(aid, aid): branch  # {"agent1": "massgen/abc123"}
    for aid, branch in self._agent_current_branches.items()
    if aid != agent_id and branch
}
```

### Final Presentation

```python
self._isolation_manager = IsolationContextManager(
    session_id=self.session_id,
    write_mode=write_mode,
    workspace_path=workspace_path,
    base_commit=winner_branch,       # Start from winner's work
    branch_label="presenter",        # Explicit readable name
)
```

## Testing

Tests live in `massgen/tests/test_write_mode_scratch.py`. Key test classes:

| Class | Covers |
|-------|--------|
| `TestScratchDirectory` | `.massgen_scratch/` creation, git exclusion, diff filtering |
| `TestScratchArchiveLabel` | `archive_label` naming, fallback to hex suffix |
| `TestBranchLifecycle` | `cleanup_round` keeps branch, `cleanup_session` deletes, `previous_branch` deletion |
| `TestWorkspaceScratchNoContextPaths` | Workspace mode (no context_paths) branch + scratch lifecycle |
| `TestAutoCommitBeforeCleanup` | Auto-commit on cleanup, no-op when clean |
| `TestWorkspaceStructureBranchInfo` | System prompt shows branch name, other branches with labels, scratch archive mention |
| `TestRestartContextBranchInfo` | Branch info in restart context (dict format) |

```bash
uv run pytest massgen/tests/test_write_mode_scratch.py -v
```
