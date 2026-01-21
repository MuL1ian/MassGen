# -*- coding: utf-8 -*-
"""Plan storage and session management for plan-and-execute workflow."""

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .logger_config import logger

PLANS_DIR = Path(".massgen/plans")


@dataclass
class PlanMetadata:
    """Metadata for a plan session."""

    plan_id: str
    created_at: str
    planning_session_id: str
    planning_log_dir: str
    execution_session_id: Optional[str] = None
    execution_log_dir: Optional[str] = None
    status: str = "planning"  # planning, ready, executing, completed, failed


class PlanSession:
    """Represents a single plan-and-execute session."""

    def __init__(self, plan_id: str, create: bool = False):
        self.plan_id = plan_id
        self.plan_dir = PLANS_DIR / f"plan_{plan_id}"
        self.workspace_dir = self.plan_dir / "workspace"
        self.frozen_dir = self.plan_dir / "frozen"
        self.metadata_file = self.plan_dir / "plan_metadata.json"
        self.execution_log_file = self.plan_dir / "execution_log.jsonl"
        self.diff_file = self.plan_dir / "plan_diff.json"

        if create:
            self.plan_dir.mkdir(parents=True, exist_ok=True)
            self.workspace_dir.mkdir(exist_ok=True)
            self.frozen_dir.mkdir(exist_ok=True)

    def load_metadata(self) -> PlanMetadata:
        """Load plan metadata from disk."""
        if not self.metadata_file.exists():
            raise FileNotFoundError(f"Plan metadata not found: {self.metadata_file}")
        return PlanMetadata(**json.loads(self.metadata_file.read_text()))

    def save_metadata(self, metadata: PlanMetadata):
        """Save plan metadata to disk."""
        self.metadata_file.write_text(json.dumps(metadata.__dict__, indent=2))

    def log_event(self, event_type: str, data: Dict[str, Any]):
        """Append event to execution log."""
        event = {"timestamp": datetime.now().isoformat(), "event_type": event_type, "data": data}
        with self.execution_log_file.open("a") as f:
            f.write(json.dumps(event) + "\n")

    def copy_workspace_to_frozen(self):
        """Copy workspace contents to frozen directory (immutable snapshot)."""
        if self.frozen_dir.exists():
            shutil.rmtree(self.frozen_dir)
        shutil.copytree(self.workspace_dir, self.frozen_dir)
        logger.info(f"[PlanStorage] Froze workspace snapshot: {self.frozen_dir}")

    def compute_plan_diff(self) -> Dict[str, Any]:
        """Compare workspace/ and frozen/ to detect plan drift."""
        # Plan is stored as plan.json in workspace root (renamed from project_plan.json during finalize)
        workspace_plan = self.workspace_dir / "plan.json"
        frozen_plan = self.frozen_dir / "plan.json"

        if not workspace_plan.exists() or not frozen_plan.exists():
            return {"error": "Plan files missing"}

        workspace_data = json.loads(workspace_plan.read_text())
        frozen_data = json.loads(frozen_plan.read_text())

        diff = {"tasks_added": [], "tasks_removed": [], "tasks_modified": [], "divergence_score": 0.0}

        workspace_ids = {t["id"]: t for t in workspace_data.get("tasks", [])}
        frozen_ids = {t["id"]: t for t in frozen_data.get("tasks", [])}

        # Find added tasks
        for task_id in workspace_ids:
            if task_id not in frozen_ids:
                diff["tasks_added"].append(task_id)

        # Find removed tasks
        for task_id in frozen_ids:
            if task_id not in workspace_ids:
                diff["tasks_removed"].append(task_id)

        # Find modified tasks
        for task_id in frozen_ids:
            if task_id in workspace_ids:
                if workspace_ids[task_id] != frozen_ids[task_id]:
                    diff["tasks_modified"].append({"id": task_id, "original": frozen_ids[task_id], "modified": workspace_ids[task_id]})

        # Compute divergence score (0.0 = no changes, 1.0 = complete rewrite)
        total_tasks = len(frozen_ids)
        if total_tasks > 0:
            changes = len(diff["tasks_added"]) + len(diff["tasks_removed"]) + len(diff["tasks_modified"])
            diff["divergence_score"] = min(1.0, changes / total_tasks)

        return diff


class PlanStorage:
    """Manages plan storage and retrieval."""

    def __init__(self):
        PLANS_DIR.mkdir(parents=True, exist_ok=True)

    def create_plan(self, planning_session_id: str, planning_log_dir: str) -> PlanSession:
        """Create a new plan session."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        plan_id = timestamp

        session = PlanSession(plan_id, create=True)

        metadata = PlanMetadata(
            plan_id=plan_id,
            created_at=datetime.now().isoformat(),
            planning_session_id=planning_session_id,
            planning_log_dir=planning_log_dir,
            status="planning",
        )
        session.save_metadata(metadata)
        session.log_event("plan_created", {"plan_id": plan_id})

        logger.info(f"[PlanStorage] Created plan session: {plan_id}")
        return session

    def get_latest_plan(self) -> Optional[PlanSession]:
        """Get most recent plan session."""
        if not PLANS_DIR.exists():
            return None

        plan_dirs = sorted(PLANS_DIR.glob("plan_*"), reverse=True)
        if not plan_dirs:
            return None

        plan_id = plan_dirs[0].name.replace("plan_", "")
        return PlanSession(plan_id)

    def finalize_planning_phase(self, session: PlanSession, workspace_source: Path):
        """Copy planning workspace to plan storage and freeze it."""
        # Copy all files from planning workspace to session workspace
        if workspace_source.exists():
            for item in workspace_source.rglob("*"):
                if item.is_file():
                    rel_path = item.relative_to(workspace_source)
                    dest = session.workspace_dir / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)

        # Rename project_plan.json -> plan.json for MCP planning tool compatibility
        # Planning phase outputs project_plan.json (to distinguish from internal tasks/plan.json)
        # but execution phase expects plan/plan.json to align with MCP tools
        project_plan = session.workspace_dir / "project_plan.json"
        if project_plan.exists():
            project_plan.rename(session.workspace_dir / "plan.json")
            logger.info("[PlanStorage] Renamed project_plan.json -> plan.json")

        # Create immutable frozen copy
        session.copy_workspace_to_frozen()

        # Update metadata
        metadata = session.load_metadata()
        metadata.status = "ready"
        session.save_metadata(metadata)
        session.log_event("planning_finalized", {"workspace_files": [str(f) for f in session.workspace_dir.rglob("*") if f.is_file()]})

        logger.info(f"[PlanStorage] Finalized planning phase for {session.plan_id}")
