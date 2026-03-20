---
id: "TASK-048"
type: "task"
plan: "PLAN-011"
chunk: "CHUNK-012"
project: ""
title: "Multi-project filtering and inheritance"
status: "open"
description: ""
human: false
model: "sonnet-latest"
executor: "ralph"
depends_on: []
blocked_by: []
files: []
acceptance: []
created_at: "2026-03-20T16:01:08Z"
updated_at: "2026-03-20T16:01:08Z"
---

# Context

The `--project` flag exists on some commands but the behavior is incomplete. Project metadata is set per-artifact but doesn't inherit: if a plan has `project: "myapp"`, its chunks and tasks don't automatically get that project. This task makes project filtering work consistently across all read commands and adds inheritance so child artifacts get their parent's project unless overridden.

# Scope

- Add `--project` flag to all read commands that don't have it yet: `onward show`, `onward progress`, `onward recent`, `onward ready` (if added by TASK-046)
- Implement project inheritance in `cmd_new_chunk`: if `--project` is not specified, inherit from the parent plan
- Implement project inheritance in `cmd_new_task`: if `--project` is not specified, inherit from the parent chunk
- Implement project inheritance in `prepare_task_writes` and `prepare_chunk_writes` in `split.py` (already uses `artifact_project(parent)` — verify it works correctly)
- Add `resolve_project(artifact, artifacts)` in `artifacts.py` that walks up the hierarchy (task → chunk → plan) to find the effective project
- Use `resolve_project` in filtering logic so a task with empty project but a plan with project "myapp" still appears under `--project myapp`
- Update `artifact_project()` to support hierarchical resolution (or add a separate resolver)
- Add tests for inheritance, filtering, and override behavior

# Out of scope

- Multi-value project filtering (`--project a --project b`)
- Project as a top-level organizational unit (it's just a metadata tag)
- Project-specific config (all projects share one `.onward.config.yaml`)
- Renaming or migrating projects

# Files to inspect

- `src/onward/artifacts.py` — `artifact_project()` (line ~208), `select_next_artifact`, `report_rows`, `render_active_work_tree_lines` for existing project filtering
- `src/onward/cli.py` — all subparsers to verify `--project` flag presence
- `src/onward/cli_commands.py` — `cmd_new_chunk`, `cmd_new_task`, `cmd_show`, `cmd_progress`, `cmd_recent`, all commands that use project filtering
- `src/onward/split.py` — `prepare_task_writes`, `prepare_chunk_writes` for `artifact_project` usage

# Implementation notes

- `resolve_project(artifact, artifacts_or_by_id)` logic:
  1. If artifact has non-empty `project`, return it
  2. If artifact is a task, look up parent chunk; if chunk has project, return it
  3. If artifact is a task or chunk, look up parent plan; if plan has project, return it
  4. Return empty string
- This requires a `status_by_id`-like lookup dict. Pass a `dict[str, Artifact]` or the full artifact list.
- For filtering: when `--project myapp` is specified, include an artifact if `resolve_project(artifact, by_id) == "myapp"`.
- Inheritance in `cmd_new_chunk`: look up the parent plan, use `artifact_project(plan)` if `--project` is empty.
- Inheritance in `cmd_new_task`: look up the parent chunk (already done to get `plan_id`), use `artifact_project(chunk)` if `--project` is empty.
- `prepare_chunk_writes` and `prepare_task_writes` already use `artifact_project(parent)` — verify this is correct and inherits properly. It should be correct already since it reads the parent's project field.
- Don't break the current behavior: explicit `--project ""` should still set empty project (override, not inherit).

# Acceptance criteria

- `onward new chunk PLAN-X "title"` inherits project from plan if `--project` not specified
- `onward new task CHUNK-X "title"` inherits project from chunk (or chunk's plan)
- `--project myapp` filtering on `list`, `report`, `tree`, `ready`, `next`, `show`, `progress`, `recent` includes artifacts with inherited project
- Explicit `--project ""` overrides to empty
- `resolve_project` walks task → chunk → plan hierarchy
- Tests cover: inheritance, filtering with inherited project, override to empty

# Handoff notes

- The `resolve_project` function is useful for `onward report` and `onward tree` which already filter by project — switch them to use hierarchical resolution.
- `artifact_project()` currently just reads the field. After this task, there should be a clear distinction: `artifact_project()` reads the raw field, `resolve_project()` does hierarchical resolution.
- If performance matters (many artifacts), consider caching the `by_id` dict in commands that iterate multiple times.
