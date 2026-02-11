# Release Workflow

## Automated (GitHub Actions)

| Trigger | Action | Workflow |
|---------|--------|----------|
| Git tag push | GitHub Release created | `auto-release.yml` |
| GitHub Release published | PyPI publish | `pypi-publish.yml` |
| Git tag push | Docker images built | `docker-publish.yml` |
| Git tag push | Docs validated | `release-docs-automation.yml` |

## Release Preparation

Use the `release-prep` skill to automate release documentation:

```bash
release-prep v0.1.34
```

This will:
1. Archive previous announcement -> `docs/announcements/archive/`
2. Generate CHANGELOG.md entry draft
3. Create `docs/announcements/current-release.md`
4. Validate documentation is updated
5. Check LinkedIn character count (~3000 limit)

## Announcement Files

```text
docs/announcements/
|-- feature-highlights.md    # Long-lived feature list (update for major features)
|-- current-release.md       # Active announcement (copy to LinkedIn/X)
+-- archive/                 # Past announcements
```

## Full Release Process

1. **Merge release PR** to main
2. **Run `release-prep v0.1.34`** - generates CHANGELOG, announcement
3. **Review and commit** announcement files
4. **Create git tag**: `git tag v0.1.34 && git push origin v0.1.34`
5. **Publish GitHub Release** - triggers PyPI publish automatically
6. **Post to LinkedIn/X** - copy from `docs/announcements/current-release.md` + `feature-highlights.md`
7. **Update links** in `current-release.md` after posting
