---
id: "TASK-075"
type: "task"
plan: "PLAN-013"
chunk: "CHUNK-021"
project: ""
title: "Integration tests for claim lifecycle"
status: "completed"
description: "Add integration tests in tests/ covering the end-to-end claim lifecycle: work_chunk registers and releases claims in ongoing.json; report and next exclude claimed tasks; a stale claim (simulated dead PID) is auto-cleaned on next report invocation. Use the existing test harness pattern with tmp workspace fixtures. Tests should exercise cmd_report and cmd_next through the function-level API, not subprocess calls."
human: false
model: "sonnet-latest"
executor: "onward-exec"
depends_on:
- "TASK-073"
- "TASK-074"
files:
- "tests/"
- "src/onward/execution.py"
- "src/onward/cli_commands.py"
acceptance:
- "Test: work_chunk registers claim entry before task loop"
- "Test: work_chunk releases claim on completion"
- "Test: report excludes claimed tasks from actionable sections"
- "Test: next skips claimed tasks"
- "Test: stale claim (dead PID) is cleaned on next report"
- "All existing tests continue to pass"
created_at: "2026-03-21T02:11:44Z"
updated_at: "2026-03-21T03:17:36Z"
effort: "m"
---

# Context

Add integration tests in tests/ covering the end-to-end claim lifecycle: work_chunk registers and releases claims in ongoing.json; report and next exclude claimed tasks; a stale claim (simulated dead PID) is auto-cleaned on next report invocation. Use the existing test harness pattern with tmp workspace fixtures. Tests should exercise cmd_report and cmd_next through the function-level API, not subprocess calls.

# Scope

- Add integration tests in tests/ covering the end-to-end claim lifecycle: work_chunk registers and releases claims in ongoing.json; report and next exclude claimed tasks; a stale claim (simulated dead PID) is auto-cleaned on next report invocation. Use the existing test harness pattern with tmp workspace fixtures. Tests should exercise cmd_report and cmd_next through the function-level API, not subprocess calls.

# Out of scope

- None specified.

# Files to inspect

- `tests/`
- `src/onward/execution.py`
- `src/onward/cli_commands.py`

# Implementation notes

- Keep the change scoped to this task.

# Acceptance criteria

- Test: work_chunk registers claim entry before task loop
- Test: work_chunk releases claim on completion
- Test: report excludes claimed tasks from actionable sections
- Test: next skips claimed tasks
- Test: stale claim (dead PID) is cleaned on next report
- All existing tests continue to pass

# Handoff notes
