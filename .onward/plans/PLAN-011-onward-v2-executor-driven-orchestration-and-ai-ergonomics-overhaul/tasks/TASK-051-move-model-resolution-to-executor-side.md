---
id: "TASK-051"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-013"
project: ""
title: "Move model resolution to executor side"
status: "open"
description: ""
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T16:01:10Z"
updated_at: "2026-03-20T16:01:10Z"
---

# Context

Onward currently resolves model aliases (e.g., `sonnet-latest` → `claude-sonnet-4-6`) in `config.py` before passing the model to the executor. This is wrong-layer: the executor knows which models it supports and how to resolve aliases. Different executors may map the same alias differently. This task moves model resolution out of Onward core — Onward passes through the model string as-is, and the executor handles resolution.

# Scope

- Remove `MODEL_FAMILIES` dict from `config.py`
- Remove `resolve_model_alias()` from `config.py`
- Update all callers of `resolve_model_alias` to pass through the raw model string instead:
  - `_execute_task_run` in `execution.py` — model passed to executor payload
  - `run_chunk_post_markdown_hook` in `execution.py`
  - `execute_plan_review` in `execution.py`
  - `build_plan_review_slots` / `_legacy_plan_review_slots` in `config.py` — store raw model
  - `cmd_split` in `cli_commands.py` — model passed to split
- Update the executor payload to pass the raw model string (the executor resolves it)
- Keep `models.*` config keys for default model selection — they just store raw strings now
- Remove `resolve_model_alias` from imports in `execution.py` and `cli_commands.py`
- Update tests that assert on resolved model names to assert on raw alias strings instead
- Update docs to clarify that model resolution is the executor's job

# Out of scope

- Changing the executor script to add model resolution (that's already the executor's domain)
- Changing config key names (`models.default`, etc.)
- Adding model validation in Onward (executor validates)
- Removing model fields from artifact metadata

# Files to inspect

- `src/onward/config.py` — `MODEL_FAMILIES` (line ~9), `resolve_model_alias` (line ~157), `PlanReviewTry` (uses resolved model), `_legacy_plan_review_slots`, `build_plan_review_slots`
- `src/onward/execution.py` — `_execute_task_run` (line ~191), `run_chunk_post_markdown_hook` (line ~432), `execute_plan_review` (line ~552)
- `src/onward/cli_commands.py` — `cmd_split` (line ~634), import of `resolve_model_alias`
- `tests/test_cli_work.py` — tests that check model values in payloads
- `tests/test_cli_review.py` — tests that check resolved model names

# Implementation notes

- The `PlanReviewTry` dataclass has `model_resolved: str`. After this change, it should be renamed to just `model: str` (it's no longer "resolved"). This is a simple rename with `replace_all`.
- `_execute_task_run` currently does: `model = resolve_model_alias(task_model)`. After: `model = task_model` (just the raw string).
- `_legacy_plan_review_slots` and `build_plan_review_slots` wrap models in `resolve_model_alias()`. Remove those calls.
- Search for all uses of `resolve_model_alias` to find every call site. There should be ~6 call sites.
- The `model_setting` function in `config.py` stays unchanged — it reads a string from config. No resolution needed.
- Tests that construct payloads and check `model` values may assert `"claude-sonnet-4-6"` where they should now assert `"sonnet-latest"`. Update these.
- Consider: should the `PlanReviewSlot` field name change from `model_resolved` to `model`? Yes — it's cleaner and the "resolved" suffix is misleading once we stop resolving.

# Acceptance criteria

- `MODEL_FAMILIES` dict is removed from `config.py`
- `resolve_model_alias` function is removed from `config.py`
- Executor payloads contain raw model strings (e.g., `"sonnet-latest"`, not `"claude-sonnet-4-6"`)
- No call to `resolve_model_alias` remains in the codebase
- `PlanReviewTry.model_resolved` renamed to `PlanReviewTry.model`
- All tests pass with updated model string assertions
- `models.*` config keys still work for default model selection

# Handoff notes

- The executor reference script (`scripts/onward-exec`) needs to implement its own model resolution — map `sonnet-latest` to whatever the current model version is. This should already be the case if the executor is set up correctly.
- This is a clean refactor — no behavior change from the user's perspective, just cleaner separation of concerns.
- The `PlanReviewTry` rename from `model_resolved` to `model` affects `cmd_review_plan` in `cli_commands.py` which prints the field. Update the log message too.
