# Testing Module

## Goal

Build a fully automated testing system for MassGen across:

- Core Python orchestration and backends
- TUI event/rendering behavior
- WebUI stores/components/E2E flows
- Integration and nightly real-provider checks

The target workflow is test-first: agree on tests with the user, implement tests, then implement code until tests pass.

## Baseline (Validated on 2026-02-06)

- `80` Python test files in `massgen/tests/`
- `200` `Test*` classes in `massgen/tests/`
- `29` xfail registry entries in `massgen/tests/xfail_registry.yml`
- `18` of those xfails are expired as of `2026-02-06`
- CI currently runs pre-commit checks, but does not run `pytest`
- No first-party WebUI test files in `webui/src/`
- No dedicated automated tests for `massgen/frontend/` TUI modules

## Testing Strategy

### P0: PR-Gated Fast Automation

1. Add `pytest` workflow in `.github/workflows/tests.yml` for every push/PR.
2. Keep expensive tests off by default (`RUN_EXPENSIVE=0`, `RUN_INTEGRATION=0`, `RUN_DOCKER=0`).
3. Add deterministic unit tests for:
   - `massgen/orchestrator.py`
   - `massgen/coordination_tracker.py`
   - `massgen/system_message_builder.py`
   - `massgen/mcp_tools/security.py`
4. Add TUI pipeline tests using:
   - `massgen/frontend/displays/timeline_event_recorder.py`
   - `massgen/frontend/displays/content_handlers.py`
   - `massgen/frontend/displays/content_processor.py`
5. Add WebUI tests (Vitest + Testing Library) for stores and critical components.

### P1: Deterministic UI Regression

1. TUI snapshot tests with `pytest-textual-snapshot`.
2. Golden transcript tests using `MASSGEN_TUI_TIMELINE_TRANSCRIPT`.
3. Playwright E2E for setup + coordination flows in WebUI.

### P2: Nightly Deep Validation

1. Nightly expensive tests against real providers.
2. Optional LLM-assisted visual/interaction checks for TUI and WebUI.

## TUI Testing Layers

1. Unit logic: `ToolBatchTracker`, helpers, normalization logic.
2. Event pipeline: `TimelineEventRecorder` with scripted `MassGenEvent` sequences.
3. Widget behavior: Textual `run_test(headless=True)` + Pilot.
4. Snapshot regression: SVG snapshots (`pytest-textual-snapshot`).
5. Transcript golden files: compare timeline structure instead of full text.

## WebUI Testing Layers

1. Store unit tests (`agentStore`, `wizardStore`, `workspaceStore`).
2. Utility tests (artifact detection, path normalization).
3. Component tests (cards, voting view, key workflow widgets).
4. Playwright E2E (setup gate, live coordination rendering, reconnect behavior).

## Recommended Package Baselines (2026 Refresh)

Python:

- `pytest` 9.x
- `pytest-asyncio` 1.3+
- `pytest-cov` 7.x
- `pytest-textual-snapshot` 1.1+
- `cairosvg` 2.8+ (optional, for SVG-to-PNG vision checks)

WebUI:

- `vitest` 4.x
- `@testing-library/react` 16.x
- `@testing-library/dom` (required peer for React Testing Library 16)
- `@testing-library/jest-dom` 6.9+
- `@testing-library/user-event` 14.x+
- `jsdom` 27.x
- `@playwright/test` 1.57+
- `msw` 2.12+

## LLM-Assisted Test Automation

WebUI:

- Prefer Playwright's native test agent workflow (`npx playwright init-agents`) for faster authoring, healing, and maintenance of E2E tests.

TUI:

- Keep deterministic tests as primary gate.
- Use LLM-driven terminal tools (`ht`, `agent-tui`) only as optional nightly evaluators, not PR gates.

## TDD Execution Contract

For non-trivial feature work, use this sequence:

1. Align with user on acceptance tests and failure conditions.
2. Implement or update tests first.
3. Run tests and confirm they fail for the intended reason.
4. Implement code until tests pass.
5. Keep tests committed as regression protection.

This contract applies to backend logic, TUI behavior, WebUI behavior, and integration workflows.

## Instruction File Parity Hook

`CLAUDE.md` and `AGENTS.md` must remain identical. This repo uses a pre-commit hook:

- Hook id: `sync-agent-instructions`
- Script: `scripts/precommit_sync_agent_instructions.py`
- Behavior:
  - If one file changes, sync it to the other.
  - If both files change differently, fail and require manual merge.

## Core Commands

```bash
# Fast local suite
uv run pytest massgen/tests -q --tb=short

# Integration/expensive (manual or nightly)
uv run pytest massgen/tests --run-integration --run-expensive -v

# WebUI unit tests (after setup)
cd webui && npm run test

# WebUI E2E (after setup)
cd webui && npx playwright test
```
