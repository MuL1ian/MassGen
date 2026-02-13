# -*- coding: utf-8 -*-
"""Standalone MCP server that exposes the MassGen submit_critique tool.

This allows CLI-based backends (Codex) to use the critique-based voting
tool as a native MCP tool call.  The server reads configuration and
mutable state from a JSON specs file written by the orchestrator.

The server re-reads the specs file on every tool call so the orchestrator
can update state (has_existing_answers) between rounds without restarting
the server process.

Usage (launched by backend via config.toml):
    fastmcp run massgen/mcp_tools/critique_tools_server.py:create_server -- \
        --specs /path/to/critique_specs.json

IMPORTANT: This file must NOT import from massgen — it runs inside Docker
for Codex where massgen is not installed.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import fastmcp

logger = logging.getLogger(__name__)

SERVER_NAME = "massgen_critique"


async def create_server() -> fastmcp.FastMCP:
    """Factory function to create MCP server from critique specs."""
    parser = argparse.ArgumentParser(description="MassGen Critique MCP Server")
    parser.add_argument(
        "--specs",
        type=str,
        required=True,
        help="Path to JSON file containing critique specs and state",
    )
    args = parser.parse_args()

    mcp = fastmcp.FastMCP(SERVER_NAME)
    specs_path = Path(args.specs)

    _register_critique_tool(mcp, specs_path)

    logger.info(f"Critique MCP server ready (specs: {specs_path})")
    return mcp


def _read_specs(specs_path: Path) -> Dict[str, Any]:
    """Read specs file, returning empty dict on error."""
    try:
        with open(specs_path) as f:
            return json.load(f)
    except Exception as exc:
        logger.error(f"Failed to read critique specs: {exc}")
        return {}


def _validate_tickets(tickets: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """Validate structural quality of deficiency tickets.

    Returns (valid, issues) where valid=False only if >50% of tickets
    have hard failures.  Individual issues are advisory unless the
    majority threshold is crossed.
    """
    issues: List[str] = []
    if not tickets:
        return True, []

    hard_failures = 0
    seen_word_sets: List[set] = []

    for ticket in tickets:
        tid = ticket.get("id", "?")

        # Check deficiency length
        deficiency = (ticket.get("deficiency") or "").strip()
        if len(deficiency) < 30:
            issues.append(f"{tid}: deficiency too short ({len(deficiency)} chars, need >= 30)")
            hard_failures += 1

        # Check verification
        verification = (ticket.get("verification") or "").strip()
        if len(verification) < 10:
            issues.append(f"{tid}: verification too short ({len(verification)} chars, need >= 10)")
            hard_failures += 1

        # Check severity
        severity = (ticket.get("severity") or "").strip().lower()
        if severity not in ("approach", "feature", "polish"):
            issues.append(f"{tid}: invalid severity '{severity}' (must be approach|feature|polish)")
            hard_failures += 1

        # Severity / smallest_fix mismatch
        smallest_fix = (ticket.get("smallest_fix") or "").strip()
        if severity == "approach" and len(smallest_fix) < 50:
            issues.append(
                f"{tid}: severity=approach but smallest_fix is only {len(smallest_fix)} chars " f"(approach-level problems need substantial fix descriptions >= 50 chars)",
            )

        # Near-duplicate detection via Jaccard similarity on word sets
        words = set(deficiency.lower().split())
        for prev_idx, prev_words in enumerate(seen_word_sets):
            if not words or not prev_words:
                continue
            intersection = len(words & prev_words)
            union = len(words | prev_words)
            if union > 0 and intersection / union > 0.8:
                issues.append(f"{tid}: near-duplicate of ticket at position {prev_idx + 1}")
        seen_word_sets.append(words)

    # Valid unless >50% of tickets have hard failures
    valid = hard_failures <= len(tickets) / 2
    return valid, issues


def evaluate_critique_submission(
    approach_assessment: Dict[str, Any],
    tickets: List[Dict[str, Any]],
    recommendation: str,
    recommendation_reasoning: str,
    state: Dict[str, Any],
) -> Dict[str, Any]:
    """Evaluate critique submission and return verdict payload used by stdio + SDK."""
    terminate_action = state.get("terminate_action", "vote")
    iterate_action = state.get("iterate_action", "new_answer")
    has_existing_answers = state.get("has_existing_answers", False)

    # Normalize tickets
    if not isinstance(tickets, list):
        tickets = []

    # Step 1: No existing answers → must produce first answer
    if not has_existing_answers:
        return {
            "verdict": iterate_action,
            "explanation": f"First answer — no existing answers to evaluate. Verdict: {iterate_action}.",
            "tickets_valid": True,
            "validation_issues": [],
            "approach_assessment": approach_assessment,
        }

    # Step 2: Validate ticket quality
    tickets_valid, validation_issues = _validate_tickets(tickets)
    if not tickets_valid:
        return {
            "verdict": "rejected",
            "explanation": (
                "Ticket quality is insufficient — more than half of your tickets have structural "
                "problems (too short, missing verification, invalid severity). Rewrite your tickets "
                f"with specific, concrete deficiencies. Issues: {'; '.join(validation_issues)}"
            ),
            "tickets_valid": False,
            "validation_issues": validation_issues,
            "approach_assessment": approach_assessment,
        }

    # Classify tickets by severity
    approach_tickets = [t for t in tickets if (t.get("severity") or "").lower() == "approach"]
    feature_tickets = [t for t in tickets if (t.get("severity") or "").lower() == "feature"]
    polish_tickets = [t for t in tickets if (t.get("severity") or "").lower() == "polish"]

    # Step 3: Any approach-level tickets → iterate with strategy change
    if approach_tickets:
        ticket_ids = [t.get("id", "?") for t in approach_tickets]
        return {
            "verdict": iterate_action,
            "explanation": (f"Approach-level deficiencies found ({', '.join(ticket_ids)}). " "Change your strategy — patches won't fix fundamental approach problems. " f"Verdict: {iterate_action}."),
            "tickets_valid": True,
            "validation_issues": validation_issues,
            "approach_assessment": approach_assessment,
        }

    # Step 4: Any feature-level tickets → iterate to close them
    if feature_tickets:
        ticket_ids = [t.get("id", "?") for t in feature_tickets]
        return {
            "verdict": iterate_action,
            "explanation": (f"Feature-level deficiencies remain ({', '.join(ticket_ids)}). " f"Close these tickets in your next answer. Verdict: {iterate_action}."),
            "tickets_valid": True,
            "validation_issues": validation_issues,
            "approach_assessment": approach_assessment,
        }

    # Step 5: Only polish or empty tickets → terminate
    explanation_parts = []
    if polish_tickets:
        explanation_parts.append(
            f"Only polish-level issues remain ({len(polish_tickets)} ticket(s))",
        )
    else:
        explanation_parts.append("No deficiencies found")
    explanation_parts.append(f"— the answer is ready. Verdict: {terminate_action}.")

    return {
        "verdict": terminate_action,
        "explanation": " ".join(explanation_parts),
        "tickets_valid": True,
        "validation_issues": validation_issues,
        "approach_assessment": approach_assessment,
    }


def _register_critique_tool(mcp: fastmcp.FastMCP, specs_path: Path) -> None:
    """Register the submit_critique tool on the FastMCP server."""
    import inspect

    # Read specs once at startup just for initial state
    _read_specs(specs_path)

    async def submit_critique(
        approach_assessment: dict,
        tickets: list,
        recommendation: str,
        recommendation_reasoning: str,
    ) -> str:
        # Codex sometimes sends args as JSON strings; normalise
        if isinstance(approach_assessment, str):
            try:
                approach_assessment = json.loads(approach_assessment)
            except (json.JSONDecodeError, TypeError):
                return json.dumps(
                    {"error": "approach_assessment must be a JSON object, not a string"},
                )
        if isinstance(tickets, str):
            try:
                tickets = json.loads(tickets)
            except (json.JSONDecodeError, TypeError):
                return json.dumps(
                    {"error": "tickets must be a JSON array, not a string"},
                )

        if not isinstance(approach_assessment, dict):
            return json.dumps({"error": "approach_assessment must be a JSON object"})
        if not isinstance(tickets, list):
            return json.dumps({"error": "tickets must be a JSON array"})

        # Re-read specs to get latest state from orchestrator
        current = _read_specs(specs_path)
        state = current.get("state", {})
        result = evaluate_critique_submission(
            approach_assessment=approach_assessment,
            tickets=tickets,
            recommendation=recommendation,
            recommendation_reasoning=recommendation_reasoning,
            state=state,
        )
        return json.dumps(result)

    submit_critique.__doc__ = (
        "Submit your deficiency critique. Provide an approach assessment, "
        "deficiency tickets (each with severity, impact, and verification), "
        "and your recommendation. The tool evaluates ticket significance and "
        "returns a verdict telling you whether to iterate or vote."
    )

    sig = inspect.Signature(
        [
            inspect.Parameter("approach_assessment", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            inspect.Parameter("tickets", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            inspect.Parameter("recommendation", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            inspect.Parameter("recommendation_reasoning", inspect.Parameter.POSITIONAL_OR_KEYWORD),
        ],
    )
    submit_critique.__signature__ = sig

    mcp.tool(
        name="submit_critique",
        description=submit_critique.__doc__,
    )(submit_critique)

    logger.info("Registered submit_critique MCP tool")


# ---------- spec file I/O ----------


def write_critique_specs(
    state: Dict[str, Any],
    output_path: Path,
) -> Path:
    """Write critique specs + state to a JSON file.

    Called by the orchestrator before launch and whenever state changes.
    """
    specs = {
        "state": state,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(specs, f, indent=2, default=str)
    return output_path


def build_server_config(specs_path: Path) -> Dict[str, Any]:
    """Build a stdio MCP server config dict for the critique server."""
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
