## 1. Mode State and Mode Bar
- [ ] 1.1 Extend `TuiModeState.plan_mode` to support `analysis`
- [ ] 1.2 Add analysis configuration state (profile, target log/turn, session skill selection)
- [ ] 1.3 Update mode bar plan toggle cycle and labels to include analysis
- [ ] 1.4 Update Shift+Tab handler to cycle through analysis mode

## 2. Analysis Popover
- [ ] 2.1 Extend `PlanOptionsPopover` to render analysis controls
- [ ] 2.2 Add analysis events (profile changed, target changed, view report, open skills)
- [ ] 2.3 Wire popover events in `TextualApp` handlers
- [ ] 2.4 Keep existing plan/execute popover behavior unchanged

## 3. Skills UX
- [ ] 3.1 Add skills management modal for Default vs Created skill grouping
- [ ] 3.2 Add session-only toggle behavior for discovered skills
- [ ] 3.3 Add slash-command and/or quick-key entry point for skills modal
- [ ] 3.4 Pass selected skill filter into runtime config for system prompt filtering

## 4. Analysis Runtime Integration
- [ ] 4.1 Add analysis prompt prefix builder for dev/user profiles
- [ ] 4.2 Apply analysis mode runtime overrides in textual CLI turn execution
- [ ] 4.3 Default analysis target to current session latest turn
- [ ] 4.4 Add "view ANALYSIS_REPORT.md" flow from popover

## 5. User Profile Skill Creation
- [ ] 5.1 Detect skill draft blocks in user-profile analysis output
- [ ] 5.2 Add confirmation modal before writing skill files
- [ ] 5.3 Write approved skills into `.agent/skills/<name>/SKILL.md`

## 6. Tests and Validation
- [ ] 6.1 Extend `test_tui_modes.py` for analysis mode summary/cycle behavior
- [ ] 6.2 Add tests for analysis prompt/profile behavior and skill filtering hooks
- [ ] 6.3 Run targeted pytest for modified areas
- [ ] 6.4 Run `openspec validate add-tui-log-analysis-skill-mode --strict`
