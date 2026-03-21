---
id: "TASK-027"
type: "task"
plan: "PLAN-003"
chunk: "CHUNK-007"
project: ""
title: "Add --project to sync subcommands"
status: "in_progress"
description: ""
human: false
model: "claude-sonnet-4-5"
executor: "onward-exec"
effort: "s"
depends_on:
- "TASK-026"
files: []
acceptance: []
created_at: "2026-03-21T15:49:50Z"
updated_at: "2026-03-21T18:09:35Z"
run_count: 1
---

# Context

Sync push, pull, and status need to know which project's plans to synchronize in multi-root mode. This mirrors the `--project` argument added to other commands in TASK-023 but applies specifically to sync subcommands.

# Scope

- Add `--project` argument to `sync push`, `sync pull`, `sync status` subparsers in `cli.py`.
- Thread the project value through to sync functions in `sync.py` and `cli_commands.py`.
- In multi-root mode, require `--project` for sync operations (sync operates on one project at a time).
- In single-root mode, `--project` is ignored.

# Out of scope

- Migrating sync.py hardcoded paths (TASK-026 — already done).
- Syncing all projects at once (future work — could iterate roots).
- Different sync configs per project (future work).

# Files to inspect

- `src/onward/cli.py` — sync subcommand parser definitions
- `src/onward/sync.py` — sync functions that need the project parameter
- `src/onward/cli_commands.py` — `cmd_sync_push`, `cmd_sync_pull`, `cmd_sync_status`

# Implementation notes

- Sync currently operates on the single `.onward/plans` directory. With `--project`, it operates on `layout.plans_dir(project)`.
- Error message when `--project` missing in multi-root: `"Sync requires --project when multiple roots are configured. Available: a, b"`.
- Consider whether `onward sync status` without `--project` could show status for all projects (similar to combined report in TASK-024). If so, implement it; if not, note as future work.
- The sync config (mode, remote, branch) is shared across projects — it's in `.onward.config.yaml` at the workspace level.

# Acceptance criteria

- `onward sync push --project nb` syncs only the `nb` project's plans.
- `onward sync status --project nb` shows sync status for that project.
- Missing `--project` in multi-root mode produces a clear error.
- Single-root mode works as before without `--project`.

# Handoff notes

- Per-project sync branches or per-project sync configs could be a future enhancement if users need different sync strategies per project.
