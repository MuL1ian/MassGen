# MassGen Roadmap

**Current Version:** v0.1.39

**Release Schedule:** Mondays, Wednesdays, Fridays @ 9am PT

**Last Updated:** January 16, 2026

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
| **v0.1.40** | 01/19/26 | OpenAI Responses /compact Endpoint | @ncrispino | Use OpenAI's native compact endpoint instead of custom summarization |
| | | TUI Production Upgrade | @ncrispino | Migrate to Textual as primary terminal interface |
| **v0.1.41** | 01/21/26 | Integrate Smart Semantic Search | @ncrispino | Advanced semantic search capabilities for improved retrieval |
| | | Add Model Selector for Log Analysis | @ncrispino | Choose model for `massgen logs analyze` self-analysis mode |
| **v0.1.42** | 01/24/26 | Improve Log Sharing and Analysis | @ncrispino | Enhanced log sharing workflows and analysis tools |
| | | Add Fara-7B for Computer Use | @ncrispino | Support for Fara-7B model for computer use tasks |

*All releases ship on MWF @ 9am PT when ready*

---

## ✅ v0.1.39 - Plan and Execute Workflow (COMPLETED)

**Released: January 16, 2026**

### Features

- **Plan and Execute Workflow**: Complete plan-then-execute workflow separating "what to build" from "how to build it" ([PR #794](https://github.com/massgen/MassGen/pull/794))
  - `--plan-and-execute`: Create plan then immediately execute it
  - `--execute-plan <id|path|latest>`: Execute existing plans without re-planning
  - `--plan-depth <shallow|medium|deep>`: Control plan granularity (5-10, 20-50, or 100-200+ tasks)
  - `--broadcast <human|agents|false>`: Control planning collaboration

- **Task Verification Workflow**: New `verified` status for distinguishing implementation from validation
  - Status flow: `pending` → `in_progress` → `completed` → `verified`
  - `verification_group` labels for batch verification (e.g., "foundation", "frontend_ui")
  - Agents verify entire groups at logical checkpoints

- **Plan Storage System**: Persistent plan management in `.massgen/plans/`
  - Plan structure: `plan_metadata.json`, `execution_log.jsonl`, `plan_diff.json`
  - `frozen/` directory for immutable planning-phase snapshots
  - `workspace/` directory for modified plan after execution
  - Plan IDs use timestamp format: `YYYYMMDD_HHMMSS_microseconds`

### Fixed

- **Response API Function Call Messages**: Sanitized function_call messages for OpenAI Response API compatibility ([PR #792](https://github.com/massgen/MassGen/pull/792))
  - Filter function_call messages to only include valid fields
  - Ensure 'arguments' field is JSON-serialized string, not an object

- **Plan Execution Edge Cases**: Various fixes for plan execution workflow
  - Single-agent config handling for both `agent:` and `agents:` shapes
  - Progress calculation now counts `verified` tasks as completed

*See [Ongoing Work](#-ongoing-work--continuous-releases) section for detailed track information.*

---

## 📋 v0.1.40 - OpenAI Compact Endpoint & TUI Production Upgrade

### Features

**1. OpenAI Responses /compact Endpoint** (@ncrispino)
- Issue: [#739](https://github.com/massgen/MassGen/issues/739)
- Use OpenAI's native `/compact` endpoint instead of custom summarization
- Leverage API-level context compression for better efficiency
- **Use Case**: Reduce token usage and improve response quality with native compression

**2. TUI Production Upgrade** (@ncrispino)
- Issue: [#778](https://github.com/massgen/MassGen/issues/778)
- Migrate to Textual as primary terminal interface
- Replace rich_terminal with production-ready Textual TUI
- Improved stability, layout, and user experience
- **Use Case**: Professional-grade terminal interface for daily use

### Success Criteria
- ✅ OpenAI compact endpoint integration working
- ✅ Textual TUI as default terminal interface

---

## 📋 v0.1.41 - Smart Semantic Search & Log Analysis Model Selector

### Features

**1. Integrate Smart Semantic Search** (@ncrispino)
- Issue: [#639](https://github.com/massgen/MassGen/issues/639)
- Advanced semantic search capabilities for improved retrieval
- Integration with existing search infrastructure
- **Use Case**: Better context retrieval and information discovery

**2. Add Model Selector for Log Analysis** (@ncrispino)
- Issue: [#766](https://github.com/massgen/MassGen/issues/766)
- Allow users to choose which model to use for `massgen logs analyze` self-analysis mode
- Configurable model selection for different analysis requirements
- **Use Case**: Flexibility in choosing analysis model based on cost/quality tradeoffs

### Success Criteria
- ✅ Semantic search integrated and functional
- ✅ Model selector working for log analysis command

---

## 📋 v0.1.42 - Log Sharing & Fara-7B Support

### Features

**1. Improve Log Sharing and Analysis** (@ncrispino)
- Issue: [#722](https://github.com/massgen/MassGen/issues/722)
- Enhanced log sharing workflows
- Improved analysis tools and visualizations
- **Use Case**: Better collaboration and debugging workflows

**2. Add Fara-7B for Computer Use** (@ncrispino)
- Issue: [#646](https://github.com/massgen/MassGen/issues/646)
- Support for Fara-7B model for computer use tasks
- Integration with existing computer use infrastructure
- **Use Case**: Alternative model option for GUI automation workflows

### Success Criteria
- ✅ Log sharing improvements deployed
- ✅ Fara-7B working with computer use features

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

### Track: Enhanced Cost Tracking (@ncrispino, nickcrispino)
- Expanded token counting and cost calculation across multiple providers
- Real-time token usage for OpenRouter, xAI/Grok, Gemini, Claude Code backends
- Per-agent token breakdown with cost inspection command
- **Status:** ✅ Completed in v0.1.24

### Track: UI-TARS Backend Support (@franklinnwren, zhichengren)
- PR: [#584](https://github.com/massgen/MassGen/pull/584)
- New backend for ByteDance's UI-TARS-1.5-7B model for GUI automation
- OpenAI-compatible API via HuggingFace Inference Endpoints
- Tool implementation with Docker and browser automation examples
- **Status:** ✅ Completed in v0.1.25

### Track: Evolving Skill Creator System (@ncrispino, nickcrispino)
- PR: [#629](https://github.com/massgen/MassGen/pull/629)
- Framework for creating and iterating on reusable workflow plans
- Skills capture steps, Python scripts, and learnings through iteration
- Support for loading skills from previous sessions
- **Status:** ✅ Completed in v0.1.25

### Track: Textual Terminal Display Enhancement (@praneeth999, ram2561)
- PR: [#589](https://github.com/massgen/MassGen/pull/589)
- Adaptive layout management for different terminal sizes
- Enhanced dark/light themes with modals and panels
- Improved agent coordination visualization
- **Status:** ✅ Completed in v0.1.25

### Track: Shadow Agent Response Depth (@ncrispino, nickcrispino)
- PR: [#634](https://github.com/massgen/MassGen/pull/634)
- Test-time compute scaling via `response_depth` parameter (low/medium/high)
- Controls solution complexity in shadow agent broadcast responses
- **Status:** ✅ Completed in v0.1.26

### Track: Docker Diagnostics Module (@ncrispino, nickcrispino)
- PR: [#634](https://github.com/massgen/MassGen/pull/634)
- Comprehensive Docker error detection with platform-specific resolution
- Distinguishes binary not installed, daemon not running, permission denied, images missing
- **Status:** ✅ Completed in v0.1.26

### Track: Web UI Setup System (@ncrispino, nickcrispino)
- PR: [#634](https://github.com/massgen/MassGen/pull/634)
- Guided first-run setup with SetupPage, ConfigEditorModal, CoordinationStep
- API key management endpoints and environment checks
- **Status:** ✅ Completed in v0.1.26

### Track: Multimodal Backend Integration (@ncrispino, @qidanrui, nickcrispino, danrui2020)
- Commits: 598a32f8, dc920078
- Native multimodal understanding for Gemini and OpenAI backends
- Image, audio, video understanding via `read_media` with backend-native APIs
- **Status:** ✅ Completed in v0.1.28

### Track: Multimodal Generation Consolidation (@ncrispino, nickcrispino)
- Commit: dc920078
- Unified `generate_media` tool with provider selection
- New `generation/` module for OpenAI (DALL-E, Sora, TTS), Google (Imagen, Veo), OpenRouter
- **Status:** ✅ Completed in v0.1.28

### Track: Web UI Artifact Previewer (@ncrispino, @voidcenter, nickcrispino, justin_zhang)
- Commit: 598a32f8
- Preview workspace artifacts directly in web interface
- Support for PDF, DOCX, PPTX, XLSX, images, HTML, SVG, Markdown, Mermaid
- **Status:** ✅ Completed in v0.1.28

### Track: Minimum Answers Before Voting (@ncrispino, nickcrispino)
- Commit: bc7881d2
- New `min_answers_before_voting` orchestrator configuration option
- Integrated into CLI quickstart wizard and Web UI CoordinationStep
- **Status:** ✅ Completed in v0.1.28

### Track: Azure OpenAI Workflow Fixes (@AbhimanyuAryan, abhimanyuaryan)
- Commit: c71094ac
- Parameter filtering for unsupported Azure parameters
- Fixed tool_choice handling, message validation, and response format extraction
- **Status:** ✅ Completed in v0.1.28

### Track: OpenRouter Tool-Capable Model Filtering (@shubham2345)
- Commit: 40acf82c
- Model list filters to only show models supporting tool calling
- Checks `supported_parameters` for "tools" capability
- **Status:** ✅ Completed in v0.1.28

### Track: Subagent System (@ncrispino, nickcrispino)
- PR: [#690](https://github.com/massgen/MassGen/pull/690)
- Spawn parallel child MassGen processes for independent task execution
- Process isolation with independent workspaces per subagent
- New `spawn_subagents` tool with result aggregation and token tracking
- **Status:** ✅ Completed in v0.1.29

### Track: Tool Metrics Distribution Statistics (@ncrispino, nickcrispino)
- Commit: 30aca047
- Enhanced `get_tool_metrics_summary()` with per-call averages
- Output distribution stats (min/max/median) for bottleneck analysis
- **Status:** ✅ Completed in v0.1.29

### Track: CLI Per-Agent System Messages (@ncrispino, nickcrispino)
- Commit: 78177372
- New mode for assigning different system messages per agent in quickstart
- Options: "Skip", "Same for all", "Different per agent"
- **Status:** ✅ Completed in v0.1.29

### Track: OpenAI Responses API Fixes (@ncrispino, nickcrispino)
- PR: [#685](https://github.com/massgen/MassGen/pull/685)
- Fixed duplicate item errors when using `previous_response_id`
- Preserved function call ID for proper reasoning item pairing
- **Status:** ✅ Completed in v0.1.29

### Track: OpenRouter Web Search Plugin (@shubham2345)
- PR: [#693](https://github.com/massgen/MassGen/pull/693)
- Native web search integration via OpenRouter's plugins array
- Maps `enable_web_search` to `{"id": "web"}` plugin format
- **Status:** ✅ Completed in v0.1.30

### Track: Persona Generator Diversity Modes (@ncrispino, nickcrispino)
- PR: [#699](https://github.com/massgen/MassGen/pull/699)
- Two diversity modes: `perspective` (values/priorities) and `implementation` (solution types)
- Phase-based adaptation with softened personas for convergence
- **Status:** ✅ Completed in v0.1.30

### Track: Azure OpenAI Multi-Endpoint Support (@AbhimanyuAryan, abhimanyuaryan)
- PR: [#698](https://github.com/massgen/MassGen/pull/698)
- Support both Azure-specific and OpenAI-compatible endpoints
- Environment variable expansion (`${VAR}`) in config files
- **Status:** ✅ Completed in v0.1.30

### Track: Test Suite Fixes (@maxim-saplin)
- PR: [#688](https://github.com/massgen/MassGen/pull/688)
- Comprehensive test fixes with xfail registry
- Fixed persistent memory retrieval and backend tool registration
- **Status:** ✅ Completed in v0.1.30

### Track: Logfire Observability Integration (@ncrispino, nickcrispino)
- PR: [#708](https://github.com/massgen/MassGen/pull/708)
- Comprehensive structured logging and tracing via Logfire (Pydantic team)
- Automatic LLM instrumentation for OpenAI, Anthropic Claude, and Google Gemini backends
- Tool execution tracing with timing metrics and agent coordination observability
- Enable via `--logfire` CLI flag or `MASSGEN_LOGFIRE_ENABLED=true` environment variable
- **Status:** ✅ Completed in v0.1.31

### Track: Azure OpenAI Native Tool Call Streaming (@AbhimanyuAryan, abhimanyuaryan)
- PR: [#705](https://github.com/massgen/MassGen/pull/705)
- Tool calls accumulated and yielded as structured `tool_calls` chunks
- Fixed streaming behavior for Azure OpenAI tool calling
- **Status:** ✅ Completed in v0.1.31

### Track: OpenRouter Web Search Logging (@shubham2345)
- PR: [#704](https://github.com/massgen/MassGen/pull/704)
- Fixed logging output for web search operations
- **Status:** ✅ Completed in v0.1.31

### Track: Session Export Multi-Turn Support (@ncrispino, nickcrispino)
- PR: [#715](https://github.com/massgen/MassGen/pull/715)
- Enhanced `massgen export` with turn range selection and workspace options
- Multi-turn file collection preserving turn/attempt structure
- **Status:** ✅ Completed in v0.1.32

### Track: Logfire Optional Dependency (@AbhimanyuAryan, abhimanyuaryan)
- PR: [#711](https://github.com/massgen/MassGen/pull/711)
- Moved Logfire from required to optional `[observability]` extra
- Helpful error message when `--logfire` used without Logfire installed
- **Status:** ✅ Completed in v0.1.32

### Track: Per-Attempt Logging (@ncrispino, nickcrispino)
- Commit: a808d730
- Separate log files per orchestration restart attempt
- Handler reconfiguration via `set_log_attempt()` function
- **Status:** ✅ Completed in v0.1.32

### Track: Office Document PDF Conversion (@ncrispino, nickcrispino)
- Commit: 7c7a32e3
- Automatic DOCX/PPTX/XLSX to PDF conversion for session sharing
- Docker + LibreOffice headless conversion with image fallback
- **Status:** ✅ Completed in v0.1.32

### Track: Reactive Context Compression (@ncrispino, nickcrispino)
- Issue: [#617](https://github.com/massgen/MassGen/issues/617)
- PR: [#697](https://github.com/massgen/MassGen/pull/697)
- Automatic context compression when context length errors are detected
- Streaming buffer system for compression recovery
- **Status:** ✅ Completed in v0.1.33

### Track: Backend Model List Auto-Update (@ncrispino, nickcrispino)
- Issue: [#645](https://github.com/massgen/MassGen/issues/645)
- PR: [#669](https://github.com/massgen/MassGen/pull/669)
- Native model listing APIs for providers (Groq, Together, and others)
- Research third-party wrappers; document manual update processes
- **Status:** ✅ Completed in v0.1.34

### Track: OpenAI-Compatible Chat Server (@maxim-saplin)
- Issue: [#628](https://github.com/massgen/MassGen/issues/628)
- PR: [#689](https://github.com/massgen/MassGen/pull/689)
- Run MassGen as an OpenAI-compatible API server
- **Status:** ✅ Completed in v0.1.34

### Track: Code-Based Tools in Web UI (@ncrispino, nickcrispino)
- Issue: [#612](https://github.com/massgen/MassGen/issues/612)
- Ensure code-based tools work properly in Web UI
- Integration with new Web UI features
- **Status:** ✅ Completed in v0.1.34

### Track: Test MassGen for PPTX Slides (@ncrispino, nickcrispino)
- Issue: [#686](https://github.com/massgen/MassGen/issues/686)
- Verify and improve PPTX generation capabilities
- Test slide generation workflows and output quality
- **Status:** ✅ Completed in v0.1.34

### Track: OpenRouter Tool-Use Model Filtering (@shubham2345)
- Issue: [#647](https://github.com/massgen/MassGen/issues/647)
- Restrict OpenRouter model list to only show models that support tool use
- Filter based on `supported_parameters` capability checks
- **Status:** ✅ Completed in v0.1.34

### Track: OpenAI Responses /compact Endpoint (@ncrispino, nickcrispino)
- Issue: [#739](https://github.com/massgen/MassGen/issues/739)
- Use OpenAI's native `/compact` endpoint instead of custom summarization
- Leverage API-level context compression for better efficiency
- **Target:** v0.1.40

### Track: Improve Logging (@ncrispino, nickcrispino)
- Issue: [#683](https://github.com/massgen/MassGen/issues/683)
- PR: [#761](https://github.com/massgen/MassGen/pull/761)
- Enhanced logging for better debugging and observability via Logfire workflow attributes
- New `massgen logs analyze` CLI command with self-analysis mode
- **Status:** ✅ Completed in v0.1.35

### Track: Add Fara-7B for Computer Use (@ncrispino, nickcrispino)
- Issue: [#646](https://github.com/massgen/MassGen/issues/646)
- Support for Fara-7B model for computer use tasks
- Integration with existing computer use infrastructure
- **Target:** v0.1.42

### Track: @filename Syntax for Inline Context Paths (@ncrispino, nickcrispino)
- Issue: [#767](https://github.com/massgen/MassGen/issues/767)
- Add `@path/to/file` syntax to include files/directories as read-only context
- Smart directory consolidation when 3+ sibling files referenced
- **Target:** v0.1.40

### Track: Integrate Smart Semantic Search (@ncrispino, nickcrispino)
- Issue: [#639](https://github.com/massgen/MassGen/issues/639)
- Advanced semantic search capabilities for improved retrieval
- Integration with existing search infrastructure
- **Target:** v0.1.41

### Track: Add Model Selector for Log Analysis (@ncrispino, nickcrispino)
- Issue: [#766](https://github.com/massgen/MassGen/issues/766)
- Allow users to choose which model to use for `massgen logs analyze` self-analysis mode
- Configurable model selection for different analysis requirements
- **Target:** v0.1.41

### Track: General Hook Framework (@ncrispino, nickcrispino)
- Issue: [#745](https://github.com/massgen/MassGen/issues/745)
- PR: [#769](https://github.com/massgen/MassGen/pull/769)
- Extensible hook system for agent lifecycle events
- Enable custom actions at key orchestration points
- **Status:** ✅ Completed in v0.1.36

### Track: Plan and Execute Workflow (@ncrispino, nickcrispino)
- PR: [#794](https://github.com/massgen/MassGen/pull/794)
- Complete plan-then-execute workflow separating "what to build" from "how to build it"
- `--plan-and-execute` and `--execute-plan` CLI options
- Task verification workflow with `verified` status and verification groups
- Plan storage system in `.massgen/plans/` with frozen snapshots
- **Status:** ✅ Completed in v0.1.39

### Track: Improve Log Sharing and Analysis (@ncrispino, nickcrispino)
- Issue: [#722](https://github.com/massgen/MassGen/issues/722)
- Enhanced log sharing workflows
- Improved analysis tools and visualizations
- **Target:** v0.1.42

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

**Self-Learning & Adaptation**
- Agents learn from past executions to improve future performance
- Automatic skill acquisition from successful task completions
- Feedback loops for continuous improvement
- Memory systems for retaining learned patterns across sessions

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

**Last Updated:** January 16, 2026
**Maintained By:** MassGen Team
