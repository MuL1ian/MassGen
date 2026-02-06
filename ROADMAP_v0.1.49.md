# MassGen v0.1.49 Roadmap

## Overview

Version 0.1.49 focuses on enhanced log analysis capabilities and worktree isolation improvements.

- **Log Analysis Model Selector** (Required): Allow users to choose which model to use for log analysis
- **Git Worktree Isolation for Agent Changes** (Required): Worktree isolation improvements for agent file changes

## Key Technical Priorities

1. **Log Analysis Model Selection**: Configurable model choice for `massgen logs analyze` self-analysis mode
   **Use Case**: Flexibility in choosing analysis model based on cost/quality tradeoffs

2. **Git Worktree Isolation Improvements**: Enhanced worktree isolation for agent file changes
   **Use Case**: Safer agent file operations with improved isolation workflow

## Key Milestones

### Milestone 1: Add Model Selector for Log Analysis (REQUIRED)

**Goal**: Allow users to choose which model to use for `massgen logs analyze` self-analysis mode

**Owner**: @ncrispino (nickcrispino on Discord)

**Issue**: [#766](https://github.com/massgen/MassGen/issues/766)

#### 1.1 CLI Interface Design
- [ ] Design `--model` parameter for `massgen logs analyze`
- [ ] Support model specification in standard format (provider/model)
- [ ] Add default model selection logic
- [ ] Design help text and examples

#### 1.2 Backend Configuration
- [ ] Parse model string into backend configuration
- [ ] Validate model availability and compatibility
- [ ] Handle API key requirements for different providers
- [ ] Support environment variable-based defaults

#### 1.3 Integration with Log Analysis
- [ ] Pass selected model to log analysis workflow
- [ ] Update analysis prompt for different model capabilities
- [ ] Handle model-specific response formats
- [ ] Test with various model types (Claude, GPT, Gemini)

#### 1.4 Testing & Documentation
- [ ] Test with multiple providers (OpenAI, Anthropic, Google)
- [ ] Verify cost and quality tradeoffs
- [ ] Document model selection options
- [ ] Add usage examples to CLI help

**Success Criteria**:
- Users can specify model via `--model` flag
- Analysis works across different providers
- Clear documentation and examples
- Proper error handling for invalid models

---

### Milestone 2: Git Worktree Isolation for Agent Changes (REQUIRED)

**Goal**: Improve worktree isolation for agent file changes

**Owner**: @ncrispino (nickcrispino on Discord)

**Issue**: [#853](https://github.com/massgen/MassGen/issues/853)

#### 2.1 Isolation Improvements
- [ ] Review current worktree isolation implementation from v0.1.48
- [ ] Identify edge cases and improvement areas
- [ ] Implement fixes and enhancements

#### 2.2 Testing & Validation
- [ ] Test with various project structures
- [ ] Verify isolation works correctly across scenarios
- [ ] Update documentation if needed

**Success Criteria**:
- Worktree isolation handles edge cases correctly
- Agent file changes properly isolated and reviewed

---

## Timeline

**Target Release**: February 9, 2026

### Phase 1 (Feb 7-8)
- CLI Interface Design (Milestone 1.1)
- Backend Configuration (Milestone 1.2)
- Isolation Improvements (Milestone 2.1)

### Phase 2 (Feb 8-9)
- Integration with Log Analysis (Milestone 1.3)
- Testing & Validation (Milestone 1.4, 2.2)

---

## Success Metrics

- **Analysis Quality**: Improved or maintained log analysis quality with model selection
- **User Experience**: Clear, intuitive model selection interface
- **Isolation Reliability**: Worktree isolation handles all project structures correctly
- **Compatibility**: Seamless integration with existing analysis workflows

---

## Resources

- **Issue #766**: [Add Model Selector for Log Analysis](https://github.com/massgen/MassGen/issues/766)
- **Issue #853**: [Git Worktree Isolation for Agent Changes](https://github.com/massgen/MassGen/issues/853)
- **Owner**: @ncrispino (nickcrispino on Discord)
- **Related PRs**: TBD
- **Documentation**: Updates to `docs/source/reference/cli.rst` for model selector

---

## Related Tracks

This release builds on previous work:
- **v0.1.35**: Enhanced logging with `massgen logs analyze` (#683, #761)
- **v0.1.48**: OpenAI Responses /compact Endpoint (#739), Decomposition Mode (#858), Worktree Isolation (#857)

And sets the foundation for:
- **v0.1.50**: Refactor ask_others for targeted queries (#809), curated quickstart models (#840)
- **v0.1.51**: TUI screenshot support (#831), multi-turn round/log fixes (#848)
