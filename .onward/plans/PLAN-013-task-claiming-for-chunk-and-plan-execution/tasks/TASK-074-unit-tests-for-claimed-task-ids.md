---
id: "TASK-074"
type: "task"
plan: "PLAN-013"
chunk: "CHUNK-021"
project: ""
title: "Unit tests for claimed_task_ids"
status: "completed"
description: "Add unit tests in tests/ covering claimed_task_ids: returns empty set when ongoing.json is missing or empty; returns correct task IDs from entries with scope chunk/plan; prunes entries with dead PIDs; respects claim_timeout_minutes expiry; returns empty set when claim_timeout_minutes is 0. Use tmp_path fixtures with synthetic ongoing.json files. Mock os.kill for PID liveness checks."
human: false
model: "sonnet-latest"
executor: "onward-exec"
depends_on:
- "TASK-073"
files:
- "tests/"
acceptance:
- "Test: empty/missing ongoing.json returns empty set"
- "Test: active entries return correct claimed task IDs"
- "Test: dead-PID entries are pruned and not returned"
- "Test: expired entries (beyond claim_timeout_minutes) are pruned"
- "Test: claim_timeout_minutes=0 returns empty set"
- "All existing tests continue to pass"
created_at: "2026-03-21T02:11:44Z"
updated_at: "2026-03-21T03:17:34Z"
effort: "m"
---

# Context

Add unit tests in tests/ covering claimed_task_ids: returns empty set when ongoing.json is missing or empty; returns correct task IDs from entries with scope chunk/plan; prunes entries with dead PIDs; respects claim_timeout_minutes expiry; returns empty set when claim_timeout_minutes is 0. Use tmp_path fixtures with synthetic ongoing.json files. Mock os.kill for PID liveness checks.

# Scope

- Add unit tests in tests/ covering claimed_task_ids: returns empty set when ongoing.json is missing or empty; returns correct task IDs from entries with scope chunk/plan; prunes entries with dead PIDs; respects claim_timeout_minutes expiry; returns empty set when claim_timeout_minutes is 0. Use tmp_path fixtures with synthetic ongoing.json files. Mock os.kill for PID liveness checks.

# Out of scope

- None specified.

# Files to inspect

- `tests/`

# Implementation notes

- Keep the change scoped to this task.

# Acceptance criteria

- Test: empty/missing ongoing.json returns empty set
- Test: active entries return correct claimed task IDs
- Test: dead-PID entries are pruned and not returned
- Test: expired entries (beyond claim_timeout_minutes) are pruned
- Test: claim_timeout_minutes=0 returns empty set
- All existing tests continue to pass

# Handoff notes
