---
id: "TASK-085"
type: "task"
plan: "PLAN-015"
chunk: "CHUNK-024"
project: ""
title: "Update run readers for backward compat with legacy flat files"
status: "open"
description: ""
human: false
model: "sonnet-latest"
executor: "onward-exec"
depends_on: ["TASK-084"]
files: []
acceptance: []
created_at: "2026-03-21T03:40:00Z"
updated_at: "2026-03-21T03:40:00Z"
---

# Context

After TASK-084 changes the write path, the read path (`collect_runs_for_target`,
`latest_run_for`, and any other run-scanning helpers) must find both new-style
`runs/TASK-XXX/info-*.json` and legacy `runs/RUN-*-TASK-XXX.json` files.

# Scope

- Update `collect_runs_for_target(task_id)` to glob both:
  - `runs/TASK-{task_id}/info-*.json` (new)
  - `runs/RUN-*-{task_id}.json` (legacy)
- Merge results and sort by `started_at` ascending
- Update `latest_run_for(task_id)` to use the updated `collect_runs_for_target`
- Ensure the `summary_log` path returned for legacy runs still points to the old `.log` sibling file

# Out of scope

- Migrating or deleting legacy files
- Reading `output-*.log` content (CHUNK-028)

# Files to inspect

- `src/onward/execution.py` — `collect_runs_for_target`, `latest_run_for`

# Implementation notes

- For legacy runs the summary log path is `runs/RUN-<ts>-<task>.log` (sibling of `.json`)
- For new runs the summary log path is `runs/TASK-XXX/summary-<ts>.log`
- Consider a small helper `_run_info_paths(root, task_id)` that yields all matching `info` JSON paths regardless of layout

# Acceptance criteria

- [ ] `collect_runs_for_target("TASK-060")` returns the existing legacy run records
- [ ] `collect_runs_for_target("TASK-084")` returns new-layout records after a run
- [ ] A task with both legacy and new runs gets all of them merged in `started_at` order
- [ ] `latest_run_for` returns the newest across both layouts

# Handoff notes

After this task, `onward show TASK-XXX` should still display legacy runs correctly.
