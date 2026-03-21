---
id: "TASK-073"
type: "task"
plan: "PLAN-013"
chunk: "CHUNK-021"
project: ""
title: "Add PID liveness check and claim_timeout_minutes config"
status: "completed"
description: "In src/onward/execution.py, enhance claimed_task_ids() to perform PID liveness checks via os.kill(pid, 0) on Unix. Dead-PID entries should be pruned from ongoing.json on read (write back the cleaned data). In src/onward/config.py, add a work.claim_timeout_minutes setting (default 120) that expires claims older than the threshold regardless of PID. When claim_timeout_minutes is 0, disable claiming entirely (claimed_task_ids returns empty set)."
human: false
model: "sonnet-latest"
executor: "onward-exec"
depends_on: []
files:
- "src/onward/execution.py"
- "src/onward/config.py"
acceptance:
- "claimed_task_ids prunes entries whose PID is no longer alive"
- "Pruned entries are removed from ongoing.json on disk"
- "work.claim_timeout_minutes defaults to 120 in config"
- "Claims older than claim_timeout_minutes are expired regardless of PID"
- "work.claim_timeout_minutes: 0 disables claiming (returns empty set)"
created_at: "2026-03-21T02:11:44Z"
updated_at: "2026-03-21T03:17:34Z"
effort: "m"
---

# Context

In src/onward/execution.py, enhance claimed_task_ids() to perform PID liveness checks via os.kill(pid, 0) on Unix. Dead-PID entries should be pruned from ongoing.json on read (write back the cleaned data). In src/onward/config.py, add a work.claim_timeout_minutes setting (default 120) that expires claims older than the threshold regardless of PID. When claim_timeout_minutes is 0, disable claiming entirely (claimed_task_ids returns empty set).

# Scope

- In src/onward/execution.py, enhance claimed_task_ids() to perform PID liveness checks via os.kill(pid, 0) on Unix. Dead-PID entries should be pruned from ongoing.json on read (write back the cleaned data). In src/onward/config.py, add a work.claim_timeout_minutes setting (default 120) that expires claims older than the threshold regardless of PID. When claim_timeout_minutes is 0, disable claiming entirely (claimed_task_ids returns empty set).

# Out of scope

- None specified.

# Files to inspect

- `src/onward/execution.py`
- `src/onward/config.py`

# Implementation notes

- Keep the change scoped to this task.

# Acceptance criteria

- claimed_task_ids prunes entries whose PID is no longer alive
- Pruned entries are removed from ongoing.json on disk
- work.claim_timeout_minutes defaults to 120 in config
- Claims older than claim_timeout_minutes are expired regardless of PID
- work.claim_timeout_minutes: 0 disables claiming (returns empty set)

# Handoff notes
