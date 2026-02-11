---
name: skill-organizer
description: Analyze, reorganize, and catalog all installed skills. Merges overlapping skills, restructures the filesystem hierarchy, and generates a compact SKILL_REGISTRY.md routing guide for system prompts.
---

# Skill Organizer

Reads all installed skills, identifies overlaps and confusability, merges where
appropriate, and produces a compact `SKILL_REGISTRY.md` that serves as a routing
guide in agent system prompts.

## Why This Exists

Models have a skill selection capacity (kappa) of approximately 50-100 items.
Beyond that, selection accuracy degrades. As skills accumulate through log analysis
and manual creation, the skill library can cross this threshold. This skill
keeps the library organized and the routing guide compact.

Reference: [Scaling LLM Agents with Skill Libraries](https://arxiv.org/pdf/2601.04748v2)

## Workflow

### Step 1: Inventory

List all skill directories in the .agent/skills/ folder.

Then read each skill's SKILL.md to understand scope, quality, and overlap.
Each skill lives in a subdirectory of .agent/skills/ with a SKILL.md file.

### Step 2: Identify overlapping or confusable skills

Look for:
- Skills that do the same thing with slightly different names
- Skills whose scopes significantly overlap (one is a subset of another)
- Skills that could be combined into a single broader skill with multiple sections
- Near-duplicate skills created from different log analysis sessions

### Step 3: Merge into hierarchical parent skills

For each group of overlapping or related skills, create a single **parent skill**
with sections covering each sub-capability:

1. Choose a broader parent name and directory (e.g., `web-app-dev` instead of
   separate `react-frontend`, `nodejs-backend`, `web-testing`)
2. Write one comprehensive SKILL.md with clearly labeled sections for each
   sub-capability. Each section should be self-contained enough that an agent
   can read just that section for a focused task.
3. Move bundled resources (templates, examples, configs) from merged skills
   into subdirectories of the parent skill directory.
4. Remove the redundant skill directories.

When merging, prefer the skill with:
- Better-quality instructions and examples
- More complete bundled resources
- A more descriptive, general name

The goal is fewer, richer skills — a parent skill with 4 well-written sections
is better than 4 separate shallow skills.

### Step 4: Generate SKILL_REGISTRY.md

Write `.agent/skills/SKILL_REGISTRY.md` as a compact routing guide:

```markdown
# Skill Registry

## <Category> (<count>)

- **skill-name**: What it does in one sentence.
  Use when: <trigger condition — when should the agent read this skill?>
  Sections: <comma-separated list of sections/sub-capabilities within the skill>

- **skill-name**: What it does in one sentence.
  Use when: <trigger condition>

## Recently Added
- **new-skill** (project): Frontmatter description — not yet categorized
```

The registry should:
- Group skills by purpose/domain (not alphabetically)
- For each skill, include: what it does, when to read it, and what sections it contains
- The "Use when" line is critical — it tells agents when to load the full SKILL.md
- The "Sections" line (when applicable) shows what sub-capabilities live inside the skill
- Stay under 50 entries total (merge aggressively if needed)
- Include a "Recently Added" section for skills created since last organization
- NOT duplicate full skill content, just enough for selection routing

### Step 5: Report

Summarize what you did:
- How many skills were found
- Which skills were merged (old names -> new name)
- Which skills were kept as-is
- The final registry structure

## Constraints

- Do NOT use keyword matching, Jaccard similarity, or heuristic categorization.
  Use your understanding of what each skill does.
- Be aggressive about merging: fewer high-quality skills beats many overlapping ones.
- Preserve all bundled resources (templates, examples, configs) during merges.
- The SKILL_REGISTRY.md is a routing guide, not documentation. Keep it concise.
- Skills in `massgen/skills/` (builtin) should not be merged or deleted, only
  cataloged in the registry.
