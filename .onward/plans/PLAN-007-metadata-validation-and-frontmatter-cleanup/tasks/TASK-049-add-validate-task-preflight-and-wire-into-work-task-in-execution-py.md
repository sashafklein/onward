---
id: "TASK-049"
type: "task"
plan: "PLAN-007"
chunk: "CHUNK-015"
project: ""
title: "Add validate_task_preflight() and wire into work_task() in execution.py"
status: "completed"
description: "In `src/onward/execution.py`:\n\n1. Add a new function `validate_task_preflight(task: Artifact) -> list[str]` that:\n   - Calls `validate_artifact(task)` from `onward.artifacts`\n   - Filters or returns all issues that represent blocking problems (bad field values: invalid complexity/effort, invalid model, invalid human, etc.)\n   - Unknown field warnings and missing optional fields should also be surfaced\n   - Returns the list of issue strings (empty list = clean)\n\n2. In `work_task()`, call `validate_task_preflight(fresh)` **after** re-reading the fresh artifact but **before** the `update_artifact_status(layout, fresh, 'in_progress', project)` call.\n   - If `validate_task_preflight` returns any issues, raise `ValueError` with a clear message listing all issues (e.g. `\"task metadata validation failed:\\n  - {issue1}\\n  - {issue2}\"`)\n   - The task must remain in its current status (`open`) — do NOT call `update_artifact_status` before raising\n\n3. Export `validate_task_preflight` if it needs to be accessible from tests (make it a module-level function, not prefixed with `_`)."
human: false
model: "sonnet"
executor: "onward-exec"
depends_on:
- "TASK-048"
files:
- "src/onward/execution.py"
acceptance:
- "Calling work_task on a task whose frontmatter has `complexity: banana` raises ValueError with a message mentioning the bad value"
- "The task's status remains `open` after the failed preflight (not `in_progress`)"
- "Calling work_task on a task whose frontmatter has `model: nonexistent-model-xyz` raises ValueError"
- "A well-formed task passes preflight and proceeds to execution normally"
- "All existing work_task tests continue to pass"
created_at: "2026-03-21T20:20:59Z"
updated_at: "2026-03-21T20:37:24Z"
effort: "s"
run_count: 1
last_run_status: "completed"
---

# Context

In `src/onward/execution.py`:

1. Add a new function `validate_task_preflight(task: Artifact) -> list[str]` that:
   - Calls `validate_artifact(task)` from `onward.artifacts`
   - Filters or returns all issues that represent blocking problems (bad field values: invalid complexity/effort, invalid model, invalid human, etc.)
   - Unknown field warnings and missing optional fields should also be surfaced
   - Returns the list of issue strings (empty list = clean)

2. In `work_task()`, call `validate_task_preflight(fresh)` **after** re-reading the fresh artifact but **before** the `update_artifact_status(layout, fresh, 'in_progress', project)` call.
   - If `validate_task_preflight` returns any issues, raise `ValueError` with a clear message listing all issues (e.g. `"task metadata validation failed:\n  - {issue1}\n  - {issue2}"`)
   - The task must remain in its current status (`open`) — do NOT call `update_artifact_status` before raising

3. Export `validate_task_preflight` if it needs to be accessible from tests (make it a module-level function, not prefixed with `_`).

# Scope

- In `src/onward/execution.py`:

1. Add a new function `validate_task_preflight(task: Artifact) -> list[str]` that:
   - Calls `validate_artifact(task)` from `onward.artifacts`
   - Filters or returns all issues that represent blocking problems (bad field values: invalid complexity/effort, invalid model, invalid human, etc.)
   - Unknown field warnings and missing optional fields should also be surfaced
   - Returns the list of issue strings (empty list = clean)

2. In `work_task()`, call `validate_task_preflight(fresh)` **after** re-reading the fresh artifact but **before** the `update_artifact_status(layout, fresh, 'in_progress', project)` call.
   - If `validate_task_preflight` returns any issues, raise `ValueError` with a clear message listing all issues (e.g. `"task metadata validation failed:\n  - {issue1}\n  - {issue2}"`)
   - The task must remain in its current status (`open`) — do NOT call `update_artifact_status` before raising

3. Export `validate_task_preflight` if it needs to be accessible from tests (make it a module-level function, not prefixed with `_`).

# Out of scope

- None specified.

# Files to inspect

- `src/onward/execution.py`

# Implementation notes

- Keep the change scoped to this task.

# Acceptance criteria

- Calling work_task on a task whose frontmatter has `complexity: banana` raises ValueError with a message mentioning the bad value
- The task's status remains `open` after the failed preflight (not `in_progress`)
- Calling work_task on a task whose frontmatter has `model: nonexistent-model-xyz` raises ValueError
- A well-formed task passes preflight and proceeds to execution normally
- All existing work_task tests continue to pass

# Handoff notes
