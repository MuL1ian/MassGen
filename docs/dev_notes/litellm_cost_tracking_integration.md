# LiteLLM Integration for Accurate Cost Tracking

## Status
**Design Complete** - Not yet implemented

## Problem Statement

MassGen currently underestimates or overestimates costs due to missing support for:

1. **Reasoning tokens** (OpenAI o1/o3 models) - Can cause **16x cost underestimation**
   - Example: o1-preview with 15,000 reasoning tokens = $0.90 untracked cost

2. **Cached tokens** (Anthropic prompt caching) - Can cause **8x cost overestimation**
   - Example: 100K cached tokens counted at full price instead of 10% discount

3. **New pricing tiers** - Manual maintenance of pricing data becomes outdated

## Current Implementation

### Token Tracking (`massgen/token_manager/token_manager.py`)

```python
@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0
```

**Limitations:**
- No reasoning_tokens field
- No cached_tokens field
- No breakdown of cost components

### Cost Calculation

```python
def calculate_cost(self, input_tokens: int, output_tokens: int, provider: str, model: str) -> float:
    pricing = self.get_model_pricing(provider, model)
    input_cost = (input_tokens / 1000) * pricing.input_cost_per_1k
    output_cost = (output_tokens / 1000) * pricing.output_cost_per_1k
    return input_cost + output_cost
```

**Limitations:**
- Treats all tokens uniformly
- No special handling for reasoning tokens
- No support for cached token discounts

### Pricing Data

```python
@dataclass
class ModelPricing:
    input_cost_per_1k: float
    output_cost_per_1k: float
    context_window: Optional[int] = None
    max_output_tokens: Optional[int] = None
```

**Limitations:**
- No reasoning_cost_per_1k field
- No cached_read_cost_per_1k / cached_write_cost_per_1k fields

## Proposed Solution: LiteLLM Integration

### Why LiteLLM?

LiteLLM provides:
- ✅ Comprehensive pricing database (500+ models, auto-updated)
- ✅ Automatic reasoning token handling
- ✅ Automatic cached token handling
- ✅ Supports all major providers (OpenAI, Anthropic, Google, xAI)
- ✅ Already used for pricing database (on-demand loading implemented)

### Architecture

```
API Response (with usage)
    ↓
Backend extracts usage object
    ↓
TokenCostCalculator.calculate_cost_with_usage_object()
    ↓
    ├─→ Try: litellm.completion_cost(response_with_usage)
    │        └─→ Automatically handles reasoning/cached tokens
    │
    └─→ Fallback: Existing calculate_cost(input, output)
             └─→ Basic calculation for unknown models
```

## Implementation Plan

### Phase 1: Add New Method to TokenCostCalculator

**File**: `massgen/token_manager/token_manager.py`

Add new method that uses litellm:

```python
def calculate_cost_with_usage_object(
    self,
    model: str,
    usage: Union[Dict[str, Any], Any],
    provider: Optional[str] = None
) -> float:
    """
    Calculate cost from API usage object using litellm.

    Automatically handles:
    - Reasoning tokens (o1/o3 models)
    - Cached tokens (prompt caching)
    - Cache creation vs cache read pricing
    - Provider-specific token structures

    Args:
        model: Model identifier (e.g., "gpt-4o", "claude-sonnet-4-5-20250929")
        usage: Usage object/dict from API response
        provider: Optional provider name for fallback

    Returns:
        Cost in USD
    """
    try:
        from litellm import completion_cost
        from types import SimpleNamespace

        # Normalize usage to object form
        if isinstance(usage, dict):
            usage_obj = SimpleNamespace(**usage)
        else:
            usage_obj = usage

        # Create minimal response structure for litellm
        mock_response = SimpleNamespace(model=model, usage=usage_obj)

        # Calculate with litellm (handles all token types)
        cost = completion_cost(
            completion_response=mock_response,
            model=model,
            custom_llm_provider=provider
        )

        logger.debug(f"litellm cost: {model} = ${cost:.6f}")
        return cost

    except ImportError:
        logger.debug("litellm not available, using fallback")
    except Exception as e:
        logger.debug(f"litellm failed ({e}), using fallback")

    # Fallback to existing logic
    return self._extract_and_calculate_basic_cost(usage, provider, model)


def _extract_and_calculate_basic_cost(
    self,
    usage: Union[Dict, Any],
    provider: str,
    model: str
) -> float:
    """Extract basic token counts and calculate cost (fallback)."""
    # OpenAI format: prompt_tokens, completion_tokens
    # Anthropic format: input_tokens, output_tokens

    if isinstance(usage, dict):
        input_tokens = usage.get('prompt_tokens') or usage.get('input_tokens', 0)
        output_tokens = usage.get('completion_tokens') or usage.get('output_tokens', 0)
    else:
        input_tokens = getattr(usage, 'prompt_tokens', 0) or getattr(usage, 'input_tokens', 0)
        output_tokens = getattr(usage, 'completion_tokens', 0) or getattr(usage, 'output_tokens', 0)

    return self.calculate_cost(input_tokens, output_tokens, provider, model)
```

