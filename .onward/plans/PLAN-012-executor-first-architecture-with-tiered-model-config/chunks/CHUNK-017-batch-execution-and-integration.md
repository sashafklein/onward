---
id: "CHUNK-017"
type: "chunk"
plan: "PLAN-012"
project: ""
title: "Batch execution and integration"
status: "completed"
description: "Wire onward work to use the Executor protocol with batch execution for chunks and plans."
priority: "high"
model: "composer-2"
depends_on:
- "CHUNK-015"
- "CHUNK-016"
created_at: "2026-03-20T21:50:09Z"
updated_at: "2026-03-20T22:52:14Z"
---

# Summary

Replace the current per-task subprocess spawning in `execution.py` with calls through the Executor protocol. Refactor `_work_chunk` to collect all ready tasks, resolve their models via the tier system, build TaskContexts, and call `execute_batch()` -- yielding results and updating status/run-records after each task. Single-task and plan-level work use the same path.

# Scope

- Refactor `_execute_task_run()` to delegate to `executor.execute_task()`
- Refactor `_work_chunk` loop to use `executor.execute_batch()` with iterator
- Update run record creation and status management to work with ExecutorResult
- Single `work_task()` creates a one-element batch
- Plan-level `_work_plan` uses batch per chunk
- Hooks (pre/post shell, markdown) stay in Onward, called before/after executor
- Failure handling: stop batch on first failure, report which tasks succeeded

# Out of scope

- Parallel execution within a chunk
- Changing hook behavior
- Changing the run record schema

# Dependencies

- CHUNK-015 (executor protocol) -- need the Executor ABC and SubprocessExecutor
- CHUNK-016 (built-in executor) -- need BuiltinExecutor for the default path

# Expected files/systems involved

- `src/onward/execution.py` -- major refactor: delegate to executor, batch-aware loops
- `src/onward/cli_commands.py` -- simplify `_work_chunk`, `_work_plan`
- `tests/test_cli_work.py` -- update for new execution path
- `tests/test_cli_lifecycle.py` -- verify status transitions still work

# Completion criteria

- [ ] `onward work TASK-*` goes through executor.execute_task() (not raw subprocess)
- [ ] `onward work CHUNK-*` collects ready tasks and calls execute_batch()
- [ ] Status updated after each task in batch (observable via run records)
- [ ] Failure in task N stops the batch; tasks N+1.. are not attempted
- [ ] Hooks run at correct points (pre-task before executor, post-task after success)
- [ ] External executor path (SubprocessExecutor) produces identical behavior to before
- [ ] All existing lifecycle and work tests pass
