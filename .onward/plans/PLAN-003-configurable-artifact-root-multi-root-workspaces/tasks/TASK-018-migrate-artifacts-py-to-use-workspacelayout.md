---
id: "TASK-018"
type: "task"
plan: "PLAN-003"
chunk: "CHUNK-005"
project: ""
title: "Migrate artifacts.py to use WorkspaceLayout"
status: "in_progress"
description: ""
human: false
model: "claude-sonnet-4-5"
executor: "onward-exec"
effort: "l"
depends_on:
- "TASK-012"
files: []
acceptance: []
created_at: "2026-03-21T15:49:27Z"
updated_at: "2026-03-21T17:03:09Z"
run_count: 1
---

# Context

`artifacts.py` is the core module for discovering, loading, and indexing Onward artifacts. It has 6+ hardcoded `.onward/` path constructions that must be replaced with `WorkspaceLayout` method calls. This is one of the largest migration tasks.

# Scope

- Replace `root / ".onward/plans"` in `artifact_glob` and `find_plan_dir` with `layout.plans_dir(project)`.
- Replace index/recent file paths in `load_index`, `index_is_fresh`, `regenerate_indexes` with `layout.index_path(project)` and `layout.recent_path(project)`.
- Replace notes path in `_notes_path` with `layout.notes_dir(project)`.
- Thread a `layout` (or `project`) parameter through function signatures that currently take only `root`.
- For multi-root support, `artifact_glob` should accept an optional project filter: when `project=None` in multi-root mode, scan all plan directories.
- Update `regenerate_indexes` to handle per-project index files.

# Out of scope

- Migrating execution.py (TASK-019).
- Migrating config.py template/prompt resolution (TASK-020).
- Cross-root ID uniqueness logic (TASK-025).
- Updating callers in cli_commands.py (TASK-021).

# Files to inspect

- `src/onward/artifacts.py` — all functions with `.onward` string literals
- `src/onward/config.py` (or `layout.py`) — `WorkspaceLayout` class

# Implementation notes

- Many functions currently accept `root: Path` as first arg. Change to accept `layout: WorkspaceLayout` instead, or add layout as an additional parameter.
- `artifact_glob` is called from many places — ensure the signature change is compatible or provide an adapter.
- For multi-root `artifact_glob(project=None)`: iterate `layout.all_project_keys()`, glob each `plans_dir`, merge results. Artifact IDs must remain globally unique (enforced by TASK-025).
- Index files are per-project in multi-root mode: each project root gets its own `index.json` and `recent.json`.
- Be careful with `find_plan_dir` — it searches for a plan by ID. In multi-root mode, it may need to search across all roots.

# Acceptance criteria

- No `.onward/` string literals remain in `artifacts.py`.
- `artifact_glob` with default layout returns same results as before.
- `artifact_glob` with multi-root layout scans all plan directories.
- `load_index` / `regenerate_indexes` use layout-derived paths.
- All existing tests that exercise artifacts.py still pass (may need path fixture updates).

# Handoff notes

- This task touches many function signatures. Coordinate with TASK-019 and TASK-020 which do similar migrations in parallel modules — avoid merge conflicts on shared imports.
- TASK-021 will update the callers in split.py and cli_commands.py.
