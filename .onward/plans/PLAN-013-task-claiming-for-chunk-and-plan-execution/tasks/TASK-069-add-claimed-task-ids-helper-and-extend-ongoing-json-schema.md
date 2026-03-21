---
id: "TASK-069"
type: "task"
plan: "PLAN-013"
chunk: "CHUNK-019"
project: ""
title: "Add claimed_task_ids helper and extend ongoing.json schema"
status: "completed"
description: "In src/onward/execution.py, implement claimed_task_ids(root: Path) -> set[str] that loads ongoing.json, filters entries with scope in {\"chunk\", \"plan\"}, checks each PID via os.kill(pid, 0), prunes stale entries (removing dead-PID rows and writing back), and returns the union of all claimed_children sets. Also add a _register_claim(root, run_id, target, scope, claimed_children, pid) helper that appends a claim entry to ongoing.json, and a _release_claim(root, run_id) that removes it."
human: false
model: "sonnet-latest"
executor: "onward-exec"
depends_on: []
files:
- "src/onward/execution.py"
acceptance:
- "claimed_task_ids returns empty set when ongoing.json is empty or missing"
- "claimed_task_ids returns correct task IDs from entries with scope chunk/plan"
- "claimed_task_ids prunes entries whose PID is dead (os.kill check)"
- "_register_claim adds a claim entry with scope, claimed_children, pid, status, started_at"
- "_release_claim removes the matching entry from ongoing.json"
created_at: "2026-03-21T02:09:56Z"
updated_at: "2026-03-21T03:17:30Z"
effort: "m"
run_count: 0
last_run_status: "failed"
---

# Context

In src/onward/execution.py, implement claimed_task_ids(root: Path) -> set[str] that loads ongoing.json, filters entries with scope in {"chunk", "plan"}, checks each PID via os.kill(pid, 0), prunes stale entries (removing dead-PID rows and writing back), and returns the union of all claimed_children sets. Also add a _register_claim(root, run_id, target, scope, claimed_children, pid) helper that appends a claim entry to ongoing.json, and a _release_claim(root, run_id) that removes it.

# Scope

- In src/onward/execution.py, implement claimed_task_ids(root: Path) -> set[str] that loads ongoing.json, filters entries with scope in {"chunk", "plan"}, checks each PID via os.kill(pid, 0), prunes stale entries (removing dead-PID rows and writing back), and returns the union of all claimed_children sets. Also add a _register_claim(root, run_id, target, scope, claimed_children, pid) helper that appends a claim entry to ongoing.json, and a _release_claim(root, run_id) that removes it.

# Out of scope

- None specified.

# Files to inspect

- `src/onward/execution.py`

# Implementation notes

- Keep the change scoped to this task.

# Acceptance criteria

- claimed_task_ids returns empty set when ongoing.json is empty or missing
- claimed_task_ids returns correct task IDs from entries with scope chunk/plan
- claimed_task_ids prunes entries whose PID is dead (os.kill check)
- _register_claim adds a claim entry with scope, claimed_children, pid, status, started_at
- _release_claim removes the matching entry from ongoing.json

# Handoff notes
