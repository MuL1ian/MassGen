# MassGen v0.1.25 Roadmap

## Overview

Version 0.1.25 focuses on system reminders and improved agent broadcasting for more controlled multi-agent communication.

- **Add system reminders** (Required): 📋 Framework for injecting reminders mid-run during LLM streaming
- **Improve agent broadcasting so it only asks targeted questions and we can control the amount of detail it responds with** (Required): 🎯 Sensitivity-based scaling for broadcast response complexity

## Key Technical Priorities

1. **Add system reminders**: Framework for injecting system reminders mid-run during LLM streaming
   **Use Case**: Keep agents focused on key objectives and constraints throughout long conversations

2. **Improve agent broadcasting so it only asks targeted questions and we can control the amount of detail it responds with**: Enable scaling of broadcast responses based on configurable sensitivity levels
   **Use Case**: Enable adaptive agent responses with three-tier sensitivity configuration

## Key Milestones

### 🎯 Milestone 1: Add system reminders (REQUIRED)

**Goal**: Framework for injecting system reminders mid-run during LLM streaming

**Owner**: @ncrispino (nickcrispino on Discord)

**Issue**: [#557](https://github.com/massgen/MassGen/issues/557)

#### 1.1 Reminder Framework Design
- [ ] Design generic reminder injection framework
- [ ] Support context awareness reminders
- [ ] Support human feedback reminders
- [ ] Support safety and memory reminders

#### 1.2 Mid-Run Injection Mechanism
- [ ] Implement mid-run injection during LLM streaming (like tool calls)
- [ ] Implement reminder injection into conversation flow
- [ ] Generic and extensible design for flexible downstream usage
- [ ] Support reminder priorities and ordering

#### 1.3 Integration & Testing
- [ ] Unit tests for reminder system
- [ ] Integration tests with multi-turn conversations
- [ ] Performance testing for overhead
- [ ] Documentation and configuration examples

**Success Criteria**:
- ✅ System reminders can be injected mid-run during LLM streaming
- ✅ Framework supports context awareness, human feedback, safety, and memory reminders
- ✅ Design is generic and extensible for flexible downstream usage
- ✅ Documentation covers reminder framework and usage

---

### 🎯 Milestone 2: Improve agent broadcasting so it only asks targeted questions and we can control the amount of detail it responds with (REQUIRED)

**Goal**: Enable scaling of agent broadcast responses based on configurable sensitivity levels

**Owner**: @ncrispino (nickcrispino on Discord)

**Issue**: [#614](https://github.com/massgen/MassGen/issues/614)

#### 2.1 Sensitivity Configuration
- [ ] Implement configuration-based sensitivity levels (three tiers)
- [ ] Define scaling behavior for each sensitivity tier
- [ ] Support per-agent sensitivity overrides
- [ ] Document sensitivity level behaviors

#### 2.2 Response Complexity Scaling
- [ ] Dynamic response complexity that scales with sensitivity settings
- [ ] Targeted questioning that adapts to complexity configuration
- [ ] Support ranging from simple responses to complex implementations
- [ ] Allow per-broadcast sensitivity overrides

#### 2.3 Integration & Testing
- [ ] Unit tests for targeted broadcasting
- [ ] Integration tests with multi-agent workflows
- [ ] Performance testing for broadcast efficiency
- [ ] Documentation and usage examples

**Success Criteria**:
- ✅ Three-tier sensitivity levels are configurable
- ✅ Response complexity scales appropriately with sensitivity settings
- ✅ Targeted questioning adapts to complexity configuration
- ✅ Documentation covers sensitivity configuration and scaling behavior

---

## Success Criteria

### Functional Requirements

**System Reminders:**
- [ ] Mid-run injection during LLM streaming works
- [ ] Context awareness reminders function correctly
- [ ] Human feedback reminders function correctly
- [ ] Safety and memory reminders function correctly
- [ ] Framework is generic and extensible

**Improve Agent Broadcasting:**
- [ ] Three-tier sensitivity configuration works
- [ ] Response complexity scales with sensitivity
- [ ] Targeted questioning adapts to configuration
- [ ] Per-broadcast sensitivity overrides function
- [ ] Scaling behavior is documented and predictable

### Performance Requirements
- [ ] Reminder injection has minimal overhead
- [ ] Broadcasting latency is acceptable
- [ ] Memory usage is reasonable
- [ ] No degradation in coordination speed

### Quality Requirements
- [ ] All tests passing
- [ ] Comprehensive documentation
- [ ] Configuration examples provided
- [ ] Error handling is robust
- [ ] User-facing messages are clear

---

## Dependencies & Risks

### Dependencies
- **System Reminders**: Existing tool call injection mechanism, message template system, orchestrator infrastructure
- **Improve Agent Broadcasting**: Existing broadcast system (v0.1.18), shadow agent system (v0.1.22), coordination tracker

### Risks & Mitigations
1. **Reminder Timing**: *Mitigation*: Configurable intervals, testing with various conversation lengths
2. **Broadcasting Complexity**: *Mitigation*: Incremental implementation, backward compatibility with existing broadcast
3. **Performance Overhead**: *Mitigation*: Efficient injection, lazy evaluation where possible
4. **Configuration Complexity**: *Mitigation*: Sensible defaults, clear documentation, validation

---

## Future Enhancements (Post-v0.1.25)

### v0.1.26 Plans
- **Memory as Tools** (@ncrispino): Include memory (including filesystem) as callable tools for agents
- **Grok 4.1 Fast Model Support** (@praneeth999): Add support for xAI's Grok 4.1 Fast model

### v0.1.27 Plans
- **Clarify Code Execution in Docs** (@ncrispino): Improve documentation clarity for code execution features
- **Local Computer Use Models** (@franklinnwren): Add support for local vision models in computer use workflows

### Long-term Vision
- **Advanced Agent Communication**: Sophisticated inter-agent protocols and negotiation
- **Adaptive Context Management**: Dynamic context windows based on task requirements
- **Tool Marketplace**: User-contributed tools and integrations
- **Cost Analytics**: Detailed cost tracking and budget management

---

## Timeline Summary

| Phase | Focus | Key Deliverables | Owner | Priority |
|-------|-------|------------------|-------|----------|
| Phase 1 | Add system reminders | Reminder configuration, injection mechanism, documentation | @ncrispino | **REQUIRED** |
| Phase 2 | Improve agent broadcasting | Agent targeting, response detail control, documentation | @ncrispino | **REQUIRED** |

**Target Release**: December 15, 2025 (Monday @ 9am PT)

---

## Getting Started

### For Contributors

**Phase 1 - Add system reminders:**
1. Review reminder system design (Issue #557)
2. Implement reminder configuration schema
3. Build injection mechanism
4. Add periodic and conditional triggers
5. Add integration tests
6. Document configuration and usage

**Phase 2 - Improve agent broadcasting:**
1. Review broadcasting improvements (Issue #614)
2. Implement agent targeting
3. Add response detail configuration
4. Integrate with shadow agents
5. Add integration tests
6. Document broadcasting configuration

### For Users

- v0.1.25 brings system reminders and improved agent broadcasting:

  **Add system reminders:**
  - Framework for injecting reminders mid-run during LLM streaming
  - Keep agents focused on objectives
  - Support for context awareness, human feedback, safety, and memory reminders
  - Generic and extensible design
  - Flexible downstream usage

  **Improve agent broadcasting:**
  - Three-tier sensitivity configuration for broadcast responses
  - Dynamic response complexity that scales with sensitivity
  - Targeted questioning that adapts to configuration
  - Scaling from simple to complex implementations
  - Configurable sensitivity levels per broadcast

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup and workflow
- Code standards and testing requirements
- Pull request process
- Documentation guidelines

**Contact Track Owner:**
- Add system reminders & Improve agent broadcasting: @ncrispino on Discord (nickcrispino)

---

*This roadmap reflects v0.1.25 priorities focusing on system reminders and targeted agent broadcasting.*

**Last Updated:** December 12, 2025
**Maintained By:** MassGen Team
