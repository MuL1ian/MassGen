# MassGen v0.1.45 Roadmap

## Overview

Version 0.1.45 focuses on improving subagent display and visibility in the TUI.

- **Subagent TUI Streaming** (Required): Stream and display subagents almost identically to main process
- **Single Source of Truth** (Required): Refactor TUI to use unified display components for all agents

## Key Technical Priorities

1. **Subagent TUI Streaming**: Real-time subagent visualization with clickable timeline views
   **Use Case**: Better visibility into subagent execution, improved debugging workflows

2. **Unified Display Components**: Shared TUI components for consistent rendering across agent types
   **Use Case**: Code reusability, consistent user experience, easier maintenance

## Key Milestones

### Milestone 1: Subagent TUI Streaming (REQUIRED)

**Goal**: Stream and display subagents almost identically to main process in TUI

**Owner**: @ncrispino (nickcrispino on Discord)

**Issue**: [#821](https://github.com/Leezekun/MassGen/issues/821)

#### 1.1 Research & Design
- [ ] Study current TUI architecture and event streaming
- [ ] Design subagent preview card component
- [ ] Design subagent timeline view interaction
- [ ] Plan event routing from subagents to TUI

#### 1.2 Subagent Preview Cards
- [ ] Create collapsible subagent preview card component
- [ ] Show subagent metadata (ID, status, model)
- [ ] Display real-time streaming preview
- [ ] Add click handler to expand to full timeline

#### 1.3 Subagent Timeline View
- [ ] Design modal or expanded view for full subagent timeline
- [ ] Reuse existing timeline components for subagent display
- [ ] Ensure identical tool card rendering
- [ ] Support navigation between multiple subagents

#### 1.4 Event Streaming Integration
- [ ] Route subagent events to TUI display
- [ ] Handle subagent lifecycle events (start, progress, complete)
- [ ] Support concurrent subagent streaming
- [ ] Add error handling for subagent failures

#### 1.5 Testing & Polish
- [ ] Test with multiple concurrent subagents
- [ ] Verify tool displays match main agent formatting
- [ ] Test click interactions and navigation
- [ ] Add loading states and transitions

**Success Criteria**:
- Subagents stream to TUI in real-time with preview cards
- Clicking subagent card shows full timeline view
- Tool displays identical between main agents and subagents
- Supports multiple concurrent subagents

---

### Milestone 2: Single Source of Truth for TUI Display (REQUIRED)

**Goal**: Refactor TUI display creation to use shared components for main agents and subagents

**Owner**: @ncrispino (nickcrispino on Discord)

**Related Issue**: [#821](https://github.com/Leezekun/MassGen/issues/821)

#### 2.1 Component Architecture Refactor
- [ ] Identify shared display components (tool cards, status, timeline)
- [ ] Extract reusable components from main TUI
- [ ] Create unified event parser for all agent types
- [ ] Design component API for agent-agnostic rendering

#### 2.2 Unified Event Parsing
- [ ] Create shared event parser for streaming chunks
- [ ] Support both main agent and subagent event formats
- [ ] Handle tool calls, thinking, text content uniformly
- [ ] Add extensibility for future agent types

#### 2.3 Component Integration
- [ ] Update main TUI to use new shared components
- [ ] Update subagent display to use same components
- [ ] Ensure consistent styling and behavior
- [ ] Add configuration for component customization

#### 2.4 Testing & Documentation
- [ ] Test component reuse across different agent types
- [ ] Verify styling consistency
- [ ] Document component API and usage
- [ ] Add examples for extending display components

**Success Criteria**:
- Shared components used by both main and subagent displays
- Identical event parsing for all agent types
- No duplicated display code
- Easy to extend for future agent types

---

## Timeline

**Target Release**: January 30, 2026

### Week 1 (Jan 28-30)
- Research & Design (Milestone 1.1)
- Component Architecture Refactor (Milestone 2.1)
- Subagent Preview Cards (Milestone 1.2)

### Week 2 (Jan 31-Feb 2)
- Subagent Timeline View (Milestone 1.3)
- Unified Event Parsing (Milestone 2.2)
- Event Streaming Integration (Milestone 1.4)

### Week 3 (Feb 3-5)
- Component Integration (Milestone 2.3)
- Testing & Polish (Milestone 1.5, 2.4)
- Documentation updates

---

## Success Metrics

- **Subagent Visibility**: All subagent activity visible in TUI with real-time streaming
- **User Experience**: Consistent display quality between main agents and subagents
- **Code Quality**: Single source of truth for display components, no duplication
- **Extensibility**: Easy to add support for new agent types in future

---

## Resources

- **Issue**: [#821 - Improve subagent display in TUI](https://github.com/Leezekun/MassGen/issues/821)
- **Owner**: @ncrispino (nickcrispino on Discord)
- **Related PRs**: TBD
- **Documentation**: `docs/dev_notes/tui_subagent_display.md` (to be created)
