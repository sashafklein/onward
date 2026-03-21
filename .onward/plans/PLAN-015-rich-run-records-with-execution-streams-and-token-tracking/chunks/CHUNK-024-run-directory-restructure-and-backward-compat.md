---
id: "CHUNK-024"
type: "chunk"
plan: "PLAN-015"
project: ""
title: "Run directory restructure and backward compat"
status: "open"
description: ""
priority: "medium"
model: "sonnet-latest"
created_at: "2026-03-21T03:40:00Z"
updated_at: "2026-03-21T03:40:00Z"
---

# Summary

Changes the on-disk layout for run records from a flat `runs/RUN-<ts>-<task>.*` pair into per-task directories (`runs/TASK-XXX/info-<ts>.json`, `summary-<ts>.log`, `output-<ts>.log`). Backward compatibility with existing flat run files is preserved so `onward show` keeps working on old records.

# Scope

- Update `_prepare_task_run` in `execution.py` to produce per-task directory paths for `run_json`, `run_log`, and a new `output_log`
- Add `output_log: Path` field to the `PreparedTaskRun` dataclass
- Update `collect_runs_for_target` and `latest_run_for` to scan both new (`runs/TASK-*/info-*.json`) and legacy (`runs/RUN-*-<task>.json`) paths, merge, and sort by `started_at`
- Keep `run_id` format as `RUN-<timestamp>-<task-id>` (logical ID unchanged)

# Out of scope

- Writing anything to `output-*.log` during execution (CHUNK-025)
- Token fields in `info-*.json` (CHUNK-027)
- CLI display changes (CHUNK-028)

# Dependencies

None — this is the foundation all other chunks build on.

# Expected files/systems involved

- `src/onward/execution.py` — `_prepare_task_run`, `PreparedTaskRun`, `collect_runs_for_target`, `latest_run_for`

# Completion criteria

- [ ] New task run creates `runs/TASK-XXX/info-<ts>.json` and `summary-<ts>.log` (not flat `RUN-*.json`/`.log`)
- [ ] `PreparedTaskRun` exposes an `output_log: Path` field pointing to `runs/TASK-XXX/output-<ts>.log`
- [ ] `collect_runs_for_target("TASK-XXX")` returns both new and legacy runs merged by timestamp
- [ ] Existing `RUN-*.json` / `RUN-*.log` files in `.onward/runs/` are untouched

# Notes

The `output_log` path is created by `_prepare_task_run` but left empty until CHUNK-025 wires streaming into it.
