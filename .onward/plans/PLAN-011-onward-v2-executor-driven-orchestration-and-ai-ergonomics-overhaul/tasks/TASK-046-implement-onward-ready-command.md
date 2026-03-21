---
id: "TASK-046"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-012"
project: ""
title: "Implement onward ready command"
status: "completed"
description: ""
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T16:01:08Z"
updated_at: "2026-03-20T20:10:48Z"
---

# Context

`onward next` returns a single artifact. There's no way to see all actionable work across plans and projects. `onward ready` fills this gap: it shows every task that could be started right now, grouped by plan and chunk, optionally filtered by project. This is the "what can I work on?" command for agents and humans.

# Scope

- Add `ready` subcommand to `build_parser()` in `cli.py` with `--root`, `--project`, `--no-color` flags
- Add `cmd_ready` handler in `cli_commands.py`
- `cmd_ready` collects all artifacts, finds all tasks where `task_is_next_actionable()` is true
- Group results by plan → chunk hierarchy
- Display format:
  ```
  PLAN-011 Onward v2: executor-driven orchestration
    CHUNK-009 [open] Status model cleanup
      TASK-034 (A) Add failed status and retry command
      TASK-036 (A) Remove onward start command
    CHUNK-010 [open] Intelligent split
      TASK-038 (A) Wire split to executor
  ```
- Include effort estimate if `effort` metadata exists (from TASK-047, optional)
- Respect `--project` filter
- Run `finalize_chunks_all_tasks_terminal` before displaying (same as `onward next`)
- Add tests

# Out of scope

- Sorting by effort/priority (display in ID order for now)
- JSON output mode
- Showing human tasks (they're filtered out by `task_is_next_actionable`)
- Showing chunk-level or plan-level readiness (only task-level)

# Files to inspect

- `src/onward/cli.py` — `build_parser()` to add `ready` subcommand
- `src/onward/cli_commands.py` — add `cmd_ready`, reference `cmd_tree` and `cmd_report` for display patterns
- `src/onward/artifacts.py` — `task_is_next_actionable()`, `collect_artifacts()`, `artifact_project()`, `is_human_task()`
- `src/onward/execution.py` — `finalize_chunks_all_tasks_terminal()`

# Implementation notes

- The core logic is: `collect_artifacts(root)` → build `status_by_id` → filter tasks via `task_is_next_actionable` → group by plan/chunk → display.
- This is similar to `render_active_work_tree_lines` but filtered to only ready (actionable) tasks rather than all open/in_progress.
- Group plan → chunk → tasks using dicts keyed by plan_id and chunk_id. Sort by ID within each level.
- Use `colorize` for status display (same as `cmd_tree`).
- The `(A)` marker is always shown (human tasks are already filtered out by `task_is_next_actionable`). Include it for consistency with `onward tree`.
- If no ready tasks exist, print "No ready tasks" and exit 0.
- Consider: should this command also list chunks that have no tasks yet (implying they need splitting)? Probably not — keep it focused on actionable tasks.

# Acceptance criteria

- `onward ready` shows all actionable tasks grouped by plan/chunk
- `onward ready --project X` filters to that project
- Output includes plan title, chunk title+status, task title+marker
- Empty result prints "No ready tasks"
- `finalize_chunks_all_tasks_terminal` runs before display
- Tests cover: basic display, project filtering, no ready tasks

# Handoff notes

- This complements `onward next` (single pick) and `onward tree` (full tree). `ready` is the "what's available" view.
- If TASK-047 (effort metadata) has landed, consider showing effort next to each task. If not, skip it — the display format should degrade gracefully.
- Future enhancement: `--sort effort` to show smallest tasks first for quick wins.