### Phase 2: Update Backends to Use New Method

**Target backends:**
1. `massgen/backend/chat_completions.py` - OpenAI Chat Completions API
2. `massgen/backend/response.py` - OpenAI Response API
3. `massgen/backend/claude_code.py` - Claude Code SDK
4. `massgen/backend/gemini.py` - Gemini API

**Pattern for each backend:**

```python
# OLD (line ~662 in chat_completions.py):
if hasattr(chunk, "usage") and chunk.usage:
    input_tokens = chunk.usage.prompt_tokens
    output_tokens = chunk.usage.completion_tokens
    cost = self.calculate_cost(input_tokens, output_tokens, model)
    self.token_usage.estimated_cost += cost

# NEW:
if hasattr(chunk, "usage") and chunk.usage:
    # Use litellm for accurate cost (handles reasoning/cached tokens)
    cost = self.token_calculator.calculate_cost_with_usage_object(
        model=all_params.get("model"),
        usage=chunk.usage,
        provider=self.get_provider_name()
    )

    # Still track basic counts for display/debugging
    input_tokens = getattr(chunk.usage, 'prompt_tokens', 0) or getattr(chunk.usage, 'input_tokens', 0)
    output_tokens = getattr(chunk.usage, 'completion_tokens', 0) or getattr(chunk.usage, 'output_tokens', 0)

    self.token_usage.input_tokens += input_tokens
    self.token_usage.output_tokens += output_tokens
    self.token_usage.estimated_cost += cost
```

**Key changes:**
- Pass entire `chunk.usage` object to new method
- Let litellm handle complexity of token types
- Keep basic token tracking for display purposes

### Phase 3: Optional - Enhanced TokenUsage Tracking

**File**: `massgen/token_manager/token_manager.py`

Extend TokenUsage dataclass to track special token types:

```python
@dataclass
class TokenUsage:
    """Token usage and cost tracking."""

    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0

    # Optional: Track special token types for visibility
    reasoning_tokens: int = 0  # OpenAI o1/o3 reasoning
    cached_tokens: int = 0     # Prompt cache hits

    def add(self, other: "TokenUsage"):
        """Add another TokenUsage to this one."""
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.estimated_cost += other.estimated_cost
        self.reasoning_tokens += other.reasoning_tokens
        self.cached_tokens += other.cached_tokens
```

**To populate these fields**, extract from usage object before calling litellm:

```python
# Extract special token types for display
if hasattr(chunk.usage, 'completion_tokens_details'):
    reasoning = getattr(chunk.usage.completion_tokens_details, 'reasoning_tokens', 0)
    self.token_usage.reasoning_tokens += reasoning

if hasattr(chunk.usage, 'prompt_tokens_details'):
    cached = getattr(chunk.usage.prompt_tokens_details, 'cached_tokens', 0)
    self.token_usage.cached_tokens += cached
```

## Testing Strategy

### Unit Tests

**File**: `massgen/tests/test_token_manager_litellm.py` (new)

