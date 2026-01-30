# MassGen v0.1.46 Roadmap

## Overview

Version 0.1.46 focuses on fixing TUI scrolling and timeline management issues.

- **TUI Scrolling Fix** (Required): Fix blank space issues when timeline truncates older items
- **Timeline Truncation** (Required): Ensure proper rendering of final presentation box

## Key Technical Priorities

1. **Timeline Truncation Fix**: Eliminate blank space when TUI removes older items after reaching limit
   **Use Case**: Better TUI experience with proper scrolling and space management for long-running sessions

2. **Final Presentation Box Rendering**: Ensure final answer box displays correctly without being pushed down
   **Use Case**: Consistent final answer display, improved readability of agent results

## Key Milestones

### Milestone 1: Fix Timeline Truncation Blank Space (REQUIRED)

**Goal**: Fix blank space issues when TUI truncates older items after reaching item limit

**Owner**: @ncrispino (nickcrispino on Discord)

**Issue**: [#824](https://github.com/Leezekun/MassGen/issues/824)

#### 1.1 Research & Diagnosis
- [ ] Reproduce blank space issue with long-running sessions
- [ ] Identify root cause of blank space after item truncation
- [ ] Analyze timeline container height management
- [ ] Review item removal and reflow logic

#### 1.2 Timeline Item Removal
- [ ] Fix item removal logic to properly reclaim space
- [ ] Ensure container height updates when items are removed
- [ ] Test with various timeline item types (tools, thinking, text)
- [ ] Verify smooth transitions during removal

#### 1.3 Container Height Management
- [ ] Review and fix container height calculations
- [ ] Ensure proper reflow when content is truncated
- [ ] Test with different terminal sizes and layouts
- [ ] Add bounds checking for edge cases

#### 1.4 Testing & Validation
- [ ] Test with long-running multi-agent sessions
- [ ] Verify no blank space appears after truncation
- [ ] Test with various item counts and types
- [ ] Check memory usage and performance

**Success Criteria**:
- No blank space left when timeline items are truncated
- Smooth scrolling experience in long-running sessions
- Proper container height management
- No visual artifacts or layout issues

---

### Milestone 2: Fix Final Presentation Box Display (REQUIRED)

**Goal**: Ensure final presentation box displays correctly without being pushed down by blank space

**Owner**: @ncrispino (nickcrispino on Discord)

**Related Issue**: [#824](https://github.com/Leezekun/MassGen/issues/824)

#### 2.1 Final Presentation Positioning
- [ ] Identify why final presentation box shows as empty or is pushed down
- [ ] Review final presentation box rendering logic
- [ ] Check interaction with timeline truncation
- [ ] Test final answer display in various scenarios

#### 2.2 Layout Integration
- [ ] Ensure final presentation box has proper priority in layout
- [ ] Fix positioning relative to timeline items
- [ ] Verify scrolling behavior with final answer visible
- [ ] Test with different answer lengths and formats

#### 2.3 Edge Case Handling
- [ ] Test with very long agent outputs
- [ ] Verify behavior when truncation happens during final presentation
- [ ] Check final answer visibility with multiple agents
- [ ] Test with various terminal sizes

#### 2.4 Testing & Polish
- [ ] Test final answer display across all coordination phases
- [ ] Verify proper styling and readability
- [ ] Check interaction with voting results
- [ ] Add visual regression tests

**Success Criteria**:
- Final presentation box displays correctly without empty space
- Final answer not pushed down by blank space from truncated items
- Proper positioning and visibility of final results
- Consistent behavior across different session types

---

## Timeline

**Target Release**: February 2, 2026

### Week 1 (Feb 1-2)
- Research & Diagnosis (Milestone 1.1)
- Timeline Item Removal (Milestone 1.2)
- Final Presentation Positioning (Milestone 2.1)

### Week 2 (Feb 3-4)
- Container Height Management (Milestone 1.3)
- Layout Integration (Milestone 2.2)
- Edge Case Handling (Milestone 2.3)

### Week 3 (Feb 5-6)
- Testing & Validation (Milestone 1.4, 2.4)
- Documentation updates
- Bug fixes and polish

---

## Success Metrics

- **Visual Quality**: No blank space or layout issues in TUI timeline
- **User Experience**: Smooth scrolling and proper final answer display
- **Reliability**: Consistent behavior across different session lengths and types
- **Performance**: No degradation in rendering performance

---

## Resources

- **Issue**: [#824 - Fix TUI scrolling problem](https://github.com/Leezekun/MassGen/issues/824)
- **Owner**: @ncrispino (nickcrispino on Discord)
- **Related PRs**: TBD
- **Documentation**: `docs/dev_notes/tui_scrolling_fix.md` (to be created)
