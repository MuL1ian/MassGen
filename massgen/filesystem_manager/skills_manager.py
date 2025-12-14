# -*- coding: utf-8 -*-
"""
Skills management for MassGen.

This module provides utilities for discovering and managing skills installed via openskills.
Skills extend agent capabilities with specialized knowledge, workflows, and tools.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional

import yaml


def scan_skills(skills_dir: Path, logs_dir: Optional[Path] = None) -> List[Dict[str, str]]:
    """Scan for available skills from multiple sources.

    Discovers skills by scanning directories for SKILL.md files and parsing their
    YAML frontmatter metadata. Includes:
    - External skills (from openskills, in .agent/skills/)
    - Built-in skills (shipped with MassGen, in massgen/skills/)
    - Previous session skills (from massgen_logs, if logs_dir provided)

    Args:
        skills_dir: Path to external skills directory (typically .agent/skills/).
                   This is where openskills installs skills.
        logs_dir: Optional path to massgen_logs directory. If provided, scans for
                 SKILL.md files from previous sessions.

    Returns:
        List of skill dictionaries with keys: name, description, location.
        Location is "project", "builtin", or "previous_session".

    Example:
        >>> skills = scan_skills(Path(".agent/skills"))
        >>> print(skills[0])
        {'name': 'pdf', 'description': 'PDF manipulation toolkit...', 'location': 'project'}
    """
    skills = []

    # Scan external skills directory (.agent/skills/)
    if skills_dir.exists():
        skills.extend(_scan_directory(skills_dir, location="project"))

    # Scan built-in skills from massgen/skills/ (flat structure)
    builtin_base = Path(__file__).parent.parent / "skills"
    if builtin_base.exists():
        skills.extend(_scan_directory(builtin_base, location="builtin"))

    # Scan previous session skills if logs_dir provided
    if logs_dir:
        skills.extend(scan_previous_session_skills(logs_dir))

    return skills


def _scan_directory(directory: Path, location: str) -> List[Dict[str, str]]:
    """Scan a directory for skills.

    Args:
        directory: Directory to scan for skills
        location: Location type ("project" or "builtin")

    Returns:
        List of skill dictionaries with metadata
    """
    skills = []

    if not directory.is_dir():
        return skills

    for skill_path in directory.iterdir():
        if not skill_path.is_dir():
            continue

        # Look for SKILL.md file
        skill_file = skill_path / "SKILL.md"
        if not skill_file.exists():
            continue

        try:
            # Parse YAML frontmatter
            content = skill_file.read_text(encoding="utf-8")
            metadata = parse_frontmatter(content)

            skills.append(
                {
                    "name": metadata.get("name", skill_path.name),
                    "description": metadata.get("description", ""),
                    "location": location,
                },
            )
        except Exception:
            # Skip skills that can't be parsed
            continue

    return skills


def scan_previous_session_skills(logs_dir: Path) -> List[Dict[str, str]]:
    """Scan massgen_logs for SKILL.md files from previous sessions.

    For each session/turn, finds the last attempt (highest attempt_N) and
    looks for SKILL.md in each agent's evolving_skill directory:
    attempt_N/final/agent_X/workspace/tasks/evolving_skill/SKILL.md

    Args:
        logs_dir: Path to .massgen/massgen_logs/

    Returns:
        List of skill dicts with keys: name, description, location, source_path.
        Location will be "previous_session".
    """
    skills = []

    if not logs_dir.exists():
        return skills

    # Iterate through all log sessions (newest first)
    for session_dir in sorted(logs_dir.iterdir(), reverse=True):
        if not session_dir.is_dir() or not session_dir.name.startswith("log_"):
            continue

        # Iterate through turns
        for turn_dir in session_dir.iterdir():
            if not turn_dir.is_dir() or not turn_dir.name.startswith("turn_"):
                continue

            # Find the last attempt (highest attempt_N number)
            attempts = [d for d in turn_dir.iterdir() if d.is_dir() and d.name.startswith("attempt_")]
            if not attempts:
                continue

            # Sort by attempt number and take the last one
            try:
                last_attempt = sorted(attempts, key=lambda x: int(x.name.split("_")[1]))[-1]
            except (ValueError, IndexError):
                continue

            # Look for SKILL.md in each agent's evolving_skill directory
            final_dir = last_attempt / "final"
            if not final_dir.exists():
                continue

            for agent_dir in final_dir.iterdir():
                if not agent_dir.is_dir() or not agent_dir.name.startswith("agent_"):
                    continue

                skill_file = agent_dir / "workspace" / "tasks" / "evolving_skill" / "SKILL.md"
                if skill_file.exists():
                    try:
                        content = skill_file.read_text(encoding="utf-8")
                        metadata = parse_frontmatter(content)
                        skills.append(
                            {
                                "name": metadata.get("name", f"session-{session_dir.name}"),
                                "description": metadata.get("description", ""),
                                "location": "previous_session",
                                "source_path": str(skill_file),
                            },
                        )
                    except Exception:
                        continue

    return skills


def parse_frontmatter(content: str) -> Dict[str, str]:
    """Extract YAML frontmatter from skill file.

    Parses YAML frontmatter delimited by --- markers at the start of a file.
    This is the standard format used by openskills for skill metadata.

    Args:
        content: File content to parse

    Returns:
        Dictionary of metadata from frontmatter

    Example:
        >>> content = '''---
        ... name: example
        ... description: Example skill
        ... ---
        ... # Content here'''
        >>> metadata = parse_frontmatter(content)
        >>> print(metadata['name'])
        'example'
    """
    # Match YAML frontmatter between --- markers
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}

    try:
        # Parse YAML content
        frontmatter = match.group(1)
        metadata = yaml.safe_load(frontmatter)

        # Ensure we return a dict
        if not isinstance(metadata, dict):
            return {}

        return metadata
    except yaml.YAMLError:
        # Fall back to simple key: value parsing if YAML parsing fails
        return _parse_simple_frontmatter(match.group(1))


def _parse_simple_frontmatter(frontmatter: str) -> Dict[str, str]:
    """Simple key: value parser for frontmatter as fallback.

    Args:
        frontmatter: Frontmatter text to parse

    Returns:
        Dictionary of parsed key-value pairs
    """
    metadata = {}
    for line in frontmatter.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()

    return metadata
