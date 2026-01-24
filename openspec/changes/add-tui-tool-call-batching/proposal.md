# Change: Add TUI Tool Call Batching

## Why
Sequential tool calls from the same MCP server clutter the timeline and hide the actual workflow structure. For example, 5x `filesystem/write_file` calls appear as 5 separate cards with no visual grouping, making it hard to understand the batch operation.

## What Changes
- Batch consecutive tool calls from the same MCP server
- Display hierarchically with expandable tree view
- Show summary (e.g., `filesystem (5 calls)`) with individual calls expandable

**Design: Tree View with Auto-Collapse (Option C from plan)**

```
+---------------------------------------------------------------------+
|  filesystem                                           [0.8s] check  |
|    +-- create_directory  "deliverable"                       check  |
|    +-- create_directory  "scratch"                           check  |
|    +-- write_file        "deliverable/poem.txt" (+2 more)    check  |
+---------------------------------------------------------------------+
```

- Shows 3 items by default, collapses rest with "+N more" indicator
- Click "+N more" to expand full list
- Groups consecutive calls from same MCP server
- Always shows tree structure (no fully-collapsed state)

## Impact
- Affected files:
  - `massgen/frontend/displays/textual_widgets/tool_card.py` (new `ToolBatchCard`)
  - `massgen/frontend/displays/textual_widgets/content_sections.py` (batching logic)
  - `massgen/frontend/displays/content_handlers.py` (detect batch sequences)
  - `massgen/frontend/displays/textual_themes/dark.tcss` (batch styling)
  - `massgen/frontend/displays/textual_themes/light.tcss` (batch styling)
