---
id: "TASK-040"
type: "task"
plan: "PLAN-005"
chunk: "CHUNK-012"
project: ""
title: "Wire WorkReporter into work_task and _finalize_task_run in execution.py"
status: "open"
description: ""
human: false
model: "sonnet-latest"
executor: "onward-exec"
depends_on: ["TASK-037", "TASK-039"]
files: ["src/onward/execution.py"]
acceptance: []
created_at: "2026-03-21T16:26:53Z"
updated_at: "2026-03-21T16:26:53Z"
---

# Context

Final wiring task. Handles the standalone `work_task()` path (for `onward work TASK-XXX`) and the `_finalize_task_run` / `_run_one_task_with_hooks` internals where task completion/failure is determined and announced.

# Scope

- Add `reporter: WorkReporter | None = None` to `work_task()` (~line 876)
- In `work_task()`: use `reporter.status_change()` when setting task to `in_progress`, `reporter.working_on()` before executor call
- Add reporter parameter to `_finalize_task_run()` (~line 387) and `_run_one_task_with_hooks()` (~line 451)
- In `_finalize_task_run`: use `reporter.completed()` / `reporter.failed()` based on result
- Replace remaining `print()` calls in `work_task` for: already-completed, max-retries, preflight errors
- Wire reporter through `_execute_task_run()` (~line 618) to ensure the standalone task path gets full output

# Out of scope

- Chunk-level wiring (TASK-039)
- Tests (CHUNK-013)

# Files to inspect

- `src/onward/execution.py` lines 876–919 (`work_task`)
- `src/onward/execution.py` lines 387–462 (`_finalize_task_run`, `_run_one_task_with_hooks`)
- `src/onward/execution.py` lines 618–624 (`_execute_task_run`)

# Implementation notes

- `_finalize_task_run` is called from both the chunk loop path and the standalone task path — reporter must work in both
- When called from the chunk loop, the reporter already has the right indentation from TASK-039's `indent()` calls
- When called from standalone `work_task`, indentation is at root level (correct)
- The `parallel_execute` function (~line 465) calls `_run_one_task_with_hooks` in threads — reporter's lock handles this

# Acceptance criteria

- [ ] `work_task` accepts and uses reporter
- [ ] `_finalize_task_run` uses reporter for completion/failure
- [ ] `onward work TASK-XXX` shows status transitions with title
- [ ] No bare `print()` calls remain anywhere in the work execution path

# Handoff notes

After this, the full work path is wired. CHUNK-013 adds tests and fixes any regressions.
