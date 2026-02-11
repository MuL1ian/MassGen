# Documentation Requirements

Documentation must be **consistent with implementation**, **concise**, and **usable**.

## What to Update (per PR)

| Change Type | Required Documentation |
|-------------|----------------------|
| New features | `docs/source/user_guide/` RST with runnable commands and expected output |
| New YAML params | `docs/source/reference/yaml_schema.rst` |
| New models | `massgen/backend/capabilities.py` + `massgen/token_manager/token_manager.py` |
| Complex/architectural | Design doc in `docs/dev_notes/` with architecture diagrams |
| New config options | Example YAML in `massgen/configs/` |
| Breaking changes | Migration guide |

## What to Update (release PRs only)

For release PRs on `dev/v0.1.X` branches (e.g., `dev/v0.1.33`):
- `README.md` - Recent Achievements section
- `CHANGELOG.md` - Full release notes

## Documentation Quality Standards

**Consistency**: Parameter names, file paths, and behavior descriptions must match actual code. Flag any discrepancies.

**Usability**:
- Include runnable commands users can try immediately
- Provide architecture diagrams for complex features
- Show expected output so users know what to expect

**Conciseness**:
- Avoid bloated prose and over-documentation
- One clear explanation beats multiple redundant ones
- Remove filler text and unnecessary verbosity

## File Locations

- **Internal** (not published): `docs/dev_notes/[feature-name]_design.md`
- **User guides**: `docs/source/user_guide/`
- **Reference**: `docs/source/reference/`
- **API docs**: Auto-generate from Google-style docstrings
