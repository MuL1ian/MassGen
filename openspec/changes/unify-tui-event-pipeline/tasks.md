## 1. Implementation
- [x] 1.1 Inventory current main TUI parsing paths and event emission gaps; list all content types that bypass events
- [x] 1.2 Create shared event-to-timeline adapter (ContentProcessor + TimelineSection) usable by main and subagent views
- [x] 1.3 Route main TUI live stream through event emitter (or event listener) and remove/disable duplicate raw parsing
- [x] 1.4 Ensure subagent view consumes the same adapter and timeline rendering as main TUI
- [x] 1.5 Update subagent inner-agent tabs to show agent_id + model name and filter events consistently
- [x] 1.6 Add/adjust tests or fixtures to validate identical outputs for a shared event sequence
- [x] 1.7 Document the unified pipeline and fallback behavior for missing events
