---
id: "CHUNK-014"
type: "chunk"
plan: "PLAN-012"
project: ""
title: "Tiered model config"
status: "completed"
description: "Replace flat model keys with tiered default/high/medium/low/split/review_1/review_2 and automatic fallback chains."
priority: "high"
model: "composer-2"
created_at: "2026-03-20T21:50:09Z"
updated_at: "2026-03-20T22:24:10Z"
---

# Summary

Replace the current flat `models` config (`default`, `task_default`, `split_default`, `review_default`) with a tiered system: `default`, `high`, `medium`, `low`, `split`, `review_1`, `review_2`. Each key except `default` has an automatic fallback chain. Tasks can declare `effort: high|medium|low` to get the appropriate model tier automatically.

# Scope

- New `models` config schema with 7 keys
- Fallback chain resolution: `low` -> `medium` -> `high` -> `default`; `review_1`/`review_2` -> `high` -> `default`; `split` -> `default`
- `resolve_model_for_task(config, task)` function that checks explicit model, then effort tier, then default
- Migration: old keys (`task_default`, `split_default`, `review_default`) produce `onward doctor` warnings
- Update `build_plan_review_slots()` to use `review_1` and `review_2`
- Update scaffold defaults

# Out of scope

- Executor protocol changes (chunk 2)
- Prompt construction changes (chunk 3)
- Changing how execution.py calls the executor (chunk 4)

# Dependencies

None. This chunk is self-contained.

# Expected files/systems involved

- `src/onward/config.py` -- new model schema, fallback resolution, validation, migration warnings
- `.onward.config.yaml` -- new model key names
- `src/onward/scaffold.py` -- updated scaffold defaults
- `src/onward/execution.py` -- update callers of `model_setting()` to use new resolution
- `tests/test_cli_init_doctor.py` -- doctor warning tests
- `tests/test_architecture_seams.py` -- config key validation

# Completion criteria

- [ ] `models.default` is required; all other model keys are optional with documented fallbacks
- [ ] `resolve_model_for_tier(config, "low")` walks `low` -> `medium` -> `high` -> `default`
- [ ] `resolve_model_for_task(config, task)` respects explicit model > effort tier > default
- [ ] `review_1` falls back to `high` -> `default`; `review_2` falls back to `high` -> `default`
- [ ] `onward doctor` warns on old keys (`task_default`, `split_default`, `review_default`)
- [ ] `onward init` scaffolds the new model key names
- [ ] All existing tests pass with adapted model config
