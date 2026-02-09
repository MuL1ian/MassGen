# -*- coding: utf-8 -*-
"""
Skills management for MassGen.

This module provides utilities for discovering and managing skills installed via openskills.
Skills extend agent capabilities with specialized knowledge, workflows, and tools.
"""

import re
import shutil
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

VALID_SKILL_LIFECYCLE_MODES = {"create_new", "create_or_update", "consolidate"}


def scan_skills(
    skills_dir: Path,
    logs_dir: Optional[Path] = None,
    include_user_skills: bool = True,
) -> List[Dict[str, Any]]:
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
        include_user_skills: If True, include skills from `~/.agent/skills/` in
            addition to project and built-in skills.

    Returns:
        List of skill dictionaries with keys: name, description, location.
        Location is "project", "builtin", or "previous_session".

    Example:
        >>> skills = scan_skills(Path(".agent/skills"))
        >>> print(skills[0])
        {'name': 'pdf', 'description': 'PDF manipulation toolkit...', 'location': 'project'}
    """
    skills: List[Dict[str, Any]] = []

    # Scan external skills directory (.agent/skills/)
    if skills_dir.exists():
        skills.extend(_scan_directory(skills_dir, location="project"))

    # Scan user skills directory (~/.agent/skills/)
    if include_user_skills:
        user_skills_dir = Path.home() / ".agent" / "skills"
        if user_skills_dir.exists():
            try:
                same_as_project = user_skills_dir.resolve() == skills_dir.resolve()
            except Exception:
                same_as_project = str(user_skills_dir) == str(skills_dir)
            if not same_as_project:
                skills.extend(_scan_directory(user_skills_dir, location="user"))

    # Scan built-in skills from massgen/skills/ (flat structure)
    builtin_base = Path(__file__).parent.parent / "skills"
    if builtin_base.exists():
        skills.extend(_scan_directory(builtin_base, location="builtin"))

    # Scan previous session skills if logs_dir provided
    if logs_dir:
        skills.extend(scan_previous_session_skills(logs_dir))

    return _dedupe_skills(skills)


def _scan_directory(directory: Path, location: str) -> List[Dict[str, Any]]:
    """Scan a directory for skills.

    Args:
        directory: Directory to scan for skills
        location: Location type ("project" or "builtin")

    Returns:
        List of skill dictionaries with metadata
    """
    skills: List[Dict[str, Any]] = []

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
            metadata_name = str(metadata.get("name", "")).strip()
            resolved_name = metadata_name or skill_path.name
            origin = metadata.get("massgen_origin") or metadata.get("origin") or metadata.get("source")
            is_evolving = bool(metadata.get("evolving")) or location == "previous_session"

            skills.append(
                {
                    "name": resolved_name,
                    "description": metadata.get("description", ""),
                    "location": location,
                    "source_path": str(skill_file),
                    "directory_path": str(skill_path),
                    "is_custom": location in {"project", "user", "previous_session"},
                    "is_evolving": is_evolving,
                    "origin": origin,
                },
            )
        except Exception:
            # Skip skills that can't be parsed
            continue

    return skills


def scan_previous_session_skills(logs_dir: Path) -> List[Dict[str, Any]]:
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
    skills: List[Dict[str, Any]] = []

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
                        origin = metadata.get("massgen_origin") or metadata.get("origin") or "previous_session"
                        skills.append(
                            {
                                "name": metadata.get("name", f"session-{session_dir.name}"),
                                "description": metadata.get("description", ""),
                                "location": "previous_session",
                                "source_path": str(skill_file),
                                "directory_path": str(skill_file.parent),
                                "is_custom": True,
                                "is_evolving": True,
                                "origin": origin,
                            },
                        )
                    except Exception:
                        continue

    return _dedupe_skills(skills)


def _dedupe_skills(skills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate skills by case-insensitive name, preserving first occurrence."""
    deduped: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for skill in skills:
        name = str(skill.get("name", "")).strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(skill)
    return deduped


