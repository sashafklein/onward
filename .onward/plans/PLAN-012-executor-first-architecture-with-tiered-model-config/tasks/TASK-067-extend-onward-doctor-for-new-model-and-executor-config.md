---
id: "TASK-067"
type: "task"
plan: "PLAN-012"
chunk: "CHUNK-018"
project: ""
title: "Extend onward doctor for new model and executor config"
status: "completed"
description: "Add doctor checks for the new tiered model config, executor resolution, and builtin executor prerequisites."
human: false
model: "composer-2"
effort: "small"
depends_on:
- "TASK-066"
files:
- "src/onward/config.py"
- "tests/test_cli_init_doctor.py"
acceptance:
- "onward doctor validates new model tier keys"
- "onward doctor warns on old model keys"
- "onward doctor checks builtin executor prerequisites (claude/cursor on PATH)"
created_at: "2026-03-20T21:51:37Z"
updated_at: "2026-03-21T00:14:46Z"
run_count: 1
last_run_status: "completed"
---

# Context

Config validation needs to understand the new model schema and executor resolution. Some of this may already be in place from TASK-056 (migration warnings), but this task adds the executor-side checks.

# Scope

- Validate model config: `default` should be set (warn if missing and no old `default` key)
- Validate tier values: if set, should be non-empty strings
- Validate executor config: if `executor.command` is absent or "builtin", check that at least one AI CLI is on PATH
- Warn if configured model strings don't match any known backend pattern
- Architecture seam tests for `executor.py` and `executor_builtin.py` modules

# Out of scope

- Preflight changes (existing preflight handles command existence)

# Files to inspect

- `src/onward/config.py` -- `validate_config_contract_issues()`
- `src/onward/preflight.py` -- existing preflight checks
- `tests/test_architecture_seams.py` -- existing seam tests

# Acceptance criteria

- [ ] `onward doctor` on a config with unknown model keys reports them
- [ ] `onward doctor` with no `models.default` and no old keys warns
- [ ] Architecture seam tests include `executor.py` and `executor_builtin.py`
