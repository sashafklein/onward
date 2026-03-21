---
id: "TASK-084"
type: "task"
plan: "PLAN-015"
chunk: "CHUNK-024"
project: ""
title: "Update _prepare_task_run to per-task directory layout"
status: "completed"
description: ""
human: false
model: "sonnet-latest"
executor: "onward-exec"
depends_on: []
files: []
acceptance: []
created_at: "2026-03-21T03:40:00Z"
updated_at: "2026-03-21T03:56:16Z"
---

# Context

`_prepare_task_run` in `execution.py` currently creates flat files:
`runs/RUN-<ts>-<task>.json` and `runs/RUN-<ts>-<task>.log`. This task
restructures it to create a per-task directory and three timestamped files
inside it.

# Scope

- Change path construction in `_prepare_task_run` to:
  ```
  task_dir = root / ".onward/runs" / task_id
  task_dir.mkdir(parents=True, exist_ok=True)
  run_json  = task_dir / f"info-{ts}.json"
  run_log   = task_dir / f"summary-{ts}.log"
  output_log = task_dir / f"output-{ts}.log"
  ```
- Add `output_log: Path` field to `PreparedTaskRun` dataclass and populate it
- Keep `run_id` as `RUN-<ts>-<task-id>` (stored in the JSON, not the filename)

# Out of scope

- Writing anything to `output_log` (TASK-086)
- Backward-compatible readers (TASK-085)

# Files to inspect

- `src/onward/execution.py` — search for `_prepare_task_run` and `PreparedTaskRun`

# Implementation notes

- `task_dir.mkdir(parents=True, exist_ok=True)` handles first-run creation
- The `output_log` path is returned in `PreparedTaskRun` but may not exist yet on disk at prepare time; callers create it when they start writing
- Timestamp format: `run_timestamp()` already produces `YYYY-MM-DDTHH-MM-SSZ`; reuse it

# Acceptance criteria

- [ ] `_prepare_task_run` produces paths under `.onward/runs/TASK-XXX/`
- [ ] `PreparedTaskRun` has an `output_log` field
- [ ] The logical `run_id` in the written JSON is still `RUN-<ts>-<task>`
- [ ] Existing tests that check run JSON path patterns are updated to match new paths

# Handoff notes

TASK-085 updates the readers; do this task first so the dataclass shape is stable.