def parse_frontmatter(content: str) -> Dict[str, Any]:
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


def normalize_skill_lifecycle_mode(mode: Optional[str]) -> str:
    """Normalize lifecycle mode with safe fallback."""
    normalized = str(mode or "").strip().lower()
    if normalized not in VALID_SKILL_LIFECYCLE_MODES:
        return "create_or_update"
    return normalized


def _split_skill_content(content: str) -> Tuple[Dict[str, Any], str]:
    """Split SKILL.md into frontmatter metadata and body text."""
    metadata = parse_frontmatter(content)
    match = re.match(r"^---\n(.*?)\n---\n?", content, re.DOTALL)
    body = content[match.end() :] if match else content
    return metadata, body.strip()


def _build_skill_content(metadata: Dict[str, Any], body: str) -> str:
    """Compose SKILL.md content from metadata and body."""
    dumped = yaml.safe_dump(metadata, sort_keys=False, allow_unicode=False).strip()
    normalized_body = (body or "").strip()
    if normalized_body:
        return f"---\n{dumped}\n---\n{normalized_body}\n"
    return f"---\n{dumped}\n---\n"


def _tokenize_for_similarity(text: str) -> Set[str]:
    """Tokenize text for rough semantic overlap scoring."""
    return {token for token in re.split(r"[^a-z0-9]+", (text or "").lower()) if token}


def compute_skill_similarity(candidate: Dict[str, Any], existing: Dict[str, Any]) -> float:
    """Compute similarity score between two skill descriptors."""
    candidate_name = str(candidate.get("name", "") or "").strip().lower()
    existing_name = str(existing.get("name", "") or "").strip().lower()
    candidate_desc = str(candidate.get("description", "") or "").strip().lower()
    existing_desc = str(existing.get("description", "") or "").strip().lower()

    if not candidate_name or not existing_name:
        return 0.0

    name_ratio = SequenceMatcher(None, candidate_name, existing_name).ratio()
    desc_ratio = SequenceMatcher(None, candidate_desc, existing_desc).ratio() if candidate_desc and existing_desc else 0.0

    candidate_name_tokens = _tokenize_for_similarity(candidate_name)
    existing_name_tokens = _tokenize_for_similarity(existing_name)
    shared_name_tokens = candidate_name_tokens & existing_name_tokens
    name_jaccard = len(shared_name_tokens) / len(candidate_name_tokens | existing_name_tokens) if candidate_name_tokens and existing_name_tokens else 0.0

    candidate_tokens = _tokenize_for_similarity(f"{candidate_name} {candidate_desc}")
    existing_tokens = _tokenize_for_similarity(f"{existing_name} {existing_desc}")
    if candidate_tokens and existing_tokens:
        jaccard = len(candidate_tokens & existing_tokens) / len(candidate_tokens | existing_tokens)
    else:
        jaccard = 0.0

    score = (0.60 * name_ratio) + (0.15 * desc_ratio) + (0.15 * jaccard) + (0.10 * name_jaccard)
    if candidate_name in existing_name or existing_name in candidate_name:
        score = min(1.0, score + 0.1)
    elif shared_name_tokens:
        score = min(1.0, score + 0.08)
    return score


def find_best_skill_match(
    candidate: Dict[str, Any],
    existing_skills: List[Dict[str, Any]],
    min_similarity: float = 0.68,
) -> Optional[Dict[str, Any]]:
    """Find best existing project skill match for candidate metadata."""
    best_match: Optional[Dict[str, Any]] = None
    best_score = 0.0
    for existing in existing_skills:
        score = compute_skill_similarity(candidate, existing)
        if score > best_score:
            best_score = score
            best_match = existing

    if best_match is None or best_score < min_similarity:
        return None
    return best_match


def _parse_skill_file(skill_file: Path) -> Tuple[Dict[str, Any], str]:
    """Load metadata + body from SKILL.md file."""
    content = skill_file.read_text(encoding="utf-8")
    return _split_skill_content(content)


