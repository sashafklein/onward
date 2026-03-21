---
id: "TASK-034"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-009"
project: ""
title: "Add failed status and retry command"
status: "completed"
description: ""
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T16:01:02Z"
updated_at: "2026-03-20T17:54:03Z"
---

# Context

CHUNK-009 cleans up the Onward status model. Currently, when `onward work` fails, the task reverts to `open` — indistinguishable from a never-attempted task. This task adds a `failed` status so failed tasks are visible in reports and excluded from `onward next`, and adds `onward retry TASK-X` to explicitly reset a failed task for re-execution. It also tracks `run_count` and `last_run_status` in task frontmatter for visibility.

# Scope

- Add `"failed"` to the valid status set in `validate_artifact()` in `artifacts.py`
- Add `"failed"` to `_status_color` in `util.py` — use `"red"`
- Change `work_task()` in `execution.py`: on failure, set status to `"failed"` instead of `"open"`
- Verify `task_is_next_actionable()` excludes `"failed"` (it only allows `open`/`in_progress`; confirm and add comment)
- Add `retry` subcommand to `build_parser()` in `cli.py`: takes artifact ID and `--root`
- Add `cmd_retry` handler in `cli_commands.py`: validates task is `failed`, resets to `open`, resets `run_count` to 0
- Add `"retry"` action to `transition_status()`: `{"failed": "open"}`
- Add `retry` case to `_lifecycle_transition_error()`
- Track `run_count` (int, default 0) and `last_run_status` (string) in task metadata, updated by `_execute_task_run()`
- Update `LIFECYCLE.md`: add `failed` to status vocabulary table, document `retry` command
- Add `"failed"` to `active_task_status` in `render_active_work_tree_lines()` so failed tasks appear in the tree
- Add/update tests for failed status, retry command, run_count tracking

# Out of scope

- Circuit breaker / max retries logic (TASK-035)
- Changing chunk-level failure behavior
- Removing `onward start` (TASK-036)
- Modifying the `canceled` status semantics

# Files to inspect

- `src/onward/artifacts.py` — `validate_artifact`, `task_is_next_actionable`, `transition_status`, `_lifecycle_transition_error`, `render_active_work_tree_lines`
- `src/onward/execution.py` — `work_task` (line ~374, the `update_artifact_status` call on failure), `_execute_task_run`
- `src/onward/cli.py` — `build_parser()` to add `retry` subcommand
- `src/onward/cli_commands.py` — add `cmd_retry` handler, update import in `cli.py`
- `src/onward/util.py` — `_status_color` dict
- `docs/LIFECYCLE.md` — status vocabulary table, manual commands table, quick reference
- `tests/test_cli_work.py` — existing work failure tests to update

# Implementation notes

- The `failed` status is NOT terminal like `completed`/`canceled` — `retry` can move it back to `open`. But `failed` tasks must not be picked by `onward next` or `select_next_artifact`.
- `run_count` should be initialized to 0. Increment it in `_execute_task_run()` right before starting the run (so both successful and failed runs count).
- `last_run_status` stores `"completed"` or `"failed"` — set it alongside the status update at the end of `work_task()`.
- `cmd_retry` should use `_cmd_set_status(args, "retry")` to reuse the existing pattern, but also reset `run_count = 0` on the artifact before writing. This means `cmd_retry` needs its own handler (not just `_cmd_set_status`).
- In `render_active_work_tree_lines`, add `"failed"` to `active_task_status` so it shows in the tree — failed tasks are active work needing attention.
- The `ordered_ready_chunk_tasks` in `execution.py` already filters to `open`/`in_progress` — `failed` tasks are automatically excluded from chunk execution.

# Acceptance criteria

- `onward doctor` accepts `failed` as a valid status
- `onward work TASK-X` sets status to `failed` on executor failure (not `open`)
- `onward retry TASK-X` resets a `failed` task to `open` with `run_count` = 0
- `onward retry TASK-X` errors when task is not in `failed` status
- `onward next` does not suggest `failed` tasks
- `run_count` increments on each work run (success or failure)
- `last_run_status` is set after each run
- `onward tree` shows `failed` tasks in red
- `docs/LIFECYCLE.md` documents the `failed` status and `retry` command
- All existing tests still pass; new tests cover failed transition, retry, run_count

# Handoff notes

- TASK-035 (circuit breaker) builds directly on `run_count` and `failed` status from this task — it must land after this.
- The `_lifecycle_transition_error` function in `artifacts.py` needs a `retry` action branch for good error messages.
- Consider: should `finalize_chunks_all_tasks_terminal` treat `failed` as terminal? Probably not — a chunk with failed tasks is not done. Verify behavior.
