---
id: "TASK-055"
type: "task"
plan: "PLAN-012"
chunk: "CHUNK-014"
project: ""
title: "Add effort-based task-to-model resolution"
status: "completed"
description: "Implement resolve_model_for_task that checks explicit model, then effort tier, then default."
human: false
model: "composer-2"
effort: "small"
depends_on:
- "TASK-054"
files:
- "src/onward/config.py"
acceptance:
- "resolve_model_for_task returns explicit model when set in frontmatter"
- "resolve_model_for_task maps effort:low to models.low with fallback"
- "resolve_model_for_task returns models.default when neither model nor effort is set"
created_at: "2026-03-20T21:51:37Z"
updated_at: "2026-03-20T22:22:24Z"
run_count: 1
last_run_status: "completed"
---

# Context

Builds on TASK-054's tier resolution to add task-level model resolution. This is what execution.py will use to determine which model to run a task with.

# Scope

- Implement `resolve_model_for_task(config, task_metadata) -> str`:
  1. If `task_metadata["model"]` is set and non-empty, return it as-is
  2. If `task_metadata["effort"]` is set (high/medium/low), call `resolve_model_for_tier(config, effort)`
  3. Otherwise, return `resolve_model_for_tier(config, "default")`
- Add unit tests for all three resolution paths

# Out of scope

- Wiring into execution.py (CHUNK-017)
- Validating effort values (accept any string, only high/medium/low map to tiers)

# Files to inspect

- `src/onward/config.py` -- where `resolve_model_for_tier` was added in TASK-054

# Implementation notes

- Unknown effort values (e.g. "xl", "xs") should fall through to `default`
- The function should be pure (no side effects, no file I/O)

# Acceptance criteria

- [ ] `resolve_model_for_task(config, {"model": "custom-model"})` returns `"custom-model"`
- [ ] `resolve_model_for_task(config, {"effort": "low"})` returns the low-tier model
- [ ] `resolve_model_for_task(config, {})` returns the default model
- [ ] Unknown effort values fall through to default
