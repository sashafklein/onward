---
id: "CHUNK-015"
type: "chunk"
plan: "PLAN-012"
project: ""
title: "Executor protocol and external adapter"
status: "completed"
description: "Define the Executor ABC with TaskContext/ExecutorResult types and implement SubprocessExecutor wrapping the existing stdin JSON protocol."
priority: "high"
model: "composer-2"
depends_on:
- "CHUNK-014"
created_at: "2026-03-20T21:50:09Z"
updated_at: "2026-03-20T22:27:49Z"
---

# Summary

Define the Python `Executor` abstract base class that all executor implementations must satisfy. Create `TaskContext` and `ExecutorResult` dataclasses for the interface. Implement `SubprocessExecutor` that wraps the existing subprocess + stdin JSON protocol, preserving full backward compatibility with `scripts/onward-exec` and custom executors. Add `resolve_executor()` to pick built-in vs external based on config.

# Scope

- `Executor` ABC with `execute_task()` and `execute_batch()` (iterator-based)
- `TaskContext` dataclass: task, model, run_id, plan/chunk context, notes
- `ExecutorResult` dataclass: task_id, run_id, success, output, error, ack, return_code
- `SubprocessExecutor` implementation using existing JSON payload format
- `resolve_executor(config)` that returns SubprocessExecutor when `executor.command` is set (and not "builtin"), or BuiltinExecutor otherwise
- Default `execute_batch` implementation in ABC that loops `execute_task`

# Out of scope

- BuiltinExecutor implementation (chunk 3)
- Wiring into execution.py (chunk 4)
- Changing JSON payload schema

# Dependencies

- CHUNK-014 (model config) -- `resolve_executor` needs the new model resolution for TaskContext

# Expected files/systems involved

- `src/onward/executor.py` -- new file: ABC, dataclasses, SubprocessExecutor
- `src/onward/config.py` -- `resolve_executor()` function
- `src/onward/executor_payload.py` -- reuse for SubprocessExecutor payloads
- `src/onward/executor_ack.py` -- reuse for parsing ack from subprocess output
- `tests/` -- new tests for protocol, SubprocessExecutor

# Completion criteria

- [ ] `Executor` ABC is importable from `onward.executor`
- [ ] `SubprocessExecutor` produces identical subprocess calls as current `_execute_task_run`
- [ ] `execute_batch` default yields results from sequential `execute_task` calls
- [ ] `resolve_executor()` returns SubprocessExecutor for `executor.command: "onward-exec"`
- [ ] `resolve_executor()` returns BuiltinExecutor (stub/placeholder) when command is absent
- [ ] Type annotations are complete; protocol is documented in docstrings
