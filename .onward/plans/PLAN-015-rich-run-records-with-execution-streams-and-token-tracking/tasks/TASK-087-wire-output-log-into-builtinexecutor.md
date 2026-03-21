---
id: "TASK-087"
type: "task"
plan: "PLAN-015"
chunk: "CHUNK-025"
project: ""
title: "Wire output_log file handle into BuiltinExecutor.execute_task"
status: "open"
description: ""
human: false
model: "sonnet-latest"
executor: "onward-exec"
depends_on: ["TASK-086"]
files: []
acceptance: []
created_at: "2026-03-21T03:40:00Z"
updated_at: "2026-03-21T03:40:00Z"
---

# Context

With `_tee_stream` updated (TASK-086), `BuiltinExecutor.execute_task` needs to open
the `output_log` path (from the execution context or passed as an argument), create a
shared lock, pass both to the tee threads, and close the handle after the threads join.

# Scope

- Accept or derive `output_log: Path` in `BuiltinExecutor.execute_task` (sourced from `PreparedTaskRun` passed through the call chain)
- Open `output_log.open("w", encoding="utf-8")` before `Popen`
- Create `threading.Lock()` shared between stdout and stderr tee threads
- Pass `file_out=handle, file_lock=lock` to both `_tee_stream` calls
- Close handle in a `finally` block after both threads join

# Out of scope

- How `output_log` arrives at the executor (may need a small signature change in the execution dispatch path)

# Files to inspect

- `src/onward/executor_builtin.py` — `BuiltinExecutor.execute_task`
- `src/onward/execution.py` — how `execute_task` is called and what context is passed

# Implementation notes

- If `output_log` is None or not provided, skip the file handle entirely (graceful degradation)
- The `finally` block must close the handle even if the subprocess errors or a tee thread raises
- Touch (create empty) the file before passing it to the threads so `tail -f` can attach early

# Acceptance criteria

- [ ] `output-<ts>.log` exists and is non-empty after a task run
- [ ] File is closed cleanly after execution (no open file handle leaks)
- [ ] Both stdout and stderr lines appear in the output log
- [ ] Running `tail -f` on the file from another terminal shows live output during a task

# Handoff notes

After this task, the live streaming goal from the plan is complete. CHUNK-028 adds CLI display of the output log path.
