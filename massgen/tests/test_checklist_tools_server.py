# -*- coding: utf-8 -*-
"""Tests for checklist report-gating verdict logic."""

from pathlib import Path

from massgen.mcp_tools.checklist_tools_server import (
    evaluate_checklist_submission,
    write_checklist_specs,
)


def _all_pass_scores() -> dict:
    return {
        "T1": {"score": 95, "reasoning": "Strong confidence."},
        "T2": {"score": 92, "reasoning": "Strong confidence."},
        "T3": {"score": 94, "reasoning": "Strong confidence."},
        "T4": {"score": 93, "reasoning": "Strong confidence."},
        "T5": {"score": 96, "reasoning": "Strong confidence."},
    }


def _state(tmp_path: Path, require_gap_report: bool) -> dict:
    return {
        "terminate_action": "vote",
        "iterate_action": "new_answer",
        "has_existing_answers": True,
        "required": 5,
        "cutoff": 70,
        "require_gap_report": require_gap_report,
        "report_cutoff": 70,
        "workspace_path": str(tmp_path),
    }


def test_report_gate_forces_iteration_when_report_missing(tmp_path):
    items = ["a", "b", "c", "d", "e"]
    result = evaluate_checklist_submission(
        scores=_all_pass_scores(),
        improvements="Add stronger UX and testing.",
        report_path="",
        items=items,
        state=_state(tmp_path, require_gap_report=True),
    )

    assert result["verdict"] == "new_answer"
    assert result["report_gate_triggered"] is True
    assert result["report"]["passed"] is False
    assert any("Missing `report_path`" in issue for issue in result["report"]["issues"])


def test_report_gate_allows_vote_with_strong_report(tmp_path):
    items = ["a", "b", "c", "d", "e"]
    report_file = tmp_path / "tasks" / "checklist_gap_report.md"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(
        """
# Comprehensive Gap Report

## Output Quality
- The end result is functional but not impressive from the user perspective.
- The deliverable lacks richness and craft — it reads as adequate, not exceptional.

## Missing Improvements
- Requirements and scope: tighten acceptance criteria and user intent mapping.
- Correctness and logic: add edge case handling and explicit failure mode analysis.
- UX polish and accessibility: improve clarity, content quality, and a11y checks.
- Performance and reliability: reduce latency and strengthen error handling robustness.
- Security and privacy: verify permissions, compliance, and safety assumptions.
- Testing and validation: add tests, verification, observability, and monitoring metrics.

## Already Good Enough
Core structure is already good enough and keep as-is for now.

## Concrete Actions
1. Implement missing acceptance checks for requirements coverage.
2. Add edge-case tests for failure modes and logic validation.
3. Improve accessibility labels and keyboard flows.
4. Add performance instrumentation and monitor reliability regressions.
5. Harden security boundaries around sensitive operations.
6. Expand test coverage and validation automation.
""",
        encoding="utf-8",
    )

    result = evaluate_checklist_submission(
        scores=_all_pass_scores(),
        improvements="Close the identified gaps.",
        report_path="tasks/checklist_gap_report.md",
        items=items,
        state=_state(tmp_path, require_gap_report=True),
    )

    assert result["verdict"] == "vote"
    assert result["report_gate_triggered"] is False
    assert result["report"]["passed"] is True
    assert result["report"]["score"] >= result["report"]["cutoff"]


def test_report_gate_can_be_disabled(tmp_path):
    items = ["a", "b", "c", "d", "e"]
    result = evaluate_checklist_submission(
        scores=_all_pass_scores(),
        improvements="None",
        report_path="",
        items=items,
        state=_state(tmp_path, require_gap_report=False),
    )

    assert result["verdict"] == "vote"
    assert result["report"]["required"] is False
    assert result["report"]["passed"] is True


def test_write_checklist_specs_serializes_path_values(tmp_path):
    specs_path = tmp_path / "checklist_specs.json"
    workspace_path = tmp_path / "workspace"

    write_checklist_specs(
        items=["a", "b", "c", "d", "e"],
        state={"workspace_path": workspace_path, "required": 5, "cutoff": 70},
        output_path=specs_path,
    )

    assert specs_path.exists()
    data = specs_path.read_text(encoding="utf-8")
    assert '"workspace_path"' in data
    assert str(workspace_path) in data
