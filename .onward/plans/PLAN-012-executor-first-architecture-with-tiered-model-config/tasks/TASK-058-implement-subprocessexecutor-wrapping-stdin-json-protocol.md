---
id: "TASK-058"
type: "task"
plan: "PLAN-012"
chunk: "CHUNK-015"
project: ""
title: "Implement SubprocessExecutor wrapping stdin JSON protocol"
status: "completed"
description: "Implement SubprocessExecutor that wraps the existing external executor subprocess + stdin JSON protocol for backward compatibility."
human: false
model: "composer-2"
effort: "medium"
depends_on:
- "TASK-057"
files:
- "src/onward/executor.py"
- "src/onward/executor_payload.py"
- "src/onward/executor_ack.py"
acceptance:
- "SubprocessExecutor builds identical JSON payload as current _execute_task_run"
- "SubprocessExecutor spawns executor.command with executor.args"
- "SubprocessExecutor parses ack from output using existing executor_ack module"
- "ExecutorResult is populated correctly from subprocess output"
created_at: "2026-03-20T21:51:37Z"
updated_at: "2026-03-20T22:26:30Z"
run_count: 1
last_run_status: "completed"
---

# Context

This is the backward-compat adapter. When `executor.command` is set in config, this class wraps the existing stdin JSON protocol so external executors (including `scripts/onward-exec`) work identically.

# Scope

- `SubprocessExecutor(Executor)` class in `src/onward/executor.py`:
  - Constructor takes `command: str` and `args: list[str]`
  - `execute_task()`:
    1. Build JSON payload from TaskContext (same shape as current `_execute_task_run`)
    2. `subprocess.run([command, *args], input=json_payload, capture_output=True, ...)`
    3. Parse stdout/stderr for `onward_task_result` ack via `executor_ack.find_task_success_ack()`
    4. Return `ExecutorResult` with all fields populated
  - Reuse `with_schema_version()` from `executor_payload.py`
- Unit tests with mock subprocess

# Out of scope

- Batch payload format for external executors (they get sequential single-task calls)
- BuiltinExecutor (CHUNK-016)

# Files to inspect

- `src/onward/execution.py` -- current `_execute_task_run()` for exact payload shape
- `src/onward/executor_payload.py` -- `with_schema_version()`
- `src/onward/executor_ack.py` -- `find_task_success_ack()`

# Implementation notes

- The payload must include `type`, `run_id`, `task`, `body`, `notes`, `chunk`, `plan` -- match current shape exactly
- Set `ONWARD_RUN_ID` in subprocess env (same as current behavior)
- Handle `FileNotFoundError` when command doesn't exist (return failed ExecutorResult)

# Acceptance criteria

- [ ] Payload JSON is identical to what `_execute_task_run` currently produces
- [ ] `ONWARD_RUN_ID` env var set on subprocess
- [ ] Ack parsing uses `find_task_success_ack()` 
- [ ] FileNotFoundError produces a failed ExecutorResult (not an exception)
- [ ] Unit tests verify payload shape and result parsing
