# Backend Model Listing Discovery (MAS-163)

## Overview

MassGen’s runtime model handling is **string-based and provider-agnostic**.

Model selection relies on:
- User-supplied model strings
- Provider prefixes (e.g. `groq/`, `together/`, `cerebras/`)
- LiteLLM backend routing

There are **no strict provider-specific model registries** used during execution.

As a result, automatic model listing primarily improves:
- CLI UX (interactive selection, suggestions)
- Documentation accuracy
- Example configurations

It does **not** affect core execution or routing.

---

## Current Model Listing Status

| Provider     | Automatic Listing | Notes |
|-------------|------------------|-------|
| OpenRouter  | ✅ Yes | Models fetched dynamically |
| OpenAI      | ❌ No | Manually referenced |
| Anthropic   | ❌ No | Manually referenced |
| Groq        | ❌ No | Manually referenced |
| Nebius      | ❌ No | Manually referenced |
| Together AI | ❌ No | Manually referenced |
| Cerebras    | ❌ No | Manually referenced |
| Qwen        | ❌ No | Manually referenced |
| Moonshot    | ❌ No | Manually referenced |

---

## Findings

- Runtime model handling does **not** rely on provider registries
- Provider inference occurs via model name prefixes
- Tests confirm no hardcoded provider → model mappings
- Model names primarily appear in:
  - documentation
  - CLI examples
  - presentation artifacts

---

## Recommendations

1. Clearly document which providers support automatic model discovery
2. Mark providers requiring manual updates
3. Explore API-based model listing only for UX-facing components
4. Avoid introducing execution-time dependencies on model registries
