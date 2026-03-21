---
id: "CHUNK-019"
type: "chunk"
plan: "PLAN-013"
project: ""
title: "Claiming infrastructure and ongoing.json extension"
status: "completed"
description: "Extend ongoing.json schema with scope, claimed_children, and pid fields. Implement claimed_task_ids() helper in execution.py that loads ongoing.json, checks PID liveness, prunes stale entries, and returns the set of currently claimed task IDs. Wire claim registration and release into _work_chunk and _work_plan so that tasks owned by a running chunk/plan execution are registered before the task loop and released on exit."
priority: "high"
model: "sonnet-latest"
depends_on: []
created_at: "2026-03-21T01:59:37Z"
updated_at: "2026-03-21T03:17:32Z"
---

# Summary

Extend ongoing.json schema with scope, claimed_children, and pid fields. Implement claimed_task_ids() helper in execution.py that loads ongoing.json, checks PID liveness, prunes stale entries, and returns the set of currently claimed task IDs. Wire claim registration and release into _work_chunk and _work_plan so that tasks owned by a running chunk/plan execution are registered before the task loop and released on exit.

# Scope

- Extend ongoing.json schema with scope, claimed_children, and pid fields. Implement claimed_task_ids() helper in execution.py that loads ongoing.json, checks PID liveness, prunes stale entries, and returns the set of currently claimed task IDs. Wire claim registration and release into _work_chunk and _work_plan so that tasks owned by a running chunk/plan execution are registered before the task loop and released on exit.

# Out of scope

- None specified.

# Dependencies

- None specified.

# Expected files/systems involved

**Must touch:**
- `src/onward/execution.py`

**Likely:**
- `src/onward/cli_commands.py`

# Completion criteria

- work_chunk registers a claim entry in ongoing.json before the task loop
- work_plan registers chunk claims as each chunk enters execution
- Claims include scope, claimed_children, pid, status, and started_at
- Claims are released on success, failure, or exception via try/finally
- claimed_task_ids() returns correct task IDs from active ongoing.json entries
- claimed_task_ids() prunes entries whose PID is no longer alive

# Notes
