---
id: "TASK-043"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-011"
project: ""
title: "Enhance onward show with run history and results"
status: "open"
description: ""
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: ["TASK-041"]
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T16:01:06Z"
updated_at: "2026-03-20T16:01:06Z"
---

# Context

Currently `onward show TASK-X` displays the latest run's basic info (id, status, started_at, finished_at, log path, error). After TASK-041 adds structured task results, `show` should display richer information: full run history, structured results from the last successful run, retry count, and dependency graph (what this task blocks and is blocked by).

# Scope

- Enhance `cmd_show` in `cli_commands.py` to display:
  - **Run history**: all runs for this task (not just latest), with status, timestamps, and run IDs
  - **Structured result** from last successful run: summary, files_changed, acceptance_met/unmet
  - **Retry info**: `run_count` and `last_run_status` from task metadata (added by TASK-034)
  - **Dependency graph**: tasks this one depends on (with their status), tasks that depend on this one
- Add `collect_runs_for_target(root, target_id)` in `execution.py` that returns all run records for a given task (not just the latest)
- Add `find_dependents(artifacts, task_id)` in `artifacts.py` that finds tasks whose `depends_on` includes this task
- Format the output clearly with section headers

# Out of scope

- Changing `onward show` for plan/chunk artifacts (only task enhancement)
- Adding a `--json` output mode for `onward show`
- Showing run log content inline (too verbose; show log path instead)
- Modifying run record storage format

# Files to inspect

- `src/onward/cli_commands.py` — `cmd_show()` (lines ~355-384) for current implementation
- `src/onward/execution.py` — `latest_run_for()` (line ~509), `collect_run_records()` for the pattern
- `src/onward/artifacts.py` — `collect_artifacts()`, dependency-related functions
- `src/onward/executor_ack.py` — `parse_task_result` (from TASK-041)

# Implementation notes

- `collect_runs_for_target(root, target_id)` should glob `RUN-*-{target_id}.json` and return all records sorted by `started_at` descending.
- For the dependency graph display: iterate all artifacts, find those whose `depends_on` (or `blocked_by` for compat) includes this task's ID. Show each with its current status.
- For the structured result display: find the latest run with status "completed" and a non-null `task_result` key. Display `summary`, `files_changed` (as bullet list), `acceptance_met`/`acceptance_unmet`.
- Keep the output text-based (not JSON). Use clear section headers like `Run history:`, `Last result:`, `Dependencies:`, `Blocked tasks:`.
- The run history should be limited to the last 10 runs by default. Don't add a flag for this — 10 is plenty for visibility.
- If `run_count` or `last_run_status` are in task metadata, show them in the header section.
- Consider coloring the run status (completed=green, failed=red) if terminal colors are available. Use `sys.stdout.isatty()` to decide.

# Acceptance criteria

- `onward show TASK-X` displays all runs (up to 10) with id, status, timestamps
- `onward show TASK-X` displays structured result from last successful run (summary, files_changed, acceptance status)
- `onward show TASK-X` displays run_count and last_run_status if present
- `onward show TASK-X` displays dependency graph (depends on + depended on by)
- Output is clearly sectioned and readable
- `onward show PLAN-X` and `onward show CHUNK-X` are unchanged
- Tests cover: task with multiple runs, task with structured result, task with no runs

# Handoff notes

- This is a read-only enhancement — no status changes or side effects.
- The `find_dependents` function is useful beyond `show` — it could be reused by `onward report` or `onward tree` in the future.
- If the structured result includes `follow_ups`, consider showing them too (with links to the created follow-up task IDs if available).
