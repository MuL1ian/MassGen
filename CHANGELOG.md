# Changelog

All notable changes to MassGen will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## Recent Releases

**v0.1.26 (December 17, 2025)** - Web UI Setup & Shadow Agent Depth Scaling
New Web UI setup wizard for guided first-run configuration, Docker diagnostics module with platform-specific resolution, and shadow agent response depth for test-time compute scaling.

**v0.1.25 (December 15, 2025)** - UI-TARS Computer Use & Evolving Skills
Added UI-TARS custom tool for GUI automation, GPT-5.2 model support, and evolving skill creator system. Enhanced Textual terminal with adaptive layouts and improved OpenRouter Gemini reasoning details handling.

**v0.1.24 (December 12, 2025)** - Enhanced Cost Tracking
Expanded real-time cost tracking across multiple backends (OpenRouter, xAI, Gemini, Grok, Claude Code) with per-agent token breakdown, cost inspection command, and aggregated session totals.

---

## [0.1.26] - 2025-12-17

### Added
- **Docker Diagnostics Module**: Comprehensive error detection with platform-specific resolution steps for Docker issues (binary not installed, daemon not running, permission denied, images missing)

- **Web UI Setup & Configuration System**: Guided first-run experience with new `SetupPage`, `ConfigEditorModal`, `CoordinationStep` components, enhanced wizard flow, and backend API endpoints for API key management and environment checks

- **Shadow Agent Response Depth**: Test-time compute scaling via `response_depth` parameter (`low`/`medium`/`high`) controlling solution complexity in broadcast responses

### Changed
- **Model Registry Updates**: Added GPT-5.1-Codex family (`gpt-5.1-codex-max`, `gpt-5.1-codex`, `gpt-5.1-codex-mini`), updated Claude model naming to alias notation (`claude-sonnet-4-5`), changed defaults to `gpt-5.1-codex` and `claude-opus-4-5`

- **Shadow Agent Claude Code Compatibility**: Special handling for Claude Code backend conversation history in shadow agent spawning

### Fixed
- **Claude Code API Key Handling**: Fixed API key configuration and environment variable handling

- **Web UI Asset Loading**: Fixed configuration and static asset paths (MAS-160)

- **Package Dependencies**: Fixed pyproject.toml dependency specification (MAS-161)

### Documentations, Configurations and Resources

- Updated agent communication docs with response depth and Claude Code limitation notice; added Claude Code API key examples to backend docs; updated broadcast config examples with `response_depth`

### Technical Details
- **Major Focus**: Web UI setup experience, Docker diagnostics, shadow agent test-time compute scaling
- **Contributors**: @ncrispino and the MassGen team

## [0.1.25] - 2025-12-15

### Added
- **UI-TARS Custom Tool**: New custom tool for ByteDance's UI-TARS-1.5-7B model for GUI automation with vision and reasoning
  - Connects to UI-TARS via HuggingFace Inference Endpoints
  - Image understanding capabilities for browser and desktop automation workflows

- **GPT-5.2 Model Support**: Added OpenAI's latest GPT-5.2 model as new default (replacing gpt-5.1)

- **Evolving Skill Creator System**: Framework for creating and iterating on reusable workflow plans
  - Skills capture steps, Python scripts, and learnings that improve through iteration
  - Support for loading skills from previous sessions
  - Enhanced system message builder (+67 lines) and system prompt sections (+130 lines)

### Changed
- **Textual Terminal Display Enhancement**: Improved terminal UI with adaptive layouts and dark/light theming
  - Adaptive layout management for different terminal sizes and agent states
  - Enhanced modal and panel components for better agent coordination visualization

### Fixed
- **OpenRouter Gemini Reasoning Details**: Preserved reasoning_details in streaming responses for complete reasoning chain

- **LiteLLM Provider Context Paths**: Fixed file path handling for configuration and documentation references

### Documentations, Configurations and Resources

- **UI-TARS Configuration Examples**:
  - `massgen/configs/tools/custom_tools/ui_tars_browser_example.yaml`: Browser automation example
  - `massgen/configs/tools/custom_tools/ui_tars_docker_example.yaml`: Docker automation example

- **Evolving Skills Documentation**:
  - `massgen/configs/skills/skills_with_previous_sessions.yaml`: Previous session skills configuration
  - `massgen/skills/evolving-skill-creator/SKILL.md` (209 lines): Skill creator guide
  - Updated `docs/source/user_guide/tools/skills.rst` (+112 lines): Code mode guide

- **Textual Terminal Themes**:
  - `massgen/frontend/displays/textual_terminal/dark.tcss` (+164 lines)
  - `massgen/frontend/displays/textual_terminal/light.tcss` (+180 lines)

- **Documentation Updates**:
  - Updated `docs/source/reference/python_api.rst` (+158 lines): LiteLLM provider guide
  - Updated `docs/source/reference/supported_models.rst`: GPT-5.2 model entry
  - Updated `docs/source/user_guide/backends.rst` (+11 lines): Backend updates

### Technical Details
- **Major Focus**: UI-TARS computer use backend, evolving skills framework, Textual terminal UI improvements
- **Contributors**: @ncrispino @praneeth999 @franklinnwren and the MassGen team

## [0.1.24] - 2025-12-12

### Changed
- **Enhanced Cost Tracking Across Multiple Backends**: Expanded token counting and cost calculation to support additional providers
  - Added real-time token usage tracking for OpenRouter, xAI/Grok, Gemini, and Claude Code backends
  - New `/inspect` option `c` displays detailed cost breakdown with per-agent token usage (input, output, reasoning, cached)
  - Per-round token history tracking via `get_round_token_history()` method
  - Aggregated cost totals and tool metrics across all agents in coordination status
  - Improved cost ordering and formatting in display tables

### Technical Details
- **Major Focus**: Multi-backend cost tracking with real-time visibility
- **Contributors**: @ncrispino and the MassGen team

## [0.1.23] - 2025-12-10

### Added
- **Turn History Inspection System**: New `/inspect` command for reviewing agent outputs and coordination data from any turn
  - `/inspect` or `/inspect <N>` to view specific turn details with interactive menu
  - `/inspect all` to list all turns in the session with task summaries and winning agents
  - Menu options for viewing individual agent outputs, final answers, system logs, and coordination tables

- **Web UI Automation Mode**: Streamlined interface for programmatic and monitoring workflows
  - New `AutomationView` component with phase/elapsed time status header and session polling
  - `--automation` flag enables timeline-focused view with `LOG_DIR` and `STATUS` path output
  - Session persistence API (`mark_session_completed`) preserves completed sessions in session list

### Changed
- **Docker Container Persistence for Multi-Turn**: Containers now persist across turns for faster transitions
  - New `SessionMountManager` class pre-mounts session directory to Docker containers
  - Eliminates container recreation between turns (sub-second vs 2-5 second transitions)
  - Automatic visibility of new turn workspace directories without remounting

- **Multi-Turn Cancellation Handling**: Improved Ctrl+C behavior in multi-turn mode
  - Flag-based cancellation instead of raising exceptions from signal handlers
  - Coordination loop detects cancellation flag and stops Rich display before printing messages
  - Terminal state restoration via `_restore_terminal_for_input()` after display cancellation
  - Cancelled turns now build proper history entries with partial results

- **Async Execution Consistency**: New utilities for safe async-from-sync execution
  - New `run_async_safely()` helper for nested event loop handling
  - ThreadPoolExecutor pattern prevents `async generator ignored GeneratorExit` errors
  - Fixed mem0 adapter async lifecycle issues

### Documentations, Configurations and Resources

- **Multi-Turn Mode Documentation**: Updated `docs/source/user_guide/sessions/multi_turn_mode.rst` with `/inspect` command documentation, turn history inspection examples, and updated slash command reference

### Technical Details
- **Major Focus**: Async consistency, Web UI automation mode, Docker persistence for multi-turn, turn history inspection
- **Contributors**: @ncrispino and the MassGen team

## [0.1.22] - 2025-12-08

### Added
- **Shadow Agent System**: Lightweight agent clones that respond to broadcast questions without interrupting parent agents
  - New `massgen/shadow_agent.py` with `ShadowAgentSpawner` class (482 lines)
  - Shadow agents share parent's backend (stateless) and copy full conversation history
  - Includes parent's current turn context: text content, tool calls, MCP calls, and reasoning
  - Uses simplified system prompt (preserves identity, removes workflow tools)
  - Generates tool-free text responses with debug file saving support (`--debug` flag)

### Changed
- **Broadcast Channel Architecture**: Replaced inject-then-continue pattern with parallel shadow agent spawning
  - New `_spawn_shadow_agents()` method using `asyncio.gather()` for true parallelization
  - Parent agents continue working uninterrupted while shadows respond
  - Informational messages injected to parent agents after shadow responds ("FYI, you were asked X...")
  - Deprecated `respond_to_broadcast` tool (responses now automatic)

- **Agent Context Tracking**: Enhanced `SingleAgent` to track current turn state for shadow agent access
  - New attributes: `_current_turn_content`, `_current_turn_tool_calls`, `_current_turn_reasoning`, `_current_turn_mcp_calls`
  - Context cleared at start of each turn and populated during stream processing
  - Enables shadow agents to see parent's work-in-progress

### Documentations, Configurations and Resources

- **Agent Communication Documentation**: Updated `docs/source/user_guide/advanced/agent_communication.rst` with shadow agent architecture details, full context responses explanation, and deprecated `respond_to_broadcast` notice

### Technical Details
- **Major Focus**: Shadow agent architecture for non-blocking, context-aware broadcast responses
- **Contributors**: @ncrispino and the MassGen team

## [0.1.21] - 2025-12-05

### Added
- **Graceful Cancellation System**: Ctrl+C during coordination saves partial progress instead of losing work
  - New `massgen/cancellation.py` with `CancellationManager` class (177 lines)
  - First Ctrl+C saves and exits gracefully; second Ctrl+C forces immediate exit
  - In multi-turn mode, first Ctrl+C returns to prompt instead of exiting

### Changed
- **Session Restoration for Incomplete Turns**: Cancelled sessions can be resumed with `--continue`
  - Partial answers combined into conversation history with agent attribution
  - All agent workspaces preserved and provided as read-only context on resume
  - New `get_partial_result()` method in Orchestrator for mid-coordination state capture

### Documentations, Configurations and Resources

- **Graceful Cancellation Guide**: New `docs/source/user_guide/sessions/graceful_cancellation.rst` (196 lines)

### Technical Details
- **Major Focus**: Graceful cancellation with partial progress preservation for multi-turn sessions
- **Contributors**: @ncrispino and the MassGen team

## [0.1.20] - 2025-12-03

### Added
- **Web UI System**: Browser-based real-time visualization for multi-agent coordination
  - New `massgen/frontend/web/server.py` FastAPI server with WebSocket endpoints (1808 lines)
  - New `massgen/frontend/displays/web_display.py` display adapter for web streaming (730 lines)
  - React frontend with 18+ components: AgentCarousel, AnswerBrowser, Timeline, VoteVisualization
  - CLI flags: `--web`, `--web-port`, `--web-host` for launching web server
  - Quickstart wizard, real-time streaming with syntax highlighting, and multi-turn session support

### Changed
- **Automatic Computer Use Docker Setup**: Auto-creates Ubuntu 22.04 container with Xfce desktop for GUI automation
  - New `setup_computer_use_docker()` function with auto-detection of `computer_use_docker_example` configs
  - Container includes X11 virtual display (:99), xdotool, Firefox, Chromium, and scrot

- **Response API Formatter Enhancement**: Improved function call handling for multi-turn contexts
  - Preserves `function_call` entries and generates stub outputs for calls without recorded responses

### Fixed
- **Web UI Multi-turn Support**: Fixed frontend session continuation and follow-up question handling
- **Timeline Tracking**: Fixed timeline arrows and backend event sequencing

### Documentations, Configurations and Resources

- **Web UI Guide**: New `docs/source/user_guide/webui.rst` (250 lines) covering display modes, timeline visualization, and workspace browsing

- **Computer Use Documentation**: Enhanced `docs/source/user_guide/advanced/computer_use.rst` (+66 lines) with environment naming conventions and automatic setup instructions

- **Filesystem-First Mode Documentation**: New `docs/source/user_guide/filesystem_first.rst` (872 lines, experimental v0.2.0+) documenting 98% context reduction via on-demand tool discovery

- **LLM Council Comparison**: New `docs/source/reference/comparisons.rst` (155 lines) comparing MassGen vs LLM Council with feature tables, UI differences, and architectural comparisons

### Technical Details
- **Major Focus**: Web UI for real-time coordination visualization, automatic Docker setup for computer use agents
- **Contributors**: @voidcenter @ncrispino @praneeth999 and the MassGen team

## [0.1.19] - 2025-12-01

### Added
- **LiteLLM Integration & Programmatic API**: MassGen as a LiteLLM custom provider with direct Python interface
  - New `massgen/litellm_provider.py` with `MassGenLLM` class and `register_with_litellm()` (452 lines)
  - New `run()` and `build_config()` functions for programmatic execution without CLI
  - Model string formats: `massgen/<example>`, `massgen/model:<model>`, `massgen/path:<config>`, `massgen/build`
  - New `NoneDisplay` silent display class for suppressing output in programmatic/LiteLLM use
  - Auto-detection of backends from model names (e.g., `gpt-5` → openai, `claude-sonnet-4-5` → claude)

### Changed
- **Claude Strict Tool Use & Structured Outputs**: Enhanced Claude backend with schema validation and improved defaults
  - New `enable_strict_tool_use` config flag with recursive `additionalProperties: false` patching
  - New `output_schema` parameter for structured JSON outputs (requires Sonnet 4.5 or Opus 4.1)
  - Per-tool opt-out via `strict: false` on individual tools
  - Increased default max_tokens and improved tool_result handling
  - ConfigValidator validation for `enable_strict_tool_use` and `output_schema` fields

- **Gemini Exponential Backoff**: Automatic retry mechanism for rate limit errors
  - New `BackoffConfig` dataclass with configurable retry parameters
  - Handles HTTP 429 (rate limit) and 503 (service unavailable) with jittered backoff
  - `Retry-After` header support and Gemini-specific error pattern matching

### Documentations, Configurations and Resources

- **Documentation Reorganization**: Major restructure into `files/`, `tools/`, `integration/`, `sessions/`, and `advanced/` sections with streamlined quickstart guides

- **Configuration Examples**: `massgen/configs/providers/claude/strict_tool_use_example.yaml` for strict tool use with custom and MCP tools

### Technical Details
- **Major Focus**: LiteLLM provider integration, Claude strict tool use with structured outputs, Gemini rate limit resilience
- **Contributors**: @ncrispino @praneeth999 and the MassGen team

## [0.1.18] - 2025-11-28

### Added
- **Agent Communication System**: Agents can now ask questions to other agents and optionally humans via the `ask_others()` tool
  - Three modes: disabled (default), agent-to-agent only (`broadcast: "agents"`), or human-only (`broadcast: "human"`)
  - Blocking execution with inline response delivery into agent context
  - Human interaction UI with timeout, skip options, and session-persistent Q&A history
  - Rate limiting and serialized calls to prevent spam and duplicate prompts
  - Comprehensive event tracking in coordination logs

- **Claude Programmatic Tool Calling**: Code execution can now invoke custom and MCP tools programmatically
  - New `enable_programmatic_flow` backend flag that automatically enables code execution sandbox
  - Custom and MCP tools callable from Claude's code sandbox via `allowed_callers` marking
  - Requires claude-opus-4-5 or claude-sonnet-4-5 models with streaming indicators for invocations

- **Claude Tool Search (Deferred Loading)**: Server-side tool discovery for large tool sets
  - New `enable_tool_search` flag with `tool_search_variant` option (`"regex"` or `"bm25"`)
  - Tools with `defer_loading: true` discovered on-demand, reducing initial context size
  - Per-tool and per-MCP-server override support with streaming indicators

### Changed
- **Backend Capabilities Enhancement**: Added tool search and programmatic flow capability flags to `massgen/backend/capabilities.py` (+17 lines)
- **ConfigValidator Enhancement**: Added `enable_programmatic_flow` and `enable_tool_search` boolean field validation (+2 lines)

### Documentations, Configurations and Resources

- **Claude Advanced Tooling Guide**: New `docs/claude-advanced-tooling.md` covering model requirements, API betas, configuration examples, and streaming cues
- **Agent Communication Documentation**: New `docs/source/user_guide/agent_communication.rst` with broadcast modes, serialization, Q&A history, and examples
- **Configuration Examples**:
  - `massgen/configs/providers/claude/programmatic_with_two_tools.yaml` - Programmatic tool calling with custom and MCP tools
  - `massgen/configs/providers/claude/tool_search_example.yaml` - Tool search with visible and deferred tools
  - `massgen/configs/broadcast/test_broadcast_agents.yaml` - Agent-to-agent broadcast communication
  - `massgen/configs/broadcast/test_broadcast_human.yaml` - Human broadcast communication with Q&A prompts

### Technical Details
- **Major Focus**: Agent communication system with human broadcast support, Claude programmatic tool calling from code execution, Claude tool search for deferred tool discovery
- **Contributors**: @ncrispino @praneeth999 and the MassGen team

## [0.1.17] - 2025-11-26

### Added
- **Textual Terminal Display System**: Interactive terminal UI using the Textual library for enhanced agent coordination visualization
  - New `massgen/frontend/displays/textual_terminal_display.py` (1673 lines)
  - Multi-panel layout with dedicated views for each agent and orchestrator status
  - Real-time streaming content display with syntax highlighting support
  - Emoji fallback mapping for terminals without Unicode support
  - Content filtering for critical patterns (votes, status changes, tools, presentations)
  - Keyboard shortcuts for display interaction and safe keyboard mode
  - Automatic file output with session logging to agent-specific files
  - Thread-safe display updates with buffered content batching

- **Dark and Light Themes**: TCSS stylesheets for customizable terminal appearance
  - New `massgen/frontend/displays/textual_themes/dark.tcss` (322 lines)
  - New `massgen/frontend/displays/textual_themes/light.tcss` (322 lines)
  - VS Code-inspired color schemes with styled containers for post-evaluation and final stream panels

### Changed
- **CoordinationUI Enhancement**: Extended display coordination with Textual Terminal support
  - Enhanced `massgen/frontend/coordination_ui.py` with Textual display integration (+348 lines)
  - New `textual_terminal` display type option alongside existing rich_terminal and simple displays
  - Automatic fallback when Textual library is not available
  - Unified reasoning content processing across all display types

- **Display Module Restructuring**: Improved display initialization and base class architecture
  - Enhanced `massgen/frontend/displays/__init__.py` with Textual display exports (+30 lines)
  - Enhanced `massgen/frontend/displays/terminal_display.py` with shared base functionality (+45 lines)
  - Better separation of concerns between display implementations

### Documentations, Configurations and Resources

- **Textual Configuration Example**: Reference configuration for Textual terminal display
  - New `massgen/configs/basic/single_agent_textual.yaml` (17 lines)

- **Dependencies**: Added Textual library for modern terminal UI
  - Updated `pyproject.toml` and `requirements.txt` with `textual>=0.47.0`

### Technical Details
- **Major Focus**: Textual Terminal Display for enhanced agent coordination visualization with theme support
- **Contributors**: @praneeth999 and the MassGen team

## [0.1.16] - 2025-11-24

### Added
- **Terminal Evaluation System**: Automated terminal session recording and AI-powered evaluation using VHS
  - New `docs/source/user_guide/terminal_evaluation.rst` comprehensive evaluation guide (450 lines)
  - New `massgen/tests/test_terminal_evaluation.py` with test suite (336 lines)
  - New `massgen/tests/demo_terminal_evaluation.py` demonstration script (210 lines)
  - Records terminal sessions as GIFs using VHS (Video Home System)
  - Analyzes session recordings with multimodal models (GPT-4.1, Claude)
  - Evaluates agent performance, UI quality, and interaction patterns
  - Automated testing workflows for continuous quality monitoring

