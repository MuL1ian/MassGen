# MassGen v0.1.51 Roadmap

## Overview

Version 0.1.51 focuses on worktree isolation improvements (pushed from v0.1.50) and targeted agent queries.

- **Git Worktree Isolation for Agent Changes** (Required): Worktree isolation improvements for agent file changes
- **Refactor ask_others for Targeted Agent Queries** (Required): Support targeted queries to specific agents

## Key Technical Priorities

1. **Git Worktree Isolation Improvements**: Enhanced worktree isolation for agent file changes
   **Use Case**: Safer agent file operations with improved isolation workflow

2. **Targeted Agent Queries**: Support targeted queries to specific agents via subagent spawning
   **Use Case**: More efficient coordination by querying specific agents rather than broadcasting to all

## Key Milestones

### Milestone 1: Git Worktree Isolation for Agent Changes (REQUIRED)

**Goal**: Improve worktree isolation for agent file changes

**Owner**: @ncrispino (nickcrispino on Discord)

**Issue**: [#853](https://github.com/massgen/MassGen/issues/853)

#### 1.1 Isolation Improvements
- [ ] Review current worktree isolation implementation from v0.1.48-v0.1.50
- [ ] Identify edge cases and improvement areas
- [ ] Implement fixes and enhancements

#### 1.2 Testing & Validation
- [ ] Test with various project structures
- [ ] Verify isolation works correctly across scenarios
- [ ] Update documentation if needed

**Success Criteria**:
- Worktree isolation handles edge cases correctly
- Agent file changes properly isolated and reviewed

---

### Milestone 2: Refactor ask_others for Targeted Agent Queries (REQUIRED)

**Goal**: Support targeted queries to specific agents via subagent spawning

**Owner**: @ncrispino (nickcrispino on Discord)

**Issue**: [#809](https://github.com/massgen/MassGen/issues/809)

#### 2.1 Targeted Query Implementation
- [ ] Implement `ask_others(target_agent_id="Agent-1", question="...")` mode
- [ ] Implement selective broadcast with `agent_prompts` dict
- [ ] Pass full `_streaming_buffer` to shadow agents for improved context

#### 2.2 Testing & Documentation
- [ ] Test all three modes: broadcast to all, selective broadcast, targeted ask
- [ ] Verify context passing via streaming buffer
- [ ] Document new query modes

**Success Criteria**:
- Targeted `ask_others` working for specific agent queries
- Selective broadcast with per-agent prompts functional
- Improved context passing via streaming buffer

---

## Timeline

**Target Release**: February 13, 2026

### Phase 1 (Feb 11-12)
- Worktree Isolation Improvements (Milestone 1)
- Targeted Query Implementation (Milestone 2.1)

### Phase 2 (Feb 12-13)
- Testing & Validation (Milestones 1.2, 2.2)

---

## Success Metrics

- **Isolation Reliability**: Worktree isolation handles all project structures correctly
- **Query Efficiency**: Targeted queries reduce unnecessary agent communication
- **Compatibility**: Seamless integration with existing coordination workflows

---

## Resources

- **Issue #853**: [Git Worktree Isolation for Agent Changes](https://github.com/massgen/MassGen/issues/853)
- **Issue #809**: [Refactor ask_others for Targeted Agent Queries](https://github.com/massgen/MassGen/issues/809)
- **Owner**: @ncrispino (nickcrispino on Discord)
- **Related PRs**: TBD

---

## Related Tracks

This release builds on previous work:
- **v0.1.48**: Worktree Isolation (#857), Decomposition Mode (#858)
- **v0.1.49**: Fairness Gate, Checklist Voting, Log Analysis TUI (#869)
- **v0.1.50**: Chunked Plan Execution (#877), Skill Lifecycle Management (#878)

And sets the foundation for:
- **v0.1.52**: Quickstart model curation (#840), TUI screenshot support (#831)
- **v0.1.53**: Per-agent isolated write contexts (#854), multi-turn round/log fixes (#848)
