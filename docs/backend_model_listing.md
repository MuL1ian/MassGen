# Backend Model Listing Discovery (MAS-163)

## Context

MassGen’s runtime model handling is **string-based and provider-agnostic**.
Model selection relies on:
- model name conventions
- provider prefixes (e.g., `groq/`, `together/`, `cerebras/`)
- LiteLLM backend routing

There are **no strict provider-specific model registries** used at runtime.

As a result, automatic model listing primarily improves:
- CLI UX (interactive selection, suggestions)
- Documentation accuracy
- Example configurations

It does **not** affect core execution.

---

## Current Backend Model Listing Status

| Provider     | Automatic Listing | Source | Notes |
|-------------|------------------|--------|-------|
| OpenRouter  | ✅ Yes | OpenRouter API | Already dynamically fetched |
| OpenAI      | ❓ Unknown | | Likely available via API |
| Anthropic   | ❓ Unknown | | TBD |
| Groq        | ❓ Unknown | | TBD |
| Nebius      | ❓ Unknown | | TBD |
| Together AI| ❓ Unknown | | TBD |
| Cerebras   | ❓ Unknown | | TBD |
| Qwen       | ❓ Unknown | | TBD |
| Moonshot   | ❓ Unknown | | TBD |

---

## Findings from Codebase Inspection

- Model handling is driven by user-supplied strings
- Provider inference occurs via model prefixes
- Tests confirm no hardcoded provider model lists
- UX-facing model lists (docs / interactive setup) are the primary candidates for automation

---

## Next Steps

1. Identify UX-facing model lists (CLI, interactive setup, docs)
2. Investigate provider APIs and LiteLLM support for listing models
3. Implement automatic listing where supported
4. Clearly document providers requiring manual updates

