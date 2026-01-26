## 1. Investigation

- [ ] 1.1 Read `content_normalizer.py` to understand `normalize()` and `should_display` logic
- [ ] 1.2 Read `content_handlers.py` to understand `PresentationContentHandler.process()` flow
- [ ] 1.3 Read `content_sections.py` to understand `FinalPresentationCard.append_chunk()` implementation
- [ ] 1.4 Identify where final answer content is being filtered or lost

## 2. Implementation

- [ ] 2.1 Fix the identified content filtering issue
- [ ] 2.2 Ensure all final answer content reaches the `FinalPresentationCard`
- [ ] 2.3 If needed, separate reasoning display from answer display
- [ ] 2.4 Test with a multi-agent run that produces a final presentation

## 3. Verification

- [ ] 3.1 Run MassGen with a config that produces final presentation
- [ ] 3.2 Verify complete answer is visible in TUI
- [ ] 3.3 Ensure reasoning text doesn't obscure actual answer
