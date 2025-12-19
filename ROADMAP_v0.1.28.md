# MassGen v0.1.28 Roadmap

## Overview

Version 0.1.28 focuses on system reminders and memory as callable tools for enhanced agent control.

- **Add system reminders** (Required): Framework for injecting reminders mid-run during LLM streaming
- **Memory as Tools** (Required): Include memory (including filesystem) as callable tools for agents

## Key Technical Priorities

1. **Add system reminders**: Framework for injecting system reminders mid-run during LLM streaming
   **Use Case**: Keep agents focused on key objectives and constraints throughout long conversations

2. **Memory as Tools**: Include memory (including filesystem) as callable tools for agents
   **Use Case**: Enable agents to have explicit control over memory operations

## Key Milestones

### Milestone 1: Add system reminders (REQUIRED)

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
- System reminders can be injected mid-run during LLM streaming
- Framework supports context awareness, human feedback, safety, and memory reminders
- Design is generic and extensible for flexible downstream usage
- Documentation covers reminder framework and usage

---

### Milestone 2: Memory as Tools (REQUIRED)

**Goal**: Include memory (including filesystem) as callable tools for agents

**Owner**: @ncrispino (nickcrispino on Discord)

**Issue**: [#461](https://github.com/massgen/MassGen/issues/461)

#### 2.1 Memory Tool Interface
- [ ] Design unified memory tool interface or harden existing cli tools

#### 2.2 Tool Integration
- [ ] Integrate memory tools with existing tool system
- [ ] Automatic tool schema generation
- [ ] Per-agent memory tool configuration
- [ ] Memory tool permissions and scoping

#### 2.3 Integration & Testing
- [ ] Unit tests for memory tools
- [ ] Integration tests with multi-agent workflows
- [ ] Performance testing for memory operations
- [ ] Documentation and usage examples

**Success Criteria**:
- Memory operations are available as callable tools
- Agents can explicitly store, retrieve, and search information
- Unified interface works with different memory backends
- Documentation covers memory tool configuration and usage

---

## Success Criteria

### Functional Requirements

**System Reminders:**
- [ ] Mid-run injection during LLM streaming works
- [ ] Context awareness reminders function correctly
- [ ] Human feedback reminders function correctly
- [ ] Safety and memory reminders function correctly
- [ ] Framework is generic and extensible

**Memory as Tools:**
- [ ] Memory store operation works as tool
- [ ] Memory retrieve operation works as tool
- [ ] Memory search operation works as tool
- [ ] Filesystem memory backend supported
- [ ] Vector store memory backend supported

### Performance Requirements
- [ ] Reminder injection has minimal overhead
- [ ] Memory tool operations are efficient
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
- **Memory as Tools**: Existing memory module (v0.1.5), tool system infrastructure, memory backends

### Risks & Mitigations
1. **Reminder Timing**: *Mitigation*: Configurable intervals, testing with various conversation lengths
2. **Memory Tool Complexity**: *Mitigation*: Start with simple operations, iterate based on feedback
3. **Performance Overhead**: *Mitigation*: Efficient injection, lazy evaluation where possible
4. **Configuration Complexity**: *Mitigation*: Sensible defaults, clear documentation, validation

---

## Future Enhancements (Post-v0.1.28)

### v0.1.29 Plans
- **Grok 4.1 Fast Model Support** (@praneeth999): Add support for xAI's Grok 4.1 Fast model ([#540](https://github.com/massgen/MassGen/issues/540))
- **Automatic Context Compression** (@ncrispino): Automatic context compression for long conversations ([#617](https://github.com/massgen/MassGen/issues/617))

### v0.1.30 Plans
- **OpenAI-Compatible Chat Server** (@ncrispino): Run MassGen as an OpenAI-compatible API server ([#628](https://github.com/massgen/MassGen/issues/628))

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
| Phase 2 | Memory as Tools | Memory tool interface, integration, documentation | @ncrispino | **REQUIRED** |

**Target Release**: December 22, 2025 (Monday @ 9am PT)

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

**Phase 2 - Memory as Tools:**
1. Review memory tools design (Issue #461)
2. Design unified memory tool interface
3. Implement store/retrieve/search tools
4. Integrate with existing tool system
5. Add integration tests
6. Document memory tool configuration

### For Users

- v0.1.28 brings system reminders and memory as tools:

  **Add system reminders:**
  - Framework for injecting reminders mid-run during LLM streaming
  - Keep agents focused on objectives
  - Support for context awareness, human feedback, safety, and memory reminders
  - Generic and extensible design
  - Flexible downstream usage

  **Memory as Tools:**
  - Memory operations as callable tools
  - Explicit store, retrieve, search operations
  - Unified interface for different memory backends
  - Agent-controlled memory management

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup and workflow
- Code standards and testing requirements
- Pull request process
- Documentation guidelines

**Contact Track Owner:**
- Add system reminders & Memory as Tools: @ncrispino on Discord (nickcrispino)

---

*This roadmap reflects v0.1.28 priorities focusing on system reminders and memory as callable tools.*

**Last Updated:** December 19, 2025
**Maintained By:** MassGen Team
