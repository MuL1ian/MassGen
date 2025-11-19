# MassGen Roadmap

**Current Version:** v0.1.14

**Release Schedule:** Mondays, Wednesdays, Fridays @ 9am PT

**Last Updated:** November 19, 2025

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
| Web UI | [@voidcenter](https://github.com/voidcenter) | justin_zhang |

*For general questions, join the #massgen channel on [Discord](https://discord.gg/VVrT2rQaz5)*

---


| Release | Target | Feature | Owner | Use Case |
|---------|--------|---------|-------|----------|
| **v0.1.15** | 11/21/25 | Integrate RL into MassGen | @qidanrui @praneeth999 | Reinforcement learning integration for agent optimization and adaptive behavior |
| | | Git Worktrees for Multi-Agent | @ncrispino | Use Git worktrees for different agents to enable parallel development workflows |
| **v0.1.16** | 11/24/25 | Launch Custom Tools in Docker | @ncrispino | Enable custom tools to run in isolated Docker containers for security and portability |
| | | Improve Consistency of Memory & Tool Reminders | @ncrispino | Enhance memory and tool reminder consistency across agents |
| **v0.1.17** | 11/26/25 | MassGen Terminal Evaluation | @ncrispino | Self-evaluation and improvement of frontend/UI |
| | | Smithery MCP Tools Support | @ncrispino | Expand MCP tools access through Smithery integration |

*All releases ship on MWF @ 9am PT when ready*

---

## 📋 v0.1.15 - RL Integration & Multi-Agent Git Workflows

### Features

**1. Integrate RL into MassGen** (@qidanrui, @praneeth999)
- Issue: [#527](https://github.com/massgen/MassGen/issues/527)
- Reinforcement learning integration for agent optimization
- Adaptive agent behavior based on feedback and outcomes
- Reward modeling for multi-agent coordination
- Policy optimization for task execution strategies
- Learning from past interactions to improve future performance
- Integration with existing agent coordination infrastructure
- **Use Case**: Enable agents to learn and improve their performance over time through reinforcement learning, optimizing coordination strategies and task execution based on past successes and failures

**2. Git Worktrees for Different Agents** (@ncrispino)
- Issue: [#514](https://github.com/massgen/MassGen/issues/514)
- Enable multiple agents to work on different Git worktrees simultaneously
- Isolated working directories for parallel agent development
- Automatic worktree creation and management
- Branch synchronization across agent worktrees
- Conflict resolution support for multi-agent workflows
- Improved parallelism for multi-agent code development tasks
- **Use Case**: Allow multiple agents to work on different features or branches simultaneously without conflicts, enabling true parallel development workflows

### Success Criteria
- ✅ RL framework successfully integrates with MassGen architecture
- ✅ Agents demonstrate learning and improvement over repeated tasks
- ✅ Reward modeling accurately reflects task success metrics
- ✅ Policy optimization improves coordination strategies
- ✅ RL integration maintains system stability and performance
- ✅ Agents successfully create and manage separate Git worktrees
- ✅ Multiple agents can work on different branches simultaneously
- ✅ Worktree cleanup and management works reliably
- ✅ Branch synchronization maintains code integrity
- ✅ Performance improvements in multi-agent development scenarios

---

## 📋 v0.1.16 - Docker Tools & Expanded Integrations

### Features

**1. Launch Custom Tools in Docker** (@ncrispino)
- Issue: [#510](https://github.com/massgen/MassGen/issues/510)
- Enable custom tools to run in isolated Docker containers
- Automatic containerization of custom tool execution
- Security isolation for untrusted or experimental tools
- Improved portability across different environments
- Resource management and cleanup for tool containers
- Integration with existing Docker infrastructure
- **Use Case**: Run custom tools in isolated Docker containers for enhanced security, enabling safe execution of untrusted code and ensuring consistent tool behavior across environments

**2. Improve Consistency of Memory & Tool Reminders** (@ncrispino)
- Issue: [#537](https://github.com/massgen/MassGen/issues/537)
- Enhance consistency of memory retrieval across agents
- Improve tool reminder system for better agent awareness
- Standardize memory access patterns
- Optimize tool suggestion timing and relevance
- **Use Case**: Ensure agents have consistent access to shared memory and receive relevant tool reminders at appropriate times, improving coordination and task execution quality

### Success Criteria
- ✅ Custom tools successfully launch in Docker containers
- ✅ Security isolation prevents tools from affecting host system
- ✅ Automatic cleanup of Docker resources after tool execution
- ✅ Tool execution performance comparable to native execution
- ✅ Memory retrieval is consistent across all agents
- ✅ Tool reminders appear at appropriate times with relevant suggestions
- ✅ Memory access patterns are standardized and documented

---

## 📋 v0.1.17 - Frontend Evaluation & MCP Ecosystem Expansion

### Features

**1. MassGen Terminal Evaluation** (@ncrispino)
- Issue: [#476](https://github.com/massgen/MassGen/issues/476)
- Enable MassGen to evaluate and improve its own frontend/UI
- Terminal session recording using asciinema for visual analysis
- Automatic caption generation for recorded sessions
- Video editing integration for demonstration materials
- Comprehensive case study generation from terminal recordings
- Self-improvement capabilities extended to frontend (currently backend-only via automation mode)
- **Use Case**: Enable MassGen to analyze its own terminal interface, creating demonstration videos and documentation automatically, showcasing new features through automated workflows

**2. Smithery MCP Tools Support** (@ncrispino)
- Issue: [#521](https://github.com/massgen/MassGen/issues/521)
- Integration with Smithery to expand available MCP tools
- Automatic discovery and installation of Smithery MCP servers
- Curated registry of high-quality MCP tools from Smithery ecosystem
- Simplified tool onboarding for users
- Enhanced tool discovery and recommendation system
- **Use Case**: Expand MassGen's tool ecosystem by integrating with Smithery, giving users access to a wider range of curated MCP tools without manual configuration

### Success Criteria
- ✅ Terminal recording and playback system works reliably
- ✅ Video understanding capabilities accurately analyze terminal sessions
- ✅ Automated case study generation produces high-quality documentation
- ✅ MassGen successfully self-improves based on terminal analysis
- ✅ Smithery integration discovers and installs MCP tools automatically
- ✅ Tool registry includes curated Smithery tools with proper metadata
- ✅ Tool recommendation system suggests relevant Smithery tools
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

### Track: Launch Custom Tools in Docker (@ncrispino, nickcrispino)
- Issue: [#510](https://github.com/massgen/MassGen/issues/510)
- Enable custom tools to run in isolated Docker containers
- Security isolation and portability for custom tool execution
- **Target:** v0.1.16

### Track: Improve Consistency of Memory & Tool Reminders (@ncrispino, nickcrispino)
- Issue: [#537](https://github.com/massgen/MassGen/issues/537)
- Enhance consistency of memory retrieval across agents
- Improve tool reminder system for better agent awareness
- Standardize memory access patterns
- **Target:** v0.1.16

### Track: RL Integration (@qidanrui, @praneeth999, danrui2020, ram2561)
- Issue: [#527](https://github.com/massgen/MassGen/issues/527)
- Reinforcement learning integration for agent optimization
- Adaptive agent behavior based on feedback and outcomes
- Reward modeling for multi-agent coordination
- **Target:** v0.1.15

### Track: Git Worktrees for Multi-Agent (@ncrispino, nickcrispino)
- Issue: [#514](https://github.com/massgen/MassGen/issues/514)
- Enable multiple agents to work on different Git worktrees simultaneously
- Isolated working directories for parallel agent development
- **Target:** v0.1.15

### Track: MassGen Terminal Evaluation (@ncrispino, nickcrispino)
- Issue: [#476](https://github.com/massgen/MassGen/issues/476)
- Self-evaluation and improvement of frontend/UI through terminal recording
- Automated video generation and case study creation
- **Target:** v0.1.17

### Track: Smithery MCP Tools Support (@ncrispino, nickcrispino)
- Issue: [#521](https://github.com/massgen/MassGen/issues/521)
- Integration with Smithery to expand available MCP tools
- Automatic discovery and installation of Smithery MCP servers
- **Target:** v0.1.17

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

**Last Updated:** November 19, 2025
**Maintained By:** MassGen Team