```python
import pytest
from types import SimpleNamespace
from massgen.token_manager.token_manager import TokenCostCalculator

def test_litellm_with_reasoning_tokens():
    """Test cost calculation with reasoning tokens (o3-mini)."""
    calc = TokenCostCalculator()

    usage = {
        'prompt_tokens': 100,
        'completion_tokens': 50,
        'completion_tokens_details': {'reasoning_tokens': 30}
    }

    cost = calc.calculate_cost_with_usage_object('o3-mini', usage, 'openai')

    # Should be more expensive than basic calculation
    basic_cost = calc.calculate_cost(100, 50, 'openai', 'o3-mini')
    assert cost > basic_cost

def test_litellm_with_cached_tokens():
    """Test cost calculation with cached tokens (Claude)."""
    calc = TokenCostCalculator()

    usage = {
        'input_tokens': 1000,
        'output_tokens': 200,
        'cache_read_input_tokens': 800,
        'cache_creation_input_tokens': 0
    }

    cost = calc.calculate_cost_with_usage_object(
        'claude-sonnet-4-5-20250929',
        usage,
        'anthropic'
    )

    # Should be cheaper than basic calculation (cache discount)
    basic_cost = calc.calculate_cost(1000, 200, 'anthropic', 'claude-sonnet-4-5')
    assert cost < basic_cost

def test_litellm_fallback_on_unknown_model():
    """Test fallback when model not in litellm database."""
    calc = TokenCostCalculator()

    usage = {'prompt_tokens': 100, 'completion_tokens': 50}

    # Custom model not in litellm
    cost = calc.calculate_cost_with_usage_object('custom-model', usage, 'custom')

    # Should fall back gracefully (may return 0 or estimate)
    assert cost >= 0
```

### Integration Tests

Test with real backends:

```python
@pytest.mark.integration
def test_openai_backend_with_o3():
    """Test OpenAI backend with o3 model tracks reasoning tokens."""
    backend = ChatCompletionsBackend(
        api_key=os.environ['OPENAI_API_KEY'],
        base_url="https://api.openai.com/v1"
    )

    # Make API call
    response = await backend.chat([{"role": "user", "content": "Complex reasoning task"}])

    # Verify cost was calculated with reasoning tokens
    assert backend.token_usage.estimated_cost > 0

@pytest.mark.integration
def test_claude_backend_with_caching():
    """Test Claude backend with caching tracks cache hits."""
    backend = ClaudeBackend(api_key=os.environ['ANTHROPIC_API_KEY'])

    # Make cached API call
    response = await backend.chat(messages_with_large_system_prompt)

    # Verify cost reflects cache discount
    assert backend.token_usage.estimated_cost > 0
```

## Backward Compatibility

### No Breaking Changes
- Existing `calculate_cost(input, output, provider, model)` remains unchanged
- Backends can choose which method to use
- Graceful degradation if litellm not installed
- Falls back to manual calculation if litellm fails

### Gradual Migration
1. Add new method to TokenCostCalculator
2. Update backends one at a time
3. Test each backend independently
4. Keep old logic as fallback

## Dependencies

### Required
- `litellm` package (already used for pricing database fetching)

### Optional
None - litellm is the only new runtime dependency, and it's already being used

## Error Handling

### litellm Not Installed
```python
try:
    from litellm import completion_cost
except ImportError:
    logger.info("litellm not installed, using manual cost calculation")
    return self._fallback_calculate_cost(...)
```

### Model Not in litellm Database
```python
try:
    cost = completion_cost(...)
except Exception as e:
    logger.debug(f"litellm failed for {model}: {e}, using fallback")
    return self._fallback_calculate_cost(...)
```

### Malformed Usage Data
```python
if not usage:
    logger.warning("No usage data provided")
    return 0.0
```

## Monitoring & Validation

### Cost Comparison Logging

During rollout, compare litellm vs manual calculations:

```python
litellm_cost = self.calculate_cost_with_usage_object(model, usage, provider)
manual_cost = self.calculate_cost(input_tokens, output_tokens, provider, model)

if abs(litellm_cost - manual_cost) > 0.01:  # $0.01 threshold
    logger.info(
        f"Cost difference: litellm=${litellm_cost:.6f} vs manual=${manual_cost:.6f} "
        f"for {model} (diff: ${abs(litellm_cost - manual_cost):.6f})"
    )
```

### Validation Against Provider Bills

After implementation:
- Compare MassGen cost estimates to actual OpenAI/Anthropic bills
- Verify reasoning token costs for o1/o3 models
- Verify cache discount pricing for Claude

## Migration Path

### Phase 1: Core Integration (Week 1)
- [ ] Add `calculate_cost_with_usage_object()` to TokenCostCalculator
- [ ] Add `_extract_and_calculate_basic_cost()` fallback helper
- [ ] Unit tests for new methods
- [ ] Documentation updates

### Phase 2: Backend Updates (Week 2)
- [ ] Update `chat_completions.py` (OpenAI Chat Completions)
- [ ] Update `response.py` (OpenAI Response API)
- [ ] Test with o1/o3 models
- [ ] Verify reasoning token costs

