# Registry Updates

## When Adding New Models

1. **Always update** `massgen/backend/capabilities.py`:
   - Add to `models` list (newest first)
   - Add to `model_release_dates`
   - Update `supported_capabilities` if new features

2. **Check LiteLLM first** before adding to `token_manager.py`:
   - If model is in LiteLLM database, no pricing update needed
   - Only add to `PROVIDER_PRICING` if missing from LiteLLM
   - Use correct provider casing: `"OpenAI"`, `"Anthropic"`, `"Google"`, `"xAI"`

3. **Regenerate docs**: `uv run python docs/scripts/generate_backend_tables.py`

## When Adding New YAML Parameters

Update **both** files to exclude from API passthrough:
- `massgen/backend/base.py` -> `get_base_excluded_config_params()`
- `massgen/api_params_handler/_api_params_handler_base.py` -> `get_base_excluded_config_params()`

See also: `massgen/tests/test_api_params_exclusion.py` for automated verification of exclusion list consistency.