- **LiteLLM Cost Tracking Integration**: Accurate cost calculation using LiteLLM's pricing database
  - New `calculate_cost_with_usage_object()` in `massgen/token_manager/token_manager.py` (+178 lines)
  - New `docs/dev_notes/litellm_cost_tracking_integration.md` design documentation (581 lines)
  - New `massgen/tests/test_litellm_integration.py` comprehensive test suite (331 lines)
  - New `massgen/tests/test_backend_cost_tracking.py` integration tests (183 lines)
  - Integrates LiteLLM pricing database covering 500+ models with auto-updates
  - Handles reasoning tokens for o1/o3 models with separate pricing
  - Handles cached tokens for Claude and OpenAI prompt caching
  - Fallback to legacy calculation when LiteLLM unavailable
  - More accurate cost estimates than manual price tables

- **Memory Archiving System**: Persistent memory with multi-turn session support
  - Enhanced `massgen/orchestrator.py` with memory archiving capabilities (+51 lines)
  - Enhanced `massgen/system_message_builder.py` with archive management (+170 lines)
  - Enhanced `massgen/system_prompt_sections.py` with archiving instructions (+201 lines)
  - Enhanced `massgen/cli.py` with session continuation support (+15 lines)
  - Enables archiving long-term memory for session persistence
  - Supports multi-turn conversations with memory continuity
  - Improved memory retrieval and context management

- **MassGen Self-Evolution Skills**: Skills for MassGen to develop and maintain itself
  - New `massgen/skills/massgen-config-creator/SKILL.md` for creating valid YAML configurations (183 lines)
  - New `massgen/skills/massgen-develops-massgen/SKILL.md` for self-improvement and feature development (490 lines)
  - New `massgen/skills/massgen-release-documenter/SKILL.md` for changelog and documentation updates (252 lines)
  - New `massgen/skills/model-registry-maintainer/SKILL.md` for maintaining model registry (483 lines)
  - Enables MassGen to maintain its own codebase and documentation
  - Self-documenting release workflows
  - Automated configuration validation and generation
  - Model registry updates with pricing and capability tracking

### Changed
- **Docker Infrastructure Enhancement**: Parallel image pulling, VHS recording support, and improved container management
  - Enhanced `massgen/cli.py` with parallel Docker image pulling (+242 lines)
  - Enhanced `massgen/docker/Dockerfile` with VHS installation and improved build process (+44 lines total)
  - Enhanced `massgen/docker/Dockerfile.sudo` with VHS support and enhanced permissions (+47 lines total)
  - Enhanced `massgen/filesystem_manager/_filesystem_manager.py` with VHS utilities and better Docker integration (+50 lines)
  - Parallel pulling of multiple Docker images for faster setup
  - VHS (Video Home System) integration for terminal session recording in Docker containers
  - Better error handling and progress reporting
  - Improved Docker container lifecycle management

