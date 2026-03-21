---
id: "TASK-061"
type: "task"
plan: "PLAN-012"
chunk: "CHUNK-016"
project: ""
title: "Port prompt building from scripts/onward-exec into Python"
status: "completed"
description: "Move build_task_prompt, build_hook_prompt, build_review_prompt from scripts/onward-exec into src/onward/executor_builtin.py."
human: false
model: "composer-2"
effort: "small"
depends_on:
- "TASK-060"
files:
- "src/onward/executor_builtin.py"
- "scripts/onward-exec"
acceptance:
- "build_task_prompt produces equivalent output to scripts/onward-exec version"
- "build_hook_prompt produces equivalent output"
- "build_review_prompt produces equivalent output"
- "Functions accept TaskContext (or equivalent data) instead of raw payload dicts"
created_at: "2026-03-20T21:51:37Z"
updated_at: "2026-03-20T22:31:19Z"
run_count: 1
last_run_status: "completed"
---

# Context

The reference executor script has prompt building functions that construct the text sent to AI CLIs. Moving these into Python means the built-in executor doesn't need to serialize to JSON and back -- it can build prompts directly from TaskContext.

# Scope

- Port `build_task_prompt(payload)` -> `build_task_prompt(ctx: TaskContext) -> str`
- Port `build_hook_prompt(payload)` -> keep payload-based for now (hooks aren't TaskContext)
- Port `build_review_prompt(payload)` -> keep payload-based for now
- Add `_plan_context_lines()` and `_chunk_context_lines()` helpers
- Unit tests comparing output to the reference executor's versions

# Out of scope

- Changing prompt content (pure port, not improvement)
- Removing functions from scripts/onward-exec (it stays as reference)

# Files to inspect

- `scripts/onward-exec` lines 29-99 -- current prompt building functions

# Implementation notes

- The TaskContext-based `build_task_prompt` extracts plan/chunk context from `ctx.plan_context` and `ctx.chunk_context` dicts
- Keep the output format identical to ensure no regression
- Hook and review prompts can stay dict-based since those paths may not use TaskContext yet

# Acceptance criteria

- [ ] `build_task_prompt(ctx)` produces same text as `scripts/onward-exec:build_task_prompt(payload)` for equivalent inputs
- [ ] Tests verify output equivalence for task, hook, and review prompts
- [ ] Functions are importable from `onward.executor_builtin`
