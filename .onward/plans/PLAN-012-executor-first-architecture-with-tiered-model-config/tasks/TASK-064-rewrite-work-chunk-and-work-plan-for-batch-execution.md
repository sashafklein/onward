---
id: "TASK-064"
type: "task"
plan: "PLAN-012"
chunk: "CHUNK-017"
project: ""
title: "Rewrite _work_chunk and _work_plan for batch execution"
status: "completed"
description: "Refactor _work_chunk to collect all ready tasks, build TaskContexts, and use execute_batch with iterator-based result handling."
human: false
model: "composer-2"
effort: "large"
depends_on:
- "TASK-063"
files:
- "src/onward/execution.py"
- "src/onward/cli_commands.py"
acceptance:
- "_work_chunk collects all ready tasks and calls execute_batch"
- "Status updated after each task result yields"
- "Failure in task N stops the batch"
- "_work_plan uses batch per chunk"
- "All lifecycle tests pass"
created_at: "2026-03-20T21:51:37Z"
updated_at: "2026-03-20T22:41:13Z"
run_count: 1
last_run_status: "completed"
---

# Context

The batch execution integration. Instead of the current loop in `cli_commands.py` that picks one ready task at a time and calls `work_task()`, the new flow collects all ready tasks upfront, builds TaskContexts with resolved models, and passes the batch to the executor.

# Scope

- Refactor `_work_chunk` (in `cli_commands.py` or `execution.py`):
  1. Run pre_chunk_shell hooks
  2. Collect all ready tasks via `ordered_ready_chunk_tasks()`
  3. For each: resolve model, generate run_id, build TaskContext
  4. Call `executor.execute_batch(root, contexts)` -> Iterator[ExecutorResult]
  5. For each yielded result:
     a. Write run log
     b. Update run record
     c. Update task status (completed/failed)
     d. Run post_task hooks on success
     e. If failure: break (stop batch)
  6. If all succeeded: run post_chunk hook, mark chunk completed
- Adapt `_work_plan` to use the same batch-per-chunk pattern
- Single-task `work_task()` creates a one-element list and goes through the same path

# Out of scope

- Parallel execution
- Changing dependency resolution logic
- Changing the ready-task selection algorithm

# Files to inspect

- `src/onward/cli_commands.py` -- `_work_chunk()`, `_work_plan()`, `cmd_work()`
- `src/onward/execution.py` -- `work_task()`, `ordered_ready_chunk_tasks()`

# Implementation notes

- The current `_work_chunk` in `cli_commands.py` has a while-loop that calls `ordered_ready_chunk_tasks()` on each iteration. The new version collects once and passes to execute_batch. If blocked tasks exist (dependencies not yet met), we may need multiple passes: first batch unblocked tasks, then re-check.
- Consider: after the first batch completes, re-check for newly-unblocked tasks and do another batch. Continue until no more ready tasks.
- Circuit breaker checks should happen during TaskContext building (skip maxed tasks).

# Acceptance criteria

- [ ] `onward work CHUNK-*` sends all ready tasks to executor in one batch call
- [ ] After first batch, re-checks for newly-unblocked tasks
- [ ] Each task result triggers immediate status update
- [ ] First failure stops the current batch
- [ ] Post-chunk hook runs only when all tasks complete successfully
- [ ] `onward work PLAN-*` runs each chunk as a batch
- [ ] Circuit breaker still prevents re-running maxed tasks
- [ ] `test_cli_work.py` and `test_cli_lifecycle.py` pass
