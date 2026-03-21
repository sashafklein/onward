---
id: "TASK-038"
type: "task"
plan: "PLAN-005"
chunk: "CHUNK-012"
project: ""
title: "Wire WorkReporter into cmd_work and _work_plan in cli_commands.py"
status: "open"
description: ""
human: false
model: "sonnet-4-6"
executor: "onward-exec"
depends_on: ["TASK-037"]
files: ["src/onward/cli_commands.py"]
acceptance: []
created_at: "2026-03-21T16:26:45Z"
updated_at: "2026-03-21T16:26:45Z"
---

# Context

First wiring task. Gets the reporter created in `cmd_work` and threaded through the plan-level loop. After this, `onward work PLAN-XXX` will show plan-level status transitions and pass the reporter down to chunk execution.

# Scope

- In `cmd_work()` (~line 1061): construct `WorkReporter(color=sys.stdout.isatty())`, import it
- Pass reporter to `_work_plan()` as a new parameter
- In `_work_plan()` (~line 977): use `reporter.status_change()` when setting plan to `in_progress`
- Use `reporter.indent()` context manager around the chunk loop
- Replace `print()` calls for plan-already-completed, no-chunks, plan-completed-summary, no-chunk-ready, chunk-failure-stop
- Pass reporter through to `_work_chunk()` calls
- Also wire reporter into the `cmd_work` branch for direct `work TASK-XXX` and `work CHUNK-XXX` calls

# Out of scope

- Changes inside `execution.py` functions (TASK-039, TASK-040)
- The reporter class itself (TASK-037)

# Files to inspect

- `src/onward/cli_commands.py` lines 977–1094 (`_work_plan`, `cmd_work`)

# Implementation notes

- `_work_plan` currently has ~8 `print()` calls to replace
- The `_work_chunk` wrapper at line 973 just delegates to `execution.work_chunk` — add reporter passthrough
- For direct `work TASK-XXX`, create reporter and pass to `work_task()`
- `work_chunk` and `work_task` in `execution.py` won't accept reporter yet; use `reporter=None` default so this task can land independently

# Acceptance criteria

- [ ] `WorkReporter` constructed in `cmd_work` and passed to all code paths
- [ ] All `print()` calls in `_work_plan` replaced with reporter methods
- [ ] Plan status transitions show artifact ID and title
- [ ] Plan completion summary uses `reporter.plan_summary()`

# Handoff notes

After this, TASK-039 wires reporter into `work_chunk`/`_work_chunk_loop` in execution.py.
