# -*- coding: utf-8 -*-
"""Standalone MCP server that exposes the MassGen submit_checklist tool.

This allows CLI-based backends (Codex) to use the checklist-gated voting
tool as a native MCP tool call.  The server reads checklist configuration
and mutable state from a JSON specs file written by the orchestrator.

The server re-reads the specs file on every tool call so the orchestrator
can update state (remaining budget, has_existing_answers) between rounds
without restarting the server process.

Usage (launched by backend via config.toml):
    fastmcp run massgen/mcp_tools/checklist_tools_server.py:create_server -- \
        --specs /path/to/checklist_specs.json
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict

import fastmcp

logger = logging.getLogger(__name__)

SERVER_NAME = "massgen_checklist"


async def create_server() -> fastmcp.FastMCP:
    """Factory function to create MCP server from checklist specs."""
    parser = argparse.ArgumentParser(description="MassGen Checklist MCP Server")
    parser.add_argument(
        "--specs",
        type=str,
        required=True,
        help="Path to JSON file containing checklist specs and state",
    )
    args = parser.parse_args()

    mcp = fastmcp.FastMCP(SERVER_NAME)
    specs_path = Path(args.specs)

    _register_checklist_tool(mcp, specs_path)

    logger.info(f"Checklist MCP server ready (specs: {specs_path})")
    return mcp


def _read_specs(specs_path: Path) -> Dict[str, Any]:
    """Read specs file, returning empty dict on error."""
    try:
        with open(specs_path) as f:
            return json.load(f)
    except Exception as exc:
        logger.error(f"Failed to read checklist specs: {exc}")
        return {}


def _extract_score(entry: Any) -> int:
    """Extract numeric score from either int or {"score": int, "reasoning": str}."""
    if isinstance(entry, dict):
        return entry.get("score", 0)
    if isinstance(entry, (int, float)):
        return int(entry)
    return 0


def _register_checklist_tool(mcp: fastmcp.FastMCP, specs_path: Path) -> None:
    """Register the submit_checklist tool on the FastMCP server."""
    import inspect

    # Read specs once at startup just for the tool schema
    specs = _read_specs(specs_path)
    items = specs.get("items", [])

    # Create handler that re-reads state on each call.
    # Each score entry is {"score": int, "reasoning": str} — the reasoning
    # forces the model to justify each item but is not used in verdict logic.
    # `improvements` captures unrealized potential.
    async def submit_checklist(
        scores: dict,
        improvements: str = "",
    ) -> str:
        # Codex sometimes sends scores as a JSON string; normalise to dict
        if isinstance(scores, str):
            try:
                scores = json.loads(scores)
            except (json.JSONDecodeError, TypeError):
                return json.dumps(
                    {"error": "scores must be a JSON object, not a string"},
                )

        # Re-read specs to get latest state from orchestrator
        current = _read_specs(specs_path)
        current_items = current.get("items", items)
        state = current.get("state", {})

        terminate_action = state.get("terminate_action", "vote")
        iterate_action = state.get("iterate_action", "new_answer")
        has_existing_answers = state.get("has_existing_answers", False)

        # Pre-computed by orchestrator so this server has no massgen dependency
        required = state.get("required", len(current_items))
        cutoff = state.get("cutoff", 70)

        items_detail = []
        true_count = 0
        for i, _item_text in enumerate(current_items):
            key = f"T{i+1}"
            entry = scores.get(key, 0)
            score = _extract_score(entry)
            passed = score >= cutoff
            if passed:
                true_count += 1
            items_detail.append({"id": key, "score": score, "passed": passed})

        # Force iterate when no answers exist yet
        if not has_existing_answers:
            verdict = iterate_action
            explanation = f"First answer — no existing answers to evaluate. " f"Verdict: {verdict}."
        else:
            verdict = terminate_action if true_count >= required else iterate_action
            if verdict == iterate_action:
                failed_ids = [d["id"] for d in items_detail if not d["passed"]]
                improvements_text = improvements.strip() if improvements else ""
                explanation = (
                    f"{true_count} of {len(current_items)} items passed "
                    f"(required: {required}). Verdict: {verdict}. "
                    f"Items that need improvement: {', '.join(failed_ids)}. "
                    f"Your new answer MUST make material changes — do NOT "
                    f"simply copy or resubmit the same content."
                )
                if improvements_text:
                    explanation += (
                        f" Your own improvements analysis identified: "
                        f"{improvements_text} — use this as your implementation "
                        f"plan. The result must be obviously better, not just "
                        f"marginally different."
                    )
            else:
                explanation = f"{true_count} of {len(current_items)} items passed " f"(required: {required}). Verdict: {verdict}."

        result = {
            "verdict": verdict,
            "explanation": explanation,
            "true_count": true_count,
            "required": required,
            "items": items_detail,
        }
        return json.dumps(result)

    submit_checklist.__doc__ = (
        "Submit your checklist evaluation. Each score in 'scores' must be an "
        "object with 'score' (0-100) and 'reasoning' (why you gave that score). "
        "The 'improvements' field should describe features or content that an "
        "ideal answer would have but no existing answer has attempted."
    )

    # Set proper signature so FastMCP sees both parameters
    sig = inspect.Signature(
        [
            inspect.Parameter("scores", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            inspect.Parameter("improvements", inspect.Parameter.POSITIONAL_OR_KEYWORD),
        ],
    )
    submit_checklist.__signature__ = sig

    mcp.tool(
        name="submit_checklist",
        description=submit_checklist.__doc__,
    )(submit_checklist)

    logger.info("Registered submit_checklist MCP tool")


# ---------- spec file I/O ----------


def write_checklist_specs(
    items: list,
    state: Dict[str, Any],
    output_path: Path,
) -> Path:
    """Write checklist specs + state to a JSON file.

    Called by the orchestrator before launch and whenever state changes.
    """
    specs = {
        "items": items,
        "state": state,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(specs, f, indent=2)
    return output_path


def build_server_config(specs_path: Path) -> Dict[str, Any]:
    """Build a stdio MCP server config dict for the checklist server."""
    script_path = Path(__file__).resolve()

    return {
        "name": SERVER_NAME,
        "type": "stdio",
        "command": "fastmcp",
        "args": [
            "run",
            f"{script_path}:create_server",
            "--",
            "--specs",
            str(specs_path),
        ],
        "env": {"FASTMCP_SHOW_CLI_BANNER": "false"},
        "tool_timeout_sec": 120,
    }
