---
id: "TASK-042"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-011"
project: ""
title: "Auto-create follow-up tasks from executor results"
status: "completed"
description: ""
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on:
  - "TASK-041"
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T16:01:06Z"
updated_at: "2026-03-20T18:22:59Z"
---

# Context

After TASK-041 implements the structured task result schema with `follow_ups`, this task makes Onward automatically create new tasks from those follow-ups. When an executor completes a task and reports follow-up work, Onward should create those as new tasks in the same chunk, with `depends_on` pointing to the completed task. This closes the feedback loop: the AI discovers work during execution, and it's automatically captured in the planning system.

# Scope

- Add `create_follow_up_tasks(root, task, follow_ups)` function in `artifacts.py` (or a new `feedback.py` module)
- Each follow-up becomes a new task in the same chunk as the completed task:
  - `title` from follow-up
  - `description` from follow-up
  - `depends_on: [completed_task_id]`
  - `model` defaults to `task_default` from config
  - `priority` from follow-up (default "medium")
  - `status: "open"`
- Call `create_follow_up_tasks` from `work_task()` in `execution.py` after a successful run that has `follow_ups` in the task result
- Print created follow-up task IDs to stdout
- Regenerate indexes after creating follow-ups
- Add `--no-follow-ups` flag to `onward work` to suppress auto-creation (opt-out)
- Add tests for follow-up creation, empty follow-ups, and opt-out flag

# Out of scope

- Creating follow-ups from failed runs (only successful runs)
- Cross-chunk follow-ups (follow-ups go in the same chunk)
- Modifying existing follow-up tasks if re-run creates duplicates
- Interactive confirmation before creating follow-ups

# Files to inspect

- `src/onward/artifacts.py` — `next_id`, `find_plan_dir`, `format_artifact`, `write_artifact`, `regenerate_indexes` for the creation pattern
- `src/onward/execution.py` — `work_task()` (line ~348) for the integration point after successful run
- `src/onward/cli.py` — `work_parser` to add `--no-follow-ups` flag
- `src/onward/cli_commands.py` — `cmd_work()` to pass the flag through
- `src/onward/executor_ack.py` — `parse_task_result` (from TASK-041) for accessing follow-ups
- `src/onward/config.py` — `model_setting` for `task_default`

# Implementation notes

- The creation pattern follows `cmd_new_task` in `cli_commands.py` — build metadata dict, format artifact, write file, regenerate indexes.
- Follow-up tasks should be created with:
  - `plan`: same as parent task
  - `chunk`: same as parent task
  - `project`: same as parent task
  - `executor`: same as parent task (default "ralph")
  - `human`: false (AI-discovered work is AI-executable)
- Deduplication: if a follow-up title matches an existing open task in the same chunk, skip it and print a warning. This prevents re-runs from creating duplicates.
- The `--no-follow-ups` flag should be on the `work` subparser and passed through via `args`. In `cmd_work`, check the flag before calling `create_follow_up_tasks`.
- Keep the follow-up creation outside the core `work_task` function — do it in `cmd_work` after `work_task` returns. This keeps `work_task` focused on execution and makes the opt-out easier to implement.
- Index regeneration: call once after all follow-ups are created (batch), not per follow-up.

# Acceptance criteria

- Successful `onward work TASK-X` with `follow_ups` in result creates new tasks in the same chunk
- Created tasks have `depends_on: [TASK-X]`, correct plan/chunk/project
- Created task IDs are printed to stdout
- `onward work --no-follow-ups TASK-X` suppresses follow-up creation
- Duplicate follow-up titles are skipped with a warning
- Empty `follow_ups` list creates no tasks (no error)
- Tests cover: creation, deduplication, opt-out, empty list

# Handoff notes

- This interacts with TASK-035 (circuit breaker) if follow-ups themselves fail — they'll go through the same circuit breaker logic.
- Follow-ups are always created as `open` tasks, so they're immediately eligible for `onward next`.
- In chunk mode (`onward work CHUNK-X`), follow-ups created during execution become eligible for the next iteration of the chunk work loop. This is correct behavior — the chunk loop re-checks ready tasks after each execution.
