## ADDED Requirements

### Requirement: Complete Final Presentation Display
The TUI final presentation card SHALL display the complete final answer/output, not just reasoning fragments.

#### Scenario: Final answer fully visible
- **WHEN** a multi-agent session completes and produces a final presentation
- **THEN** the complete final answer (poem, solution, etc.) is displayed in the FinalPresentationCard
- **AND** the answer content is not truncated or filtered

#### Scenario: Reasoning does not obscure answer
- **WHEN** the final presentation includes both reasoning text and the actual answer
- **THEN** the actual answer is prominently displayed
- **AND** reasoning text does not push the answer out of view

### Requirement: Content Filtering Preserves Answers
The `ContentNormalizer` SHALL NOT filter out substantive answer content from final presentations.

#### Scenario: Answer content passes through normalizer
- **WHEN** final answer content is processed by ContentNormalizer
- **THEN** the `should_display` method returns true for answer content
- **AND** the content reaches the FinalPresentationCard unchanged

---

## PROPOSED Requirements (Content Normalization Overhaul)

### Background: Current Problems

The `ContentNormalizer` has grown organically to handle many edge cases:
1. **13+ filter patterns** for workspace state content (`WORKSPACE_STATE_PATTERNS`)
2. **12+ patterns** for workspace tool JSON (`WORKSPACE_TOOL_PATTERNS`)
3. **9+ patterns** for coordination content (`COORDINATION_PATTERNS`)
4. **Heuristic-based filtering** using JSON "scores" and escaped newline counts
5. **Fragile ordering** - filter checks happen in arbitrary order

**Result**: Legitimate content gets filtered while noise still leaks through.

### Requirement: Content Type Hierarchy
The normalizer SHALL use a clear content type hierarchy to determine display behavior.

#### Scenario: Presentation content always displays
- **GIVEN** content with `raw_type="presentation"` OR content_type="presentation"
- **WHEN** normalized
- **THEN** `should_display` is always True
- **AND** no workspace/JSON filters are applied

#### Scenario: Tool content uses dedicated handlers
- **GIVEN** content with content_type starting with "tool_"
- **WHEN** normalized
- **THEN** content is passed to tool card handlers unchanged
- **AND** only minimal stripping of prefixes is applied
- **AND** workspace state filters are NOT applied

#### Scenario: Agent text content gets standard filtering
- **GIVEN** content with content_type="text" from agent responses
- **WHEN** normalized
- **THEN** workspace state patterns are checked
- **AND** JSON noise patterns are checked
- **AND** content is displayed if no filters match

### Requirement: Replace Heuristic Filters with Explicit Rules
The normalizer SHALL replace score-based heuristics with explicit pattern rules.

#### Context: Current heuristics to remove
```python
# Current problematic heuristics:
json_score = sum(content.count(ind) for ind in json_indicators)
if content_len > 0 and json_score >= 2:
    if content_len < 200 or json_score >= 3:
        return True  # Filter based on "feels like JSON"

escaped_newlines = content.count("\\n")
if escaped_newlines >= 3:
    if any(term.lower() in content.lower() for term in workspace_terms):
        return True  # Filter based on "has escaped newlines"
```

#### Scenario: No false positives from JSON-like content
- **GIVEN** valid agent content containing JSON code examples or structured data
- **WHEN** normalized
- **THEN** content is NOT filtered just because it contains `": "` or `",`
- **AND** content is only filtered if it matches explicit workspace action patterns

#### Scenario: Explicit pattern matching for workspace content
- **GIVEN** workspace coordination JSON like `{"action_type": "new_answer", ...}`
- **WHEN** normalized
- **THEN** content is filtered because it matches explicit `action_type` pattern
- **NOT** because it has a "high JSON score"

### Requirement: Separate Reasoning from Answer in Presentations
The display system SHALL visually separate reasoning/thinking from the actual answer in final presentations.

#### Context: Reasoning patterns
Providers often emit reasoning with patterns like:
- `**Bold Headers**` followed by reasoning text
- `<thinking>` tags (Claude)
- Lines starting with reasoning markers

#### Scenario: Reasoning displayed but de-emphasized
- **WHEN** final presentation contains both reasoning and answer
- **THEN** reasoning is displayed in a collapsible or smaller section
- **AND** the answer is displayed prominently below/after reasoning
- **AND** user can expand to see full reasoning if desired

### Requirement: Consolidate Filter Patterns
The normalizer SHALL consolidate redundant and overlapping patterns.

#### Context: Current pattern redundancy
```python
# Redundant patterns (examples):
WORKSPACE_TOOL_PATTERNS has both:
  - r'"action_type"\s*:\s*"'        # with leading quote
  - r'action_type"\s*:\s*"'         # without leading quote (partial)

WORKSPACE_STATE_PATTERNS has both:
  - r'"action_type"\s*:\s*"'        # duplicate of above
  - r'"action_type"\s*:\s*""'       # malformed variant
```

#### Scenario: Single source of truth for patterns
- **GIVEN** a need to filter workspace action content
- **WHEN** patterns are checked
- **THEN** a single canonical pattern list is used
- **AND** no duplicate/overlapping patterns exist
- **AND** patterns are organized by category with clear comments

### Requirement: Debug/Trace Mode for Filtering
The normalizer SHALL support a debug mode to trace why content is filtered.

#### Scenario: Debugging filtered content
- **GIVEN** debug mode is enabled (e.g., `TUI_FILTER_DEBUG=1`)
- **WHEN** content is filtered (should_display=False)
- **THEN** a log entry shows which filter matched
- **AND** the original content is logged for inspection

### Requirement: Content Type Passthrough for Structured Data
The normalizer SHALL pass through certain content types without filtering.

#### Scenario: Injection content passthrough
- **GIVEN** content with content_type="injection"
- **WHEN** normalized
- **THEN** only prefix stripping is applied
- **AND** no content filtering is applied
- **AND** dedicated injection card handles display

#### Scenario: Reminder content passthrough
- **GIVEN** content with content_type="reminder"
- **WHEN** normalized
- **THEN** only prefix stripping is applied
- **AND** no content filtering is applied

---

## Implementation Notes

### Proposed Architecture Changes

1. **Early exit for protected types**: Check content_type first, exit before filters
   ```python
   PROTECTED_TYPES = {"presentation", "injection", "reminder"}
   if content_type in PROTECTED_TYPES:
       return NormalizedContent(should_display=True, ...)
   ```

2. **Explicit filter chains**: Named filter functions with clear purpose
   ```python
   def filter_workspace_actions(content) -> bool
   def filter_json_noise(content) -> bool
   def filter_empty_content(content) -> bool
   ```

3. **Pattern consolidation**: Single pattern list per category
   ```python
   WORKSPACE_ACTION_PATTERNS = [...]  # JSON actions to filter
   JSON_NOISE_PATTERNS = [...]        # Empty/malformed JSON
   INTERNAL_STATE_PATTERNS = [...]    # CWD, file status, etc.
   ```

4. **Remove heuristics**: Delete score-based and count-based filters

### Files to Modify
- `massgen/frontend/displays/content_normalizer.py` - Main refactor
- `massgen/frontend/displays/content_handlers.py` - May need updates for presentation handling
- `massgen/frontend/displays/textual_widgets/content_sections.py` - Reasoning/answer separation in FinalPresentationCard
