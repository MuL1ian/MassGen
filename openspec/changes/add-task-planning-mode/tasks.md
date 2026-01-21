## 1. CLI & Config

- [x] 1.1 Add `--plan` and `--plan-depth` CLI arguments to `massgen/cli.py`
- [x] 1.2 Add `plan_depth` field to CoordinationConfig in `massgen/agent_config.py`
- [x] 1.3 CLI auto-adds cwd to `context_paths` when `--plan` is set
- [x] 1.4 CLI sets `broadcast="human"` when `--plan` is set
- [x] 1.5 Update config validator to validate `plan_depth` values

## 2. User Prompt Prefix

- [x] 2.1 Create `get_task_planning_prompt_prefix()` function
- [x] 2.2 Implement depth-specific instructions (shallow/medium/deep)
- [x] 2.3 Emphasize interactive questioning in prompt
- [x] 2.4 Prepend instructions to user question when `--plan` is set

## 3. Testing & Docs

- [x] 3.1 Create example config at `massgen/configs/planning/task_planning_example.yaml`
- [x] 3.2 Add integration test at `massgen/tests/test_task_planning_mode.py`
- [x] 3.3 Update CLI help text
- [ ] 3.4 Test manually with different depths