- **Model Registry Updates**: Expanded model support with accurate pricing and metadata
  - Enhanced `massgen/backend/capabilities.py` with new models and release dates (+45 lines)
  - Added Grok 4.1 family models (grok-4.1, grok-4.1-mini) with pricing
  - Added GPT-4.1 family models for terminal evaluation
  - Added release dates to all models in BACKEND_CAPABILITIES
  - Removed o4 models (don't exist in production)
  - Removed unsupported Gemini experimental models
  - Improved model metadata for better cost tracking

- **Configuration Builder Enhancement**: Improved model selection and configuration workflow
  - Enhanced `massgen/config_builder.py` with better model defaults (+73 lines)
  - Enhanced `massgen/cli.py` with improved config selection interface (+65 lines)
  - Better model recommendations based on use case
  - Improved validation and error messages

### Fixed
- **Status Mode Log Directory**: Fixed missing log directory creation in status mode
  - Fixed `massgen/cli.py` to create log directories before writing
  - Prevents errors when running in status/automation mode

- **Filesystem Docker Zod Schema**: Resolved MCP tool argument parsing in Docker
  - Enhanced `massgen/backend/chat_completions.py` with schema validation (+16 lines)
  - Enhanced `massgen/backend/claude_code.py` with improved MCP handling (+13 lines)
  - Enhanced `massgen/mcp_tools/security.py` with schema fixes (+2 lines)
  - Fixed Zod schema errors preventing proper tool call execution
  - MCP tools now correctly parse arguments in Docker filesystem mode

### Documentations, Configurations and Resources

- **Terminal Evaluation Documentation**: Complete guide for automated terminal testing
  - New `docs/source/user_guide/terminal_evaluation.rst` with setup and usage (450 lines)
  - Covers VHS configuration, recording workflows, evaluation strategies
  - Best practices for multimodal session analysis

- **Memory Filesystem Mode Enhancement**: Expanded documentation for memory integration
  - Updated `docs/source/user_guide/memory_filesystem_mode.rst` with archiving workflows (+172 lines)
  - Documents memory persistence across sessions
  - Multi-turn conversation patterns with memory continuity
  - Best practices for long-running agent interactions

- **Skills Documentation Updates**: Enhanced skills guide with self-evolution examples
  - Updated `docs/source/user_guide/skills.rst` with MassGen self-evolution skills (+178 lines)
  - Documents the four new MassGen-specific skills
  - Examples of self-maintaining systems
  - Guidelines for creating meta-skills

- **Custom Tools Documentation**: Improved custom tools integration guide
  - Updated `docs/source/user_guide/custom_tools.rst` with terminal evaluation examples (+103 lines)
  - Documents VHS integration patterns
  - Best practices for recording and evaluation tools

- **Configuration Examples**: New YAML configurations for v0.1.16 features
  - New `massgen/configs/meta/massgen_evaluates_terminal.yaml` for terminal evaluation (72 lines)
  - New `massgen/configs/tools/custom_tools/terminal_evaluation.yaml` example config (88 lines)
  - Updated `massgen/configs/skills/test_memory.yaml` with memory archiving examples
  - Updated `massgen/configs/tools/filesystem/code_based/example_code_based_tools.yaml` with Docker improvements

### Technical Details
- **Major Focus**: Terminal evaluation infrastructure, LiteLLM cost tracking integration, memory archiving system, MassGen self-evolution capabilities
- **Contributors**: @ncrispino and the MassGen team

## [0.1.15] - 2025-11-21

### Added
- **Persona Generation System**: Automatic generation of diverse system messages for multi-agent configurations
  - New `massgen/persona_generator.py` for LLM-powered persona creation (365 lines)
  - Enhanced `massgen/orchestrator.py` with persona generation orchestration (+122 lines)
  - Enhanced `massgen/agent_config.py` with persona configuration support (+5 lines)
  - Enhanced `massgen/cli.py` with `--generate-personas` flag (+54 lines)
  - Multiple generation strategies: complementary, diverse, specialized, adversarial
  - Configurable backend for persona generation (defaults to gpt-4o-mini)
  - Custom persona guidelines support for domain-specific generation
  - Increases response diversity without manual system message crafting

### Changed
- **Docker Distribution & Custom Tools Enhancement**: GitHub Container Registry integration with custom tools support
  - Enhanced `.github/workflows/docker-publish.yml` with comprehensive CI/CD pipeline (+96 lines)
  - Enhanced `massgen/docker/Dockerfile` and `Dockerfile.sudo` with MassGen pre-installation (+13 lines each)
  - Enhanced `massgen/filesystem_manager/_docker_manager.py` with improved container management (+37 lines)
  - Enhanced `massgen/cli.py` with Docker-related commands and improvements (+104 lines)
  - Custom tools can now run in isolated Docker containers for security and portability (Issue #510)
  - ARM architecture support for Apple Silicon and ARM-based cloud instances
  - Automated Docker image pruning during CI builds

- **Config Builder Enhancement**: Improved interactive configuration experience
  - Enhanced `massgen/config_builder.py` with better model selection and defaults (+17 lines)

### Documentations, Configurations and Resources

- **Installation Documentation Overhaul**: Comprehensive Docker and setup guides
  - Updated `docs/source/quickstart/installation.rst` with Docker installation instructions (+150 lines)
  - Updated `docs/source/index.rst` with improved getting started guide (+66 lines)
  - Detailed GitHub Container Registry pull instructions
  - Platform-specific Docker setup guidance

- **Persona Generation Configuration Example**: Reference configuration for persona diversity
  - New `massgen/configs/basic/multi/persona_diversity_example.yaml` with strategy and backend configuration (123 lines)

- **Pre-commit Hooks Enhancement**: Additional code quality checks
  - New `scripts/precommit_check_package_name.py` for package name validation (39 lines)
  - Updated `.pre-commit-config.yaml` with package name check (+6 lines)

### Technical Details
- **Major Focus**: Persona generation for agent diversity, Docker distribution improvements, GitHub Container Registry integration
- **Contributors**: @ncrispino and the MassGen team


## [0.1.14] - 2025-11-19

### Added
- **Parallel Tool Execution System**: Configurable concurrent tool execution across all backends with asyncio-based scheduling
  - New `concurrent_tool_execution` configuration parameter for local parallel execution control
  - New `parallel_tool_calls` parameter support for OpenAI Response API (controls model behavior)
  - New `disable_parallel_tool_use` parameter for Claude backend (inverse toggle for tool parallelism)
  - New `max_concurrent_tools` semaphore limit for execution speed control (default: 10)
  - Enhanced `massgen/backend/response.py` with parallel execution infrastructure (+239 lines)
  - Enhanced `massgen/backend/base_with_custom_tool_and_mcp.py` with `_execute_tool_calls` method (+186 lines)
  - Enhanced `massgen/api_params_handler/_response_api_params_handler.py` with parameter handling (+20 lines)
  - Unified handling of custom and MCP tool calls with optional concurrent execution
  - Works with Response, ChatCompletions, Gemini, and Claude backends
  - Model-level controls (parallel_tool_calls) separate from local execution controls (concurrent_tool_execution)

- **Gemini 3 Pro Model Support**: Full integration for Google's Gemini 3 Pro model with function calling
  - Enhanced `massgen/backend/gemini.py` with Gemini 3 Pro compatibility (60 lines modified)
  - Fixed function calling behavior specific to Gemini 3 Pro model
  - Native support for Gemini's parallel function calling capabilities

### Changed
- **Config Builder Enhancement**: Interactive quickstart workflow with guided configuration creation
  - Enhanced `massgen/config_builder.py` with interactive prompts and improved UX (+394 lines)
  - Enhanced `massgen/cli.py` with quickstart command integration and improved interface (+214 lines)
  - Enhanced `massgen/backend/capabilities.py` with model metadata (+3 lines)
  - Streamlined onboarding experience from setup to first run
  - Improved provider selection and configuration validation
  - Better integration with config selection workflow
  - Better error messages and user guidance
  - Previously introduced in v0.1.9, now significantly enhanced for user experience

- **MCP Registry Client**: Enhanced MCP server metadata fetching with official registry integration
  - New `massgen/mcp_tools/registry_client.py` for fetching server descriptions from official MCP registry (358 lines)
  - New `massgen/tests/test_mcp_registry_client.py` comprehensive test suite (184 lines)
  - Enhanced `massgen/mcp_tools/security.py` with registry integration (+49 lines)
  - Fetches metadata from https://registry.modelcontextprotocol.io/v0/servers
  - Enhances system prompts with server descriptions for better agent understanding
  - Builds upon v0.1.13's MCP server registry (server_registry.py) with external registry support

- **Planning System Enhancements**: Improved skill and tool search capabilities in planning mode
  - Enhanced `massgen/mcp_tools/planning/_planning_mcp_server.py` with better search logic (+44 lines)
  - Enhanced `massgen/system_prompt_sections.py` with refined planning prompts (+34 lines)
  - Enhanced `massgen/orchestrator.py` with planning coordination (+21 lines)
  - Enhanced `massgen/system_message_builder.py` with planning context (+12 lines)
  - PR #534: Commit 98b1ec6f
  - Better discovery of available skills and tools during planning phase
  - Improved agent decision-making for tool selection
  - More accurate task decomposition with tool awareness

- **NLIP Routing Streamlining**: Simplified and unified NLIP execution flow across backends
  - Refactored `massgen/backend/response.py` with streamlined routing (net -209 lines)
  - Refactored `massgen/backend/claude.py` with unified handling (+98 lines modified)
  - Refactored `massgen/backend/gemini.py` with consistent patterns (+178 lines modified)
  - Unified custom and MCP tool call handling with improved NLIP routing
  - Reduced code complexity while maintaining full NLIP functionality
  - Better error handling and async management in NLIP message routing
  - Builds upon v0.1.13's NLIP integration with cleaner implementation

- **Coordination Tracking Enhancement**: Improved status monitoring for automation workflows
  - Enhanced `massgen/coordination_tracker.py` with parallel tool execution tracking (+23 lines)
  - Better visibility into concurrent tool execution status for automation mode

### Documentations, Configurations and Resources

- **Parallel Tool Execution Configuration Guide**: Comprehensive documentation for tool execution parallelism
  - New `docs/parallel-tool-execution.md` complete configuration reference (179 lines)
  - Explains model-level vs. local execution controls
  - Backend-specific configuration examples for OpenAI, Claude, Gemini
  - Quick reference for all parallelism-related parameters
  - Execution flow diagrams and best practices

- **Configuration Examples**: New YAML configurations demonstrating v0.1.14 features
  - `massgen/configs/tools/custom_tools/gpt5_nano_custom_tool_with_mcp_parallel.yaml`: Parallel tool execution example with configurable concurrency
  - `massgen/configs/tools/filesystem/code_based/example_code_based_tools.yaml`: Updated with enhanced instructions for code-based tools (+52 lines)
  - `massgen/configs/providers/gemini/gemini_3_pro.yaml`: Configuration template for Gemini 3 Pro model (30 lines)

- **CI/CD Workflow Configuration**: Docker image publishing automation
  - `.github/workflows/docker-publish.yml`: Automated Docker build and publish workflow for releases (60 lines)
  - Integration with GitHub Container Registry for automated container deployment

- **Docker Configuration Updates**: Enhanced Docker setup for development and deployment
  - `massgen/docker/Dockerfile`: Improvements for standard Docker builds (+7 lines)
  - `massgen/docker/Dockerfile.sudo`: Enhanced sudo mode support (+7 lines)

### Technical Details
- **Major Focus**: Parallel tool execution infrastructure, interactive quickstart experience, MCP registry client integration, Gemini 3 Pro support, NLIP routing optimization
- **Contributors**: @praneeth999 @ncrispino and the MassGen team

## [0.1.13] - 2025-11-17

### Added
- **Code-Based Tools System (CodeAct Paradigm)**: Tool integration via importable Python code instead of schema-based tools
  - New `massgen/filesystem_manager/_tool_code_writer.py` for writing MCP tool wrappers to workspace (450 lines)
  - New `massgen/mcp_tools/code_generator.py` for generating Python wrapper code from MCP schemas (507 lines)
  - New `massgen/mcp_tools/server_registry.py` for MCP server catalog with auto-discovery (205 lines)
  - Enhanced `massgen/filesystem_manager/_filesystem_manager.py` with code-based tools setup (+562 lines)
  - Agents import and use tools as native Python functions with type hints and docstrings
  - Reduces token usage by 98% through on-demand tool loading (Anthropic research)
  - Pre-configured registry with popular MCP servers (Playwright, GitHub, Context7, Memory)
  - Auto-discovery eliminates manual MCP server configuration

- **NLIP (Natural Language Interface Protocol) Integration**: Advanced tool routing with natural language interface
  - Enhanced `massgen/backend/response.py` with NLIP routing infrastructure (+134 lines)
  - Enhanced `massgen/backend/claude.py`, `gemini.py`, `chat_completions.py` with NLIP support (+255 lines total)
  - Enhanced `massgen/orchestrator.py` with orchestrator-level NLIP configuration (+48 lines)
  - Routes tool execution requests through natural language interface
  - Multi-backend support across Claude, Gemini, and OpenAI
  - Per-agent or orchestrator-level configuration with fallback to direct execution
  - Enables natural language task decomposition and intelligent tool selection

- **Skills Installation System**: Cross-platform automated skills installer
  - New `massgen/utils/skills_installer.py` for automated skills installation (350 lines)
  - New `scripts/init_skills.sh` and `scripts/init.sh` for shell-based setup (650 lines total)
  - **`massgen --setup-skills` command** for one-command installation
  - Installs openskills CLI, Anthropic skills collection, and Crawl4AI skill
  - Cross-platform support: Windows, macOS, Linux with idempotent installation
  - Comprehensive progress indicators and error handling

### Changed
- **Tool Size & Command-Line Enhancements**: Increased tool capacity and improved CLI execution
  - Updated `massgen/backend/utils.py` tool truncation threshold from 10,000 to 15,000 characters
  - Enhanced `massgen/backend/bash_cli.py` with command-line-only mode improvements
  - Commit: b51067b8 "Command line only mode; increase tool size from 10k to 15k"
  - Allows more comprehensive tool documentation and examples
  - Improved command parsing and error handling
  - Better integration with code-based tools workflow

- **Exclude File Operation MCPs**: Removed filesystem MCP tools in favor of native file operations
  - Updated `massgen/mcp_tools/mcp_manager.py` to exclude `@modelcontextprotocol/server-filesystem` (+204 lines)
  - Commit: 5bdf46bf "Adjusted prompts and added TOOL.md for custom tools"
  - Prevents redundancy with MassGen's built-in filesystem operations
  - Reduces token usage from duplicate tool definitions
  - Clearer tool usage patterns for agents

### Documentations, Configurations and Resources

- **TOOL.md Documentation System**: Standardized documentation format for custom tools
  - New `massgen/tool/_video_tools/TOOL.md` for video tools documentation (161 lines)
  - New `massgen/tool/_web_tools/TOOL.md` for web scraping tools documentation (161 lines)
  - New `massgen/tool/_playwright_mcp/TOOL.md` for Playwright MCP documentation (201 lines)
  - **Standardized structure**: name, description, category, tasks, keywords, usage examples
  - Frontmatter metadata in YAML format for tool discovery
  - Clear "When to Use This Tool" and "When NOT to Use" sections
  - Function signatures with parameter descriptions and return types
  - Configuration prerequisites and setup instructions
  - Common use cases and limitations documentation
  - Enables agents to understand tool capabilities and make informed decisions
  - Total: 12 new TOOL.md files across custom tools directory (~3,800 lines)

- **Configuration Examples**: New YAML configurations for v0.1.13 features
  - `massgen/configs/tools/filesystem/code_based/example_code_based_tools.yaml`: Code-based tools with auto-discovery and shared tools directory (153 lines)
  - `massgen/configs/tools/filesystem/exclude_mcps/test_minimal_mcps.yaml`: Minimal MCPs with command-line file operations and memory filesystem mode (37 lines)
  - `massgen/configs/examples/nlip_basic.yaml`: Basic NLIP protocol support with router and translation settings (54 lines)
  - `massgen/configs/examples/nlip_openai_weather_test.yaml`: OpenAI with NLIP integration for custom tools and MCP servers (36 lines)
  - `massgen/configs/examples/nlip_orchestrator_test.yaml`: Orchestrator-level NLIP configuration for multi-agent coordination (47 lines)

- **Skills Installation Documentation**: Comprehensive guides for skills setup
  - Updated `scripts/init.sh` with detailed help text and options (438 lines)
  - Updated `scripts/init_skills.sh` with skip flags for selective installation (212 lines)
  - Examples: `./init.sh --skip-docker`, `./init_skills.sh --skip-anthropic`

- **Code-Based Tools User Guide**: Complete documentation for CodeAct paradigm implementation
  - New `docs/source/user_guide/code_based_tools.rst` (726 lines)
  - Quick start examples and configuration
  - Explains 98% context reduction benefit (Anthropic research)
  - Covers workspace structure, Python wrapper generation, async workflows
  - Real-world examples: weather forecasting, GitHub integration, multi-tool composition

- **MCP Server Registry Reference**: Documentation for built-in MCP server catalog
  - New `docs/source/reference/mcp_server_registry.rst` (219 lines)
  - Documents all pre-configured MCP servers (Context7, GitHub, Filesystem, Memory, etc.)
  - Connection examples and tool listings
  - API key requirements and configuration
  - Auto-discovery setup instructions

- **Installation Guide Updates**: Enhanced setup documentation with automation scripts
  - Updated `docs/source/quickstart/installation.rst` (+115 lines)
  - Automated development setup using `scripts/init.sh`
  - Script options and flags documentation
  - System requirements and verification steps
  - Windows support roadmap notes

- **Documentation Updates**: Enhanced existing guides with v0.1.13 features
  - Updated `docs/source/user_guide/file_operations.rst` (+44 lines) - Code-based tools integration
  - Updated `docs/source/user_guide/mcp_integration.rst` (+71 lines) - Registry and auto-discovery
  - Updated `docs/source/reference/yaml_schema.rst` (+5 lines) - Code-based tools configuration options

### Technical Details
- **Major Focus**: CodeAct paradigm implementation, MCP registry infrastructure, skills installation automation, TOOL.md documentation standard, self-evolution capabilities, NLIP integration
- **Contributors**: @qidanrui @ncrispino @franklinnwren @praneeth999 and the MassGen team

## [0.1.12] - 2025-11-14

### Added
- **Semtools Skill**: Semantic search capabilities using embedding-based similarity matching
  - New `massgen/skills/semtools/SKILL.md` for meaning-based code and document search (606 lines)
  - Rust-based CLI for high-performance semantic search beyond keyword matching
  - Workspace management for indexing large codebases with fast repeated searches
  - Document parsing support for PDFs, DOCX, PPTX with optional API integration
  - Discovery-focused search finding relevant code without knowing exact keywords
  - Complements traditional ripgrep (keyword) and ast-grep (syntax) search tools

- **Serena Skill**: Symbol-level code understanding via Language Server Protocol (LSP)
  - New `massgen/skills/serena/SKILL.md` for IDE-like semantic code analysis (499 lines)
  - Symbol discovery across 30+ programming languages (classes, functions, variables, types)
  - Reference tracking to find all usage locations of symbols
  - Precise code editing with surgical symbol-level insertions
  - LSP-powered understanding of code structure, scope, and relationships
  - Enables symbol-aware refactoring and navigation capabilities

- **System Message Builder**: New modular system for constructing agent prompts
  - New `massgen/system_message_builder.py` for flexible prompt composition (488 lines)
  - Separates prompt construction logic from orchestrator
  - Enables better organization and reusability of system prompt components
  - Foundation for improved prompt engineering and customization

### Changed
- **System Prompt Architecture**: Complete refactoring for improved LLM attention and effectiveness
  - Enhanced `massgen/system_prompt_sections.py` with hierarchical prompt structure (1286 lines)
  - Reorganized prompt ordering to place critical instructions (skills, memory) at optimal positions
  - Reduced message template redundancy in `message_templates.py` (-682 lines)
  - Simplified orchestrator prompt assembly in `orchestrator.py` (-428 lines)
  - Applied 2025 prompt engineering best practices: XML structure, attention management, priority signaling
  - Improved skills and memory system visibility to agents through better positioning

- **Skills System Refactoring**: Enhanced architecture with local execution support
  - **Local Mode**: Skills can now execute directly without Docker containers
  - **Directory Reorganization**: Moved file-search from `skills/always/file_search/` to `skills/file-search/`
  - **Semantic Search Skills**: Promoted semtools and serena from optional to core skills directory
  - Enhanced `massgen/filesystem_manager/skills_manager.py` for local execution support
  - Enhanced `massgen/filesystem_manager/_code_execution_server.py` for local skill commands (+71 lines)
  - Enhanced `massgen/filesystem_manager/_filesystem_manager.py` with local mode capabilities (+173 lines)
  - Enhanced `massgen/filesystem_manager/_docker_manager.py` for skills integration (+59 lines)
  - Updated `massgen/backend/claude_code.py` for local skill execution (+26 lines)

- **Gemini Computer Use Tool**: Multi-agent support with Docker integration
  - Enhanced `massgen/tool/_gemini_computer_use/gemini_computer_use_tool.py` (949 lines total, +446 lines)
  - Added Docker container support for browser and desktop automation
  - New screenshot capture functions for Docker environments (`take_screenshot_docker`)
  - New action execution system for Docker (`execute_docker_action`)
  - X11 display integration with xdotool for precise control
  - VNC compatibility for remote visualization and debugging
  - Multi-agent coordination capabilities for collaborative computer use

- **Browser Automation Tool**: Enhanced screenshot management
  - Updated `massgen/tool/_browser_automation/browser_automation_tool.py` to save screenshots as files (+39 lines)
  - New `output_filename` parameter to save screenshots directly to agent workspace
  - Automatic workspace path resolution with `agent_cwd` parameter
  - Reduces token usage by avoiding base64-encoded screenshot returns
  - Better integration with file-based workflows and serena skill

### Documentations, Configurations and Resources

- **System Prompt Architecture Documentation**: Comprehensive design document for prompt refactoring
  - New `docs/dev_notes/system_prompt_architecture_redesign.md` (593 lines)
  - Documents LLM attention management and hierarchical structure principles
  - Explains XML-based prompt engineering for Claude models
  - Covers priority signaling and position-based emphasis strategies
  - Implementation roadmap for future prompt improvements

- **Computer Use Visualization Guide**: Multi-agent computer use documentation
  - New `docs/backend/docs/COMPUTER_USE_VISUALIZATION.md` (455 lines)
  - Covers VNC setup and remote visualization workflows
  - Documents multi-agent coordination patterns for computer use
  - Troubleshooting guide for Docker-based automation
  - Architecture diagrams for computer use tool integration

- **Skills Documentation Update**: Enhanced skills system guide
  - Updated `docs/source/user_guide/skills.rst` with local mode documentation (+222 lines)
  - Covers new semantic search skills (semtools/serena)
  - Documents skill directory reorganization
  - Local vs Docker execution trade-offs and best practices

- **YAML Schema Documentation**: Configuration reference updates
  - Updated `docs/source/reference/yaml_schema.rst` with skills configuration options (+36 lines)
  - Documents local mode parameters and skill settings

- **Computer Use Tools Guide**: Enhanced documentation
  - Updated `docs/backend/docs/COMPUTER_USE_TOOLS_GUIDE.md` with Gemini Docker support (+94 lines)
  - Multi-agent computer use configuration examples
  - VNC viewer setup instructions

- **Configuration Examples**: New YAML configurations for v0.1.12 features
  - `massgen/configs/tools/custom_tools/multi_agent_computer_use_example.yaml`: Multi-agent coordination for computer use (194 lines)
  - `massgen/configs/tools/custom_tools/gemini_computer_use_docker_example.yaml`: Gemini with Docker automation (84 lines)
  - Updated `massgen/configs/tools/custom_tools/simple_browser_automation_example.yaml`: File-based screenshot workflow

- **VNC Viewer Script**: Automated VNC setup for computer use visualization
  - New `scripts/enable_vnc_viewer.sh` for quick VNC configuration (40 lines)
  - Streamlines Docker-based computer use debugging and monitoring

### Technical Details
- **Major Focus**: System prompt architecture refactoring, semantic search skills (semtools/serena), local skill execution, multi-agent computer use with Docker
- **Contributors**: @ncrispino @franklinnwren @Henry-811 and the MassGen team

## [0.1.11] - 2025-11-12

### Added
- **Skills System**: Modular prompting framework for enhancing agent capabilities
  - New `SkillsManager` class in `massgen/filesystem_manager/skills_manager.py` for dynamic skill loading and injection (158 lines)
  - **File Search Skill**: Always-available skill for searching files and code across workspace (`massgen/skills/always/file_search/SKILL.md`, 280 lines)
  - Automatic skill discovery and loading from `massgen/skills/` directory structure
  - Docker-compatible skill mounting and environment setup
  - Skills organized into `always/` (auto-included) and `optional/` categories
  - Flexible skill injection into agent system prompts via orchestrator
  - Configuration examples in `massgen/configs/skills/` (skills_basic.yaml, skills_existing_filesystem.yaml, skills_with_memory.yaml)

- **Memory MCP Tool & Filesystem Integration**: MCP server for agent memory management with filesystem persistence and combined workflows
  - New `massgen/mcp_tools/memory/` module with memory MCP server implementation (513 lines total)
  - **MemoryMCPServer** in `_memory_mcp_server.py` (352 lines) for memory CRUD operations with automatic filesystem sync
  - **Memory data models** in `_memory_models.py` (161 lines) with short-term and long-term memory tiers
  - Memory persistence to workspace under `memory/short_term/` and `memory/long_term/` directories
  - Markdown-based memory storage format for human readability
  - Integration with orchestrator for cross-agent memory sharing (+218 lines in orchestrator.py)
  - Memory-specific message templates for memory operations (+95 lines in message_templates.py)
  - **Combined workflows**: Simultaneous use of memory MCP tools and filesystem operations for advanced workflows
  - Enables agents to maintain persistent memory while manipulating files
  - Configuration examples demonstrating integrated workflows for long-running projects requiring both code changes and learned context
  - Inspired by Letta's context hierarchy design pattern

- **Rate Limiting System (Gemini)**: Multi-dimensional rate limiting for Gemini API calls and agent startup
  - New `massgen/backend/rate_limiter.py` (321 lines) with comprehensive rate limiting infrastructure
  - Support for multiple limit types: requests per minute (RPM), tokens per minute (TPM), requests per day (RPD)
  - Model-specific rate limits with configurable thresholds for Gemini models
  - Graceful cooldown periods with exponential backoff
  - Agent startup rate limiting to prevent API quota exhaustion
  - Test suite in `massgen/tests/test_rate_limiter.py` (122 lines)
  - Configuration system in `massgen/configs/rate_limits/` with rate_limits.yaml and rate_limit_config.py (180 lines)
  - CLI flag `--enable-rate-limiting` for opt-in rate limiting

### Changed
- **Claude Code Backend**: Improved Windows support for long system prompts
  - Enhanced handling of long system prompts on Windows platforms
  - Resolved command-line length limitations and encoding issues
  - Updated `massgen/backend/claude_code.py` with more robust Windows compatibility (27 lines changed)

- **Planning MCP Server**: Added filesystem task persistence within workspace
  - Tasks now saved to agent workspace instead of separate tasks/ directory
  - Improved task organization and workspace management
  - Enhanced `massgen/mcp_tools/planning/_planning_mcp_server.py` (+84 lines)
  - Removed standalone tasks/ skill in favor of integrated planning

### Fixed
- **Rate Limiter Asyncio Lock**: Resolved asyncio lock event loop error
  - Fixed asyncio lock reuse across different event loops causing errors
  - Improved rate limiter thread safety and event loop handling
  - Updated `massgen/backend/rate_limiter.py` and added comprehensive tests

### Documentations, Configurations and Resources

- **Skills System Documentation**: Comprehensive guide for using and creating skills
  - New `docs/source/user_guide/skills.rst` (473 lines)
  - Covers skill structure, loading mechanisms, and best practices
  - Examples of creating custom skills for specific agent capabilities

- **Memory-Filesystem Mode Documentation**: Guide for integrated memory and filesystem workflows
  - New `docs/source/user_guide/memory_filesystem_mode.rst` (883 lines)
  - Demonstrates combining memory MCP tools with filesystem operations
  - Configuration examples and use case scenarios

- **Rate Limiting Documentation**: Complete rate limiting configuration guide
  - New `docs/rate_limiting.md` (254 lines)
  - Model-specific rate limits and configuration examples
  - Best practices for managing API quotas
  - New `massgen/configs/rate_limits/README.md` (108 lines)

- **Skills Configuration Examples**: Three YAML configurations for skills usage
  - `massgen/configs/skills/skills_basic.yaml`: Basic skills setup
  - `massgen/configs/skills/skills_existing_filesystem.yaml`: Skills with filesystem integration
  - `massgen/configs/skills/skills_with_memory.yaml`: Skills with memory MCP integration

- **Filesystem Tool Discovery Design**: Comprehensive design document for new tool paradigm
  - New `docs/dev_notes/filesystem_tool_discovery_design.md` (1,582 lines)
  - Proposes shift from context-based to filesystem-based tool discovery
  - Enables attaching 100+ MCP servers without context pollution
  - Details progressive disclosure and code-based tool composition
  - Includes implementation proposals and technical architecture

### Technical Details
- **Major Focus**: Skills system for modular agent prompting, memory MCP tool with filesystem persistence, multi-dimensional rate limiting, memory-filesystem integration mode
- **Contributors**: @ncrispino @abhimanyuaryan @qidanrui @sonichi @Henry-811 and the MassGen team

## [0.1.10] - 2025-11-10

### Added
- **Docker Custom Image Support**: Example Dockerfile for extending MassGen base image with custom packages
  - New `massgen/docker/Dockerfile.custom-example` demonstrating how to add ML/data science packages, development tools, and system utilities
  - Template for creating specialized Docker images for specific project needs

### Changed
- **Docker Authentication Configuration**: Restructured to nested dictionary format for better organization
  - New `command_line_docker_credentials` structure consolidating all credential-related settings
  - Nested `mount` array for credential file mounting (`ssh_keys`, `git_config`, `gh_config`, `npm_config`, `pypi_config`)
  - Nested `env_file`, `env_vars`, and `pass_all_env` for environment variable management
  - Nested `additional_mounts` for custom volume mounting
  - Migration from flat parameters (`command_line_docker_mount_ssh_keys`, `command_line_docker_pass_env_vars`, etc.) to organized nested structure
  - Enhanced `massgen/filesystem_manager/_docker_manager.py` and `_filesystem_manager.py` with new configuration parsing

- **Docker Package Management**: New nested configuration structure for dependency installation
  - New `command_line_docker_packages` structure with `auto_install_deps`, `auto_install_on_clone`, and `preinstall` settings
  - Support for pre-installing Python, npm, and system packages before agent execution
  - Improved dependency detection and installation workflow

- **Framework Interoperability Streaming**: Real-time intermediate step streaming for external framework agents
  - **LangGraph Streaming**: Updated `massgen/tool/_extraframework_agents/langgraph_lesson_planner_tool.py` (78 lines changed)
    - Now yields intermediate updates from each workflow node (standards, lesson_plan, reviewed_plan)
    - Distinguishes between logs (`is_log=True`) and final output using result type
    - Enables real-time progress tracking during LangGraph workflow execution
  - **SmoLAgent Streaming**: Updated `massgen/tool/_extraframework_agents/smolagent_lesson_planner_tool.py` (60 lines changed)
    - Streams ActionStep and PlanningStep outputs as logs during agent execution
    - FinalAnswerStep yielded as final output
    - Set verbosity_level=0 to prevent duplicate console output
  - Both frameworks now provide visibility into multi-step reasoning processes

- **Parallel Execution Safety**: Extended automatic workspace isolation to all execution modes
  - Parallel execution safety now works in both `--automation` and normal modes (previously automation-only)
  - Automatic Docker container naming with unique instance ID suffixes (e.g., `massgen-agent_a-a1b2c3d4`)
  - Enhanced `massgen/filesystem_manager/_filesystem_manager.py` with instance ID generation for all modes

### Fixed
- **Session Management**: Resolved CLI session handling issues
  - Fixed session restoration edge cases in `massgen/cli.py`
  - Improved error handling for session state loading

### Documentations, Configurations and Resources

- **MassGen Contributor Handbook**: Comprehensive contributor guide addressing issue #387
  - New handbook website at https://massgen.github.io/Handbook/
  - Eight major sections: Case Studies, Issues, Development, Documentation, Release, Announcements, Marketing, and Resources
  - Workflow diagrams illustrating contribution pipeline from research to release
  - Seven contribution tracks with assigned track owners
  - Communication channels and meeting schedules (daily sync 5:30pm PST, research 6:00pm PST)
  - Getting started guide for new contributors

- **Docker Configuration Examples**: Three new YAML configurations for advanced Docker workflows
  - `massgen/configs/tools/code-execution/docker_custom_image.yaml`: Using custom Docker images
  - `massgen/configs/tools/code-execution/docker_full_dev_setup.yaml`: Complete development environment setup
  - `massgen/configs/tools/code-execution/docker_github_readonly.yaml`: Read-only GitHub access configuration

- **Automation Documentation**: Enhanced parallel execution section
  - Updated `docs/source/user_guide/automation.rst` clarifying automatic isolation works in all modes
  - Added Docker container isolation examples with unique container naming
  - Clarified that `--automation` flag is for output control, not parallel safety

- **Code Execution Design Documentation**: Updated Docker configuration architecture
  - Enhanced `docs/dev_notes/CODE_EXECUTION_DESIGN.md` (90 lines revised)
  - New credential and package management configuration examples
  - Architecture diagrams for nested configuration structures

- **Computer Use Tools Documentation**: Clarified Docker usage requirements
  - Updated `massgen/tool/_computer_use/README.md` and `QUICKSTART.md`
  - Specified Docker requirements for Claude computer use
  - Added troubleshooting guide for computer use setup

### Technical Details
- **Major Focus**: Docker configuration improvements with nested structures for credentials and packages, framework interoperability streaming enhancements, parallel execution safety across all modes, contributor handbook
- **Contributors**: @ncrispino @Eric-Shang @franklinnwren and the MassGen team

## [0.1.9] - 2025-11-07

### Added
- **Session Management System**: Comprehensive session state tracking and restoration for multi-turn conversations
  - New `massgen/session/` module with session state and registry management (530 lines total)
  - **SessionState** dataclass for complete session state including conversation history, workspace paths, and turn metadata (`_state.py`, 219 lines)
  - **SessionRegistry** for listing, managing, and restoring previous sessions (`_registry.py`, 311 lines)
  - **restore_session()** function for seamless session continuation across CLI invocations
  - Session metadata tracking including winning agents history and orchestrator turn data
  - Automatic session storage with unique identifiers and timestamps
  - Test suite in `test_session_registry.py` (201 lines)

- **Computer Use Tools**: Browser and desktop automation capabilities for multi-agent workflows
  - **General Computer Use Tool**: OpenAI computer-use-preview integration for automated browser/computer control (`massgen/tool/_computer_use/computer_use_tool.py`, 741 lines)
    - Support for browser environment (Playwright) and Docker container execution
    - Action execution: click, type, scroll, navigate, screenshot analysis
    - Configurable max iterations and safety controls
  - **Claude Computer Use Tool**: Anthropic Claude Computer Use API integration (`massgen/tool/_claude_computer_use/claude_computer_use_tool.py`, 473 lines)
    - Native Claude Computer Use beta API support
    - Browser and desktop control with safety confirmations
    - Async execution with Playwright integration
  - **Gemini Computer Use Tool**: Google Gemini-based computer control (`massgen/tool/_gemini_computer_use/gemini_computer_use_tool.py`, 503 lines)
    - Gemini model integration for computer use workflows
    - Screenshot analysis and action generation
  - **Browser Automation Tool**: Lightweight browser automation for specific tasks (`massgen/tool/_browser_automation/browser_automation_tool.py`, 176 lines)
    - Focused browser automation without full computer use overhead
  - Comprehensive test suite in `test_computer_use.py` (629 lines)

- **OpenAI Operator API Handler**: Support for OpenAI's computer-use-preview model
  - New `massgen/api_params_handler/_openai_operator_api_params_handler.py` (72 lines)
  - Specialized parameter handling for computer use actions
  - Integration with computer use tool execution flow

### Changed
- **Config Builder Enhancement**: Intelligent model matching and discovery
  - **Fuzzy Model Name Matching**: New `massgen/utils/model_matcher.py` (214 lines) allowing approximate model name input
  - **Model Catalog System**: New `massgen/utils/model_catalog.py` (218 lines) with curated lists of common models across providers
  - Enhanced `massgen/config_builder.py` with automatic model search and suggestions
  - Support for partial model names with intelligent completion (e.g., "sonnet" → "claude-sonnet-4-5-20250929")
  - Contribution from acrobat3 (K. from JP)

- **Backend Capabilities Enhancement**: Expanded provider support with six new backend registrations
  - Added **Cerebras AI** backend capabilities (llama models with WSE hardware acceleration)
  - Added **Together AI** backend capabilities (Meta-Llama, Mixtral models)
  - Added **Fireworks AI** backend capabilities (Llama, Qwen models with fast inference)
  - Added **Groq** backend capabilities (Llama, Mixtral with LPU hardware)
  - Added **OpenRouter** backend capabilities (unified access to 200+ models with audio/video support)
  - Added **Moonshot (Kimi)** backend capabilities (Chinese-optimized models with long context)
  - Updated `massgen/backend/capabilities.py` with comprehensive backend specifications

- **Memory System Improvement**: Enhanced memory update logic for multi-agent coordination
  - New `massgen/memory/_update_prompts.py` (276 lines) with specialized update prompts for mem0
  - **MASSGEN_UNIVERSAL_UPDATE_MEMORY_PROMPT**: Philosophy for accumulating qualitative patterns vs statistics
  - Improved fact merging logic focusing on actionable tool usage patterns and technical insights

- **Chat Agent Enhancement**: Session restoration and improved orchestrator restart handling
  - Session state restoration in `massgen/chat_agent.py`
  - Enhanced turn tracking and workspace persistence
  - Improved logging and coordination with orchestrator restarts

- **CLI Enhancement**: Extended command-line interface for session management
  - Session listing and restoration commands in `massgen/cli.py`
  - Enhanced display selection and output formatting
  - Support for continuing previous sessions with automatic state restoration

### Documentations, Configurations and Resources

- **Diversity System Documentation**: Comprehensive guide for increasing agent diversity
  - New `docs/source/user_guide/diversity.rst` (388 lines)
  - Covers answer novelty requirements (lenient/balanced/strict)
  - Documents DSPy question paraphrasing integration (from v0.1.8)
  - Best practices for multi-agent diversity strategies
  - Configuration examples and recommendations

- **Memory System Documentation**: Updated memory user guide
  - Updated `docs/source/user_guide/memory.rst` with enhanced memory update logic and configuration

- **Computer Use Configuration Examples**: Five YAML configurations demonstrating computer use capabilities
  - `massgen/configs/tools/custom_tools/claude_computer_use_example.yaml`: Claude-specific computer use
  - `massgen/configs/tools/custom_tools/gemini_computer_use_example.yaml`: Gemini-specific computer use
  - `massgen/configs/tools/custom_tools/computer_use_example.yaml`: General computer use with OpenAI
  - `massgen/configs/tools/custom_tools/computer_use_docker_example.yaml`: Docker-based computer use
  - `massgen/configs/tools/custom_tools/computer_use_browser_example.yaml`: Browser automation focus

- **Session Management Configuration**: Example demonstrating session continuation
  - `massgen/configs/memory/grok4_gpt5_gemini_mcp_filesystem_test_with_claude_code.yaml`: Multi-turn session with MCP filesystem

- **Computer Use Documentation**:
  - New `massgen/backend/docs/COMPUTER_USE_TOOLS_GUIDE.md`: Comprehensive guide for computer use tools (494 lines)
  - New `scripts/computer_use_setup.md`: Setup instructions for computer use tools
  - New `scripts/setup_docker_cua.sh`: Automated Docker setup script for computer use

### Technical Details
- **Major Focus**: Session management with conversation restoration, computer use automation tools, intelligent config builder with fuzzy matching, expanded backend support, memory system enhancements
- **Contributors**: @franklinnwren @ncrispino @Henry-811 and the MassGen team

## [0.1.8] - 2025-11-05

### Added
- **Automation Mode for LLM Agents**: Complete infrastructure for running MassGen via LLM agents and programmatic workflows
  - New `--automation` CLI flag for silent execution with minimal output (~10 lines vs 250-3,000+)
  - New `SilentDisplay` class in `massgen/frontend/displays/silent_display.py` for automation-friendly output
  - Real-time `status.json` monitoring file updated every 2 seconds via enhanced `CoordinationTracker`
  - Meaningful exit codes: 0 (success), 1 (config error), 2 (execution error), 3 (timeout), 4 (interrupted)
  - Automatic workspace isolation for parallel execution with unique suffixes
  - Meta-coordination capabilities: MassGen running MassGen configurations
  - Automatic log directory creation and management for automation sessions

- **DSPy Question Paraphrasing Integration**: Intelligent question diversity for multi-agent coordination
  - New `massgen/dspy_paraphraser.py` module with semantic-preserving paraphrasing (557 lines)
  - Three paraphrasing strategies: "diverse", "balanced" (default), "conservative"
  - Configurable number of variants per orchestrator session
  - Automatic semantic validation using `SemanticValidationSignature` to ensure meaning preservation
  - Thread-safe caching system with SHA-256 hashing for performance
  - Support for all backends (Gemini, OpenAI, Claude, etc.) as paraphrasing engines

- **Case Study Summary**: Comprehensive documentation of MassGen capabilities
  - New `docs/CASE_STUDIES_SUMMARY.md` providing centralized overview of 33 case studies (368 lines)
  - Organized by category: Release Features, Research, Travel, Creative, In Development, Planned
  - Covers versions v0.0.3 to v0.1.5 with status tracking and links to videos
  - Statistics: 19 completed, 8 with video demonstrations, 6 categories

### Changed
- **Orchestrator Enhancement**: Integration of DSPy paraphrasing and automation tracking
  - Question variant distribution to different agents based on configured strategy
  - Improved coordination event logging with structured status exports

- **CLI Enhancement**: Extended command-line interface for automation workflows
  - Enhanced display selection logic automatically choosing SilentDisplay in automation mode
  - Improved output formatting optimized for LLM agent parsing and monitoring

### Documentations, Configurations and Resources

- **Case Study**: Meta-level self-analysis demonstrating automation mode
  - New `docs/source/examples/case_studies/meta-self-analysis-automation-mode.md`: Comprehensive case study showing MassGen analyzing its own v0.1.8 codebase using automation mode

- **Automation Documentation**: Comprehensive guides for LLM agent integration
  - New `AI_USAGE.md`: Complete guide for LLM agents running MassGen (319 lines)
  - New `docs/source/user_guide/automation.rst`: Full automation guide with BackgroundShellManager patterns (890 lines)
  - New `docs/source/reference/status_file.rst`: Complete `status.json` schema reference with field-by-field documentation (565 lines)
  - Updated `README.md` and `README_PYPI.md` with automation mode sections (135 lines each)

- **DSPy Documentation**: Complete implementation and usage guide
  - New `massgen/backend/docs/DSPY_IMPLEMENTATION_GUIDE.md`: Comprehensive DSPy integration guide (653 lines)
  - Covers quick start, configuration, strategies, troubleshooting, and semantic validation
  - Includes paraphrasing examples and best practices

- **Meta-Coordination Configurations**: MassGen running MassGen examples
  - `massgen/configs/meta/massgen_runs_massgen.yaml`: Single agent autonomously running MassGen experiments
  - `massgen/configs/meta/massgen_suggests_to_improve_massgen.yaml`: Self-improvement configuration
  - Demonstrates automation mode usage for meta-coordination workflows

- **DSPy Configuration Example**: New YAML configuration for DSPy-enabled coordination
  - `massgen/configs/basic/multi/three_agents_dspy_enabled.yaml`: Three-agent setup with DSPy paraphrasing

- **Case Study Summary Documentation**: Centralized case study reference
  - New `docs/CASE_STUDIES_SUMMARY.md`: Comprehensive overview of all MassGen case studies with categorization and status tracking

### Technical Details
- **Major Focus**: Automation infrastructure for LLM agents, DSPy-powered question paraphrasing, meta-coordination capabilities, comprehensive case study documentation
- **Contributors**: @ncrispino @praneeth999 @franklinnwren @qidanrui @sonichi @Henry-811 and the MassGen team

## [0.1.7] - 2025-11-03

### Added
- **Agent Task Planning System**: MCP-based task management with dependency tracking
  - New `massgen/mcp_tools/planning/` module with dedicated planning server (`_planning_mcp_server.py`)
  - Task dataclasses with dependency validation and status management (`planning_dataclasses.py`)
  - Support for task states (pending/in_progress/completed/blocked) with automatic transitions based on dependencies
  - Orchestrator integration for plan-aware coordination
  - Test suite in `test_planning_integration.py` and `test_planning_tools.py`

- **Background Shell Execution**: Long-running command support with persistent sessions
  - New `BackgroundShell` class in `massgen/filesystem_manager/background_shell.py`
  - Shell lifecycle management with output streaming and real-time monitoring
  - Automatic timeout handling for long-running processes
  - Enhanced code execution server with background execution capabilities
  - Test coverage in `test_background_shell.py`

- **Preemption Coordination**: Multi-agent coordination with interruption support
  - Agents can preempt ongoing coordination to submit better answers without full restart
  - Enhanced coordination tracker with preemption event logging
  - Improved orchestrator logic to preserve partial progress during preemption

### Fixed
- **System Message Handling**: Resolved system message extraction in Claude Code backend for background shell execution
- **Case Study Documentation**: Fixed broken links and outdated examples in older case studies

### Documentations, Configurations and Resources

- **Documentation Updates**: New user guides and design documentation
  - New `docs/source/user_guide/agent_task_planning.rst`: Task planning guide with usage patterns and API reference
  - Updated `docs/source/user_guide/code_execution.rst`: Added 122 lines for background shell usage
  - New `docs/dev_notes/agent_planning_coordination_design.md`: Comprehensive design document for agent planning and coordination system
  - New `docs/dev_notes/preempt_not_restart_design.md`: 456-line design document with preemption algorithms
  - Updated `docs/source/development/architecture.rst`: Added 61 lines for preemption coordination architecture

- **Configuration Examples**: New YAML configurations demonstrating v0.1.7 features
  - `example_task_todo.yaml`: Task planning configuration
  - `background_shell_demo.yaml`: Background shell execution demonstration

### Technical Details
- **Major Focus**: Agent task planning with dependencies, background command execution, preemption-based coordination
- **Contributors**: @ncrispino @Henry-811 and the MassGen team

## [0.1.6] - 2025-10-31

### Added
- **Framework Interoperability**: External agent framework integration as MassGen custom tools
  - New `massgen/tool/_extraframework_agents/` module with 5 framework integrations
  - **AG2 Lesson Planner Tool**: Nested chat functionality wrapped as custom tool for multi-agent lesson planning (supports streaming)
  - **LangGraph Lesson Planner Tool**: LangGraph graph-based workflows integrated as tool
  - **AgentScope Lesson Planner Tool**: AgentScope agent system wrapped for lesson creation
  - **OpenAI Assistants Lesson Planner Tool**: OpenAI Assistants API integrated as tool
  - **SmoLAgent Lesson Planner Tool**: HuggingFace SmoLAgent integration for lesson planning
  - Enables MassGen agents to delegate tasks to specialized external frameworks
  - Each framework runs autonomously and returns results to MassGen orchestrator
  - Note: Only AG2 currently supports streaming; other frameworks return complete results

- **Configuration Validator**: Comprehensive YAML configuration validation system
  - New `ConfigValidator` class in `massgen/config_validator.py` for pre-flight validation
  - Memory configuration validation with detailed error messages
  - Pre-commit hook integration for automatic config validation
  - Comprehensive test suite in `massgen/tests/test_config_validator.py`
  - Validates agent configurations, backend parameters, tool settings, and memory options
  - Provides actionable error messages with suggestions for common mistakes

### Changed
- **Backend Architecture Refactoring**: Unified tool execution with ToolExecutionConfig
  - New `ToolExecutionConfig` dataclass in `base_with_custom_tool_and_mcp.py` for standardized tool handling
  - Refactored `ResponseBackend` with unified tool execution flow
  - Refactored `ChatCompletionsBackend` with unified tool execution flow
  - Refactored `ClaudeBackend` with unified tool execution methods
  - Eliminates duplicate code paths between custom tools and MCP tools
  - Consistent error handling and status reporting across all tool types
  - Improved maintainability and extensibility for future tool systems

- **Gemini Backend Simplification**: Major architectural cleanup and consolidation
  - Removed `gemini_mcp_manager.py` module
  - Removed `gemini_trackers.py` module
  - Refactored `gemini.py` to use manual tool execution via base class
  - Streamlined tool handling and cleanup logic
  - Removed continuation logic and duplicate code
  - Updated `_gemini_formatter.py` for simplified tool conversion
  - Net reduction of 1,598 lines through consolidation
  - Improved maintainability and performance

- **Custom Tool System Enhancement**: Improved tool management and execution
  - Enhanced `ToolManager` with category management capabilities
  - Improved tool registration and validation system
  - Enhanced tool result handling and error reporting
  - Better support for async tool execution
  - Improved tool schema generation for LLM consumption

### Documentations, Configurations and Resources

- **Framework Interoperability Examples**: 8 new configuration files demonstrating external framework integration
  - **AG2 Examples**: `ag2_lesson_planner_example.yaml`, `ag2_and_langgraph_lesson_planner.yaml`, `ag2_and_openai_assistant_lesson_planner.yaml`
  - **LangGraph Examples**: `langgraph_lesson_planner_example.yaml`
  - **AgentScope Examples**: `agentscope_lesson_planner_example.yaml`
  - **OpenAI Assistants Examples**: `openai_assistant_lesson_planner_example.yaml`
  - **SmoLAgent Examples**: `smolagent_lesson_planner_example.yaml`
  - **Multi-Framework Examples**: `two_models_with_tools_example.yaml`

### Technical Details
- **Major Focus**: Framework interoperability for external agent integration, unified tool execution architecture, Gemini backend simplification, and configuration validation system
- **Contributors**: @Eric-Shang @praneeth999 @ncrispino @qidanrui @sonichi @Henry-811 and the MassGen team

## [0.1.5] - 2025-10-29

### Added
- **Memory System**: Complete long-term memory implementation with semantic retrieval
  - New `massgen/memory/` module with comprehensive memory management
  - **PersistentMemory** via mem0 integration for semantic fact storage and retrieval
  - **ConversationMemory** for short-term verbatim message tracking
  - **Automatic Context Compression** when approaching token limits
  - **Memory Sharing for Multi-Turn Conversations** with turn-aware filtering to prevent temporal leakage
  - **Session Management** for memory isolation and continuation across runs
  - **Qdrant Vector Database Integration** for efficient semantic search (server and local modes)
  - **Context Monitoring** with real-time token usage tracking
  - Fact extraction prompts with customizable LLM and embedding providers
  - Supports OpenAI, Anthropic, Groq, and other mem0-compatible providers

- **Memory Configuration Support**: New YAML configuration options
  - Memory enable/disable toggle at global and per-agent levels
  - Configurable compression thresholds (trigger_threshold, target_ratio)
  - Retrieval settings (limit, exclude_recent for smart retrieval)
  - Session naming for continuation and cross-session memory
  - LLM and embedding provider configuration for mem0
  - Qdrant connection settings (server/local mode, host, port, path)

### Changed
- **Chat Agent Enhancement**: Memory integration for agent workflows
  - Memory recording after agent responses (conversation and persistent)
  - Memory retrieval on restart/reset for context restoration
  - Integration with compression and context monitoring modules

- **Orchestrator Enhancement**: Memory coordination for multi-agent workflows
  - Memory initialization and management across agent lifecycles
  - Memory cleanup on orchestrator shutdown

### Documentations, Configurations and Resources

- **Memory Documentation**: Comprehensive memory system user guide
  - New `docs/source/user_guide/memory.rst`
  - Complete usage guide with quick start, configuration reference, and examples
  - Design decisions documentation explaining architecture choices
  - Troubleshooting guide for common memory issues
  - Monitoring and debugging instructions with log examples
  - API reference for PersistentMemory, ConversationMemory, and ContextMonitor

- **Configuration Examples**: 5 new memory-focused YAML configurations
  - `gpt5mini_gemini_context_window_management.yaml`: Multi-agent with context compression
  - `gpt5mini_gemini_research_to_implementation.yaml`: Research to implementation workflow
  - `gpt5mini_high_reasoning_gemini.yaml`: High reasoning agents with memory
  - `gpt5mini_gemini_baseline_research_to_implementation.yaml`: Baseline research workflow
  - `single_agent_compression_test.yaml`: Testing compression behavior

- **Infrastructure and Testing**:
  - Memory test suite with 4 test files in `massgen/tests/memory/`
  - Additional memory tests: `test_agent_memory.py`, `test_conversation_memory.py`, `test_orchestrator_memory.py`, `test_persistent_memory.py`

### Technical Details
- **Major Focus**: Long-term memory system with semantic retrieval and memory sharing for multi-turn conversations
- **Contributors**: @ncrispino @qidanrui @kitrakrev @sonichi @Henry-811 and the MassGen team

## [0.1.4] - 2025-10-27

### Added
- **Multimodal Generation Tools**: Comprehensive generation capabilities via OpenAI APIs
  - New `text_to_image_generation` tool for generating images from text prompts using DALL-E models
  - New `text_to_video_generation` tool for generating videos from text prompts
  - New `text_to_speech_continue_generation` tool for text-to-speech with continuation support
  - New `text_to_speech_transcription_generation` tool for audio transcription and generation
  - New `text_to_file_generation` tool for generating documents (PDF, DOCX, XLSX, PPTX)
  - New `image_to_image_generation` tool for image-to-image transformations
  - Implemented in `massgen/tool/_multimodal_tools/` with 6 new modules

- **Binary File Protection System**: Enhanced security for file operations
  - New binary file blocking in `PathPermissionManager` preventing text tools from reading binary files
  - Added `BINARY_FILE_EXTENSIONS` set covering images, videos, audio, archives, executables, and Office documents
  - New `_validate_binary_file_access()` method with intelligent tool suggestions
  - Prevents context pollution by blocking Read, read_text_file, and read_file tools from binary files
  - Comprehensive test suite in `test_binary_file_blocking.py`

- **Crawl4AI Web Scraping Integration**: Advanced web content extraction tool
  - New `crawl4ai_tool` for intelligent web scraping with LLM-powered extraction
  - Implemented in `massgen/tool/_web_tools/crawl4ai_tool.py`

### Changed
- **Multimodal File Size Limits**: Enhanced validation and automatic handling
  - Automatic image resizing for files exceeding size limits
  - Comprehensive size limit test suite in `test_multimodal_size_limits.py`
  - Enhanced validation in understand_audio and understand_video tools

### Documentations, Configurations and Resources

- **PyPI Package Documentation**: Standalone README for PyPI distribution
  - New `README_PYPI.md` with comprehensive package documentation
  - Improved package metadata and installation instructions

- **Release Management Documentation**: Comprehensive release workflow guide
  - New `docs/dev_notes/release_checklist.md` with step-by-step release procedures
  - Detailed checklist for testing, documentation, and deployment

- **Binary File Protection Documentation**: Enhanced protected paths user guide
  - Updated `docs/source/user_guide/protected_paths.rst` with binary file protection section
  - Documents 40+ protected binary file types and specialized tool suggestions

- **Configuration Examples**: 9 new YAML configuration files
  - **Generation Tools**: 8 multimodal generation configurations
    - `text_to_image_generation_single.yaml` and `text_to_image_generation_multi.yaml`
    - `text_to_video_generation_single.yaml` and `text_to_video_generation_multi.yaml`
    - `text_to_speech_generation_single.yaml` and `text_to_speech_generation_multi.yaml`
    - `text_to_file_generation_single.yaml` and `text_to_file_generation_multi.yaml`
  - **Web Scraping**: `crawl4ai_example.yaml` for Crawl4AI integration

### Technical Details
- **Major Focus**: Multimodal generation tools, binary file protection system, web scraping integration
- **Contributors**: @qidanrui @ncrispino @sonichi @Henry-811 and the MassGen team

## [0.1.3] - 2025-10-24

### Added
- **Post-Evaluation Workflow Tools**: Submit and restart capabilities for winning agents
  - New `PostEvaluationToolkit` class in `massgen/tool/workflow_toolkits/post_evaluation.py`
  - `submit` tool for confirming final answers
  - `restart_orchestration` tool for restarting with improvements and feedback
  - Post-evaluation phase where winning agent evaluates its own answer
  - Support for all API formats (Claude, Response API, Chat Completions)
  - Configuration parameter `enable_post_evaluation_tools` for opt-in/out

- **Custom Multimodal Understanding Tools**: Active tools for analyzing workspace files using OpenAI's GPT-4.1 API
  - New `understand_image` tool for analyzing images (PNG, JPEG, JPG) with detailed metadata extraction
  - New `understand_audio` tool for transcribing and analyzing audio files (WAV, MP3, FLAC, OGG)
  - New `understand_video` tool for extracting frames and analyzing video content (MP4, AVI, MOV, WEBM)
  - New `understand_file` tool for processing documents (PDF, DOCX, XLSX, PPTX) with text and metadata extraction
  - Works with any backend (uses OpenAI for analysis)
  - Returns structured JSON with comprehensive metadata

- **Docker Sudo Mode**: Enhanced Docker execution with privileged command support
  - New `use_sudo` parameter for Docker execution
  - Sudo mode for commands requiring elevated privileges
  - Enhanced security instructions and documentation
  - Test coverage in `test_code_execution.py`

### Changed
- **Interactive Config Builder Enhancement**: Improved workflow and provider handling
  - Better flow from automatic setup to config builder
  - Auto-detection of environment variables
  - Improved provider-specific configuration handling
  - Integrated multimodal tools selection in config wizard

### Fixed
- **System Message Warning**: Resolved deprecated system message configuration warning
  - Fixed system message handling in `agent_config.py`
  - Updated chat agent to properly handle system messages
  - Removed deprecated warning messages

- **Config Builder Issues**: Multiple configuration builder improvements
  - Fixed config display errors
  - Improved config saving across different provider types
  - Better error handling for missing configurations

### Documentations, Configurations and Resources

- **Multimodal Tools Documentation**: Comprehensive documentation for new multimodal tools
  - `docs/source/user_guide/multimodal.rst`: Updated with custom tools section
  - `massgen/tool/docs/multimodal_tools.md`: Complete 779-line technical documentation

- **Docker Sudo Mode Documentation**: Enhanced Docker execution documentation
  - `docs/source/user_guide/code_execution.rst`: Added 98 lines documenting sudo mode
  - `massgen/docker/README.md`: Updated with sudo mode instructions

- **Configuration Examples**: New example configurations
  - `configs/tools/multimodal_tools/understand_image.yaml`: Image analysis configuration
  - `configs/tools/multimodal_tools/understand_audio.yaml`: Audio transcription configuration
  - `configs/tools/multimodal_tools/understand_video.yaml`: Video analysis configuration
  - `configs/tools/multimodal_tools/understand_file.yaml`: Document processing configuration

- **Example Resources**: New test resources for v0.1.3 features
  - `massgen/configs/resources/v0.1.3-example/multimodality.jpg`: Image example
  - `massgen/configs/resources/v0.1.3-example/Sherlock_Holmes.mp3`: Audio example
  - `massgen/configs/resources/v0.1.3-example/oppenheimer_trailer_1920.mp4`: Video example
  - `massgen/configs/resources/v0.1.3-example/TUMIX.pdf`: PDF document example

- **Case Studies**: New case study demonstrating v0.1.3 features
  - `docs/source/examples/case_studies/multimodal-case-study-video-analysis.md`: Meta-level demonstration of multimodal video understanding with agents analyzing their own case study videos

### Technical Details
- **Major Focus**: Post-evaluation workflow tools, custom multimodal understanding tools, Docker sudo mode
- **Contributors**: @ncrispino @qidanrui @sonichi @Henry-811 and the MassGen team

## [0.1.2] - 2025-10-22

### Added
- **Claude 4.5 Haiku Support**: Added latest Claude Haiku model
  - New model: `claude-haiku-4-5-20251001`
  - Updated model registry in `backend/capabilities.py`

### Changed
- **Planning Mode Enhancement**: Intelligent automatic MCP tool blocking based on operation safety
  - New `_analyze_question_irreversibility()` method in orchestrator analyzes questions to determine if MCP operations are reversible
  - New `set_planning_mode_blocked_tools()`, `get_planning_mode_blocked_tools()`, and `is_mcp_tool_blocked()` methods in backend for selective tool control
  - Dynamically enables/disables planning mode - read-only operations allowed during coordination, write operations blocked
  - Planning mode supports different workspaces without conflicts
  - Zero configuration required - works transparently


- **Claude Model Priority**: Reorganized model list in capabilities registry
  - Changed default model from `claude-sonnet-4-20250514` to `claude-sonnet-4-5-20250929`
  - Moved `claude-opus-4-1-20250805` higher in priority order
  - Updated in both Claude and Claude Code backends

### Fixed
- **Grok Web Search**: Resolved web search functionality in Grok backend
  - Fixed `extra_body` parameter handling for Grok's Live Search API
  - New `_add_grok_search_params()` method for proper search parameter injection
  - Enhanced `_stream_with_custom_and_mcp_tools()` to support Grok-specific parameters
  - Improved error handling for conflicting search configurations
  - Better integration with Chat Completions API params handler

### Documentations, Configurations and Resources

- **Intelligent Planning Mode Case Study**: Complete feature documentation
  - `docs/source/examples/case_studies/INTELLIGENT_PLANNING_MODE.md`: Comprehensive guide for automatic planning mode
  - Demonstrates automatic irreversibility detection
  - Shows read/write operation classification
  - Includes examples for Discord, filesystem, and Twitter operations

- **Configuration Updates**: Enhanced YAML examples
  - Updated 5 planning mode configurations in `configs/tools/planning/` with selective blocking examples
  - Updated `three_agents_default.yaml` with Grok-4-fast model
  - Test coverage in `test_intelligent_planning_mode.py`

### Technical Details
- **Major Focus**: Intelligent planning mode with selective tool blocking, model support enhancements
- **Contributors**: @franklinnwren @ncrispino @qidanrui @sonichi @Henry-811 and the MassGen team

## [0.1.1] - 2025-10-20

### Added
- **Custom Tools System**: Complete framework for registering and executing user-defined Python functions as tools
  - New `ToolManager` class in `massgen/tool/_manager.py` for centralized tool registration and lifecycle management
  - Support for custom tools alongside MCP servers across all backends (Claude, Gemini, OpenAI Response API, Chat Completions, Claude Code)
  - Three tool categories: builtin, mcp, and custom tools
  - Automatic tool discovery with name prefixing and conflict resolution
  - Tool validation with parameter schema enforcement
  - Comprehensive test coverage in `test_custom_tools.py`

- **Voting Sensitivity & Answer Novelty Controls**: Three-tier system for multi-agent coordination
  - New `voting_sensitivity` parameter with three levels: "lenient", "balanced", "strict"
  - "Lenient": Accepts any reasonable answer
  - "Balanced": Default middle ground
  - "Strict": High-quality requirement
  - Answer novelty detection with `_check_answer_novelty()` method in `orchestrator.py` preventing duplicate answers
  - Configurable `max_new_answers_per_agent` limiting submissions per agent
  - Token-based similarity thresholds (50-70% overlap) for duplicate detection

- **Interactive Configuration Builder**: Wizard for creating YAML configurations
  - New `config_builder.py` module with step-by-step prompts
  - Guided workflow for backend selection, model configuration, and API key setup
  - Model-specific parameter handling (temperature, reasoning, verbosity)
  - Tool enablement options (MCP servers, custom tools, builtin tools)
  - Configuration validation and preview before saving
  - Integration with `massgen --config-builder` command

- **Backend Capabilities Registry**: Centralized feature support tracking
  - New `capabilities.py` module in `massgen/backend/` documenting backend capabilities
  - Feature matrix showing MCP, custom tools, multimodal, and code execution support
  - Runtime capability queries for backend selection

### Changed
- **Gemini Backend Architecture**: Major refactoring for improved maintainability
  - Extracted MCP management into `gemini_mcp_manager.py`
  - Extracted tracking logic into `gemini_trackers.py`
  - Extracted utilities into `gemini_utils.py`
  - New API params handler `_gemini_api_params_handler.py`
  - Improved session management and tool execution flow

- **Python Version Requirements**: Updated minimum supported version
  - Changed from Python 3.10+ to Python 3.11+ in `pyproject.toml`
  - Ensures compatibility with modern type hints and async features

- **API Key Setup Command**: Simplified command name
  - Renamed `massgen --setup-keys` to `massgen --setup` for brevity
  - Maintained all functionality for interactive API key configuration

- **Configuration Examples**: Updated example commands
  - Changed from `python -m massgen.cli` to simplified `massgen` command
  - Updated 40+ configuration files for consistency

### Fixed
- **CLI Configuration Selection**: Resolved error with large config lists
  - Fixed crash when using `massgen --select` with many available configurations
  - Improved pagination and display of configuration options
  - Enhanced error handling for configuration discovery

- **CLI Help System**: Improved documentation display
  - Fixed help text formatting in `massgen --help`
  - Better organization of command options and examples

### Documentations, Configurations and Resources

- **Case Study: Universal Code Execution via MCP**: Comprehensive v0.0.31 feature documentation
  - `docs/source/examples/case_studies/universal-code-execution-mcp.md`
  - Demonstrates pytest test creation and execution across backends
  - Shows command validation, security layers, and result interpretation

- **Documentation Updates**: Enhanced existing documentation
  - Added custom tools user guide and integration examples
  - Reorganized case studies for improved navigation
  - Updated configuration schema with new voting and tools parameters

- **Custom Tools Examples**: 40+ example configurations
  - Basic single-tool setups for each backend
  - Multi-agent configurations with custom tools
  - Integration examples combining MCP and custom tools
  - Located in `configs/tools/custom_tools/`

- **Voting Sensitivity Examples**: Configuration examples for voting controls
  - `configs/voting/gemini_gpt_voting_sensitivity.yaml`
  - Demonstrates lenient, balanced, and strict voting modes
  - Shows answer novelty threshold configuration

### Technical Details
- **Major Focus**: Custom tools system, voting sensitivity controls, interactive config builder, and comprehensive documentation
- **Contributors**: @qidanrui @ncrispino @praneeth999 @sonichi @Eric-Shang @Henry-811 and the MassGen team

## [0.1.0] - 2025-10-17 (PyPI Release)

### Added
- **PyPI Package Release**: Official MassGen package available on PyPI for easy installation via pip
- **Enhanced Documentation**: Comprehensive Sphinx documentation with improved structure and clarity
  - Rebuilt documentation with v0.1.0 version numbers
  - Improved backend capabilities table with split multimodal columns
  - Enhanced explanations for multimodal capabilities (Both, Understanding, Generation)
  - Updated homepage with v0.1.0 features

### Changed
- **Documentation Updates**: Major documentation improvements for PyPI release
  - Updated version numbers across all documentation files
  - Clarified multimodal capability terminology
  - Enhanced backend configuration guides

### Technical Details
- **Major Focus**: PyPI distribution and documentation improvements
- **Contributors**: @ncrispino @qidanrui @sonichi @Henry-811 and the MassGen team

## [0.0.32] - 2025-10-15

### Added
- **Docker Execution Mode**: Isolated command execution via Docker containers
  - New `DockerManager` class for persistent container lifecycle management
  - Container-based isolation with volume mounts for workspace and context paths
  - Configurable resource limits (CPU, memory) and network isolation modes (none/bridge/host)
  - Multi-agent support with dedicated containers per agent
  - Build script and comprehensive Dockerfile for massgen/mcp-runtime image
  - Enable via `command_line_execution_mode: "docker"` in agent configuration
  - Test suite in `test_code_execution.py` covering Docker and local execution modes

### Changed
- **Code Execution via MCP**: Extended v0.0.31's execute_command tool with Docker execution mode
  - Docker environment detection for automatic image verification
  - Local command execution remains available via `command_line_execution_mode: "local"`
  - Enhanced security layers for both local and Docker modes

- **Claude Code Backend**: Docker mode integration and MCP tool handling improvements
  - Automatic Bash tool disablement when Docker mode is enabled
  - MCP tool auto-permission support via `can_use_tool` hook
  - MCP server configuration format conversion (list to dict format)
  - System message enhancements to prevent git repository confusion in Docker

- **MCP Tools Architecture**: Major refactoring for simplicity and maintainability
  - Renamed `MultiMCPClient` to `MCPClient` reflecting simplified architecture
  - Removed deprecated `converters.py` module (275 lines removed)
  - Streamlined `client.py` with 1,029 lines removed through consolidation
  - Standardized type hints and module-level constants in `backend_utils.py`
  - Simplified exception handling in `exceptions.py` and security validation in `security.py`

### Fixed
- **Configuration Examples**: Improved configuration organization and usability
  - Renamed configuration files for better discoverability
  - Fixed CPU limits in example configurations to be runnable
  - Reverted gemini_mcp_test.yaml for consistency

- **Orchestrator Timeout and Cleanup**: Enhanced timeout handling and resource management
  - Improved timeout mechanisms for better reliability
  - Better cleanup of resources after orchestration sessions

### Documentations, Configurations and Resources

- **Docker Documentation**: New comprehensive Docker mode guide in `massgen/docker/README.md`
  - Complete Docker setup and usage documentation
  - Build scripts and Dockerfile with detailed comments
  - Security considerations for container-based execution
  - Resource management and isolation strategies

- **Code Execution Design**: Updated `CODE_EXECUTION_DESIGN.md` with Docker architecture details

- **New Configuration Files**: Added 5 Docker-specific example configurations
  - `docker_simple.yaml`: Basic single-agent Docker execution
  - `docker_multi_agent.yaml`: Multi-agent Docker deployment
  - `docker_with_resource_limits.yaml`: Resource-constrained Docker setup
  - `docker_claude_code.yaml`: Claude Code with Docker execution
  - `docker_verification.yaml`: Docker setup verification configuration

### Technical Details
- **Commits**: 17 commits including Docker execution, MCP refactoring, and Claude Code enhancements
- **Files Modified**: 32 files across backend, filesystem manager, MCP tools, and configurations
- **Major Features**: Docker execution mode, MCP architecture simplification, Claude Code Docker integration
- **New Module**: `_docker_manager.py` with DockerManager class (438 lines)
- **Dependencies Updated**: `docker>=7.0.0` added as optional dependency
- **Contributors**: @ncrispino @praneeth999 @qidanrui @sonichi @Henry-811 and the MassGen team

## [0.0.31] - 2025-10-14

### Added
- **Code Execution via MCP**: Universal command execution through MCP
  - New `execute_command` MCP tool enabling bash/shell execution across Claude, Gemini, OpenAI (Response API), and Chat Completions providers (Grok, ZAI, etc.)
  - AG2-inspired security with multi-layer protection: dangerous command sanitization, command filtering (whitelist/blacklist), PathPermissionManager hooks, path validation, timeout enforcement
  - Command filtering with regex patterns for whitelist/blacklist control
  - New MCP server `_code_execution_server.py` with subprocess-based local execution
  - Test coverage in `test_code_execution.py` covering basics, path validation, command sanitization, output handling, and virtual environment detection

- **Audio Generation Tools**: Text-to-speech and audio transcription capabilities via OpenAI APIs
  - New `generate_and_store_audio_no_input_audios` tool for generating audio from text using gpt-4o-audio-preview model
  - New `generate_text_with_input_audio` tool for transcribing audio files using OpenAI's Transcription API
  - New `convert_text_to_speech` tool for converting text to speech with gpt-4o-mini-tts model
  - Support for multiple voices (alloy, echo, fable, onyx, nova, shimmer, coral, sage) and audio formats (wav, mp3, opus, aac, flac)
  - Optional speaking instructions for tone and style control in TTS
  - Automatic workspace organization with timestamp-based filenames

- **Video Generation Tools**: Text-to-video generation via OpenAI's Sora-2 API
  - New `generate_and_store_video_no_input_images` tool for generating videos from text prompts
  - Support for Sora-2 model with configurable video duration
  - Asynchronous video generation with progress monitoring
  - Automatic MP4 format with workspace storage and organization

### Changed
- **AG2 Group Chat Support**: Enhanced AG2 adapter with native multi-agent group chat coordination
  - New group chat manager integration with AG2's `GroupChat` and `GroupChatManager`
  - Configurable speaker selection modes: auto (LLM-based), round_robin, manual
  - Support for nested conversations and workflow tools within group chat sessions
  - Automatic tool registration/unregistration for clean group chat lifecycle
  - Enhanced adapter architecture with group chat state management
  - Better agent reinitialization and termination logic for multi-turn group conversations
  - Test coverage in `test_ag2_adapter.py` and `test_ag2_utils.py`

- **File Operation Tracker**: Enhanced with auto-generated file exemptions
  - New `_is_auto_generated()` method to identify build artifacts and cache files
  - Prevents permission errors when agents clean up after running tests or builds

- **Path Permission Manager**: Added execute_command tool validation
  - Added `execute_command` to command_tools set for bash-like security validation
  - PreToolUse hooks now validate execute_command calls for dangerous patterns and path restrictions
  - Enhanced test coverage with 93 new test lines for command tool validation

- **Message Templates**: Added code execution result guidance
  - New system message guidance when `enable_command_execution=True` instructing agents to explain test results and command outputs in their answers
  - Better agent behavior for explaining what was tested and what results mean

### Documentations, Configurations and Resources

- **Code Execution Design Documentation**: Comprehensive technical design document
  - `CODE_EXECUTION_DESIGN.md`: Design doc covering architecture, security layers, implementation plan, virtual environment support, and future Docker enhancements

- **New Configuration Files**: Added 8 new example configurations
  - **AG2 Group Chat**: `ag2_groupchat.yaml`, `ag2_groupchat_gpt.yaml`
  - **Code Execution**: `basic_command_execution.yaml`, `code_execution_use_case_simple.yaml`, `command_filtering_whitelist.yaml`, `command_filtering_blacklist.yaml`,
  - **Audio Generation**: `single_gpt4o_audio_generation.yaml`, `gpt4o_audio_generation.yaml`
  - **Video Generation**: `single_gpt4o_video_generation.yaml`

### Technical Details
- **Commits**: 29 commits including AG2 group chat, code execution, audio/video generation, and enhancements
- **Files Modified**: 39 files with 3,649 insertions and 154 deletions
- **Major Features**: AG2 group chat, universal code execution via MCP, audio/video generation tools
- **New Tests**: `test_ag2_adapter.py`, `test_ag2_utils.py`, `test_code_execution.py`
- **Contributors**: @Eric-Shang @ncrispino @qidanrui @sonichi @Henry-811 and the MassGen team

## [0.0.30] - 2025-10-10

### Changed
- **Multimodal Support - Audio and Video Processing**: Extended v0.0.27's image-only multimodal foundation
  - Audio file support with WAV and MP3 formats for Chat Completions and Claude backends
  - Video file support with MP4, AVI, MOV, WEBM formats for Chat Completions and Claude backends
  - Audio/video path parameters (`audio_path`, `video_path`) for local files and HTTP/HTTPS URLs
  - Base64 encoding for local audio/video files with automatic MIME type detection
  - Configurable media file size limits (default 64MB, configurable via `media_max_file_size_mb`)
  - New audio/video content formatters in `_chat_completions_formatter.py` and `_claude_formatter.py`
  - Enhanced `base_with_mcp.py` with 340+ lines of multimodal content processing

- **Claude Code Backend SDK Update**: Updated to newer Agent SDK package
  - Migrated from `claude-code-sdk>=0.0.19` to `claude-agent-sdk>=0.0.22`
  - Updated internal SDK classes: `ClaudeCodeOptions` → `ClaudeAgentOptions`
  - Enhanced bash tool permission validation in `PathPermissionManager`
  - Improved system message handling with SDK preset support
  - New bash/shell/exec tool detection for dangerous operation prevention

- **Chat Completions Backend Enhancement**: Qwen API provider integration
  - Added Qwen API support to existing Chat Completions provider ecosystem
  - New `QWEN_API_KEY` environment variable support
  - Qwen-specific configuration examples for video understanding

### Fixed
- **Planning Mode Configuration**: Fixed crash when configuration lacks `coordination_config`
  - Added null check in `orchestrator.py` to prevent AttributeError
  - Improved graceful handling of missing planning mode configuration

- **Claude Code System Message Handling**: Resolved system message processing issues
  - Fixed system message extraction and formatting in `claude_code.py`
  - Better integration with Agent SDK for message handling

- **AG2 Adapter Import Ordering**: Resolved import sequence issues
  - Fixed import statements in `adapters/utils/ag2_utils.py`
  - Pre-commit isort formatting corrections

### Documentations, Configurations and Resources

- **Case Studies**: Comprehensive documentation for v0.0.28 and v0.0.29 features
  - `ag2-framework-integration.md`: AG2 adapter system and external framework integration
  - `mcp-planning-mode.md`: MCP Planning Mode design and implementation guide

- **New Configuration Files**: Added 7 new example configurations
  - `ag2/ag2_case_study.yaml`: AG2 framework integration case study configuration
  - `filesystem/cc_gpt5_gemini_filesystem.yaml`: Claude Code, GPT-5, and Gemini filesystem collaboration
  - `basic/single/single_gemini2.5pro.yaml`: Gemini 2.5 Pro single agent setup
  - `basic/single/single_openrouter_audio_understanding.yaml`: Audio understanding with OpenRouter
  - `basic/single/single_qwen_video_understanding.yaml`: Video understanding with Qwen API
  - `debug/test_sdk_migration.yaml`: Claude Code SDK migration testing

### Technical Details
- **Commits**: 20 commits including multimodal enhancements, Claude Code SDK migration, and documentation
- **Files Modified**: 25 files with 2,501 insertions and 84 deletions
- **Major Features**: Audio/video multimodal support, Claude Code Agent SDK migration, Qwen API integration
- **Dependencies Updated**: `anthropic>=0.61.0`, `claudecode>=0.0.12`
- **Contributors**: @ncrispino @praneeth999 @qidanrui @sonichi @Henry-811 and the MassGen team

## [0.0.29] - 2025-10-08

### Added
- **MCP Planning Mode**: New coordination strategy for irreversible MCP actions
  - New `CoordinationConfig` class with `enable_planning_mode` flag
  - Agents plan without executing during coordination, winning agent executes during final presentation
  - Orchestrator and frontend coordination UI support
  - Support for multiple backends: Response API, Chat Completions, and Gemini
  - Test suites in `test_mcp_blocking.py` and `test_gemini_planning_mode.py`

- **File Operation Tracker**: Read-before-delete enforcement for safer file operations
  - New `FileOperationTracker` class in `filesystem_manager/_file_operation_tracker.py`
  - Prevents agents from deleting files they haven't read first
  - Tracks read files and agent-created files (created files exempt from read requirement)
  - Directory deletion validation with comprehensive error messages

- **Path Permission Manager Enhancements**: Integration with FileOperationTracker
  - Added read/write/delete operation tracking methods to `PathPermissionManager`
  - Integration with `FileOperationTracker` for read-before-delete enforcement
  - Enhanced delete validation for files and batch operations
  - Extended test coverage in `test_path_permission_manager.py`

### Changed
- **Message Templates**: Improved multi-agent coordination guidance
  - Added `has_irreversible_actions` support for context path write access
  - Explicit temporary workspace path structure display for better agent understanding
  - Task handling priority hierarchy and simplified new_answer requirements
  - Unified evaluation guidance

- **MCP Tool Filtering**: Enhanced multi-level filtering capabilities
  - Combined backend-level and per-MCP-server tool filtering
  - MCP-server-specific `allowed_tools` can override backend-level settings
  - Merged `exclude_tools` from both backend and MCP server configurations

- **Backend Planning Mode Support**: Extended planning mode to multiple backends
  - Enhanced `base.py`, `response.py`, `chat_completions.py`, and `gemini.py`
  - Gemini backend now supports planning mode with session-based tool execution
  - Planning mode support across all major backend types


### Fixed
- **Circuit Breaker Logic**: Enhanced MCP server initialization in `base_with_mcp.py`
- **Final Answer Context**: Improved workspace copying when no new answer is provided
- **Multi-turn MCP Usage**: Addressed non-use of MCP in certain scenarios and improved final answer autonomy
- **Configuration Issues**: Updated Playwright automation configuration and fixed agent IDs

### Documentations, Configurations and Resources

- **MCP Planning Mode Examples**: 5 new planning mode configurations in `tools/planning/`
  - `five_agents_discord_mcp_planning_mode.yaml`: Discord MCP with planning mode (5 agents)
  - `five_agents_filesystem_mcp_planning_mode.yaml`: Filesystem MCP with planning mode
  - `five_agents_notion_mcp_planning_mode.yaml`: Notion MCP with planning mode (5 agents)
  - `five_agents_twitter_mcp_planning_mode.yaml`: Twitter MCP with planning mode (5 agents)
  - `gpt5_mini_case_study_mcp_planning_mode.yaml`: Case study configuration

- **MCP Example Configurations**: New example configurations for MCP integration in `tools/mcp/`
  - `five_agents_travel_mcp_test.yaml`: Travel planning MCP example (5 agents)
  - `five_agents_weather_mcp_test.yaml`: Weather service MCP example (5 agents)

- **Debug Configurations**: New debugging and testing utilities
  - `skip_coordination_test.yaml`: Test configuration for skipping coordination rounds

- **Documentation Updates**: Enhanced project documentation
  - Updated `permissions_and_context_files.md` in `backend/docs/` with file operation tracking details
  - Updated README with AG2 as optional installation and uv tool instructions

### Technical Details
- **Commits**: 23+ commits including planning mode, file operation tracking, and MCP enhancements
- **Files Modified**: 43 files across agent config, backend, filesystem manager, MCP tools, and configurations
- **Major Features**: MCP planning mode, FileOperationTracker, enhanced permissions, MCP tool filtering
- **New Tests**: `test_mcp_blocking.py`, `test_gemini_planning_mode.py` for planning mode validation
- **Contributors**: @ncrispino @franklinnwren @qidanrui @sonichi @praneeth999 and the MassGen team

## [0.0.28] - 2025-10-06

### Added
- **AG2 Framework Integration**: Complete adapter system for external agent frameworks
  - New `massgen/adapters/` module with base adapter architecture (`base.py`, `ag2_adapter.py`)
  - Support for AG2 ConversableAgent and AssistantAgent types
  - Code execution capabilities with multiple executor types: LocalCommandLineCodeExecutor, DockerCommandLineCodeExecutor, JupyterCodeExecutor, YepCodeCodeExecutor
  - Function/tool calling support for AG2 agents
  - Async execution with `a_generate_reply` for autonomous operation
  - AG2 utilities module for agent setup and API key management (`adapters/utils/ag2_utils.py`)

- **External Agent Backend**: New backend type for integrating external frameworks
  - New `ExternalAgentBackend` class supporting adapter registry pattern
  - Bridge between MassGen orchestration and external agent frameworks via adapters
  - Framework-specific configuration extraction and validation
  - Currently supports AG2 with extensible architecture for future frameworks

- **AG2 Test Suite**: Comprehensive test coverage for AG2 integration
  - `test_ag2_adapter.py`: AG2 adapter functionality tests
  - `test_agent_adapter.py`: Base adapter interface tests
  - `test_external_agent_backend.py`: External backend integration tests

### Fixed
- **MCP Circuit Breaker Logic**: Enhanced initialization for MCP servers
  - Improved circuit breaker state management in `base_with_mcp.py`
  - Better error handling during MCP server initialization

### Documentations, Configurations and Resources

- **AG2 Configuration Examples**: New YAML configurations demonstrating AG2 integration
  - `ag2/ag2_single_agent.yaml`: Basic single AG2 agent setup
  - `ag2/ag2_coder.yaml`: AG2 agent with code execution
  - `ag2/ag2_coder_case_study.yaml`: Multi-agent setup with AG2 and Gemini
  - `ag2/ag2_gemini.yaml`: AG2-Gemini hybrid configuration

- **Design Documentation**: Enhanced multi-source agent integration design
  - Updated `MULTI_SOURCE_AGENT_INTEGRATION_DESIGN.md` with AG2 adapter architecture

### Technical Details
- **Commits**: 12 commits including AG2 integration, testing, and configuration examples
- **Files Modified**: 18 files with 1,423 insertions and 71 deletions
- **Major Features**: AG2 framework integration, external agent backend, adapter architecture
- **New Module**: `massgen/adapters/` with AG2 support
- **Contributors**: @Eric-Shang @praneeth999 @qidanrui @sonichi @Henry-811 and the MassGen team

## [0.0.27] - 2025-10-03

### Added
- **Multimodal Support - Image Processing**: Foundation for multimodal content processing
  - New `stream_chunk` module with base classes for multimodal content (`base.py`, `text.py`, `multimodal.py`)
  - Support for image input and output in conversation messages
  - Image generation and understanding capabilities for multi-agent workflows
  - Multimodal content structure supporting images, audio, video, and documents (architecture ready)

- **File Upload and File Search**: Extended backend capabilities for document operations
  - File upload support integrated into Response backend via `_response_api_params_handler.py`
  - File search functionality for enhanced context retrieval and Q&A
  - Vector store management for file search operations
  - Cleanup utilities for uploaded files and vector stores

- **Workspace Tools Enhancements**: Extended MCP-based workspace management
  - Added `read_multimodal_files` tool for reading images as base64 data with MIME type

- **Claude Sonnet 4.5 Support**: Added latest Claude model to model mappings
  - Support for Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)
  - Updated model registry in `utils.py`

### Changed
- **Message Architecture Refactoring**: Extracted and refactored messaging system for multimodal support
  - Extracted `StreamChunk` classes into dedicated module (`massgen/stream_chunk/`)
  - Enhanced message templates for image generation workflows
  - Improved orchestrator and chat agent for multimodal message handling

- **Backend Enhancements**: Extended backends for multimodal and file operations
  - Enhanced `response.py` with image generation, understanding, and saving capabilities
  - Improved `base_with_mcp.py` with image handling for MCP-based workflows
  - New `api_params_handler` module for centralized parameter management including file uploads
  - Better streaming and error handling for multimodal content

- **Frontend Display Improvements**: Enhanced terminal UI for multimodal content
  - Refactored `rich_terminal_display.py` for rendering images in terminal
  - Improved message formatting and visual presentation

### Documentations, Configurations and Resources

- **New Configuration Files**: Added multimodal and enhanced filesystem examples
  - `gpt4o_image_generation.yaml`: Multi-agent image generation setup
  - `gpt5nano_image_understanding.yaml`: Multi-agent image understanding configuration
  - `single_gpt4o_image_generation.yaml`: Single agent image generation
  - `single_gpt5nano_image_understanding.yaml`: Single agent image understanding
  - `single_gpt5nano_file_search.yaml`: Single agent file search example
  - `grok4_gpt5_gemini_filesystem.yaml`: Enhanced filesystem configuration
  - Updated `claude_code_gpt5nano.yaml` with improved filesystem settings

- **Case Study Documentation**: New `multi-turn-filesystem-support.md` demonstrating v0.0.25 multi-turn capabilities with Bob Dylan website example

- **Presentation Materials**: New `applied-ai-summit.html` presentation with updated build scripts and call-to-action slides

- **Example Resources**: New `multimodality.jpg` for testing multimodal capabilities under `massgen/configs/resources/v0.0.27-example/`


### Technical Details
- **Major Features**: Image processing foundation, StreamChunk architecture, file upload/search, workspace multimodal tools
- **New Module**: `massgen/stream_chunk/` with base, text, and multimodal classes
- **Contributors**: @qidanrui @sonichi @praneeth999 @ncrispino @Henry-811 and the MassGen team

## [0.0.26] - 2025-10-01

### Added
- **File Deletion and Workspace Management**: New MCP tools for workspace file operations
  - New workspace deletion tools: `delete_file`, `delete_files_batch` for managing workspace files
  - New comparison tools: `compare_directories`, `compare_files` for file diffing
  - Consolidated `_workspace_tools_server.py` replacing previous `_workspace_copy_server.py`
  - Improved workspace cleanup mechanisms for multi-turn sessions
  - Proper permission checks for all file operations

- **File-Based Context Paths**: Support for single file access without exposing entire directories
  - Context paths can now be individual files, not just directories
  - Better control over agent access to specific reference files
  - Enhanced path validation distinguishing between file and directory contexts

- **Protected Paths Feature**: Prevent agents from modifying specific reference files
  - Protected paths within write-permitted context paths
  - Agents can read but not modify protected files


### Changed
- **Code Refactoring**: Improved module structure and import paths
  - Moved utility modules from `backend/utils/` to top-level `massgen/` directory
  - Relocated `api_params_handler`, `formatter`, and `filesystem_manager` modules
  - Simplified import paths and improved code discoverability
  - Better separation of concerns between backend-specific and shared utilities

- **Path Permission Manager**: Major enhancements to permission system
  - Enhanced `will_be_writable` logic for better permission state tracking
  - Improved path validation distinguishing between context paths and workspace paths
  - Comprehensive test coverage in `test_path_permission_manager.py`
  - Better handling of edge cases and nested path scenarios

### Fixed
- **Path Permission Edge Cases**: Resolved various permission checking issues
  - Fixed file context path validation logic
  - Corrected protected path matching behavior
  - Improved handling of nested paths and symbolic links
  - Better error handling for non-existent paths

### Documentations, Configurations and Resources

- **Example Resources**: Added v0.0.26 example resources for testing new features
  - Bob Dylan themed website with multiple pages and styles
  - Additional HTML, CSS, and JavaScript examples
  - Resources organized under `massgen/configs/resources/v0.0.26-example/`

- **Design Documentation**: Added comprehensive design documentation
  - New `file_deletion_and_context_files.md` documenting file deletion and context file features
  - Updated `permissions_and_context_files.md` with v0.0.26 features
  - Added detailed examples for protected paths and file context paths

- **Release Workflow Documentation**: Added comprehensive release example checklist
  - Step-by-step guide for release preparation in `docs/workflows/release_example_checklist.md`
  - Best practices for testing new features

- **Configuration Examples**: New configuration examples for v0.0.26 features
  - `gemini_gpt5nano_protected_paths.yaml`: Protected paths example
  - `gemini_gpt5nano_file_context_path.yaml`: File-based context paths example
  - `gemini_gemini_workspace_cleanup.yaml`: Workspace cleanup example

### Technical Details
- **Commits**: 20+ commits including file deletion tools, protected paths, and refactoring
- **Files Modified**: 46 files with 4,343 insertions and 836 deletions
- **Major Features**: File deletion tools, protected paths, file-based context paths, enhanced CLI prompts
- **New Tools**: `delete_file`, `delete_files_batch`, `compare_directories`, `compare_files` MCP tools
- **Contributors**: @praneeth999 @ncrispino @qidanrui @sonichi @Henry-811 and the MassGen team

## [0.0.25] - 2025-09-29

### Added
- **Multi-Turn Filesystem Support**: Complete implementation for persistent filesystem context across conversation turns
  - Automatic session management (no flag needed)
  - Persistent workspace management across conversation turns with `.massgen` directory
  - Workspace snapshot preservation and restoration between turns
  - Support for maintaining file context and modifications throughout multi-turn sessions
  - New configuration examples: `two_gemini_flash_filesystem_multiturn.yaml`, `grok4_gpt5_gemini_filesystem_multiturn.yaml`, `grok4_gpt5_claude_code_filesystem_multiturn.yaml`
  - Design documentation in `multi_turn_filesystem_design.md`

- **SGLang Backend Integration**: Added SGLang support to inference backend alongside existing vLLM
  - New SGLang server support with default port 30000 and `SGLANG_API_KEY` environment variable
  - SGLang-specific parameters support (e.g., `separate_reasoning` for guided generation)
  - Auto-detection between vLLM and SGLang servers based on configuration
  - New configuration `two_qwen_vllm_sglang.yaml` for mixed server deployments
  - Unified `InferenceBackend` class replacing separate `vllm.py` implementation
  - Updated documentation renamed from `vllm_implementation.md` to `inference_backend.md`

- **Enhanced Path Permission System**: New exclusion patterns and validation improvements
  - Added `DEFAULT_EXCLUDED_PATTERNS` for common directories (.git, node_modules, .venv, etc.)
  - New `will_be_writable` flag for better permission state tracking
  - Improved path validation with different handling for context vs workspace paths
  - Enhanced test coverage in `test_path_permission_manager.py`

### Changed
- **CLI Enhancements**: Major improvements to command-line interface
  - Enhanced logging with configurable log levels and file output
  - Improved error handling and user feedback

- **System Prompt Improvements**: Refined agent system prompts for better performance
  - Clearer instructions for file context handling
  - Better guidance for multi-turn conversations
  - Improved prompt templates for filesystem operations

- **Documentation Updates**: Comprehensive documentation improvements
  - Updated README with clearer installation instructions

### Fixed
- **Filesystem Manager**: Resolved workspace and permission issues
  - Fixed warnings for non-existent temporary workspaces
  - Better cleanup of old workspaces
  - Fixed relative path issues in workspace copy operations

- **Configuration Issues**: Multiple configuration fixes
  - Fixed multi-agent configuration templates
  - Fixed code generation prompts for consistency

### Technical Details
- **Commits**: 30+ commits including multi-turn filesystem, SGLang integration, and bug fixes
- **Files Modified**: 33 files with 3,188 insertions and 642 deletions
- **Major Features**: Multi-turn filesystem support, unified vLLM/SGLang backend, enhanced permissions
- **New Backend**: SGLang integration alongside existing vLLM support
- **Contributors**: @praneeth999 @ncrispino @qidanrui @sonichi @Henry-811 and the MassGen team

## [0.0.24] - 2025-09-26

### Added
- **vLLM Backend Support**: Complete integration with vLLM for high-performance local model serving
  - New `vllm.py` backend supporting VLLM's OpenAI-compatible API
  - Configuration examples in `three_agents_vllm.yaml`
  - Comprehensive documentation in `vllm_implementation.md`
  - Support for large-scale model inference with optimized performance

- **POE Provider Support**: Extended ChatCompletions backend to support POE (Platform for Open Exploration)
  - Added POE provider integration for accessing multiple AI models through a single platform
  - Seamless integration with existing ChatCompletions infrastructure

- **GPT-5-Codex Model Recognition**: Added GPT-5-Codex to model registry
  - Extended model mappings in `utils.py` to recognize gpt-5-codex as a valid OpenAI model

- **Backend Utility Modules**: Major refactoring for improved modularity
  - New `api_params_handler` module for centralized API parameter management
  - New `formatter` module for standardized message formatting across backends
  - New `token_manager` module for unified token counting and management
  - Extracted filesystem utilities into dedicated `filesystem_manager` module

### Changed
- **Backend Consolidation**: Significant code refactoring and simplification
  - Refactored `chat_completions.py` and `response.py` with cleaner API handler patterns
  - Moved filesystem management from `mcp_tools` to `backend/utils/filesystem_manager`
  - Improved separation of concerns with specialized handler modules
  - Enhanced code reusability across different backend implementations

- **Documentation Updates**: Improved documentation structure
  - Moved `permissions_and_context_files.md` to backend docs
  - Added multi-source agent integration design documentation
  - Updated filesystem permissions case study for v0.0.21 and v0.0.22 features

- **CI/CD Pipeline**: Enhanced automated release process
  - Updated auto-release workflow for better reliability
  - Improved GitHub Actions configuration

- **Pre-commit Configuration**: Updated code quality tools
  - Enhanced pre-commit hooks for better code consistency
  - Updated linting rules for improved code standards

### Fixed
- **Streaming Chunk Processing**: Resolved critical bugs in chunk handling
  - Fixed chunk processing errors in response streaming
  - Improved error handling for malformed chunks
  - Better resilience in stream processing pipeline

- **Gemini Backend Session Management**: Improved cleanup
  - Implemented proper session closure for google-genai aiohttp client
  - Added explicit cleanup of aiohttp sessions to prevent potential resource leaks

### Technical Details
- **Commits**: 35 commits including backend refactoring, vLLM integration, and bug fixes
- **Files Modified**: 50+ files across backend, utilities, configurations, and documentation
- **Major Refactor**: Complete restructuring of backend utilities
- **New Backend**: vLLM integration for high-performance local inference
- **Contributors**: @qidanrui @sonichi @praneeth999 @ncrispino @Henry-811 and the MassGen team

## [0.0.23] - 2025-09-24

### Added
- **Backend Architecture Refactoring**: Major consolidation of MCP functionality
  - New `base_with_mcp.py` base class consolidating common MCP functionality (488 lines)
  - Extracted shared MCP logic from individual backends into unified base class
  - Standardized MCP client initialization and error handling across all backends

- **Formatter Module**: Extracted message and tool formatting logic into dedicated module
  - New `massgen/formatter/` module with specialized formatters
  - `message_formatter.py`: Handles message formatting across backends
  - `tool_formatter.py`: Manages tool call formatting
  - `mcp_tool_formatter.py`: Specialized MCP tool formatting

### Changed
- **Backend Consolidation**: Massive code deduplication across backends
  - Reduced `chat_completions.py` by 700+ lines
  - Reduced `claude.py` by 700+ lines
  - Simplified `response.py` by 468+ lines
  - Total reduction: ~1,932 lines removed across core backend files

### Fixed
- **Coordination Table Display**: Fixed escape key handling on macOS
  - Updated `create_coordination_table.py` and `rich_terminal_display.py`

### Technical Details
- **Commits**: 20+ commits focusing on backend refactoring and infrastructure improvements
- **Files Modified**: 100+ files across backend, documentation, CI/CD, and presentation components
- **Lines Changed**: Net reduction of ~1,932 lines through backend consolidation
- **Major Refactor**: MCP functionality extracted into shared `base_with_mcp.py` base class
- **Contributors**: @qidanrui @ncrispino @Henry-811 and the MassGen team

## [0.0.22] - 2025-09-22

### Added
- **Workspace Copy Tools via MCP**: New file copying capabilities for efficient workspace operations
  - Added `workspace_copy_server.py` with MCP-based file copying functionality (369 lines)
  - Support for copying files and directories between workspaces
  - Efficient handling of large files with streaming operations
  - Testing infrastructure for copy operations

- **Configuration Organization**: Major restructuring of configuration files for better usability
  - New hierarchical structure: `basic/`, `providers/`, `tools/`, `teams/` directories
  - Added comprehensive `README.md` for configuration guide
  - New `BACKEND_CONFIGURATION.md` with detailed backend setup
  - Organized configs by use case and provider for easier navigation
  - Added provider-specific examples (Claude, OpenAI, Gemini, Azure)

- **Enhanced File Operations**: Improved file handling for large-scale operations
  - Clear all temporary workspaces at startup for clean state
  - Enhanced security validation in MCP tools

### Changed

- **Workspace Management**: Optimized workspace operations and path handling
  - Enhanced `filesystem_manager.py` with 193 additional lines
  - Run MCP servers through FastMCP to avoid banner displays

- **Backend Enhancements**: Improved backend capabilities
  - Improved `response.py` with better error handling

### Fixed
- **Write Tool Call Issues**: Resolved large character count problems
  - Fixed write tool call issues when dealing with large character counts

- **Path Resolution Issues**: Resolved various path-related bugs
  - Fixed relative/absolute path workspace issues
  - Improved path validation and normalization

- **Documentation Fixes**: Corrected multiple documentation issues
  - Fixed broken links in case studies
  - Fixed config file paths in documentation and examples
  - Corrected example commands with proper paths

### Technical Details
- **Commits**: 50+ commits including workspace copy, configuration restructuring, and documentation improvements
- **Files Modified**: 90+ files across configs, backend, mcp_tools, and documentation
- **Major Refactoring**: Configuration file reorganization into logical categories
- **New Documentation**: Added 762+ lines of documentation for configs and backends
- **Contributors**: @ncrispino @qidanrui @Henry-811 and the MassGen team

## [0.0.21] - 2025-09-19

### Added
- **Advanced Filesystem Permissions System**: Comprehensive permission management for agent file access
  - New `PathPermissionManager` class for granular permission validation
  - User context paths with configurable READ/WRITE permissions for multi-agent file sharing
  - Test suite for permission validation in `test_path_permission_manager.py`
  - Documentation in `permissions_and_context_files.md` for implementation guide

- **Function Hook Manager**: Per-agent function call permission system
  - Refactored `FunctionHookManager` to be per-agent rather than global
  - Pre-tool-use hooks for validating file operations before execution
  - Support for write permission enforcement during context agent operations
  - Integration with all function-based backends (OpenAI, Claude, Chat Completions)

- **Grok MCP Integration**: Extended MCP support to Grok backend
  - Migrated Grok backend to inherit from Chat Completions backend
  - Full MCP server support for Grok including stdio and HTTP transports
  - Filesystem support through MCP servers

- **New Configuration Files**: Added test and example configurations
  - `grok3_mini_mcp_test.yaml`: Grok MCP testing configuration
  - `grok3_mini_mcp_example.yaml`: Grok MCP usage example
  - `grok3_mini_streamable_http_test.yaml`: Grok HTTP streaming test
  - `grok_single_agent.yaml`: Single Grok agent configuration
  - `fs_permissions_test.yaml`: Filesystem permissions testing configuration

### Changed
- **Backend Architecture**: Unified backend implementations and permission support
  - Grok backend refactored to use Chat Completions backend
  - All backends now support per-agent permission management
  - Enhanced context file support across Claude, Gemini, and OpenAI backends

### Technical Details
- **Commits**: 20+ commits including permission system, Grok MCP, and terminal improvements
- **Files Modified**: 40+ files across backends, MCP tools, permissions, and display modules
- **New Features**: Filesystem permissions, per-agent hooks, Grok MCP via Chat Completions
- **Contributors**: @Eric-Shang @ncrispino @qidanrui @Henry-811 and the MassGen team

## [0.0.20] - 2025-09-17

### Added
- **Claude Backend MCP Support**: Extended MCP (Model Context Protocol) integration to Claude backend
  - Filesystem support through MCP servers (`FilesystemSupport.MCP`) for Claude backend
  - Support for both stdio and HTTP-based MCP servers with Claude Messages API
  - Seamless integration with existing Claude function calling and tool use
  - Recursive execution model allowing Claude to autonomously chain multiple tool calls in sequence without user intervention
  - Enhanced error handling and retry mechanisms for Claude MCP operations

- **MCP Configuration Examples**: New YAML configurations for Claude MCP usage
  - `claude_mcp_test.yaml`: Basic Claude MCP testing with test server
  - `claude_mcp_example.yaml`: Claude MCP integration example
  - `claude_streamable_http_test.yaml`: HTTP transport testing for Claude MCP

- **Documentation**: Enhanced MCP technical documentation
  - `MCP_IMPLEMENTATION_CLAUDE_BACKEND.md`: Complete technical documentation for Claude MCP integration
  - Detailed architecture diagrams and implementation guides

### Changed
- **Backend Enhancements**: Improved MCP support across backends
  - Extended MCP integration from Gemini and Chat Completions to include Claude backend
  - Enhanced error reporting and debugging for MCP operations
  - Added Kimi/Moonshot API key support in Chat Completions backend

### Technical Details
- **New Features**: Claude backend MCP integration with recursive execution model
- **Files Modified**: Claude backend modules (`claude.py`), MCP tools, configuration examples
- **MCP Coverage**: Major backends now support MCP (Claude, Gemini, Chat Completions including OpenAI)
- **Contributors**: @praneeth999 @qidanrui @sonichi @ncrispino @Henry-811 MassGen development team

## [0.0.19] - 2025-09-15

### Added
- **Coordination Tracking System**: Comprehensive tracking of multi-agent coordination events
  - New `coordination_tracker.py` with `CoordinationTracker` class for capturing agent state transitions
  - Event-based tracking with timestamps and context preservation
  - Support for recording answers, votes, and coordination phases
  - New `create_coordination_table.py` utility in `massgen/frontend/displays/` for generating coordination reports

- **Enhanced Agent Status Management**: New enums for better state tracking
  - Added `ActionType` enum in `massgen/utils.py`: NEW_ANSWER, VOTE, VOTE_IGNORED, ERROR, TIMEOUT, CANCELLED
  - Added `AgentStatus` enum in `massgen/utils.py`: STREAMING, VOTED, ANSWERED, RESTARTING, ERROR, TIMEOUT, COMPLETED
  - Improved state machine for agent coordination lifecycle

### Changed
- **Frontend Display Enhancements**: Improved terminal interface with coordination visualization
  - Modified `massgen/frontend/displays/rich_terminal_display.py` to add coordination table display method
  - Added new terminal menu option 'r' to display coordination table
  - Enhanced menu system with better organization of debugging tools
  - Support for rich-formatted tables showing agent interactions across rounds

### Technical Details
- **Commits**: 20+ commits including coordination tracking system and frontend enhancements
- **Files Modified**: 5+ files across coordination tracking, frontend displays, and utilities
- **New Features**: Coordination event tracking with visualization capabilities
- **Contributors**: @ncrispino @qidanrui @sonichi @a5507203 @Henry-811 and the MassGen team

## [0.0.18] - 2025-09-12

### Added
- **Chat Completions MCP Support**: Extended MCP (Model Context Protocol) integration to ChatCompletions-based backends
  - Full MCP support for all Chat Completions providers (Cerebras AI, Together AI, Fireworks AI, Groq, Nebius AI Studio, OpenRouter)
  - Filesystem support through MCP servers (`FilesystemSupport.MCP`) for Chat Completions backend
  - Cross-provider function calling compatibility enabling seamless MCP tool execution across different providers
  - Universal MCP server compatibility with existing stdio and streamable-http transports

- **New MCP Configuration Examples**: Added 9 new Chat Completions MCP configurations
  - GPT-OSS configurations: `gpt_oss_mcp_example.yaml`, `gpt_oss_mcp_test.yaml`, `gpt_oss_streamable_http_test.yaml`
  - Qwen API configurations: `qwen_api_mcp_example.yaml`, `qwen_api_mcp_test.yaml`, `qwen_api_streamable_http_test.yaml`
  - Qwen Local configurations: `qwen_local_mcp_example.yaml`, `qwen_local_mcp_test.yaml`, `qwen_local_streamable_http_test.yaml`

- **Enhanced LMStudio Backend**: Improved local model support
  - Better tracking of attempted model loads
  - Improved server output handling and error reporting

### Changed
- **Backend Architecture**: Major MCP framework expansion
  - Extended existing v0.0.15 MCP infrastructure to support all ChatCompletions providers
  - Refactored `chat_completions.py` with 1200+ lines of MCP integration code
  - Enhanced error handling and retry mechanisms for provider-specific quirks

- **CLI Improvements**: Better backend creation and provider detection
  - Enhanced backend creation logic for improved provider handling
  - Better system message handling for different backend types

### Technical Details
- **Main Feature**: Chat Completions MCP integration enabling all providers to use MCP tools
- **Files Modified**: 20+ files across backend, mcp_tools, configurations, and CLI
- **Contributors**: @praneeth999 @qidanrui @sonichi @a5507203 @ncrispino @Henry-811 and the MassGen team

## [0.0.17] - 2025-09-10

### Added
- **OpenAI Backend MCP Support**: Extended MCP (Model Context Protocol) integration to OpenAI backend
  - Full MCP tool discovery and execution capabilities for OpenAI models
  - Support for both stdio and HTTP-based MCP servers with OpenAI
  - Seamless integration with existing OpenAI function calling
  - Robust error handling and retry mechanisms

- **MCP Configuration Examples**: New YAML configurations for OpenAI MCP usage
  - `gpt5_mini_mcp_test.yaml`: Basic OpenAI MCP testing with test server
  - `gpt5_mini_mcp_example.yaml`: Weather service integration example for OpenAI
  - `gpt5_mini_streamable_http_test.yaml`: HTTP transport testing for OpenAI MCP
  - Enhanced existing multi-agent configurations with OpenAI MCP support

- **Documentation**: Added case studies and technical documentation
  - `unified-filesystem-mcp-integration.md`: Case study demonstrating unified filesystem capabilities with MCP integration across multiple backends (from v0.0.16)
  - `MCP_INTEGRATION_RESPONSE_BACKEND.md`: Technical documentation for MCP integration with response backends

### Changed
- **Backend Enhancements**: Improved MCP support across backends
  - Extended MCP integration from Gemini and Claude Code to include OpenAI backend
  - Unified MCP tool handling across all supported backends
  - Enhanced error reporting and debugging for MCP operations

### Technical Details
- **New Features**: OpenAI backend MCP integration
- **Documentation**: Added case study for unified filesystem MCP integration
- **Contributors**: @praneeth999 @qidanrui @sonichi @ncrispino @a5507203 @Henry-811 and the MassGen team

## [0.0.16] - 2025-09-08

### Added
- **Unified Filesystem Support with MCP Integration**: Advanced filesystem capabilities designed for all backends
  - Complete `FilesystemManager` class providing unified filesystem access with extensible backend support
  - Currently supports Gemini and Claude Code backends, designed for seamless expansion to all backends
  - MCP-based filesystem operations enabling file manipulation, workspace management, and cross-agent collaboration

- **Expanded Configuration Library**: New YAML configurations for various use cases
  - **Gemini MCP Filesystem Testing**: `gemini_mcp_filesystem_test.yaml`, `gemini_mcp_filesystem_test_sharing.yaml`, `gemini_mcp_filesystem_test_single_agent.yaml`, `gemini_mcp_filesystem_test_with_claude_code.yaml`
  - **Hybrid Model Setups**: `geminicode_gpt5nano.yaml`

- **Case Studies**: Added comprehensive case studies from previous versions
  - `gemini-mcp-notion-integration.md`: Gemini MCP Notion server integration and productivity workflows
  - `claude-code-workspace-management.md`: Claude Code context sharing and workspace management demonstrations


### Technical Details
- **Commits**: 30+ commits including workspace redesign and orchestrator enhancements
- **Files Modified**: 40+ files across orchestrator, mcp_tools, configurations, and case studies
- **New Architecture**: Complete workspace management system with FilesystemManager
- **Contributors**: @ncrispino @a5507203 @sonichi @Henry-811 and the MassGen team

## [0.0.15] - 2025-09-05

### Added
- **MCP (Model Context Protocol) Integration Framework**: Complete implementation for external tool integration
  - New `massgen/mcp_tools/` package with 8 core modules for MCP support
  - Multi-server MCP client supporting simultaneous connections to multiple MCP servers
  - Two transport types: stdio (process-based) and streamable-http (web-based)
  - Circuit breaker patterns for fault tolerance and reliability
  - Comprehensive security framework with command sanitization and validation
  - Automatic tool discovery with name prefixing for multi-server setups

- **Gemini MCP Support**: Full MCP integration for Gemini backend
  - Session-based tool execution via Gemini SDK
  - Automatic tool discovery and calling capabilities
  - Robust error handling with exponential backoff
  - Support for both stdio and HTTP-based MCP servers
  - Integration with existing Gemini function calling

- **Test Infrastructure for MCP**: Development and testing utilities
  - Simple stdio-based MCP test server (`mcp_test_server.py`)
  - FastMCP streamable-http test server (`test_http_mcp_server.py`)
  - Comprehensive test suite for MCP integration

- **MCP Configuration Examples**: New YAML configurations for MCP usage
  - `gemini_mcp_test.yaml`: Basic Gemini MCP testing
  - `gemini_mcp_example.yaml`: Weather service integration example
  - `gemini_streamable_http_test.yaml`: HTTP transport testing
  - `multimcp_gemini.yaml`: Multi-server MCP configuration
  - Additional Claude Code MCP configurations

### Changed
- **Dependencies**: Updated package requirements
  - Added `mcp>=1.12.0` for official MCP protocol support
  - Added `aiohttp>=3.8.0` for HTTP-based MCP communication
  - Updated `pyproject.toml` and `requirements.txt`

- **Documentation**: Enhanced project documentation
  - Created technical analysis documents for Gemini MCP integration
  - Added comprehensive MCP tools README with architecture diagrams
  - Added security and troubleshooting guides for MCP

### Technical Details
- **Commits**: 40+ commits including MCP integration, documentation, and bug fixes
- **Files Modified**: 35+ files across MCP modules, backends, configurations, and tests
- **Security Features**: Configurable security levels (strict/moderate/permissive)
- **Contributors**: @praneeth999 @qidanrui @sonichi @a5507203 @ncrispino @Henry-811 and the MassGen team

## [0.0.14] - 2025-09-02

### Added
- **Enhanced Logging System**: Improved logging infrastructure with add_log feature
  - Better log organization and preservation for multi-agent workflows
  - Enhanced workspace management for Claude Code agents
  - New final answer directory structure in Claude Code and logs for storing final results

### Documentation
- **Release Documents**: Updated release documentation and materials
  - Updated CHANGELOG.md for better release tracking
  - Removed unnecessary use case documentation

### Technical Details
- **Commits**: 19 commits
- **Files Modified**: Logging system enhancements, documentation updates
- **New Features**: Enhanced logging, improved final presentation logging for Claude Code
- **Contributors**: @qidanrui @sonichi and the MassGen team

## [0.0.13] - 2025-08-28

### Added
- **Unified Logging System**: Better logging infrastructure for better debugging and monitoring
  - New centralized `logger_config.py` with colored console output and file logging
  - Debug mode support via `--debug` CLI flag for verbose logging
  - Consistent logging format across all backends, including Claude, Gemini, Grok, Azure OpenAI, and other providers
  - Color-coded log levels for better visibility (DEBUG: cyan, INFO: green)

- **Windows Platform Support**: Enhanced cross-platform compatibility
  - Windows-specific fixes for terminal display and color output
  - Improved path handling for Windows file systems
  - Better process management on Windows platform

### Changed
- **Frontend Improvements**: Refined display
  - Enhanced rich terminal display formatting to not show debug info in the final presentation

- **Documentation Updates**: Improved project documentation
  - Updated CONTRIBUTING.md with better guidelines
  - Enhanced README with logging configuration details
  - Renamed roadmap from v0.0.13 to v0.0.14 for future planning

### Technical Details
- **Commits**: 35+ commits including new logging system and Windows support
- **Files Modified**: 24+ files across backend, frontend, logging, and CLI modules
- **New Features**: Unified logging system with debug mode, Windows platform support
- **Contributors**: @qidanrui @sonichi @Henry-811 @JeffreyCh0 @voidcenter and the MassGen team

## [0.0.12] - 2025-08-27

### Added
- **Enhanced Claude Code Agent Context Sharing**: Improved multiple Claude Code agent coordination with workspace sharing
  - New workspace snapshot stored in orchestrator's space for better context management
  - New temporary working directory for each agent, stored in orchestrator's space
  - Claude Code agents can now share context by referencing their own temporary working directory in the orchestrator's workspace
  - Anonymous agent context mapping when referencing temporary directories
  - Improved context preservation across agent coordination cycles

- **Advanced Orchestrator Configurations**: Enhanced orchestrator configurations
  - Configurable system message support for orchestrator
  - New snapshot and temporary workspace settings for better context management

### Changed
- **Documentation Updates**: documentation improvements
  - Updated README with current features and usage examples
  - Improved configuration examples and setup instructions

### Technical Details
- **Commits**: 10+ commits including context sharing enhancements, workspace management, and configuration improvements
- **Files Modified**: 20+ files across orchestrator, backend, configuration, and documentation
- **New Features**: Enhanced Claude Code agent workspace sharing with temporary working directories and snapshot mechanisms
- **Contributors**: @qidanrui @sonichi @Henry-811 @JeffreyCh0 @voidcenter and the MassGen team

## [0.0.11] - 2025-08-25

### Known Issues
- **System Message Handling in Multi-Agent Coordination**: Critical issues affecting Claude Code agents
  - **Lost System Messages During Final Presentation** (`orchestrator.py:1183`)
    - Claude Code agents lose domain expertise during final presentation
    - ConfigurableAgent doesn't properly expose system messages via `agent.system_message`
  - **Backend Ignores System Messages** (`claude_code.py:754-762`)
    - Claude Code backend filters out system messages from presentation_messages
    - Only processes user messages, causing loss of agent expertise context
    - System message handling only works during initial client creation, not with `reset_chat=True`
  - **Ambiguous Configuration Sources**
    - Multiple conflicting system message sources: `custom_system_instruction`, `system_prompt`, `append_system_prompt`
    - Backend parameters silently override AgentConfig settings
    - Unclear precedence and behavior documentation
  - **Architecture Violations**
    - Orchestrator contains Claude Code-specific implementation details
    - Tight coupling prevents easy addition of new backends
    - Violates separation of concerns principle

### Fixed
- **Custom System Message Support**: Enhanced system message configuration and preservation
  - Added `base_system_message` parameter to conversation builders for agent's custom system message
  - Orchestrator now passes agent's `get_configurable_system_message()` to conversation builders
  - Custom system messages properly combined with MassGen coordination instructions instead of being overwritten
  - Backend-specific system prompt customization (system_prompt, append_system_prompt)
- **Claude Code Backend Enhancements**: Improved integration and configuration
  - Better system message handling and extraction
  - Enhanced JSON structured response parsing
  - Improved coordination action descriptions
- **Final Presentation & Agent Logic**: Enhanced multi-agent coordination (#135)
  - Improved final presentation handling for Claude Code agents
  - Better coordination between agents during final answer selection
  - Enhanced CLI presentation logic
  - Agent configuration improvements for workflow coordination
- **Evaluation Message Enhancement**: Improved synthesis instructions
  - Changed to "digest existing answers, combine their strengths, and do additional work to address their weaknesses"
  - Added "well" qualifier to evaluation questions
  - More explicit guidance for agents to synthesize and improve upon existing answers

### Changed
- **Documentation Updates**: Enhanced project documentation
  - Renamed roadmap from v0.0.11 to v0.0.12 for future planning
  - Updated README with latest features and improvements
  - Improved CONTRIBUTING guidelines
  - Enhanced configuration examples and best practices

### Added
- **New Configuration Files**: Introduced additional YAML configuration files
  - Added `multi_agent_playwright_automation.yaml` for browser automation workflows

### Removed
- **Deprecated Configurations**: Cleaned up configuration files
  - Removed `gemini_claude_code_paper_search_mcp.yaml`
  - Removed `gpt5_claude_code_paper_search_mcp.yaml`
- **Gemini CLI Tests**: Removed Gemini CLI related tests

### Technical Details
- **Commits**: 25+ commits including bug fixes, feature additions, and improvements
- **Files Modified**: 35+ files across backend, orchestrator, frontend, configuration, and documentation
- **New Configuration**: `multi_agent_playwright_automation.yaml` for browser automation workflows
- **Contributors**: @qidanrui @Leezekun @sonichi @voidcenter @Daucloud @Henry-811 and the MassGen team

## [0.0.10] - 2025-08-22

### Added
- **Azure OpenAI Support**: Integration with Azure OpenAI services
  - New `azure_openai.py` backend with async streaming capabilities
  - Support for Azure-hosted GPT-4.1 and GPT-5-chat models
  - Configuration examples for single and multi-agent Azure setups
  - Test suite for Azure OpenAI functionality
- **Enhanced Claude Code Backend**: Major refactoring and improvements
  - Simplified MCP (Model Context Protocol) integration
- **Final Presentation Support**: New orchestrator presentation capabilities
  - Support for final answer presentation in multi-agent scenarios
  - Fallback mechanisms for presentation generation
  - Test coverage for presentation functionality

### Fixed
- **Claude Code MCP**: Cleaned up and simplified MCP implementation
  - Removed redundant MCP server and transport modules
- **Configuration Management**: Improved YAML configuration handling
  - Fixed Azure OpenAI deployment configurations
  - Updated model mappings for Azure services

### Changed
- **Backend Architecture**: Significant refactoring of backend systems
  - Consolidated Azure OpenAI implementation using AsyncAzureOpenAI
  - Improved error handling and streaming capabilities
  - Enhanced async support across all backends
- **Documentation Updates**: Enhanced project documentation
  - Updated README with Azure OpenAI setup instructions
  - Renamed roadmap from v0.0.10 to v0.0.11
  - Improved presentation materials for DataHack Summit 2025
- **Test Infrastructure**: Expanded test coverage
  - Added comprehensive Azure OpenAI backend tests
  - Integration tests for final presentation functionality
  - Simplified test structure with better coverage

### Removed
- **Deprecated MCP Components**: Removed unused MCP modules
  - Removed standalone MCP client, transport, and server implementations
  - Cleaned up MCP test files and testing checklist
  - Simplified Claude Code backend by removing redundant MCP code

### Technical Details
- **Commits**: 35+ commits including Azure OpenAI integration and Claude Code improvements
- **Files Modified**: 30+ files across backend, configuration, tests, and documentation
- **New Backend**: Azure OpenAI backend with full async support
- **Contributors**: @qidanrui @Leezekun @sonichi and the MassGen team

## [0.0.9] - 2025-08-22

### Added
- **Quick Start Guide**: Comprehensive quickstart documentation in README
  - Streamlined setup instructions for new users
  - Example configurations for getting started quickly
  - Clear installation and usage steps
- **Multi-Agent Configuration Examples**: New configuration files for various setups
  - Paper search configuration with GPT-5 and Claude Code
  - Multi-agent setups with different model combinations
- **Roadmap Documentation**: Added comprehensive roadmap for version 0.0.10
  - Focused on Claude Code context sharing between agents
  - Multi-agent context synchronization planning
  - Enhanced backend features and CLI improvements roadmap

### Fixed
- **Web Search Processing**: Fixed bug in response handling for web search functionality
  - Improved error handling in web search responses
  - Better streaming of search results
- **Rich Terminal Display**: Fixed rendering issues in terminal UI
  - Resolved display formatting problems
  - Improved message rendering consistency

### Changed
- **Claude Code Integration**: Optimized Claude Code implementation
  - MCP (Model Context Protocol) integration
  - Streamlined Claude Code backend configuration
- **Documentation Updates**: Enhanced project documentation
  - Updated README with quickstart guide
  - Added CONTRIBUTING.md guidelines
  - Improved configuration examples

### Technical Details
- **Commits**: 10 commits including bug fixes, code cleanup, and documentation updates
- **Files Modified**: Multiple files across backend, configurations, and documentation
- **Contributors**: @qidanrui @sonichi @Leezekun @voidcenter @JeffreyCh0 @stellaxiang

## [0.0.8] - 2025-08-18

### Added
- **Timeout Management System**: Timeout capabilities for better control and time management
  - New `TimeoutConfig` class for configuring timeout settings at different levels
  - Orchestrator-level timeout with graceful fallback
  - Added `fast_timeout_example.yaml` configuration demonstrating conservative timeout settings
  - Test suite for timeout mechanisms in `test_timeout.py`
  - Timeout indicators in Rich Terminal Display showing remaining time
- **Enhanced Display Features**: Improved visual feedback and user experience
  - Optimized message display formatting for better readability
  - Enhanced status indicators for timeout warnings and fallback notifications
  - Improved coordination UI with better multi-agent status tracking

### Fixed
- **Display Optimization**: Multiple improvements to message rendering
  - Fixed message display synchronization issues
  - Optimized terminal display refresh rates
  - Improved handling of concurrent agent outputs
  - Better formatting for multi-line responses
- **Configuration Management**: Enhanced robustness of configuration loading
  - Fixed import ordering issues in CLI module
  - Improved error handling for missing configurations
  - Better validation of timeout settings

### Changed
- **Orchestrator Architecture**: Simplified and enhanced timeout implementation
  - Refactored timeout handling to be more efficient and maintainable
  - Improved graceful degradation when timeouts occur
  - Better integration with frontend displays for timeout notifications
  - Enhanced error messages for timeout scenarios
- **Code Cleanup**: Removed deprecated configurations and improved code organization
  - Removed obsolete `two_agents_claude_code` configuration
  - Cleaned up unused imports and redundant code
  - Reformatted files for better consistency
- **CLI Enhancements**: Improved command-line interface functionality
  - Better timeout configuration parsing
  - Enhanced error reporting for timeout scenarios
  - Improved help documentation for timeout settings

### Technical Details
- **Commits**: 18 commits including various optimizations and bug fixes
- **Files Modified**: 13+ files across orchestrator, frontend, configuration, and test modules
- **Key Features**: Timeout management system with graceful fallback, enhanced display optimizations
- **New Configuration**: `fast_timeout_example.yaml` for time-conscious usage
- **Contributors**: @qidanrui @Leezekun @sonichi @voidcenter

## [0.0.7] - 2025-08-15

### Added
- **Local Model Support**: Complete integration with LM Studio for running open-weight models locally
  - New `lmstudio.py` backend with automatic server management
  - Automatic model downloading and loading capabilities
  - Zero-cost reporting for local model usage
- **Extended Provider Support**: Enhanced ChatCompletionsBackend to support multiple providers
  - Cerebras AI, Together AI, Fireworks AI, Groq, Nebius AI Studio, OpenRouter
  - Provider-specific environment variable detection
  - Automatic provider name inference from base URLs
- **New Configuration Files**: Added configurations for local and hybrid model setups
  - `lmstudio.yaml`: Single agent configuration for LM Studio
  - `two_agents_opensource_lmstudio.yaml`: Hybrid setup with GPT-5 and local Qwen model
  - `gpt5nano_glm_qwen.yaml`: Three-agent setup combining Cerebras, ZAI GLM-4.5, and local Qwen
  - Updated `three_agents_opensource.yaml` for open-source model combinations

### Fixed
- **Backend Stability**: Improved error handling across all backend systems
  - Fixed API key resolution and client initialization
  - Enhanced provider name detection and configuration
  - Resolved streaming issues in ChatCompletionsBackend
- **Documentation**: Corrected references and updated model naming conventions
  - Fixed GPT model references in documentation diagrams
  - Updated case study file naming consistency

### Changed
- **Backend Architecture**: Refactored ChatCompletionsBackend for better extensibility
  - Improved provider registry and configuration management
  - Enhanced logging and debugging capabilities
  - Streamlined message processing and tool handling
- **Dependencies**: Added new requirements for local model support
  - Added `lmstudio==1.4.1` for LM Studio Python SDK integration
- **Documentation Updates**: Enhanced documentation for local model usage
  - Updated environment variables documentation
  - Added setup instructions for LM Studio integration
  - Improved backend configuration examples

### Technical Details
- **Commits**: 16 commits including merge pull requests #80 and #100
- **Files Modified**: 17+ files across backend, configuration, documentation, and CLI modules
- **New Dependencies**: LM Studio SDK (`lmstudio==1.4.1`)
- **Contributors**: @qidanrui @sonichi @Leezekun @praneeth999 @voidcenter

## [0.0.6] - 2025-08-13

### Added
- **GLM-4.5 Model Support**: Integration with ZhipuAI's GLM-4.5 model family
  - Added GLM-4.5 backend support in `chat_completions.py`
  - New configuration file `zai_glm45.yaml` for GLM-4.5 agent setup
  - Updated `zai_coding_team.yaml` with GLM-4.5 integration
  - Added GLM-4.5 model mappings and environment variable support
- **Enhanced Reasoning Display**: Improved reasoning presentation for GLM models
  - Added reasoning start and completion indicators in frontend displays
  - Enhanced coordination UI to show reasoning progress
  - Better visual formatting for reasoning states in terminal display

### Fixed
- **Claude Code Backend**: Updated default allowed tools configuration
  - Fixed default tools setup in `claude_code.py` backend

### Changed
- **Documentation Updates**: Updated README.md with GLM-4.5 support information
  - Added GLM-4.5 to supported models list
  - Updated environment variables documentation for ZhipuAI integration
  - Enhanced model comparison and configuration examples
- **Configuration Management**: Enhanced agent configuration system
  - Updated `agent_config.py` with GLM-4.5 support
  - Improved CLI integration for GLM models
  - Better model parameter handling in utils.py

### Technical Details
- **Commits**: 6 major commits including merge pull requests #90 and #94
- **Files Modified**: 12+ files across backend, frontend, configuration, and documentation
- **New Dependencies**: ZhipuAI GLM-4.5 model integration
- **Contributors**: @Stanislas0 @qidanrui @sonichi @Leezekun @voidcenter

## [0.0.5] - 2025-08-11

### Added
- **Claude Code Integration**: Complete integration with Claude Code CLI backend
  - New `claude_code.py` backend with streaming capabilities and tool support
  - Support for Claude Code SDK with stateful conversation management
  - JSON tool call functionality and proper tool result handling
  - Session management with append system prompt support
- **New Configuration Files**: Added Claude Code specific YAML configurations
  - `claude_code_single.yaml`: Single agent setup using Claude Code backend
  - `claude_code_flash2.5.yaml`: Multi-agent setup with Claude Code and Gemini Flash 2.5
  - `claude_code_flash2.5_gptoss.yaml`: Multi-agent setup with Claude Code, Gemini Flash 2.5, and GPT-OSS
- **Test Coverage**: Added test suite for Claude Code functionality
  - `test_claude_code_orchestrator.py`: orchestrator testing
  - Backend-specific test coverage for Claude Code integration

### Fixed
- **Backend Stability**: Multiple critical bug fixes across all backend systems
  - Fixed parameter handling in `chat_completions.py`, `claude.py`, `gemini.py`, `grok.py`
  - Resolved response processing issues in `response.py`
  - Improved error handling and client existence validation
- **Tool Call Processing**: Enhanced tool call parsing and execution
  - Deduplicated tool call parsing logic across backends
  - Fixed JSON tool call functionality and result formatting
  - Improved builtin tool result handling in streaming contexts
- **Message Handling**: Resolved system message processing issues
  - Fixed SystemMessage to StreamChunk conversion
  - Proper session info extraction from system messages
  - Cleaned up message formatting and display consistency
- **Frontend Display**: Fixed output formatting and presentation
  - Improved rich terminal display formatting
  - Better coordination UI integration and multi-turn conversation display
  - Enhanced status message display with proper newline handling

### Changed
- **Code Architecture**: Significant refactoring and cleanup across the codebase
  - Renamed and consolidated backend files for consistency
  - Simplified chat agent architecture and removed redundant code
  - Streamlined orchestrator logic with improved error handling
- **Configuration Management**: Updated and cleaned up configuration files
  - Updated agent configuration with Claude Code support
- **Backend Infrastructure**: Enhanced backend parameter handling
  - Improved stateful conversation management across all backends
  - Better integration with orchestrator for multi-agent coordination
  - Enhanced streaming capabilities with proper chunk processing
- **Documentation**: Updated project documentation
  - Added Claude Code setup instructions in README
  - Updated backend architecture documentation
  - Improved reasoning and streaming integration notes

### Technical Details
- **Commits**: 50+ commits since version 0.0.4
- **Files Modified**: 25+ files across backend, configuration, frontend, and test modules
- **Major Components Updated**: Backend systems, orchestrator, frontend display, configuration management
- **New Dependencies**: Added Claude Code SDK integration
- **Contributors**: @qidanrui @randombet @sonichi

## [0.0.4] - 2025-08-08

### Added
- **GPT-5 Series Support**: Full support for OpenAI's GPT-5 model family
  - GPT-5: Full-scale model with advanced capabilities
  - GPT-5-mini: Efficient variant for faster responses
  - GPT-5-nano: Lightweight model for resource-constrained deployments
- **New Model Parameters**: Introduced GPT-5 specific configuration options
  - `text.verbosity`: Control response detail level (low/medium/high)
  - `reasoning.effort`: Configure reasoning depth (minimal/medium/high)
  - Note: reasoning parameter is mutually exclusive with web search capability
- **Configuration Files**: Added dedicated YAML configurations
  - `gpt5.yaml`: Three-agent setup with GPT-5, GPT-5-mini, and GPT-5-nano
  - `gpt5_nano.yaml`: Three GPT-5-nano agents with different reasoning levels
- **Extended Model Support**: Added GPT-5 series to model mappings in utils.py
- **Reasoning for All Models**: Extended reasoning parameter support beyond GPT-5 models

### Fixed
- **Tool Output Formatting**: Added proper newline formatting for provider tool outputs
  - Web search status messages now display on new lines
  - Code interpreter status messages now display on new lines
  - Search query display formatting improved
- **YAML Configuration**: Fixed configuration syntax in GPT-5 related YAML files
- **Backend Response Handling**: Multiple bug fixes in response.py for proper parameter handling

### Changed
- **Documentation Updates**:
  - Updated README.md to highlight GPT-5 series support
  - Changed example commands to use GPT-5 models
  - Added new backend configuration examples with GPT-5 specific parameters
  - Updated models comparison table to show GPT-5 as latest OpenAI model
- **Parameter Handling**: Improved backend parameter validation
  - Temperature parameter now excluded for GPT-5 series models (like o-series)
  - Max tokens parameter now excluded for GPT-5 series models
  - Added conditional logic for GPT-5 specific parameters (text, reasoning)
- **Version Number**: Updated to 0.0.4 in massgen/__init__.py

### Technical Details
- **Commits**: 9 commits since version 0.0.3
- **Files Modified**: 6 files (response.py, utils.py, README.md, __init__.py, and 2 new config files)
- **Contributors**: @qidanrui @sonichi @voidcenter @JeffreyCh0 @praneeth999

## [0.0.3] - 2025-08-03

### Added
- Complete architecture with foundation release
- Multi-backend support: Claude (Messages API), Gemini (Chat API), Grok (Chat API), OpenAI (Responses API)
- Builtin tools: Code execution and web search with streaming results
- Async streaming with proper chat agent interfaces and tool result handling
- Multi-agent orchestration with voting and consensus mechanisms
- Real-time frontend displays with multi-region terminal UI
- CLI with file-based YAML configuration and interactive mode
- Proper StreamChunk architecture separating tool_calls from builtin_tool_results
- Multi-turn conversation support with dynamic context reconstruction
- Chat interface with orchestrator supporting async streaming
- Case study configurations and specialized YAML configs
- Claude backend support with production-ready multi-tool API and streaming
- OpenAI builtin tools support for code execution and web search streaming

### Fixed
- Grok backend testing and compatibility issues
- CLI multi-turn conversation display with coordination UI integration
- Claude streaming handler with proper tool argument capture
- CLI backend parameter passing with proper ConfigurableAgent integration

### Changed
- Restructured codebase with new architecture
- Improved message handling and streaming capabilities
- Enhanced frontend features and user experience

## [0.0.1] - Initial Release

### Added
- Basic multi-agent system framework
- Support for OpenAI, Gemini, and Grok backends
- Simple configuration system
- Basic streaming display
- Initial logging capabilities
