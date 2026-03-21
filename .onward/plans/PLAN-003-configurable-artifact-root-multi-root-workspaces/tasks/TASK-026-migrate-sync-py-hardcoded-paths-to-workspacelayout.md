---
id: "TASK-026"
type: "task"
plan: "PLAN-003"
chunk: "CHUNK-007"
project: ""
title: "Migrate sync.py hardcoded paths to WorkspaceLayout"
status: "open"
description: ""
human: false
model: "claude-sonnet-4-5"
executor: "onward-exec"
effort: "m"
depends_on: ["TASK-012"]
files: []
acceptance: []
created_at: "2026-03-21T15:49:49Z"
updated_at: "2026-03-21T15:49:49Z"
---

# Context

`sync.py` has ~10 hardcoded `.onward/` path references for plan directories, worktree paths, and git add targets. These must be migrated to use `WorkspaceLayout` for configurable root support.

# Scope

- Replace `root / ".onward" / "plans"` with `layout.plans_dir(project)` in all sync functions.
- Replace `wt / ".onward" / "plans"` (worktree plan paths) with layout-derived paths.
- Update `plans_dir` references in `ensure_branch_worktree`, `ensure_repo_clone`.
- Update `remote_plans_path` to use layout.
- Update `git_commit_plans_if_changed` git-add paths to use the correct artifact root.
- Update `worktree_path` default from hardcoded `.onward` to configurable root.
- Thread `layout` parameter through sync functions that need it.

# Out of scope

- Adding `--project` to sync subcommands (TASK-027).
- Multi-root sync strategy (syncing multiple roots — TASK-027 scope).
- Worktree or clone setup for multi-root.

# Files to inspect

- `src/onward/sync.py` — all functions with `.onward` string literals

# Implementation notes

- Sync is the most filesystem-heavy module. It creates worktrees, clones, copies plan files.
- Worktree plan paths: the worktree mirrors the workspace layout, so if the workspace uses `root: nb`, the worktree should also have `nb/plans/`.
- Git add paths must match the actual file paths relative to the repo root — changing the artifact root changes what paths get staged.
- Be careful with `ensure_repo_clone` — the cloned repo may have a different layout config.
- The sync config itself (`.onward.config.yaml:sync`) stays in the same place.

# Acceptance criteria

- No `.onward/` string literals remain in `sync.py`.
- Sync operations use layout-derived paths for plan directories.
- Worktree paths reflect the configured artifact root.
- Git add commands stage files under the correct paths.
- Existing sync tests pass.

# Handoff notes

- TASK-027 adds `--project` support so sync can target a specific project in multi-root mode.
- Sync with multi-root is complex — each project might sync to a different branch or repo. That design is deferred to TASK-027/future work.