### Phase 3: Claude/Gemini Support (Week 3)
- [ ] Update `claude_code.py`
- [ ] Update `gemini.py`
- [ ] Test with Claude prompt caching
- [ ] Verify cache discount pricing

### Phase 4: Validation & Monitoring (Week 4)
- [ ] Add cost comparison logging
- [ ] Compare against real provider bills
- [ ] Document cost tracking improvements
- [ ] Update user guide

## Files to Modify

### Core Implementation
1. **`massgen/token_manager/token_manager.py`**
   - Add `calculate_cost_with_usage_object()` method
   - Add `_extract_and_calculate_basic_cost()` helper
   - Keep existing `calculate_cost()` for backward compat

### Backend Updates
2. **`massgen/backend/chat_completions.py`**
   - Update usage processing (line ~662)
   - Call new method with full usage object

3. **`massgen/backend/response.py`**
   - Update usage processing (line ~791)
   - Call new method with full usage object

4. **`massgen/backend/claude_code.py`**
   - Update `update_token_usage_from_result_message()` (line 355)
   - Call new method with ResultMessage usage

5. **`massgen/backend/gemini.py`**
   - Update usage processing
   - Call new method with Gemini usage object

### Testing
6. **`massgen/tests/test_token_manager_litellm.py`** (new)
   - Unit tests for litellm integration
   - Mock responses with reasoning/cached tokens
   - Fallback behavior tests

### Documentation
7. **`docs/source/user_guide/cost_tracking.rst`** (new or update existing)
   - Explain cost tracking accuracy improvements
   - Document reasoning token tracking
   - Document cached token tracking

## Pricing Examples

### OpenAI o3-mini with Reasoning

**API Response:**
```json
{
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 50,
    "completion_tokens_details": {
      "reasoning_tokens": 30
    }
  }
}
```

**Cost Calculation:**
- Input: 100 tokens @ $1.10/M = $0.00011
- Output: 20 tokens @ $4.40/M = $0.00088 (50 - 30 reasoning)
- Reasoning: 30 tokens @ $4.40/M = $0.000132
- **Total: $0.001122**

Without reasoning tracking, we'd calculate:
- Input: 100 @ $1.10/M = $0.00011
- Output: 50 @ $4.40/M = $0.00022
- **Total: $0.00033** (underestimated by 70%)

### Claude Sonnet 4.5 with Caching

**API Response:**
```json
{
  "usage": {
    "input_tokens": 1000,
    "output_tokens": 200,
    "cache_read_input_tokens": 800,
    "cache_creation_input_tokens": 0
  }
}
```

**Cost Calculation:**
- New input: 200 tokens @ $3/M = $0.0006
- Cached input: 800 tokens @ $0.30/M = $0.00024
- Output: 200 tokens @ $15/M = $0.003
- **Total: $0.00384**

Without cache tracking, we'd calculate:
- Input: 1000 @ $3/M = $0.003
- Output: 200 @ $15/M = $0.003
- **Total: $0.006** (overestimated by 56%)

## Risks & Mitigations

### Risk: litellm dependency failure
**Mitigation**: Graceful fallback to existing `calculate_cost()`

### Risk: litellm pricing out of date
**Mitigation**: Fallback to `PROVIDER_PRICING` for critical models

### Risk: Performance overhead
**Mitigation**: litellm is lightweight, negligible overhead

### Risk: Breaking existing code
**Mitigation**: New method is additive, existing method unchanged

## Success Metrics

- [ ] Cost estimates within 5% of actual provider bills
- [ ] Reasoning token costs tracked for o1/o3 models
- [ ] Cache discount pricing tracked for Claude
- [ ] No regressions in existing functionality
- [ ] All unit tests passing

## Related Issues

- Accurate cost tracking enables better budget management
- Users can make informed decisions about model selection
- Supports future cost alert features
- Enables cost-based optimization recommendations

## References

- **LiteLLM docs**: https://docs.litellm.ai/docs/completion/token_usage
- **LiteLLM pricing DB**: https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json
- **OpenAI usage format**: `massgen/backend/docs/OPENAI_response_streaming.md`
- **Anthropic caching**: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching

## Next Steps

1. Review this design doc
2. Approve implementation plan
3. Create implementation PR
4. Test with real API calls
5. Validate against provider bills
