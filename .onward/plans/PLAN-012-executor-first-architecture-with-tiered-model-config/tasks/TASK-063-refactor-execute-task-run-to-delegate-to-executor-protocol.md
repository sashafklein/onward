---
id: "TASK-063"
type: "task"
plan: "PLAN-012"
chunk: "CHUNK-017"
project: ""
title: "Refactor _execute_task_run to delegate to Executor protocol"
status: "completed"
description: "Replace the raw subprocess spawning in _execute_task_run with a call to executor.execute_task(), keeping all run record and status management in execution.py."
human: false
model: "composer-2"
effort: "large"
depends_on: []
files:
- "src/onward/execution.py"
- "src/onward/config.py"
acceptance:
- "_execute_task_run delegates to executor.execute_task()"
- "Run record creation and status updates remain in execution.py"
- "Hooks still run at correct points (pre/post shell, post markdown)"
- "Existing test suite passes with no behavioral change"
- "External executor path (SubprocessExecutor) produces identical behavior"
created_at: "2026-03-20T21:51:37Z"
updated_at: "2026-03-20T22:36:43Z"
run_count: 1
last_run_status: "completed"
---

# Context

The central refactoring task. Currently `_execute_task_run()` in `execution.py` does everything: builds JSON, spawns subprocess, captures output, writes logs, updates records. This task splits it: the executor handles spawning + output, execution.py handles everything else.

# Scope

- Refactor `_execute_task_run(root, task)`:
  1. Resolve executor via `resolve_executor(config)`
  2. Resolve model via `resolve_model_for_task(config, task.metadata)`
  3. Build `TaskContext` from task, model, run_id, plan/chunk context, notes
  4. Create initial run record (same as today)
  5. Run pre_task_shell hooks (same as today)
  6. Call `executor.execute_task(root, ctx)` -> `ExecutorResult`
  7. Write output to run log from `ExecutorResult.output`
  8. Parse ack from `ExecutorResult.ack`
  9. Run post_task_shell and post_task_markdown hooks on success (same as today)
  10. Update run record with final status
- `work_task()` unchanged in its interface
- Ongoing.json management unchanged

# Out of scope

- Batch execution (TASK-064)
- Changing hook behavior
- Changing run record schema

# Files to inspect

- `src/onward/execution.py` -- `_execute_task_run()` (the big function to refactor)
- `src/onward/config.py` -- `resolve_executor()`, `resolve_model_for_task()`
- `src/onward/executor.py` -- `Executor`, `TaskContext`, `ExecutorResult`

# Implementation notes

- The key insight: `_execute_task_run` currently has a ~60-line block for subprocess management (lines 301-332). That entire block becomes a single `executor.execute_task()` call.
- Everything before (run record setup, hooks) and after (log writing, status update) stays.
- The `model` variable should come from `resolve_model_for_task` now (uses tier fallback).
- Hook markdown execution still needs the executor for the subprocess call -- for now, hooks can continue using the raw subprocess path or be adapted separately.

# Acceptance criteria

- [ ] `_execute_task_run` is shorter: subprocess block replaced with executor call
- [ ] Run log contains same content as before (output from ExecutorResult)
- [ ] Pre/post hooks run in same order and with same behavior
- [ ] `ONWARD_RUN_ID` still set (executor handles this)
- [ ] `work_require_success_ack` logic uses `ExecutorResult.ack`
- [ ] All tests in `test_cli_work.py` pass without changes to test logic
