---
id: "TASK-054"
type: "task"
plan: "PLAN-012"
chunk: "CHUNK-014"
project: ""
title: "Implement tiered model schema with fallback chains"
status: "completed"
description: "Replace flat models config with tiered default/high/medium/low/split/review_1/review_2 and implement fallback chain resolution."
human: false
model: "composer-2"
effort: "medium"
depends_on: []
files:
- "src/onward/config.py"
- ".onward.config.yaml"
- "src/onward/scaffold.py"
acceptance:
- "CONFIG_SECTION_KEYS['models'] contains default, high, medium, low, split, review_1, review_2"
- "resolve_model_for_tier(config, 'low') walks low -> medium -> high -> default"
- "resolve_model_for_tier(config, 'review_1') walks review_1 -> high -> default"
- "resolve_model_for_tier(config, 'review_2') walks review_2 -> high -> default"
- "resolve_model_for_tier(config, 'split') walks split -> default"
- "model_setting() still works for callers that haven't migrated yet"
- "All existing tests pass"
created_at: "2026-03-20T21:51:37Z"
updated_at: "2026-03-20T22:18:40Z"
run_count: 1
last_run_status: "completed"
---

# Context

First task in CHUNK-014. Establishes the new model config schema and the core fallback resolution function that everything else builds on.

# Scope

- Update `CONFIG_SECTION_KEYS["models"]` to accept: `default`, `high`, `medium`, `low`, `split`, `review_1`, `review_2`
- Implement `resolve_model_for_tier(config, tier_name) -> str` with these fallback chains:
  - `high` -> `default`
  - `medium` -> `high` -> `default`
  - `low` -> `medium` -> `high` -> `default`
  - `split` -> `default`
  - `review_1` -> `high` -> `default`
  - `review_2` -> `high` -> `default`
- Update `.onward.config.yaml` to use new key names
- Update `scaffold.py` to generate the new config shape on `onward init`
- Keep `model_setting()` working for backward compat during migration

# Out of scope

- Effort-based resolution (TASK-055)
- Old key deprecation warnings (TASK-056)
- Changing execution.py callers (CHUNK-017)

# Files to inspect

- `src/onward/config.py` -- current `model_setting()`, `CONFIG_SECTION_KEYS`, `build_plan_review_slots()`
- `.onward.config.yaml` -- current model keys
- `src/onward/scaffold.py` -- `onward init` template

# Implementation notes

- The fallback chain can be a simple dict: `FALLBACK = {"high": ["default"], "medium": ["high", "default"], "low": ["medium", "high", "default"], ...}`
- `resolve_model_for_tier` walks the chain, returning the first non-empty value
- `models.default` is required; if missing, fall back to `"opus-latest"` hardcoded
- Update `build_plan_review_slots()` to use `review_1` and `review_2` instead of `review_default` and `default`

# Acceptance criteria

- [ ] `resolve_model_for_tier({"models": {"default": "X"}}, "low")` returns `"X"` (full chain)
- [ ] `resolve_model_for_tier({"models": {"default": "X", "low": "Y"}}, "low")` returns `"Y"` (direct)
- [ ] `resolve_model_for_tier({"models": {"default": "X", "medium": "Y"}}, "low")` returns `"Y"` (partial chain)
- [ ] `build_plan_review_slots` uses `review_1` and `review_2`
- [ ] `onward init` produces config with new model key names
- [ ] All existing tests pass (adapted where needed)
