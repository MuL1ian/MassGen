# MassGen v0.1.32 Roadmap

## Overview

Version 0.1.32 focuses on backend model list auto-update and automatic context compression for enhanced provider support and longer conversations.

- **Backend Model List Auto-Update** (Required): Automatic model listing via provider APIs, third-party wrappers, or documented manual processes
- **Automatic Context Compression** (Required): Automatic context compression to manage long conversations efficiently

## Key Technical Priorities

1. **Backend Model List Auto-Update**: Implement native model listing APIs for providers that support it
   **Use Case**: Reduce manual model registry maintenance; OpenRouter already auto-fetches, extend to other providers

2. **Automatic Context Compression**: Automatic context compression to manage long conversations efficiently
   **Use Case**: Enable longer multi-turn conversations without losing important context

## Key Milestones

### Milestone 1: Backend Model List Auto-Update (REQUIRED)

**Goal**: Implement automatic model listing for providers, reducing manual registry maintenance

**Owner**: @ncrispino (nickcrispino on Discord)

**Issue**: [#645](https://github.com/massgen/MassGen/issues/645)

#### 1.1 Native API Implementation
- [ ] Implement model listing API for OpenAI
- [ ] Implement model listing API for Anthropic
- [ ] Implement model listing API for Grok
- [ ] Implement model listing API for Groq
- [ ] Implement model listing API for Nebius

#### 1.2 Third-Party Wrapper Research
- [ ] Research third-party wrappers for providers without native APIs
- [ ] Evaluate wrapper reliability and update frequency
- [ ] Implement wrapper integration where beneficial

#### 1.3 Documentation & Process
- [ ] Document manual update process for providers requiring it
- [ ] Create tracking system for new model releases
- [ ] Backend documentation noting update requirements

#### 1.4 Integration & Testing
- [ ] Unit tests for model listing APIs
- [ ] Integration tests with provider endpoints
- [ ] Fallback handling for API failures
- [ ] Documentation and configuration examples

**Success Criteria**:
- Providers with listing APIs auto-fetch available models
- Third-party wrapper integration for providers without native APIs
- Clear documentation for manually-updated providers
- Model registry stays current with minimal manual intervention

---

### Milestone 2: Automatic Context Compression (REQUIRED)

**Goal**: Automatic context compression to manage long conversations efficiently

**Owner**: @ncrispino (nickcrispino on Discord)

**Issue**: [#617](https://github.com/massgen/MassGen/issues/617)

#### 2.1 Compression Framework Design
- [ ] Design context compression architecture
- [ ] Implement compression threshold detection
- [ ] Support configurable compression strategies

#### 2.2 Summarization Implementation
- [ ] Implement intelligent conversation summarization
- [ ] Preserve essential context during compression
- [ ] Handle multi-agent conversation compression

#### 2.3 Configuration & Control
- [ ] Configurable compression thresholds
- [ ] Strategy selection (aggressive, balanced, conservative)
- [ ] Per-agent compression settings

#### 2.4 Integration & Testing
- [ ] Unit tests for compression logic
- [ ] Integration tests with long conversations
- [ ] Performance testing for compression overhead
- [ ] Documentation and configuration examples

**Success Criteria**:
- Context compression activates automatically when approaching limits
- Compressed context preserves essential conversation information
- Configurable thresholds and strategies
- Documentation covers compression configuration and usage

---

## Success Criteria

### Functional Requirements

**Backend Model List Auto-Update:**
- [ ] OpenAI models auto-fetched via API
- [ ] Anthropic models auto-fetched via API
- [ ] Grok models auto-fetched via API
- [ ] Groq models auto-fetched via API
- [ ] Nebius models auto-fetched via API
- [ ] Third-party wrappers integrated where needed
- [ ] Manual update documentation complete

**Automatic Context Compression:**
- [ ] Compression threshold detection works
- [ ] Summarization preserves key context
- [ ] Multi-agent compression handled correctly
- [ ] Configuration options available
- [ ] No loss of critical information

### Performance Requirements
- [ ] Model listing has minimal startup overhead
- [ ] Compression is efficient and fast
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
- **Backend Model List Auto-Update**: Provider API access, existing model registry, backend capabilities system
- **Automatic Context Compression**: Existing conversation history system, summarization capabilities, token counting

### Risks & Mitigations
1. **Provider API Changes**: *Mitigation*: Version detection, fallback to cached lists
2. **API Rate Limits**: *Mitigation*: Caching, background refresh, exponential backoff
3. **Compression Quality**: *Mitigation*: Configurable aggressiveness, preserve key markers
4. **Context Loss**: *Mitigation*: Selective compression, user-controllable settings

---

## Future Enhancements (Post-v0.1.32)

### v0.1.33 Plans
- **OpenAI-Compatible Chat Server** (@ncrispino): Run MassGen as an OpenAI-compatible API server ([#628](https://github.com/massgen/MassGen/issues/628))
- **Code-Based Tools in Web UI** (@ncrispino): Ensure code-based tools work in Web UI ([#612](https://github.com/massgen/MassGen/issues/612))

### v0.1.34 Plans
- **Test MassGen for PPTX Slides** (@ncrispino): Verify and improve PPTX generation capabilities ([#686](https://github.com/massgen/MassGen/issues/686))
- **OpenRouter Tool-Use Model Filtering** (@shubham2345): Restrict OpenRouter model list to tool-capable models ([#647](https://github.com/massgen/MassGen/issues/647))

### Long-term Vision
- **Advanced Agent Communication**: Sophisticated inter-agent protocols and negotiation
- **Adaptive Context Management**: Dynamic context windows based on task requirements
- **Tool Marketplace**: User-contributed tools and integrations
- **Cost Analytics**: Detailed cost tracking and budget management

---

## Timeline Summary

| Phase | Focus | Key Deliverables | Owner | Priority |
|-------|-------|------------------|-------|----------|
| Phase 1 | Backend Model List Auto-Update | Native APIs, third-party wrappers, documentation | @ncrispino | **REQUIRED** |
| Phase 2 | Automatic Context Compression | Compression framework, summarization, configuration | @ncrispino | **REQUIRED** |

**Target Release**: December 31, 2025 (Wednesday @ 9am PT)

---

## Getting Started

### For Contributors

**Phase 1 - Backend Model List Auto-Update:**
1. Review model listing design (Issue #645)
2. Implement provider-specific listing APIs
3. Research and integrate third-party wrappers
4. Document manual update processes
5. Add integration tests
6. Document configuration and usage

**Phase 2 - Automatic Context Compression:**
1. Review compression design (Issue #617)
2. Design compression threshold system
3. Implement summarization logic
4. Add configurable strategies
5. Add integration tests
6. Document compression configuration

### For Users

- v0.1.32 brings backend model auto-update and context compression:

  **Backend Model List Auto-Update:**
  - Automatic model listing from provider APIs
  - Extended coverage beyond OpenRouter
  - Third-party wrapper support
  - Clear documentation for manual updates
  - Reduced maintenance burden

  **Automatic Context Compression:**
  - Automatic compression for long conversations
  - Intelligent summarization preserving key context
  - Configurable thresholds and strategies
  - Multi-agent conversation support
  - Longer conversations without context overflow

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup and workflow
- Code standards and testing requirements
- Pull request process
- Documentation guidelines

**Contact Track Owner:**
- Backend Model List Auto-Update & Automatic Context Compression: @ncrispino on Discord (nickcrispino)

---

*This roadmap reflects v0.1.32 priorities focusing on backend model auto-update and automatic context compression.*

**Last Updated:** December 29, 2025
**Maintained By:** MassGen Team