def _coerce_list(value: Any) -> List[str]:
    """Normalize scalar or list metadata values into list[str]."""
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if value is None:
        return []
    text = str(value).strip()
    return [text] if text else []


def _merge_skill_files(target_skill_file: Path, source_skill_file: Path) -> None:
    """Merge source skill content into target skill file and preserve provenance."""
    target_meta, target_body = _parse_skill_file(target_skill_file)
    source_meta, source_body = _parse_skill_file(source_skill_file)

    source_name = str(source_meta.get("name", "") or source_skill_file.parent.name).strip()
    target_name = str(target_meta.get("name", "") or target_skill_file.parent.name).strip()
    if target_name:
        target_meta["name"] = target_name

    target_desc = str(target_meta.get("description", "") or "").strip()
    source_desc = str(source_meta.get("description", "") or "").strip()
    if source_desc and (not target_desc or len(source_desc) > len(target_desc)):
        target_meta["description"] = source_desc

    target_meta["evolving"] = True
    target_meta["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    origins: List[str] = []
    for item in (
        target_meta.get("massgen_origin"),
        source_meta.get("massgen_origin"),
        target_meta.get("origin"),
        source_meta.get("origin"),
    ):
        value = str(item or "").strip()
        if value and value not in origins:
            origins.append(value)

    if origins:
        target_meta["massgen_origin"] = origins[-1]
        target_meta["massgen_origins"] = origins

    merged_from = _coerce_list(target_meta.get("merged_from"))
    if source_name and source_name.lower() != target_name.lower() and source_name not in merged_from:
        merged_from.append(source_name)
    if merged_from:
        target_meta["merged_from"] = merged_from

    source_body = source_body.strip()
    if source_body and source_body not in target_body:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        section_title = f"## Evolving Updates ({stamp})"
        source_label = source_name or source_skill_file.parent.name
        addition = f"{section_title}\nSource Skill: {source_label}\n\n{source_body}"
        target_body = f"{target_body.rstrip()}\n\n{addition}".strip()

    target_skill_file.write_text(
        _build_skill_content(target_meta, target_body),
        encoding="utf-8",
    )


def _ensure_evolving_metadata(skill_file: Path, fallback_origin: Optional[str] = None) -> None:
    """Ensure minimal evolving metadata exists in skill frontmatter."""
    metadata, body = _parse_skill_file(skill_file)
    changed = False

    if metadata.get("evolving") is not True:
        metadata["evolving"] = True
        changed = True

    current_origin = str(metadata.get("massgen_origin", "") or "").strip()
    if not current_origin:
        origin = str(fallback_origin or "analysis").strip()
        if origin:
            metadata["massgen_origin"] = origin
            changed = True

    if changed:
        skill_file.write_text(_build_skill_content(metadata, body), encoding="utf-8")


def apply_analysis_skill_lifecycle(
    source_skill_dir: Path,
    project_skills_root: Path,
    lifecycle_mode: str = "create_or_update",
    preexisting_skill_dirs: Optional[Set[str]] = None,
    min_similarity: float = 0.68,
) -> Dict[str, Any]:
    """Apply analysis lifecycle mode for one source skill directory."""
    mode = normalize_skill_lifecycle_mode(lifecycle_mode)
    skill_file = source_skill_dir / "SKILL.md"
    if not skill_file.exists():
        return {"action": "skipped", "reason": "missing_skill_file"}

    project_skills_root.mkdir(parents=True, exist_ok=True)

    source_meta, _ = _parse_skill_file(skill_file)
    source_name = str(source_meta.get("name", "") or source_skill_dir.name).strip() or source_skill_dir.name
    source_origin = str(source_meta.get("massgen_origin", "") or "").strip() or str(source_meta.get("origin", "") or "").strip() or "analysis"

    preexisting = preexisting_skill_dirs or set()
    source_dirname = source_skill_dir.name
    dest_dir = project_skills_root / source_dirname

    if mode == "create_new":
        if source_dirname in preexisting:
            return {"action": "skipped", "reason": "preexisting_snapshot", "name": source_name}
        if dest_dir.exists():
            return {"action": "skipped", "reason": "already_exists", "name": source_name}

        shutil.copytree(str(source_skill_dir), str(dest_dir))
        _ensure_evolving_metadata(dest_dir / "SKILL.md", fallback_origin=source_origin)
        return {"action": "created", "target": str(dest_dir), "name": source_name}

    # create_or_update / consolidate: prefer same directory target when available.
    if dest_dir.exists() and (dest_dir / "SKILL.md").exists():
        _merge_skill_files(dest_dir / "SKILL.md", skill_file)
        return {"action": "updated", "target": str(dest_dir), "name": source_name}

    existing_skills = _scan_directory(project_skills_root, location="project")
    candidate = {
        "name": source_name,
        "description": str(source_meta.get("description", "") or ""),
    }
    best_match = find_best_skill_match(candidate, existing_skills, min_similarity=min_similarity)
    if best_match and best_match.get("source_path"):
        target_skill_file = Path(str(best_match["source_path"]))
        if target_skill_file.exists():
            _merge_skill_files(target_skill_file, skill_file)
            return {
                "action": "updated",
                "target": str(target_skill_file.parent),
                "name": source_name,
                "matched": str(best_match.get("name", "")),
            }

    shutil.copytree(str(source_skill_dir), str(dest_dir))
    _ensure_evolving_metadata(dest_dir / "SKILL.md", fallback_origin=source_origin)
    return {"action": "created", "target": str(dest_dir), "name": source_name}


def _archive_skill_directory(skill_dir: Path, archive_root: Path) -> Path:
    """Move merged skill directory into archive folder."""
    archive_root.mkdir(parents=True, exist_ok=True)
    destination = archive_root / skill_dir.name
    if destination.exists():
        suffix = datetime.now(timezone.utc).strftime("%H%M%S")
        destination = archive_root / f"{skill_dir.name}_{suffix}"
    shutil.move(str(skill_dir), str(destination))
    return destination


def consolidate_project_skills(
    project_skills_root: Path,
    min_similarity: float = 0.86,
) -> List[Dict[str, str]]:
    """Consolidate similar project skills by merging and archiving duplicates."""
    if not project_skills_root.exists():
        return []

    merged: List[Dict[str, str]] = []
    merged_dirs: Set[Path] = set()
    archive_batch = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_root = project_skills_root / "_archive" / archive_batch

    # Re-scan each loop since merges/archives mutate the directory set.
    while True:
        skills = sorted(
            _scan_directory(project_skills_root, location="project"),
            key=lambda item: str(item.get("name", "")).lower(),
        )
        candidates = [item for item in skills if item.get("source_path")]
        found_pair = False

        for i, left in enumerate(candidates):
            left_path = Path(str(left.get("source_path", ""))).parent
            if left_path in merged_dirs or not left_path.exists():
                continue
            for right in candidates[i + 1 :]:
                right_path = Path(str(right.get("source_path", ""))).parent
                if right_path in merged_dirs or not right_path.exists():
                    continue

                score = compute_skill_similarity(left, right)
                if score < min_similarity:
                    continue

                # Keep lexicographically-first directory as canonical target.
                target_path, source_path = sorted([left_path, right_path], key=lambda p: str(p).lower())
                target_skill_file = target_path / "SKILL.md"
                source_skill_file = source_path / "SKILL.md"
                if not (target_skill_file.exists() and source_skill_file.exists()):
                    continue

                _merge_skill_files(target_skill_file, source_skill_file)
                archived_to = _archive_skill_directory(source_path, archive_root)

                merged.append(
                    {
                        "target": str(target_path),
                        "source": str(source_path),
                        "archived_to": str(archived_to),
                    },
                )
                merged_dirs.add(source_path)
                found_pair = True
                break
            if found_pair:
                break

        if not found_pair:
            break

    return merged
