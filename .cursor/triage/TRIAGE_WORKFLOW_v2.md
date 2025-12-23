# Triage Workflow V2 (MassGen)

This document defines the standard workflow for triaging and fixing test failures in MassGen. It enforces a strict separation of artifacts and a traceable "Fix Loop" for agents.

## 1. Artifact Architecture

All triage artifacts are stored in `.cursor/triage/` to prevent workspace clutter.

| Path | Description |
| :--- | :--- |
| `.cursor/triage/TRIAGE_DASHBOARD.md` | **Central Dashboard**. Tracks global run stats (Pass/Fail) and status of all clusters. Agents update this. |
| `.cursor/triage/inbox/` | **Raw Inputs**. JUnit XML files (`junit-latest.xml`, etc.). |
| `.cursor/triage/clusters/` | **Task Packets**. One Markdown file per cluster (e.g., `cluster_abc123.md`). |
| `.cursor/triage/reports/` | **History**. CSVs or logs tracking pass/fail counts over time. |
| `.cursor/triage/artifacts/` | **Debris**. Place for temp workspaces (e.g., `test_workspace/`) generated during runs. |

## 2. The "Fix Loop" (Agent Protocol)

Agents must follow this strict loop when assigned a triage task. **Always use the `.venv` environment for execution.**

### Phase 1: Pickup
1.  **Read Dashboard**: Open `.cursor/triage/TRIAGE_DASHBOARD.md`.
2.  **Select Cluster**: Find a cluster marked `[ ] Open`.
3.  **Read Packet**: Open the corresponding `.cursor/triage/clusters/cluster_<id>.md`.
    *   *Note: The packet contains the "Compact Context" (failure trace + suspect files).*

### Phase 2: Baseline (Verify Failure)
1.  **Execute Repro**: Run the "Single failing test" command provided in the packet.
2.  **Assert Failure**: The test **MUST** fail. If it passes, the cluster is flaky or already fixed. Mark as `[?] Investigate`.

### Phase 3: Fix
1.  **Analyze**: Use the stack trace and suspect files to identify the root cause.
2.  **Scope & Safety**:
    *   **Primary Goal**: Align failing tests with current CODE or clean them up.
    *   **Code Freeze**: Do NOT change application code unless absolutely necessary and apparent.
    *   **Escalate**: If application code appears fundamentally broken/bad, **STOP** and warn the user.
3.  **Classify**:
    *   **Test Fix**: Update test logic/expectations.
    *   **Integration/External**: Add `@pytest.mark.integration` (or `docker`/`expensive`) to skip by default.
    *   **Defer**: Add an entry to `massgen/tests/xfail_registry.yml` with a strict **expiry date**.
4.  **Implement**: Apply the fix.

### Phase 4: Verify (Verify Fix)
1.  **Execute Repro**: Run the "Single failing test" command again.
2.  **Assert Pass**: The test **MUST** pass (or be skipped/xfailed).
3.  **Execute Cluster**: Run the "Cluster subset" command (up to 25 tests) to ensure no regressions in the group.

### Phase 5: Update
1.  **Update Dashboard**: Edit `.cursor/triage/TRIAGE_DASHBOARD.md`.
  *   **Triage Progress (Live)**: Update `Current` and `Delta` for Total/Passed/Failed/Skipped. Keep `Total` stable; treat new xfails as **Skipped**. Delta = Current − Baseline.
  *   **Progress Log (Snapshots)**: Append a row (or create table if missing) with cluster ID, status, owner, and the current Total/Passed/Failed/Skipped after your fix.
  *   Change `[ ] Open` to `[x] Resolved` (or `[-] Deferred`).
  *   Add your Agent ID (or "User") to the "Owner" column.
  *   **Resolution Column**: Add a brief note including:
    *   **Stats**: Before/After counts (e.g., "4 Fail -> 4 Pass" or "4 Fail -> 4 XFail").
    *   **Action**: What was done (e.g., "Fixed typo", "Refactored fixture", "Deferred").
2.  **Log**: (Optional) Append a line to `.cursor/triage/reports/fix_log.md` with details.

## 3. Tooling Reference

### Generating the Dashboard (Triage Lead)
To refresh the dashboard from a new test run:

```bash
# 1. Run tests (generate XML)
/Users/admin/src/MassGen/.venv/bin/python -m pytest massgen/tests \
  --junitxml=.cursor/triage/inbox/junit-latest.xml

# 2. Cluster & Update Dashboard
/Users/admin/src/MassGen/.venv/bin/python .cursor/triage/triage_pytest_failures.py \
  --junit-xml .cursor/triage/inbox/junit-latest.xml \
  --out-dir .cursor/triage
```

### Configuration
*   **Policy**: `massgen/tests/conftest.py` (Defines markers and default skips).
*   **Registry**: `massgen/tests/xfail_registry.yml` (Tracks deferred failures).
