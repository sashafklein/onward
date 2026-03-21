---
id: "TASK-056"
type: "task"
plan: "PLAN-012"
chunk: "CHUNK-014"
project: ""
title: "Migrate old model config keys with deprecation warnings"
status: "completed"
description: "Add onward doctor warnings for old model keys (task_default, split_default, review_default) and treat them as aliases during transition."
human: false
model: "composer-2"
effort: "small"
depends_on:
- "TASK-054"
files:
- "src/onward/config.py"
- "tests/test_cli_init_doctor.py"
acceptance:
- "onward doctor warns on task_default, split_default, review_default"
- "Old keys are treated as aliases: split_default -> split, review_default -> review_1"
- "Both old and new keys present produces a warning (new wins)"
created_at: "2026-03-20T21:51:37Z"
updated_at: "2026-03-20T22:24:17Z"
run_count: 1
last_run_status: "completed"
---

# Context

Smooth migration path so existing configs don't break. Old keys are read as aliases but produce doctor warnings encouraging migration.

# Scope

- In `config_raw_deprecation_warnings()`, add warnings for old model keys
- In `validate_config_contract_issues()`, accept old keys without "unsupported" errors but add deprecation warnings
- In `resolve_model_for_tier()`, if new key is empty, check old alias:
  - `task_default` -> ignored (was for new task creation, not a tier)
  - `split_default` -> `split`
  - `review_default` -> `review_1`
- If both old and new key are set, new wins with a warning
- Unit tests for migration scenarios

# Out of scope

- Removing old keys entirely (can happen in a future plan)

# Files to inspect

- `src/onward/config.py` -- `config_raw_deprecation_warnings()`, `validate_config_contract_issues()`
- `tests/test_cli_init_doctor.py` -- existing doctor tests

# Implementation notes

- `CONFIG_SECTION_KEYS["models"]` should accept both old and new keys (no "unsupported" error for old ones during transition)
- The migration is read-only: Onward never rewrites the user's config file

# Acceptance criteria

- [ ] Config with `split_default: sonnet-latest` and no `split` key: resolves split to sonnet-latest with doctor warning
- [ ] Config with both `split_default: X` and `split: Y`: uses Y with doctor warning about old key
- [ ] `onward doctor` output includes clear migration message for each old key
