---
id: "TASK-039"
type: "task"
plan: "PLAN-005"
chunk: "CHUNK-012"
project: ""
title: "Wire WorkReporter into work_chunk and _work_chunk_loop in execution.py"
status: "completed"
description: ""
human: false
model: "sonnet"
executor: "onward-exec"
depends_on:
- "TASK-037"
- "TASK-038"
files:
- "src/onward/execution.py"
acceptance: []
created_at: "2026-03-21T16:26:49Z"
updated_at: "2026-03-21T19:21:13Z"
run_count: 1
last_run_status: "completed"
---

# Context

Second wiring task. Threads the reporter through chunk-level execution so that chunk status transitions and per-task progress are announced.

# Scope

- Add `reporter: WorkReporter | None = None` parameter to `work_chunk()` (~line 1030) and `_work_chunk_loop()` (~line 1059)
- In `work_chunk()`: use `reporter.status_change()` when setting chunk to `in_progress`
- In `_work_chunk_loop()`: use `reporter.indent()` around task execution
- Replace `print()` calls for: chunk-already-completed, DAG errors, unresolved dependencies, max-retries warnings, per-task completion/failure, chunk-stopping, chunk-completed
- Use `reporter.status_change()` when setting each task to `in_progress` (~line 1120)
- Use `reporter.completed()` / `reporter.failed()` for per-task results (~line 1128)
- Pass reporter through to `_run_hooked_executor_batch` / `_execute_task_run`

# Out of scope

- Changes to `_finalize_task_run` internals (TASK-040)
- The reporter class itself (TASK-037)

# Files to inspect

- `src/onward/execution.py` lines 1030–1161 (`work_chunk`, `_work_chunk_loop`)
- `src/onward/execution.py` lines 524–616 (`_run_hooked_executor_batch`)

# Implementation notes

- `_work_chunk_loop` has ~12 `print()` calls to replace
- The `working_on()` call should go right before the executor is invoked
- For parallel execution (`parallel_execute`), the reporter's thread-safe `_write()` handles interleaving
- `_run_hooked_executor_batch` will need the reporter parameter threaded through for completion messages

# Acceptance criteria

- [ ] `work_chunk` and `_work_chunk_loop` accept and use reporter
- [ ] All `print()` calls in chunk execution replaced with reporter methods
- [ ] Chunk/task status transitions show artifact ID and title
- [ ] Chunk completion announced via reporter

# Handoff notes

After this, TASK-040 handles the deeper `_finalize_task_run` / `work_task` wiring.
