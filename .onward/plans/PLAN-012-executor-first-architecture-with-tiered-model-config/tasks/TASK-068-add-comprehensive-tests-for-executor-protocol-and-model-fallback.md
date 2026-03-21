---
id: "TASK-068"
type: "task"
plan: "PLAN-012"
chunk: "CHUNK-018"
project: ""
title: "Add comprehensive tests for executor protocol and model fallback"
status: "completed"
description: "Create test files for the new executor protocol, CLI routing, model fallback chains, batch execution, and SubprocessExecutor equivalence."
human: false
model: "composer-2"
effort: "medium"
depends_on:
- "TASK-067"
files:
- "tests/test_executor.py"
- "tests/test_executor_builtin.py"
acceptance:
- "test_executor.py covers: ABC enforcement, TaskContext construction, SubprocessExecutor payload"
- "test_executor_builtin.py covers: CLI routing, prompt building, streaming mock"
- "Model fallback chain tests cover all 7 tiers with various config combinations"
- "Batch execution tests verify stop-on-failure and result ordering"
created_at: "2026-03-20T21:51:37Z"
updated_at: "2026-03-21T00:17:39Z"
run_count: 1
last_run_status: "completed"
---

# Context

Final test coverage sweep. Individual tasks should have unit tests, but this task ensures comprehensive coverage and adds integration-style tests.

# Scope

- `tests/test_executor.py` (new):
  - ABC cannot be instantiated
  - `execute_batch` default yields sequential results
  - SubprocessExecutor builds correct payload
  - SubprocessExecutor handles FileNotFoundError
  - SubprocessExecutor parses ack correctly
- `tests/test_executor_builtin.py` (new):
  - `route_model_to_backend` patterns (all known model families)
  - `ClaudeBackend.build_argv` correctness
  - `CursorBackend.build_argv` correctness
  - `build_task_prompt` equivalence with scripts/onward-exec
  - BuiltinExecutor with mocked subprocess (streaming capture)
  - BuiltinExecutor with missing CLI (graceful failure)
- Model fallback chain tests (can be in existing test files or new):
  - All 7 tiers with full config, partial config, empty config
  - `resolve_model_for_task` with explicit model, effort, and neither
- Batch execution tests:
  - All-success batch
  - Failure mid-batch stops remaining
  - Empty batch (no ready tasks)

# Out of scope

- E2E tests with real AI CLIs (those are manual)

# Files to inspect

- `tests/test_cli_work.py` -- existing work tests for reference
- `tests/workspace_helpers.py` -- test workspace setup helpers

# Acceptance criteria

- [ ] `pytest tests/test_executor.py` passes
- [ ] `pytest tests/test_executor_builtin.py` passes
- [ ] Model fallback tests cover edge cases (all null, partial, full)
- [ ] Batch tests verify ordering and stop-on-failure
- [ ] Full test suite `pytest` passes
