---
id: "TASK-057"
type: "task"
plan: "PLAN-012"
chunk: "CHUNK-015"
project: ""
title: "Define Executor ABC, TaskContext, and ExecutorResult"
status: "completed"
description: "Create the executor protocol in a new src/onward/executor.py with the abstract interface, context, and result types."
human: false
model: "composer-2"
effort: "medium"
depends_on: []
files:
- "src/onward/executor.py"
acceptance:
- "Executor ABC has execute_task and execute_batch methods"
- "execute_batch default impl yields results from sequential execute_task calls"
- "TaskContext contains task, model, run_id, plan_context, chunk_context, notes"
- "ExecutorResult contains task_id, run_id, success, output, error, ack, return_code"
- "All types have complete type annotations"
created_at: "2026-03-20T21:51:37Z"
updated_at: "2026-03-20T22:25:03Z"
run_count: 1
last_run_status: "completed"
---

# Context

Foundation for the entire executor architecture. This defines the contract that both BuiltinExecutor and SubprocessExecutor must satisfy.

# Scope

- Create `src/onward/executor.py`
- `TaskContext` frozen dataclass:
  - `task: Artifact` -- the task artifact
  - `model: str` -- already resolved through fallback chain
  - `run_id: str` -- pre-generated run ID
  - `plan_context: dict | None` -- plan metadata+body if available
  - `chunk_context: dict | None` -- chunk metadata+body if available
  - `notes: str | None` -- task notes
- `ExecutorResult` dataclass:
  - `task_id: str`
  - `run_id: str`
  - `success: bool`
  - `output: str` -- captured stdout
  - `error: str` -- captured stderr or error message
  - `ack: dict | None` -- parsed onward_task_result
  - `return_code: int`
- `Executor` ABC:
  - `execute_task(self, root: Path, ctx: TaskContext) -> ExecutorResult` (abstract)
  - `execute_batch(self, root: Path, tasks: list[TaskContext]) -> Iterator[ExecutorResult]` (default: loop)

# Out of scope

- SubprocessExecutor implementation (TASK-058)
- BuiltinExecutor implementation (CHUNK-016)
- Wiring into execution.py (CHUNK-017)

# Files to inspect

- `src/onward/artifacts.py` -- Artifact type used in TaskContext
- `src/onward/executor_ack.py` -- ack dict shape for ExecutorResult

# Implementation notes

- Use `from __future__ import annotations` for forward references
- `Executor` should be an ABC (not Protocol) since we want a default `execute_batch` implementation
- Import `Artifact` from `onward.artifacts` for TaskContext typing

# Acceptance criteria

- [ ] `from onward.executor import Executor, TaskContext, ExecutorResult` works
- [ ] `Executor` cannot be instantiated directly (ABC)
- [ ] `execute_batch` default yields results in order
- [ ] All fields have type annotations
- [ ] Module has docstring explaining the protocol
