---
id: "TASK-065"
type: "task"
plan: "PLAN-012"
chunk: "CHUNK-017"
project: ""
title: "Update run record and status management for ExecutorResult"
status: "completed"
description: "Ensure run records, ongoing.json, and status transitions work correctly with the new ExecutorResult-based flow."
human: false
model: "composer-2"
effort: "medium"
depends_on:
- "TASK-063"
files:
- "src/onward/execution.py"
acceptance:
- "Run records populated from ExecutorResult fields"
- "ongoing.json updated correctly during batch execution"
- "Run log written from ExecutorResult.output"
- "success_ack and task_result fields populated from ExecutorResult.ack"
created_at: "2026-03-20T21:51:37Z"
updated_at: "2026-03-20T22:53:00Z"
run_count: 1
last_run_status: "completed"
---

# Context

After TASK-063 changes the execution path, this task ensures all the bookkeeping (run records, ongoing.json, logs) works correctly with ExecutorResult as the data source instead of raw subprocess output.

# Scope

- Verify and fix run record creation:
  - `status`, `finished_at`, `error` from ExecutorResult
  - `model` from TaskContext.model (uses tier resolution)
  - `success_ack`, `task_result` from ExecutorResult.ack
- Verify ongoing.json management:
  - Add active run before executor call
  - Remove after ExecutorResult received
  - Works correctly during batch (multiple sequential adds/removes)
- Verify run log writing:
  - Log sections: hook output + ExecutorResult.output + ExecutorResult.error
  - Same log format as today
- Add/update tests for run record contents

# Out of scope

- Changing run record schema
- Adding new fields to run records

# Files to inspect

- `src/onward/execution.py` -- run record creation, ongoing.json management

# Implementation notes

- The run record `model` field should now reflect the tier-resolved model, not just what was in task metadata
- The `executor` field in run records should indicate which executor was used ("builtin" or the command name)

# Acceptance criteria

- [ ] Run record JSON contains correct model (tier-resolved)
- [ ] Run record `executor` field shows "builtin" or external command name
- [ ] ongoing.json shows active run during execution, cleared after
- [ ] Run log format matches existing format
- [ ] `test_run_record_io.py` passes
