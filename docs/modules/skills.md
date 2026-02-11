# MassGen Skills

MassGen includes specialized skills in `massgen/skills/` for common workflows (log analysis, running experiments, creating configs, etc.).

## Enabling Skill Discovery

If MassGen skills aren't being discovered, symlink them to `.claude/skills/`:

```bash
mkdir -p .claude/skills
for skill in massgen/skills/*/; do
  ln -sf "../../$skill" ".claude/skills/$(basename "$skill")"
done

# Also symlink the skill-creator for creating new skills
ln -sf "../.agent/skills/skill-creator" ".claude/skills/skill-creator"
```

Once symlinked, Claude Code will automatically discover and use these skills when relevant.

## Creating New Skills

When you notice a repeatable workflow emerging (e.g., same sequence of steps done multiple times), suggest creating a new skill for it. Use the `skill-creator` skill to help structure and create new skills in `massgen/skills/`.

## Improving Existing Skills

After you finish a workflow using a skill, it is a good idea to improve it, especially if a human has guided you through new workflows or you found other errors or inefficiencies. You should edit the file in `massgen/skills/` to improve it and have the human approve it.
