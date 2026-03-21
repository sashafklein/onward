---
id: "CHUNK-021"
type: "chunk"
plan: "PLAN-013"
project: ""
title: "Stale claim cleanup, config, and tests"
status: "completed"
description: "Add PID liveness check (os.kill(pid, 0)) and configurable work.claim_timeout_minutes (default 120) to claimed_task_ids() for stale claim expiry. Add unit tests for claimed_task_ids (correct IDs, stale PID pruning, empty ongoing.json). Add integration tests for claim registration/release during work_chunk, report/next exclusion of claimed tasks, and stale claim auto-cleanup."
priority: "medium"
model: "sonnet-latest"
depends_on:
- "CHUNK-019"
- "CHUNK-020"
created_at: "2026-03-21T01:59:37Z"
updated_at: "2026-03-21T03:17:36Z"
---

# Summary

Add PID liveness check (os.kill(pid, 0)) and configurable work.claim_timeout_minutes (default 120) to claimed_task_ids() for stale claim expiry. Add unit tests for claimed_task_ids (correct IDs, stale PID pruning, empty ongoing.json). Add integration tests for claim registration/release during work_chunk, report/next exclusion of claimed tasks, and stale claim auto-cleanup.

# Scope

- Add PID liveness check (os.kill(pid, 0)) and configurable work.claim_timeout_minutes (default 120) to claimed_task_ids() for stale claim expiry. Add unit tests for claimed_task_ids (correct IDs, stale PID pruning, empty ongoing.json). Add integration tests for claim registration/release during work_chunk, report/next exclusion of claimed tasks, and stale claim auto-cleanup.

# Out of scope

- None specified.

# Dependencies

- CHUNK-019
- CHUNK-020

# Expected files/systems involved

**Must touch:**
- `src/onward/execution.py`
- `tests/`

**Likely:**
- `src/onward/config.py`
- `src/onward/cli_commands.py`

**Deferred / out of scope for this chunk:**
- `docs/`

# Completion criteria

- Dead PID entries are pruned from ongoing.json on read
- work.claim_timeout_minutes: 0 in config disables claiming
- Unit tests cover claimed_task_ids with active, stale, and empty entries
- Integration test: work_chunk registers and releases claims
- Integration test: report/next exclude claimed tasks
- Integration test: killing the work process releases the stale claim on next report
- All existing tests continue to pass

# Notes
