# MassGen v0.1.41 Roadmap

## Overview

Version 0.1.41 focuses on OpenAI Responses API improvements and log analysis model selection.

- **OpenAI Responses /compact Endpoint** (Required): Use OpenAI's native `/compact` endpoint instead of custom summarization
- **Add Model Selector for Log Analysis** (Required): Choose model for `massgen logs analyze` self-analysis mode

## Key Technical Priorities

1. **OpenAI Responses /compact Endpoint**: Leverage API-level context compression for better efficiency
   **Use Case**: Reduce token usage and improve response quality with native compression

2. **Add Model Selector for Log Analysis**: Allow users to choose which model to use for log analysis
   **Use Case**: Flexibility in choosing analysis model based on cost/quality tradeoffs

## Key Milestones

### Milestone 1: OpenAI Responses /compact Endpoint (REQUIRED)

**Goal**: Use OpenAI's native `/compact` endpoint instead of custom summarization

**Owner**: @ncrispino (nickcrispino on Discord)

**Issue**: [#739](https://github.com/massgen/MassGen/issues/739)

#### 1.1 Compact Endpoint Integration
- [ ] Research OpenAI `/compact` endpoint API
- [ ] Implement compact endpoint client
- [ ] Replace custom summarization with native endpoint
- [ ] Handle fallback for non-OpenAI backends

#### 1.2 Context Compression
- [ ] Integrate with existing context management
- [ ] Configure compression thresholds
- [ ] Test with long conversations
- [ ] Measure token savings

#### 1.3 Testing & Validation
- [ ] Unit tests for compact endpoint
- [ ] Integration tests with orchestration
- [ ] Performance benchmarks vs custom summarization
- [ ] Edge case handling

**Success Criteria**:
- OpenAI compact endpoint integrated successfully
- Token usage reduced compared to custom summarization
- Response quality maintained or improved
- Fallback works for non-OpenAI backends

---

### Milestone 2: Add Model Selector for Log Analysis (REQUIRED)

**Goal**: Allow users to choose which model to use for `massgen logs analyze` self-analysis mode

**Owner**: @ncrispino (nickcrispino on Discord)

**Issue**: [#766](https://github.com/massgen/MassGen/issues/766)

#### 2.1 Model Selection UI
- [ ] Add `--model` flag to `massgen logs analyze` command
- [ ] Implement model selection logic
- [ ] Support all available backend models
- [ ] Provide sensible defaults (e.g., GPT-4o-mini, Claude Haiku)

#### 2.2 Configuration Support
- [ ] Allow model selection via config file
- [ ] Document available model options
- [ ] Add model validation and error handling

#### 2.3 Testing & Documentation
- [ ] Test with different models (GPT, Claude, Gemini)
- [ ] Measure analysis quality across models
- [ ] Update documentation with usage examples
- [ ] Document cost/quality tradeoffs

**Success Criteria**:
- Model selector integrated successfully
- Works with all major backends (OpenAI, Claude, Gemini)
- Clear documentation on model selection
- Sensible default model chosen

---

## Success Criteria

### Functional Requirements

**OpenAI Responses /compact Endpoint:**
- [ ] Compact endpoint integrated
- [ ] Token savings measured and documented
- [ ] Fallback for non-OpenAI backends works
- [ ] No regression in response quality

**Add Model Selector for Log Analysis:**
- [ ] Model selector integrated in `massgen logs analyze`
- [ ] Works with all major backends
- [ ] Documentation complete with usage examples
- [ ] Default model selection is sensible

### Performance Requirements
- [ ] Token usage reduced with compact endpoint
- [ ] No performance degradation in existing workflows
- [ ] Model selector has minimal overhead

### Quality Requirements
- [ ] All tests passing
- [ ] Comprehensive documentation
- [ ] Error handling is robust
- [ ] User-facing messages are clear

---

## Dependencies & Risks

### Dependencies
- **OpenAI Compact Endpoint**: OpenAI API access, Responses API support
- **Model Selector**: Existing `massgen logs analyze` command, backend model registry

### Risks & Mitigations
1. **API Changes**: *Mitigation*: Monitor OpenAI API updates, implement version checks
2. **Backend Compatibility**: *Mitigation*: Implement proper fallback for non-OpenAI backends
3. **Model Selection Confusion**: *Mitigation*: Provide clear documentation and sensible defaults

---

## Future Enhancements (Post-v0.1.41)

### v0.1.42 Plans
- **Improve Log Sharing and Analysis**: Enhanced log sharing workflows ([#722](https://github.com/massgen/MassGen/issues/722))
- **Claude Code Plugin for MassGen Agents**: Plugin for spawning MassGen agents from Claude Code interface ([#773](https://github.com/massgen/MassGen/issues/773))

### Long-term Vision
- **Advanced Agent Communication**: Sophisticated inter-agent protocols and negotiation
- **Adaptive Context Management**: Dynamic context windows based on task requirements
- **Tool Marketplace**: User-contributed tools and integrations
- **Cost Analytics**: Detailed cost tracking and budget management

---

## Timeline Summary

| Phase | Focus | Key Deliverables | Owner | Priority |
|-------|-------|------------------|-------|----------|
| Phase 1 | OpenAI Compact Endpoint | API integration, token savings | @ncrispino | **REQUIRED** |
| Phase 2 | Model Selector for Log Analysis | CLI flag, model selection logic | @ncrispino | **REQUIRED** |

**Target Release**: January 21, 2026

---

## Getting Started

### For Contributors

**OpenAI Responses /compact Endpoint:**
1. Review OpenAI Responses API documentation
2. Implement compact endpoint integration
3. Add fallback for non-OpenAI backends
4. Test with various conversation lengths
5. Benchmark token savings

**Add Model Selector for Log Analysis:**
1. Review existing `massgen logs analyze` command
2. Implement `--model` flag with argparse
3. Add model validation logic
4. Test with different backend models
5. Document usage and cost/quality tradeoffs

### For Users

- v0.1.41 brings API improvements and enhanced log analysis:

  **OpenAI Responses /compact Endpoint:**
  - Native context compression via OpenAI API
  - Reduced token usage
  - Better response quality

  **Model Selector for Log Analysis:**
  - Choose which model to use for log analysis
  - Balance cost vs quality based on your needs
  - Use `massgen logs analyze --model <model-name>` to specify model

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup and workflow
- Code standards and testing requirements
- Pull request process
- Documentation guidelines

**Contact Track Owner:**
- OpenAI Compact Endpoint: @ncrispino on Discord (nickcrispino)
- Model Selector for Log Analysis: @ncrispino on Discord (nickcrispino)

---

*This roadmap reflects v0.1.41 priorities focusing on OpenAI compact endpoint integration and log analysis model selection.*

**Last Updated:** January 20, 2026
**Maintained By:** MassGen Team
