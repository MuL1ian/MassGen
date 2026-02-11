# CodeRabbit Integration

This project uses CodeRabbit for automated PR reviews. Configuration: `.coderabbit.yaml`

## Claude Code CLI Integration

CodeRabbit integrates directly with Claude Code via CLI. After implementing a feature, run:

```bash
coderabbit --prompt-only
```

This provides token-efficient review output. Claude Code will create a task list from detected issues and can apply fixes systematically.

**Options**:
- `--type uncommitted` - Review only uncommitted changes
- `--type committed` - Review only committed changes
- `--base develop` - Specify comparison branch

**Workflow example**: Ask Claude to implement and review together:
> "Implement the new config option and then run coderabbit --prompt-only"

## PR Commands (GitHub/GitLab)

In PR comments:
- `@coderabbitai review` - Trigger incremental review
- `@coderabbitai resolve` - Mark all comments as resolved
- `@coderabbitai summary` - Regenerate PR summary

## Applying Suggestions

- **Committable suggestions**: Click "Commit suggestion" button on GitHub
- **Complex fixes**: Hand off to Claude Code or address manually
