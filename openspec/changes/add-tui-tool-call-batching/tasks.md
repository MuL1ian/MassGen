## 1. Design

- [ ] 1.1 Read current `tool_card.py` to understand ToolCallCard structure
- [ ] 1.2 Read `content_handlers.py` to understand how tool calls are processed
- [ ] 1.3 Design `ToolBatchCard` widget structure

## 2. Implementation

- [ ] 2.1 Create `ToolBatchCard` widget in `tool_card.py`
- [ ] 2.2 Implement batching logic to group consecutive same-server tool calls
- [ ] 2.3 Add tree view rendering with expand/collapse functionality
- [ ] 2.4 Implement "+N more" indicator for collapsed items
- [ ] 2.5 Add CSS styling for batch cards in dark.tcss
- [ ] 2.6 Add CSS styling for batch cards in light.tcss

## 3. Integration

- [ ] 3.1 Update content handlers to detect batch sequences
- [ ] 3.2 Update timeline mounting logic to use ToolBatchCard for grouped calls
- [ ] 3.3 Ensure individual tool results map back to correct batch item

## 4. Testing

- [ ] 4.1 Test with config that uses multiple consecutive filesystem tool calls
- [ ] 4.2 Verify batch grouping works correctly
- [ ] 4.3 Verify expand/collapse functionality
- [ ] 4.4 Verify tool results display correctly within batch
