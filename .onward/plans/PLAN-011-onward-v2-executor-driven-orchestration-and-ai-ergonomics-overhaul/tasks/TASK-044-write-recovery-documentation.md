---
id: "TASK-044"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-011"
project: ""
title: "Write recovery documentation"
status: "open"
description: ""
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T16:01:07Z"
updated_at: "2026-03-20T16:01:07Z"
---

# Context

When AI-driven execution fails, agents (and humans) need clear recovery instructions. This task creates `docs/RECOVERY.md` — a practical guide for diagnosing and recovering from execution failures. It covers reading run logs, common failure modes, retry strategies, and manual intervention patterns. This is a documentation-only task.

# Scope

- Create `docs/RECOVERY.md` with these sections:
  - **Reading run logs**: how to find log paths via `onward show TASK-X`, what the log sections mean
  - **Common failure modes**: executor not found, preflight failures, timeout, AI model errors, acceptance ack missing, hook failures
  - **Recovery actions**:
    - Retry: `onward retry TASK-X` then `onward work TASK-X` (requires TASK-034's `failed` status)
    - Skip: `onward cancel TASK-X` and create follow-up task
    - Intervene: edit task body, adjust acceptance criteria, re-run
    - Reset chunk: cancel failed tasks, create replacements
  - **Circuit breaker**: what it means, how to reset (requires TASK-035)
  - **Hook failures**: pre/post hook debugging
  - **Escalation**: when to involve a human (`human: true` tasks)
- Add a reference to `docs/RECOVERY.md` from `AGENTS.md` (in the "Related docs" or similar section)
- Add a reference from `docs/LIFECYCLE.md`

# Out of scope

- Implementing any recovery commands (this is docs only)
- Changing error messages in the CLI to reference RECOVERY.md
- Writing troubleshooting for executor-specific issues (Cursor, Claude CLI, etc.)

# Files to inspect

- `docs/RECOVERY.md` — new file to create
- `AGENTS.md` — add reference
- `docs/LIFECYCLE.md` — add reference in related docs section
- `docs/AI_OPERATOR.md` — may want a cross-reference
- `src/onward/execution.py` — reference for understanding the execution flow, error points, log structure

# Implementation notes

- Write for the audience of an AI agent that just had a task fail. The agent needs to know: what happened, where to look, and what to do next.
- Reference concrete CLI commands (not abstractions). Show exact command sequences for each recovery path.
- The log file structure in `.onward/runs/RUN-*.log` has sections: `$ command`, `[pre_task_shell]`, `[task stdout]`, `[task stderr]`, `[post_task_shell]`, `[error]`. Document what each section contains.
- The run record JSON in `.onward/runs/RUN-*.json` has: `id`, `target`, `status`, `model`, `started_at`, `finished_at`, `error`, `log_path`, optionally `success_ack` and `task_result`.
- Include a quick-reference table at the top: symptom → action.
- Keep the doc under 200 lines — concise and scannable, not exhaustive.
- Note: TASK-034 (`failed` status) and TASK-035 (circuit breaker) may not have landed yet when this task runs. Write the doc assuming they will exist, and note "requires TASK-034" inline where relevant. The doc should be accurate regardless of execution order.

# Acceptance criteria

- `docs/RECOVERY.md` exists with all specified sections
- Quick-reference symptom → action table at the top
- Concrete CLI command sequences for each recovery path
- Run log structure documented
- Run record JSON structure documented
- Referenced from `AGENTS.md` and `docs/LIFECYCLE.md`
- Doc is under 200 lines, concise and scannable

# Handoff notes

- This task is independent of the code tasks in CHUNK-011 and can land in any order.
- After TASK-034 (failed status) and TASK-035 (circuit breaker) land, verify the recovery doc accurately describes their behavior. Create a follow-up to update if needed.
- Consider: should `onward work` error messages include a "see docs/RECOVERY.md" hint? That would be a separate task.
