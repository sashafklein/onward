---
id: "TASK-094"
type: "task"
plan: "PLAN-015"
chunk: "CHUNK-028"
project: ""
title: "Add verbose run stats to onward report --verbose"
status: "open"
description: ""
human: false
model: "sonnet-latest"
executor: "onward-exec"
depends_on: ["TASK-085", "TASK-092"]
files: []
acceptance: []
created_at: "2026-03-21T03:40:00Z"
updated_at: "2026-03-21T03:40:00Z"
---

# Context

`onward report --verbose` currently shows extra task detail. This task adds a
`[Run stats]` section at the bottom aggregating all runs for the current plan's tasks.

# Scope

- In `cmd_report`, when `--verbose` is passed:
  - Collect all run records for every task in the plan
  - Compute: total runs, completed count, failed count, pass rate, total input tokens, total output tokens
  - Print a stats block:
    ```
    [Run stats]
      Total runs: 14 (12 completed, 2 failed)
      Total tokens: 45.2k input / 123.4k output
      Pass rate: 85.7%
    ```
- Skip token totals if no runs have token data (print `tokens: n/a`)

# Out of scope

- Per-task breakdown in report (that's `onward show --runs`)
- Dollar cost estimation

# Files to inspect

- `src/onward/cli_commands.py` — `cmd_report` and its `--verbose` branch
- `src/onward/execution.py` — `collect_runs_for_target`

# Implementation notes

- Must iterate over all task IDs in the active plan; may need to load from `index.yaml`
- Token aggregation: skip `None` entries, sum only where data exists
- Pass rate: `completed / total * 100` — show `n/a` if zero runs

# Acceptance criteria

- [ ] `onward report --verbose` shows a `[Run stats]` section at the bottom
- [ ] Token totals shown when available, `n/a` when no token data exists
- [ ] Pass rate shown as percentage
- [ ] No crash when there are zero runs

# Handoff notes

Minor UX polish — the stats section should be visually distinct (e.g., separated by a blank line).
