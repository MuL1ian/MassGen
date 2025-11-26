# MassGen Roadmap

**Current Version:** v0.1.16

**Release Schedule:** Mondays, Wednesdays, Fridays @ 9am PT

**Last Updated:** November 24, 2025

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
| **v0.1.17** | 11/26/25 | Broadcasting to Humans/Agents for Implementation Questions | @ncrispino | Enable agents to broadcast questions when facing implementation uncertainties |
| | | Grok 4.1 Fast Model Support | @ncrispino | Add support for xAI's Grok 4.1 Fast model |
| **v0.1.18** | 11/28/25 | Integrate RL into MassGen | @qidanrui @praneeth999 | Reinforcement learning integration for agent optimization and adaptive behavior |
| | | Textual Terminal Display | @praneeth999 | Rich terminal UI with Textual framework for enhanced visualization |
| **v0.1.19** | 12/02/25 | Filesystem-Based Memory Reliability | @ncrispino | Ensure memory persistence across turns with filesystem backend |
| | | Smithery MCP Tools Support | @ncrispino | Expand MCP tools access through Smithery integration |

*All releases ship on MWF @ 9am PT when ready*

---

## 📋 v0.1.17 - Broadcasting & Model Support

### Features

**1. Broadcasting to Humans/Agents for Implementation Questions** (@ncrispino)
- Issue: [#437](https://github.com/massgen/MassGen/issues/437)
- Enable agents to broadcast questions when facing implementation uncertainties
- Support for human-in-the-loop clarification during task execution
- Agent-to-agent communication for collaborative problem solving
- Structured question/answer workflow with context preservation
- Integration with existing orchestration and coordination systems
- **Use Case**: When agents encounter ambiguous requirements or implementation decisions, they can broadcast questions to humans or other agents for clarification, improving decision quality and reducing errors

**2. Grok 4.1 Fast Model Support** (@ncrispino)
- Issue: [#540](https://github.com/massgen/MassGen/issues/540)
- Add support for xAI's Grok 4.1 Fast model
- Integration with existing Grok backend infrastructure
- Pricing and token counting configuration
- Model capability registration in backend capabilities
- Performance optimization for fast inference
- **Use Case**: Provide access to xAI's latest high-speed model for rapid agent responses and cost-effective multi-agent workflows

### Success Criteria
- ✅ Agents can broadcast questions to humans during execution
- ✅ Agent-to-agent question routing works seamlessly
- ✅ Question context is preserved and responses are integrated
- ✅ Grok 4.1 Fast model is accessible via configuration
- ✅ Token counting and pricing are accurate for Grok 4.1 Fast
- ✅ Model performs with expected latency and cost characteristics

---

## 📋 v0.1.18 - RL Integration & Enhanced UI

### Features

**1. Integrate RL into MassGen** (@qidanrui, @praneeth999)
- Issue: [#527](https://github.com/massgen/MassGen/issues/527)
- Reinforcement learning integration for agent optimization
- Adaptive agent behavior based on feedback and outcomes
- Reward modeling for multi-agent coordination
- Policy optimization for task execution strategies
- Learning from past interactions to improve future performance
- **Use Case**: Enable agents to learn and improve their performance over time through reinforcement learning, optimizing coordination strategies and task execution based on past successes and failures

**2. Textual Terminal Display** (@praneeth999)
- Issue: [#539](https://github.com/massgen/MassGen/issues/539)
- Rich terminal UI using Textual framework
- Enhanced visualization for multi-agent coordination
- Interactive agent status displays with real-time updates
- Improved logging and debugging interface
- Modern TUI with responsive layout and themes
- **Use Case**: Provide a more intuitive and visually appealing terminal interface for monitoring multi-agent workflows, improving user experience and debugging capabilities

### Success Criteria
- ✅ RL framework successfully integrates with MassGen architecture
- ✅ Agents demonstrate learning and improvement over repeated tasks
- ✅ Reward modeling accurately reflects task success metrics
- ✅ Textual UI renders correctly across different terminal emulators
- ✅ Real-time updates display agent activities without performance degradation
- ✅ UI is intuitive and improves user experience over current display

---

## 📋 v0.1.19 - Memory & MCP Ecosystem Expansion

### Features

**1. Filesystem-Based Memory Reliability** (@ncrispino)
- Issue: [#499](https://github.com/massgen/MassGen/issues/499)
- Ensure filesystem-based memory is reliable and can be used across turns
- Persistent memory state with atomic write operations
- Crash recovery and data consistency guarantees
- Multi-turn conversation memory continuity
- Performance optimization for large memory contexts
- **Use Case**: Enable reliable long-term memory persistence using filesystem backend, ensuring agents can maintain context across multiple conversation turns and system restarts without data loss

**2. Smithery MCP Tools Support** (@ncrispino)
- Issue: [#521](https://github.com/massgen/MassGen/issues/521)
- Integration with Smithery to expand available MCP tools
- Automatic discovery and installation of Smithery MCP servers
- Curated registry of high-quality MCP tools from Smithery ecosystem
- Simplified tool onboarding for users
- Enhanced tool discovery and recommendation system
- **Use Case**: Expand MassGen's tool ecosystem by integrating with Smithery, giving users access to a wider range of curated MCP tools without manual configuration

### Success Criteria
- ✅ Filesystem memory operations are atomic and crash-safe
- ✅ Memory state persists reliably across conversation turns
- ✅ Performance remains acceptable with large memory contexts
- ✅ Smithery integration discovers and installs MCP tools automatically
- ✅ Tool registry includes curated Smithery tools with proper metadata
- ✅ Users can easily browse and install Smithery tools

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

### Track: Broadcasting to Humans/Agents (@ncrispino, nickcrispino)
- Issue: [#437](https://github.com/massgen/MassGen/issues/437)
- Enable agents to broadcast questions when facing implementation uncertainties
- Human-in-the-loop and agent-to-agent communication for clarification
- **Target:** v0.1.17

### Track: Grok 4.1 Fast Model Support (@ncrispino, nickcrispino)
- Issue: [#540](https://github.com/massgen/MassGen/issues/540)
- Add support for xAI's Grok 4.1 Fast model
- Integration with existing Grok backend infrastructure
- **Target:** v0.1.17

### Track: RL Integration (@qidanrui, @praneeth999, danrui2020, ram2561)
- Issue: [#527](https://github.com/massgen/MassGen/issues/527)
- Reinforcement learning integration for agent optimization
- Adaptive agent behavior based on feedback and outcomes
- Reward modeling for multi-agent coordination
- **Target:** v0.1.18

### Track: Textual Terminal Display (@praneeth999, ram2561)
- Issue: [#539](https://github.com/massgen/MassGen/issues/539)
- Rich terminal UI using Textual framework
- Enhanced visualization for multi-agent coordination
- **Target:** v0.1.18

### Track: Filesystem-Based Memory Reliability (@ncrispino, nickcrispino)
- Issue: [#499](https://github.com/massgen/MassGen/issues/499)
- Ensure filesystem-based memory is reliable across conversation turns
- Persistent memory state with atomic operations
- **Target:** v0.1.19

### Track: Smithery MCP Tools Support (@ncrispino, nickcrispino)
- Issue: [#521](https://github.com/massgen/MassGen/issues/521)
- Integration with Smithery to expand available MCP tools
- Automatic discovery and installation of Smithery MCP servers
- **Target:** v0.1.19

### Track: Coding Agent Enhancements (@ncrispino, nickcrispino)
- PR: [#251](https://github.com/massgen/MassGen/pull/251)
- Enhanced file operations and workspace management
- **Shipping:** Continuous improvement

### Track: Web UI (@voidcenter, justin_zhang)
- PR: [#257](https://github.com/massgen/MassGen/pull/257)
- Visual multi-agent coordination interface
- **Target:** TBD

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

**Last Updated:** November 24, 2025
**Maintained By:** MassGen Team
