---
id: "TASK-093"
type: "task"
plan: "PLAN-015"
chunk: "CHUNK-028"
project: ""
title: "Implement onward show --runs run history table"
status: "completed"
description: ""
human: false
model: "sonnet-latest"
executor: "onward-exec"
depends_on:
- "TASK-085"
- "TASK-092"
files: []
acceptance: []
created_at: "2026-03-21T03:40:00Z"
updated_at: "2026-03-21T03:56:25Z"
---

# Context

With run records now containing `files_changed` and `token_usage`, `onward show`
can display a meaningful run history. This task implements the `--runs` display
(or extends existing run history output if the flag already exists).

# Scope

- In `cmd_show` (`cli_commands.py`), when `--runs` is passed for a task ID:
  - Call `collect_runs_for_target(task_id)` to get all runs
  - For each run, print: run number, timestamp, status, duration (from `started_at`/`finished_at`), model, token counts (or `-`), file count
- Format example:
  ```
  Runs for TASK-020 (2 runs):
    #1  2026-03-21T00:30:00Z  completed  2m13s  composer-2  1.2k/4.5k tokens  3 files
    #2  2026-03-21T01:15:00Z  failed     0m45s  composer-2  0.8k/1.2k tokens  0 files
  ```
- Handle missing fields gracefully (use `-` for nulls)

# Out of scope

- `onward report --verbose` stats (TASK-094)

# Files to inspect

- `src/onward/cli_commands.py` — `cmd_show` and its arg parsing
- `src/onward/execution.py` — `collect_runs_for_target` return shape

# Implementation notes

- Duration: `finished_at - started_at`; display as `Xm Ys`
- Token display: `f"{input//1000:.1f}k/{output//1000:.1f}k"` or `-` if null
- File count: `len(files_changed)` or `0`

# Acceptance criteria

- [ ] `onward show TASK-XXX --runs` prints a table of all runs (new and legacy)
- [ ] Token and file columns show `-` when data is absent
- [ ] Output is readable without wrapping in an 80-column terminal
- [ ] Works for tasks with zero runs (prints "No runs yet")

# Handoff notes

After this, `onward show` is the primary introspection surface for run history.
