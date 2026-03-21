---
id: "TASK-070"
type: "task"
plan: "PLAN-013"
chunk: "CHUNK-019"
project: ""
title: "Wire claim registration into work_chunk and _work_plan"
status: "completed"
description: "In src/onward/execution.py, update work_chunk to register a claim (via _register_claim) before the task loop begins, listing all open child task IDs as claimed_children with scope=\"chunk\" and pid=os.getpid(). Use try/finally to ensure _release_claim runs on success, failure, or exception. In src/onward/cli_commands.py, update _work_plan (or the plan-level work function) to register each chunk claim as it enters execution, releasing on chunk completion or failure. Collect open tasks for each chunk at claim time."
human: false
model: "sonnet-latest"
executor: "onward-exec"
depends_on:
- "TASK-069"
files:
- "src/onward/execution.py"
- "src/onward/cli_commands.py"
acceptance:
- "work_chunk registers a claim entry in ongoing.json before the task loop"
- "work_chunk releases the claim on normal completion"
- "work_chunk releases the claim on task failure or exception (try/finally)"
- "_work_plan registers chunk claims as each chunk enters execution"
- "_work_plan releases chunk claims as each chunk finishes"
created_at: "2026-03-21T02:09:56Z"
updated_at: "2026-03-21T03:17:31Z"
effort: "m"
---

# Context

In src/onward/execution.py, update work_chunk to register a claim (via _register_claim) before the task loop begins, listing all open child task IDs as claimed_children with scope="chunk" and pid=os.getpid(). Use try/finally to ensure _release_claim runs on success, failure, or exception. In src/onward/cli_commands.py, update _work_plan (or the plan-level work function) to register each chunk claim as it enters execution, releasing on chunk completion or failure. Collect open tasks for each chunk at claim time.

# Scope

- In src/onward/execution.py, update work_chunk to register a claim (via _register_claim) before the task loop begins, listing all open child task IDs as claimed_children with scope="chunk" and pid=os.getpid(). Use try/finally to ensure _release_claim runs on success, failure, or exception. In src/onward/cli_commands.py, update _work_plan (or the plan-level work function) to register each chunk claim as it enters execution, releasing on chunk completion or failure. Collect open tasks for each chunk at claim time.

# Out of scope

- None specified.

# Files to inspect

- `src/onward/execution.py`
- `src/onward/cli_commands.py`

# Implementation notes

- Keep the change scoped to this task.

# Acceptance criteria

- work_chunk registers a claim entry in ongoing.json before the task loop
- work_chunk releases the claim on normal completion
- work_chunk releases the claim on task failure or exception (try/finally)
- _work_plan registers chunk claims as each chunk enters execution
- _work_plan releases chunk claims as each chunk finishes

# Handoff notes
