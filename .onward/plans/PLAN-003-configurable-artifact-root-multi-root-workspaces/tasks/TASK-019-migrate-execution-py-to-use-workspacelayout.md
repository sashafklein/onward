---
id: "TASK-019"
type: "task"
plan: "PLAN-003"
chunk: "CHUNK-005"
project: ""
title: "Migrate execution.py to use WorkspaceLayout"
status: "open"
description: ""
human: false
model: "claude-sonnet-4-5"
executor: "onward-exec"
effort: "l"
depends_on: ["TASK-012"]
files: []
acceptance: []
created_at: "2026-03-21T15:49:29Z"
updated_at: "2026-03-21T15:49:29Z"
---

# Context

`execution.py` handles run records, ongoing task state, and plan reviews. It has 6+ hardcoded `.onward/` path references for runs, ongoing.json, and reviews directories that must be replaced with `WorkspaceLayout` method calls.

# Scope

- Replace `root / ".onward/ongoing.json"` with `layout.ongoing_path(project)` in `load_ongoing`, `_write_ongoing`.
- Replace `root / ".onward/runs"` with `layout.runs_dir(project)` in `_prepare_task_run`, `collect_runs_for_target`, `collect_run_records`.
- Replace `root / ".onward/reviews"` with `layout.reviews_dir(project)` in `execute_plan_review`.
- Thread `layout` parameter through all affected function signatures.
- Update `_prepare_task_run` to write run records under the correct project's runs directory.
- Update `collect_run_records` to scan the correct runs directory.

# Out of scope

- Migrating artifacts.py (TASK-018).
- Migrating config.py template/prompt paths (TASK-020).
- Migrating CLI command handlers (TASK-021).

# Files to inspect

- `src/onward/execution.py` — all functions with `.onward` string literals
- `src/onward/config.py` (or `layout.py`) — `WorkspaceLayout` class

# Implementation notes

- `ongoing.json` tracks currently executing tasks. In multi-root mode, each project has its own `ongoing.json` — a task in project A doesn't block project B.
- `collect_run_records` is used by report/progress commands. In multi-root mode with no project filter, it should scan all roots.
- Functions currently take `root: Path`. Change to `layout: WorkspaceLayout` with `project` parameter.
- The run record file naming (timestamp-based) is unchanged — only the parent directory changes.
- Review files use plan IDs in their filenames, which are globally unique, so no collision risk.

# Acceptance criteria

- No `.onward/` string literals remain in `execution.py`.
- `load_ongoing` / `_write_ongoing` use `layout.ongoing_path(project)`.
- Run records are written to `layout.runs_dir(project)`.
- Reviews are written to `layout.reviews_dir(project)`.
- All existing execution tests pass (may need fixture updates).

# Handoff notes

- Coordinate with TASK-018 (artifacts.py) — both change function signatures that cli_commands.py calls. TASK-021 updates the callers.
- If ongoing.json format needs a `project` field, note it for a follow-up task.
