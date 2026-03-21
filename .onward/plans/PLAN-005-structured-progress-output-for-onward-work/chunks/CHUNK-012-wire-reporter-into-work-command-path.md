---
id: "CHUNK-012"
type: "chunk"
plan: "PLAN-005"
project: ""
title: "Wire reporter into work command path"
status: "in_progress"
description: ""
priority: "medium"
model: "opus-latest"
created_at: "2026-03-21T16:25:55Z"
updated_at: "2026-03-21T16:42:56Z"
---

# Summary

Thread the `WorkReporter` through the entire `onward work` execution path — from `cmd_work` down through plan loops, chunk loops, and task execution. Replace all bare `print()` calls with reporter methods so the user sees structured, titled, hierarchical progress output.

# Scope

- Construct `WorkReporter` in `cmd_work()` and pass it to `_work_plan` / `_work_chunk` / `work_task`
- Add `reporter: WorkReporter | None = None` parameter to execution functions in `execution.py`
- Replace ~20 bare `print()` calls in `cli_commands.py` and `execution.py` with reporter methods
- Add title resolution where call sites only have artifact IDs
- Use `reporter.indent()` context manager around chunk/task execution in plan/chunk loops
- Handle edge cases: already-completed artifacts, no-chunks plans, dependency failures, max-retries skips

# Out of scope

- Changes to the reporter class itself (CHUNK-011)
- New tests (CHUNK-013)

# Dependencies

- CHUNK-011 (WorkReporter class must exist)

# Expected files/systems involved

- `src/onward/cli_commands.py` (`cmd_work`, `_work_plan`)
- `src/onward/execution.py` (`work_chunk`, `_work_chunk_loop`, `work_task`, `_finalize_task_run`, `_run_hooked_executor_batch`)

# Completion criteria

- [ ] All `print()` calls in the work path replaced with reporter methods
- [ ] `onward work PLAN-XXX` shows hierarchical output with plan/chunk/task titles
- [ ] `onward work CHUNK-XXX` shows chunk/task output
- [ ] `onward work TASK-XXX` shows task output
- [ ] No bare print() calls remain in the work code path
