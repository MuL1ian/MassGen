# -*- coding: utf-8 -*-
"""Tests for analysis skill lifecycle create/update/consolidate behaviors."""

from pathlib import Path

from massgen.filesystem_manager.skills_manager import (
    apply_analysis_skill_lifecycle,
    consolidate_project_skills,
    parse_frontmatter,
)


def _write_skill(
    skill_dir: Path,
    *,
    name: str,
    description: str,
    body: str,
    extra_meta: dict | None = None,
) -> None:
    skill_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "name": name,
        "description": description,
    }
    if extra_meta:
        metadata.update(extra_meta)

    lines = ["---"]
    for key, value in metadata.items():
        if isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {value}")
    lines.extend(["---", body])
    (skill_dir / "SKILL.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_create_or_update_updates_existing_similar_skill(tmp_path: Path) -> None:
    """create_or_update should merge content into an existing similar project skill."""
    project_skills = tmp_path / ".agent" / "skills"
    existing = project_skills / "poem-writing"
    source = tmp_path / "source" / "poem-workflow"

    _write_skill(
        existing,
        name="poem-writing",
        description="Write poems with constraints and rhyme",
        body="# Poem Writing\nUse iterative drafting.",
    )
    _write_skill(
        source,
        name="poem-writer",
        description="Workflow for writing constrained poems",
        body="# Poem Writer\nDraft then refine with meter checks.",
        extra_meta={"massgen_origin": "log_1::turn_1", "evolving": True},
    )

    result = apply_analysis_skill_lifecycle(
        source,
        project_skills,
        lifecycle_mode="create_or_update",
    )

    assert result["action"] == "updated"
    assert not (project_skills / "poem-workflow").exists()

    updated_content = (existing / "SKILL.md").read_text(encoding="utf-8")
    updated_meta = parse_frontmatter(updated_content)
    assert "Evolving Updates" in updated_content
    assert updated_meta.get("evolving") is True
    assert "poem-writer" in (updated_meta.get("merged_from") or [])


def test_create_new_keeps_existing_skill_and_creates_new_dir(tmp_path: Path) -> None:
    """create_new should always create a new project skill directory when possible."""
    project_skills = tmp_path / ".agent" / "skills"
    existing = project_skills / "poem-writing"
    source = tmp_path / "source" / "poem-workflow"

    _write_skill(
        existing,
        name="poem-writing",
        description="Write poems with constraints and rhyme",
        body="# Poem Writing\nUse iterative drafting.",
    )
    _write_skill(
        source,
        name="poem-writer",
        description="Workflow for writing constrained poems",
        body="# Poem Writer\nDraft then refine with meter checks.",
    )

    result = apply_analysis_skill_lifecycle(
        source,
        project_skills,
        lifecycle_mode="create_new",
    )

    assert result["action"] == "created"
    assert (project_skills / "poem-workflow" / "SKILL.md").exists()
    existing_content = (existing / "SKILL.md").read_text(encoding="utf-8")
    assert "Evolving Updates" not in existing_content


def test_consolidate_project_skills_merges_and_archives_similar_entries(tmp_path: Path) -> None:
    """Consolidation should merge very similar skills and archive superseded directories."""
    project_skills = tmp_path / ".agent" / "skills"
    skill_a = project_skills / "poem-writing"
    skill_b = project_skills / "poem-writer"

    _write_skill(
        skill_a,
        name="poem-writing",
        description="Write poems with constraints and rhyme",
        body="# Poem Writing\nUse iterative drafting.",
    )
    _write_skill(
        skill_b,
        name="poem-writer",
        description="Workflow for writing constrained poems",
        body="# Poem Writer\nDraft then refine with meter checks.",
    )

    merges = consolidate_project_skills(project_skills, min_similarity=0.60)

    assert merges
    active_count = int(skill_a.exists()) + int(skill_b.exists())
    assert active_count == 1

    archive_root = project_skills / "_archive"
    assert archive_root.exists()
    archived_skill_files = list(archive_root.glob("**/SKILL.md"))
    assert archived_skill_files
