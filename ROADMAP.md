# MassGen Roadmap

**Current Version:** v0.1.23

**Release Schedule:** Mondays, Wednesdays, Fridays @ 9am PT

**Last Updated:** December 10, 2025

This roadmap outlines MassGen's development priorities for upcoming releases. Each release focuses on specific capabilities with real-world use cases.

---

## 👥 Contributors & Contact

Want to contribute or collaborate on a specific track? Reach out to the track owners below:

| Track | GitHub | Discord |
|-------|--------|---------|
| Tool System Refactoring | [@qidanrui](https://github.com/qidanrui) | danrui2020 |
| Multimodal Support | [@qidanrui](https://github.com/qidanrui) | danrui2020 |
| General Interoperability | [@qidanrui](https://github.com/qidanrui) | danrui2020 |
| RL Integration | [@qidanrui](https://github.com/qidanrui) [@praneeth999](https://github.com/praneeth999) | danrui2020, ram2561 |
| Agent Adapter System | [@Eric-Shang](https://github.com/Eric-Shang) | ericshang. |
| Framework Streaming | [@Eric-Shang](https://github.com/Eric-Shang) | ericshang. |
| Irreversible Actions Safety | [@franklinnwren](https://github.com/franklinnwren) | zhichengren |
| Computer Use | [@franklinnwren](https://github.com/franklinnwren) | zhichengren |
| Memory Module | [@qidanrui](https://github.com/qidanrui) [@ncrispino](https://github.com/ncrispino) | danrui2020, nickcrispino |
| Rate Limiting System | [@AbhimanyuAryan](https://github.com/AbhimanyuAryan) | abhimanyuaryan |
| DSPy Integration | [@praneeth999](https://github.com/praneeth999) | ram2561 |
| MassGen Handbook | [@a5507203](https://github.com/a5507203) [@Henry-811](https://github.com/Henry-811) | crinvo, henry_weiqi |
| Session Management | [@ncrispino](https://github.com/ncrispino) | nickcrispino |
| Automatic MCP Tool Selection | [@ncrispino](https://github.com/ncrispino) | nickcrispino |
| Parallel File Operations | [@ncrispino](https://github.com/ncrispino) | nickcrispino |
| MassGen Terminal Evaluation | [@ncrispino](https://github.com/ncrispino) | nickcrispino |
| Textual Terminal Display | [@praneeth999](https://github.com/praneeth999) | ram2561 |
| Web UI | [@voidcenter](https://github.com/voidcenter) | justin_zhang |

*For general questions, join the #massgen channel on [Discord](https://discord.gg/VVrT2rQaz5)*

---


| Release | Target | Feature | Owner | Use Case |
|---------|--------|---------|-------|----------|
| **v0.1.24** | 12/12/25 | Integrate RL into MassGen | @qidanrui @praneeth999 | Reinforcement learning integration for agent optimization and adaptive behavior |
| | | Smithery MCP Tools Support | @ncrispino | Expand MCP tools access through Smithery integration |
| **v0.1.25** | 12/15/25 | Memory as Tools | @ncrispino | Include memory (including filesystem) as callable tools for agents |
| | | Grok 4.1 Fast Model Support | @praneeth999 | Add support for xAI's Grok 4.1 Fast model for rapid agent responses |
| **v0.1.26** | 12/17/25 | Clarify Code Execution in Docs | @ncrispino | Improve documentation clarity for code execution features |
| | | Local Computer Use Models | @franklinnwren | Add support for local vision models in computer use workflows |

*All releases ship on MWF @ 9am PT when ready*

---

## 📋 v0.1.24 - RL Integration & MCP Ecosystem

### Features

**1. Integrate RL into MassGen** (@qidanrui, @praneeth999)
- Issue: [#527](https://github.com/massgen/MassGen/issues/527)
- Reinforcement learning integration for agent optimization
- Adaptive agent behavior based on feedback and outcomes
- Reward modeling for multi-agent coordination
- **Use Case**: Enable agents to learn and improve their performance over time through reinforcement learning

**2. Smithery MCP Tools Support** (@ncrispino)
- Issue: [#521](https://github.com/massgen/MassGen/issues/521)
- Integration with Smithery to expand available MCP tools
- Automatic discovery and installation of Smithery MCP servers
- **Use Case**: Expand MassGen's tool ecosystem by integrating with Smithery

### Success Criteria
- ✅ RL framework successfully integrates with MassGen architecture
- ✅ Smithery integration discovers and installs MCP tools automatically

---

## 📋 v0.1.25 - Memory as Tools & Grok 4.1 Fast

### Features

**1. Memory as Tools** (@ncrispino)
- Issue: [#461](https://github.com/massgen/MassGen/issues/461)
- Include memory (including filesystem) as callable tools for agents
- Agents can explicitly invoke memory operations via tool calls
- Unified interface for different memory backends
- **Use Case**: Enable agents to have explicit control over memory operations, allowing them to store, retrieve, and manage persistent information as tool calls

**2. Grok 4.1 Fast Model Support** (@praneeth999)
- Issue: [#540](https://github.com/massgen/MassGen/issues/540)
- Add support for xAI's Grok 4.1 Fast model
- Integration with existing Grok backend infrastructure
- Pricing and token counting configuration
- **Use Case**: Provide access to xAI's latest high-speed model for rapid agent responses

### Success Criteria
- ✅ Memory operations are available as callable tools
- ✅ Agents can explicitly store and retrieve information
- ✅ Grok 4.1 Fast model is accessible via configuration
- ✅ Token counting and pricing are accurate for Grok 4.1 Fast

---

## 📋 v0.1.26 - Code Execution Documentation & Local Computer Use

### Features

**1. Clarify Code Execution in Docs** (@ncrispino)
- Issue: [#573](https://github.com/massgen/MassGen/issues/573)
- Improve documentation clarity for code execution features
- Clear examples and usage patterns for code execution sandbox
- Best practices and security considerations
- **Use Case**: Help users understand and effectively use code execution capabilities

**2. Local Computer Use Models** (@franklinnwren)
- Issue: [#559](https://github.com/massgen/MassGen/issues/559)
- Add support for local vision models in computer use workflows
- Enable computer use without relying on cloud-based vision APIs
- Integration with local model serving infrastructure
- **Use Case**: Run computer use agents with local models for privacy, cost savings, and offline operation

### Success Criteria
- ✅ Code execution documentation is clear and comprehensive
- ✅ Users can follow guides to enable and use code execution
- ✅ Local vision models can be used for computer use tasks
- ✅ Documentation covers local model setup and configuration

---

## 🔨 Ongoing Work & Continuous Releases

These features are being actively developed on **separate parallel tracks** and will ship incrementally on the MWF release schedule:

### Track: Agent Adapter System (@Eric-Shang, ericshang.)
- PR: [#283](https://github.com/massgen/MassGen/pull/283)
- Unified agent interface for easier backend integration
- **Shipping:** Continuous improvements

### Track: Irreversible Actions Safety (@franklinnwren, zhichengren)
- Human-in-the-loop approval system for dangerous operations
- LLM-based tool risk detection
- **Target:** v0.1.3 and beyond

### Track: Multimodal Support (@qidanrui, danrui2020)
- PR: [#252](https://github.com/massgen/MassGen/pull/252)
- Image, audio, video processing across backends
- **Shipping:** Incremental improvements each release

### Track: Memory Module (@qidanrui, @ncrispino, danrui2020, nickcrispino)
- Issues: [#347](https://github.com/massgen/MassGen/issues/347), [#348](https://github.com/massgen/MassGen/issues/348)
- Short and long-term memory implementation with persistence
- **Status:** ✅ Completed in v0.1.5

### Track: Agent Task Planning (@ncrispino, nickcrispino)
- Agent task planning with dependency tracking
- **Status:** ✅ Completed in v0.1.7

### Track: Automation & Meta-Coordination (@ncrispino, nickcrispino)
- LLM agent automation with status tracking and silent execution
- MassGen running MassGen for self-improvement workflows
- **Status:** ✅ Completed in v0.1.8
- **Case Study:** Meta-level self-analysis demonstrating automation mode (`meta-self-analysis-automation-mode.md`)

### Track: DSPy Integration (@praneeth999, ram2561)
- Question paraphrasing for multi-agent diversity
- Semantic validation and caching system
- **Status:** ✅ Completed in v0.1.8

### Track: Framework Streaming (@Eric-Shang, ericshang.)
- PR: [#462](https://github.com/massgen/MassGen/pull/462)
- Real-time streaming for LangGraph and SmoLAgent intermediate steps
- Enhanced debugging and monitoring for external framework tools
- **Status:** ✅ Completed in v0.1.10

### Track: Rate Limiting System (@AbhimanyuAryan, abhimanyuaryan)
- PR: [#383](https://github.com/massgen/MassGen/pull/383)
- Multi-dimensional rate limiting for Gemini models
- Model-specific limits with sliding window tracking
- **Status:** ✅ Completed in v0.1.11

### Track: MassGen Handbook (@a5507203, @Henry-811, crinvo, henry_weiqi)
- Issue: [#387](https://github.com/massgen/MassGen/issues/387)
- Comprehensive user documentation and handbook at https://massgen.github.io/Handbook/
- Centralized policies and resources for development and research teams
- **Status:** ✅ Completed in v0.1.10

### Track: Computer Use (@franklinnwren, zhichengren)
- PR: [#402](https://github.com/massgen/MassGen/pull/402)
- Browser and desktop automation with OpenAI, Claude, and Gemini integration
- Visual perception through screenshot processing and action execution
- **Status:** ✅ Completed in v0.1.9

### Track: Session Management (@ncrispino, nickcrispino)
- PR: [#466](https://github.com/massgen/MassGen/pull/466)
- Complete session state tracking and restoration
- Resume previous MassGen conversations with full context
- **Status:** ✅ Completed in v0.1.9

### Track: Semtools & Serena Skills (@ncrispino, nickcrispino)
- PR: [#515](https://github.com/massgen/MassGen/pull/515)
- Semantic search capabilities via semtools (embedding-based similarity)
- Symbol-level code understanding via serena (LSP integration)
- Package as reusable skills within MassGen framework
- **Status:** ✅ Completed in v0.1.12

### Track: System Prompt Architecture (@ncrispino, nickcrispino)
- PR: [#515](https://github.com/massgen/MassGen/pull/515)
- Complete refactoring of system prompt assembly
- Hierarchical structure with improved LLM attention management
- Skills system local execution support
- **Status:** ✅ Completed in v0.1.12

### Track: Multi-Agent Computer Use (@franklinnwren, zhichengren)
- PR: [#513](https://github.com/massgen/MassGen/pull/513)
- Enhanced Gemini computer use with Docker integration
- Multi-agent coordination for computer automation
- VNC visualization and debugging support
- **Status:** ✅ Completed in v0.1.12

### Track: Code-Based Tools System / Automatic MCP Tool Selection (@ncrispino, nickcrispino)
- Issue: [#414](https://github.com/massgen/MassGen/issues/414)
- Tool integration via importable Python code instead of schema-based tools
- MCP server registry with auto-discovery
- Reduces token usage through on-demand tool loading
- **Status:** ✅ Completed in v0.1.13

### Track: NLIP Integration (@praneeth999, @qidanrui, ram2561, danrui2020)
- PR: [#475](https://github.com/massgen/MassGen/pull/475)
- Natural Language Integration Platform for advanced tool routing
- Multi-backend support across Claude, Gemini, and OpenAI
- Per-agent and orchestrator-level configuration
- **Status:** ✅ Completed in v0.1.13

### Track: Parallel Tool Execution (@praneeth999, ram2561)
- PR: [#520](https://github.com/massgen/MassGen/pull/520)
- Configurable concurrent tool execution across all backends
- Model-level and local execution controls
- Asyncio-based scheduling with semaphore limits
- **Status:** ✅ Completed in v0.1.14

### Track: Gemini 3 Pro Support (@ncrispino, nickcrispino)
- PR: [#530](https://github.com/massgen/MassGen/pull/530)
- Full integration for Google's Gemini 3 Pro model
- Function calling support with parallel tool capabilities
- **Status:** ✅ Completed in v0.1.14

### Track: Parallel File Operations (@ncrispino, nickcrispino)
- Issue: [#441](https://github.com/massgen/MassGen/issues/441)
- Increase parallelism of file read operations
- Standard efficiency evaluation and benchmarking methodology
- **Status:** ✅ Completed in v0.1.14

### Track: Persona Generation System (@ncrispino, nickcrispino)
- PR: [#547](https://github.com/massgen/MassGen/pull/547)
- Automatic generation of diverse system messages for multi-agent configurations
- Multiple generation strategies: complementary, diverse, specialized, adversarial
- **Status:** ✅ Completed in v0.1.15

### Track: Docker Distribution Enhancement (@ncrispino, nickcrispino)
- PR: [#545](https://github.com/massgen/MassGen/pull/545), [#538](https://github.com/massgen/MassGen/pull/538)
- GitHub Container Registry integration with ARM support
- MassGen pre-installed in Docker images for immediate use
- **Status:** ✅ Completed in v0.1.15

### Track: Launch Custom Tools in Docker (@ncrispino, nickcrispino)
- Issue: [#510](https://github.com/massgen/MassGen/issues/510)
- Enable custom tools to run in isolated Docker containers
- Security isolation and portability for custom tool execution
- **Status:** ✅ Completed in v0.1.15

### Track: MassGen Terminal Evaluation (@ncrispino, nickcrispino)
- Issue: [#476](https://github.com/massgen/MassGen/issues/476)
- PR: [#553](https://github.com/massgen/MassGen/pull/553)
- Self-evaluation and improvement of frontend/UI through terminal recording
- Automated video generation and case study creation using VHS
- **Status:** ✅ Completed in v0.1.16

### Track: LiteLLM Cost Tracking Integration (@ncrispino, nickcrispino)
- Issue: [#543](https://github.com/massgen/MassGen/issues/543)
- PR: [#553](https://github.com/massgen/MassGen/pull/553)
- Accurate cost calculation using LiteLLM's pricing database
- Integration with LiteLLM pricing for 500+ models with auto-updates
- **Status:** ✅ Completed in v0.1.16

### Track: Memory Archiving System (@ncrispino, nickcrispino)
- PR: [#555](https://github.com/massgen/MassGen/pull/555)
- Persistent memory with multi-turn session support
- Memory archiving for session persistence and continuity
- **Status:** ✅ Completed in v0.1.16

### Track: MassGen Self-Evolution Skills (@ncrispino, nickcrispino)
- Issue: [#476](https://github.com/massgen/MassGen/issues/476)
- Four new skills for MassGen to develop and maintain itself
- Self-documenting release workflows and configuration generation
- **Status:** ✅ Completed in v0.1.16

### Track: Improve Consistency of Memory & Tool Reminders (@ncrispino, nickcrispino)
- Issue: [#537](https://github.com/massgen/MassGen/issues/537)
- Enhance consistency of memory retrieval across agents
- Improve tool reminder system for better agent awareness
- Standardize memory access patterns
- **Status:** ✅ Completed in v0.1.16

### Track: Textual Terminal Display (@praneeth999, ram2561)
- Issue: [#539](https://github.com/massgen/MassGen/issues/539)
- PR: [#482](https://github.com/massgen/MassGen/pull/482)
- Rich terminal UI using Textual framework with dark/light themes
- Enhanced visualization for multi-agent coordination
- **Status:** ✅ Completed in v0.1.17

### Track: Broadcasting to Humans/Agents (@ncrispino, nickcrispino)
- Issue: [#437](https://github.com/massgen/MassGen/issues/437)
- PR: [#569](https://github.com/massgen/MassGen/pull/569)
- Enable agents to broadcast questions when facing implementation uncertainties
- Human-in-the-loop and agent-to-agent communication for clarification
- **Status:** ✅ Completed in v0.1.18

### Track: Claude Advanced Tooling (@praneeth999, ram2561)
- PR: [#568](https://github.com/massgen/MassGen/pull/568)
- Programmatic tool calling from code execution sandbox
- Server-side tool search with deferred loading
- **Status:** ✅ Completed in v0.1.18

### Track: LiteLLM Integration & Programmatic API (@ncrispino, nickcrispino)
- PR: [#580](https://github.com/massgen/MassGen/pull/580)
- MassGen as a LiteLLM custom provider with `MassGenLLM` class
- New `run()` and `build_config()` functions for programmatic execution
- `NoneDisplay` for silent output in programmatic/LiteLLM use
- **Status:** ✅ Completed in v0.1.19

### Track: Claude Strict Tool Use & Structured Outputs (@praneeth999, ram2561)
- PR: [#572](https://github.com/massgen/MassGen/pull/572)
- `enable_strict_tool_use` config flag with recursive schema patching
- `output_schema` parameter for structured JSON outputs
- **Status:** ✅ Completed in v0.1.19

### Track: Gemini Exponential Backoff (@praneeth999, ram2561)
- PR: [#576](https://github.com/massgen/MassGen/pull/576)
- Automatic retry mechanism for rate limit errors (429, 503)
- Jittered exponential backoff with `Retry-After` header support
- **Status:** ✅ Completed in v0.1.19

### Track: CUA Dockerfile / Auto Docker Setup (@franklinnwren, zhichengren)
- Issue: [#552](https://github.com/massgen/MassGen/issues/552)
- Automatic Docker container setup for Computer Use Agent
- Auto-detection of CUA configs with automatic container creation
- **Status:** ✅ Completed in v0.1.20

### Track: Web UI (@voidcenter, justin_zhang)
- PR: [#588](https://github.com/massgen/MassGen/pull/588)
- Browser-based real-time visualization for multi-agent coordination
- FastAPI server with WebSocket streaming and React frontend
- **Status:** ✅ Completed in v0.1.20

### Track: Response API Formatter Enhancement (@praneeth999, ram2561)
- Improved function call handling for multi-turn contexts
- Preserves function_call entries and generates stub outputs
- **Status:** ✅ Completed in v0.1.20

### Track: Computer Use Documentation (@franklinnwren, zhichengren)
- Issue: [#562](https://github.com/massgen/MassGen/issues/562)
- Comprehensive documentation for computer use workflows
- Environment naming conventions and automatic setup instructions
- **Status:** ✅ Completed in v0.1.20

### Track: Graceful Cancellation (@ncrispino, nickcrispino)
- PR: [#596](https://github.com/massgen/MassGen/pull/596)
- Ctrl+C saves partial progress during multi-agent coordination
- Session restoration for incomplete turns with `--continue`
- Multi-turn mode returns to prompt instead of exiting
- **Status:** ✅ Completed in v0.1.21

### Track: Shadow Agent Architecture (@ncrispino, nickcrispino)
- PR: [#600](https://github.com/massgen/MassGen/pull/600)
- Shadow agents for non-blocking broadcast responses
- Full context inheritance (conversation history + current turn)
- Parallel spawning with asyncio.gather()
- **Status:** ✅ Completed in v0.1.22

### Track: Web UI Automation Mode (@voidcenter, @ncrispino, justin_zhang, nickcrispino)
- PR: [#607](https://github.com/massgen/MassGen/pull/607)
- Automation-friendly Web UI view with status header and session polling
- LOG_DIR and STATUS path output for programmatic monitoring
- Session persistence API for completed sessions
- **Status:** ✅ Completed in v0.1.23

### Track: Multi-Turn Cancellation Improvements (@ncrispino, nickcrispino)
- PR: [#608](https://github.com/massgen/MassGen/pull/608)
- Flag-based cancellation handling in multi-turn mode
- Terminal state restoration after Rich display cancellation
- Cancelled turns build proper history entries with partial results
- **Status:** ✅ Completed in v0.1.23

### Track: Docker Container Persistence (@ncrispino, nickcrispino)
- Commit: 34279c88
- SessionMountManager for pre-mounting session directories to Docker containers
- Eliminates container recreation between turns (sub-second vs 2-5 second transitions)
- **Status:** ✅ Completed in v0.1.23

### Track: Turn History Inspection (@ncrispino, nickcrispino)
- Commits: 028f591d, 477423a6
- New `/inspect` command for reviewing agent outputs from any turn
- `/inspect all` to list all turns with summaries
- Interactive menu for viewing agent outputs, final answers, and coordination logs
- **Status:** ✅ Completed in v0.1.23

### Track: Async Execution Consistency (@ncrispino, nickcrispino)
- PR: [#608](https://github.com/massgen/MassGen/pull/608)
- New `run_async_safely()` helper for nested event loop handling
- Fixed mem0 adapter async lifecycle issues
- **Status:** ✅ Completed in v0.1.23

### Track: Grok 4.1 Fast Model Support (@praneeth999, ram2561)
- Issue: [#540](https://github.com/massgen/MassGen/issues/540)
- Add support for xAI's Grok 4.1 Fast model
- Integration with existing Grok backend infrastructure
- **Target:** v0.1.25

### Track: Clarify Code Execution in Docs (@ncrispino, nickcrispino)
- Issue: [#573](https://github.com/massgen/MassGen/issues/573)
- Improve documentation clarity for code execution features
- Clear examples and usage patterns
- **Target:** v0.1.26

### Track: RL Integration (@qidanrui, @praneeth999, danrui2020, ram2561)
- Issue: [#527](https://github.com/massgen/MassGen/issues/527)
- Reinforcement learning integration for agent optimization
- Adaptive agent behavior based on feedback and outcomes
- Reward modeling for multi-agent coordination
- **Target:** v0.1.24

### Track: Smithery MCP Tools Support (@ncrispino, nickcrispino)
- Issue: [#521](https://github.com/massgen/MassGen/issues/521)
- Integration with Smithery to expand available MCP tools
- Automatic discovery and installation of Smithery MCP servers
- **Target:** v0.1.24

### Track: Memory as Tools (@ncrispino, nickcrispino)
- Issue: [#461](https://github.com/massgen/MassGen/issues/461)
- Include memory (including filesystem) as callable tools for agents
- Unified interface for different memory backends
- **Target:** v0.1.25

### Track: Coding Agent Enhancements (@ncrispino, nickcrispino)
- PR: [#251](https://github.com/massgen/MassGen/pull/251)
- Enhanced file operations and workspace management
- **Shipping:** Continuous improvement

---

## 🎯 Long-Term Vision (v0.2.0+)

**Advanced Orchestration Patterns**
- Task/subtask decomposition and parallel coordination
- Assignment of agents to specific tasks and increasing of diversity
- Improvement in voting as tasks continue

**Visual Workflow Designer**
- No-code multi-agent workflow creation
- Drag-and-drop agent configuration
- Real-time testing and debugging

**Enterprise Features**
- Role-based access control (RBAC)
- Audit logs and compliance reporting
- Multi-user collaboration
- Advanced analytics and cost tracking

**Additional Framework Integrations**
- LangChain agent support
- CrewAI compatibility
- Custom framework adapters

**Complete Multimodal Pipeline**
- End-to-end audio processing (speech-to-text, text-to-speech)
- Video understanding and generation
- Advanced document processing (PDF, Word, Excel)

---

## 🔗 GitHub Integration

Track development progress:
- [Active Issues](https://github.com/massgen/MassGen/issues)
- [Pull Requests](https://github.com/massgen/MassGen/pulls)
- [Project Boards](https://github.com/massgen/MassGen/projects) (TODO)

---

## 🤝 Contributing

Interested in contributing? You have two options:

**Option 1: Join an Existing Track**
1. See [Contributors & Contact](#-contributors--contact) table above for active tracks
2. Contact the track owner via Discord to discuss your ideas
3. Follow [CONTRIBUTING.md](CONTRIBUTING.md) for development process

**Option 2: Create Your Own Track**
1. Have a significant feature idea? Propose a new track!
2. Reach out via the #massgen channel on [Discord](https://discord.gg/VVrT2rQaz5)
3. Work with the MassGen dev team to integrate your track into the roadmap
4. Become a track owner and guide other contributors

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code standards, testing, and documentation requirements.

---

## 📚 Related Documentation

- [CHANGELOG.md](CHANGELOG.md) - Complete release history
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [Documentation](https://docs.massgen.ai/en/latest/) - Full user guide

---

*This roadmap is community-driven. Releases ship on **Mondays, Wednesdays, Fridays @ 9am PT**. Timelines may shift based on priorities and feedback. Open an issue to suggest changes!*

**Last Updated:** December 10, 2025
**Maintained By:** MassGen Team
