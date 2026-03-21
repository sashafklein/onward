---
id: "PLAN-006"
type: "plan"
project: ""
title: "Simple model aliases (opus, sonnet, haiku, codex)"
status: "completed"
description: ""
priority: "medium"
model: "opus"
created_at: "2026-03-21T18:54:50Z"
updated_at: "2026-03-21T18:54:50Z"
---

# Summary

Add actual model alias resolution to Onward. The docs claim aliases like `opus-latest` resolve
to canonical model IDs like `claude-opus-4-6`, but no such resolution exists in code — model
strings are passed verbatim to CLI backends. Simplify to four clean aliases (`opus`, `sonnet`,
`haiku`, `codex`) that resolve to current canonical model IDs.

# Problem

INSTALLATION.md documents a model alias table that isn't implemented. Users see aliases
in the docs/scaffold config but the code just passes strings through. The `-latest` suffix
variants are unnecessary noise — "latest" should be implied.

# Goals

- Implement `MODEL_ALIASES` dict and `resolve_model_alias()` in `config.py`
- Support four simple aliases: `opus`, `sonnet`, `haiku`, `codex`
- Resolve aliases before passing model strings to CLI backends
- Update all default/fallback values from `opus-latest` → `opus`, `haiku-latest` → `haiku`, etc.
- Update scaffold templates, docs, prompts, and tests

# Non-goals

- No need for `-latest` suffix variants
- No need for `gpt5` alias (drop it from docs)

# Proposed approach

1. **`config.py`**: Add `MODEL_ALIASES` dict mapping `opus` → `claude-opus-4-6`, `sonnet` → `claude-sonnet-4-6`, `haiku` → `claude-haiku-4`, `codex` → `codex-5-3`. Add `resolve_model_alias(model: str) -> str` that does case-insensitive lookup, returning the input unchanged if not an alias.
2. **`executor_builtin.py`**: Call `resolve_model_alias` in `BuiltinExecutor.execute_task` before building argv. Also apply in `route_model_to_backend` for consistent routing.
3. **`config.py` defaults**: Change `effective_default_model` fallback from `"opus-latest"` to `"opus"`.
4. **`scaffold.py`**: Update default config template to use short aliases.
5. **Prompts**: Update split/task prompts to reference short aliases.
6. **Docs**: Update INSTALLATION.md alias table and examples.
7. **Tests**: Update all `opus-latest`/`haiku-latest`/`codex-latest` references. Add tests for `resolve_model_alias`.

# Acceptance criteria

- `resolve_model_alias("opus")` returns `"claude-opus-4-6"`
- `resolve_model_alias("sonnet")` returns `"claude-sonnet-4-6"`
- `resolve_model_alias("haiku")` returns `"claude-haiku-4"`
- `resolve_model_alias("codex")` returns `"codex-5-3"`
- `resolve_model_alias("claude-opus-4-6")` returns `"claude-opus-4-6"` (passthrough)
- No remaining references to `opus-latest`, `haiku-latest`, `codex-latest` in source or scaffold
- All tests pass
