# MassGen v0.1.48 Roadmap

## Overview

Version 0.1.48 focuses on OpenAI native compression and enhanced log analysis capabilities.

- **OpenAI Responses /compact Endpoint** (Required): Use OpenAI's native `/compact` endpoint instead of custom summarization
- **Log Analysis Model Selector** (Required): Allow users to choose which model to use for log analysis

## Key Technical Priorities

1. **OpenAI /compact Endpoint Integration**: Leverage API-level context compression for better efficiency
   **Use Case**: Reduce token usage and improve response quality with native compression

2. **Log Analysis Model Selection**: Configurable model choice for `massgen logs analyze` self-analysis mode
   **Use Case**: Flexibility in choosing analysis model based on cost/quality tradeoffs

## Key Milestones

### Milestone 1: OpenAI Responses /compact Endpoint (REQUIRED)

**Goal**: Use OpenAI's native `/compact` endpoint instead of custom summarization

**Owner**: @ncrispino (nickcrispino on Discord)

**Issue**: [#739](https://github.com/massgen/MassGen/issues/739)

#### 1.1 Research & Design
- [ ] Review OpenAI's `/compact` endpoint documentation
- [ ] Understand request/response format differences
- [ ] Design integration with existing compression system
- [ ] Plan fallback strategy for non-OpenAI backends

#### 1.2 Backend Integration
- [ ] Update OpenAI backend to use `/compact` endpoint
- [ ] Implement request formatting for compact endpoint
- [ ] Handle response parsing and conversation continuation
- [ ] Add configuration flag for enabling/disabling compact mode

#### 1.3 Compression System Updates
- [ ] Refactor compression logic to conditionally use native endpoint
- [ ] Update streaming buffer handling for compact responses
- [ ] Ensure compatibility with reactive compression system
- [ ] Test with various context sizes and message histories

#### 1.4 Testing & Validation
- [ ] Test with long conversation histories
- [ ] Verify token savings compared to custom summarization
- [ ] Test multi-turn conversations with compression
- [ ] Benchmark performance and response quality

**Success Criteria**:
- OpenAI backend successfully uses `/compact` endpoint
- Token usage reduced compared to custom summarization
- Response quality maintained or improved
- Seamless integration with existing compression system

---

### Milestone 2: Add Model Selector for Log Analysis (REQUIRED)

**Goal**: Allow users to choose which model to use for `massgen logs analyze` self-analysis mode

**Owner**: @ncrispino (nickcrispino on Discord)

**Issue**: [#766](https://github.com/massgen/MassGen/issues/766)

#### 2.1 CLI Interface Design
- [ ] Design `--model` parameter for `massgen logs analyze`
- [ ] Support model specification in standard format (provider/model)
- [ ] Add default model selection logic
- [ ] Design help text and examples

#### 2.2 Backend Configuration
- [ ] Parse model string into backend configuration
- [ ] Validate model availability and compatibility
- [ ] Handle API key requirements for different providers
- [ ] Support environment variable-based defaults

#### 2.3 Integration with Log Analysis
- [ ] Pass selected model to log analysis workflow
- [ ] Update analysis prompt for different model capabilities
- [ ] Handle model-specific response formats
- [ ] Test with various model types (Claude, GPT, Gemini)

#### 2.4 Testing & Documentation
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

## Timeline

**Target Release**: February 7, 2026

### Phase 1 (Feb 5-6)
- Research & Design (Milestone 1.1)
- Backend Integration (Milestone 1.2)
- CLI Interface Design (Milestone 2.1)

### Phase 2 (Feb 6-7)
- Compression System Updates (Milestone 1.3)
- Backend Configuration (Milestone 2.2)
- Integration with Log Analysis (Milestone 2.3)

### Phase 3 (Feb 7)
- Testing & Validation (Milestone 1.4, 2.4)
- Documentation updates
- Bug fixes and polish

---

## Success Metrics

- **Token Efficiency**: Measurable reduction in token usage with `/compact` endpoint
- **Analysis Quality**: Improved or maintained log analysis quality with model selection
- **User Experience**: Clear, intuitive model selection interface
- **Compatibility**: Seamless integration with existing compression and analysis workflows

---

## Resources

- **Issue #739**: [OpenAI Responses /compact Endpoint](https://github.com/massgen/MassGen/issues/739)
- **Issue #766**: [Add Model Selector for Log Analysis](https://github.com/massgen/MassGen/issues/766)
- **Owner**: @ncrispino (nickcrispino on Discord)
- **Related PRs**: TBD
- **Documentation**: Updates to `docs/source/reference/cli.rst` for model selector

---

## Related Tracks

This release builds on previous work:
- **v0.1.33**: Reactive Context Compression (#617, #697)
- **v0.1.35**: Enhanced logging with `massgen logs analyze` (#683, #761)

And sets the foundation for:
- **v0.1.49**: Refactor ask_others for targeted queries (#809)
- **v0.1.50**: TUI screenshot support (#831)
